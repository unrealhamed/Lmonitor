"""v1.19.1 - less RAM while Lmonitor sits in the tray.

Measured before: ~160 MB in Task Manager after the window was open once and closed again
(graphics driver, Qt, sensor library keep it). Now, 4 s after the window is closed or
minimized (and 20 s after a start at sign-in), Lmonitor gives the RAM it does not use back
to Windows (EmptyWorkingSet); every 5 min again if it grew above 60 MB. Measured after:
~17 MB (overlays off) / ~30 MB (overlay bar on)."""
import os as _os, sys
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
W = E.WinApi
junk = [bytearray(1024 * 1024) for _ in range(40)]       # 40 MB touched
for b in junk:
    b[::4096] = b"\x01" * len(b[::4096])
before = W.memory_mb()
chk("memory can be read (%.0f MB)" % (before or -1), before and before > 30)
chk("trim works", W.trim_memory() is True)
after = W.memory_mb()
chk("working set went down (%.0f -> %.0f MB)" % (before, after), after < before * 0.5)
chk("the data is still there", all(b[0] == 1 for b in junk))

br = read("lmonitor", "qt", "bridge.py")
chk("trimmed after the window is closed / minimized", "self._trim_once.start()" in br and "TRIM_AFTER_MS = 4000" in br)
chk("not while the window is open", "if self._ui_visible:\n            return" in br and "self._trim_once.stop()" in br)
chk("again now and then only if it grew", "TRIM_EVERY_MS = 5 * 60 * 1000" in br and "TRIM_ABOVE_MB = 60" in br)
chk("start at sign-in (tray only) is trimmed too", "QTimer.singleShot(20000, self._trim)" in br)
chk("version 1.19.1 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 19, 1))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
