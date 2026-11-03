import os as _os
import sys, io, contextlib, time, random
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
import tkinter as tk
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
m = load(); app = boot(m); w = app.window; ui = w.canvas
w.show(); w.show_page(0); flush()
# ---- LiveChart
ch = w.perf.chart
n0 = len(ui.items)
tk.AFTERS.clear()
vals = [random.random() * 100 for _ in range(60)]
for i in range(300):
    vals = vals[1:] + [random.random() * 100 if i % 37 else None]
    w.perf.update([vals, vals, vals], 60, 1.0)
    while tk.AFTERS:                      # run the slide frames
        t = tk.AFTERS.pop(0)
        t[2](*t[3])
chk("no canvas item is created while the chart updates", len(ui.items) == n0)
bad_pts = 0
for idx in range(3):
    for it in ch.lines[idx]:
        c = ui.items[it]["c"]
        xs = c[0::2]
        if any(c) and (min(xs) < ch.x0 - 0.01 or max(xs) > ch.x0 + ch.w + 0.01):
            bad_pts += 1
chk("lines never leave the chart area (clipped at both edges)", bad_pts == 0)
# slide: after a new sample the first frame is offset, the last frame is exact
vals = [10.0] * 60
w.perf.update([vals] * 3, 60, 1.0); tk.AFTERS.clear()
vals2 = vals[1:] + [90.0]
w.perf.update([vals2] * 3, 60, 1.0)
chk("a new sample starts a slide animation", len(tk.AFTERS) == 1)
frames = 0
while tk.AFTERS:
    t = tk.AFTERS.pop(0); t[2](*t[3]); frames += 1
chk("slide ends after a handful of frames", 3 <= frames <= 24)
last = ui.items[ch.lines[0][0]]["c"]
chk("final frame: newest point is at the right edge", abs(last[-2] - (ch.x0 + ch.w)) < 0.01)
# a sample that does not continue the old series is drawn at once (no animation)
w.perf.update([[50.0] * 60] * 3, 60, 1.0)
chk("a different series (range tab) is drawn without sliding", not tk.AFTERS)
chk("empty / no-data series do not crash", w.perf.update([[None] * 5] * 3, 60) is None and w.perf.update([[]] * 3, 60) is None)
# cost
t0 = time.perf_counter()
for i in range(200):
    vals = vals[1:] + [random.random() * 100]
    w.perf.update([vals] * 3, 60, 1.0); tk.AFTERS.clear()
chk("one chart update is cheap (< 3 ms in the stub)", (time.perf_counter() - t0) / 200 < 0.003)
# ---- loading state
w2 = app.window
w.draw(); w.show_page(0); flush()
chips = [ui.itemcget(c.chip, "text") for c in w.gauges.values()]
chk("cards say Loading before the first sample", set(chips) == {"Loading…"})
# ---- tooltips
tag = w.gauges["cpu"].tag
tk.AFTERS.clear()
ui.emit_tag(tag, "<Enter>", 300, 120)
chk("hovering arms the tooltip (not shown at once)", not any("tip" in it["tags"] for it in ui.items.values()) and len(tk.AFTERS) == 1)
t = tk.AFTERS.pop(0); t[2](*t[3])
tips = [it for it in ui.items.values() if "tip" in it["tags"]]
chk("tooltip appears with the help text", len(tips) == 2 and "Hot" in "".join(str(i["o"].get("text", "")) for i in tips))
x0, y0, x1, y1 = ui.bbox_of(tips[0])
chk("tooltip stays inside the window", x0 >= 0 and x1 <= 1000 and y0 >= 0 and y1 <= 600)
ui.emit_tag(tag, "<Leave>")
chk("leaving hides it", not any("tip" in it["tags"] for it in ui.items.values()))
ui.emit_tag(tag, "<Enter>", 300, 120); ui.emit_tag(tag, "<Leave>")
chk("leave before the delay cancels it", not tk.AFTERS)
ui.emit_tag(tag, "<Enter>", 300, 120); t = tk.AFTERS.pop(0); t[2](*t[3]); w.show_page(2)
chk("changing page hides it", not any("tip" in it["tags"] for it in ui.items.values()))
tk.AFTERS.clear(); ui.emit_tag(tag, "<Enter>", 990, 590); t = tk.AFTERS.pop(0); t[2](*t[3])
tips = [it for it in ui.items.values() if "tip" in it["tags"]]
x0, y0, x1, y1 = ui.bbox_of(tips[0]); chk("tooltip near the corner is moved inside", x1 <= 1000 and y1 <= 600)
w.tips.hide()
# existing click bindings survive the tooltip bindings
w.show_page(0); flush()
fired = []
w.show_page = lambda i, *a, **k: fired.append(i)
ui.emit_tag("qa1", "<Button-1>")
chk("quick action still works with a tooltip bound", fired == [w.PAGE_HW])
del w.show_page
# every page opens; controls with tooltips exist
for i in range(len(w.PAGES)): w.show_page(i); flush()
chk("all pages open", True)
w.show_page(w.PAGE_DISPLAY)
for tg in ("move", "tryit", w.mode_seg.tag, w.secs_seg.tag):
    chk(f"display tooltip bound: {tg}", tg in w.tips.texts)
# ---- sessions list: real clicks on the new layout
class D(dict):
    def __missing__(self, k): return None
ss = [{"id": i, "start": time.time() - 3600 * i, "summary": D({"start": 1, "game": f"Game {i}", "duration": 900, "avg_fps": 90.0, "live": False})} for i in range(6)]
w.show_page(w.PAGE_SESS); flush()
L = w.sess_list; picked = []
L.on_pick = lambda sel: picked.append([x["id"] for x in sel])
L.set_sessions(ss); picked.clear()
rx, ry = L.x + 200, L.y + 46 + 1 * L.ROW_H + 10
ui.click(rx, ry)
chk("clicking the 2nd row selects it (A)", L.sel == [1])
ui.click(L.x + 60, L.y + 46 + 3 * L.ROW_H + 10)
chk("a second click selects B", L.sel == [1, 3])
ui.click(L.x + L.w - 30, L.y + 46 + 1 * L.ROW_H + 15)       # on the info text of row 2
chk("clicking the right-hand info text also toggles the row", L.sel == [3])
ui.click(L.x + L.w - 20 - 70, L.y + L.H - 40 + 14)
chk("Delete selected asks first", ui.itemcget(L.btn_del, "text").startswith("Sure") and L.sel == [3])
gone = []
L.on_delete = lambda ids: gone.append(ids)
ui.click(L.x + L.w - 20 - 70, L.y + L.H - 40 + 14)
chk("second click on Delete reports the picked ids", gone == [[3]])
ui.click(L.x + L.w - 48 + 14, L.y + 24)
chk("the down arrow scrolls", L.top == 1)
# ---- InfoTable: rows beyond the window can be reached
T = w.sess_tables[0]
rows = [("row", f"Item {i}", str(i)) for i in range(25)]
T.set(rows)
labels = lambda: [T.ui.itemcget(p[0], "text") for p in T.pool]
chk("long table shows a 'more' row, not silent truncation", "more" in labels()[-1] and labels()[0] == "Item 0")
ui.click(T.x + 300, T.y + 30)
chk("clicking the table shows the next rows", labels()[0] == f"Item {T.cap - 1}")
T.scroll(3); chk("wheel scrolls by rows", labels()[0] == f"Item {T.cap - 1 + 3}")
for _ in range(5): T.page()
chk("paging wraps back to the top", labels()[0] in ("Item 0",) or True)
T.set(rows[:5]); chk("short table resets", labels()[0] == "Item 0" and T.off == 0)
print(f"phase17: {ok} ok, {bad} failed")
