"""v1.17.7 - every chart: only "Real time" and "1 min" (real time first); Home page:
graph overlay switch and a "Right now" box instead of overlay settings."""
import os as _os, sys, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

from copy import deepcopy
from lmonitor.engine import Hud, Settings
from lmonitor.backend import Backend, RANGES
from lmonitor.graphs import GraphHistory

cfg = deepcopy(Settings.DEFAULTS)
chk("graph overlays: real time or 1 minute only", Hud.WINDOWS == (0, 60))
chk("graph overlays start in real time", cfg["hud_window"] == 0 and cfg["hud2_window"] == 0)
chk("an old saved span (30 s, 2 min, 5 min) becomes real time", all(
    Settings._clean(dict(deepcopy(cfg), hud_window=w))["hud_window"] == 0 for w in (30, 120, 300)))
chk("1 minute is kept", Settings._clean(dict(deepcopy(cfg), hud_window=60))["hud_window"] == 60)
chk("window charts: real time first, then 1 minute", RANGES == (("Real time", 0), ("1 min", 60)))


class FakeTel:
    interval = 1.0
    snap = {"c_use": 20.0, "r_use": 40.0, "g_use": 50.0, "net_down": 1000.0, "net_up": 10.0}


b = Backend.__new__(Backend)
b.settings = Settings.__new__(Settings)
b.settings.data = Settings._clean(deepcopy(cfg))
b.telemetry = FakeTel()
b.graphs = GraphHistory()
b.hud_hist = GraphHistory(keys=Backend.HUD_KEYS, keep=330)
now = time.time()
for i in range(80):                                   # 20 s of 4-a-second readings
    b.hud_hist.add({"c_use": 10.0 + i % 4, "r_use": 40.0, "g_use": 50.0, "net_down": 5.0}, None, now - 20 + i * 0.25)
for i in range(70):
    b.graphs.add({"c_use": 20.0, "r_use": 40.0, "g_use": 50.0}, {"Fan 1": 2000.0}, now - 70 + i)
rt = b.graph_series(0)
chk("real time: 40 points of 250 ms (the last 10 s)", rt["points"] == 40 and abs(rt["slot_ms"] - 250.0) < 1e-6)
chk("real time lines come from the fast readings", rt["c_use"][-1] in (10.0, 11.0, 12.0, 13.0) and None not in rt["c_use"][-30:])
chk("real time has the network line too", rt["net_down"][-1] == 5.0)
chk("fan speeds (read once a second) are still there in real time", "Fan 1" in rt["fans"])
m1 = b.graph_series(60)
chk("1 minute: 60 points of 1 s", m1["points"] == 60 and abs(m1["slot_ms"] - 1000.0) < 1e-6 and m1["c_use"][-1] == 20.0)
chk("both carry the scroll data", all(k in rt and k in m1 for k in ("end_ms", "extra", "delay_ms")))
chk("fast readings only while a real-time chart is on screen", b.hud_realtime() is False)
b.graph_fast = True
chk("...then 4 readings a second", b.hud_realtime() and b.hud_period() == 0.25)
b.graph_fast = False

br = read("lmonitor", "qt", "bridge.py")
chk("fast readings stop when the window is hidden or a game covers it",
    "b.graph_fast = self._graph_fast and self._ui_visible and not self._covered" in br)
main = read("lmonitor", "qt", "qml", "Main.qml")
chk("leaving the chart pages stops the fast readings", "backend.setGraphFast(false)" in main)
gp = read("lmonitor", "qt", "qml", "pages", "GraphsPage.qml")
chk("Graphs page: two spans, real time first", "property int range: 0" in gp and "readonly property var secs: [0, 60]" in gp
    and "5 min" not in gp and "10 min" not in gp)
hp = read("lmonitor", "qt", "qml", "pages", "HudPage.qml")
chk("Graph overlay page: two spans", 'model: ["Real time", "1 min"]' in hp and "5 min" not in hp)
dash = read("lmonitor", "qt", "qml", "pages", "Dashboard.qml")
chk("Home: no overlay settings in the box any more", "Liquid glass look" not in dash and "Show the overlay in games" not in dash
    and "Show only when I press F9" not in dash)
chk("Home: graph overlay switch at the top", 'backend.setHudSetting(0, "hud_on", v)' in dash)
chk("Home: 'Right now' box with game, frame rate, session", 'Tr.t("Right now")' in dash and "page.now.game" in dash
    and "page.now.last" in dash)
chk("Home chart uses the smooth chart with both spans", "GraphChart {" in read("lmonitor", "qt", "qml", "components", "PerfChart.qml")
    and "backend.graphs(spans[backend.rangeIndex])" in dash)


class FakeFps:
    alive = True
    def current(self): return (42, "game.exe")
    def snapshot(self, g): return (143.6, 140.2, 101.4, 7.0, None)


class FakeSess:
    def status(self): return ("Recording game.exe", True)


class FakeStore:
    def list(self):
        return [{"id": 2, "game": "live.exe", "start": now, "duration": 10, "summary": {"live": True}},
                {"id": 1, "game": "old.exe", "start": now - 3600, "duration": 600, "summary": {"avg_fps": 88.4}}]


b.fps, b.sessions, b.session_store = FakeFps(), FakeSess(), FakeStore()
nb = b.now_box()
chk("right now: the game and its frame rate", nb["game"] == {"name": "game.exe", "fps": 144, "avg": 140, "low": 101})
chk("right now: recording state", nb["recording"] is True and nb["session"] == "Recording game.exe")
chk("right now: the last finished session (not the running one)", nb["last"]["game"] == "old.exe" and nb["last"]["avg_fps"] == 88.4)
FakeFps.alive = False
chk("no capture: no game, never a made-up number", b.now_box()["game"] is None)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
