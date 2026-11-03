import os as _os
import sys, os, ctypes, struct, json, shutil
from unittest.mock import MagicMock
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "stubs"))
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import imagetk_stub, PIL
sys.modules["PIL.ImageTk"] = imagetk_stub; PIL.ImageTk = imagetk_stub
import tkinter as tk
OUT = _os.path.join(__import__("tempfile").gettempdir(), "lmonitor_test_prev")
APPD = _os.path.join(__import__("tempfile").gettempdir(), "lmonitor_test_appdata_ov")

def load(blur=True, keep_cfg=False, blur_ok=True):
    for k in [k for k in sys.modules if k in ("monitor_oop", "pynvml")]: del sys.modules[k]
    ctypes.windll = MagicMock(); ctypes.windll.shell32.IsUserAnAdmin.return_value = 1
    ctypes.windll.kernel32.GetLastError.return_value = 0
    calls = []
    def swca(hwnd, ref):
        d = ref._obj; raw = ctypes.string_at(d.data, 16); calls.append((d.attr,) + struct.unpack("<iiII", raw)); return 1 if blur_ok else 0
    ctypes.windll.user32.SetWindowCompositionAttribute.side_effect = swca
    st = {"ex": 0}
    ctypes.windll.user32.GetWindowLongW.side_effect = lambda h, i: st["ex"]
    def setl(h, i, v): st["ex"] = v
    ctypes.windll.user32.SetWindowLongW.side_effect = setl
    ctypes.EXSTYLE = st
    if not keep_cfg: shutil.rmtree(APPD, ignore_errors=True)
    os.environ["APPDATA"] = APPD; os.environ.pop("NVFAIL", None); sys.argv = ["monitor.py"]
    import importlib.util
    spec = importlib.util.spec_from_file_location("monitor_oop", _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "monitor.py"))
    m = importlib.util.module_from_spec(spec); sys.modules["monitor_oop"] = m; spec.loader.exec_module(m)
    m.WinApi.blur_supported = staticmethod(lambda: blur)
    return m, calls

def flush():
    for _ in range(300):
        if not tk.AFTERS: return
        for t in list(tk.AFTERS):
            if t in tk.AFTERS:
                tk.AFTERS.remove(t)
                if t[2]: t[2](*t[3])

def boot(m):
    m.WinApi.setup(); m.WinApi.ensure_admin(); app = m.App(); app.window.draw(); app.rebuild(); flush(); return app

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: check.bad += 1
check.bad = 0

# ---------- 1) looks
m, calls = load(); app = boot(m); o = app.overlay; S = app.settings; ui = o.top
check("dark default: bg tint, no transparentcolor", o.bg == "#101010" and ui.attrs.get("-transparentcolor") == "" and abs(ui.attrs["-alpha"] - .8) < 1e-9)
check("dark: blur switched off (state 0)", calls and calls[-1][1] == 0)
app.window.show(); flush()
app.window._pick_look(1); flush()
check("glass: labels use KEY, transparentcolor KEY, alpha 1", o.bg == o.KEY and ui.attrs["-transparentcolor"] == o.KEY and ui.attrs["-alpha"] == 1.0 and all(l.opts["bg"] == o.KEY for l in o.labels.values()))
st = calls[-1]; check("glass: acrylic state 4, attr 19", st[0] == 19 and st[1] == 4)
a = (st[3] >> 24) & 255; check(f"glass: tint alpha follows opacity 80% -> {a}", a == int(255*.8*.9))
check("glass: edge outline", ui.opts.get("highlightthickness") == 2)
app.window._on_alpha(40); flush(); st = calls[-1]; check("opacity 40 -> alpha byte " + str((st[3]>>24)&255), (st[3] >> 24) & 255 == int(255*.4*.9))
app.window._pick_bg("midnight"); flush(); check("background midnight applied", o.tint == "#0e1526" and (calls[-1][3] & 0xFFFFFF) == 0x26150e)
app.window._pick_bg("accent"); flush(); check("accent bg derived from theme", o.tint == m.Theme.overlay_bg("accent") and o.tint != "#101010")
# graph canvas bg follows
check("graph canvas transparent in glass", o.canvas is not None and o.canvas.bg == o.KEY)
app.window._pick_look(0); flush(); check("back to dark", o.bg == o.tint and ui.attrs["-transparentcolor"] == "")
# blur refused -> fallback
m2, c2 = load(blur_ok=False); app2 = boot(m2); app2.settings["look"] = "glass"; app2.rebuild(); flush()
check("blur refused -> falls back to dark bar", app2.overlay.glass_ok is False and app2.overlay.bg == app2.overlay.tint)
m3, c3 = load(blur=False); app3 = boot(m3); app3.settings["look"] = "glass"; app3.rebuild(); flush()
check("old Windows -> no acrylic call at all", app3.overlay.glass is False and not [c for c in c3 if c[1] == 4])
app3.window.show(); app3.window.update_status(); flush(); print("   status text:", app3.window.canvas.itemcget(app3.window.blur_id, "text"))

# ---------- 2) persistence
app.settings["look"] = "glass"; app.settings["bg"] = "graphite"; app.settings["alpha"] = 65; app.settings.save()
raw = json.load(open(m.Paths.CFG_FILE)); check("file has look/bg/alpha", raw["look"] == "glass" and raw["bg"] == "graphite" and raw["alpha"] == 65)
m, calls = load(keep_cfg=True); app = boot(m); S = app.settings
check("restart keeps look/bg/alpha", S["look"] == "glass" and S["bg"] == "graphite" and S["alpha"] == 65 and app.overlay.glass)
bad = dict(raw, look="neon", bg="pink", x="a", y=3, pos="custom", order={"groups": ["CPU", "XX", "CPU"], "items": {"GPU": ["g_mem", "nope"]}})
json.dump(bad, open(m.Paths.CFG_FILE, "w")); m, calls = load(keep_cfg=True); S = m.Settings()
check("bad file is sanitized", S["look"] == "dark" and S["bg"] == "black" and S["x"] is None and S["pos"] == "left" and S["order"]["groups"][0] == "CPU" and sorted(S["order"]["groups"]) == ["CPU","FPS","GPU","NET","RAM"] and S["order"]["items"]["GPU"][0] == "g_mem" and len(S["order"]["items"]["GPU"]) == 5)

# ---------- 3) reorder with drag & drop
m, calls = load(); app = boot(m); w = app.window; S = app.settings; ui = w.canvas
w.show(); w.show_page(w.PAGE_ORDER); flush()
rl = w.order_groups; ids0 = [r[0] for r in rl.rows]
mid = lambda i: rl.slot_y(i) + rl.h / 2
rl.press(0, tk.Event(0, mid(0))); rl.move(tk.Event(0, mid(2) + 3)); rl.release(tk.Event(0, mid(2) + 3)); flush()
check(f"drag section FPS 0->2: {ids0} -> {S['order']['groups']}", S["order"]["groups"] == ["GPU", "CPU", "FPS", "RAM", "NET"])
labs = [k for k in ("FPS","GPU","CPU")]
order_seen = [g for g, _ in m.Metrics.ordered(S["order"])]
check("overlay rebuilt in new order (labels packed: GPU before FPS)", list(o_ := app.overlay.labels).index("g_use") < list(o_).index("fps"))
# items tab
w._pick_order_group(1); flush()
il = w.order_items; mid2 = lambda i: il.slot_y(i) + il.h / 2
il.press(4, tk.Event(0, mid2(4))); il.move(tk.Event(0, mid2(0) - 2)); il.release(tk.Event(0, mid2(0) - 2)); flush()
check("drag GPU item VRAM to first: " + str(S["order"]["items"]["GPU"]), S["order"]["items"]["GPU"][0] == "g_mem")
check("overlay label order follows (g_mem before g_use)", list(app.overlay.labels).index("g_mem") < list(app.overlay.labels).index("g_use"))
# tiny drag = no change
before = list(S["order"]["groups"]); rl.press(1, tk.Event(0, mid(1))); rl.move(tk.Event(0, mid(1) + 4)); rl.release(tk.Event(0, mid(1) + 4)); check("small drag keeps order", S["order"]["groups"] == before)
# hidden metric dims but stays in order
w.toggle_key("g_pow"); flush(); check("hidden item still listed", any(r[0] == "g_pow" and r[2] is False for r in w.order_items.rows))
w.canvas.render(f"{OUT}/p2_order.png")
S.save(); m, calls = load(keep_cfg=True); app = boot(m)
check("order survives restart", app.settings["order"]["groups"] == ["GPU", "CPU", "FPS", "RAM", "NET"] and app.settings["order"]["items"]["GPU"][0] == "g_mem")
# vertical layout + graph position
app.settings["layout"] = "v"; app.rebuild(); check("vertical layout builds", app.overlay.has_content)
app.settings["order"]["items"]["FPS"] = ["graph", "fps", "avg", "low", "ft"]; app.rebuild(); check("graph first (vertical) builds", app.overlay.canvas is not None)
app.settings["layout"] = "h"; app.rebuild(); check("graph first (horizontal) builds", app.overlay.canvas is not None)

# ---------- 4) move with mouse
m, calls = load(); app = boot(m); w = app.window; S = app.settings; o = app.overlay; w.show(); w.show_page(w.PAGE_DISPLAY); flush()
check("starts click-through", (ctypes.EXSTYLE["ex"] & 0x20) == 0x20)
ctypes.windll.user32.SetWindowLongW.reset_mock()
ok = app.set_moving(True); flush()
check("move mode on, pos=custom seeded", ok and app.moving and o.moving and S["pos"] == "custom" and S["x"] == o.x)
style_calls = ctypes.windll.user32.SetWindowLongW.call_args_list
check("click-through removed in move mode (0x20 cleared)", style_calls and (ctypes.EXSTYLE["ex"] & 0x20) == 0)
Theme_ACC = m.Theme.ACCENT_HI
check("solid panel + accent outline in move mode", o.bg == o.tint and o.top.opts["highlightthickness"] == 2 and o.top.attrs["-alpha"] == S["alpha"] / 100 and o.top.opts["highlightbackground"] == Theme_ACC)
check("drag handlers bound on bar + labels", "<B1-Motion>" in o.top.binds and all("<B1-Motion>" in l.binds for l in o.labels.values()))
check("Done button text", w.canvas.itemcget(w.move_txt, "text") == "Done")
o.top.emit("<ButtonPress-1>", x_root=o.x + 10, y_root=o.y + 5)
o.top.emit("<B1-Motion>", x_root=700, y_root=300); o.top.emit("<ButtonRelease-1>", x_root=700, y_root=300); flush()
check(f"dragged to (~690,295): got ({S['x']},{S['y']})", (S["x"], S["y"]) == (700 - 10, 300 - 5) and o.top.winfo_reqwidth() > 0)
# off-screen drag is clamped
o.top.emit("<ButtonPress-1>", x_root=o.x + 3, y_root=o.y + 3)
o.top.emit("<B1-Motion>", x_root=99999, y_root=99999); o.top.emit("<ButtonRelease-1>", x_root=99999, y_root=99999); flush()
W_, H_ = o.top.winfo_reqwidth(), o.top.winfo_reqheight()
check(f"clamped inside 1920x1080: ({S['x']},{S['y']}) w={W_} h={H_}", S["x"] == 1920 - W_ and S["y"] == 1080 - H_)
o.top.emit("<ButtonPress-1>", x_root=S["x"] + 3, y_root=S["y"] + 3); o.top.emit("<B1-Motion>", x_root=-500, y_root=-500); o.top.emit("<ButtonRelease-1>", x_root=-500, y_root=-500)
check("clamped at top-left", (S["x"], S["y"]) == (0, 0))
o.top.emit("<ButtonPress-1>", x_root=3, y_root=3); o.top.emit("<B1-Motion>", x_root=403, y_root=203); o.top.emit("<ButtonRelease-1>", x_root=403, y_root=203); flush()
ctypes.windll.user32.SetWindowLongW.reset_mock()
o.top.emit("<Button-3>"); flush()
check("right-click ends move mode, click-through back", not app.moving and not o.moving and (ctypes.EXSTYLE["ex"] & 0x20) == 0x20)
check("saved to file", json.load(open(m.Paths.CFG_FILE))["x"] == 400 and json.load(open(m.Paths.CFG_FILE))["pos"] == "custom")
check("segmented shows none selected for a custom position", w.pos_seg.index == -1)
w.canvas.render(f"{OUT}/p2_display.png")
# presets still work, custom stays remembered
app.set_position(2); flush(); check("preset right works", S["pos"] == "right" and o.x == 1920 - o.top.winfo_reqwidth() - m.Theme.MARGIN)
app.set_position(3); flush(); check("custom restores saved spot", (o.x, o.y) == (400, 200))
# saved spot off-screen (resolution change) is pulled back in
S["x"], S["y"] = 5000, 5000; o.invalidate(); o.place(); check("stale off-screen position clamped", o.x <= 1920 - o.top.winfo_reqwidth() and o.y <= 1080 - o.top.winfo_reqheight())
# restart keeps custom spot
S["x"], S["y"] = 400, 200; S.save(); m, calls = load(keep_cfg=True); app = boot(m)
check("restart keeps custom position", (app.overlay.x, app.overlay.y) == (400, 200))
# move mode with nothing to show / closing window ends it
app.settings.show.update({k: False for k in m.Metrics.KEYS}); app.rebuild(); check("move refused with empty overlay", app.set_moving(True) is False)
for k in m.Metrics.KEYS: app.settings.show[k] = True
app.rebuild(); app.window.show(); app.set_moving(True); app.window.hide(); check("closing window ends move mode", not app.moving)
# reset
app.reset_defaults(); flush(); check("reset clears look/bg/order/pos", app.settings["look"] == "dark" and app.settings["pos"] == "left" and app.settings["x"] is None and app.settings["order"] == m.Metrics.default_order())

# ---------- 5) previews / pages
m, calls = load(); app = boot(m); w = app.window; w.show(); w.show_page(4); flush(); w.update_status(); app.window._pick_look(1); flush()
w.canvas.render(f"{OUT}/p2_appearance.png")
for look in ("dark", "glass"):
    m.Overlay.preview(look, "#101010", "#76b900", 480, 208).save(f"{OUT}/prev_{look}.png")
print("errors:", open(m.Paths.LOG_FILE).read() if os.path.exists(m.Paths.LOG_FILE) else "none")
print("FAILED:", check.bad)
