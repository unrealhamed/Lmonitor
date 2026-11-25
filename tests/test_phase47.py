"""v1.21.3 - Lmonitor no longer makes games stutter now and then.

Measured on the author's PC (268 programs running): the game-session recorder looked at every
program with psutil every 10 s - ~700 ms of CPU each time, at Lmonitor's above-normal
priority, holding up the overlay thread too. Now one Windows call (process_usage) gives all
programs in ~5 ms, every 20 s. Also: while a game runs the CPU sensors (which make the sensor
library visit every CPU core) are read every 2 s instead of every second, and the overlays are
put on top again only when another window really is above them (before: every 5 s)."""
import os as _os, sys, time, subprocess
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
t0 = time.perf_counter()
u = E.process_usage()
ms = (time.perf_counter() - t0) * 1000
me = u.get(_os.getpid())
chk("all programs in one call (%.1f ms, %d programs)" % (ms, len(u)), len(u) > 20 and ms < 150)
chk("this program found with its name and memory", me is not None and me[0].lower().startswith("python") and me[2] > 10 * 2 ** 20)
busy = subprocess.Popen(["powershell.exe", "-NoProfile", "-Command",       # python.exe is skipped by the scan
                         "$t=[DateTime]::Now; while(([DateTime]::Now-$t).TotalSeconds -lt 5){}"])
time.sleep(1.0)
rec = E.SessionRecorder(None, None, None, None)
cur = {"pid": -1, "n": 2, "apps": {}, "scans": 0}
rec._scan_apps(cur)
time.sleep(1.5)
c0 = time.process_time()
rec._scan_apps(cur)
cost = (time.process_time() - c0) * 1000
busy.wait()
ncpu = __import__("psutil").cpu_count() or 1
py = cur["apps"].get("powershell.exe")
chk("a busy program is seen as busy (about one core: %.1f %% of the PC)" % (py[0] if py else -1),
    py is not None and py[0] >= 50.0 / ncpu)
chk("the scan is light (%.0f ms of CPU, was ~700)" % cost, cost < 100)
chk("scan every 20 s during a game (was 10)", E.SessionRecorder.SCAN_EVERY * E.SessionRecorder.STEP == 20)
chk("Windows' own memory processes are skipped", "memory compression" in E.SessionRecorder.SKIP_APPS)
chk("CPU sensors every 2 s while a game runs", E.CpuReader.GAME_PERIOD == 2.0
    and "self.cpu._bg.period = CpuReader.GAME_PERIOD if game_fps is not None else 1.0" in read("lmonitor", "backend.py"))
ov = read("lmonitor", "qt", "overlay.py")
chk("overlays put on top again only when covered", ov.count("if WinApi.covered(h):") == 2)
chk("covered() answers without error", E.WinApi.covered(0) in (True, False))
chk("version 1.21.3 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 21, 3))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
