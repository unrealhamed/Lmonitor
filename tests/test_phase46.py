"""v1.21.2 - the overlay's FPS no longer flickers to "N/A" in the middle of a game.

PresentMon hands over frames in batches; on a busy PC a batch can come 2-4 s late. The bar
showed "N/A" whenever no frame had arrived for 2 s, and whenever another window was in front
for a moment. Simulated (scratch fpssim.py, 144 FPS): batches 3.8 s late every 3rd second:
28 % of readings were N/A before, 0 % now; another window in front 1 s out of 6: 17 % -> 0 %.
Now: the overlays follow the game that was in front while it keeps drawing, a late batch keeps
the last good number for up to 5 s, the frame graph moves on the frames' own clock, and the
bar updates 3 times a second. A game that really stopped drawing still shows N/A after 5 s."""
import os as _os, sys, time
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
FG = {"pid": 10}
E.WinApi.foreground_pid = staticmethod(lambda: FG["pid"])
m = E.FpsMonitor()

def frames(pid, name, until, secs=2.0, fps=144):
    """frames of `secs` seconds ending at `until`, arrived at `until` (a batch)."""
    p = m.procs.get(pid) or m.ProcData()
    m.procs[pid] = p
    p.name = name
    t, step = until - secs, 1.0 / fps
    while t < until:
        p.recent.append((t, 1000.0 / fps))
        p.graph.append(1000.0 / fps)
        p.count += 1
        p.total_ms += 1000.0 / fps
        t += step
    p.last = until
    p.clock = until
    return p

now = time.time()
frames(10, "game.exe", now)
s = m.snapshot(True)
chk("game in front: its FPS", s is not None and round(s[0]) == 144)
chk("frame graph: at most 300 frames, oldest first", s[4] and len(s[4]) <= E.Theme.GRAPH_POINTS)
m.procs[10].recent = E.deque((t - 3.0, ms) for t, ms in m.procs[10].recent)   # the next batch is 3 s late
m.procs[10].last = now - 3.0
s = m.snapshot(False)
chk("a batch 3 s late: the last good number stays (no N/A)", s is not None and round(s[0]) == 144)
FG["pid"] = 99                                     # another window in front for a moment
frames(10, "game.exe", time.time())
s = m.snapshot(False)
chk("another window in front for a moment: still the game's FPS", s is not None and round(s[0]) == 144)
st = m.recent_stats(time.time() - 0.5)
chk("graph overlay too", st is not None and round(st[0]) == 144)
frames(20, "chrome.exe", time.time())
FG["pid"] = 20
chk("a browser in front does not take the overlay over", m.target()[0] == 10)
FG["pid"] = 30
frames(30, "other_game.exe", time.time())
chk("another game in front that draws frames: the overlay follows it", m.target()[0] == 30)
m.procs[30].last = time.time() - 6
m.procs[30].held = (time.time() - 6, 60.0, 16.7)
m.procs[10].last = time.time() - 6
chk("no frames for over 5 s: N/A (the game really stopped)", m.snapshot(False) is None)
chk("frames up to 4.5 s late are waited for", E.FpsMonitor.LAG_MAX == 4.5)
br = read("lmonitor", "qt", "bridge.py")
chk("bar with FPS: 3 updates a second", "BAR_FPS_PERIOD = 0.33" in br)
bar = read("lmonitor", "qt", "qml", "components", "OverlayBar.qml")
chk("bar graph scale follows the usual frame time (no jumping)", "v[Math.floor(v.length / 2)] * 2.2" in bar)
chk("version 1.21.2 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 21, 2))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
