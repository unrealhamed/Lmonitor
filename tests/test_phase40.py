"""v1.19.0 - new design ("Slate"): light / dark, simpler Personalize and overlay look, new Home.

What changed and why:
- 10 app themes, 17 accents + an own hue, 4 sizes, 3 corner styles and 6 fonts -> Light or Dark,
  6 accents, 3 sizes. Old settings move over safely (light themes -> Light, the rest -> Dark;
  accents to the nearest new one; 90 % -> 100 %, 120 % -> 125 %).
- The overlay bar has one look: dark and see-through, only the opacity is set. Liquid glass
  (Windows blur behind a game window), 10 background colors, 6 value colors and the
  regular / bold choices were removed.
- Home was redesigned: four cards, the chart, Right now, Network (adapter, since start-up)
  and This PC (up time, battery, power plan, PC check score)."""
import os as _os, sys, json, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, _os.path.join(ROOT, "tests", "stubs"))

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

import lmonitor.engine as E
T, S = E.Theme, E.Settings

# ---- colors
for m in ("dark", "light"):
    for a in T.UI_ACCENTS:
        c = T.ui_colors(m, a[0])
        if not all(k in c for k in ("bg0", "bg1", "card", "raised", "line", "lineStrong", "text", "sub", "dim",
                                     "accent", "accentHover", "accentText", "warn", "danger", "info", "light")):
            chk("all colors for %s / %s" % (m, a[0]), False)
chk("every mode x accent gives every color", True)
def lum(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda x: x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
for m in ("dark", "light"):
    c = T.ui_colors(m, "mint")
    chk("%s: body text readable (%.1f:1)" % (m, contrast(c["text"], c["card"])), contrast(c["text"], c["card"]) >= 7)
    chk("%s: secondary text readable (%.1f:1)" % (m, contrast(c["sub"], c["card"])), contrast(c["sub"], c["card"]) >= 4.5)
    for a in T.UI_ACCENTS:
        cc = T.ui_colors(m, a[0])
        if contrast(cc["accentText"], cc["accent"]) < 4.5:
            chk("%s / %s: text on the accent readable (%.1f:1)" % (m, a[0], contrast(cc["accentText"], cc["accent"])), False)
chk("text on every accent button readable (4.5:1 or more)", True)

# ---- old settings move over
def load_old(raw):
    p = E.Paths.CFG_FILE
    _os.makedirs(_os.path.dirname(p), exist_ok=True)
    json.dump(raw, open(p, "w", encoding="utf-8"))
    return S()
s = load_old({"ui_theme": "day", "ui_accent": "teal", "ui_scale": 120, "ui_radius": "sharp", "ui_font": "Tahoma",
              "ui_hue": 40, "look": "glass", "bg": "wine", "value_color": "amber", "weight": "normal", "language": "fa"})
chk("old light theme -> Light, teal -> Mint, 120 % -> 125 %", (s["ui_mode"], s["ui_accent"], s["ui_scale"]) == ("light", "mint", 125))
chk("old overlay look -> the one look", (s["look"], s["bg"], s["value_color"], s["weight"], s["label_weight"])
    == ("dark", "black", "white", "bold", "bold"))
chk("other settings kept", s["language"] == "fa")
chk("removed keys are not carried on", not any(k in s.data for k in ("ui_theme", "ui_radius", "ui_font", "ui_hue")))
s = load_old({"ui_theme": "crimson", "ui_accent": "custom", "ui_scale": 90})
chk("old dark theme -> Dark, own hue -> Mint, 90 % -> 100 %", (s["ui_mode"], s["ui_accent"], s["ui_scale"]) == ("dark", "mint", 100))
s = load_old({"ui_mode": "light", "ui_accent": "violet"})
chk("new settings read back", (s["ui_mode"], s["ui_accent"]) == ("light", "violet"))
s.save(); chk("saved file has no old keys", "ui_theme" not in json.load(open(E.Paths.CFG_FILE, encoding="utf-8")))

# ---- Home data
from lmonitor.backend import Backend
b = Backend()
b.sample(); time.sleep(0.3); b.sample()
d = b.dashboard(0)
pc = d.get("pc_info", {})
chk("This PC: up time, battery, power plan, score", all(k in pc for k in ("uptime", "battery", "plan", "score", "windows"))
    and pc["uptime"] != "")
chk("Network: adapter, link speed, since start-up", all(k in d["network"] for k in ("adapter", "link", "since_boot")))
chk("Storage card: total size", d["cards"]["disk"].get("total_gb") is None or d["cards"]["disk"]["total_gb"] > 0)
chk("the power plan is read on its own thread", "BackgroundReader(self._read_plan, 300.0" in read("lmonitor", "backend.py"))
b.settings.data.update(ui_mode="light", ui_accent="blue", ui_scale=110, language="fa")
b.reset_settings()
chk("'Reset overlay settings' keeps the window's look and language",
    (b.settings["ui_mode"], b.settings["ui_accent"], b.settings["ui_scale"], b.settings["language"]) == ("light", "blue", 110, "fa"))

# ---- the window
qml = lambda *p: read("lmonitor", "qt", "qml", *p)
pers, ovl, main, dash = qml("pages", "PersonalizePage.qml"), qml("pages", "OverlayPage.qml"), qml("Main.qml"), qml("pages", "Dashboard.qml")
chk("Personalize: language, start with Windows, light / dark, accent, size - nothing else",
    all(x in pers for x in ('"ui_mode"', '"ui_accent"', '"ui_scale"', "setAutostart", '"language"'))
    and not any(x in pers for x in ("ui_theme", "ui_radius", "ui_font", "ui_hue", "uiThemes", "hueHex")))
chk("Overlay look: opacity only", '"alpha"' in ovl and not any(x in ovl for x in ('"look"', "backgrounds", "valueColors", '"weight"', "glassOk")))
chk("no glass code left", not any(x in read("lmonitor", "engine.py") for x in ("blur_hwnd", "round_hwnd", "blur_supported"))
    and "glassOk" not in read("lmonitor", "qt", "bridge.py"))
chk("menu items keep their order, each with an icon", [l for l in ("Home", "Graphs", "Hardware", "Overlay", "Graph overlay", "Sessions",
    "Optimizer", "Storage", "PC check", "Personalize", "About") if ('label: "%s", icon:' % l) in main] == ["Home", "Graphs", "Hardware",
    "Overlay", "Graph overlay", "Sessions", "Optimizer", "Storage", "PC check", "Personalize", "About"])
chk("icons from Windows' own icon font (no image files)", "Segoe Fluent Icons" in qml("Lmonitor", "Tokens.qml")
    and "Segoe MDL2 Assets" in qml("Lmonitor", "Tokens.qml"))
chk("Home: four cards, chart, right now, network, this PC", dash.count("MetricTile {") == 4 and "GraphChart {" in dash
    and '"Right now"' in dash and '"This PC"' in dash and "Usage history" in dash)
gauge = qml("components", "Gauge.qml")
chk("gauge number centered on the gauge", "anchors.horizontalCenter: parent.horizontalCenter" in gauge
    and "anchors.verticalCenter: parent.verticalCenter" in gauge)
for old in ("HwCard", "Ring", "StatCard", "UsageBar", "PerfChart", "Dot"):
    if _os.path.exists(_os.path.join(ROOT, "lmonitor", "qt", "qml", "components", old + ".qml")):
        chk("unused component removed: " + old, False)
chk("unused old components removed", True)
fa = qml("Lmonitor", "fa.js")
need = ("This PC", "Up time", "Battery", "Power plan", "Light", "Dark", "Interface size", "Usage history", "Since start-up",
        "A new look", "Light and dark", "A new Home", "Fewer, better settings")
miss = [k for k in need if ('"%s":' % k) not in fa]
chk("Persian texts %s" % (miss or ""), not miss)
wn = E.WhatsNew.pending("1.18.6", "1.19.0")
art = qml("components", "WhatsNewArt.qml")
chk("What's new 1.19.0 with its own animations", wn and wn["version"] == "1.19.0"
    and all(('art.kind === "%s"' % s["art"]) in art for s in wn["slides"]))
chk("version 1.19.0 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 19, 0))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
