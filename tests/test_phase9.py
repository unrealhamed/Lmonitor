import os as _os
import sys, io, contextlib, time, os, json
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

m = load()
app = boot(m); S = app.settings; o = app.overlay; rv = app.reveal
chk("defaults: always visible, 5 s", S["show_mode"] == "always" and S["hotkey_secs"] == 5)
chk("always mode: bar visible and in place", app.shown and o.slide == 1.0 and app.overlay_visible())
chk("F9 does nothing in always mode", rv.press() is False and not rv.active)

# settings validation
S["show_mode"] = "x"; S["hotkey_secs"] = 7; S.save()
m2 = load(keep_cfg=True); a2 = m2.Settings()
chk("bad saved values fall back", a2["show_mode"] == "always" and a2["hotkey_secs"] == 5)
S["show_mode"] = "always"; S["hotkey_secs"] = 5

# switching to F9 mode hides the bar until the key is pressed
app.set_show_mode(1); flush()
chk("F9 mode: hidden until pressed", S["show_mode"] == "hotkey" and not rv.active and not app.overlay_visible())
chk("hidden bar is withdrawn", o.top.state() in ("withdrawn", "") if hasattr(o.top, "state") else True)
# geometry: above the screen at 0, in place at 1
o.top.update_idletasks()
w, h = o.top.winfo_reqwidth(), o.top.winfo_reqheight()
o.place(); mon = o.monitor()
o.slide = 0.0; y0 = o._draw_y(h); o.slide = 1.0; y1 = o._draw_y(h); o.slide = 0.5; ym = o._draw_y(h)
chk("slide 0 = fully above the display", y0 + h <= mon.y)
chk("slide 1 = its place, 0.5 in between", y1 == o.y and y0 < ym < y1)

# state machine with a fake clock
rv._loop = lambda: None
hid = []; orig_hide = o.hide; o.hide = lambda: (hid.append(1), orig_hide())
S["hotkey_secs"] = 3
t = 5000.0
chk("press starts the slide", rv.press(t) is True and rv.state == "in" and app.overlay_visible())
rs = []
for i in range(40):
    t += 0.02; rv.step(t); rs.append(rv.r)
chk("slides in smoothly (monotonic, ~0.35 s)", rs == sorted(rs) and rv.state == "shown" and rv.r == 1.0 and abs(rs.index(1.0) * 0.02 - 0.35) < 0.05)
t += 2.0; rv.step(t)
chk("stays 3 s", rv.state == "shown")
rv.press(t)   # extends
t += 2.0; rv.step(t)
chk("F9 again extends the time", rv.state == "shown")
t += 1.2; rv.step(t)
chk("then slides out", rv.state == "out")
rs = []
for i in range(40):
    t += 0.02; rv.step(t); rs.append(rv.r)
chk("slides up and hides again", rv.state == "hidden" and rs == sorted(rs, reverse=True) and hid)
# press during the slide-out reverses it
rv.press(t); t += 0.5; rv.step(t); t += 3.5; rv.step(t)
chk("(reached out state)", rv.state == "out")
t += 0.1; rv.step(t); r_mid = rv.r
rv.press(t)
chk("press during slide-out slides back in", rv.state == "in" and 0 < r_mid < 1)
rv.reset(); o.slide = 0.0

# 5 and 10 seconds via the setting
app.set_hotkey_secs(2); chk("10 s setting", S["hotkey_secs"] == 10)
app.set_hotkey_secs(0); chk("3 s setting", S["hotkey_secs"] == 3)
app.set_hotkey_secs(1); chk("5 s setting", S["hotkey_secs"] == 5)

# key polling: one press = one show, even when the key is held
presses = []
rv.press = lambda *a: presses.append(1)
keys = [False, True, True, True, False, True]
for k in keys:
    m.WinApi.key_down = staticmethod(lambda vk, k=k: k); rv.poll()
chk("polling reacts to presses, not to holding", len(presses) == 2)
chk("F9 virtual-key code", rv.VK_F9 == 0x78)
del rv.press

# moving the bar shows it regardless of the mode
rv.reset()
app.settings["pos"] = "custom"; app.settings["x"] = 100; app.settings["y"] = 100
app.set_moving(True); flush()
chk("move mode shows the bar even in F9 mode", app.overlay_visible() and o.slide == 1.0)
app.set_moving(False); flush()
chk("after move it waits for F9 again", not app.overlay_visible())

# back to always
app.set_show_mode(0); flush()
chk("back to always visible", app.overlay_visible() and o.slide == 1.0)
chk("settings saved", S["show_mode"] == "always")

# UI
w = app.window; w.show(); w.show_page(w.PAGE_DISPLAY); flush()
w.canvas.render(f"{OUT}/p9_display.png")
w.mode_seg.select(1); app.set_show_mode(1); flush()
w.canvas.render(f"{OUT}/p9_display_f9.png")
chk("display page has the new card", w.mode_seg is not None and w.secs_seg is not None)
called = []
app.try_reveal = lambda: called.append(1)
w.canvas.event_generate if False else None
# GitHub link
opened = []
m.webbrowser.open = lambda u: opened.append(u)
w.open_github()
chk("GitHub link opens the project page", opened == ["https://github.com/unrealhamed/Lmonitor"])
w.show_page(0); flush(); w.canvas.render(f"{OUT}/p9_side.png")
w._gh_hover(True); w._gh_hover(False)
chk("hover works", True)
for i in range(len(w.PAGES)): w.show_page(i); flush()
chk("all pages open", True)
print(f"phase9: {ok} ok, {bad} failed")
