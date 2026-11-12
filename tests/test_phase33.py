"""v1.18.0 - whole-program check: bugs found and lighter work.

1. The Hardware page asked for the extra sensors on the window's thread every second and
   waited for the sensor lock each time (a CPU sensor update holds it ~0.5 s under full
   load). Now only the first call takes the lock.
2. error.log showed "'MethodObject' object is not callable" from the CPU sensor thread:
   a reader thread still used the sensor library while Python shut down. At exit the
   readers now stop and the library is closed under its lock.
3. "Start with Windows" asked Task Scheduler (schtasks, 0.1-0.5 s) on the window's thread.
4. The bar and both graph overlays checked the keyboard 25x a second even when off.
5. The window's colors were rebuilt in Python ~30 times per settings change.
6. Rows of the Home page / chips of the Graphs page were deleted and built again on every
   reading.
7. The real-time graph overlay redrew 60x a second; half-pixel steps give 45.
8. Dead code removed (old report class with a missing helper, 24-hour recorder that
   nothing showed, old window constants, a second copy of the network table code)."""
import os as _os, sys, threading, time
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
eng, back = read("lmonitor", "engine.py"), read("lmonitor", "backend.py")
bridge, ovl = read("lmonitor", "qt", "bridge.py"), read("lmonitor", "qt", "overlay.py")
qml = lambda *p: read("lmonitor", "qt", "qml", *p)

chk("version 1.18.0", E.AppInfo.VERSION == "1.18.0")

# ---- 1. extra sensors: no lock after the first time
h = E.LibreHardwareHost.__new__(E.LibreHardwareHost)
h._extras_on, h.computer, h.suspended = True, object(), False
got = []
def hold():
    with E.HW_LOCK:
        got.append(1); time.sleep(0.6)
t = threading.Thread(target=hold); t.start()
while not got: time.sleep(0.01)
t0 = time.perf_counter(); h.enable_extras(); dt = time.perf_counter() - t0
t.join()
chk("Hardware page does not wait for a sensor update (%.0f ms)" % (dt * 1000), dt < 0.05)

# ---- 2. clean exit
chk("readers can be stopped for good", hasattr(E.BackgroundReader, "stopped")
    and "while not BackgroundReader.stopped:" in eng)
r = E.BackgroundReader(lambda: calls.append(1), 0.1, "t")
calls = []
E.BackgroundReader.stopped = True
try:
    r.poke(); time.sleep(0.15)
    chk("a stopped reader neither reads nor starts a thread", not calls and r._thread is None)
finally:
    E.BackgroundReader.stopped = False
chk("exit stops the readers, then closes the sensor library", "BackgroundReader.stopped = True" in back
    and "self.host.suspend()" in back.split("def close(self):")[1])

# ---- 3. start with Windows off the window's thread
chk("Task Scheduler is asked on a worker thread", "_autostart_job" in bridge
    and "Autostart.is_on()" not in bridge.split("def autostart(self):")[1].split("@Property")[0])

# ---- 4. keyboard checks only while an overlay is on
chk("overlay timers run only while switched on", ovl.count("def _sync_poll(self):") == 2
    and "self.poll.start()\n        self.apply()" not in ovl)

# ---- 5. window colors cached
chk("window colors built once per settings change", "self._ui_cache = self._b.ui_style()" in bridge)

# ---- 6. rows kept
dash, graphs = qml("pages", "Dashboard.qml"), qml("pages", "GraphsPage.qml")
chk("Home rows are not rebuilt every second", "model: 4" in dash and "model: 5" in dash
    and "model: [" not in dash)
chk("Graphs chips are not rebuilt 4x a second", "fanKey" in graphs)

# ---- 7. lighter animation
chk("graph overlay: half-pixel steps", "Math.round(0.5 / pxPerMs)" in qml("components", "GraphHud.qml"))
chk("hidden graph overlay: clock stops", "animate: w.visible" in qml("HudWindow.qml"))
chk("high-refresh screens: at most ~70 chart steps a second", ">= 14" in qml("Lmonitor", "Clock.qml"))

# ---- 8. dead code
for name in ("Diagnostics", "Recorder", "Monitor"):
    chk("removed: " + name, not hasattr(E, name))
chk("removed: second network table reader", "_virtual_names" not in eng)
chk("removed: old Tk window constants", "SIDE_W" not in eng and "F_SMALL" not in eng)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
