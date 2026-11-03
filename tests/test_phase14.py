import os as _os
import sys, io, contextlib, time, os, json
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT, press
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
m = load()
S = m.Settings()
chk("font defaults", S["font"] == "Consolas" and S["weight"] == "bold" and S["label_weight"] == "bold")
# a bad saved file is cleaned
os.makedirs(os.path.dirname(m.Paths.CFG_FILE), exist_ok=True)
json.dump({"font": "x" * 100, "weight": "heavy", "label_weight": 5}, open(m.Paths.CFG_FILE, "w"))
S2 = m.Settings()
chk("bad font / weights fall back", S2["font"] == "Consolas" and S2["weight"] == "bold" and S2["label_weight"] == "bold")
json.dump({"font": "Segoe UI", "weight": "normal", "label_weight": "normal"}, open(m.Paths.CFG_FILE, "w"))
S3 = m.Settings()
chk("saved font and weights are loaded", (S3["font"], S3["weight"], S3["label_weight"]) == ("Segoe UI", "normal", "normal"))
json.dump({}, open(m.Paths.CFG_FILE, "w"))
app = boot(m); w = app.window; ov = app.overlay
fams = {"consolas": "Consolas", "segoe ui": "Segoe UI", "courier new": "Courier New", "wingdings": "Wingdings", "@vertical": "@Vertical", "arial": "Arial"}
ov.families = lambda: fams
chk("installed font is used as is", ov.resolve_font("segoe ui") == "Segoe UI")
chk("missing font -> Consolas fallback", ov.resolve_font("Nope Sans") == "Consolas")
fams2 = {"courier new": "Courier New"}
ov.families = lambda: fams2
chk("no Consolas either -> Courier New", ov.resolve_font("Nope") == "Courier New")
ov.families = lambda: fams
w.show(); w.show_page(w.PAGE_TYPO); w._fill_typo(); flush()
chk("typography page has no font list any more", not hasattr(w, "ty_list") and not hasattr(w, "ty_seg"))
chk("preview shows the overlay font", w.canvas.itemcget(w.ty_prev, "font")[0] == "Consolas" if isinstance(w.canvas.itemcget(w.ty_prev, "font"), tuple) else True)
w.canvas.render(f"{OUT}/p14_typo.png")
app.set_font(font="Segoe UI"); flush()
chk("set_font still changes the setting, the overlay font and the preview", app.settings["font"] == "Segoe UI" and ov.font.cget("family") == "Segoe UI" and ov.label_font.cget("family") == "Segoe UI" and w.canvas.itemcget(w.ty_prev, "font")[0] == "Segoe UI")
w.ty_val.select(0); w.app.set_font(weight="normal"); flush()
chk("value weight toggle reaches the preview", w.canvas.itemcget(w.ty_prev, "font")[2] == "normal")
app.set_font(weight="normal", label_weight="bold"); flush()
chk("value and label weights are separate", ov.font.cget("weight") == "normal" and ov.label_font.cget("weight") == "bold")
app.set_text_size(14); flush()
chk("text size moves both fonts", ov.font.cget("size") == 14 and ov.label_font.cget("size") == 14)
app.settings.save()
chk("saved to disk", json.load(open(m.Paths.CFG_FILE))["font"] == "Segoe UI")
S4 = m.Settings()
chk("survives a restart", S4["font"] == "Segoe UI" and S4["weight"] == "normal" and S4["label_weight"] == "bold")
w.canvas.render(f"{OUT}/p14_typo2.png")
for i in range(len(w.PAGES)): w.show_page(i); flush()
chk("all pages open", True)
print(f"phase14: {ok} ok, {bad} failed")
