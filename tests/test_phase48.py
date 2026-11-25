"""v1.21.4 - a name of your own for each game (for good), and how Windows showed the game.

- The pencil in Sessions names the PROGRAM: every session of it, now and later, and Home's
  "Right now" / "Last session" show that name. Empty = the program's own name again.
- Each session now keeps how Windows showed the game (PresentMon's PresentMode column) and
  whether Lmonitor's overlay was on. A window above a full-screen game can take it out of the
  fast "independent flip" path - two benchmarks (overlay on / off) now show if that happens;
  "Overlay: on -> off" is listed under what changed."""
import os as _os, sys, time, json
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, _os.path.join(ROOT, "tests", "stubs"))

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

import lmonitor.engine as E
from lmonitor.backend import Backend
cfg = E.Paths.CFG_FILE
if _os.path.exists(cfg):
    _os.remove(cfg)
b = Backend()
st = E.SessionStore(_os.path.join(E.Paths.CFG_DIR, "t48.db"))
b.session_store = st
c = {k: [None] * 40 for k in E.SessionRecorder.KEYS}
c["t"] = [i * 2.0 for i in range(40)]
for day in (0, 1):
    s = E.SessionAnalyzer.summarize(c, {"game": "FortniteClient-Win64-Shipping.exe", "start": time.time() - 9000 + day * 3000,
                                        "end": time.time() - 8000 + day * 3000}, {"count": 0})
    st.save(s, {"t": []})
b.name_program("FortniteClient-Win64-Shipping.exe", "  Fortnite ")
items = b.tools_sessions()["items"]
chk("every session of the program shows its name", [i["game"] for i in items] == ["Fortnite", "Fortnite"])
rep = b.session_report(items[0]["id"])
chk("report: the name, the file name below", rep["game"] == "Fortnite" and rep["game_name"] == "FortniteClient-Win64-Shipping")
s = E.SessionAnalyzer.summarize(c, {"game": "fortniteclient-win64-shipping.exe", "start": time.time(), "end": time.time() + 99}, {"count": 0})
st.save(s, {"t": []})
chk("a new session later gets the same name (any letter case)", b.tools_sessions()["items"][0]["game"] == "Fortnite")
b.save_settings()
chk("kept in the settings file (after a restart too)", json.load(open(cfg, encoding="utf-8"))["game_names"]
    == {"fortniteclient-win64-shipping.exe": "Fortnite"} and Backend().settings["game_names"]["fortniteclient-win64-shipping.exe"] == "Fortnite")
b.name_program("FortniteClient-Win64-Shipping.exe", "")
chk("empty name: the program's own name again", b.tools_sessions()["items"][0]["game"] == "fortniteclient-win64-shipping")
b.name_program("x.exe", "y" * 100)
chk("at most 60 letters", len(b.settings["game_names"]["x.exe"]) == 60)

# ---- how Windows showed the game
import threading
E.WinApi.foreground_pid = staticmethod(lambda: 4242)
class Out:
    def __iter__(self):
        yield "Application,ProcessID,MsBetweenPresents,PresentMode\n"
        for i in range(300):
            yield "game.exe,4242,6.9,%s\n" % ("Hardware: Independent Flip" if i < 240 else "Composed: Flip")
class Proc:
    stdout = Out()
    def poll(self): return None
m = E.FpsMonitor()
pr = Proc()
m.proc = pr
m._reader(pr)
cnt = m.counters(4242)
chk("PresentMon's display mode counted per frame", cnt and cnt[3] == {"Hardware: Independent Flip": 240, "Composed: Flip": 60})
m.proc = None
fake_cur = {"base": (0, 0.0, [0] * 4001, {}), "last": (300, 2070.0), "hist": cnt[2], "modes": cnt[3],
            "name": "game.exe", "start": time.time() - 70, "approx": False, "apps": {}, "scans": 0,
            "c": c, "sid": None, "extra": {"overlay": True}}
class G:
    def display_name(self): return "gpu"
class Cpu:
    name = "cpu"
rec = E.SessionRecorder(m, Cpu(), G(), st)
sid = rec._save(fake_cur, time.time(), live=False)
saved = next(x["summary"] for x in st.list() if x["id"] == sid)
chk("session keeps the display mode shares and the overlay state", saved["present_modes"] ==
    {"Hardware: Independent Flip": 0.8, "Composed: Flip": 0.2} and saved["overlay"] is True)
rows = E.SessionView.rows_summary(saved)
chk("shown in the details", any(r[1] == "Hardware: Independent Flip" and "80 %" in r[2] for r in rows if len(r) > 2))
a = dict(saved, start=1.0, duration=600, benchmark=True, overlay=True, avg_fps=100.0)
bb = dict(saved, start=9e9, duration=600, benchmark=True, overlay=False, avg_fps=110.0)
chk("compare: overlay on -> off listed", "Overlay: on -> off" in E.SessionReport.compare(a, bb)["changed"])
chk("the overlay state comes from the settings", '"overlay": bool(st["on"] or st["hud_on"] or st["hud2_on"])' in read("lmonitor", "backend.py"))
sess = read("lmonitor", "qt", "qml", "pages", "SessionsPage.qml")
chk("pencil names the program", "tools.programRename(page.rep.exe" in sess and "every session of this game" in sess)
chk("version 1.21.4 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 21, 4))
b.close()
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
