"""v1.20.2 - "Start with Windows" no longer gets lost.

The user had the option on, but Windows' task was gone (an uninstall removes it; it was not
there at all on their PC), so Lmonitor did not start. Now the choice is kept in Lmonitor's
own settings (autostart_on) and the installed program makes the task again at its next start
when it is missing or points to another Lmonitor.exe. A copy run from source never touches it."""
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
A, W = E.Autostart, E.WinApi
EXE = r"D:\App\Lmonitor\Lmonitor.exe"
state = {"task": None}          # None = no task, else the exe it starts
calls = []

def fake(*a):
    calls.append(a)
    if a[0] == "/Query":
        if state["task"] is None:
            return 1, "ERROR: The system cannot find the file specified."
        return 0, ("<Command>%s</Command>" % state["task"]) if "/XML" in a else "Lmonitor  Ready"
    if a[0] == "/Create":
        state["task"] = EXE
        return 0, "SUCCESS"
    if a[0] == "/Delete":
        state["task"] = None
        return 0, "SUCCESS"
    return 1, "?"

real = (A._schtasks, A.command, W.is_admin, getattr(sys, "frozen", None))
A._schtasks = staticmethod(fake)
A.command = staticmethod(lambda: (EXE, "--startup"))
W.is_admin = staticmethod(lambda: True)
sys.frozen = True
try:
    on, err = A.repair(True)
    chk("wanted but the task is gone: made again", on and err == "" and any(c[0] == "/Create" for c in calls))
    calls.clear()
    on, err = A.repair(True)
    chk("task there and right: nothing changed", on and not any(c[0] == "/Create" for c in calls))
    state["task"] = r"C:\Old place\Lmonitor.exe"
    on, err = A.repair(True)
    chk("task starts another Lmonitor.exe: made again for this one", on and state["task"] == EXE)
    state["task"] = None; calls.clear()
    on, err = A.repair(False)
    chk("not wanted: never created", not on and not any(c[0] == "/Create" for c in calls))
    W.is_admin = staticmethod(lambda: False)
    on, err = A.repair(True)
    chk("without admin rights: not tried (no error box at each start)", not on and err == "")
    W.is_admin = staticmethod(lambda: True)
    del sys.frozen
    on, err = A.repair(True)
    chk("a copy run from source never takes the task", not on and state["task"] is None)
finally:
    A._schtasks, A.command, W.is_admin = staticmethod(real[0]), real[1], staticmethod(real[2])
    if real[3] is not None:
        sys.frozen = real[3]
    elif hasattr(sys, "frozen"):
        del sys.frozen

s = E.Settings()
chk("the choice is a setting (unknown at first)", s["autostart_on"] is None)
s.data["autostart_on"] = "yes"
chk("only on / off / unknown are kept", E.Settings._clean(s.data)["autostart_on"] is None)
br = read("lmonitor", "qt", "bridge.py")
chk("switching remembers the choice", 'self._b.settings["autostart_on"] = bool(on)' in br)
chk("at start: repaired when chosen", "state, err = Autostart.repair(True)" in br)
chk("older versions: an existing task counts as 'chosen'", 'st["autostart_on"] is None and state' in br)
chk("version 1.20.2 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 20, 2))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
