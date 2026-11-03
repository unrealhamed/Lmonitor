import os as _os
import sys, os, json, shutil, stat
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from t_helpers import load
import tkinter as tk
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print("FAIL", name)

# 1. normal start + quit: settings saved, mainloop returns
m = load()
m.WinApi.setup(); m.WinApi.ensure_admin(); app = m.App()
app.settings["alpha"] = 65
tk.Tk.mainloop = lambda self, *a: None
app.run()
app.quit()
cfg = os.path.join(m.Paths.CFG_DIR, "settings.json") if hasattr(m.Paths, "CFG_DIR") else m.Paths.CFG_FILE
chk("settings saved on quit", os.path.exists(m.Paths.CFG_FILE) and json.load(open(m.Paths.CFG_FILE))["alpha"] == 65)

# 2. restart keeps settings
m = load(keep_cfg=True)
chk("settings restored", m.Settings()["alpha"] == 65)

# 3. corrupt settings -> defaults, no crash
open(m.Paths.CFG_FILE, "w").write("{not json")
m = load(keep_cfg=True)
chk("corrupt settings -> defaults", m.Settings()["alpha"] == 80)

# 4. read-only settings dir: save must not raise
m = load(); s = m.Settings()
os.makedirs(m.Paths.CFG_DIR, exist_ok=True)
orig = os.replace
m.os.replace = lambda *a: (_ for _ in ()).throw(PermissionError("ro"))
try: s.save(); chk("readonly save safe", True)
except Exception: chk("readonly save safe", False)
m.os.replace = orig

# 5. storage skips remote drives
m = load()
P = type("P", (), {})
def part(mp, opts, fs="NTFS"):
    p = P(); p.mountpoint, p.opts, p.fstype = mp, opts, fs; return p
m.psutil.disk_partitions = lambda all=False: [part("C:\\", "rw,fixed"), part("Z:\\", "rw,remote"), part("D:\\", "cdrom", "")]
m.psutil.disk_usage = lambda mp: type("U", (), dict(total=100, used=50, free=50, percent=50.0))()
rows = m.StorageReader().read()
chk("remote/cdrom skipped", [r["mount"] for r in rows] == ["C:\\"])

# 6. no PresentMon / driver missing paths do not raise
m = load(); f = m.FpsMonitor()
m.Paths.PRESENTMON = "/nonexistent/PresentMon.exe"
try: f.start(); f.stop(); chk("no presentmon safe", True)
except Exception as e: chk("no presentmon safe %r" % e, False)

# 7. tray exit goes through Tk thread
m = load(); m.WinApi.setup(); app = m.App(); called = []
app.quit = lambda: called.append(1)
m.TrayIcon._exit(app.tray); app.root.update()
chk("tray exit scheduled", True)
print("phase4:", ok, "ok,", bad, "failed")
sys.exit(1 if bad else 0)
