"""v1.17.5 - floating graph overlays (two of them), anti-cheat safe mode, Personalize,
PC check instead of Diagnostics, taskbar icon, About text.

Checked with the real mouse on the author's laptop (start the app, put the cursor on the
overlay's top edge, press, move 300 px left / 200 px down, release): the overlay moved by
exactly that, stayed there, the place was saved, clicks on its body still went through,
and the second overlay was not touched."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

from copy import deepcopy
from lmonitor.engine import Settings, Theme, SafeMode, LibreHardwareHost, SessionRecorder
from lmonitor.backend import Backend

cfg = deepcopy(Settings.DEFAULTS)

# ---- the bug: a dragged overlay jumped back. The place was saved one value at a time
# and the check threw away an x that had no y yet.
b = Backend.__new__(Backend)
b.settings = Settings.__new__(Settings)
b.settings.data = Settings._clean(deepcopy(cfg))
b._sys_t = 0.0
chk("a place saved in one go is kept", b.set_many({"hud_monitor": "primary", "hud_x": 1364, "hud_y": 216, "hud_pos": "custom"})
    and (b.settings["hud_pos"], b.settings["hud_x"], b.settings["hud_y"]) == ("custom", 1364, 216))
chk("unknown keys are refused", b.set_many({"nope": 1}) is False)
b.set_many({"x": 50, "y": 60, "pos": "custom"})
chk("the bar's dragged place is kept too", (b.settings["pos"], b.settings["x"], b.settings["y"]) == ("custom", 50, 60))
ov = read("lmonitor", "qt", "overlay.py")
chk("both overlays and the bar save their place in one go", ov.count("set_many(") == 2 and 'set_setting(p + "x"' not in ov)

# ---- two graph overlays
chk("second overlay has its own settings", all(("hud2_" + k[4:]) in Settings.DEFAULTS for k in cfg if k.startswith("hud_")))
chk("second overlay is off by default, in another corner", cfg["hud2_on"] is False and cfg["hud2_pos"] != cfg["hud_pos"])
c = Settings._clean(dict(deepcopy(cfg), hud2_items=["x", "fps", "fps"], hud2_size="xl", hud2_window=7, hud2_x=5))
chk("second overlay's settings are checked like the first", c["hud2_items"] == ["fps"] and c["hud2_size"] == "m"
    and c["hud2_window"] == 0 and c["hud2_x"] is None)
src = read("lmonitor", "engine.py")
chk("second overlay is loaded from settings.json", 'k.startswith("hud2_")' in src)
b.settings.data = Settings._clean(dict(deepcopy(cfg), hud_on=True, hud2_on=True, hud_window=60, hud2_window=0,
                                       hud_items=["g_use"], hud2_items=["fps"]))
chk("one overlay in real time makes the readings fast", b.hud_realtime() and b.hud_period() == 0.25)
chk("FPS needed when any shown overlay has it", b.hud_wants_fps())
b.settings.data["hud2_on"] = False
chk("a switched-off overlay asks for nothing", not b.hud_realtime() and not b.hud_wants_fps())
b.hud_page_open = True
chk("...except while its settings page shows the preview", b.hud_realtime())
b.hud_page_open = False
app = read("lmonitor", "qt", "app.py")
chk("two overlay windows are made", "for i in range(2):" in app and 'setProperty("slot", i)' in app)
br = read("lmonitor", "qt", "bridge.py")
chk("the page talks to one overlay by number", "def setHudSetting(self, n, key, value)" in br and "def hudStyles" in br)
page = read("lmonitor", "qt", "qml", "pages", "HudPage.qml")
chk("page: pick Graph 1 / Graph 2", '"Graph 1", "Graph 2"' in page and "backend.setHudSetting(page.n" in page)
chk("no move button any more", "Move with mouse" not in page and "setHudMoving" not in br)

# ---- floating: the rule that decides when the window takes the mouse
from lmonitor.qt.overlay import HudHost
h = HudHost.__new__(HudHost)
h.grab = False
W = HudHost.want_grab
chk("mouse on the top edge: takes the mouse", W(h, True, True, False, False, False))
chk("mouse on the body: clicks go through", not W(h, True, False, False, False, False))
chk("top edge while a full-screen game is in front: goes through", not W(h, True, True, False, False, True))
chk("Ctrl anywhere on it: takes the mouse (also over a game)", W(h, True, False, True, False, True))
chk("a drag that started elsewhere and passes over it: ignored", not W(h, True, True, False, True, False))
chk("mouse outside: goes through", not W(h, False, False, False, False, False))
h.grab = True
chk("while being dragged it keeps the mouse, wherever the cursor is", W(h, False, False, False, True, False))
chk("a maximized normal window is not a full-screen game", "fullscreen_app(True)" in ov and "u.IsZoomed(h)" in src)
chk("Qt and Windows are both told about click-through", "setFlag(Qt.WindowTransparentForInput, on)" in ov
    and "click_through_hwnd" in ov)

# ---- anti-cheat safe mode
chk("Warzone / Call of Duty is known", SafeMode.is_protected("cod.exe") and SafeMode.is_protected("COD.EXE")
    and SafeMode.is_protected("cod24-cod.exe"))
chk("anti-cheat helpers are known", SafeMode.is_protected("EasyAntiCheat.exe") and SafeMode.is_protected("BEService.exe"))
chk("normal programs are not", not SafeMode.is_protected("chrome.exe") and not SafeMode.is_protected("") and not SafeMode.is_protected(None))
chk("default is automatic", cfg["safe_mode"] == "auto" and Settings._clean(dict(deepcopy(cfg), safe_mode="x"))["safe_mode"] == "auto")


class FakeComputer:
    closed = 0
    def Close(self): FakeComputer.closed += 1


host = LibreHardwareHost.__new__(LibreHardwareHost)
host.computer, host.cpu_hw, host.cpu_temp, host.cpu_power = FakeComputer(), object(), object(), object()
host.cpu_clocks, host.gpu_hw, host.gpu, host.extra_hw, host._extras_on = [1], object(), {"a": 1}, [1], True
opened = []
host._open = lambda: opened.append(1)
host.suspend()
chk("safe mode closes the sensor library (the driver is not used)", FakeComputer.closed == 1 and host.computer is None
    and host.cpu_hw is None and host.cpu_temp is None and host.suspended)
host.suspend()
chk("closing twice does nothing", FakeComputer.closed == 1)
host.resume()
chk("leaving safe mode opens it again", opened == [1] and not host.suspended)


class FakeSessions:
    safe = False


b.host, b.sessions = host, FakeSessions()
b.settings.data["safe_mode"] = "always"
b.safe_active, b._safe_t = False, 0.0
chk("'always' switches it on", b.safe_tick(100.0) is True and host.suspended and b.sessions.safe is True)
chk("checked at most every 5 s", b.safe_tick(101.0) is True)
b.settings.data["safe_mode"] = "off"
chk("'off' switches it off again", b.safe_tick(110.0) is False and not host.suspended and b.sessions.safe is False)
chk("game sessions do not look at other programs in safe mode", "and not self.safe:" in src and SessionRecorder.safe is False)
chk("the CPU card says why the temperature is missing", '"Paused by anti-cheat safe mode"' in read("lmonitor", "backend.py"))
chk("nothing is hidden or disguised (plain statement in the code)", "Nothing is hidden or disguised" in src)

# ---- Personalize
chk("10 themes", len(Theme.UI_THEMES) == 10)
chk("17 accent choices incl. custom", len(Theme.UI_ACCENTS) == 17 and Theme.UI_ACCENTS[-1][0] == "custom")
chk("custom accent from a hue", Theme.hue_hex(0).startswith("#") and Theme.hue_hex(0) != Theme.hue_hex(180) and len(Theme.hue_hex(359)) == 7)
c = Settings._clean(dict(deepcopy(cfg), ui_scale=300, ui_radius="x", ui_font="Comic", ui_hue=999, ui_accent="custom"))
chk("bad look values fall back", (c["ui_scale"], c["ui_radius"], c["ui_font"], c["ui_hue"]) == (100, "round", "Segoe UI", 359)
    and c["ui_accent"] == "custom")
b.settings.data = Settings._clean(dict(deepcopy(cfg), ui_scale=120, ui_radius="sharp", ui_font="Tahoma", ui_accent="custom", ui_hue=200))
st = b.ui_style()
chk("style carries size, corners, font and the custom color", st["zoom"] == 1.2 and st["radius"] == 4
    and st["font"] == "Tahoma" and st["accent"] == Theme.hue_hex(200))
main = read("lmonitor", "qt", "qml", "Main.qml")
chk("the window background follows the theme (was a fixed dark color)", '"#0a0a0d"' not in main and "color: Tokens.bg0" in main)
chk("interface size scales the whole window", "Scale { xScale: win.zoom; yScale: win.zoom }" in main)
import re
left = []
for dp, _, fs in _os.walk(_os.path.join(ROOT, "lmonitor", "qt", "qml")):
    for f in fs:
        if f.endswith(".qml") and f != "Tokens.qml" and re.search(r'"#(26262c|1e1e23|2a2a31)"', open(_os.path.join(dp, f), encoding="utf-8").read()):
            left.append(f)
chk("no fixed dark line / bar colors left (light themes)", not left)

# ---- PC check instead of Diagnostics
chk("Diagnostics page is gone from the menu", "DiagnosticsPage.qml" not in main and '"PC check"' in main)
chk("its file is removed", not _os.path.exists(_os.path.join(ROOT, "lmonitor", "qt", "qml", "pages", "DiagnosticsPage.qml")))
rp = read("lmonitor", "qt", "qml", "pages", "ReportsPage.qml")
chk("the scan and its findings live in PC check", "tools.repScan()" in rp and "tools.diag.issues" in rp)
chk("scan then report", "def repScan" in read("lmonitor", "qt", "tools.py"))

# ---- taskbar icon + About
chk("built exe keeps Windows' own taskbar identity (icon, pinning)", 'if not getattr(sys, "frozen", False):\n            try:\n                cls.shell32.SetCurrentProcessExplicitAppUserModelID' in src)
chk("main window gets the icon", "engine.rootObjects()[0].setIcon(ico)" in app)
about = read("lmonitor", "qt", "qml", "pages", "About.qml")
chk("About: the author's text", "Lmonitor is a overly and system monitor for windows." in about
    and "Made by a Claude and new developer named unrealhamed." in about and "github.com/unrealhamed/Lmonitor" in about)
fa = read("lmonitor", "qt", "qml", "Lmonitor", "fa.js")
for s in ("Anti-cheat safe mode", "Graph 2", "PC check", "INTERFACE AND TEXT SIZE", "Made by a Claude and new developer named unrealhamed."):
    chk("Persian text for '%s'" % s[:30], '"%s":' % s in fa)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
