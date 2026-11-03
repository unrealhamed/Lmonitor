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
m = load(); P = m.Profiles
# ---- pure logic
cs, bl, dt = (P.density_show(k) for k in ("compact", "balanced", "detailed"))
chk("density presets are real show-flag sets", sum(cs.values()) == 4 and cs["fps"] and cs["g_use"] and not cs["g_temp"] and sum(bl.values()) == 7 and all(dt.values()))
chk("density detected from the flags, custom otherwise", P.density_of(cs) == "compact" and P.density_of(dt) == "detailed" and P.density_of(dict(cs, g_temp=True)) == "")
# ---- app
app = boot(m); w = app.window; S = app.settings
app.schedule = lambda key, fn, *a: fn()
S.reset()
w.show(); w.show_page(w.PAGE_PROFILES); flush()
app.set_density("compact"); flush()
chk("compact density changes what the bar shows and is remembered", S.show["g_use"] and not S.show["g_temp"] and P.density_of(S.show) == "compact")
app.set_density("detailed")
chk("detailed shows everything", all(S.show.values()))
app.set_value_color("amber"); flush()
chk("value color applied to the bar", S["value_color"] == "amber" and app.overlay.value_hex() == "#ffd166")
app.set_value_color("accent")
chk("accent value color follows the app accent", app.overlay.value_hex() == m.Theme.ACCENT)
app.set_value_color("white")
# put() maps normal color, keeps warning colors
ov = app.overlay; ov.labels["g_use"] = type("L", (), {"config": lambda s, **k: ov.__dict__.setdefault("_c", []).append(k)})()
app.set_value_color("cyan")
ov.labels["g_use"] = type("L", (), {"config": lambda s, **k: ov.__dict__.__setitem__("_c", k)})()
ov.put("g_use", "5%"); c1 = ov._c["fg"]
ov.put("g_use", "99%", "#ff0000"); c2 = ov._c["fg"]
chk("normal values use the chosen color, warnings keep theirs", c1 == "#7fe3ff" and c2 == "#ff0000")
app.set_value_color("white")
# old settings files that still hold saved profiles load fine and drop them
raw = {"profiles": [{"name": "x"}], "profile": "x", "value_color": "cyan"}
os.makedirs(os.path.dirname(m.Paths.CFG_FILE), exist_ok=True)
json.dump(raw, open(m.Paths.CFG_FILE, "w")); S3 = m.Settings()
chk("old settings with profiles still load; value color kept", S3["value_color"] == "cyan" and "profiles" not in S3.data)
chk("profile feature is gone from the app", not hasattr(app, "profile_save_new") and not hasattr(m, "ProfileList"))
app.set_value_color("white"); S.save()
S2 = m.Settings(); chk("value color survives a restart", S2["value_color"] == "white")
# window
w.show_page(w.PAGE_PROFILES); w._fill_profiles(); flush()
chk("profiles page has only density + value colors", not hasattr(w, "pf_list") and not hasattr(w, "pf_entry") and len(w.pf_rings) == len(m.Theme.VALUE_COLORS))
w.canvas.render(f"{OUT}/p15_profiles.png")
chk("12 menu rows... menu still fits", all((w.show_page(i), w.nav.bottom <= 400)[1] for i in range(len(w.PAGES))))
print(f"phase15: {ok} ok, {bad} failed")
