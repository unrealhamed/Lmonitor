import os as _os
import sys, io, contextlib, time, os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
m = load(); app = boot(m); w = app.window; tel = app.telemetry; ui = w.canvas
w.show(); w.show_page(0); flush()
class VM: percent = 40.0; used = 8 * 1024**3; total = 16 * 1024**3
def snap(**k):
    s = {"g_use": 30, "g_temp": 55, "g_pow": 120, "g_clk": 1800, "g_mem": None, "g_fan": None, "c_use": 20, "c_temp": 50, "c_pow": 30, "c_clk": 4200, "c_approx": False, "vm": VM(), "sw": None, "r_use": 40.0, "net_down": 1000, "net_up": 500}
    s.update(k); return s
def show(**k):
    tel.snap = snap(**k); w._update_dashboard(); flush()
txt = lambda key, it: ui.itemcget(getattr(w.gauges[key], it), "text")
show()
chk("normal load: Normal chip, values shown", txt("cpu", "chip") == "Normal" and txt("cpu", "value") == "20%" and "50" in txt("cpu", "sub") and "4.2 GHz" in txt("cpu", "sub2"))
show(c_temp=None, g_temp=None)
chk("no temperature sensor: honest text, status from load only (not 'Hot')", txt("cpu", "chip") == "Normal" and "no temperature" in txt("cpu", "sub") and "no temperature" in txt("gpu", "sub") and ui.itemcget(w.live["st_cpu"], "text") == "Unavailable" and ui.itemcget(w.live["st_gpu"], "text") == "Unavailable")
show(c_use=None, c_temp=None, c_clk=None)
chk("nothing at all: No data and --", txt("cpu", "chip") == "No data" and txt("cpu", "value") == "--")
show(g_temp=85); chk("GPU at 85 C is Hot", txt("gpu", "chip") == "Hot")
show(g_temp=72); chk("GPU at 72 C is Warm (10 below the hot limit)", txt("gpu", "chip") == "Warm")
show(c_use=95, c_temp=60); chk("CPU 95 % load is High load", txt("cpu", "chip") == "High load")
show(r_use=92.0); chk("RAM 92 % is High load", txt("ram", "chip") == "High load")
show(r_use=85.0); chk("RAM 85 % is Warm", txt("ram", "chip") == "Warm")
tel.storage._rows = [{"mount": "C:\\", "fs": "NTFS", "label": "", "total": 100, "used": 95, "free": 5, "pct": 95.0}]
show(); chk("disk with 5 % free is Almost full", txt("disk", "chip") == "Almost full" and "free" in txt("disk", "sub"))
tel.storage._rows = [{"mount": "C:\\", "fs": "NTFS", "label": "", "total": 100, "used": 85, "free": 15, "pct": 85.0}]
show(); chk("disk with 15 % free is Low space", txt("disk", "chip") == "Low space")
tel.storage._rows = []
show(); chk("no disk data -> No data", txt("disk", "chip") == "No data" and txt("disk", "value") == "--")
chk("health score: no scan -> '--'", ui.itemcget(w.live["score"], "text") == "--" and "run a scan" in ui.itemcget(w.live["score_sub"], "text"))
app.scanner.issues = [{"id": a.lower(), "area": a, "title": a, "sev": "ok", "evidence": [], "explain": "", "fix": ""} for a in m.ReportBuilder.AREAS]
show(); chk("health score from the last scan", ui.itemcget(w.live["score"], "text") == "100")
# quick actions go to real pages
seen = []
w.show_page = lambda i, animate=True: seen.append(i)
app.scan_now = lambda: seen.append("scan")
ids = [i for i, it in ui.items.items() if any(t.startswith("qa") for t in it["tags"])]
chk("four quick-action buttons exist", len({t for i in ids for t in ui.items[i]["tags"] if t.startswith("qa")}) == 4)
for n in range(4):
    cb = ui.binds.get(f"qa{n}") if hasattr(ui, "binds") else None
w.canvas.render(f"{OUT}/p16_dash.png")
print(f"phase16: {ok} ok, {bad} failed")
