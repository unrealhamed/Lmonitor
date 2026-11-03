import os as _os
import sys, os, ctypes, json, shutil, time, tracemalloc, threading
from unittest.mock import MagicMock
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "stubs"))
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import imagetk_stub, PIL
sys.modules["PIL.ImageTk"] = imagetk_stub; PIL.ImageTk = imagetk_stub
import tkinter as tk
import psutil
OUT = _os.path.join(__import__("tempfile").gettempdir(), "lmonitor_test_prev")
APPD = _os.path.join(__import__("tempfile").gettempdir(), "lmonitor_test_appdata")
D1, D2 = "\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"

def load(keep_cfg=False):
    for k in [k for k in sys.modules if k in ("monitor_oop", "pynvml") or k == "lmonitor" or k.startswith("lmonitor.")]: del sys.modules[k]
    ctypes.windll = MagicMock(); ctypes.windll.shell32.IsUserAnAdmin.return_value = 1
    ctypes.windll.kernel32.GetLastError.return_value = 0
    st = {"ex": 0}
    ctypes.windll.user32.GetWindowLongW.side_effect = lambda h, i: st["ex"]
    def setl(h, i, v): st["ex"] = v
    ctypes.windll.user32.SetWindowLongW.side_effect = setl
    ctypes.windll.user32.SetWindowCompositionAttribute.return_value = 1
    if not keep_cfg: shutil.rmtree(APPD, ignore_errors=True)
    os.environ["APPDATA"] = APPD; os.environ.pop("NVFAIL", None); sys.argv = ["monitor.py"]
    import importlib.util
    spec = importlib.util.spec_from_file_location("monitor_oop", _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "monitor.py"))
    m = importlib.util.module_from_spec(spec); sys.modules["monitor_oop"] = m; spec.loader.exec_module(m)
    m.WinApi.blur_supported = staticmethod(lambda: True)
    m.SYS = {"mons": [m.Monitor(D1, 1, 0, 0, 1920, 1080, True, 1920, 1080, 60),
                      m.Monitor(D2, 2, 1920, 0, 2560, 1440, False, 2560, 1440, 144)]}
    m.DisplayManager._enumerate = lambda self: list(m.SYS["mons"])
    return m

def flush():
    for _ in range(300):
        if not tk.AFTERS: return
        for t in list(tk.AFTERS):
            if t in tk.AFTERS:
                tk.AFTERS.remove(t)
                if t[2]: t[2](*t[3])

def boot(m):
    m.WinApi.setup(); m.WinApi.ensure_admin(); app = m.App(); app.window.draw(); app.rebuild(); flush(); return app



def press(w, lst, i, part="button"):
    """Click row i of an ActionList the way the mouse does (through the canvas)."""
    ry = lst.y + lst.TOP + i * lst.ROW_H
    if part == "button":
        w.canvas.click(lst.x + lst.w - 24 - lst.BTN_W / 2, ry + 22)
    elif part == "check":
        w.canvas.click(lst.x + 30, ry + 22)
    else:                                   # the row itself (title area)
        w.canvas.click(lst.x + 60, ry + 22)
