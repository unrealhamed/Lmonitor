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
d = b.ui_style("default", "auto")
chk("default theme = Qt palette + green", d["bg0"] == "#08080a" and d["accent"] == "#1fd18b")
for t in ("night", "day", "aurora"):
    u = b.ui_style(t, "blue")
    chk(t + " theme complete + blue accent", all(k in u for k in ("bg0","bg1","card","cardHi","line","text","sub","dim","accent","accentText","light")))
chk("day is light", b.ui_style("day", "auto")["light"] is True)
chk("aurora auto accent", b.ui_style("aurora", "auto")["accent"] == "#2ee6c5")
b.set_setting("ui_theme", "night"); b.set_setting("ui_accent", "pink")
chk("settings stored (shared with Tk)", b.settings["ui_theme"] == "night" and b.settings["ui_accent"] == "pink")
print("phase20: %d ok, %d failed" % (ok, bad))
