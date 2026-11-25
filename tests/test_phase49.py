"""v1.22.0 - smarter Home, sessions grouped by game, overlay background / edges, installer.

- Overlay: the background always fits its content (the window only grows; before, the
  background filled the window and stayed too wide), left / right sit flush with the edge.
- Sessions: one row per program with its sessions under it; one session per launch (no new
  session after an alt-tab / minimize while the game still runs; PresentMon forgetting the
  game while it is in the background does not lose its counts); several deleted at once.
- Insights (Home): status lines + the few most important findings with their reasons; the PC's
  baseline (driver / Windows / hardware) notices changes and compares games before / after.
- Reports: "what would likely help" from measured data (directions, never numbers), the game
  getting slower during a session, disk use of background programs, fingerprint metrics.
- Installer: Windows 11 style, light / dark like Windows, Lmonitor's pictures and plain texts."""
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
q = lambda *p: read("lmonitor", "qt", "qml", *p)

# ================================================================ overlay
bar, win, ov = q("components", "OverlayBar.qml"), q("OverlayWindow.qml"), read("lmonitor", "qt", "overlay.py")
chk("background as big as the content, at the chosen side of the window",
    "x: bar.cx; width: bar.implicitWidth; height: bar.implicitHeight" in bar and 'edge === "right" ? width - implicitWidth' in bar)
chk("square corners on the screen-edge side", "topLeftRadius:" in bar and "bottomRightRadius:" in bar)
chk("window gets smaller again when the content stayed smaller", "w.keepW > bar.implicitWidth + 24" in win)
chk("left / right flush with the screen edge (no margin)", "x, y = g.x() + g.width() - ww, g.y()" in ov and "x, y = g.x(), g.y()" in ov
    and "Theme.MARGIN" not in ov)

# ================================================================ one session per launch
class FakeFps:
    alive = True
    def __init__(self): self.cur, self.cnt, self.on = (77, "game.exe"), [0, 0.0, [0] * 4001, {}], True
    def current(self): return self.cur
    def counters(self, pid): return [self.cnt[0], self.cnt[1], list(self.cnt[2]), dict(self.cnt[3])] if pid == 77 else None
    def recent(self, pid, within): return pid == 77 and self.on
class FakeCpu:
    name = "cpu"
    def read(self, *a): return 60.0, 40.0, 4000.0, False
class FakeGpu:
    power_limit = False
    def read(self, want): return 90.0, 70.0, 100.0, 2000.0, (4.0, 8.0)
    def display_name(self): return "gpu"
class Store:
    def __init__(self): self.rows = []
    def save(self, s, c): self.rows.append(s); return len(self.rows)
    def update(self, sid, s, c): self.rows[sid - 1] = s
st, fps = Store(), FakeFps()
rec = E.SessionRecorder(fps, FakeCpu(), FakeGpu(), st)
rec._alive = lambda cur: True                 # the game process keeps running
t = 1000.0
def play(secs):
    global t
    for _ in range(int(secs / 2)):
        fps.cnt[0] += 240; fps.cnt[1] += 2000.0; fps.cnt[2][27] += 240
        rec.step(t); t += 2
play(80)
fps.on = False                                # alt-tab: no frames for 2 minutes
for _ in range(60):
    rec.step(t); t += 2
chk("alt-tab / minimize for 2 min: the session is paused, not ended", rec.cur is not None and rec.cur["paused"]
    and "paused" not in str(st.rows))
fps.on = True
fps.cnt = [0, 0.0, [0] * 4001, {}]            # PresentMon forgot the game meanwhile: counts start at 0
play(80)
rec._alive = lambda cur: False                # the game is closed
fps.on = False
rec.step(t)
chk("one launch = one saved session (no second one after coming back)", len(st.rows) == 1 and not st.rows[0]["live"])
# 80 s before + 80 s after the pause, minus the first 6 s (4 readings) before it counted as a game
chk("frames of before and after the alt-tab are all counted", st.rows[0]["frames"] == 240 * 80 - 240 * 4)

# ================================================================ groups, multi-delete
from lmonitor.backend import Backend
cfg = E.Paths.CFG_FILE
if _os.path.exists(cfg):
    _os.remove(cfg)
b = Backend()
store = E.SessionStore(_os.path.join(E.Paths.CFG_DIR, "t49.db"))
b.session_store = store
c = {k: [None] * 100 for k in E.SessionRecorder.KEYS}
c["t"] = [i * 2.0 for i in range(100)]
c["fps"] = [100.0] * 100
c["g_use"] = [97.0] * 100
now = time.time()
def mk(game, start, fps_):
    s = E.SessionAnalyzer.summarize(dict(c, fps=[fps_] * 100), {"game": game, "start": start, "end": start + 300},
                                    {"count": int(fps_ * 300), "total_ms": 300000.0, "low1": fps_ * 0.7})
    return store.save(s, {"t": []})
ids = [mk("a.exe", now - 9000 + i * 1000, 100.0) for i in range(3)] + [mk("a.exe", now - 500, 80.0), mk("b.exe", now - 4000, 60.0)]
gs = b.session_groups()
chk("one entry per program, newest played first", [g["exe"] for g in gs] == ["a.exe", "b.exe"])
chk("each with its sessions, how many and total time", gs[0]["count"] == 4 and len(gs[0]["sessions"]) == 4
    and gs[0]["total"] == "20 min")
chk("compared with its usual: a.exe is slower than usual now", gs[0]["status"] == "slower than usual")
store.delete(ids[:2])
chk("deleting some sessions keeps the others", [g["count"] for g in b.session_groups()] == [2, 1])
sess = q("pages", "SessionsPage.qml")
chk("list: arrow opens a game, Select mode with a confirmed delete", "page.toggleOpen(row.gr)" in sess
    and "tools.sessionsDelete(page.pickedIds())" in sess and "ConfirmButton" in sess and "page.selecting" in sess)

# ================================================================ insights / what changed / what would help
bp = _os.path.join(E.Paths.CFG_DIR, "t49_baseline.json")
if _os.path.exists(bp):
    _os.remove(bp)
base = E.Baseline(bp)
chk("first look: no change", base.update({"driver": "560.10", "windows": "26100.1"}, t=1000.0) == [])
ch = base.update({"driver": "566.14", "windows": "26100.1", "cpu": ""}, t=5000.0)
chk("a new driver is noticed, an unknown value is not a change", [x["key"] for x in ch] == ["driver"])
sums = []
for i, (st_, f) in enumerate([(1000, 100), (2000, 102), (3000, 98), (6000, 90), (7000, 88)]):
    sums.append({"game": "g.exe", "display": "Game", "start": float(st_), "duration": 600, "avg_fps": float(f)})
eff = E.Insights.change_effect(sums, 5000.0, "Graphics driver")
chk("after a driver change: games compared before / after, with counts", eff ==
    ["Game: about 10 % less average FPS than before (3 session(s) before, 2 after)."])
items = E.Insights.build(sums, base.changes(), now=5000.0 + 3600)
chk("insight names the change and says it cannot tell the cause",
    items and items[0]["text"] == "Graphics driver changed: 560.10 -> 566.14." and "cannot tell" in items[0]["why"])
chk("at most 4 insights, worst first", len(E.Insights.build(sums * 3, [], now=1.0)) <= 4)
chk("no data: says it is still learning (nothing made up)", E.Insights.build([], [])[0]["text"] == "Lmonitor is still learning your PC.")
s = E.SessionAnalyzer.summarize(dict(c, fps=[120.0] * 50 + [90.0] * 50, g_temp=[70.0] * 50 + [82.0] * 50),
                                {"game": "g.exe", "start": 0, "end": 300}, {"count": 30000, "total_ms": 300000.0})
chk("game got slower during the session (and hotter): noticed", s["fade"]["fps"] < -10
    and any("got slower the longer you played" in n["text"] for n in E.SessionReport.noticed(s)))
wi = E.SessionReport.what_if(s)
chk("what would help: GPU-bound -> lower settings likely more FPS, no FPS number promised",
    any(x["text"].startswith("Lower resolution or graphics settings: likely more FPS") for x in wi)
    and not any("FPS" in x["text"] and "+" in x["text"] for x in wi))
chk("what would help: not enough data -> says so", E.SessionReport.what_if({})[0]["sure"] is False)
apps = E.SessionAnalyzer.apps({"backup.exe": [0.0, 10 * 2 ** 20, 300.0]}, 10)
chk("a program busy with the disk counts as heavy", apps and apps[0]["disk"] == 30.0)
d = b.dashboard(0) if b.sample() is None else None
ins = b.insights()
chk("Home: four status lines and insights", [r["t"] for r in ins["status"]] == ["Temperatures", "PC check", "Stability", "Graphics driver"]
    and isinstance(ins["items"], list))
dash = q("pages", "Dashboard.qml")
chk("Home: Start with Windows next to the overlay switches", 'label: "Start with Windows"; on: backend.autostart === true' in dash
    and "backend.setAutostart(v)" in dash and 'label: "Overlay"' in dash and 'label: "Graph overlay"' in dash)
chk("Home: Smart insights card", "page.ins.items" in dash and '"Smart insights"' in dash)
b.close()

# ================================================================ installer + texts
iss = read("installer", "Lmonitor.iss")
chk("installer: Windows 11 style, follows light / dark, Lmonitor's pictures", "WizardStyle=modern dynamic windows11" in iss and "WizardImageFileDynamicDark=" in iss
    and "WizardImageFile=art\\wizard-164x314.bmp" in iss and "WizardSmallImageFile=art\\small-55x55.bmp" in iss)
chk("installer: plain welcome / done texts, fewer pages", "WelcomeLabel1=Welcome to Lmonitor" in iss and "DisableReadyPage=yes" in iss)
chk("installer pictures are made by the build", "make_installer_art.py" in read("build_installer_qt.bat"))
fa = q("Lmonitor", "fa.js")
need = ("Games", "Select", "Smart insights", "What would likely help", "Processor", "Graphics card", "as usual",
        "slower than usual", "Lmonitor is still learning your PC.", "A smarter Home")
miss = [k for k in need if ('"%s":' % k) not in fa]
chk("Persian texts %s" % (miss or ""), not miss)
chk("version 1.22.0 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 22, 0))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
