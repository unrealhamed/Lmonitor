import os as _os, sys, re
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

QML = _os.path.join(ROOT, "lmonitor", "qt", "qml")
def read(*p): return open(_os.path.join(QML, *p), encoding="utf-8").read()

# ---- bug: clicking another app stops the shared Clock, its `now` becomes older than the
# chart's start time and the slide offset goes negative (the graph jumps backwards).
# The expression is taken from LiveCanvas.qml itself and run with Qt's JS engine.
m = re.search(r"readonly property real progress:(.*?)\n    Canvas \{", read("components", "LiveCanvas.qml"), re.S)
expr = m.group(1).strip() if m else "0"
from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine
_qt = QCoreApplication.instance() or QCoreApplication([])
def progress(now, t0, interval=1000):
    v = QJSEngine().evaluate("const slide=true,t0=%d,interval=%d,Clock={now:%d};(%s)" % (t0, interval, now, expr))
    return None if v.isError() else v.toNumber()
chk("slide offset is 0 when the clock is older than the picture (app not in front)", progress(1000, 5000) == 0)
chk("slide offset stays between 0 and 1", all(0 <= progress(5000 + d, 5000) <= 1 for d in (-9000, -1, 0, 400, 5000)))
chk("normal slide still works", abs(progress(5500, 5000) - 500 / 1000) < 1e-9)
chk("clock keeps running while another app has focus",
    "ApplicationActive" not in re.search(r'Binding \{ target: Clock.*', read("Main.qml")).group(0))


chk("Graphs page does not use the once-per-second slide", "AreaChart" not in read("pages", "GraphsPage.qml"))

# ---- Graphs history
from lmonitor.graphs import GraphHistory
g = GraphHistory()
for t in range(10):
    g.add({"c_temp": 40 + t, "g_temp": None, "c_use": 10, "g_use": 5}, {"CPU Fan": 3000 + t}, now=float(t))
s = g.series(10, points=5, now=10.0)
chk("buckets are averaged", s["c_temp"] == [40.5, 42.5, 44.5, 46.5, 48.5])
chk("no reading stays None (never a made-up 0)", s["g_temp"] == [None] * 5)
chk("fan RPM per fan name", s["fans"]["CPU Fan"][0] == 3000.5 and len(s["fans"]["CPU Fan"]) == 5)
h = GraphHistory()
h.add({"c_temp": 50}, None, now=0.0)
h.add({"c_temp": 60}, None, now=100.0)
s = h.series(60, points=3, now=101.0)
chk("a gap shows as None", s["c_temp"][0] is None and s["c_temp"][-1] == 60)
chk("no fans -> empty", s["fans"] == {})
h.add({"c_temp": 1}, None, now=701.0)
chk("history older than 10 minutes is dropped", len(h.data) == 1)
chk("empty history gives empty lists", GraphHistory().series(60, points=4, now=1.0)["c_use"] == [None] * 4)

# ---- Backend wiring: fan speeds are read only while the Graphs page is open
for d in (_os.path.join(ROOT, "tests", "stubs"), "/home/claude/stubs"):
    if _os.path.isdir(d): sys.path.insert(0, d)
sys.modules["tkinter"] = None
from lmonitor.backend import Backend
b = Backend()
calls = []
b.telemetry.sample = lambda: None
b.telemetry.snap = {"c_temp": 50, "g_temp": 60, "c_use": 10, "g_use": 20}
def fake_read():
    calls.append(1)
    return [("SuperIO", "x", "Fan", "CPU Fan", 3100.0), ("SuperIO", "x", "Temperature", "T", 40)]
b.telemetry.sensors.read = fake_read
b.sample()
chk("Graphs closed: sensors are not read for fans", not calls and b.graph_series(60)["fans"] == {})
b.graph_fans = True
b.sample()
s = b.graph_series(60)
chk("Graphs open: fan RPM is recorded (fans only, no temperatures)", list(s["fans"]) == ["CPU Fan"] and 3100.0 in s["fans"]["CPU Fan"])
chk("temperatures and usage are recorded", 60.0 in s["g_temp"] and 10.0 in s["c_use"])
print("phase22: %d ok, %d failed" % (ok, bad))
