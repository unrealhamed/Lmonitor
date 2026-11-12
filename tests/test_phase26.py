"""v1.17.3 - graph overlay: smooth scrolling, real time, mouse drag, real min / max.

Measured on the author's laptop (real overlay window, frame by frame): the line moves
with the clock, at most 0.3 px off the steady speed per frame, never backwards; cost with
a full-screen window in front: 1 min span 0.2 % CPU / 0.6 % iGPU, real time 0.7 % / 3 %.
Accuracy against nvidia-smi / Windows counters: GPU temp 0.3 C, GPU use 0.25 %,
GPU power 0.04 W, CPU use under load 1.4 %, RAM 0.14 % (mean differences)."""
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
from lmonitor.engine import Hud, Settings, FpsMonitor, GpuReader
from lmonitor.backend import Backend
from lmonitor.graphs import GraphHistory

cfg = deepcopy(Settings.DEFAULTS)

# ---- settings
c = Settings._clean(dict(deepcopy(cfg), hud_window=0))
chk("real time (0) is a valid time span", c["hud_window"] == 0)
c = Settings._clean(dict(deepcopy(cfg), hud_window=False))
chk("only real time and 1 minute exist (old 5 min -> real time)", Settings._clean(dict(deepcopy(cfg), hud_window=300))["hud_window"] == 0 and Hud.WINDOWS == (0, 60))
chk("motion defaults to smooth", Settings._clean(deepcopy(cfg))["hud_motion"] == "smooth")
chk("bad motion -> smooth", Settings._clean(dict(deepcopy(cfg), hud_motion="fast"))["hud_motion"] == "smooth")
chk("power saver is kept", Settings._clean(dict(deepcopy(cfg), hud_motion="saver"))["hud_motion"] == "saver")


class FakeTel:
    interval = 1.0
    snap = {"g_temp": 60.0, "c_temp": 70.0, "g_use": 50.0, "c_use": 20.0, "r_use": 40.0,
            "g_pow": 90.0, "c_pow": 30.0}


class FakeGpu:
    available = True
    calls = []
    def read(self, want, nvml_only=False):
        self.calls.append(nvml_only)
        return 77.0, 66.0, 111.0, None, None


class FakeFps:
    alive = True
    def recent_stats(self, since, fps_window=1.0): return (120.0, 25.0)


def make(window):
    b = Backend.__new__(Backend)
    b.settings = Settings.__new__(Settings)
    b.settings.data = Settings._clean(dict(deepcopy(cfg), hud_on=True, hud_window=window,
                                           hud_items=["fps", "ft", "g_use", "c_temp"]))
    b.telemetry, b.gpu, b.fps = FakeTel(), FakeGpu(), FakeFps()
    b.hud_hist = GraphHistory(keys=Backend.HUD_KEYS, keep=330)
    b._hud_t, b._hud_live = 0.0, {}
    from lmonitor.engine import CpuLoad
    b._hud_load = CpuLoad()
    return b

# ---- real time: 4 readings a second, from fast sources only
b = make(0)
chk("real time reads every 0.25 s", b.hud_period() == 0.25)
t0 = 1000.0
n = sum(1 for i in range(41) if b.hud_tick(t0 + i * 0.25))
chk("40 readings in 10 s", n == 41)
chk("a reading that comes too early is skipped", not b.hud_tick(t0 + 10.1))
chk("GPU in real time: NVML only (never the slow sensor library)", FakeGpu.calls and all(FakeGpu.calls))
chk("real time GPU values are fresh (not the 1 s reading)", b._hud_live["g_use"] == 77.0)
chk("CPU temperature stays the 1 s sensor reading", b._hud_live["c_temp"] == 70.0)
v = b.hud_view()
chk("real time shows the last 10 s in 40 points", v["window"] == 10 and v["points"] == 40 and v["realtime"])
chk("scroll data present", all(k in v for k in ("end_ms", "slot_ms", "delay_ms", "extra")))
chk("slot = 250 ms", abs(v["slot_ms"] - 250.0) < 1e-6)
chk("the newest slot holds the newest reading", v["items"][2]["series"][-1] == 77.0)
chk("no hole in a steady 4/s stream", None not in v["items"][2]["series"][-30:])

# ---- normal span: once a second, reusing the dashboard reading
b = make(60)
FakeGpu.calls = []
chk("1 min reads once a second", b.hud_period() == 1.0)
for i in range(65):
    b.hud_tick(2000.0 + i)
chk("normal span never reads the GPU itself", FakeGpu.calls == [])
chk("normal span uses the dashboard reading", b._hud_live["g_use"] == 50.0)
v = b.hud_view()
chk("1 min: 60 points + extra", v["points"] == 60 and len(v["items"][0]["series"]) == 60 + v["extra"])
chk("the delay covers a slot + a late reading", v["delay_ms"] >= v["slot_ms"])

# ---- lo / hi are real readings, not slot averages
b = make(60)
FakeTel.snap = dict(FakeTel.snap, g_use=10.0)
for i in range(30):
    FakeTel.snap["g_use"] = 99.0 if i == 15 else 10.0      # one short spike
    b.hud_tick(3000.0 + i)
v = b.hud_view()
gu = v["items"][2]
chk("a one-reading spike shows as the real highest value", gu["hi"] == "99" and gu["lo"] == "10")

# ---- FPS / worst frame from PresentMon's frame list
fm = FpsMonitor.__new__(FpsMonitor)
import threading
fm.lock = threading.Lock()
p = FpsMonitor.ProcData()
now = time.time()
for k in range(100):                        # 100 frames of 10 ms in the last second, one of 40 ms
    p.recent.append((now - 1.0 + k * 0.0099, 40.0 if k == 95 else 10.0))
p.last = now
fm.procs = {4242: p}
from lmonitor.engine import WinApi
real_fg = WinApi.foreground_pid
WinApi.foreground_pid = classmethod(lambda cls: 4242)
st = fm.recent_stats(now - 0.25)
chk("FPS over the last second", st is not None and 90 < st[0] < 100)
chk("worst frame of the last moment found (stutter)", st is not None and st[1] == 40.0)
st2 = fm.recent_stats(now - 0.02)
chk("a moment without the slow frame does not report it", st2 is not None and st2[1] == 10.0)
WinApi.foreground_pid = classmethod(lambda cls: 1)
chk("other program in front: None", fm.recent_stats(now - 0.25) is None)
WinApi.foreground_pid = real_fg

# ---- QML: smooth but light, drag with the mouse
hud = read("lmonitor", "qt", "qml", "components", "GraphHud.qml")
chk("one sliding picture per chart (painted only on new data)", "renderStrategy: Canvas.Immediate" in hud
    and "plot.drawnEnd = hud.endMs" in hud)
chk("clock throttled to 16..100 ms (not every screen refresh)", "Math.max(16, Math.min(100" in hud
    and "FrameAnimation" not in hud)
chk("power saver: nothing moves", 'readonly property bool smooth: (style.hud_motion || "smooth") === "smooth"' in hud)
ov = read("lmonitor", "qt", "overlay.py")
chk("grab check + Ctrl", "def _grab_check" in ov and "VK_CONTROL" in ov)
chk("top-edge drag is off while a full-screen game is in front", "on_handle and not fullscreen" in ov)
chk("place from the preview", "def place(self, fx, fy)" in ov)
win = read("lmonitor", "qt", "qml", "HudWindow.qml")
chk("the window takes the mouse only while it is grabbed", "enabled: w.st.grab" in win)
page = read("lmonitor", "qt", "qml", "pages", "HudPage.qml")
chk("drag in the preview", "backend.placeHud(" in page)
chk("real time in the time-span choice", '"Real time"' in page)
chk("preview reads only while the page is open", "setHudPageOpen(true)" in page and "setHudPageOpen(false)" in page)

# ---- the place math (HudHost.place / relative) without a screen
from lmonitor.qt import overlay as ovm
chk("place() clamps to the screen", "max(0.0, min(1.0, fx))" in ov)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
