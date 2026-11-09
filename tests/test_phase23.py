import os as _os, sys, re
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

QML = _os.path.join(ROOT, "lmonitor", "qt", "qml")
def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

from lmonitor.graphs import GraphHistory

SNAP = lambda v: {"c_temp": v, "g_temp": v, "c_use": v, "g_use": v}

# ---- bug: the 1 minute view had holes. Readings came about every 1.07 s, one slot is
# exactly 1 s, so about every 15 s a slot stayed empty and the line broke.
h = GraphHistory()
t = 1000.0
while t < 1120.0:
    h.add(SNAP(40.0), None, now=t)
    t += 1.07
s = h.series(60, 60, h.latest())
chk("uneven readings leave no hole in the 1 minute view", None not in s["c_temp"])

# a hole is joined with a straight line
h = GraphHistory()
h.add(SNAP(10.0), None, now=100.5)
h.add(SNAP(40.0), None, now=103.5)
s = h.series(60, 60, 103.5)
chk("short hole is joined in a straight line", s["c_temp"][-4:] == [10.0, 20.0, 30.0, 40.0])

# a real stop stays visible
h = GraphHistory()
h.add(SNAP(10.0), None, now=100.5)
h.add(SNAP(40.0), None, now=120.5)
s = h.series(60, 60, 120.5)
chk("a long hole stays empty (never made up)", s["c_temp"][-2] is None and s["c_temp"][-1] == 40.0)
s = h.series(60, 60, 120.5, max_gap=30)
chk("the hole limit can follow a slow refresh setting", s["c_temp"][-2] is not None)
chk("a value before the first reading stays empty", s["c_temp"][0] is None)

# ---- bug: on 5 / 10 minutes every reading moved all slot edges, so the whole line changed shape
h = GraphHistory()
t = 5000.0
v = 0
while t < 5296.0:
    h.add(SNAP(float(v % 37)), None, now=t)
    t += 1.0
    v += 7
a = h.series(300, 60, 5295.5)
for i in range(1, 5):
    h.add(SNAP(99.0), None, now=5295.0 + i)
b = h.series(300, 60, 5299.0)
chk("5 min: finished slots do not change while time moves on", a["c_temp"][:-1] == b["c_temp"][:-1])
chk("5 min: only the running slot changes", a["c_temp"][-1] != b["c_temp"][-1])
chk("5 min: the chart moves on a slot edge", a["end_ms"] == b["end_ms"] == 5300000.0)
h.add(SNAP(99.0), None, now=5301.0)
c = h.series(300, 60, 5301.0)
chk("next slot: the picture shifts by exactly one slot", c["end_ms"] == b["end_ms"] + 5000.0 and c["c_temp"][:58] == b["c_temp"][1:59])
chk("the last slot holds the newest reading", c["c_temp"][-1] == 99.0)
chk("latest reading time", h.latest() == 5301.0 and GraphHistory().latest() is None)

# a hole just inside the left edge is joined from the reading outside the window
h = GraphHistory()
h.add(SNAP(10.0), None, now=938.5)
h.add(SNAP(40.0), None, now=941.5)
h.add(SNAP(40.0), None, now=999.5)
s = h.series(60, 60, 999.5)
chk("left edge: no blank slot from a chance hole", s["c_temp"][0] == 30.0)
chk("always exactly the asked number of points", len(s["c_temp"]) == 60)

# ---- steady sample rate and steady scroll
loop = re.search(r"def _loop\(self\):.*?def _overlay_loop", read("lmonitor", "qt", "bridge.py"), re.S).group(0)
chk("sample loop subtracts the time spent reading", "time.monotonic() - started" in loop)
chart = read("lmonitor", "qt", "qml", "components", "GraphChart.qml")
chk("scroll follows the clock", "root.nowMs - root.delayMs - root.drawnEnd" in chart)
chk("picture and offset change in the same frame", "Canvas.Immediate" in chart and "root.drawnEnd = root.scrollEnd" in chart)
page = read("lmonitor", "qt", "qml", "pages", "GraphsPage.qml")
chk("every Graphs chart uses the scrolling chart", page.count("GraphChart {") == 3 and page.count("delayMs: page.d.delay_ms") == 3)
chk("the clock is updated once per displayed frame", "FrameAnimation" in read("lmonitor", "qt", "qml", "Lmonitor", "Clock.qml"))

# ---- new points are outside the chart before they scroll in
for d in (_os.path.join(ROOT, "tests", "stubs"),):
    if _os.path.isdir(d): sys.path.insert(0, d)
sys.modules["tkinter"] = None
import time
from lmonitor.backend import Backend
back = Backend()
back.telemetry.interval = 1.0
for i in range(30):
    back.graphs.add(SNAP(50.0), None, now=time.time() - 30 + i)
for sec, wid in ((60, 1.0), (300, 5.0), (600, 10.0)):
    s = back.graph_series(sec)
    chk("%d s: visible + hidden points" % sec, len(s["c_temp"]) == 60 + s["extra"])
    chk("%d s: newest point never reaches the edge before the next arrives" % sec,
        s["delay_ms"] == (wid + 1.2) * 1000.0 and s["extra"] >= 2 + 1.2 / wid)
back.telemetry.interval = 5.0
s = back.graph_series(60)
chk("slow refresh setting keeps more points outside", s["extra"] >= 2 + 6.0 and s["delay_ms"] == 7000.0)

# ---- large view with several lines on one chart
chk("clicking a chart opens the large view", page.count("page.open(") == 2)
chk("names add and remove lines", "page.toggle(modelData.key)" in page)
chk("the last line cannot be removed", "k.length > 1" in page)
chk("Esc and the close button leave the large view", "Keys.onEscapePressed: page.close()" in page and "onClicked: page.close()" in page)
chk("fans get their own scale next to % and temperature", "page.maxOf(page.mainKind) / page.maxOf(k)" in page and "page.maxOf(page.sideKind)" in page)
chk("large chart draws every chosen line", "series: page.openSeries" in page)

# ---- accuracy: a VPN's traffic also passes the real adapter, so it must not be added
from lmonitor.engine import NetworkReader, Settings, Paths
n = NetworkReader()
n.speeds = {"Ethernet": (100.0, 10.0), "VPN": (90.0, 9.0), "Wi-Fi": (5.0, 1.0)}
n.info = {"Ethernet": (True, 1000), "VPN": (True, 1000), "Wi-Fi": (False, 0)}
n.virtual = {"VPN"}
chk("VPN traffic is not counted twice", n.total() == (100.0, 10.0))
n.info = {"Ethernet": (False, 0), "VPN": (True, 1000), "Wi-Fi": (False, 0)}
chk("only a virtual adapter is up: it still counts", n.total() == (90.0, 9.0))
n.virtual = set()
n.info = {"Ethernet": (True, 1000), "VPN": (False, 0), "Wi-Fi": (False, 0)}
chk("no adapter list: normal sum", n.total() == (100.0, 10.0))

# ---- charts keep the point that is sliding out
back.telemetry.interval = 1.0
for k in ("c_use", "r_use", "g_use"):
    back.telemetry.history[k].clear()
    back.telemetry.history[k].extend(float(i) for i in range(100))
chk("big chart: more points than shown, so the left edge never jumps", all(len(x) == 62 for x in back.perf(0)))

# ---- language
import json
chk("language is known", Settings.DEFAULTS["language"] == "en")
_os.makedirs(_os.path.dirname(Paths.CFG_FILE), exist_ok=True)
keep = open(Paths.CFG_FILE, encoding="utf-8").read() if _os.path.exists(Paths.CFG_FILE) else None
json.dump({"language": "fa"}, open(Paths.CFG_FILE, "w", encoding="utf-8"))
chk("the chosen language survives a restart", Settings()["language"] == "fa")
json.dump({"language": "xx"}, open(Paths.CFG_FILE, "w", encoding="utf-8"))
chk("an unknown language falls back to English", Settings()["language"] == "en")
if keep is not None:
    open(Paths.CFG_FILE, "w", encoding="utf-8").write(keep)
else:
    _os.remove(Paths.CFG_FILE)
fa = read("lmonitor", "qt", "qml", "Lmonitor", "fa.js")
chk("Persian text exists for the main pages", all('"%s":' % k in fa for k in ("Home", "Graphs", "Hardware", "Diagnostics", "Optimizer")))
print("phase23: %d ok, %d failed" % (ok, bad))
