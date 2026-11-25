"""v1.20.0 - a smarter companion, still simple.

- Sessions: a report with the main numbers first (average / 1% / 0.1% low FPS, hottest CPU /
  GPU, average CPU / GPU power, time played, frame time), what was noticed in plain words,
  all details on request, two sessions compared, saved as a picture.
- Warnings about the hardware (hot, heating up fast, thermal slowdown, memory / VRAM almost
  full, big FPS drop): reported once, not again for 15 min, only from real readings.
- Every game keeps its own overlay settings, automatically.
- Sensors that stop answering are shown as "not available", never with an old value.
- The update shows what the new version changes; About explains what Lmonitor keeps."""
import os as _os, sys, io, json, time
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

# ================================================================ sensors that stop answering
br = E.BackgroundReader(lambda: None, 1.0, "t")
br.runs, now = 5, time.monotonic()
br.ok_at, br._started = now - 2, now - 100
chk("fresh reading: not stale", not br.stale(now))
br.ok_at = now - 30
chk("no good reading for 30 s: stale", br.stale(now))
br._started = now - 3
chk("thread just (re)started: not stale yet", not br.stale(now))
def boom(): raise RuntimeError("driver hang")
b2 = E.BackgroundReader(boom, 1.0, "t2")
b2._run_once()
chk("a failing reading does not count as good", b2.ok_at == 0.0 and b2.runs == 1)
hw = read("lmonitor", "engine.py")
chk("CPU / GPU readers hide values of a stopped sensor", "self.stale = self._bg.stale()" in hw
    and "if h.cpu_hw is not None and not self.stale:" in hw and "if self.available and not self.stale:" in hw)
chk("Hardware page says the sensor stopped", "the sensor stopped answering" in hw)

# ================================================================ warnings
A = E.Alerts
def run(seq, start=1000.0, step=1.0, thermal=None, fps=None):
    al, out, t = A(), [], start
    for snap in seq:
        out += al.check(snap, fps(t) if fps else None, t, thermal)
        t += step
    return al, out
cool = {"c_temp": 60, "g_temp": 60, "c_use": 30, "g_use": 30, "r_use": 50}
hot = dict(cool, c_temp=98)
al, out = run([hot] * 40)
chk("CPU hot for 40 s: one warning", [a["key"] for a in out] == ["cpu_hot"])
al, out = run([hot] * 20)
chk("hot for 20 s only: no warning", out == [])
al, out = run([hot] * 40 + [cool] * 30 + [hot] * 40)
chk("comes back within 15 min: not repeated", [a["key"] for a in out if a["key"] == "cpu_hot"] == ["cpu_hot"])
al, out = run([hot] * 40 + [cool] * 70 + [hot] * 40, step=10)
chk("over and back after 15+ min: reported again", [a["key"] for a in out if a["key"] == "cpu_hot"] == ["cpu_hot", "cpu_hot"])
al, out = run([{"c_temp": None, "g_temp": None, "c_use": None, "g_use": None, "r_use": None}] * 60)
chk("no sensors: no warnings (nothing guessed)", out == [])
al, out = run([dict(cool, g_temp=60 + i * 1.5) for i in range(20)])
chk("GPU +28 °C in 20 s with the same load: 'heated up fast'", "gpu_jump" in [a["key"] for a in out])
al, out = run([dict(cool, g_temp=60 + i * 1.5, g_use=10 + i * 4) for i in range(20)])
chk("same rise while the load went up (a game started): no warning", "gpu_jump" not in [a["key"] for a in out])
al, out = run([dict(cool, g_use=99)] * 10, thermal=True)
chk("driver says 'slowed down by heat' under load: warning", [a["key"] for a in out] == ["gpu_throttle"]
    and "reducing its performance because of high temperature" in out[0]["title"])
al, out = run([dict(cool, g_use=99)] * 10, thermal=None)
chk("driver does not say: no throttle warning", out == [])
al, out = run([dict(cool, g_mem=(7.8, 8.0))] * 40)
chk("VRAM 97 % for 40 s: warning", [a["key"] for a in out] == ["vram_full"])
al, out = run([dict(cool, r_use=95)] * 40)
chk("RAM 95 % for 40 s: warning", [a["key"] for a in out] == ["ram_full"])
al, out = run([cool] * 80, fps=lambda t: 120 if t < 1070 else 40)
chk("FPS 120 -> 40 for a few seconds: warning", [a["key"] for a in out] == ["fps_drop"])
al, out = run([cool] * 80, fps=lambda t: 25 if t < 1070 else 10)
chk("an already low frame rate: no FPS warning", out == [])
al, out = run([hot] * 40)
chk("new warnings are handed to the window once", len(al.take()) == 1 and al.take() == [])
chk("Persian text for every warning", set(A.FA) == set(A.RULES))
chk("every warning says what to do", all(r[2] for r in A.RULES.values()))

# ================================================================ session summary / report
n = 150
c = {k: [None] * n for k in E.SessionRecorder.KEYS}
c["t"] = [1000.0 + i * 2 for i in range(n)]
c["fps"] = [100.0] * n
for k, v in (("c_use", 40), ("c_temp", 70), ("c_clk", 4000), ("c_pow", 45), ("g_use", 90), ("g_temp", 72),
             ("g_clk", 2000), ("g_pow", 110), ("ram", 55), ("avail", 8)):
    c[k] = [float(v)] * n
meta = {"game": "game.exe", "start": 1000.0, "end": 1300.0, "plan": "Balanced", "driver": "560.10"}
s = E.SessionAnalyzer.summarize(c, meta, {"count": 30000, "total_ms": 300000.0, "low1": 60.0, "low01": 40.0})
chk("summary: average power of CPU and GPU", s["c_pow"][0] == 45 and s["g_pow"][0] == 110)
chk("summary: frame times (avg, 1%, 0.1%)", [round(x, 1) for x in s["ft"]] == [10.0, 16.7, 25.0])
chk("summary: power plan and driver kept for comparisons", s["plan"] == "Balanced" and s["driver"] == "560.10")
s2 = E.SessionAnalyzer.summarize(c, meta, {"count": 5000, "total_ms": 50000.0, "low1": 60.0, "low01": 40.0})
chk("0.1% low needs 10,000 frames: not shown with 5,000", s2["low01"] is None and s2["low1"] == 60.0)
c_old = {k: v for k, v in c.items() if k != "c_pow"}
chk("old sessions without CPU power still work", E.SessionAnalyzer.summarize(c_old, meta, {"count": 0})["c_pow"] == [None, None])
R = E.SessionReport
tiles = {t["key"]: t["value"] for t in R.tiles(s)}
chk("report: 8 main numbers", len(tiles) == 8 and tiles["avg_fps"] == 100 and tiles["g_temp"] == 72)
chk("report: missing value stays None ('Not measured')", {t["key"]: t["value"] for t in R.tiles(s2)}["low01"] is None)
chk("report: a smooth game says so", R.noticed(s) == [] and "smooth" in R.verdict(s, []))
hot_s = dict(s, gpu_status="possible")
nt = R.noticed(hot_s)
chk("report: GPU throttling in plain words, with what to do", nt and nt[0]["sev"] == "warn"
    and "graphics card slowed itself down" in nt[0]["text"] and nt[0]["tip"])
chk("report: no FPS measured -> said honestly", "not measured" in R.verdict(dict(s, avg_fps=None), []))
# comparison
before = dict(s, start=1000.0, duration=600, avg_fps=100.0, low1=60.0, g_temp=[80.0, 85.0], c_temp=[70.0, 80.0])
after = dict(s, start=99999.0, duration=600, avg_fps=112.0, low1=61.0, g_temp=[73.0, 78.0], c_temp=[71.0, 80.0],
             driver="565.90")
cmp = R.compare(after, before, [{"t": 5000.0, "title": "Power plan: Balanced -> High performance", "status": "applied"},
                                {"t": 200000.0, "title": "later", "status": "applied"}])
texts = [r["text"] for r in cmp["rows"]]
chk("compare: FPS +12 %", "Your average FPS increased by 12 %." in texts)
chk("compare: GPU 7 °C cooler", "Your average GPU temperature decreased by 7 °C." in texts)
chk("compare: small changes = about the same", "Your 1% low FPS stayed about the same." in texts
    and "Your average CPU temperature stayed about the same." in texts)
chk("compare: better / worse marked", next(r for r in cmp["rows"] if r["label"] == "GPU temperature")["better"] is True)
chk("compare: what changed in between (driver, Optimizer change)", cmp["changed"] ==
    ["Graphics driver: 560.10 -> 565.90", "Power plan: Balanced -> High performance"])
chk("compare: two different games are not compared", not R.compare(before, dict(after, game="other.exe"))["ok"])
chk("compare: too short is not compared", not R.compare(before, dict(after, duration=60))["ok"])

# ================================================================ every game keeps its own settings
from lmonitor.backend import Backend
cfg = E.Paths.CFG_FILE
if _os.path.exists(cfg):
    _os.remove(cfg)
b = Backend()
st = b.settings
chk("on by default, no game yet", st["profiles_on"] and st.game == "" and st["alerts_on"])
b.set_setting("alpha", 70)
st.begin_game("Game.exe")
chk("a game without own settings: the normal ones", st["alpha"] == 70)
b.set_setting("alpha", 95)
b.set_setting("hud_on", True)
chk("changes while it runs are kept for that game", st["game_profiles"]["game.exe"] == {"alpha": 95, "hud_on": True})
b.set_setting("language", "fa")
chk("window settings are not part of a game's settings", "language" not in st["game_profiles"]["game.exe"])
st.save()
saved = json.load(open(cfg, encoding="utf-8"))
chk("saving while a game runs keeps the normal values", saved["alpha"] == 70 and saved["hud_on"] is False
    and saved["game_profiles"]["game.exe"]["alpha"] == 95)
st.end_game()
chk("game closed: normal settings back", st["alpha"] == 70 and st["hud_on"] is False and st.game == "")
st.begin_game("game.exe")
chk("next start of that game: its own settings", st["alpha"] == 95 and st["hud_on"] is True)
st.forget_game("game.exe")
chk("'Use the normal settings': forgotten and switched back", st["alpha"] == 70 and "game.exe" not in st["game_profiles"])
st.end_game()

class FakeFps:
    alive = True
    def __init__(self): self.cur = (4242, "Game.exe")
    def current(self): return self.cur
b.fps = FakeFps()
import psutil as _ps
real_exists = _ps.pid_exists
_ps.pid_exists = lambda pid: pid == 4242
try:
    t0 = 100.0
    chk("a program in front for 2 s is not a game yet", not b.game_tick(t0) and not b.game_tick(t0 + 2))
    st["game_profiles"]["game.exe"] = {"alpha": 55}
    chk("in front for 6 s: its settings are used", b.game_tick(t0 + 7) and st["alpha"] == 55 and st.game == "game.exe")
    b.fps.cur = (1, "chrome.exe")
    chk("game in the background (still running): its settings stay", not b.game_tick(t0 + 9) and st["alpha"] == 55)
    _ps.pid_exists = lambda pid: False
    chk("game closed: back to normal", b.game_tick(t0 + 11) and st["alpha"] == 70 and b.game is None)
    b.fps.cur = (7, "chrome.exe")
    b.game_tick(t0 + 20); b.game_tick(t0 + 30)
    chk("a browser is never a game", b.game is None)
finally:
    _ps.pid_exists = real_exists
gp = b.game_profile()
chk("Overlay page data: on, game, own settings, count", set(gp) == {"on", "game", "has_own", "count"})

# ================================================================ alerts from real readings
chk("warnings are checked on every reading", "self.alerts.check(snap, game_fps, thermal=self.gpu.thermal)"
    in read("lmonitor", "backend.py"))
chk("NVIDIA's own 'slowed down by heat' flag is read", "nvmlDeviceGetCurrentClocksEventReasons" in hw and "THERMAL_BITS" in hw)

# ================================================================ update notes
from lmonitor import updater as U
rel = {"tag_name": "v9.0.0", "html_url": "x", "prerelease": False, "draft": False,
       "body": "## New\r\n- **Faster** [docs](http://x)\r\n![pic](a.png)\r\nDone",
       "assets": [{"name": "Lmonitor_Setup_9.0.0.exe", "size": 1,
                   "browser_download_url": "https://github.com/unrealhamed/Lmonitor/releases/download/v9.0.0/Lmonitor_Setup_9.0.0.exe"}]}
info = U.latest("1.0.0", lambda req, timeout=None: io.BytesIO(json.dumps(rel).encode()))
chk("update shows the release's own text, plain", info["notes"] == "New\n•  Faster docs\nDone")

# ================================================================ the window
q = lambda *p: read("lmonitor", "qt", "qml", *p)
sess, ovl, hwp, about, main = q("pages", "SessionsPage.qml"), q("pages", "OverlayPage.qml"), q("pages", "HardwarePage.qml"), \
    q("pages", "About.qml"), q("Main.qml")
chk("Sessions: report, compare, picture, details on request", all(x in sess for x in (
    "tools.sessionReport(", "tools.sessionCompare(", "tools.saveWindowArea(", "page.details ?", '"Not measured"')))
chk("Overlay: one card for per-game settings", "backend.gameProfile" in ovl and '"profiles_on"' in ovl)
chk("Hardware: warnings switch and recent warnings", "backend.setAlertsOn" in hwp and "Recent warnings" in hwp)
chk("About: update notes and privacy", "backend.update.notes" in about and "Your data and privacy" in about)
chk("menu unchanged (11 items + hidden Network usage)", sum(1 for l in ("Home", "Graphs", "Hardware", "Overlay", "Graph overlay",
    "Sessions", "Optimizer", "Storage", "PC check", "Personalize", "About") if ('label: "%s", icon:' % l) in main) == 11)
fa = q("Lmonitor", "fa.js")
need = ("Settings for each game", "Warn me about problems", "Recent warnings", "What we noticed", "Not measured",
        "Compare with another session", "Save as picture", "Before and after", "Your data and privacy",
        "A smooth session: nothing slowed the game down.", "Your graphics card slowed itself down because it got too hot.",
        "Your graphics card is reducing its performance because of high temperature.")
miss = [k for k in need if ('"%s":' % k) not in fa]
chk("Persian texts %s" % (miss or ""), not miss)
chk("1.20.1: empty Sessions says when recording is off, with a button", "Turn on recording" in sess
    and "tools.sessionsOn(true)" in sess and '"Turn on recording":' in fa and "visible: !!page.rep.ft" in sess)
wn = E.WhatsNew.pending("1.19.1", "1.20.0")
chk("What's new for 1.20.0", wn and wn["version"] == "1.20.0" and len(wn["slides"]) >= 3)
chk("version 1.20.0 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 20, 0))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
