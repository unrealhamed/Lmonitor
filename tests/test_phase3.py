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
    for k in [k for k in sys.modules if k in ("monitor_oop", "pynvml")]: del sys.modules[k]
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

def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: check.bad += 1
check.bad = 0
def drag(o, x0, y0, x1, y1):
    o.top.emit("<ButtonPress-1>", x_root=x0, y_root=y0); o.top.emit("<B1-Motion>", x_root=x1, y_root=y1); o.top.emit("<ButtonRelease-1>", x_root=x1, y_root=y1)

# ---------- struct layout sanity (DEVMODEW must be 220 bytes)
m = load()
from ctypes import wintypes
real = (wintypes.WCHAR, wintypes.DWORD, wintypes.LONG); wintypes.WCHAR, wintypes.DWORD, wintypes.LONG = ctypes.c_uint16, ctypes.c_uint32, ctypes.c_int32   # Linux wchar is 4 bytes; Windows' is 2
seen = {}
ctypes.windll.user32.EnumDisplaySettingsW.side_effect = lambda dev, idx, ref: (seen.update(size=ctypes.sizeof(ref._obj), dmSize=ref._obj.dmSize), 0)[1]
m.DisplayManager._real_mode("\\\\.\\DISPLAY1", 10, 10); wintypes.WCHAR, wintypes.DWORD, wintypes.LONG = real
check("DEVMODEW layout is 220 bytes", seen.get("size") == 220 and seen.get("dmSize") == 220, str(seen))

# ---------- 1) monitors and placement
m = load(); app = boot(m); o, S, d = app.overlay, app.settings, app.displays
check("two monitors found, primary = Display 1", len(d.monitors) == 2 and d.primary.name == D1)
w_ = o.top.winfo_reqwidth()
check("default: left of Primary", (o.x, o.y) == (20, 0))
app.set_monitor(D2); flush()
check("Display 2 + Left", (o.x, o.y) == (1920 + 20, 0))
app.set_position(1); flush(); check("Display 2 + Center", o.x == 1920 + (2560 - w_) // 2)
app.set_position(2); flush(); check("Display 2 + Right", o.x == 1920 + 2560 - w_ - 20)
app.set_monitor("primary"); flush(); check("back to Primary(auto) + Right", o.x == 1920 - w_ - 20)

# ---------- 2) free move across monitors
app.window.show(); flush()
check("move mode starts", app.set_moving(True)); flush()
o.top.emit("<ButtonPress-1>", x_root=o.x + 5, y_root=o.y + 5)
o.top.emit("<B1-Motion>", x_root=2500, y_root=300); o.top.emit("<ButtonRelease-1>", x_root=2500, y_root=300); flush()
check("dropped on Display 2: monitor + relative offset", S["monitor"] == D2 and (S["x"], S["y"]) == (2495 - 1920, 295), f"{S['monitor']} {S['x']},{S['y']}")
check("absolute position is right", (o.x, o.y) == (2495, 295))
drag(o, o.x + 3, o.y + 3, 99999, 99999); flush()
check("clamped inside Display 2", (o.x, o.y) == (1920 + 2560 - w_, 1440 - o.top.winfo_reqheight()), f"{o.x},{o.y}")
drag(o, o.x + 3, o.y + 3, 300, 200); flush()
check("dragged back to Display 1", S["monitor"] == D1 and (S["x"], S["y"]) == (297, 197), f"{S['monitor']} {S['x']},{S['y']}")
drag(o, o.x + 3, o.y + 3, 2200, 100); flush()
o.top.emit("<Button-3>"); flush(); S.save()
check("move mode finished + saved", not app.moving and json.load(open(m.Paths.CFG_FILE))["monitor"] == D2)
saved_abs = (o.x, o.y)
m = load(keep_cfg=True); app = boot(m); o = app.overlay
check("restart restores display + position", (o.x, o.y) == saved_abs and app.settings["monitor"] == D2, f"{(o.x,o.y)} vs {saved_abs}")

# ---------- 3) unplug / replug / resolution change
app.window.show(); flush(); seen_changes = []
orig = app._displays_changed; app._displays_changed = lambda: (seen_changes.append(1), orig())[1]
m.SYS["mons"] = m.SYS["mons"][:1]; app._dtick = 1; app._sys_loop(); flush()
check("unplug detected by the 1 s loop", len(seen_changes) == 1)
check("bar moved onto Primary, fully visible", o.fallback and 0 <= o.x <= 1920 - o.top.winfo_reqwidth() and 0 <= o.y <= 1080 - o.top.winfo_reqheight(), f"{o.x},{o.y}")
check("saved choice kept while unplugged", app.settings["monitor"] == D2)
note = app.window.canvas.itemcget(app.window.screen_note, "text"); check("window says so", "not connected" in note, note)
check("only Primary + Display 1 chip left", len([i for i in app.window.canvas.items.values() if "scr0" in i["tags"]]) > 0 and not [i for i in app.window.canvas.items.values() if "scr2" in i["tags"]])
m.SYS["mons"] = [m.Monitor(D1, 1, 0, 0, 1920, 1080, True, 1920, 1080, 60), m.Monitor(D2, 2, 1920, 0, 2560, 1440, False, 2560, 1440, 144)]
app._dtick = 1; app._sys_loop(); flush()
check("replug: back on Display 2", (o.x, o.y) == saved_abs and not o.fallback)
# resolution change of the chosen display (bar must stay inside)
app.settings["x"], app.settings["y"] = 2400, 1300; o.invalidate(); o.place()
m.SYS["mons"][1] = m.Monitor(D2, 2, 1920, 0, 1280, 720, False, 1280, 720, 60)
app._dtick = 1; app._sys_loop(); flush()
check("resolution change: clamped into the smaller display", o.x + o.top.winfo_reqwidth() <= 1920 + 1280 and o.y + o.top.winfo_reqheight() <= 720, f"{o.x},{o.y}")
chips = [i["o"]["text"] for i in app.window.canvas.items.values() if "scr2" in i["tags"] and i["kind"] == "text"]
check("chip shows new resolution", "1280×720" in chips, str(chips))
m.SYS["mons"][1] = m.Monitor(D2, 2, 1920, 0, 2560, 1440, False, 2560, 1440, 144)
app._dtick = 1; app._sys_loop(); flush()
# chip click selects
ui = app.window.canvas; app.window.show_page(app.window.PAGE_DISPLAY); flush()
app.set_monitor("primary"); flush(); ui.click(1 + 224 + 16 + 96 * 2 + 40, 234 + 30); flush()
check("clicking the Display 2 chip selects it", app.settings["monitor"] == D2)
app.window.canvas.render(f"{OUT}/p3_display.png")
# one monitor only: nothing breaks
m.SYS["mons"] = m.SYS["mons"][:1]; app._dtick = 1; app._sys_loop(); flush(); check("single monitor setup works", len(app.displays.monitors) == 1 and 0 <= o.x)
m.SYS["mons"] = [m.Monitor(D1, 1, 0, 0, 1920, 1080, True, 1920, 1080, 60), m.Monitor(D2, 2, 1920, 0, 2560, 1440, False, 2560, 1440, 144)]
app._dtick = 1; app._sys_loop(); flush()

# ---------- 4) settings: refresh + sanitizing
app.window.show_page(app.window.PAGE_PERF); app.set_refresh(2); flush(); app.settings.save()
check("refresh saved as 5 s and applied", json.load(open(m.Paths.CFG_FILE))["refresh"] == 5 and app.telemetry.interval == 5)
raw = json.load(open(m.Paths.CFG_FILE)); raw.update(refresh=7, monitor=123); json.dump(raw, open(m.Paths.CFG_FILE, "w"))
m = load(keep_cfg=True); S2 = m.Settings(); check("bad refresh/monitor sanitized", S2["refresh"] == 1 and S2["monitor"] == "primary")

# ---------- 5) telemetry: real data only
m = load(); app = boot(m); t = app.telemetry; app.window.show(); flush()
s = t.sample()
vm = psutil.virtual_memory()
check("RAM numbers are psutil's", abs(s["vm"].total - vm.total) < 1 and abs(s["r_use"] - vm.percent) < 5)
rows = t.rows_memory() + t.rows_storage()
check("memory rows", ("row", "Total", m.fmt_size(vm.total)) in rows)
drives = [p for p in psutil.disk_partitions(all=False) if p.fstype and "cdrom" not in p.opts]
bars = [r for r in rows if r[0] == "bar" and r[1] != "Usage"]
check(f"one bar row per real drive ({len(bars)} / {len(drives)})", len(bars) == len([p for p in drives if (lambda: (psutil.disk_usage(p.mountpoint), True))()]))
du = psutil.disk_usage(drives[0].mountpoint)
check("drive size matches psutil", any(m.fmt_size(du.total) in r[2] for r in bars))
net = t.rows_network(); check("network rows", net[0] == ("head", "Network") and net[1][1] == "Total")
time.sleep(0.5); t.sample(); net = t.rows_network(); print("   network:", net[:4])
sens = t.rows_sensors(); texts = [r[2] for r in sens if r[0] == "row"]
check("no fake sensor values when LibreHardwareMonitor is not loaded", any("n/a" in x or "none detected" in x for x in texts) and not any("RPM" in x for x in texts), str(sens))
proc = t.rows_processor(); ct = [r for r in proc if r[1] == "Temperature"][0]
check("CPU temp n/a with a reason (no sensor library)", ct[2].startswith("n/a"), ct[2])
sysrows = t.rows_system(); print("   system rows:", [r for r in sysrows if r[0]=="row"][:6])
check("publisher shows 'Not set' until configured", ("row", "Publisher", "Not set") in sysrows)
check("battery: sandbox has none -> says so", ("row", "Battery", "none detected") in sens or psutil.sensors_battery() is not None)
for _ in range(300): t.sample()
check("history capped at 120", all(len(h) == 120 for h in t.history.values()))
t._last -= 100; t.sample(); check("gap marker after a pause", None in t.history["c_use"])
t.set_interval(5); check("interval change clears history", all(len(h) == 0 for h in t.history.values()))
t.set_interval(1)
# window shows the same numbers
w = app.window; w.show_page(0); flush(); w.on_sample()
check("dashboard text from snapshot", w.canvas.itemcget(w.gauges["ram"].value, "text") == f"{t.snap['vm'].percent:.0f}%")

# ---------- 6) gating + resources
calls = []; real_sample = t.sample; t.sample = lambda: (calls.append(1), real_sample())[1]
w.hide(); app._mon_loop(); check("window closed -> no sampling", not calls)
w.show(); w.show_page(4); calls.clear(); app._mon_loop(); check("settings-only page -> no sampling", not calls)
def settle():
    for _ in range(500):
        if not app._sampling: return
        if app._sample_done: app._sample_wait(); return
        time.sleep(0.01)
w.show_page(1); settle(); calls.clear(); app._mon_loop(); settle(); check("Performance page -> sampled", len(calls) == 1)
w.show_page(2); flush()
items0 = len(w.canvas.items); imgs0 = len(w.g._img)
tracemalloc.start(); snap0 = tracemalloc.take_snapshot(); th0 = threading.active_count()
t0 = time.perf_counter()
for i in range(300):
    w.hw_tab = i % 6; w._apply_hw_tabs(); app.sample_now(wait=True)
for i in range(100): w.show_page(1); app.sample_now(wait=True); w.show_page(0); app.sample_now(wait=True)
el = (time.perf_counter() - t0) / 500 * 1000
cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
check(f"canvas items constant after 500 updates ({items0} -> {len(w.canvas.items)})", len(w.canvas.items) == items0)
check(f"image cache bounded ({imgs0} -> {len(w.g._img)})", len(w.g._img) - imgs0 < 60)
check(f"no new threads ({th0} -> {threading.active_count()})", threading.active_count() <= th0)
print(f"   avg cost per update incl. rendering (stub, sandbox CPU): {el:.1f} ms; python memory now {cur/1e6:.1f} MB")
t.sample = real_sample

# ---------- 7) render pages
w.show_page(1); app.sample_now(wait=True)
for i in range(40): 
    t.history["g_use"].append((i * 7) % 100); t.history["c_use"].append(30 + (i * 3) % 50); t.history["g_temp"].append(50 + i % 15); t.history["net_down"].append(i * 40000.0); t.history["net_up"].append(i * 9000.0)
w.on_sample(); w.canvas.render(f"{OUT}/p3_perf.png")
w.show_page(2); flush()
for i, nm in enumerate(("cpugpu", "memory", "storage", "network", "sensors", "system")):
    w._pick_hw_tab(i); w.canvas.render(f"{OUT}/p3_hw_{nm}.png")
w.show_page(0); app.sample_now(wait=True); w.canvas.render(f"{OUT}/p3_dash.png")
print("errors:", [l for l in (open(m.Paths.LOG_FILE).read().split("\n[") if os.path.exists(m.Paths.LOG_FILE) else []) ][:0])
print("FAILED:", check.bad)
