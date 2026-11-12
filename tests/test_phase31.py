"""v1.17.8 - everything froze while a benchmark (FurMark) or a game loaded the PC.

Measured on the author's laptop with every CPU thread busy: Windows' network calls went
from 6 to 700 ms, the CPU sensor update from 2 to 450 ms, psutil.cpu_times from 0 to
80 ms. They ran on the thread that feeds the overlays, so the overlay got new data only
every 1.5 s (longest pause 1.9 s) and drew 30 frames in 11 s. Now slow readings run on
their own threads; under the same load: data every 0.28 s, longest pause 0.6 s,
612 frames. The "background mode" (below-normal priority + efficiency cores) made it
worse and is gone."""
import os as _os, sys, time, threading
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

from lmonitor.engine import BackgroundReader, CpuLoad, WinApi

# ---- a slow reading never holds up the caller
calls = []
def slow():
    calls.append(time.monotonic())
    time.sleep(0.3)
r = BackgroundReader(slow, 0.5, "test")
t0 = time.monotonic(); r.poke(); first = time.monotonic() - t0
chk("the very first values are read right away (once)", r.runs == 1 and first >= 0.29)
t0 = time.monotonic()
for _ in range(20):
    r.poke()
chk("after that, asking never waits for the slow reading", time.monotonic() - t0 < 0.05)
time.sleep(1.4)
chk("it keeps reading in the background, about once per period", 2 <= r.runs <= 4)
r.IDLE = 0.5
time.sleep(1.5)
n = r.runs
time.sleep(0.8)
chk("nobody asks any more: the thread stops", r.runs == n and (r._thread is None or not r._thread.is_alive()))
r.poke()
time.sleep(0.9)
chk("asked again: it starts again", r.runs > n)
fast = BackgroundReader(lambda: None, 1.0, "fast")
fast.poke(0.25)
time.sleep(1.1)
chk("real-time charts make it read 4 times a second for a moment", fast.runs >= 4)
err = BackgroundReader(lambda: 1 / 0, 0.2, "err")
err.poke(); time.sleep(0.5)
chk("an error in a reading does not stop it", err.runs >= 2)

# ---- CPU usage: one cheap Windows call
c = CpuLoad()
t0 = time.perf_counter()
for _ in range(200):
    v = c.read()
chk("CPU usage reading is cheap (200 reads < 50 ms)", time.perf_counter() - t0 < 0.05)
chk("CPU usage is a percentage", 0.0 <= v <= 100.0)
end = time.time() + 0.6
def burn():
    while time.time() < end:
        pass
c.read()
ts = [threading.Thread(target=burn) for _ in range(2)]
[t.start() for t in ts]; [t.join() for t in ts]
chk("CPU usage rises under load", c.read() > 0.0)

# ---- wiring
eng = read("lmonitor", "engine.py")
chk("CPU sensors, GPU, network and board sensors use background readers",
    eng.count("BackgroundReader(") >= 4 and 'BackgroundReader(self._update, 1.0, "cpu sensors")' in eng
    and 'BackgroundReader(self._poll, 1.0, "gpu sensors")' in eng and 'BackgroundReader(self._read, 1.0, "network")' in eng)
chk("network: no psutil call (it keeps Python's lock: up to 4 s under FurMark)", "interface_table()" in eng
    and "psutil.net_io_counters" not in eng and "psutil.net_if_stats" not in eng)
chk("background mode is removed", getattr(WinApi, "set_background_mode", None) is None
    and "set_background_mode" not in read("lmonitor", "qt", "bridge.py"))
chk("the safe-mode program list is read on its own thread", 'BackgroundReader(self._safe_scan, 5.0' in read("lmonitor", "backend.py"))
chk("behind a game the readings go on (charts have no holes afterwards)",
    "busy = self._ui_visible or" in read("lmonitor", "qt", "bridge.py"))

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
