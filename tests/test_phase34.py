"""v1.18.1 - two bugs from the author's videos.

1. Graph overlay over a game at a steady 143 FPS: "Frame time" kept switching to "--",
   its line had holes, and FPS showed "--" for a moment. PresentMon gets its frames from
   Windows' event tracing in batches (about once a second); Lmonitor stamped each frame
   with the time its line arrived, so a quarter second between two batches had no frames.
   Now every frame has its own time (previous frame + its frame time) and the numbers are
   measured up to where all frames have arrived.
2. Graphs page: after another page was open for a few seconds, the real-time charts came
   back with a hole (nothing filled the real-time history while no real-time chart or
   graph overlay was on). The once-a-second reading now fills it."""
import os as _os, sys, time, threading
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, _os.path.join(ROOT, "tests", "stubs"))

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

import lmonitor.engine as E

# ---- a fake clock for the engine (everything else of `time` stays real)
class Clock:
    def __init__(self, t): self.t = t
    def time(self): return self.t
    def __getattr__(self, n): return getattr(time, n)
real_time = E.time
clk = Clock(1_000_000.0)
E.time = clk
real_fg = E.WinApi.foreground_pid
E.WinApi.foreground_pid = classmethod(lambda cls: 4242)
try:
    fm = E.FpsMonitor()
    HEAD = "Application,ProcessID,SwapChainAddress,Runtime,SyncInterval,PresentFlags,MsBetweenPresents\n"

    class Proc:
        def __init__(self, lines): self.stdout = [HEAD] + lines

    T0, FT = clk.t, 1000.0 / 143
    frames = [T0 + k * FT / 1000.0 for k in range(1, int(12 * 143))]
    sent, prev_tick, bad_ticks, ticks, fps_seen = 0, None, 0, 0, []
    t = T0
    next_batch = T0 + 1.05
    while t < T0 + 11.5:
        t += 0.25
        clk.t = t
        if t >= next_batch:                       # one batch: every frame up to 50 ms ago
            batch = []
            while sent < len(frames) and frames[sent] <= next_batch - 0.05:
                batch.append("game.exe,4242,0x1,DXGI,0,0,%.3f\n" % FT)
                sent += 1
            p = Proc(batch); fm.proc = p
            fm._reader(p)
            next_batch += 1.0
        if t > T0 + 3.0:                          # after the first batches
            st = fm.recent_stats(prev_tick if prev_tick else t - 0.25)
            ticks += 1
            if st is None or st[1] is None:
                bad_ticks += 1
            else:
                fps_seen.append(st[0])
        prev_tick = t
    chk("batched frames: FPS and frame time every quarter second (%d of %d ticks empty)"
        % (bad_ticks, ticks), ticks > 30 and bad_ticks == 0)
    chk("FPS stays at the real 143 (%.1f..%.1f)" % (min(fps_seen), max(fps_seen)),
        fps_seen and all(140 <= f <= 146 for f in fps_seen))
    snap = fm.snapshot(False)
    chk("overlay bar FPS from the same clock", snap is not None and 140 <= snap[0] <= 146)
    chk("delay found from the batches (%.2f s)" % fm.lag(), 0.9 <= fm.lag() <= 1.2)

    # a stutter is still found: one 40 ms frame inside a batch
    fm2 = E.FpsMonitor()
    clk.t = T0 + 100.0
    lines = ["game.exe,4242,0x1,DXGI,0,0,%.3f\n" % (40.0 if k == 70 else FT) for k in range(143)]
    p = Proc(lines); fm2.proc = p; fm2._reader(p)
    worst = []
    for k in range(1, 9):
        clk.t = T0 + 100.0 + k * 0.25
        st = fm2.recent_stats(clk.t - 0.25)
        worst.append(st[1] if st else None)
    chk("one slow frame inside a batch still shows as the worst frame", 40.0 in worst)
finally:
    E.time = real_time
    E.WinApi.foreground_pid = real_fg

# ---- 2. real-time charts keep a line while another page is open
from lmonitor.backend import Backend
b = Backend()
b.graph_fast = False
for k in ("hud_on", "hud2_on"):
    b.settings.data[k] = False
n0 = len(b.hud_hist.data)
for _ in range(3):
    b._hud_t -= 2                                # as if a second went by
    b.sample()
chk("once-a-second readings fill the real-time history", len(b.hud_hist.data) - n0 >= 3)
src = open(_os.path.join(ROOT, "lmonitor", "backend.py"), encoding="utf-8").read()
chk("a slower Refresh (2 s) still joins the real-time line", "self.telemetry.interval * 1.6" in src)
chk("version 1.18.1 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 18, 1))

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
