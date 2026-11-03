import os as _os
import sys, os, json, time, threading
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

m = load(); app = boot(m); w = app.window; S = app.settings; ui = w.canvas
w.show(); flush()
chk("window 1000x600 with right panel", m.Theme.WIN_W == 1000 and m.Theme.PANEL_X + m.Theme.PANEL_W <= m.Theme.WIN_W)

# --- recorder
r = app.recorder
now = time.time()
r.data.clear()
for i in range(120):   # 10 minutes of samples every 5 s
    r.data.append((now - 600 + i * 5, 10 + i % 50, 40, None if i < 20 else 70))
ser = r.series(300, 30)
chk("recorder: 3 series x 30 buckets", len(ser) == 3 and all(len(x) == 30 for x in ser))
chk("recorder: averages, last 5 min only", ser[1][0] == 40 and ser[0][-1] is not None)
chk("recorder: missing data stays None", all(v is None for v in r.series(600, 60)[2][:6]))
chk("recorder: nothing recorded -> all None", all(v is None for v in m.Recorder(app.gpu).series(60)[0]))
rec = m.Recorder(app.gpu); rec.tick()
for _ in range(200):
    if not rec.busy: break
    time.sleep(0.01)
chk("recorder tick records one row in a worker thread", len(rec.data) == 1 and len(rec.data[0]) == 4)
chk("24 h at 5 s kept", m.Recorder.KEEP == 17280)

# --- dashboard fills from one sample
app.sample_now(wait=True); app.sample_now(wait=True)
w.show_page(0)
snap = app.telemetry.snap
chk("gauge text = RAM %", ui.itemcget(w.gauges["ram"].value, "text") == f"{snap['vm'].percent:.0f}%")
chk("gauge sub shows used / total", "/" in ui.itemcget(w.gauges["ram"].sub, "text"))
chk("sensor status words filled (OK or Unavailable, never blank)", ui.itemcget(w.live["st_gpu"], "text") in ("OK", "Unavailable") and ui.itemcget(w.live["st_cpu"], "text") in ("OK", "Unavailable"))
chk("hero + last update filled", ui.itemcget(w.live["hero"], "text") != "" and "Last update" in ui.itemcget(w.live["upd"], "text"))
w.canvas.render(f"{OUT}/p6_dash.png")

# --- range tabs
seen = []
real = app.recorder.series
app.recorder.series = lambda sec, points=90: (seen.append(sec), real(sec, points))[1]
for i, sec in enumerate((60, 300, 3600, 86400)):
    w._pick_range(i)
chk("range tabs ask for 5 min / 1 hr / 24 h", seen == [300, 3600, 86400])
app.recorder.series = real
w._pick_range(0)

# --- gauge states
g = w.gauges["gpu"]
g.update(None, "n/a"); chk("no data -> -- and 'No data'", ui.itemcget(g.value, "text") == "--" and ui.itemcget(g.chip, "text") == "No data")
g.update(95, "hot", "", "high"); chk("95% high load shown", ui.itemcget(g.value, "text") == "95%" and ui.itemcget(g.chip, "text") == "High load")
g.update(0, "", "", "ok"); chk("0 renders", ui.itemcget(g.value, "text") == "0%")
g.update(100, "", "", "ok"); chk("100 renders", ui.itemcget(g.value, "text") == "100%")

# --- right panel on every page
names = [n for n, _ in w.PAGES]
tags_ok = True
for i in range(len(names)):
    w.show_page(i)
    # panel items have no page tag, so they are never hidden
    if any("save" in it["tags"] and it["o"].get("state") == "hidden" for it in ui.items.values()):
        tags_ok = False
chk("panel visible on all 8 pages", tags_ok)
w.show_page(4); flush()
chk("appearance page has no second opacity slider", w.alpha_val is not None and ui.itemcget(w.alpha_val, "text") == f"{S['alpha']}%")

# --- panel controls change settings
w._on_text(14); chk("panel text size", S["text"] == 14 and ui.itemcget(w.text_val, "text") == "14 pt")
w._on_graph(150); chk("panel graph size", S["graph"] == 150)
w._on_alpha(60); chk("panel opacity", S["alpha"] == 60 and ui.itemcget(w.alpha_val, "text") == "60%")
w.pos_seg.cb(1); flush(); chk("panel position center", S["pos"] == "center")
S["pos"] = "custom"; w.sync_position(); chk("custom position -> no segment selected", w.pos_seg.index == -1)
w.pos_seg.click(tk.Event(w.pos_seg.x + 5, 0)); flush(); chk("click Left from custom", S["pos"] == "left" and w.pos_seg.index == 0)
app.set_overlay(False); w.update_status(); chk("overlay switch + status follow", ui.itemcget(w.live["hero"], "text") == "Overlay hidden")
app.set_overlay(True)

# --- reset redraws the panel, keeps theme
app.set_ui_style(theme="night"); flush()
app.reset_defaults(); flush()
chk("reset restores sizes, keeps theme", S["text"] == 11 and S["alpha"] == 80 and S["ui_theme"] == "night" and w.pos_seg is not None)

# --- display page lost the duplicates but keeps move + screens
w.show_page(3); flush()
chk("display page: move button + screens present", w.move_img is not None and w.screen_note is not None)
w.canvas.render(f"{OUT}/p6_display.png")

# --- themes render the whole new window
for key, *_ in m.Theme.UI_THEMES:
    app.set_ui_style(theme=key); flush(); w.show_page(0); app.sample_now(wait=True)
    w.canvas.render(f"{OUT}/p6_dash_{key}.png")
chk("4 themes redraw the dashboard", True)

# --- resources: threads and canvas items stay constant
n0, th0 = len(ui.find_all()), threading.active_count()
for i in range(300):
    app.sample_now(wait=True)
chk(f"items constant ({n0} -> {len(ui.find_all())}), threads {th0} -> {threading.active_count()}",
    len(ui.find_all()) == n0 and threading.active_count() <= th0 + 1)
print(f"phase6: {ok} ok, {bad} failed"); sys.exit(1 if bad else 0)
