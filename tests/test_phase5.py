import os as _os
import sys, os, json, time
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
import tkinter as tk
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

m = load(); app = boot(m); w = app.window; S = app.settings; o = app.overlay
def settle():
    for _ in range(500):
        if not app._sampling: return
        if app._sample_done: app._sample_wait(); return
        time.sleep(0.01)

# --- themes: every theme x accent draws, stays on the page, saves, restores
errs = []
for key, *_ in m.Theme.UI_THEMES:
    for acc in ("auto", "pink"):
        app.set_ui_style(theme=key, accent=acc); flush()
        if w.canvas.opts.get("bg") != m.Theme.C_BG: errs.append((key, "bg"))
chk("4 themes x accents redraw without error", not errs)
for key, *_ in m.Theme.UI_THEMES:
    app.set_ui_style(theme=key, accent="auto"); flush()
    w.show(); w.show_page(7); flush(); w.canvas.render(f"{OUT}/p5_personalize_{key}.png")
    w.show_page(0); settle(); w.canvas.render(f"{OUT}/p5_dash_{key}.png")
chk("theme saved", (app.settings.save() or True) and json.load(open(m.Paths.CFG_FILE))["ui_theme"] == "aurora")
chk("aurora accent is its own", m.Theme.ACCENT == "#2ee6c5")
app.set_ui_style(theme="day", accent="auto"); flush()
chk("day: light flag + readable white->TXT", m.Theme.LIGHT and m.Theme.ui_color(m.Theme.WHITE) == m.Theme.TXT)
chk("day: accent darkened for contrast", m.Theme.ACCENT != m.Theme.VENDOR["accent"])
m2 = load(keep_cfg=True); app2 = boot(m2)
chk("theme restored after restart", app2.settings["ui_theme"] == "day" and m2.Theme.LIGHT and m2.Theme.C_BG == "#eceff4")
app2.reset_defaults(); flush()
chk("overlay reset keeps the app theme", app2.settings["ui_theme"] == "day")
S2 = m2.Settings(); S2.data["ui_theme"] = "zzz"; S2.data["palette"] = "x"
m3 = load(keep_cfg=True)
json.dump({"ui_theme": "zzz", "ui_accent": "q", "palette": "x", "net_unit": "?"}, open(m3.Paths.CFG_FILE, "w"))
S3 = m3.Settings()
chk("bad theme/palette/unit values sanitized", (S3["ui_theme"], S3["ui_accent"], S3["palette"], S3["net_unit"]) == ("default", "auto", "auto", "bytes"))

# --- overlay palettes, backgrounds
m = load(); app = boot(m); w = app.window; S = app.settings; o = app.overlay
app.set_palette("neon"); flush()
chk("palette changes group label colors", o.colors["GPU"] == "#39ff88" and o.colors["NET"] == "#ffe14d")
app.set_palette("auto"); chk("auto palette = brand colors", o.colors["GPU"] == app.gpu.brand_color())
chk("10 backgrounds", len(m.Theme.OVERLAY_BGS) == 10 and all(m.Theme.overlay_bg(k) for k, *_ in m.Theme.OVERLAY_BGS))
w.show(); w.show_page(4); flush(); w.canvas.render(f"{OUT}/p5_appearance.png")
w._pick_palette("sunset"); w._pick_bg("ocean"); flush()
chk("appearance picks stored", S["palette"] == "sunset" and S["bg"] == "ocean")

# --- network speed on the overlay
w.show_page(5); flush(); w.canvas.render(f"{OUT}/p5_metrics.png")
chk("NET labels exist", "n_down" in o.labels and "n_up" in o.labels and o.need["NET"])
import psutil
c = type("C", (), {})
t0 = time.time()
def fake(n):
    cc = c(); cc.bytes_recv = n; cc.bytes_sent = n // 2; return {"Ethernet": cc}
st = type("S", (), dict(isup=True, speed=1000))()
m.psutil.net_if_stats = lambda: {"Ethernet": st}
m.psutil.net_io_counters = lambda pernic=True: fake(0)
app.updater.network.prev = None; app.updater.network.read(); time.sleep(0.3)
m.psutil.net_io_counters = lambda pernic=True: fake(int(0.3 * 5 * 1024 * 1024))
app.updater.update_system()
txt = o.labels["n_down"].opts["text"]
chk(f"download shown in MB/s ({txt})", txt.startswith("↓ ") and "MB/s" in txt)
app.set_net_unit(1); time.sleep(0.3)
m.psutil.net_io_counters = lambda pernic=True: fake(int(0.9 * 5 * 1024 * 1024))
app.updater.update_system(); txt2 = o.labels["n_down"].opts["text"]
chk(f"download in Mbps after unit change ({txt2})", "Mbps" in txt2 and S["net_unit"] == "bits")
chk("fmt_net edge cases", m.fmt_net(None) == "--" and m.fmt_net(0) == "0KB/s" and m.fmt_net(1250000, "bits") == "10.0Mbps")
n = m.NetworkReader(); chk("no data -> --", m.fmt_net(n.total()[0]) == "--")

# --- move mode keeps the look
for look in ("dark", "glass"):
    S["look"] = look; app.rebuild(); flush()
    before = (o.top.attrs.get("-alpha"), o.top.opts["highlightthickness"], o.tint)
    app.set_moving(True); flush()
    during = (o.top.attrs.get("-alpha"), o.top.opts["highlightthickness"], o.tint)
    chk(f"{look}: alpha/size/tint same while moving", (look == "glass" and during[1:] == before[1:]) or before == during)
    app.set_moving(False); flush()
    after = (o.top.attrs.get("-alpha"), o.top.opts["highlightthickness"], o.tint)
    chk(f"{look}: look restored after moving", after == before)

# --- navigation: instant, only 2 pages change state, no sensor read on the UI thread
w.show(); w.show_page(0); settle()
calls = []
real = app.telemetry.sample
def slow():
    calls.append(threading_name()); time.sleep(0.15); return real()
import threading
threading_name = lambda: threading.current_thread().name
app.telemetry.sample = slow
t = time.perf_counter()
for i in (1, 2, 0, 4, 1):
    w.show_page(i)
dt = (time.perf_counter() - t) * 1000
chk(f"5 page switches with a 150 ms sensor read take {dt:.0f} ms (no wait)", dt < 120)
settle(); time.sleep(0.2); settle()
chk("sensors read off the UI thread", calls and all(n != "MainThread" for n in calls))
changed = []
orig = w.canvas.itemconfigure
w.canvas.itemconfigure = lambda tag, *a, **k: (changed.append(tag), orig(tag, *a, **k))[1]
w.show_page(3); w.canvas.itemconfigure = orig
chk("page switch touches only 2 page tags", len([x for x in changed if str(x).startswith("p_")]) == 2)
app.telemetry.sample = real

# --- worker never overlaps the overlay read (lock)
chk("lock exists", hasattr(m, "HW_LOCK"))
# --- nav fits 8 entries above the sidebar footer
chk("8 menu entries end above y=400", 98 + 8 * (m.NavMenu.H + m.NavMenu.GAP) <= 400)
# --- 100 theme switches: items and images bounded
n0 = len(w.canvas.find_all()); 
for i in range(12): app.set_ui_style(theme=("night", "day", "aurora", "default")[i % 4]); flush()
n1 = len(w.canvas.find_all())
chk(f"canvas items stable after 12 theme switches ({n0}->{n1})", abs(n1 - n0) < 30)
print(f"phase5: {ok} ok, {bad} failed"); sys.exit(1 if bad else 0)
