"""v1.17.2 - graph overlay (HUD): settings, data, window and page."""
import os as _os, sys, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

from copy import deepcopy
from lmonitor.engine import Hud, Settings

# ---- settings are always valid
cfg = deepcopy(Settings.DEFAULTS)
c = Settings._clean(deepcopy(cfg))
chk("off by default (nothing new appears over games after an update)", c["hud_on"] is False)
chk("default charts are known", all(k in Hud.ITEMS for k in c["hud_items"]))
bad_cfg = deepcopy(cfg)
bad_cfg.update(hud_items=["fps", "nope", "fps", "g_temp", "c_temp", "g_use", "c_use", "r_use", "g_pow"],
               hud_pos="middle", hud_size="xl", hud_layout=3, hud_style=None, hud_theme="pink",
               hud_alpha=500, hud_window=7, hud_mode="sometimes", hud_x="1", hud_y=4,
               hud_monitor="")
c = Settings._clean(bad_cfg)
chk("unknown / repeated charts dropped, at most 6", c["hud_items"] == ["fps", "g_temp", "c_temp", "g_use", "c_use", "r_use"])
chk("bad position -> top right", c["hud_pos"] == "tr")
chk("bad size / layout / style / theme -> defaults",
    (c["hud_size"], c["hud_layout"], c["hud_style"], c["hud_theme"]) == ("m", "v", "hud", "neon"))
chk("opacity kept between 0 and 100", c["hud_alpha"] == 100)
chk("bad time span -> real time", c["hud_window"] == 0)
chk("bad visibility -> always", c["hud_mode"] == "always")
chk("half a saved position is dropped", c["hud_x"] is None and c["hud_y"] is None)
chk("empty monitor -> primary", c["hud_monitor"] == "primary")
c = Settings._clean(dict(deepcopy(cfg), hud_items=[]))
chk("never zero charts", len(c["hud_items"]) >= 1)
c = Settings._clean(dict(deepcopy(cfg), hud_pos="custom"))
chk("custom without a saved place -> top right", c["hud_pos"] == "tr")
c = Settings._clean(dict(deepcopy(cfg), hud_on=True, hud_alpha=0, hud_window=60))
chk("good values are kept", c["hud_on"] and c["hud_alpha"] == 0 and c["hud_window"] == 60)
src = read("lmonitor", "engine.py")
chk("hud settings are loaded from settings.json", '"hud_items",' in src.split("def _load")[1].split("def _clean")[0])

# ---- the data the overlay draws (Backend.hud_view without hardware)
from lmonitor.backend import Backend
from lmonitor.graphs import GraphHistory


class FakeFps:
    alive = True
    def __init__(self, st): self.st = st
    def recent_stats(self, since, fps_window=1.0): return self.st


class FakeTel:
    interval = 1.0
    snap = {"g_temp": 61.0, "c_temp": None, "g_use": 97.0, "g_pow": 80.0}


def make_backend(items, window=60):
    b = Backend.__new__(Backend)             # no sensors: only what the HUD needs
    b.settings = Settings.__new__(Settings)
    b.settings.data = Settings._clean(dict(deepcopy(cfg), hud_items=items, hud_window=window))
    b.telemetry = FakeTel()
    b.hud_hist = GraphHistory(keys=Backend.HUD_KEYS, keep=330)
    b._hud_t, b._hud_live = 0.0, {}
    return b


b = make_backend(["fps", "ft", "g_temp", "c_temp", "g_pow"])
b.fps = FakeFps((144.4, 9.5))
now = time.time()
for i in range(70):                           # one reading a second for 70 s
    FakeTel.snap["g_temp"] = 50.0 + i * 0.1
    b.hud_tick(now - 70 + i)
v = b.hud_view()
items = {it["key"]: it for it in v["items"]}
chk("one entry per chosen chart, in order", [it["key"] for it in v["items"]] == ["fps", "ft", "g_temp", "c_temp", "g_pow"])
chk("FPS text is the live value", items["fps"]["text"] == "144")
chk("frame time: worst frame, one decimal", items["ft"]["text"] == "9.5")
chk("chart has the visible points + the ones kept outside", len(items["fps"]["series"]) == v["points"] + v["extra"])
chk("FPS line comes from the readings", items["fps"]["series"][-1] == 144.4)
chk("temperature scale is 0-100", items["g_temp"]["max"] == 100)
chk("temperature text = live reading", items["g_temp"]["text"] == "56.9" or items["g_temp"]["text"] == "57")
chk("missing sensor shows -- and no line (never made up)", items["c_temp"]["text"] == "--"
    and all(x is None for x in items["c_temp"]["series"]) and items["c_temp"]["lo"] == "--")
chk("power scale is a round number above the data", items["g_pow"]["max"] in (100, 150) and items["g_pow"]["max"] >= 80)
chk("FPS scale fits 144 fps", items["fps"]["max"] >= 144)
chk("each chart has a theme color", all(it["color"].startswith("#") for it in v["items"]))
chk("lo / hi are real readings of the span", items["g_temp"]["lo"] == "51" and items["g_temp"]["hi"] == "57")
b2 = make_backend(["fps", "ft"])
b2.fps = FakeFps(None)
b2.hud_tick(now)
v = b2.hud_view()
chk("no game in front: FPS is --", v["items"][0]["text"] == "--" and v["items"][1]["text"] == "--")
chk("nice max: 87 -> 100", Backend._nice_max([87], 10) == 100)
chk("nice max: 230 W -> 250 (round number)", Backend._nice_max([230], 10) in (250, 300))
chk("nice max: floor kept for small numbers", Backend._nice_max([3], 60) == 60)
# ---- the window and its host
ov = read("lmonitor", "qt", "overlay.py")
chk("graph overlay host exists, F10 toggles it", "class HudHost" in ov and "VK_F10" in ov)
chk("click-through flags are set", ov.split("class HudHost")[1].count("WindowTransparentForInput") >= 2)
win = read("lmonitor", "qt", "qml", "HudWindow.qml")
chk("window size comes from the settings (never from the numbers)",
    "width: hudView.implicitWidth" in win)
hud = read("lmonitor", "qt", "qml", "components", "GraphHud.qml")
size_part = hud.split("implicitWidth:")[1].split("\n")[0] + hud.split("implicitHeight:")[1].split("\n")[0]
chk("HUD size depends on settings only", "info" not in size_part and "series" not in size_part)
chk("no frame-rate animation in the HUD (throttled clock)", "FrameAnimation" not in hud and "Clock." not in hud)
br = read("lmonitor", "qt", "bridge.py")
chk("HUD data once per reading (not per loop)", "if b.hud_tick():" in br)
chk("PresentMon starts when the HUD shows FPS", "hud and b.hud_wants_fps()" in br)
app = read("lmonitor", "qt", "app.py")
chk("app loads the graph overlay window", "HudWindow.qml" in app and "HudHost" in app)
main = read("lmonitor", "qt", "qml", "Main.qml")
chk("page in the side menu", '"pages/HudPage.qml"' in main)
fa = read("lmonitor", "qt", "qml", "Lmonitor", "fa.js")
for s in ("Graph overlay", "Gaming HUD", "F10 shows / hides", "BACKGROUND OPACITY", "Frame time"):
    chk("Persian text for '%s'" % s, '"%s":' % s in fa)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
