import os as _os
import sys, io, contextlib, time, json
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "stubs"))
sys.modules["tkinter"] = None
import lmonitor.engine as m
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
sys.modules["tkinter"] = None
from lmonitor.backend import Backend
from lmonitor import engine as E
b = Backend()
b.settings.data["show"] = {k: True for k in E.Metrics.KEYS}
chk("density detailed detected", b.density() == "detailed")
chk("set_density compact", b.set_density("compact") and b.density() == "compact")
chk("set_density balanced", b.set_density("balanced") and b.density() == "balanced")
chk("unknown density refused", not b.set_density("x"))
b.set_show("fps", False)
chk("manual change -> custom", b.density() == "")
# 1.19: one design ("Slate") in two modes
d = b.ui_style("dark", "mint")
chk("dark mode + mint", d["bg0"] == "#0E1014" and d["accent"] == "#2DD4A0" and d["light"] is False)
for m in ("dark", "light"):
    u = b.ui_style(m, "blue")
    chk(m + " mode complete + blue accent", all(k in u for k in ("bg0","bg1","card","raised","line","lineStrong","text","sub",
                                                             "dim","accent","accentHover","accentText","warn","danger","info","light")))
chk("light mode is light, accent darker for white", b.ui_style("light", "mint")["light"] is True
    and b.ui_style("light", "mint")["accent"] == "#047857")
b.set_setting("ui_mode", "light"); b.set_setting("ui_accent", "pink")
chk("settings stored", b.settings["ui_mode"] == "light" and b.settings["ui_accent"] == "pink")
b.set_setting("ui_mode", "sepia"); b.set_setting("ui_accent", "gold")
chk("unknown mode / accent fall back", b.settings["ui_mode"] == "dark" and b.settings["ui_accent"] == "mint")
print("phase20: %d ok, %d failed" % (ok, bad))
