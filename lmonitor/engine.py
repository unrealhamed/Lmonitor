"""Lmonitor engine: everything that reads the PC and keeps state.

No window code lives here. The Qt window (lmonitor/qt) uses these classes.
Dependency rule: the engine never imports a UI module.
"""
import atexit
import ctypes
import functools
import math
import json
import os
import re
import sqlite3
import subprocess
import sys
import textwrap
import threading
import time
import traceback
import webbrowser
import zlib
from collections import deque, namedtuple
from copy import deepcopy
from ctypes import wintypes

import clr
import psutil

try:
    import pynvml
except Exception:
    pynvml = None




# =============================================================== Paths
class Paths:
    # The DLLs, PresentMon and the icon live in the project folder (next to
    # build_qt.bat), one level above this package; in a built EXE, in _MEIPASS.
    HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    APPDATA = os.environ.get("APPDATA", HERE)
    CFG_DIR = os.path.join(APPDATA, "Lmonitor")
    OLD_CFG_DIR = os.path.join(APPDATA, "SystemMonitor")  # before the rename
    CFG_FILE = os.path.join(CFG_DIR, "settings.json")
    LOG_FILE = os.path.join(CFG_DIR, "error.log")
    LHM_DLL = os.path.join(HERE, "LibreHardwareMonitorLib.dll")
    PRESENTMON = os.path.join(HERE, "PresentMon.exe")
    PAWNIO_SETUP = os.path.join(HERE, "PawnIO_setup.exe")  # optional, bundled
    ICON = "Lmonitor.ico"

    @classmethod
    def migrate(cls):
        """Copy the settings of the old "SystemMonitor" folder once."""
        old = os.path.join(cls.OLD_CFG_DIR, "settings.json")
        if os.path.exists(old) and not os.path.exists(cls.CFG_FILE):
            try:
                os.makedirs(cls.CFG_DIR, exist_ok=True)
                with open(old, "rb") as a, open(cls.CFG_FILE, "wb") as b:
                    b.write(a.read())
            except Exception:
                pass


# =============================================================== Theme
class Theme:
    # ---- overlay
    BG = "#101010"
    WHITE = "#ffffff"
    YELLOW = "#ffd400"
    RED = "#ff3b30"
    DARKRED = "#b00020"
    GRAY = "#b0b0b0"
    NVIDIA_GREEN = "#76b900"
    AMD_ORANGE = "#f26a21"
    INTEL_BLUE = "#2a9df4"
    OVERLAY_FONT = "Consolas"
    MARGIN = 20             # gap to the screen edge (left / right)
    GRAPH_POINTS = 300      # frames shown in the frametime graph
    GRAPH_W, GRAPH_H = 160, 22
    GRAPH_TOP_MS = 50.0     # top of the graph in milliseconds
    GRAPH_SS = 3            # smoothing quality of the graph

    # ---- overlay backgrounds: (key, menu name, color); None = from the accent
    OVERLAY_BGS = (("black", "Black", "#101010"),
                   ("graphite", "Graphite", "#1b1d23"),
                   ("slate", "Slate", "#232a35"),
                   ("midnight", "Midnight", "#0e1526"),
                   ("ocean", "Ocean", "#0b2230"),
                   ("forest", "Forest", "#0f1f17"),
                   ("wine", "Wine", "#24101a"),
                   ("violet", "Violet", "#1c1233"),
                   ("ember", "Ember", "#2a160c"),
                   ("accent", "Accent", None))

    # ---- overlay label colors: (key, menu name, {group: color}); None = auto
    VALUE_COLORS = (("white", "White", "#ffffff"), ("soft", "Soft", "#d9d9e0"),
                    ("cyan", "Cyan", "#7fe3ff"), ("lime", "Lime", "#b6ff6a"),
                    ("amber", "Amber", "#ffd166"), ("accent", "Accent", None))
    OVERLAY_PALETTES = (
        ("auto", "Auto", None),
        ("mono", "Mono", {"FPS": "#ffffff", "GPU": "#e4e4e4", "CPU": "#c8c8c8",
                          "RAM": "#acacac", "NET": "#909090"}),
        ("neon", "Neon", {"FPS": "#ffffff", "GPU": "#39ff88", "CPU": "#35d6ff",
                          "RAM": "#ff5ce1", "NET": "#ffe14d"}),
        ("sunset", "Sunset", {"FPS": "#fff1e0", "GPU": "#ff7a45",
                              "CPU": "#ffb454", "RAM": "#ff5f8f",
                              "NET": "#c792ea"}),
        ("ocean", "Ocean", {"FPS": "#e8f7ff", "GPU": "#4cc9f0",
                            "CPU": "#6ea8ff", "RAM": "#7ae7c7",
                            "NET": "#b8c0ff"}),
        ("candy", "Candy", {"FPS": "#ffffff", "GPU": "#ffadad",
                            "CPU": "#ffd6a5", "RAM": "#caffbf",
                            "NET": "#9bf6ff"}))
    NET_COLOR = "#5ac8fa"

    # ---- main window (colors that do not depend on the GPU vendor)
    SIDE_W = 200
    WIN_W, WIN_H = 1000, 600
    PANEL_X, PANEL_W = 752, 232          # quick settings, right side
    PAGE_X, PAGE_W = 224, 512           # content area of every page
    C_BG, C_SIDE = "#17171b", "#111114"
    C_CARD, C_TRACK = "#212126", "#34343c"
    SUB, TXT, DIM = "#9a9aa8", "#f2f2f5", "#7c7c88"
    C_OK = "#3ddc84"                    # "everything fine" dot
    F_LABEL = ("Segoe UI", 10, "bold")
    F_SEG = ("Segoe UI", 11, "bold")
    F_HEAD = ("Segoe UI Semibold", 12)
    F_TITLE = ("Segoe UI Semibold", 20)
    F_BRAND = ("Segoe UI Semibold", 15)
    F_NAV = ("Segoe UI Semibold", 11)
    F_BIG = ("Segoe UI Semibold", 26)
    F_SMALL = ("Segoe UI", 10)
    F_SMALL_B = ("Segoe UI Semibold", 10)

    # ---- accent colors by GPU vendor (applied once at start-up)
    NVIDIA = {"accent": "#76b900", "hi": "#8fd400", "on": "#0d1200"}
    AMD = {"accent": "#ed1c24", "hi": "#ff4048", "on": "#ffffff"}
    NEUTRAL = {"accent": "#6f8cff", "hi": "#8ea5ff", "on": "#0a0d1c"}
    ACCENT, ACCENT_HI, C_ON = NVIDIA["accent"], NVIDIA["hi"], NVIDIA["on"]
    VENDOR = NVIDIA
    LIGHT = False                        # True while a light app theme is used

    # ---- app themes (the whole window): key, name, note, colors
    UI_THEMES = (
        ("default", "Default", "Neutral dark, accent follows your GPU",
         {"C_BG": "#17171b", "C_SIDE": "#111114", "C_CARD": "#212126",
          "C_TRACK": "#34343c", "SUB": "#9a9aa8", "TXT": "#f2f2f5",
          "DIM": "#7c7c88", "light": False, "accent": None}),
        ("night", "Night", "Deep blue-black, easy on the eyes",
         {"C_BG": "#0b0e15", "C_SIDE": "#07090e", "C_CARD": "#121823",
          "C_TRACK": "#232c3d", "SUB": "#8d97ad", "TXT": "#e9eef8",
          "DIM": "#667188", "light": False, "accent": None}),
        ("day", "Day", "Bright and clean for daylight",
         {"C_BG": "#eceff4", "C_SIDE": "#dfe3ea", "C_CARD": "#ffffff",
          "C_TRACK": "#d2d8e2", "SUB": "#586174", "TXT": "#151a24",
          "DIM": "#7b8497", "light": True, "accent": None}),
        ("aurora", "Aurora", "Violet dusk with a mint glow (my own design)",
         {"C_BG": "#150f26", "C_SIDE": "#0f0a1d", "C_CARD": "#1f1737",
          "C_TRACK": "#33295a", "SUB": "#aaa0cf", "TXT": "#f5f1ff",
          "DIM": "#7f75a8", "light": False, "accent": "#2ee6c5"}))
    UI_ACCENTS = (("auto", "Auto", None), ("green", "Green", "#76b900"),
                  ("blue", "Blue", "#4f8cff"), ("violet", "Violet", "#8b5cf6"),
                  ("pink", "Pink", "#ec4899"), ("orange", "Orange", "#f97316"),
                  ("teal", "Teal", "#14b8a6"))

    @classmethod
    def apply_vendor(cls, vendor):
        """vendor: "nvidia" -> green, "amd" -> red, anything else -> neutral."""
        p = {"nvidia": cls.NVIDIA, "amd": cls.AMD}.get(vendor, cls.NEUTRAL)
        cls.VENDOR = p
        cls.ACCENT, cls.ACCENT_HI, cls.C_ON = p["accent"], p["hi"], p["on"]
        return p

    @classmethod
    def ui_spec(cls, key):
        for k, _, _, spec in cls.UI_THEMES:
            if k == key:
                return spec
        return cls.UI_THEMES[0][3]

    @staticmethod
    def _on_color(accent):
        r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
        return "#10131a" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#ffffff"

    @classmethod
    def apply_ui(cls, theme="default", accent="auto"):
        """Colors of the whole app window (call before drawing it)."""
        spec = cls.ui_spec(theme)
        for k in ("C_BG", "C_SIDE", "C_CARD", "C_TRACK", "SUB", "TXT", "DIM"):
            setattr(cls, k, spec[k])
        cls.LIGHT = spec["light"]
        chosen = dict((k, c) for k, _, c in cls.UI_ACCENTS).get(accent)
        if chosen:
            base = chosen
            on = cls._on_color(chosen)
        elif spec["accent"]:
            base = spec["accent"]
            on = cls._on_color(base)
        else:
            base, on = cls.VENDOR["accent"], cls.VENDOR["on"]
        if cls.LIGHT:   # readable on white
            base = cls.mix(base, "#000000", 0.16)
            on = cls._on_color(base)
        cls.ACCENT, cls.ACCENT_HI, cls.C_ON = (
            base, cls.mix(base, "#ffffff", 0.18), on)



    @classmethod
    def palette(cls, key):
        """{group: color} of an overlay label palette (None = automatic)."""
        for k, _, cols in cls.OVERLAY_PALETTES:
            if k == key:
                return cols
        return None

    @classmethod
    def overlay_bg(cls, key):
        """#rrggbb of an overlay background name."""
        for k, _, color in cls.OVERLAY_BGS:
            if k == key:
                return color or cls.mix("#101010", cls.ACCENT, 0.30)
        return cls.BG

    @staticmethod
    def mix(c1, c2, t):
        """Blend two #rrggbb colors (t = 0 -> c1, t = 1 -> c2)."""
        a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
        return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t)
                                       for i in range(3))


# =============================================================== Metrics
class Metrics:
    # group name, [(key, menu label, column width in the vertical layout)]
    GROUPS = [
        ("FPS", [("fps", "FPS", 5), ("avg", "Average", 8),
                 ("low", "1% Low", 9), ("ft", "Frametime", 8),
                 ("graph", "Graph", 0)]),
        ("GPU", [("g_use", "Usage", 5), ("g_temp", "Temp", 6),
                 ("g_pow", "Power", 5), ("g_clk", "Clock", 8),
                 ("g_mem", "VRAM", 11)]),
        ("CPU", [("c_use", "Usage", 5), ("c_temp", "Temp", 6),
                 ("c_pow", "Power", 5), ("c_clk", "Clock", 8)]),
        ("RAM", [("r_use", "Usage", 5), ("r_amt", "Used", 12),
                 ("r_swap", "Swap", 16)]),
        ("NET", [("n_down", "Download", 11), ("n_up", "Upload", 11)]),
    ]
    KEYS = [k for _, items in GROUPS for k, _, _ in items]

    @classmethod
    def items(cls, group):
        return dict(cls.GROUPS)[group]

    @classmethod
    def default_order(cls):
        return {"groups": [n for n, _ in cls.GROUPS],
                "items": {n: [k for k, _, _ in its] for n, its in cls.GROUPS}}

    @classmethod
    def clean_order(cls, raw):
        """Make any saved order valid: known names only, none missing."""
        out = cls.default_order()
        if not isinstance(raw, dict):
            return out

        def merge(saved, default):
            keep = []
            for k in saved if isinstance(saved, list) else []:
                if k in default and k not in keep:
                    keep.append(k)
            return keep + [k for k in default if k not in keep]

        out["groups"] = merge(raw.get("groups"), out["groups"])
        saved_items = raw.get("items")
        saved_items = saved_items if isinstance(saved_items, dict) else {}
        for n in out["items"]:
            out["items"][n] = merge(saved_items.get(n), out["items"][n])
        return out

    @classmethod
    def ordered(cls, order=None):
        """GROUPS in the user's order: [(group, [(key, label, width)])]."""
        order = cls.clean_order(order)
        table = dict(cls.GROUPS)
        result = []
        for n in order["groups"]:
            by_key = {it[0]: it for it in table[n]}
            result.append((n, [by_key[k] for k in order["items"][n]]))
        return result



# =============================================================== Thresholds
class Thresholds:
    """(limit, color): the first limit the value reaches wins, else white."""
    TEMP = ((75, Theme.DARKRED), (60, Theme.RED), (40, Theme.YELLOW))
    USE = ((70, Theme.DARKRED), (50, Theme.RED), (30, Theme.YELLOW))

    @staticmethod
    def _pick(v, table):
        if v is None:
            return Theme.WHITE
        for limit, color in table:
            if v >= limit:
                return color
        return Theme.WHITE

    @classmethod
    def temp(cls, v):
        return cls._pick(v, cls.TEMP)

    @classmethod
    def use(cls, v):
        return cls._pick(v, cls.USE)


# =============================================================== Logger
class Logger:
    _seen = set()

    @classmethod
    def error(cls, where="", text=None):
        """Write an error once to error.log."""
        try:
            tb = text or traceback.format_exc()
            if tb in cls._seen:
                return
            cls._seen.add(tb)
            os.makedirs(Paths.CFG_DIR, exist_ok=True)
            if (os.path.exists(Paths.LOG_FILE)
                    and os.path.getsize(Paths.LOG_FILE) > 200000):
                return
            with open(Paths.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {where}\n{tb}\n")
        except Exception:
            pass


# =============================================================== Settings
class Settings:
    POS = ["left", "center", "right", "custom"]
    LOOKS = ["dark", "glass"]
    REFRESH = (1, 2, 5)    # seconds: how often the window's live data updates
    DEFAULTS = {"pos": "left", "x": None, "y": None, "monitor": "primary",
                "refresh": 1, "layout": "h",
                "text": 11, "graph": 100, "alpha": 80, "on": True,
                "driver_asked": False, "look": "dark", "bg": "black",
                "palette": "auto", "net_unit": "bytes",
                "ui_theme": "default", "ui_accent": "auto", "sessions_on": True,
                "show_mode": "always", "hotkey_secs": 5, "language": "en",
                "font": "Consolas", "weight": "bold", "label_weight": "bold",
                "value_color": "white",
                "order": Metrics.default_order(),
                "show": {k: True for k in Metrics.KEYS}}

    def __init__(self):
        Paths.migrate()
        self.data = self._load()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    @property
    def show(self):
        """{metric key: visible?}  Always read it through this property."""
        return self.data["show"]

    @staticmethod
    def _num(v, lo, hi, default, step=1):
        try:
            v = max(lo, min(hi, int(v)))
        except (TypeError, ValueError):
            return default
        return lo + round((v - lo) / step) * step

    def _load(self):
        cfg = deepcopy(self.DEFAULTS)
        try:
            with open(Paths.CFG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k in ("pos", "x", "y", "layout", "text", "graph", "alpha", "on",
                      "driver_asked", "look", "bg", "monitor", "refresh",
                      "palette", "net_unit", "ui_theme", "ui_accent",
                      "sessions_on", "show_mode", "hotkey_secs", "font", "weight",
                      "label_weight", "value_color", "language"):
                if k in raw:
                    cfg[k] = raw[k]
            shows = raw.get("show", {})
            for k in Metrics.KEYS:
                if k in shows:
                    cfg["show"][k] = bool(shows[k])
            if raw.get("show_graph") is False and "graph" not in shows:
                cfg["show"]["graph"] = False  # very old settings file
            cfg["order"] = Metrics.clean_order(raw.get("order"))
        except Exception:
            pass
        return self._clean(cfg)

    @classmethod
    def _clean(cls, cfg):
        """Make any settings dict valid (also used for profiles)."""
        if cfg["pos"] not in cls.POS:
            cfg["pos"] = "left"
        if cfg["layout"] not in ("h", "v"):
            cfg["layout"] = "h"
        if not isinstance(cfg["monitor"], str) or not cfg["monitor"] \
                or len(cfg["monitor"]) > 64:
            cfg["monitor"] = "primary"
        if cfg["refresh"] not in cls.REFRESH:
            cfg["refresh"] = 1
        if cfg["look"] not in cls.LOOKS:
            cfg["look"] = "dark"
        if cfg["bg"] not in [k for k, _, _ in Theme.OVERLAY_BGS]:
            cfg["bg"] = "black"
        if cfg["palette"] not in [k for k, _, _ in Theme.OVERLAY_PALETTES]:
            cfg["palette"] = "auto"
        if cfg["language"] not in ("en", "fa"):
            cfg["language"] = "en"
        if cfg["net_unit"] not in ("bytes", "bits"):
            cfg["net_unit"] = "bytes"
        if cfg["ui_theme"] not in [k for k, _, _, _ in Theme.UI_THEMES]:
            cfg["ui_theme"] = "default"
        if cfg["ui_accent"] not in [k for k, _, _ in Theme.UI_ACCENTS]:
            cfg["ui_accent"] = "auto"
        if not isinstance(cfg["font"], str) or not cfg["font"].strip() \
                or len(cfg["font"]) > 64 or any(ord(c) < 32 for c in cfg["font"]):
            cfg["font"] = "Consolas"
        for k in ("weight", "label_weight"):
            if cfg[k] not in ("normal", "bold"):
                cfg[k] = "bold"
        if cfg["value_color"] not in [k for k, _, _ in Theme.VALUE_COLORS]:
            cfg["value_color"] = "white"
        if not isinstance(cfg["show"], dict):
            cfg["show"] = {k: True for k in Metrics.KEYS}
        cfg["show"] = {k: bool(cfg["show"].get(k, True)) for k in Metrics.KEYS}
        cfg["order"] = Metrics.clean_order(cfg["order"])
        for k in ("x", "y"):  # saved position: whole numbers or nothing
            if not isinstance(cfg[k], int) or isinstance(cfg[k], bool):
                cfg["x"] = cfg["y"] = None
        if cfg["pos"] == "custom" and cfg["x"] is None:
            cfg["pos"] = "left"
        cfg["text"] = cls._num(cfg["text"], 8, 18, 11)
        cfg["graph"] = cls._num(cfg["graph"], 50, 200, 100, 10)
        cfg["alpha"] = cls._num(cfg["alpha"], 40, 100, 80, 5)
        cfg["on"] = bool(cfg["on"])
        cfg["driver_asked"] = bool(cfg["driver_asked"])
        cfg["sessions_on"] = bool(cfg["sessions_on"])
        if cfg["show_mode"] not in ("always", "hotkey"):
            cfg["show_mode"] = "always"
        if cfg["hotkey_secs"] not in (3, 5, 10):
            cfg["hotkey_secs"] = 5
        return cfg

    def save(self):
        try:
            os.makedirs(Paths.CFG_DIR, exist_ok=True)
            tmp = Paths.CFG_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f)
            os.replace(tmp, Paths.CFG_FILE)
        except Exception:
            Logger.error("settings save")

    def reset(self):
        self.data.clear()
        self.data.update(deepcopy(self.DEFAULTS))


# =============================================================== Profiles
class Profiles:
    """Density presets: which metrics the bar shows (real switches)."""
    DENSITY = (("compact", "Compact", ("fps", "g_use", "c_use", "r_use")),
               ("balanced", "Balanced", ("fps", "low", "g_use", "g_temp",
                                         "c_use", "c_temp", "r_use")),
               ("detailed", "Detailed", None))        # None = everything

    @classmethod
    def density_show(cls, key):
        for k, _, keys in cls.DENSITY:
            if k == key:
                return {m: (keys is None or m in keys) for m in Metrics.KEYS}
        return None

    @classmethod
    def density_of(cls, show):
        for k, _, _ in cls.DENSITY:
            if cls.density_show(k) == {m: bool(show.get(m)) for m in Metrics.KEYS}:
                return k
        return ""                       # custom


# =============================================================== WinApi
class WinApi:
    EX_FLAGS = 0x80000 | 0x20 | 0x80 | 0x08000000  # layered, click-through,
    #                                                toolwindow, no-activate
    admin = False
    _mutex = None
    user32 = shell32 = kernel32 = None

    @classmethod
    def setup(cls):
        """Declare the Windows functions we call (needed for 64-bit)."""
        cls.user32 = ctypes.windll.user32
        cls.shell32 = ctypes.windll.shell32
        cls.kernel32 = ctypes.windll.kernel32
        u = cls.user32
        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetParent.argtypes = [wintypes.HWND]
        u.GetParent.restype = wintypes.HWND
        u.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetWindowLongW.restype = ctypes.c_long
        u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        u.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.UINT]
        cls.shell32.ShellExecuteW.restype = ctypes.c_void_p
        try:  # own taskbar identity: groups windows under the Lmonitor icon
            cls.shell32.SetCurrentProcessExplicitAppUserModelID("Lmonitor.App")
        except Exception:
            pass

    # ---- access level
    @classmethod
    def is_admin(cls):
        try:
            return bool(cls.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @classmethod
    def relaunch_as_admin(cls):
        """Ask Windows (UAC prompt) to start this program again as admin."""
        if getattr(sys, "frozen", False):
            exe, args = sys.executable, sys.argv[1:]
        else:
            exe = sys.executable
            args = [os.path.abspath(sys.argv[0])] + sys.argv[1:]
        params = " ".join(f'"{a}"' for a in args + ["--elevated"])
        rc = cls.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return (rc or 0) > 32  # <= 32: the user said no / it failed

    @classmethod
    def ensure_admin(cls):
        cls.admin = cls.is_admin()
        if (not cls.admin and "--elevated" not in sys.argv
                and cls.relaunch_as_admin()):
            sys.exit(0)  # the elevated copy takes over

    @classmethod
    def single_instance(cls):
        """Exit if this program is already running."""
        tries = 10 if "--elevated" in sys.argv else 1  # old copy may be closing
        for _ in range(tries):
            cls._mutex = cls.kernel32.CreateMutexW(None, False,
                                                   "LmonitorOverlay")
            if cls.kernel32.GetLastError() != 183:  # 183 = already running
                return
            time.sleep(0.5)
        sys.exit(0)


    # ---- windows

    OPEN_OK = re.compile(r"ms-settings:[a-z-]+|[a-z]+\.msc|"
                         r"SystemPropertiesPerformance\.exe|control [a-z]+\.cpl")

    @classmethod
    def open_target(cls, target):
        """Open a Windows settings page / console (only a fixed kind of target)."""
        if not cls.OPEN_OK.fullmatch(target or ""):
            return False
        try:
            if target.startswith("control "):
                subprocess.Popen(["control", target.split()[1]],
                                 creationflags=0x08000000)
            else:
                os.startfile(target)
            return True
        except Exception:
            Logger.error("open target")
            return False

    @classmethod
    def key_down(cls, vk):
        """Is this key held down right now (works while a game has focus)?"""
        try:
            r = cls.user32.GetAsyncKeyState(vk)
            return isinstance(r, int) and bool(r & 0x8000)
        except Exception:
            return False

    @classmethod
    def foreground_pid(cls):
        pid = wintypes.DWORD(0)
        cls.user32.GetWindowThreadProcessId(cls.user32.GetForegroundWindow(),
                                            ctypes.byref(pid))
        return pid.value

    # --- by window handle (HWND): used by any UI (Tk, Qt)

    @classmethod
    def keep_on_top_hwnd(cls, h):
        cls.user32.SetWindowPos(h, -1, 0, 0, 0, 0, 0x13)


    # --- Tk widget variants (kept for the classic window)



    @staticmethod
    def blur_supported():
        """Blur-behind (acrylic) needs Windows 10 version 1803 or newer."""
        try:
            return sys.getwindowsversion().build >= 17134
        except Exception:
            return False


    @classmethod
    def blur_hwnd(cls, hwnd, tint=None, alpha=0):
        """Windows blur-behind on (tint = "#rrggbb") or off (tint = None).

        Uses the undocumented SetWindowCompositionAttribute call. Returns
        True when Windows accepted it.
        """
        try:
            class Accent(ctypes.Structure):
                _fields_ = [("state", ctypes.c_int), ("flags", ctypes.c_int),
                            ("color", ctypes.c_uint), ("anim", ctypes.c_int)]

            class Data(ctypes.Structure):
                _fields_ = [("attr", ctypes.c_int), ("data", ctypes.c_void_p),
                            ("size", ctypes.c_size_t)]
            a = Accent()
            if tint is not None:
                r, g, b = (int(tint[i:i + 2], 16) for i in (1, 3, 5))
                a.state, a.flags = 4, 2          # acrylic blur-behind
                a.color = (alpha << 24) | (b << 16) | (g << 8) | r  # AABBGGRR
            d = Data(19, ctypes.cast(ctypes.byref(a), ctypes.c_void_p),
                     ctypes.sizeof(a))
            ok = cls.user32.SetWindowCompositionAttribute(
                hwnd, ctypes.byref(d))
            return bool(ok) or tint is None
        except Exception:
            return tint is None

    @classmethod
    def round_hwnd(cls, hwnd, on=True, w=0, h=0, r=10):
        """Rounded window shape (needed for blur, which fills the whole
        rectangle). Windows 11: DWM corners; older Windows: a window region
        of w x h physical pixels."""
        try:
            if sys.getwindowsversion().build >= 22000:
                pref = ctypes.c_int(2 if on else 0)     # DWMWCP_ROUND / default
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 33, ctypes.byref(pref), 4)
            elif on and w > 0 and h > 0:
                rgn = ctypes.windll.gdi32.CreateRoundRectRgn(
                    0, 0, int(w) + 1, int(h) + 1, 2 * r, 2 * r)
                cls.user32.SetWindowRgn(hwnd, rgn, True)
            else:
                cls.user32.SetWindowRgn(hwnd, None, True)
        except Exception:
            pass




# =============================================================== LibreHardwareMonitor
HW_LOCK = threading.RLock()   # one thread at a time talks to the sensor library


def hw_locked(fn):
    """Sensor reads run on a worker thread too: never two at once."""
    @functools.wraps(fn)
    def run(*a, **k):
        with HW_LOCK:
            return fn(*a, **k)
    return run


class LibreHardwareHost:
    """Loads the DLL once and finds the CPU / GPU sensors we need."""

    def __init__(self):
        self.computer = None  # keep a reference so it is not garbage collected
        self.cpu_hw = None
        self.cpu_name = ""
        self.cpu_name_raw = ""
        self.extra_hw = []   # motherboard, drives, battery... (loaded on demand)
        self.board_name = ""
        self._extras_on = False
        self.cpu_temp = self.cpu_power = None
        self.cpu_clocks = []
        self.gpu_hw = None   # AMD / Intel GPU, or NVIDIA when NVML has gaps
        self.gpu_type = ""
        self.gpu = {}        # role -> sensor
        try:
            self._open()
        except Exception:
            Logger.error("init LibreHardwareMonitor")

    # ---- small helpers
    @staticmethod
    def find_sensor(hw, kind, prefer=(), avoid=()):
        """First sensor of a type; preferred names win, avoided names lose."""
        ok = [x for x in hw.Sensors if x.SensorType.ToString() == kind]
        good = [x for x in ok if not any(a in x.Name for a in avoid)]
        for x in good:
            if any(w in x.Name for w in prefer):
                return x
        return (good or ok or [None])[0]

    @staticmethod
    def named(hw, names):
        for n in names:
            for x in hw.Sensors:
                if x.Name == n:
                    return x
        return None

    @staticmethod
    def value(sensor):
        """Sensor value as float, or None."""
        if sensor is None:
            return None
        try:
            v = sensor.Value
        except Exception:
            return None
        return None if v is None else float(v)

    @staticmethod
    def positive(v):
        return v if v is not None and v > 0 else None  # 0 = not readable

    # ---- start-up
    def _open(self):
        clr.AddReference(Paths.LHM_DLL)
        from LibreHardwareMonitor.Hardware import Computer
        self.computer = Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.Open()
        for hw in self.computer.Hardware:
            kind = hw.HardwareType.ToString()
            if kind == "Cpu" and self.cpu_hw is None:
                self._map_cpu(hw)
            elif kind.startswith("Gpu"):  # prefer a discrete GPU over Intel iGPU
                if self.gpu_hw is None or (self.gpu_type.endswith("Intel")
                                           and not kind.endswith("Intel")):
                    self.gpu_hw, self.gpu_type = hw, kind
        if self.gpu_hw is not None:
            self._map_gpu(self.gpu_hw)

    def _map_cpu(self, hw):
        self.cpu_hw = hw
        self.cpu_name_raw = str(hw.Name)
        self.cpu_name = self.cpu_name_raw.lower()
        hw.Update()
        pkg = other = None
        core_clocks, any_clocks = [], []
        for x in hw.Sensors:
            st, nm = x.SensorType.ToString(), x.Name
            if st == "Temperature":
                if "Package" in nm or "Tctl" in nm:
                    if pkg is None:
                        pkg = x
                elif other is None:
                    other = x
            elif st == "Power" and "Package" in nm:
                if self.cpu_power is None:
                    self.cpu_power = x
            elif st == "Clock" and "Core" in nm:
                any_clocks.append(x)
                if not any(w in nm for w in ("Effective", "Average", "Max")):
                    core_clocks.append(x)
        self.cpu_temp = pkg if pkg is not None else other
        self.cpu_clocks = core_clocks or any_clocks

    def _map_gpu(self, hw):
        hw.Update()
        f = self.find_sensor
        self.gpu["use"] = f(hw, "Load", ("GPU Core", "Core"),
                            ("Memory", "Video", "Bus"))
        self.gpu["temp"] = f(hw, "Temperature", ("GPU Core", "Core"),
                             ("Hot Spot", "Memory", "VR", "Junction"))
        self.gpu["pw"] = f(hw, "Power", ("Package", "Core"))
        self.gpu["clk"] = f(hw, "Clock", ("Core",), ("Memory",))
        self.gpu["mem_used"] = self.named(
            hw, ("GPU Memory Used", "D3D Dedicated Memory Used"))
        self.gpu["mem_total"] = self.named(
            hw, ("GPU Memory Total", "D3D Dedicated Memory Total"))
        self.gpu["mem_free"] = self.named(hw, ("GPU Memory Free",))

    @hw_locked
    def enable_extras(self):
        """Load motherboard / drive / battery sensors (first time only).

        Done on demand, so start-up stays as fast as before and nothing
        extra runs unless the Hardware page asks for it.
        """
        if self._extras_on or self.computer is None:
            return
        self._extras_on = True
        c = self.computer
        for flag in ("IsMotherboardEnabled", "IsStorageEnabled",
                     "IsControllerEnabled", "IsBatteryEnabled"):
            try:
                setattr(c, flag, True)
            except Exception:
                pass  # this LibreHardwareMonitor build does not know it
        try:
            flat = []

            def walk(hw):
                flat.append(hw)
                for sub in hw.SubHardware:
                    walk(sub)
            for hw in c.Hardware:
                kind = hw.HardwareType.ToString()
                if kind != "Cpu" and not kind.startswith("Gpu"):
                    walk(hw)
            self.extra_hw = flat
            for hw in flat:
                if hw.HardwareType.ToString() == "Motherboard":
                    self.board_name = str(hw.Name)
                    break
        except Exception:
            Logger.error("enable extra sensors")

    @hw_locked
    def dump(self):
        """Every sensor as text lines (for the troubleshooting report)."""
        lines = []
        if self.computer is None:
            return lines
        try:
            for hw in self.computer.Hardware:
                hw.Update()
                lines.append(f"[{hw.HardwareType.ToString()}] {hw.Name}")
                for x in hw.Sensors:
                    lines.append(
                        f"  {x.SensorType.ToString():12} {x.Name:34} {x.Value}")
                lines.append("")
        except Exception:
            lines.append(traceback.format_exc())
        return lines


# =============================================================== CPU
class CpuReader:
    MIN_UPDATE = 0.8                # seconds between two real sensor updates
    def __init__(self, host):
        self.host = host
        self.seen = False  # True once a CPU temperature/power was read

    @property
    def name(self):
        return self.host.cpu_name

    @property
    def available(self):
        return self.host.cpu_hw is not None

    @staticmethod
    def usage():
        return psutil.cpu_percent()

    def brand_color(self):
        n = self.name
        if "intel" in n:
            return Theme.INTEL_BLUE
        if "amd" in n or "ryzen" in n:
            return Theme.AMD_ORANGE
        return Theme.WHITE

    @hw_locked
    def read(self, want_t, want_p, want_c):
        """-> (temp C, power W, clock MHz, clock_is_approximate)."""
        h = self.host
        t = p = c = None
        approx = False
        if h.cpu_hw is not None:
            now = time.monotonic()
            if now - getattr(self, "_upd", 0.0) >= self.MIN_UPDATE:
                h.cpu_hw.Update()          # the sensor library is slow: at most ~1/s
                self._upd = now
            if want_t:
                t = h.positive(h.value(h.cpu_temp))
            if want_p:
                p = h.positive(h.value(h.cpu_power))
            if want_c:
                vals = [v for v in map(h.value, h.cpu_clocks) if v]
                c = sum(vals) / len(vals) if vals else None
        if t is not None or p is not None:
            self.seen = True
        if want_c and c is None:  # no sensor: use what Windows reports
            try:
                f = psutil.cpu_freq()
                if f and f.current:
                    c, approx = float(f.current), True
            except Exception:
                pass
        return t, p, c, approx


# =============================================================== GPU
class GpuReader:
    def __init__(self, host):
        self.host = host
        self.handle = None
        self.available = False  # NVIDIA + NVML working
        self.name = ""
        self.errors = {}        # NVML function -> last error (for the report)
        if pynvml is not None:
            try:
                pynvml.nvmlInit()
                self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                n = pynvml.nvmlDeviceGetName(self.handle)
                self.name = (n.decode() if isinstance(n, bytes) else str(n)).lower()
                self.available = True
                atexit.register(lambda: pynvml.nvmlShutdown())
            except Exception:
                Logger.error("init NVML")

    def _q(self, fn, *args):
        try:
            return fn(self.handle, *args)
        except Exception as e:
            self.errors[fn.__name__] = repr(e)[:90]
            return None

    @hw_locked
    def fan(self):
        """GPU fan speed in % (NVIDIA only), else None."""
        fn = getattr(pynvml, "nvmlDeviceGetFanSpeed", None)
        if not self.available or fn is None:
            return None
        return self._q(fn)

    def vendor(self):
        """"nvidia", "amd" or "other" (drives the window's accent color)."""
        if self.available:
            return "nvidia"
        t = self.host.gpu_type
        if t.endswith("Nvidia"):
            return "nvidia"
        if t.endswith("Amd"):
            return "amd"
        return "other"

    def display_name(self):
        if self.name:
            return self.name
        hw = self.host.gpu_hw
        try:
            return str(hw.Name).lower() if hw is not None else ""
        except Exception:
            return ""

    def brand_color(self):
        if self.available:
            return Theme.NVIDIA_GREEN
        t = self.host.gpu_type
        if t.endswith("Intel"):
            return Theme.INTEL_BLUE
        if t.endswith("Amd"):
            return Theme.AMD_ORANGE
        return Theme.NVIDIA_GREEN

    @hw_locked
    def read(self, want):
        """(usage %, temp C, power W, clock MHz, (used GB, total GB)).

        `want` is the {key: visible} dict; None means unknown.
        """
        use = temp = pw = clk = mem = None
        if self.available:  # NVIDIA: NVML first
            nv = pynvml
            if want["g_use"]:
                u = self._q(nv.nvmlDeviceGetUtilizationRates)
                use = u.gpu if u is not None else None
            if want["g_temp"]:
                temp = self._q(nv.nvmlDeviceGetTemperature,
                               nv.NVML_TEMPERATURE_GPU)
            if want["g_pow"]:
                w = self._q(nv.nvmlDeviceGetPowerUsage)
                pw = w / 1000 if w is not None else None
            if want["g_clk"]:
                clk = self._q(nv.nvmlDeviceGetClockInfo, nv.NVML_CLOCK_GRAPHICS)
            if want["g_mem"]:
                # v2 leaves out the memory the driver reserves for itself (about 240 MB
                # on an 8 GB card), which is what nvidia-smi and Task Manager report
                v2 = getattr(nv, "nvmlMemory_v2", None)
                m = self._q(nv.nvmlDeviceGetMemoryInfo, v2) if v2 is not None else None
                if m is None:
                    m = self._q(nv.nvmlDeviceGetMemoryInfo)
                if m is not None and m.total:
                    mem = (m.used / 1024**3, m.total / 1024**3)
        h = self.host
        if h.gpu_hw is not None:  # AMD / Intel, or what NVML could not read
            gaps = ((want["g_use"] and use is None)
                    or (want["g_temp"] and temp is None)
                    or (want["g_pow"] and pw is None)
                    or (want["g_clk"] and clk is None)
                    or (want["g_mem"] and mem is None))
            if gaps:
                h.gpu_hw.Update()
                g, val, pos = h.gpu, h.value, h.positive
                if want["g_use"] and use is None:
                    use = val(g.get("use"))
                if want["g_temp"] and temp is None:
                    temp = pos(val(g.get("temp")))
                if want["g_pow"] and pw is None:
                    pw = pos(val(g.get("pw")))
                if want["g_clk"] and clk is None:
                    clk = pos(val(g.get("clk")))
                if want["g_mem"] and mem is None:
                    used, total = val(g.get("mem_used")), val(g.get("mem_total"))
                    free = val(g.get("mem_free"))
                    if total is None and used is not None and free is not None:
                        total = used + free
                    if used is not None and total:
                        k = 1 / 1024 if total < 1e5 else 1 / 1024**3  # MB / bytes
                        mem = (used * k, total * k)
        return use, temp, pw, clk, mem


# =============================================================== Memory
class MemoryReader:
    @staticmethod
    def ram():
        return psutil.virtual_memory()

    @staticmethod
    def swap():
        return psutil.swap_memory()


# =============================================================== FPS (PresentMon)
class FpsMonitor:
    IGNORE = {"dwm.exe", "explorer.exe", "lmonitor.exe", "systemmonitor.exe", "python.exe",
              "pythonw.exe", "presentmon.exe"}

    class ProcData:
        __slots__ = ("recent", "graph", "total_ms", "count", "last", "low",
                     "low_time", "name", "hist")

        def __init__(self):
            self.recent = deque()  # (time, ms) of the last 60 seconds
            self.graph = deque(maxlen=Theme.GRAPH_POINTS)
            self.total_ms = 0.0
            self.count = 0
            self.last = 0.0
            self.low = None
            self.low_time = 0.0
            self.name = ""
            self.hist = [0] * 4001   # frame times in 0.25 ms steps (sessions)

    def __init__(self):
        self.lock = threading.Lock()
        self.procs = {}
        self.proc = None
        self.status = ""
        atexit.register(self.stop)

    # ---- process control
    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        if self.alive:
            return
        if not os.path.exists(Paths.PRESENTMON):
            self.status = "PresentMon.exe not found"
            return
        try:
            self.proc = subprocess.Popen(
                [Paths.PRESENTMON, "--output_stdout", "--no_console_stats",
                 "--stop_existing_session"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                errors="replace", bufsize=1,
                creationflags=0x08000000 | 0x4000)  # no window, below normal
        except Exception as e:
            self.proc = None
            self.status = f"PresentMon error: {e}"[:60]
            return
        self.status = "PresentMon: waiting for data"
        threading.Thread(target=self._reader, args=(self.proc,),
                         daemon=True).start()

    def stop(self):
        p, self.proc = self.proc, None
        if p is not None:
            try:
                p.terminate()
            except Exception:
                pass
        with self.lock:
            self.procs.clear()
        self.status = ""

    # ---- reading the CSV that PresentMon prints
    def _reader(self, proc):
        i_app = i_pid = i_ft = None
        for line in proc.stdout:
            if proc is not self.proc:
                return
            parts = line.strip().split(",")
            if i_ft is None:  # waiting for the CSV header
                low = [p.strip().lower() for p in parts]
                if "application" in low and "processid" in low:
                    i_app, i_pid = low.index("application"), low.index("processid")
                    for name in ("msbetweenpresents", "frametime"):
                        if name in low:
                            i_ft = low.index(name)
                            break
                    self.status = ("PresentMon: running" if i_ft is not None
                                   else "PresentMon: frametime column missing")
                    if i_ft is None:
                        return
                elif line.strip():
                    self.status = "PresentMon: " + line.strip()[:48]
                continue
            try:
                if parts[i_app].strip().lower() in self.IGNORE:
                    continue
                pid = int(parts[i_pid])
                ms = float(parts[i_ft])
            except (ValueError, IndexError):
                continue
            if ms <= 0:
                continue
            now = time.time()
            with self.lock:
                p = self.procs.get(pid)
                if p is None:
                    p = self.procs[pid] = self.ProcData()
                p.name = parts[i_app].strip()
                p.hist[min(4000, int(ms * 4))] += 1
                p.recent.append((now, ms))
                p.graph.append(ms)
                p.total_ms += ms
                p.count += 1
                p.last = now
                cut = now - 60
                while p.recent and p.recent[0][0] < cut:
                    p.recent.popleft()
        if proc is self.proc:
            self.status = "PresentMon: stopped"

    # ---- for game sessions
    def current(self):
        """-> (pid, program name) of the program in front if it draws frames."""
        pid = WinApi.foreground_pid()
        with self.lock:
            p = self.procs.get(pid)
            if p is None or time.time() - p.last > 2 or not p.name:
                return None
            return pid, p.name

    def recent(self, pid, within):
        """Did this program draw a frame in the last `within` seconds?"""
        with self.lock:
            p = self.procs.get(pid)
            return p is not None and time.time() - p.last <= within

    def counters(self, pid):
        """-> (frames, total ms, histogram copy) since PresentMon first saw it."""
        with self.lock:
            p = self.procs.get(pid)
            return None if p is None else (p.count, p.total_ms, list(p.hist))

    @staticmethod
    def lows(hist, n):
        """1% / 0.1% low FPS from a frame-time histogram of n frames."""
        out = {"low1": None, "low01": None}
        for key, frac in (("low1", 0.01), ("low01", 0.001)):
            k = max(1, int(n * frac))
            taken, tot = 0, 0.0
            for b in range(len(hist) - 1, -1, -1):
                c = hist[b]
                if c:
                    use = min(c, k - taken)
                    tot += use * (b + 0.5) / 4.0
                    taken += use
                    if taken >= k:
                        break
            if taken and tot > 0:
                out[key] = 1000.0 * taken / tot
        return out

    # ---- numbers for the program in front (the game)
    def snapshot(self, want_graph):
        """-> (fps, average, 1% low, last frametime, graph list) or None."""
        now = time.time()
        pid = WinApi.foreground_pid()
        times = None
        with self.lock:
            for k in [k for k, v in self.procs.items() if now - v.last > 10]:
                del self.procs[k]
            p = self.procs.get(pid)
            if p is None or now - p.last > 2:
                return None
            cnt, total, last = 0, 0.0, 0.0
            for t, ms in reversed(p.recent):  # only the last second
                if now - t > 1.0:
                    break
                if cnt == 0:
                    last = ms
                cnt += 1
                total += ms
            if cnt == 0:
                return None
            fps = 1000.0 * cnt / total
            avg = 1000.0 * p.count / p.total_ms
            if now - p.low_time > 2.0:
                p.low_time = now
                if len(p.recent) >= 100:
                    times = [ms for _, ms in p.recent]
                else:
                    p.low = None
            graph = list(p.graph) if want_graph else None
        if times is not None:  # sort outside the lock
            times.sort(reverse=True)
            k = max(1, len(times) // 100)
            low = 1000.0 / (sum(times[:k]) / k)
            with self.lock:
                p.low = low
        return fps, avg, p.low, last, graph


# =============================================================== PawnIO driver


# =============================================================== Diagnostics
class Diagnostics:
    def __init__(self, app):
        self.app = app

    def build(self):
        a = self.app
        h = a.host
        L = [f"Lmonitor report  {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"running as admin : {WinApi.admin}",
             f"PawnIO driver    : "
             f"{'installed' if a.driver.installed() else 'MISSING'}",
             f"PawnIO installer : "
             f"{'bundled' if os.path.exists(Paths.PAWNIO_SETUP) else 'not bundled'}",
             f"NVIDIA (NVML)    : {a.gpu.available} {a.gpu.name}",
             f"LibreHardwareMon.: "
             f"{'loaded' if h.computer is not None else 'FAILED'}",
             f"CPU              : {h.cpu_name}",
             f"GPU via LHM      : {h.gpu_type or '-'}",
             f"PresentMon.exe   : {os.path.exists(Paths.PRESENTMON)}  "
             f"({a.fps.status})",
             ""]
        for fn, err in a.gpu.errors.items():
            L.append(f"NVML error       : {fn}: {err}")
        L.append(f"PawnIO service   : {a.driver.service_state()}")
        L.append(f"PawnIOLib.dll    : {a.driver.library_info()}")
        L.append("")
        L += h.dump()
        try:
            with open(Paths.LOG_FILE, "r", encoding="utf-8") as f:
                L += ["---- error.log ----", f.read()[-3000:]]
        except Exception:
            pass
        return L

    def save(self):
        """Write the report; returns a short message for the menu."""
        lines = self.build()
        desk = os.path.join(os.path.expanduser("~"), "Desktop")
        folder_out = desk if os.path.isdir(desk) else Paths.CFG_DIR
        path = os.path.join(folder_out, "Lmonitor_report.txt")
        try:
            os.makedirs(folder_out, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return "Saved: " + ("Desktop" if folder_out == desk else path)
        except Exception:
            Logger.error("save report")
            return "Could not save the report"


# =============================================================== App info
class AppInfo:
    """Name / version shown in the Hardware > System tab."""
    NAME = "Lmonitor"
    VERSION = "1.17.0"
    PUBLISHER = ""      # put your name or company here (empty = "Not set")
    URL = "https://github.com/unrealhamed/Lmonitor"


# =============================================================== formatting
def fmt_value(v, spec=".0f", unit="", na="n/a"):
    """A number as text, or "n/a" when the sensor gave nothing."""
    return na if v is None else format(v, spec) + unit


def fmt_size(n):
    """Bytes -> '476.9 GB'."""
    for unit, div in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2)):
        if n >= div:
            return f"{n / div:.1f} {unit}"
    return f"{n / 1024:.0f} KB"


def fmt_rate(bps):
    """Bytes per second -> '1.2 MB/s'."""
    if bps is None:
        return "n/a"
    for unit, div in (("MB/s", 1024 ** 2), ("KB/s", 1024)):
        if bps >= div:
            return f"{bps / div:.1f} {unit}"
    return f"{bps:.0f} B/s"


def fmt_net(bps, unit="bytes"):
    """Short speed for the overlay: '1.2MB/s' or '9.6Mbps' ('--' = no data)."""
    if bps is None:
        return "--"
    if unit == "bits":
        bits = bps * 8
        if bits >= 1e6:
            return f"{bits / 1e6:.1f}Mbps"
        return f"{bits / 1e3:.0f}Kbps"
    if bps >= 1024 ** 2:
        return f"{bps / 1024 ** 2:.1f}MB/s"
    return f"{bps / 1024:.0f}KB/s"


# =============================================================== SystemInfo
class SystemInfo:
    """Facts that do not change while the app runs.

    Collected once in a background thread (PowerShell can take a second or
    two), so the window never waits for it.
    """

    def __init__(self, host, gpu):
        self.host, self.gpu = host, gpu
        self.ready = False
        self.windows = ""           # "Windows 11 Pro 23H2 (build 22631.3007)"
        self.cpu_registry = ""      # CPU name from the registry
        self.gpu_drivers = []       # [(name, driver version)]
        self.battery_wmi = None     # (design mWh, full-charge mWh)
        self.nvidia_driver = ""
        self.disks = []             # physical drives (Windows storage API)
        self.letter_disk = {}       # "C" -> disk number
        self.started = False

    def start(self):
        """Begin collecting (once, in the background)."""
        if not self.started:
            self.started = True
            threading.Thread(target=self._collect, daemon=True).start()

    @staticmethod
    def _powershell(script, timeout=12):
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, stdin=subprocess.DEVNULL, text=True,
            timeout=timeout, creationflags=0x08000000 if os.name == "nt" else 0)  # no window
        return r.stdout.strip()

    @classmethod
    def _json_t(cls, script, timeout):
        out = cls._powershell(script, timeout)
        if not out:
            return []
        data = json.loads(out)
        return data if isinstance(data, list) else [data]

    @classmethod
    def _json(cls, script):
        out = cls._powershell(script)
        if not out:
            return []
        data = json.loads(out)
        return data if isinstance(data, list) else [data]

    @staticmethod
    def disk_kind(d):
        """'NVMe SSD' / 'SSD' / 'HDD' / '' (empty = Windows does not say)."""
        media = d["media"] if d["media"] in ("SSD", "HDD") else ""
        if d["bus"] == "NVMe":
            return "NVMe SSD" if media in ("", "SSD") else "NVMe"
        return media or ("USB" if d["bus"] == "USB" else "")

    def disk_for(self, mount):
        """The physical drive behind a mount point such as 'C:\\' (or None)."""
        num = self.letter_disk.get(mount[:1].upper())
        for d in self.disks:
            if num is not None and d["id"] == num:
                return d
        return None

    def _collect(self):
        try:
            self._windows()
        except Exception:
            Logger.error("system info: windows")
        try:
            if pynvml is not None and self.gpu.available:
                v = pynvml.nvmlSystemGetDriverVersion()
                self.nvidia_driver = v.decode() if isinstance(v, bytes) else str(v)
        except Exception:
            pass
        try:
            for d in self._json("Get-CimInstance Win32_VideoController | "
                                "Select-Object Name,DriverVersion | "
                                "ConvertTo-Json -Compress"):
                if d.get("Name"):
                    self.gpu_drivers.append(
                        (str(d["Name"]), str(d.get("DriverVersion") or "")))
        except Exception:
            Logger.error("system info: video controllers")
        try:  # physical drives: type and the health Windows reports
            for d in self._json(
                    "Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,"
                    "@{n='Media';e={\"$($_.MediaType)\"}},"
                    "@{n='Bus';e={\"$($_.BusType)\"}},"
                    "@{n='Health';e={\"$($_.HealthStatus)\"}},"
                    "@{n='State';e={\"$($_.OperationalStatus)\"}},Size | "
                    "ConvertTo-Json -Compress"):
                self.disks.append({
                    "id": str(d.get("DeviceId")), "name": str(d.get("FriendlyName") or ""),
                    "media": str(d.get("Media") or ""), "bus": str(d.get("Bus") or ""),
                    "health": str(d.get("Health") or ""), "state": str(d.get("State") or ""),
                    "size": d.get("Size")})
            for p in self._json("Get-Partition | Where-Object DriveLetter | "
                                "Select-Object DriveLetter,DiskNumber | "
                                "ConvertTo-Json -Compress"):
                self.letter_disk[str(p["DriveLetter"]).upper()] = str(p["DiskNumber"])
        except Exception:
            Logger.error("system info: physical disks")
        try:  # battery health: designed vs. full-charge capacity
            des = self._json("Get-CimInstance -Namespace root\\wmi -ClassName "
                             "BatteryStaticData | Select-Object DesignedCapacity "
                             "| ConvertTo-Json -Compress")
            ful = self._json("Get-CimInstance -Namespace root\\wmi -ClassName "
                             "BatteryFullChargedCapacity | Select-Object "
                             "FullChargedCapacity | ConvertTo-Json -Compress")
            if des and ful and des[0].get("DesignedCapacity"):
                self.battery_wmi = (float(des[0]["DesignedCapacity"]),
                                    float(ful[0]["FullChargedCapacity"]))
        except Exception:
            pass  # no battery / not supported: shown as n/a
        self.ready = True

    def _windows(self):
        import platform
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")

            def get(name):
                try:
                    return str(winreg.QueryValueEx(key, name)[0])
                except OSError:
                    return ""
            name = get("ProductName")
            build, ubr = get("CurrentBuildNumber"), get("UBR")
            if build.isdigit() and int(build) >= 22000:  # 11 starts at 22000
                name = name.replace("Windows 10", "Windows 11")
            ver = get("DisplayVersion") or get("ReleaseId")
            self.windows = (f"{name} {ver} (build {build}"
                            f"{'.' + ubr if ubr else ''})").replace("  ", " ")
            try:
                cpu = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                self.cpu_registry = str(
                    winreg.QueryValueEx(cpu, "ProcessorNameString")[0]).strip()
            except OSError:
                pass
        except ImportError:
            self.windows = platform.platform()


# =============================================================== Storage
class StorageReader:
    """Drives with size / used / free (cached for a few seconds)."""
    TTL = 5.0

    def __init__(self):
        self._t = 0.0
        self._rows = []

    @staticmethod
    def label(mount):
        """Volume name such as "Windows" ("" when it has none)."""
        try:
            buf = ctypes.create_unicode_buffer(261)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                mount, buf, 261, None, None, None, None, 0)
            return buf.value if ok else ""
        except Exception:
            return ""

    def read(self):
        now = time.time()
        if self._t and now - self._t < self.TTL:
            return self._rows
        rows = []
        try:
            parts = psutil.disk_partitions(all=False)
        except Exception:
            parts = []
        for p in parts:
            if "cdrom" in p.opts or "remote" in p.opts or not p.fstype:
                continue  # empty optical slots; network drives (can hang)
            try:
                u = psutil.disk_usage(p.mountpoint)
            except Exception:
                continue
            rows.append({"mount": p.mountpoint, "fs": p.fstype,
                         "label": self.label(p.mountpoint), "total": u.total,
                         "used": u.used, "free": u.free, "pct": u.percent})
        self._rows, self._t = rows, now
        return rows


# =============================================================== Network
class NetworkReader:
    """Download / upload speed of every connected network interface."""

    def __init__(self):
        self.prev = None      # (time, counters)
        self.speeds = {}      # nic -> (down B/s, up B/s)
        self.info = {}        # nic -> (is up, link speed in Mbit/s)
        self.virtual = set()  # adapters that are not real hardware (VPN, tunnels...)
        self._known = None

    @staticmethod
    def _real(name):
        n = name.lower()
        return not (n.startswith("lo") and len(n) <= 3 or "loopback" in n)

    @staticmethod
    def _virtual_names():
        """Names of the adapters Windows marks as not being hardware. Empty if unknown."""
        class Row(ctypes.Structure):            # the start of MIB_IF_ROW2 (1352 bytes)
            _fields_ = [("luid", ctypes.c_uint64), ("index", ctypes.c_ulong),
                        ("guid", ctypes.c_byte * 16), ("alias", ctypes.c_wchar * 257),
                        ("description", ctypes.c_wchar * 257), ("addr_len", ctypes.c_ulong),
                        ("addr", ctypes.c_ubyte * 64), ("mtu", ctypes.c_ulong),
                        ("type", ctypes.c_ulong), ("tunnel", ctypes.c_int),
                        ("media", ctypes.c_int), ("physical", ctypes.c_int),
                        ("access", ctypes.c_int), ("direction", ctypes.c_int),
                        ("flags", ctypes.c_ubyte)]
        out = set()
        try:
            api = ctypes.windll.iphlpapi
            table = ctypes.c_void_p()
            if api.GetIfTable2(ctypes.byref(table)) != 0:
                return out
            try:
                count = ctypes.c_ulong.from_address(table.value).value
                for i in range(count):
                    row = Row.from_address(table.value + 8 + i * 1352)
                    if not row.flags & 1:       # InterfaceAndOperStatusFlags.HardwareInterface
                        out.add(row.alias)
            finally:
                api.FreeMibTable(table)
        except Exception:
            Logger.error("network adapter list")
        return out

    def read(self):
        now = time.time()
        try:
            counters = psutil.net_io_counters(pernic=True)
            stats = psutil.net_if_stats()
        except Exception:
            return
        if set(counters) != self._known:        # adapters came or went
            self._known = set(counters)
            self.virtual = self._virtual_names()
        self.info = {n: (s.isup, s.speed) for n, s in stats.items()
                     if self._real(n)}
        if self.prev is None:
            self.prev = (now, counters)
            return
        dt = now - self.prev[0]
        if dt < 0.2:
            return
        old = self.prev[1]
        self.speeds = {
            n: (max(0.0, (c.bytes_recv - old[n].bytes_recv) / dt),
                max(0.0, (c.bytes_sent - old[n].bytes_sent) / dt))
            for n, c in counters.items() if n in old and self._real(n)}
        self.prev = (now, counters)

    def total(self):
        """(down, up) in bytes/s of the real adapters that are up. A VPN's traffic also
        passes through a real adapter, so adding the virtual ones would count it twice.
        Virtual adapters only count when no real adapter is up."""
        if not self.speeds:
            return None, None
        up_now = [n for n in self.speeds if self.info.get(n, (False, 0))[0]]
        use = [n for n in up_now if n not in self.virtual] or up_now
        return (sum(self.speeds[n][0] for n in use),
                sum(self.speeds[n][1] for n in use))

    def interfaces(self):
        """[(name, link Mbit/s, down, up)] for interfaces that are up."""
        return [(n, sp, *self.speeds.get(n, (None, None)))
                for n, (isup, sp) in sorted(self.info.items()) if isup]


# =============================================================== Battery
class BatteryReader:
    @staticmethod
    def read():
        """psutil battery info, or None on PCs without a battery."""
        try:
            return psutil.sensors_battery()
        except Exception:
            return None


# =============================================================== Sensors
class SensorReader:
    """Fans, board / drive temperatures, voltages (LibreHardwareMonitor)."""
    TTL = 2.0
    UNITS = {"Temperature": " °C", "Fan": " RPM", "Voltage": " V",
             "Control": " %", "Level": " %", "Load": " %", "Power": " W",
             "Clock": " MHz", "Current": " A"}

    def __init__(self, host, gpu):
        self.host, self.gpu = host, gpu
        self._t = 0.0
        self._data = []

    @hw_locked
    def read(self):
        """[(hardware type, hardware name, sensor type, sensor name, value)]."""
        now = time.time()
        if self._t and now - self._t < self.TTL:
            return self._data
        h = self.host
        hardware = list(h.extra_hw)
        if h.gpu_hw is not None:
            hardware.append(h.gpu_hw)
        out = []
        for hw in hardware:
            try:
                hw.Update()
                kind, name = hw.HardwareType.ToString(), str(hw.Name)
                for x in hw.Sensors:
                    v = h.value(x)
                    if v is not None:
                        out.append((kind, name, x.SensorType.ToString(),
                                    str(x.Name), v))
            except Exception:
                Logger.error("sensor read")
        self._data, self._t = out, now
        return out


# =============================================================== Recorder
class Recorder:
    """Long history for the dashboard chart: CPU / RAM / GPU every 5 seconds
    (24 hours kept, about 1 MB). The reading runs in a worker thread."""
    STEP = 5.0
    KEEP = int(24 * 3600 / STEP)

    def __init__(self, gpu):
        self.gpu = gpu
        self.load = CpuLoad()          # its own counters
        self.data = deque(maxlen=self.KEEP)   # (time, cpu, ram, gpu)
        self.busy = False
        self._last = 0.0

    def tick(self, snap=None):
        """Record one point. With `snap` (the telemetry reading that was just
        taken) nothing is read again; without it a worker thread reads."""
        if snap is not None:
            now = time.time()
            if now - self._last >= self.STEP - 0.2:     # one point per STEP
                self._last = now
                self.data.append((now, snap.get("c_use"), snap.get("r_use"),
                                  snap.get("g_use")))
            return
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._record, daemon=True).start()

    def _record(self):
        try:
            self.data.append((time.time(), self.load.read(),
                              psutil.virtual_memory().percent,
                              self.gpu.read(Telemetry.ALL)[0]))
        except Exception:
            Logger.error("recorder")
        finally:
            self.busy = False

    def series(self, seconds, points=90):
        """[cpu, ram, gpu] of the last `seconds`, averaged into `points`
        buckets (None where nothing was recorded)."""
        t0 = time.time() - seconds
        width = seconds / points
        sums = [[0.0] * points for _ in range(3)]
        cnt = [[0] * points for _ in range(3)]
        for row in list(self.data):
            if row[0] < t0:
                continue
            b = min(points - 1, int((row[0] - t0) / width))
            for k in range(3):
                if row[1 + k] is not None:
                    sums[k][b] += row[1 + k]
                    cnt[k][b] += 1
        return [[(sums[k][b] / cnt[k][b]) if cnt[k][b] else None
                 for b in range(points)] for k in range(3)]


# =============================================================== Game sessions
class SessionStore:
    """Finished game sessions in one small SQLite file in %APPDATA%\\Lmonitor.

    A row holds the summary (JSON) and the samples (compressed JSON).
    Only the newest KEEP sessions are kept."""
    KEEP = 60

    def __init__(self, path=None):
        self.path = path or os.path.join(Paths.CFG_DIR, "sessions.db")

    def _con(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        con = sqlite3.connect(self.path, timeout=5)
        con.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY "
                    "KEY AUTOINCREMENT, game TEXT, start REAL, duration REAL, "
                    "summary TEXT, samples BLOB)")
        return con

    def save(self, summary, samples):
        con = self._con()
        try:
            cur = con.execute(
                "INSERT INTO sessions (game, start, duration, summary, samples)"
                " VALUES (?,?,?,?,?)",
                (summary["game"], summary["start"], summary["duration"],
                 json.dumps(summary),
                 zlib.compress(json.dumps(samples).encode("utf-8"))))
            sid = cur.lastrowid
            con.execute("DELETE FROM sessions WHERE id NOT IN (SELECT id FROM "
                        "sessions ORDER BY start DESC LIMIT ?)", (self.KEEP,))
            con.commit()
            return sid
        finally:
            con.close()

    def clear_live(self):
        """After a crash a session may still be marked as running: it is not."""
        try:
            con = self._con()
            try:
                for sid, text in con.execute(
                        "SELECT id, summary FROM sessions").fetchall():
                    s = json.loads(text)
                    if s.get("live"):
                        s["live"] = False
                        con.execute("UPDATE sessions SET summary=? WHERE id=?",
                                    (json.dumps(s), sid))
                con.commit()
            finally:
                con.close()
        except Exception:
            Logger.error("session clear_live")

    def update(self, sid, summary, samples):
        con = self._con()
        try:
            con.execute("UPDATE sessions SET game=?, start=?, duration=?, "
                        "summary=?, samples=? WHERE id=?",
                        (summary["game"], summary["start"], summary["duration"],
                         json.dumps(summary),
                         zlib.compress(json.dumps(samples).encode("utf-8")), sid))
            con.commit()
        finally:
            con.close()

    def list(self):
        """Newest first: [{'id', 'game', 'start', 'duration', 'summary'}]"""
        try:
            con = self._con()
            try:
                rows = con.execute("SELECT id, game, start, duration, summary "
                                   "FROM sessions ORDER BY start DESC").fetchall()
            finally:
                con.close()
        except Exception:
            Logger.error("session list")
            return []
        out = []
        for sid, game, start, dur, text in rows:
            try:
                out.append({"id": sid, "game": game, "start": start,
                            "duration": dur, "summary": json.loads(text)})
            except ValueError:
                continue
        return out


    def delete(self, ids):
        con = self._con()
        try:
            con.executemany("DELETE FROM sessions WHERE id=?", [(i,) for i in ids])
            con.commit()
        finally:
            con.close()


class SessionAnalyzer:
    """Turns the samples of one game session into evidence-based findings.

    Nothing is guessed: every finding says what was measured. A high
    temperature alone is never called throttling - the clock must also fall
    while the chip is fully loaded. Missing sensors give "cannot judge"."""
    STEP = 2.0              # seconds between samples
    GPU_HOT, CPU_HOT = 80, 90   # deg C above which a clock drop counts as thermal
    GPU_LOAD, CPU_LOAD = 90, 50
    GPU_DROP, CPU_DROP = 0.10, 0.15
    MIN_SECS = 6            # evidence must last this long
    HEAVY_CPU, HEAVY_MB = 3.0, 800

    @staticmethod
    def vals(xs):
        return [x for x in xs if x is not None]

    @classmethod
    def pct(cls, xs, p):
        xs = sorted(cls.vals(xs))
        return xs[min(len(xs) - 1, int(p / 100 * len(xs)))] if xs else None

    @classmethod
    def avg(cls, xs):
        xs = cls.vals(xs)
        return sum(xs) / len(xs) if xs else None

    @staticmethod
    def mx(xs):
        xs = [x for x in xs if x is not None]
        return max(xs) if xs else None

    @classmethod
    def throttle(cls, use, temp, clk, load_min, hot, drop, label, approx=False):
        """-> {'status', 'text', 'secs', 'base'}  (status: possible / clock_dip /
        hot_no_drop / ok / no_temp / no_clock / few)"""
        if not cls.vals(temp):
            return {"status": "no_temp", "secs": 0, "base": None,
                    "text": f"{label} temperature not available - cannot judge "
                            "throttling"}
        tmax = cls.mx(temp)
        peak = cls.mx(use)
        cool = {"status": "cool", "secs": 0, "base": None,
                "text": f"{label}: max {tmax:.0f} °C, under {hot} °C - thermal "
                        "throttling unlikely" + (f" (load peaked at {peak:.0f} %)"
                                                 if peak is not None else "")}
        loaded = [i for i in range(len(clk)) if clk[i] is not None
                  and use[i] is not None and use[i] >= load_min]
        if not cls.vals(clk):
            return cool if tmax < hot else {
                "status": "no_clock", "secs": 0, "base": None,
                "text": f"{label} clock not available - cannot tell "
                        "throttling from a hot chip"}
        if len(loaded) < 8:
            return cool if tmax < hot else {
                "status": "few", "secs": 0, "base": None,
                "text": f"{label} reached {tmax:.0f} °C but was rarely fully "
                        "loaded - too little data to judge throttling"}
        base = cls.pct([clk[i] for i in loaded], 90)
        lim = base * (1 - drop)
        dips = [i for i in loaded if clk[i] < lim]
        hot_dips = [i for i in dips if temp[i] is not None and temp[i] >= hot]
        note = " (clock reported by Windows - less exact)" if approx else ""
        if len(hot_dips) * cls.STEP >= cls.MIN_SECS:
            s = len(hot_dips) * cls.STEP
            return {"status": "possible", "secs": s, "base": base,
                    "text": f"Possible thermal throttling: {label} clock fell "
                            f"under {lim:.0f} MHz (usual {base:.0f}) for {s:.0f} s"
                            f" while at {hot}+ °C{note}"}
        if len(dips) * cls.STEP >= cls.MIN_SECS:
            s = len(dips) * cls.STEP
            return {"status": "clock_dip", "secs": s, "base": base,
                    "text": f"{label} clock dipped for {s:.0f} s but the chip was"
                            f" under {hot} °C - not thermal (power limit, game "
                            f"load or boost behaviour){note}"}
        if tmax is not None and tmax >= hot:
            return {"status": "hot_no_drop", "secs": 0, "base": base,
                    "text": f"{label} reached {tmax:.0f} °C but its clock did "
                            f"not fall - no evidence of throttling{note}"}
        return {"status": "ok", "secs": 0, "base": base,
                "text": f"{label}: no throttling evidence (max {tmax:.0f} °C, "
                        f"clock stable){note}"}

    @classmethod
    def drops(cls, c, g_base, c_base):
        """Moments where the frame rate fell far below the last minute."""
        fps, n = c["fps"], len(c["fps"])
        flagged = []
        for i in range(n):
            if fps[i] is None:
                continue
            past = cls.vals(fps[max(0, i - 30):i])
            if len(past) < 10:
                continue
            med = sorted(past)[len(past) // 2]
            if med >= 20 and fps[i] < 0.6 * med:
                flagged.append((i, med))
        groups = []
        for i, med in flagged:
            if groups and i - groups[-1][-1][0] <= 5:
                groups[-1].append((i, med))
            else:
                groups.append([(i, med)])
        out = []
        for g in groups:
            i0, i1 = g[0][0], g[-1][0]
            lo = min(c["fps"][i] for i, _ in g)
            med = g[0][1]
            out.append({"at": c["t"][i0] - c["t"][0], "secs": (i1 - i0 + 1) * cls.STEP,
                        "before": med, "low": lo,
                        "cause": cls.cause(c, max(0, i0 - 1), min(n - 1, i1 + 1),
                                           g_base, c_base)})
        out.sort(key=lambda e: e["low"] / e["before"])
        return sorted(out[:30], key=lambda e: e["at"])

    @classmethod
    def cause(cls, c, a, b, g_base, c_base):
        def m(key):
            return cls.avg(c[key][a:b + 1])
        ram, avail = m("ram"), m("avail")
        gt, gk, gu = m("g_temp"), m("g_clk"), m("g_use")
        ct, ck, cu = m("c_temp"), m("c_clk"), m("c_use")
        if (ram is not None and ram >= 90) or (avail is not None and avail < 1.5):
            return "RAM was nearly full"
        if gt is not None and gk and g_base and gt >= cls.GPU_HOT \
                and gk < g_base * (1 - cls.GPU_DROP):
            return "GPU clock fell while hot (possible thermal throttling)"
        if ct is not None and ck and c_base and ct >= cls.CPU_HOT \
                and ck < c_base * (1 - cls.CPU_DROP):
            return "CPU clock fell while hot (possible thermal throttling)"
        if gu is not None and gu >= 95:
            return "GPU was fully loaded (GPU-limited moment)"
        if cu is not None and cu >= 90:
            return "CPU was fully loaded (CPU-limited moment)"
        return "No limit visible in the recorded sensors"

    @classmethod
    def memory(cls, c):
        ram, avail = c["ram"], c["avail"]
        bad = [i for i in range(len(ram)) if (ram[i] is not None and ram[i] >= 90)
               or (avail[i] is not None and avail[i] < 1.5)]
        peak = cls.mx(ram)
        if peak is None:
            return {"status": "unknown", "text": "RAM usage was not recorded"}
        if len(bad) * cls.STEP >= cls.MIN_SECS:
            low = min(cls.vals(avail)) if cls.vals(avail) else None
            extra = f", lowest free {low:.1f} GB" if low is not None else ""
            return {"status": "low", "text": f"Low RAM: {len(bad) * cls.STEP:.0f}"
                    f" s at 90%+ used (peak {peak:.0f}%{extra})"}
        return {"status": "ok", "text": f"RAM was fine (peak {peak:.0f}% used)"}

    @classmethod
    def vram(cls, c):
        used, tot = c["vram"], c["vram_total"]
        fr = [used[i] / tot[i] for i in range(len(used))
              if used[i] is not None and tot[i]]
        if not fr:
            return {"status": "unknown", "text": "VRAM usage not available"}
        full = [f for f in fr if f >= 0.95]
        if len(full) * cls.STEP >= cls.MIN_SECS:
            return {"status": "full", "text": f"VRAM was almost full for "
                    f"{len(full) * cls.STEP:.0f} s (peak {max(fr) * 100:.0f}%) "
                    "- textures may be swapped to RAM"}
        return {"status": "ok", "text": f"VRAM was fine (peak {max(fr) * 100:.0f}%)"}

    @classmethod
    def apps(cls, scans, n_scans):
        """scans: {name: [cpu_sum, peak_rss_bytes]} -> heavy background apps."""
        out = []
        for name, (cpu_sum, rss) in scans.items():
            cpu = cpu_sum / max(1, n_scans)
            mb = rss / 1024 ** 2
            if cpu >= cls.HEAVY_CPU or mb >= cls.HEAVY_MB:
                out.append({"name": name, "cpu": round(cpu, 1), "mb": round(mb)})
        out.sort(key=lambda a: a["cpu"] * 10 + a["mb"] / 100, reverse=True)
        return out[:12]

    @classmethod
    def summarize(cls, c, meta, frames):
        """c: dict of equal-length lists. meta: names/times. frames: dict with
        count / total_ms / low1 / low01 from PresentMon's frame times."""
        n = len(c["t"])
        approx = bool(meta.get("c_approx"))
        gt = cls.throttle(c["g_use"], c["g_temp"], c["g_clk"], cls.GPU_LOAD,
                          cls.GPU_HOT, cls.GPU_DROP, "GPU")
        ct = cls.throttle(c["c_use"], c["c_temp"], c["c_clk"], cls.CPU_LOAD,
                          cls.CPU_HOT, cls.CPU_DROP, "CPU", approx)
        mem, vr = cls.memory(c), cls.vram(c)
        apps = cls.apps(meta.get("apps", {}), meta.get("scans", 0))
        events = cls.drops(c, gt["base"], ct["base"])
        finds = []

        def add(sev, title, text):
            finds.append({"sev": sev, "title": title, "text": text})
        for key, title, r in (("gpu", "GPU temperature / clock", gt),
                              ("cpu", "CPU temperature / clock", ct)):
            sev = {"possible": "warn", "clock_dip": "notice", "ok": "ok",
                   "cool": "ok", "hot_no_drop": "notice"}.get(r["status"], "unknown")
            add(sev, title, r["text"])
        add({"low": "warn", "ok": "ok"}.get(mem["status"], "unknown"),
            "RAM", mem["text"])
        add({"full": "notice", "ok": "ok"}.get(vr["status"], "unknown"),
            "VRAM", vr["text"])
        heavy = [a for a in apps]
        if heavy:
            names = ", ".join(a["name"] for a in heavy[:3])
            add("notice", "Background apps",
                f"{len(heavy)} heavy app(s) ran during the game, e.g. {names}")
        else:
            add("ok", "Background apps", "No heavy background apps seen")
        if events:
            worst = min(events, key=lambda e: e["low"] / e["before"])
            add("notice", "Frame-rate drops",
                f"{len(events)} drop(s); worst: {worst['before']:.0f} -> "
                f"{worst['low']:.0f} FPS - {worst['cause']}")
        else:
            add("ok", "Frame-rate drops", "No big frame-rate drops")
        a = cls.avg
        return {
            "game": meta["game"], "start": meta["start"], "end": meta["end"],
            "duration": meta["end"] - meta["start"], "samples": n,
            "cpu_name": meta.get("cpu_name", ""), "gpu_name": meta.get("gpu_name", ""),
            "avg_fps": (1000.0 * frames["count"] / frames["total_ms"]
                        if frames.get("total_ms") else None),
            "low1": frames.get("low1"), "low01": frames.get("low01"),
            "frames": frames.get("count", 0),
            "c_use": [a(c["c_use"]), cls.mx(c["c_use"])],
            "g_use": [a(c["g_use"]), cls.mx(c["g_use"])],
            "ram": [a(c["ram"]), cls.mx(c["ram"])],
            "c_temp": [a(c["c_temp"]), cls.mx(c["c_temp"])],
            "g_temp": [a(c["g_temp"]), cls.mx(c["g_temp"])],
            "c_clk": [a(c["c_clk"]), cls.mx(c["c_clk"])],
            "g_clk": [a(c["g_clk"]), cls.mx(c["g_clk"])],
            "vram_peak": cls.mx(c["vram"]), "vram_total": cls.mx(c["vram_total"]),
            "c_approx": approx, "gpu_status": gt["status"],
            "cpu_status": ct["status"], "mem_status": mem["status"],
            "findings": finds, "drops": events, "apps": apps,
        }


class SessionRecorder:
    """Watches for a game (a program that draws frames in front, seen by
    PresentMon), records it every 2 s and saves a session when it ends.

    Programs that are almost never games (browsers, players) are ignored.
    Sessions shorter than a minute are dropped. step() does one cycle and
    runs in a worker thread, so the window never waits for it."""
    STEP = 2.0
    START_AFTER = 6         # s of steady frames before a session starts
    END_AFTER = 20          # s without frames = the game ended
    MIN_SECONDS = 60
    SCAN_EVERY = 5          # background-app scan every N samples (10 s)
    CHECKPOINT = 15         # save the running session every N samples (30 s)
    IGNORE = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
              "vivaldi.exe", "vlc.exe", "mpv.exe", "wmplayer.exe", "spotify.exe",
              "discord.exe", "steamwebhelper.exe", "steam.exe", "obs64.exe",
              "teams.exe", "slack.exe", "code.exe", "devenv.exe", "notepad.exe",
              "searchhost.exe", "startmenuexperiencehost.exe",
              "shellexperiencehost.exe", "taskmgr.exe", "mspaint.exe"}
    SKIP_APPS = {"system idle process", "system", "registry", "memcompression",
                 "presentmon.exe", "lmonitor.exe", "python.exe", "pythonw.exe",
                 "searchindexer.exe", "msmpeng.exe"}
    KEYS = ("t", "fps", "c_use", "c_temp", "c_clk", "g_use", "g_temp", "g_clk",
            "g_pow", "vram", "vram_total", "ram", "avail")

    def __init__(self, fps, cpu, gpu, store, enabled=lambda: True):
        self.fps, self.cpu, self.gpu, self.store = fps, cpu, gpu, store
        self.enabled = enabled
        self.load = CpuLoad()
        self.cur = None
        self.cand = None            # (pid, since) while a game is being confirmed
        self.busy = False
        self.version = 0            # +1 whenever a session was saved
        self.last_id = None
        self.procs = {}             # psutil.Process objects (cpu% needs history)

    # ---- scheduling
    def tick(self):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            self.step(time.time())
        except Exception:
            Logger.error("session step")
        finally:
            self.busy = False

    # ---- one cycle
    def step(self, now):
        if not self.enabled():
            self.cand = None
            if self.cur is not None:
                self.finish(now)
            return
        if self.cur is None:
            self._look_for_game(now)
        else:
            self._sample(now)

    def _look_for_game(self, now):
        cur = self.fps.current()
        if cur is None or cur[1].lower() in self.IGNORE:
            self.cand = None
            return
        pid, name = cur
        if self.cand is None or self.cand[0] != pid:
            self.cand = (pid, now)
            return
        if now - self.cand[1] >= self.START_AFTER:
            base = self.fps.counters(pid)
            if base is None:
                return
            self.cand = None
            self.cur = {"pid": pid, "name": name, "start": now, "base": base,
                        "last": base[:2], "last_frame": now, "n": 0,
                        "c": {k: [] for k in self.KEYS}, "apps": {},
                        "scans": 0, "approx": False, "hist": base[2],
                        "sid": None}

    def _sample(self, now):
        cur, fps = self.cur, self.fps
        if not fps.recent(cur["pid"], self.END_AFTER):
            self.finish(cur["last_frame"])
            return
        c = cur["c"]
        counters = fps.counters(cur["pid"])
        f = None
        if counters is not None:
            dc, dms = counters[0] - cur["last"][0], counters[1] - cur["last"][1]
            cur["last"] = counters[:2]
            cur["hist"] = counters[2]   # kept: PresentMon forgets a program 10 s after its last frame
            if dc > 0 and dms > 0:
                f = 1000.0 * dc / dms
                cur["last_frame"] = now
        vm = psutil.virtual_memory()
        ct = cc = None
        try:
            ct, _, cc, approx = self.cpu.read(True, False, True)
            cur["approx"] = cur["approx"] or approx
        except Exception:
            Logger.error("session cpu")
        gu = gt = gp = gk = mem = None
        try:
            gu, gt, gp, gk, mem = self.gpu.read(Telemetry.ALL)
        except Exception:
            Logger.error("session gpu")
        row = {"t": now, "fps": f, "c_use": self.load.read(), "c_temp": ct,
               "c_clk": cc, "g_use": gu, "g_temp": gt, "g_clk": gk, "g_pow": gp,
               "vram": mem[0] if mem else None,
               "vram_total": mem[1] if mem else None,
               "ram": vm.percent, "avail": vm.available / 1024 ** 3}
        for k in self.KEYS:
            c[k].append(row[k])
        cur["n"] += 1
        if cur["n"] % self.SCAN_EVERY == 1:
            self._scan_apps(cur)
        if cur["n"] % self.CHECKPOINT == 0 and now - cur["start"] >= self.MIN_SECONDS:
            self._save(cur, now, live=True)   # visible in the list while playing

    def _scan_apps(self, cur):
        """CPU % (of the whole PC) and memory per program name."""
        me = os.getpid()
        seen, per = set(), {}
        ncpu = psutil.cpu_count() or 1
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pid, name = p.info["pid"], (p.info["name"] or "").lower()
                if pid in (cur["pid"], me) or not name or name in self.SKIP_APPS:
                    continue
                seen.add(pid)
                pr = self.procs.get(pid)
                if pr is None:
                    pr = self.procs[pid] = p
                cpu = pr.cpu_percent(None) / ncpu
                rss = pr.memory_info().rss
                e = per.setdefault(name, [0.0, 0])
                e[0] += cpu
                e[1] += rss
            except (psutil.Error, OSError):
                continue
        for pid in [k for k in self.procs if k not in seen]:
            del self.procs[pid]
        if cur["n"] > 1:   # the first pass only primes the CPU counters
            cur["scans"] += 1
            for name, (cpu, rss) in per.items():
                e = cur["apps"].setdefault(name, [0.0, 0])
                e[0] += cpu
                e[1] = max(e[1], rss)

    # ---- end of a session
    def finish(self, end):
        cur, self.cur = self.cur, None
        if cur is None:
            return None
        if end - cur["start"] < self.MIN_SECONDS or cur["n"] < 5:
            return None
        return self._save(cur, end, live=False)

    def _save(self, cur, end, live):
        """Write the session so far (a new row, then updates of that row).
        Uses the counters kept at the last sample: PresentMon may already have
        forgotten the program when the game has just closed."""
        b = cur["base"]
        count, ms = cur["last"][0] - b[0], cur["last"][1] - b[1]
        hist = [x - y for x, y in zip(cur["hist"], b[2])]
        frames = {"count": count, "total_ms": ms}
        frames.update(FpsMonitor.lows(hist, count))
        meta = {"game": cur["name"], "start": cur["start"], "end": end,
                "c_approx": cur["approx"], "apps": cur["apps"],
                "scans": cur["scans"], "cpu_name": getattr(self.cpu, "name", ""),
                "gpu_name": self.gpu.display_name()}
        summary = SessionAnalyzer.summarize(cur["c"], meta, frames)
        summary["live"] = live
        try:
            if cur["sid"] is None:
                cur["sid"] = self.store.save(summary, cur["c"])
            else:
                self.store.update(cur["sid"], summary, cur["c"])
        except Exception:
            Logger.error("session save")
            return None
        self.last_id = cur["sid"]
        self.version += 1
        return self.last_id

    def stop(self):
        if self.cur is not None:
            self.finish(time.time())

    # ---- what the window shows
    def status(self):
        """-> (text, recording?)"""
        cur = self.cur
        if not self.enabled():
            return "Session recording is off", False
        if cur is not None:
            s = int(time.time() - cur["start"])
            return (f"Recording {cur['name']}  {s // 3600:d}:{s % 3600 // 60:02d}"
                    f":{s % 60:02d}", True)
        if not self.fps.alive:
            return "Waiting for PresentMon: " + (self.fps.status or "not started"), False
        return "Waiting for a game (a program drawing frames in front)", False


class SessionView:
    """Text rows for the Sessions page (same row format as the Hardware page)."""

    @staticmethod
    def clock(sec):
        sec = int(sec)
        return (f"{sec // 3600:d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"
                if sec >= 3600 else f"{sec // 60:d}:{sec % 60:02d}")

    @staticmethod
    def pair(v, unit="", spec=".0f"):
        if not v or v[0] is None:
            return "n/a"
        return f"{v[0]:{spec}}{unit}  (max {v[1]:{spec}}{unit})"

    @staticmethod
    def wrap(text, first, width=54):
        return [("row", "  " + ln, "") for ln in textwrap.wrap(text, width) or [""]]

    SEV = {"ok": ("OK", "C_OK"), "notice": ("Notice", "YELLOW"),
           "warn": ("Warning", "RED"), "unknown": ("Unknown", "DIM")}

    @classmethod
    def sev(cls, key):
        word, col = cls.SEV.get(key, cls.SEV["unknown"])
        return word, getattr(Theme, col)

    @classmethod
    def rows_summary(cls, s):
        if s is None:
            return [("row", "Select a session in the list above", "")]
        f = lambda v, u="", sp=".0f": "n/a" if v is None else f"{v:{sp}}{u}"
        when = time.strftime("%d %b %Y  %H:%M", time.localtime(s["start"]))
        lows = " / ".join("n/a" if s[k] is None else f"{s[k]:.1f}"
                          for k in ("low1", "low01"))
        rows = [("row", s["game"], f"{when}   {cls.clock(s['duration'])}"),
                ("head", "Frame rate (from PresentMon frame times)"),
                ("row", "Average FPS", f(s["avg_fps"], "", ".1f")),
                ("row", "1% low / 0.1% low", lows),
                ("head", "Load"),
                ("row", "CPU usage", cls.pair(s["c_use"], " %")),
                ("row", "GPU usage", cls.pair(s["g_use"], " %")),
                ("row", "RAM used", cls.pair(s["ram"], " %")),
                ("row", "VRAM peak", "n/a" if s.get("vram_peak") is None
                 or not s.get("vram_total") else
                 f"{s['vram_peak']:.1f} / {s['vram_total']:.1f} GB"),
                ("head", "Temperature and clocks"),
                ("row", "CPU temperature", cls.pair(s["c_temp"], " °C")),
                ("row", "GPU temperature", cls.pair(s["g_temp"], " °C")),
                ("row", "CPU clock", cls.pair(s["c_clk"], " MHz")
                 + ("  ~" if s.get("c_approx") else "")),
                ("row", "GPU clock", cls.pair(s["g_clk"], " MHz"))]
        return rows

    @classmethod
    def rows_findings(cls, s):
        if s is None:
            return [("row", "Select a session in the list above", "")]
        rows = []
        for fd in s["findings"]:
            word, col = cls.sev(fd["sev"])
            rows.append(("row", fd["title"], word, col))
            rows += cls.wrap(fd["text"], "", 74)
        if len(rows) <= 11:
            rows.append(("row", "", ""))
            rows += cls.wrap("Shown only when the sensors prove it. 'Unknown' = "
                             "a sensor was missing, not 'fine'.", "", 92)
        return rows

    @classmethod
    def rows_drops(cls, s):
        if s is None:
            return [("row", "Select a session in the list above", "")]
        if not s["drops"]:
            return [("head", "Frame-rate drops"),
                    ("row", "No drop below 60% of the previous minute", "OK",
                     Theme.C_OK)]
        rows = [("head", f"{len(s['drops'])} frame-rate drop(s)")]
        for e in s["drops"]:
            rows.append(("row", f"at {cls.clock(e['at'])}  ({e['secs']:.0f} s)",
                         f"{e['before']:.0f} -> {e['low']:.0f} FPS", Theme.YELLOW))
            rows.append(("row", "  " + e["cause"], ""))
        return rows

    @classmethod
    def rows_apps(cls, s):
        if s is None:
            return [("row", "Select a session in the list above", "")]
        if not s["apps"]:
            return [("head", "Background apps"),
                    ("row", "No heavy background apps were seen", "OK", Theme.C_OK)]
        rows = [("head", "Heavy background apps during the game")]
        for a in s["apps"]:
            mem = f"{a['mb'] / 1024:.1f} GB" if a["mb"] >= 1024 else f"{a['mb']} MB"
            rows.append(("row", a["name"], f"CPU {a['cpu']:.1f} %   RAM {mem}",
                         Theme.YELLOW))
        rows.append(("row", "", ""))
        rows += cls.wrap(f"Listed: average over {SessionAnalyzer.HEAVY_CPU:.0f} % "
                         f"of the PC's CPU or over {SessionAnalyzer.HEAVY_MB} MB. "
                         "Close what you do not need before playing.", "")
        return rows

    # (label, key, lower-is-better, number format, unit)
    CMP = [("Average FPS", "avg_fps", False, ".1f", ""),
           ("1% low FPS", "low1", False, ".1f", ""),
           ("CPU temp (max)", ("c_temp", 1), True, ".0f", " °C"),
           ("GPU temp (max)", ("g_temp", 1), True, ".0f", " °C"),
           ("CPU usage (avg)", ("c_use", 0), True, ".0f", " %"),
           ("GPU usage (avg)", ("g_use", 0), None, ".0f", " %"),
           ("RAM used (peak)", ("ram", 1), True, ".0f", " %")]

    @staticmethod
    def _get(s, key):
        if isinstance(key, tuple):
            v = s.get(key[0])
            return v[key[1]] if v else None
        return s.get(key)


    STAT = {"possible": "possible throttle", "clock_dip": "clock dip",
            "hot_no_drop": "hot, no drop", "ok": "none seen", "cool": "none seen",
            "low": "low RAM",
            "no_temp": "unknown", "no_clock": "unknown", "few": "unknown",
            "unknown": "unknown"}

    @staticmethod
    def title(sess):
        s = sess["summary"]
        when = time.strftime("%d %b %H:%M", time.localtime(sess["start"]))
        fps = s.get("avg_fps")
        return (("● " if s.get("live") else "") + f"{s['game']}",
                f"{when}  {SessionView.clock(s['duration'])}"
                + (f"  {fps:.0f} fps" if fps else ""))


# =============================================================== Diagnostics
class ScanStore:
    """The last scans (issues only), kept in %APPDATA%\\Lmonitor\\scans.json.
    Reports and before/after comparisons read them later."""
    KEEP = 20

    def __init__(self, path=None):
        self.path = path or os.path.join(Paths.CFG_DIR, "scans.json")

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def add(self, scan):
        scans = (self.load() + [scan])[-self.KEEP:]
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(scans, f)
            os.replace(tmp, self.path)
        except Exception:
            Logger.error("scan store")


class DiagCollector:
    """Reads the facts from Windows (PowerShell, registry, psutil). Every
    reader returns None when Windows did not answer - never a guess."""
    RUN_KEYS = [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
                ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
                ("HKLM", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")]
    APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
    CHECKS = ["Startup items", "Power plan", "Disk space", "Event Log",
              "Drivers", "Devices", "Services", "Settings", "Memory"]

    @staticmethod
    def _reg(hive, path, name=None):
        import winreg
        h = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}[hive]
        key = winreg.OpenKey(h, path)
        try:
            return winreg.QueryValueEx(key, name)[0] if name is not None else key
        except OSError:
            return None

    @classmethod
    def reg_value(cls, hive, path, name):
        try:
            return cls._reg(hive, path, name)
        except Exception:
            return None

    # ---- each reader
    @classmethod
    def startup(cls):
        return [{"name": i["name"], "cmd": i["cmd"], "where": i["where"],
                 "enabled": i["enabled"]} for i in StartupManager.list()]

    @staticmethod
    def power():
        out = SystemInfo._powershell("powercfg /getactivescheme", 8)
        m = re.search(r"([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})\s*\(([^)]*)\)", out or "")
        if not m:
            return None
        return {"guid": m.group(1).lower(), "name": m.group(2)}

    @staticmethod
    def battery():
        try:
            b = psutil.sensors_battery()
        except Exception:
            b = None
        return {"present": b is not None, "plugged": bool(b.power_plugged) if b else None}

    @staticmethod
    def disks():
        out = []
        for p in psutil.disk_partitions(all=False):
            if "cdrom" in p.opts or not p.fstype:
                continue
            try:
                u = psutil.disk_usage(p.mountpoint)
            except OSError:
                continue
            out.append({"mount": p.mountpoint, "total": u.total, "free": u.free})
        return out

    @classmethod
    def events(cls):
        rows = SystemInfo._json_t(
            "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2,3; "
            "StartTime=(Get-Date).AddDays(-7)} -MaxEvents 1500 -ErrorAction "
            "SilentlyContinue | Select-Object ProviderName,Id,Level,"
            "@{n='T';e={$_.TimeCreated.ToString('s')}} | ConvertTo-Json -Compress", 40)
        return [{"p": str(r.get("ProviderName") or ""), "id": int(r.get("Id") or 0),
                 "lvl": int(r.get("Level") or 0), "t": str(r.get("T") or "")}
                for r in rows]

    @staticmethod
    def gpu_drivers():
        rows = SystemInfo._json_t(
            "Get-CimInstance Win32_VideoController | Select-Object Name,"
            "DriverVersion,@{n='Date';e={if($_.DriverDate){$_.DriverDate.ToString("
            "'yyyy-MM-dd')}else{''}}} | ConvertTo-Json -Compress", 20)
        return [{"name": str(r.get("Name") or ""), "ver": str(r.get("DriverVersion") or ""),
                 "date": str(r.get("Date") or "")} for r in rows]

    @staticmethod
    def problem_devices():
        rows = SystemInfo._json_t(
            "Get-CimInstance Win32_PnPEntity | Where-Object {$_.ConfigManagerErrorCode"
            " -ne 0 -and $_.ConfigManagerErrorCode -ne 22} | Select-Object Name,"
            "PNPClass,ConfigManagerErrorCode | ConvertTo-Json -Compress", 25)
        return [{"name": str(r.get("Name") or "?"), "cls": str(r.get("PNPClass") or ""),
                 "code": r.get("ConfigManagerErrorCode")} for r in rows]

    @staticmethod
    def services():
        rows = SystemInfo._json_t(
            "Get-Service -Name SysMain,WSearch,DiagTrack,wuauserv,Audiosrv "
            "-ErrorAction SilentlyContinue | Select-Object Name,@{n='S';e={\"$($_.Status)\"}}"
            ",@{n='T';e={\"$($_.StartType)\"}} | ConvertTo-Json -Compress", 15)
        return {str(r.get("Name")): {"status": str(r.get("S")), "start": str(r.get("T"))}
                for r in rows}

    @classmethod
    def settings(cls):
        g = cls.reg_value
        return {
            "game_mode": g("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled"),
            "game_dvr": g("HKCU", r"System\GameConfigStore", "GameDVR_Enabled"),
            "capture": g("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                         "AppCaptureEnabled"),
            "hags": g("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode"),
            "fast_startup": g("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                              "HiberbootEnabled")}

    @staticmethod
    def memory():
        vm, sw = psutil.virtual_memory(), psutil.swap_memory()
        return {"ram_gb": vm.total / 1024 ** 3, "swap_gb": sw.total / 1024 ** 3}

    @classmethod
    def collect(cls, progress=lambda i, n, name: None):
        """-> facts dict. A reader that fails gives None and an entry in errors."""
        steps = [("startup", cls.startup), ("power", cls.power), ("battery", cls.battery),
                 ("disks", cls.disks), ("events", cls.events),
                 ("gpu_drivers", cls.gpu_drivers), ("devices", cls.problem_devices),
                 ("services", cls.services), ("settings", cls.settings),
                 ("memory", cls.memory)]
        facts, errors = {}, {}
        for i, (key, fn) in enumerate(steps):
            progress(i, len(steps), key)
            try:
                facts[key] = fn()
            except Exception as e:
                facts[key] = None
                errors[key] = (str(e) or type(e).__name__)[:120]
                Logger.error(f"diagnostics: {key}")
        facts["errors"] = errors
        return facts


class DiagAnalyzer:
    """Turns facts into issues. An issue = {id, area, title, sev, evidence,
    explain, fix, open}. sev: ok / info / notice / warn / unknown.

    'warn' needs hard evidence. A missing answer is 'unknown', never red.
    Thresholds that are our own choice are named in the text."""
    GIB = 1024 ** 3
    PLANS = {"381b4222-f694-41f0-9685-ff5bb260df2e": "balanced",
             "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "high",
             "a1841308-3541-4fab-bc81-f71556f20b4a": "saver",
             "e9a42b02-d5df-448d-aa00-03f14749eb61": "ultimate"}
    STARTUP_MANY = 10               # our threshold for "many" enabled items
    LOW_FREE_PCT, CRIT_FREE_PCT, LOW_FREE_GB = 20, 10, 10
    DRIVER_OLD_DAYS = 365
    ORDER = {"warn": 0, "notice": 1, "unknown": 2, "info": 3, "ok": 4}
    SEV_WORD = {"warn": "Warning", "notice": "Notice", "unknown": "Unknown",
                "info": "Info", "ok": "OK"}

    @staticmethod
    def issue(id_, area, title, sev, evidence, explain, fix, open_=None):
        return {"id": id_, "area": area, "title": title, "sev": sev,
                "evidence": list(evidence), "explain": explain, "fix": fix,
                "open": open_}

    @classmethod
    def unknown(cls, id_, area, title, facts, key):
        why = (facts.get("errors") or {}).get(key) or "Windows did not answer"
        return cls.issue(id_, area, title, "unknown", [why],
                         "This check could not be done, so nothing can be said "
                         "about it - it is not a sign of a problem.",
                         "Run the scan again. If it stays unknown, the Windows "
                         "component may be disabled or blocked.")

    @classmethod
    def analyze(cls, facts, now=None):
        out = []
        for fn in (cls.startup, cls.power, cls.disks, cls.events, cls.drivers,
                   cls.devices, cls.memory, cls.services, cls.settings):
            try:
                out += fn(facts)
            except Exception:
                Logger.error(f"diagnostics analyze {fn.__name__}")
        out.sort(key=lambda i: (cls.ORDER[i["sev"]], i["area"]))
        return out

    # ---- startup
    @classmethod
    def startup(cls, f):
        items = f.get("startup")
        if items is None:
            return [cls.unknown("startup", "Startup", "Startup items", f, "startup")]
        on = [i for i in items if i["enabled"]]
        off = len(items) - len(on)
        ev = [f"{len(on)} enabled, {off} disabled (Run keys, Startup folders)"]
        ev += [f"{i['name']}  -  {i['where']}" for i in on[:6]]
        if len(on) > 6:
            ev.append(f"+{len(on) - 6} more")
        many = len(on) >= cls.STARTUP_MANY
        return [cls.issue(
            "startup", "Startup", "Programs that start with Windows",
            "notice" if many else "ok", ev,
            ("Programs that start with Windows use memory and some CPU in the "
             "background and slow the start. "
             + (f"{len(on)} is above our guideline of {cls.STARTUP_MANY}."
                if many else "The number is reasonable.")
             + " Only you know which ones you need, so Lmonitor judges none."),
            "Open Startup Apps and switch off what you do not need at every start. "
            "You can switch it on again at any time.",
            "ms-settings:startupapps")]

    # ---- power plan
    @classmethod
    def power(cls, f):
        p = f.get("power")
        if p is None:
            return [cls.unknown("power", "Power", "Power plan", f, "power")]
        kind = cls.PLANS.get(p["guid"], "custom")
        bat = f.get("battery") or {}
        laptop, plugged = bat.get("present"), bat.get("plugged")
        ev = [f"Active plan: {p['name']}"]
        if laptop:
            ev.append("Laptop, " + ("plugged in" if plugged else "on battery"))
        if kind == "saver" and not (laptop and not plugged):
            return [cls.issue(
                "power", "Power", "Power plan limits performance", "notice", ev,
                "Power saver holds the CPU back to save energy. That costs frame "
                "rate in games" + (" - and you are plugged in, so there is no "
                                   "battery reason for it." if laptop else "."),
                "Switch to Balanced, or to High performance for gaming.",
                "control powercfg.cpl")]
        if kind == "custom":
            return [cls.issue(
                "power", "Power", "Power plan", "info", ev,
                "This is a custom plan, so Lmonitor cannot say whether it limits "
                "performance.", "Nothing to do unless games feel slow; then try "
                "Balanced or High performance.", "control powercfg.cpl")]
        note = {"balanced": "Balanced is fine for most PCs.",
                "high": "High performance keeps clocks up - good for gaming.",
                "ultimate": "Ultimate Performance keeps clocks up - good for gaming.",
                "saver": "Power saver on battery is normal."}[kind]
        return [cls.issue("power", "Power", "Power plan", "ok", ev, note,
                          "No change needed.", "control powercfg.cpl")]

    # ---- disk space
    @classmethod
    def disks(cls, f):
        disks = f.get("disks")
        if disks is None:
            return [cls.unknown("disks", "Storage", "Free disk space", f, "disks")]
        out = []
        for d in disks:
            if not d["total"]:
                continue
            pct = 100.0 * d["free"] / d["total"]
            gb = d["free"] / cls.GIB
            ev = [f"{d['mount']}  {gb:.1f} GB free of {d['total'] / cls.GIB:.0f} GB "
                  f"({pct:.0f} % free)"]
            if pct < cls.CRIT_FREE_PCT or gb < cls.LOW_FREE_GB:
                sev = "warn"
            elif pct < cls.LOW_FREE_PCT:
                sev = "notice"
            else:
                sev = "ok"
            low = sev != "ok"
            out.append(cls.issue(
                "disk_" + d["mount"].rstrip(":\\").lower(), "Storage",
                f"Free space on {d['mount'].rstrip(chr(92))}", sev, ev,
                ("Windows and games need free space for updates, the page file, "
                 "shader caches and saves. Below "
                 f"{cls.CRIT_FREE_PCT} % or {cls.LOW_FREE_GB} GB free (our limits) "
                 "things get slow or fail." if low else "Enough free space."),
                ("Uninstall games you no longer play, empty the recycle bin or use "
                 "Storage Sense. Storage & Cleanup (next) lists what is safe to "
                 "remove." if low else "No change needed."),
                "ms-settings:storagesense" if low else None))
        return out

    # ---- event log
    GROUPS = [
        ("kernel41", "Unexpected shutdowns / restarts",
         lambda p, i: "kernel-power" in p and i == 41, "warn",
         "Windows found that the PC did not shut down cleanly: it crashed, hung, "
         "or lost power (Microsoft: Kernel-Power event 41). The event alone does "
         "not say which.",
         "Check temperatures and the power supply, undo any overclock, and test "
         "the memory. Event Viewer shows the details."),
        ("whea", "Hardware errors reported (WHEA)",
         lambda p, i: "whea" in p, None,
         "The CPU / PCIe hardware reported an error to Windows. Corrected "
         "(Warning) errors are usually harmless when they are rare; "
         "uncorrected (Error) ones are serious.",
         "Update the BIOS and chipset / GPU drivers, undo overclocking and XMP / "
         "EXPO if you use it, and re-seat cards and memory if it keeps happening."),
        ("tdr", "Graphics driver stopped responding",
         lambda p, i: p == "display" and i == 4101, "notice",
         "The graphics driver hung and Windows reset it (Timeout Detection and "
         "Recovery). You may have seen the screen flicker or a game crash.",
         "Install the latest graphics driver, close overlays and tools you do "
         "not need, and check GPU temperature and any overclock."),
        ("storage", "Disk / file system errors",
         lambda p, i: (p in ("disk", "storport", "stornvme", "iastora", "iastorv")
                       and i in (7, 11, 51, 129, 153, 157))
                      or ("ntfs" in p and i in (50, 55, 98, 140)), "warn",
         "Windows logged errors from a drive or the file system (for example "
         "paging errors, retried I/O, or file system corruption). A failing "
         "drive, a loose cable or a driver can cause them.",
         "Back up important files first. Then check the drive's health (Hardware "
         "> Storage) and run 'chkdsk' on the volume."),
        ("bugcheck", "Blue screen (crash) reports",
         lambda p, i: ("systemerrorreporting" in p or p == "bugcheck") and i == 1001, "warn",
         "Windows recorded that it restarted after a crash (blue screen).",
         "Note the stop code in Event Viewer; common causes are drivers, "
         "memory and overheating."),
    ]

    @classmethod
    def events(cls, f):
        ev = f.get("events")
        if ev is None:
            return [cls.unknown("events", "Event Log", "System Event Log (7 days)",
                                f, "events")]
        out, used = [], set()
        for key, title, test, sev, why, fix in cls.GROUPS:
            hit = [e for e in ev if test(e["p"].lower(), e["id"])]
            if not hit:
                continue
            used.update(id(e) for e in hit)
            s = sev
            if key == "whea":
                errs = [e for e in hit if e["lvl"] <= 2]
                s = "warn" if errs else ("notice" if len(hit) >= 5 else "info")
            ids = sorted({(e["p"], e["id"]) for e in hit})[:4]
            last = max(e["t"] for e in hit)
            evid = [f"{len(hit)} event(s) in 7 days, last {last.replace('T', ' ')}",
                    "Sources: " + ", ".join(f"{p} {i}" for p, i in ids)]
            if key == "kernel41" and len(hit) == 1:
                s = "notice"     # a single one can be a power cut
            out.append(cls.issue("ev_" + key, "Event Log", title, s, evid, why,
                                 fix, "eventvwr.msc"))
        rest = [e for e in ev if id(e) not in used and e["lvl"] <= 2]
        if rest:
            top = {}
            for e in rest:
                top[(e["p"], e["id"])] = top.get((e["p"], e["id"]), 0) + 1
            best = sorted(top.items(), key=lambda kv: -kv[1])[:3]
            out.append(cls.issue(
                "ev_other", "Event Log", "Other errors in the System log", "info",
                [f"{len(rest)} error event(s) in 7 days"]
                + [f"{p} {i}: {n}x" for (p, i), n in best],
                "These are not ones Lmonitor recognises as a PC-health problem. "
                "Many Windows errors are harmless, so this is only shown for "
                "your information.",
                "Only act if you also see crashes or slowdowns - then look the "
                "source up in Event Viewer.", "eventvwr.msc"))
        if not out:
            out.append(cls.issue(
                "ev_clean", "Event Log", "System Event Log (7 days)", "ok",
                [f"{len(ev)} warning/error events checked, no known problem"],
                "No crash, hardware error or disk error was logged in the last 7 days.",
                "No change needed.", "eventvwr.msc"))
        return out

    # ---- drivers
    @classmethod
    def drivers(cls, f, today=None):
        drv = f.get("gpu_drivers")
        if drv is None:
            return [cls.unknown("gpu_driver", "Drivers", "Graphics driver", f, "gpu_drivers")]
        out = []
        today = today or time.strftime("%Y-%m-%d")
        for d in drv:
            name = d["name"] or "Display adapter"
            ev = [f"{name}  version {d['ver'] or '?'}"
                  + (f"  dated {d['date']}" if d["date"] else "")]
            if "basic display" in name.lower() or "basic render" in name.lower():
                out.append(cls.issue(
                    "gpu_" + name.lower()[:12], "Drivers", "No graphics driver installed",
                    "warn", ev,
                    "Windows is using its basic display driver, so games run very "
                    "slowly and the GPU is not used properly.",
                    "Install the driver from NVIDIA / AMD / Intel or via Windows Update.",
                    "devmgmt.msc"))
                continue
            age = cls._days(d["date"], today)
            if age is None:
                out.append(cls.issue(
                    "gpu_" + name.lower()[:12], "Drivers", f"Graphics driver: {name}",
                    "unknown", ev + ["Windows did not give a driver date"],
                    "Without the date Lmonitor cannot tell how old it is. It also "
                    "cannot know the newest version (no online check in this "
                    "version).", "Check the vendor's driver app or website.", None))
                continue
            old = age > cls.DRIVER_OLD_DAYS
            ev.append(f"{age // 30} months old")
            out.append(cls.issue(
                "gpu_" + name.lower()[:12], "Drivers", f"Graphics driver: {name}",
                "notice" if old else "ok", ev,
                ("A driver this old (our limit: 12 months) may miss fixes and "
                 "optimisations for new games. Lmonitor cannot check online "
                 "whether a newer one exists." if old else
                 "The driver date is recent. Lmonitor cannot check online whether "
                 "a newer version exists."),
                ("Look for a newer driver in the NVIDIA / AMD / Intel app or on "
                 "their website." if old else "No change needed."), None))
        return out

    @staticmethod
    def _days(date, today):
        try:
            a = time.mktime(time.strptime(date, "%Y-%m-%d"))
            b = time.mktime(time.strptime(today, "%Y-%m-%d"))
            return int((b - a) // 86400)
        except (ValueError, TypeError):
            return None

    @classmethod
    def devices(cls, f):
        dev = f.get("devices")
        if dev is None:
            return [cls.unknown("devices", "Drivers", "Devices with problems", f, "devices")]
        if not dev:
            return [cls.issue("devices", "Drivers", "Devices with problems", "ok",
                              ["Windows reports no device with an error"],
                              "Every device Windows knows about reports no error.",
                              "No change needed.", "devmgmt.msc")]
        ev = [f"{d['name']}  (code {d['code']})" for d in dev[:5]]
        if len(dev) > 5:
            ev.append(f"+{len(dev) - 5} more")
        return [cls.issue(
            "devices", "Drivers", "Devices with problems", "notice", ev,
            "Windows reports an error code for these devices (usually a missing or "
            "failing driver). Some are harmless, e.g. unused virtual devices.",
            "Open Device Manager, select the device and read the message under "
            "Properties; update or reinstall its driver.", "devmgmt.msc")]

    # ---- memory and page file
    @classmethod
    def memory(cls, f):
        m = f.get("memory")
        if m is None:
            return [cls.unknown("memory", "Memory", "Memory and page file", f, "memory")]
        out = []
        ram, sw = m["ram_gb"], m["swap_gb"]
        out.append(cls.issue(
            "ram_size", "Memory", "Installed memory",
            "notice" if ram < 8 else "ok", [f"{ram:.1f} GB RAM"],
            ("Many current games want 16 GB; under 8 GB (our limit) they stutter "
             "or fail." if ram < 8 else "Enough for most current games (16 GB or "
                                        "more is comfortable)."),
            "More RAM is the fix; check that both memory slots are used." if ram < 8
            else "No change needed."))
        out.append(cls.issue(
            "pagefile", "Memory", "Page file",
            "notice" if sw <= 0 else "ok",
            [f"Page file total: {sw:.1f} GB" if sw > 0 else "No page file is set"],
            ("Without a page file some games and programs crash when memory runs "
             "low." if sw <= 0 else "A page file exists."),
            "Set 'Automatically manage paging file size' in Advanced system "
            "settings > Performance." if sw <= 0 else "No change needed.",
            "SystemPropertiesPerformance.exe" if sw <= 0 else None))
        return out

    # ---- services
    @classmethod
    def services(cls, f):
        s = f.get("services")
        if s is None:
            return [cls.unknown("services", "Services", "Selected services", f, "services")]
        out = []
        au = s.get("Audiosrv")
        if au and au["status"] != "Running":
            out.append(cls.issue(
                "audiosrv", "Services", "Windows Audio service is not running", "warn",
                [f"Audiosrv: {au['status']} (start type {au['start']})"],
                "Without it there is no sound.", "Start 'Windows Audio' in Services.",
                "services.msc"))
        lines = [f"{n}: {v['status']}, start type {v['start']}"
                 for n, v in sorted(s.items()) if n != "Audiosrv"]
        out.append(cls.issue(
            "services", "Services", "Selected services (information only)", "info",
            lines or ["None of the selected services was found"],
            "SysMain (Superfetch), Windows Search and Telemetry (DiagTrack) can use "
            "disk and CPU in the background, but disabling services has side "
            "effects and the benefit varies. Lmonitor only reports them.",
            "Leave them as they are unless you know why you want to change them.",
            "services.msc"))
        return out

    # ---- gaming related settings
    @classmethod
    def settings(cls, f):
        s = f.get("settings")
        if s is None:
            return [cls.unknown("settings", "Settings", "Windows gaming settings", f, "settings")]
        names = {1: "on", 0: "off", 2: "on"}
        ev = []
        gm = s.get("game_mode")
        ev.append("Game Mode: " + ("not set (Windows default)" if gm is None
                                   else names.get(gm, str(gm))))
        hags = s.get("hags")
        ev.append("Hardware-accelerated GPU scheduling: " + (
            "not set / not supported" if hags is None else
            {2: "on", 1: "off"}.get(hags, str(hags))))
        cap = s.get("capture")
        ev.append("Background game recording: " + ("not set" if cap is None
                                                    else names.get(cap, str(cap))))
        fs = s.get("fast_startup")
        ev.append("Fast Startup: " + ("not set" if fs is None else names.get(fs, str(fs))))
        issues = []
        if gm == 0:
            issues.append("Game Mode is off")
        if cap == 1:
            issues.append("background recording is on")
        return [cls.issue(
            "win_settings", "Settings", "Windows gaming settings",
            "notice" if issues else "info", ev + (["Noticed: " + ", ".join(issues)]
                                                  if issues else []),
            "Game Mode asks Windows to favour the game. Background recording keeps "
            "capturing video and can cost some performance. GPU scheduling and Fast "
            "Startup help some PCs and hurt others, so Lmonitor shows them without "
            "an opinion.",
            "Turn Game Mode on in Settings > Gaming; switch background recording "
            "off if you do not use it.", "ms-settings:gaming-gamemode")]

    # ---- one scan = facts + issues
    @classmethod
    def summary(cls, issues):
        c = {k: 0 for k in cls.ORDER}
        for i in issues:
            c[i["sev"]] += 1
        return c


class DiagRunner:
    """Runs one scan in a worker thread; the window polls .status / .version."""

    def __init__(self, store, collector=DiagCollector):
        self.store, self.collector = store, collector
        self.issues, self.summary, self.when = [], None, None
        self.running, self.progress = False, ""
        self.version = 0
        last = store.load()
        if last:
            self.issues, self.when = last[-1]["issues"], last[-1]["t"]
            self.summary = DiagAnalyzer.summary(self.issues)

    def start(self):
        if self.running:
            return False
        self.running, self.progress = True, "Starting"
        threading.Thread(target=self._run, daemon=True).start()
        return True


    def _run(self):
        try:
            facts = self.collector.collect(self._progress)
            issues = DiagAnalyzer.analyze(facts)
            self.issues, self.when = issues, time.time()
            self.summary = DiagAnalyzer.summary(issues)
            self.store.add({"t": self.when, "issues": issues,
                            "counts": self.summary})
        except Exception:
            Logger.error("diagnostics scan")
        finally:
            self.running, self.progress = False, ""
            self.version += 1

    def _progress(self, i, n, name):
        self.progress = f"Checking {name} ({i + 1}/{n})"


# =============================================================== Safe Optimizer
class Reg:
    """A tiny registry layer. Tests replace these methods with a dict."""
    HIVES = {"HKCU": "HKEY_CURRENT_USER", "HKLM": "HKEY_LOCAL_MACHINE"}

    @classmethod
    def _h(cls, hive):
        import winreg
        return getattr(winreg, cls.HIVES[hive])

    @classmethod
    def get(cls, hive, path, name):
        """-> (value, type) or None when it does not exist."""
        import winreg
        try:
            k = winreg.OpenKey(cls._h(hive), path)
            try:
                return winreg.QueryValueEx(k, name)
            finally:
                winreg.CloseKey(k)
        except OSError:
            return None

    @classmethod
    def set(cls, hive, path, name, value, kind):
        import winreg
        k = winreg.CreateKeyEx(cls._h(hive), path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD if kind == "dword"
                              else winreg.REG_BINARY, value)
        finally:
            winreg.CloseKey(k)

    @classmethod
    def delete(cls, hive, path, name):
        import winreg
        try:
            k = winreg.OpenKey(cls._h(hive), path, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(k, name)
            finally:
                winreg.CloseKey(k)
        except OSError:
            pass

    @classmethod
    def names(cls, hive, path):
        """[(value name, data)] of one key ([] when the key is missing)."""
        import winreg
        out = []
        try:
            k = winreg.OpenKey(cls._h(hive), path)
        except OSError:
            return out
        try:
            i = 0
            while True:
                try:
                    n, v, _ = winreg.EnumValue(k, i)
                except OSError:
                    break
                out.append((n, v))
                i += 1
        finally:
            winreg.CloseKey(k)
        return out


class StartupManager:
    """Startup programs of the Run keys and the Startup folders. They are
    switched with the same 'StartupApproved' value Task Manager uses: the entry
    itself is never deleted, so enabling it again restores everything."""
    BASE = r"Software\Microsoft\Windows\CurrentVersion"
    RUN = BASE + r"\Run"
    APPROVED = BASE + r"\Explorer\StartupApproved"
    SOURCES = [("HKCU", "Run", RUN, "HKCU Run"),
               ("HKLM", "Run", RUN, "HKLM Run"),
               ("HKLM", "Run32", r"Software\WOW6432Node\Microsoft\Windows"
                                 r"\CurrentVersion\Run", "HKLM Run (32-bit)")]
    FOLDERS = [("HKCU", "APPDATA", "Startup folder (user)"),
               ("HKLM", "PROGRAMDATA", "Startup folder (all users)")]
    ENABLED = b"\x02\x00\x00\x00" + b"\x00" * 8

    @staticmethod
    def state(raw):
        """02 / 06 = enabled, 03 = disabled; nothing stored = enabled (a
        published description of the format, not a Microsoft document)."""
        return not (raw and raw[0] == 3)

    @staticmethod
    def disabled_value(now=None):
        ft = int(((time.time() if now is None else now) + 11644473600) * 1e7)
        return b"\x03\x00\x00\x00" + ft.to_bytes(8, "little")

    @classmethod
    def _raw(cls, hive, sub, name):
        r = Reg.get(hive, cls.APPROVED + "\\" + sub, name)
        return bytes(r[0]) if r else None

    @classmethod
    def list(cls):
        items = []
        for hive, sub, path, where in cls.SOURCES:
            for name, cmd in Reg.names(hive, path):
                raw = cls._raw(hive, sub, name)
                items.append({"key": f"{hive}|{sub}|{name}", "hive": hive,
                              "sub": sub, "value": name, "name": name,
                              "where": where, "cmd": str(cmd)[:160],
                              "enabled": cls.state(raw)})
        for hive, env, where in cls.FOLDERS:
            d = os.path.join(os.environ.get(env, ""), r"Microsoft\Windows"
                             r"\Start Menu\Programs\Startup")
            try:
                files = os.listdir(d)
            except OSError:
                continue
            for f in files:
                if f.lower() == "desktop.ini":
                    continue
                raw = cls._raw(hive, "StartupFolder", f)
                items.append({"key": f"{hive}|StartupFolder|{f}", "hive": hive,
                              "sub": "StartupFolder", "value": f,
                              "name": os.path.splitext(f)[0], "where": where,
                              "cmd": os.path.join(d, f), "enabled": cls.state(raw)})
        return items

    @classmethod
    def find(cls, key):
        return next((i for i in cls.list() if i["key"] == key), None)

    @classmethod
    def set_enabled(cls, item, enabled):
        """Write the new state. -> the previous raw value (to undo it)."""
        before = cls._raw(item["hive"], item["sub"], item["value"])
        Reg.set(item["hive"], cls.APPROVED + "\\" + item["sub"], item["value"],
                cls.ENABLED if enabled else cls.disabled_value(), "binary")
        return before

    @classmethod
    def restore(cls, item_key, raw_hex):
        hive, sub, name = item_key.split("|", 2)
        path = cls.APPROVED + "\\" + sub
        if raw_hex is None:
            Reg.delete(hive, path, name)
        else:
            Reg.set(hive, path, name, bytes.fromhex(raw_hex), "binary")


class PowerManager:
    """Windows power plans through powercfg (only plans Windows lists)."""
    GUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
    HIGH = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
    BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"

    @staticmethod
    def run(args):
        r = subprocess.run(["powercfg"] + args, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=12,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        return r.returncode, r.stdout

    @classmethod
    def plans(cls):
        rc, out = cls.run(["/list"])
        if rc != 0:
            return None
        res = []
        for line in out.splitlines():
            m = re.search(r"(" + cls.GUID + r")\s+\(([^)]*)\)(\s*\*)?", line)
            if m:
                res.append({"guid": m.group(1).lower(), "name": m.group(2),
                            "active": bool(m.group(3))})
        return res

    @classmethod
    def active(cls):
        rc, out = cls.run(["/getactivescheme"])
        m = re.search(r"(" + cls.GUID + r")\s*\(([^)]*)\)", out or "")
        return {"guid": m.group(1).lower(), "name": m.group(2)} if rc == 0 and m else None

    @classmethod
    def set_active(cls, guid):
        if not re.fullmatch(cls.GUID, guid or ""):
            return False
        rc, _ = cls.run(["/setactive", guid])
        return rc == 0


class GameSettings:
    """The few per-user Windows values Lmonitor may change (nothing else)."""
    ITEMS = {
        "game_mode": {
            "title": "Game Mode", "sub": "Lets Windows favour the game you play",
            "values": [("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1)],
            "on": "On", "off": "Off", "button": "Turn on"},
        "capture": {
            "title": "Background game recording",
            "sub": "Stops Windows from recording your game in the background",
            "values": [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                        "AppCaptureEnabled", 0),
                       ("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0)],
            "on": "Off", "off": "On", "button": "Turn off"}}

    @classmethod
    def read(cls, sid):
        """-> ({value: current or None}, good?, text)"""
        it = cls.ITEMS[sid]
        cur = {}
        for hive, path, name, _ in it["values"]:
            r = Reg.get(hive, path, name)
            cur[f"{hive}|{path}|{name}"] = r[0] if r else None
        good = all(cur[f"{h}|{p}|{n}"] == g for h, p, n, g in it["values"])
        if good:
            text = it["on"]
        elif all(v is None for v in cur.values()):
            text = "Not set (Windows default)"
        else:
            text = it["off"]
        return cur, good, text

    @classmethod
    def apply(cls, sid, good=True):
        """Set the 'good' values. -> the previous values (to undo)."""
        it = cls.ITEMS[sid]
        before, _, _ = cls.read(sid)
        for hive, path, name, g in it["values"]:
            Reg.set(hive, path, name, g, "dword")
        return before

    @classmethod
    def restore(cls, before):
        for k, old in before.items():
            hive, path, name = k.split("|", 2)
            if old is None:
                Reg.delete(hive, path, name)
            else:
                Reg.set(hive, path, name, old, "dword")


class TempCleaner:
    """Clean the two Windows temp folders - only files older than a day, never
    anything through a link, never outside the temp folder."""
    MIN_AGE = 24 * 3600
    MAX_ENTRIES = 300000
    LOCATIONS = [
        ("user_temp", "Your temp folder", lambda: os.environ.get("TEMP") or ""),
        ("win_temp", "Windows temp folder",
         lambda: os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"))]

    @staticmethod
    def safe_root(root):
        """Only a real folder called 'Temp' (any case) qualifies."""
        return bool(root) and os.path.isdir(root) and \
            os.path.basename(os.path.normpath(root)).lower() in ("temp", "tmp")

    @staticmethod
    def is_link(st):
        return bool(getattr(st, "st_file_attributes", 0) & 0x400)  # reparse point

    @classmethod
    def _walk(cls, root):
        """Yield (path, stat, is_dir) without following links."""
        stack, seen = [root], 0
        while stack:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for e in it:
                    seen += 1
                    if seen > cls.MAX_ENTRIES:
                        return
                    try:
                        if e.is_symlink():
                            continue
                        st = e.stat(follow_symlinks=False)
                        if cls.is_link(st):
                            continue
                        isdir = e.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    yield e.path, st, isdir
                    if isdir:
                        stack.append(e.path)

    @classmethod
    def scan(cls, root, now=None):
        now = time.time() if now is None else now
        r = {"files": 0, "bytes": 0, "old_files": 0, "old_bytes": 0}
        if not cls.safe_root(root):
            return None
        for path, st, isdir in cls._walk(root):
            if isdir:
                continue
            r["files"] += 1
            r["bytes"] += st.st_size
            if now - st.st_mtime >= cls.MIN_AGE:
                r["old_files"] += 1
                r["old_bytes"] += st.st_size
        return r

    @classmethod
    def clean(cls, root, now=None):
        """-> {'freed', 'deleted', 'skipped'}. Files in use are skipped."""
        now = time.time() if now is None else now
        out = {"freed": 0, "deleted": 0, "skipped": 0}
        if not cls.safe_root(root):
            return out
        real = os.path.realpath(root)
        dirs = []
        for path, st, isdir in cls._walk(root):
            if not os.path.realpath(path).startswith(real + os.sep):
                continue                      # never leave the temp folder
            if isdir:
                dirs.append((path, st))
                continue
            if now - st.st_mtime < cls.MIN_AGE:
                continue
            try:
                os.remove(path)
                out["freed"] += st.st_size
                out["deleted"] += 1
            except OSError:
                out["skipped"] += 1          # in use or no permission
        for path, st in sorted(dirs, key=lambda d: -len(d[0])):
            if now - st.st_mtime >= cls.MIN_AGE:
                try:
                    os.rmdir(path)            # only empty folders
                except OSError:
                    pass
        return out


class ChangeLog:
    """Everything the Optimizer changed, with what is needed to undo it
    (%APPDATA%\\Lmonitor\\changes.json, newest 100)."""
    KEEP = 100

    def __init__(self, path=None):
        self.path = path or os.path.join(Paths.CFG_DIR, "changes.json")
        self.lock = threading.Lock()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else []
        except Exception:
            return []

    def _save(self, items):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(items[-self.KEEP:], f)
            os.replace(tmp, self.path)
        except Exception:
            Logger.error("change log")

    def add(self, entry):
        with self.lock:
            items = self.load()
            entry["id"] = (max((i["id"] for i in items), default=0)) + 1
            items.append(entry)
            self._save(items)
            return entry["id"]

    def update(self, id_, **kw):
        with self.lock:
            items = self.load()
            for i in items:
                if i["id"] == id_:
                    i.update(kw)
            self._save(items)


class Optimizer:
    """Safe, reversible changes. Every change: read the state before, ask (the
    window does), change one thing, read it back, and log it so it can be undone.
    Not done on purpose: disabling services, bulk registry edits, overclocking."""

    def __init__(self, log):
        self.log = log
        self.startup, self.plans = [], None
        self.settings = {}
        self.temp = {}              # location id -> scan result / None
        self.free_gb = None
        self.busy, self.version = False, 0
        self.last = None            # result of the last action (dict)
        self.refreshed = False

    # ---- reading the current state
    def refresh(self):
        try:
            self.startup = StartupManager.list()
        except Exception:
            self.startup = []
            Logger.error("optimizer startup")
        try:
            self.plans = PowerManager.plans()
        except Exception:
            self.plans = None
            Logger.error("optimizer plans")
        for sid in GameSettings.ITEMS:
            try:
                self.settings[sid] = GameSettings.read(sid)
            except Exception:
                self.settings[sid] = None
        self.refreshed = True
        self.version += 1


    def run(self, fn, *args):
        """Run one action in a worker thread (the window polls .busy)."""
        if self.busy:
            return False
        self.busy = True

        def work():
            try:
                fn(*args)
            except Exception:
                Logger.error("optimizer action")
                self.last = {"ok": False, "title": "Action failed",
                             "before": "", "after": "", "message":
                             "Something went wrong. Nothing was changed that "
                             "could not be undone - see error.log."}
            finally:
                self.busy = False
                self.version += 1
        threading.Thread(target=work, daemon=True).start()
        return True

    # ---- helpers
    def _result(self, **kw):
        kw.setdefault("ok", True)
        self.last = kw
        return kw

    def _log(self, kind, title, before, after, revert, verified):
        import datetime
        return self.log.add({"t": time.time(), "kind": kind, "title": title,
                             "before": before, "after": after,
                             "revert": revert, "verified": verified,
                             "status": "applied" if verified else "failed"})

    # ---- startup
    def set_startup(self, key, enable, group=""):
        item = StartupManager.find(key)
        if item is None:
            return self._result(ok=False, title="Startup item not found", before="",
                                after="", message="It is no longer in the list.")
        word = "Enable" if enable else "Disable"
        title = f"{group}{word} at startup: {item['name']}"
        raw = StartupManager.set_enabled(item, enable)
        now = StartupManager.find(key)
        ok = now is not None and now["enabled"] == enable
        revert = {"type": "startup", "key": key, "raw": raw.hex() if raw else None}
        if not ok:
            StartupManager.restore(key, revert["raw"])
        cid = self._log("startup", title, "Enabled" if item["enabled"] else "Disabled",
                        "Enabled" if enable else "Disabled", revert, ok)
        self.startup = StartupManager.list()
        n_on = sum(1 for i in self.startup if i["enabled"])
        return self._result(
            ok=ok, id=cid, title=title,
            before="Enabled" if item["enabled"] else "Disabled",
            after=("Enabled" if enable else "Disabled") if ok else "unchanged",
            message=(f"{n_on} program(s) now start with Windows. You can undo this "
                     "in History." if ok else "Windows did not keep the change - "
                     "it was put back."))

    # ---- power plan
    def set_power(self, guid, group=""):
        old = PowerManager.active()
        plans = PowerManager.plans() or []
        name = next((p["name"] for p in plans if p["guid"] == guid), None)
        if old is None or name is None:
            return self._result(ok=False, title="Power plan", before="", after="",
                                message="Windows did not list that plan.")
        PowerManager.set_active(guid)
        now = PowerManager.active()
        ok = now is not None and now["guid"] == guid
        if not ok and old:
            PowerManager.set_active(old["guid"])
        title = f"{group}Power plan: {name}"
        cid = self._log("power", title, old["name"], name if ok else old["name"],
                        {"type": "power", "guid": old["guid"]}, ok)
        self.plans = PowerManager.plans()
        return self._result(ok=ok, id=cid, title=title, before=old["name"],
                            after=name if ok else "unchanged",
                            message="You can undo this in History." if ok else
                            "Windows did not switch - the old plan was kept.")

    # ---- game settings
    def set_setting(self, sid, group=""):
        it = GameSettings.ITEMS[sid]
        cur, good, text = GameSettings.read(sid)
        before = GameSettings.apply(sid)
        cur2, good2, text2 = GameSettings.read(sid)
        if not good2:
            GameSettings.restore(before)
        title = f"{group}{it['title']}: {it['on']}"
        cid = self._log("setting", title, text, text2 if good2 else text,
                        {"type": "setting", "before": before}, good2)
        self.settings[sid] = GameSettings.read(sid)
        return self._result(ok=good2, id=cid, title=title, before=text,
                            after=text2 if good2 else "unchanged",
                            message="You can undo this in History." if good2 else
                            "Windows did not keep the change - it was put back.")

    # ---- temp files (cannot be undone)

    # ---- undo
    def revert(self, change_id):
        item = next((i for i in self.log.load() if i["id"] == change_id), None)
        rv = item and item.get("revert")
        if not item or not rv or item["status"] != "applied":
            return self._result(ok=False, title="Undo", before="", after="",
                                message="This change cannot be undone.")
        t = rv["type"]
        if t == "startup":
            StartupManager.restore(rv["key"], rv["raw"])
        elif t == "power":
            PowerManager.set_active(rv["guid"])
        elif t == "setting":
            GameSettings.restore(rv["before"])
        self.log.update(change_id, status="reverted")
        self.refresh()
        return self._result(ok=True, title="Undone: " + item["title"],
                            before=item["after"], after=item["before"],
                            message="Back to how it was.")

    # ---- presets (a few changes together; each is logged on its own)
    def preset_steps(self, name):
        """-> [(text, kind, args)] only for what would really change."""
        steps = []
        plans = self.plans or []
        act = next((p for p in plans if p["active"]), None)
        want = PowerManager.HIGH if name == "gaming" else PowerManager.BALANCED
        target = next((p for p in plans if p["guid"] == want), None)
        if target and act and act["guid"] != want:
            steps.append((f"Power plan: {act['name']} -> {target['name']}",
                          "power", (want,)))
        if name == "gaming":
            for sid in ("game_mode", "capture"):
                st = self.settings.get(sid)
                if st and not st[1]:
                    it = GameSettings.ITEMS[sid]
                    steps.append((f"{it['title']}: {st[2]} -> {it['on']}",
                                  "setting", (sid,)))
        return steps

    def preset_note(self, name):
        plans = self.plans or []
        want = PowerManager.HIGH if name == "gaming" else PowerManager.BALANCED
        if name == "gaming" and not any(p["guid"] == want for p in plans):
            return "High performance is not offered by this PC, so it is skipped."
        return ""

    def apply_preset(self, name):
        steps = self.preset_steps(name)
        if not steps:
            return self._result(ok=True, title=f"{name.title()} preset", before="",
                                after="", message="Everything is already set.")
        group = f"[{name.title()}] "
        done, ok = [], True
        for text, kind, args in steps:
            if kind == "power":
                r = self.set_power(*args, group=group)
            else:
                r = self.set_setting(*args, group=group)
            done.append(text)
            ok = ok and r["ok"]
        return self._result(ok=ok, title=f"{name.title()} preset",
                            before=f"{len(done)} change(s)", after=
                            "applied" if ok else "partly applied",
                            message="; ".join(done) + ". Undo each one in History.")


# =============================================================== Storage
class StorageGuard:
    """What may never be offered for deletion. Old does not mean unneeded: game
    libraries, saves, system folders and personal folders are show-only."""
    GAME_OR_SYSTEM = {
        "steamapps", "steamlibrary", "epic games", "riot games", "battle.net",
        "gog galaxy", "gog games", "origin games", "ea games", "ubisoft",
        "xboxgames", "windowsapps", "program files", "program files (x86)",
        "programdata", "windows", "games", "my games", "saved games",
        "savegames", "saves", "save", "saved", "$recycle.bin",
        "system volume information"}
    PERSONAL = {"documents", "pictures", "desktop", "music", "videos",
                "photos", "onedrive"}

    @staticmethod
    def parts(path):
        return [p.lower() for p in re.split(r"[\\/]+", path or "") if p]

    @classmethod
    def reason(cls, path):
        """Why this path must not be deleted ('' = no objection)."""
        ps = cls.parts(path)
        if any(p in cls.GAME_OR_SYSTEM for p in ps):
            return "Game, save or system files"
        if any(p in cls.PERSONAL for p in ps):
            return "Personal files"
        return ""

    @staticmethod
    def downloads():
        return os.path.join(os.path.expanduser("~"), "Downloads")

    @classmethod
    def deletable(cls, path):
        """Only a single regular file inside Downloads may be sent to the
        Recycle Bin - and only after the guard has no objection."""
        try:
            if not path or cls.reason(path) or not os.path.isfile(path):
                return False
            st = os.lstat(path)
            if TempCleaner.is_link(st) or os.path.islink(path):
                return False
            root = os.path.normcase(os.path.realpath(cls.downloads()))
            return os.path.normcase(os.path.realpath(path)).startswith(root + os.sep)
        except OSError:
            return False


class StorageCleaner(TempCleaner):
    """TempCleaner for a fixed list of cache folders (nothing else qualifies)."""

    @classmethod
    def safe_root(cls, root):
        if not root or not os.path.isdir(root):
            return False
        want = os.path.normcase(os.path.realpath(root))
        return any(os.path.normcase(os.path.realpath(p)) == want
                   for _, _, p, _ in Storage.cache_locations() if p)


class Storage:
    """Find what takes space. Cleaning is limited to known cache folders (files
    older than a day) and single files in Downloads (to the Recycle Bin)."""
    RECOMMENDED = ("user_temp", "win_temp", "dumps")   # ticked by default
    LARGE_MIN = 500 * 1024 ** 2        # "large file" = 500 MB or more (my choice)
    LARGE_SHOW, FOLDER_SHOW = 30, 20
    SKIP = {"windows", "program files", "program files (x86)", "programdata",
            "$recycle.bin", "system volume information", "appdata"}
    BUDGET_S = 25

    @staticmethod
    def cache_locations():
        """(id, title, path, note)"""
        la = os.environ.get("LOCALAPPDATA") or ""
        j = lambda *a: os.path.join(la, *a) if la else ""
        locs = [(lid, t, g(), "Windows recreates them as needed")
                for lid, t, g in TempCleaner.LOCATIONS]
        locs += [
            ("nv_dx", "NVIDIA shader cache", j("NVIDIA", "DXCache"),
             "Rebuilt by games; first launch may stutter a little"),
            ("nv_gl", "NVIDIA OpenGL cache", j("NVIDIA", "GLCache"),
             "Rebuilt by games"),
            ("d3d", "DirectX shader cache", j("D3DSCache"),
             "Rebuilt by games; first launch may stutter a little"),
            ("dumps", "Crash dumps", j("CrashDumps"),
             "Only useful when debugging a crash"),
            ("chrome", "Chrome cache", j("Google", "Chrome", "User Data", "Default", "Cache"),
             "Pages load slower once; sign-ins are kept"),
            ("edge", "Edge cache", j("Microsoft", "Edge", "User Data", "Default", "Cache"),
             "Pages load slower once; sign-ins are kept")]
        return locs

    def __init__(self, log):
        self.log = log
        self.caches = {}               # id -> scan dict / None
        self.folders = self.large = None
        self.busy, self.version, self.last = False, 0, None
        self.progress = ""
        self.scanned = False

    # ---- worker
    def run(self, fn, *args):
        if self.busy:
            return False
        self.busy = True

        def work():
            try:
                fn(*args)
            except Exception:
                Logger.error("storage action")
                self.last = {"ok": False, "title": "Action failed", "before": "",
                             "after": "", "message": "Something went wrong; "
                             "nothing was deleted - see error.log."}
            finally:
                self.busy = False
                self.progress = ""
                self.version += 1
        threading.Thread(target=work, daemon=True).start()
        return True

    def _result(self, **kw):
        kw.setdefault("ok", True)
        self.last = kw
        return kw

    # ---- measuring (nothing is deleted here)
    def scan_caches(self):
        for lid, title, path, note in self.cache_locations():
            try:
                self.caches[lid] = StorageCleaner.scan(path) if path else None
            except Exception:
                self.caches[lid] = None
                Logger.error("storage cache scan")
        self.scanned = True
        self.version += 1

    def reclaimable(self):
        return sum(r["old_bytes"] for r in self.caches.values() if r)

    @staticmethod
    def _walk(root, deadline, skip=()):
        """(path, stat, isdir) - no links, skipping named folders, time-limited."""
        stack, n = [root], 0
        while stack and time.time() < deadline:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for e in it:
                    n += 1
                    if n > TempCleaner.MAX_ENTRIES * 3:
                        return
                    try:
                        if e.is_symlink():
                            continue
                        st = e.stat(follow_symlinks=False)
                        if TempCleaner.is_link(st):
                            continue
                        isdir = e.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    if isdir and e.name.lower() in skip:
                        continue
                    yield e.path, st, isdir
                    if isdir:
                        stack.append(e.path)

    @staticmethod
    def scan_roots():
        roots = [os.path.expanduser("~")]
        try:
            for p in psutil.disk_partitions(all=False):
                if "fixed" in (p.opts or "").lower() and p.mountpoint:
                    drive = os.path.splitdrive(os.path.expanduser("~"))[0].lower()
                    if os.path.splitdrive(p.mountpoint)[0].lower() != drive:
                        roots.append(p.mountpoint)
        except Exception:
            pass
        return roots

    def scan_folders(self, roots=None):
        out = []
        for root in (roots or self.scan_roots()):
            deadline = time.time() + self.BUDGET_S
            try:
                kids = [e.path for e in os.scandir(root)
                        if e.is_dir(follow_symlinks=False)
                        and e.name.lower() not in ("windows", "$recycle.bin",
                                                   "system volume information")
                        and not e.name.startswith(".")]
            except OSError:
                continue
            for k in kids:
                self.progress = os.path.basename(k)
                total = files = 0
                for path, st, isdir in self._walk(k, deadline):
                    if not isdir:
                        total += st.st_size
                        files += 1
                out.append({"path": k, "bytes": total, "files": files,
                            "partial": time.time() >= deadline,
                            "reason": StorageGuard.reason(k)})
        out.sort(key=lambda d: -d["bytes"])
        self.folders = out[:self.FOLDER_SHOW]
        self.version += 1

    def scan_large(self, roots=None, min_bytes=None):
        min_bytes = self.LARGE_MIN if min_bytes is None else min_bytes
        out = []
        for root in (roots or self.scan_roots()):
            deadline = time.time() + self.BUDGET_S
            for path, st, isdir in self._walk(root, deadline, skip=self.SKIP - {"appdata"}):
                if not isdir and st.st_size >= min_bytes:
                    out.append({"path": path, "bytes": st.st_size, "mtime": st.st_mtime,
                                "reason": StorageGuard.reason(path),
                                "deletable": StorageGuard.deletable(path)})
        out.sort(key=lambda d: -d["bytes"])
        self.large = out[:self.LARGE_SHOW]
        self.version += 1

    # ---- the only things that delete

    def clean_many(self, ids):
        """Clean the chosen cache folders in one go (one log entry)."""
        locs = [l for l in self.cache_locations() if l[0] in ids and l[2]]
        if not locs:
            return self._result(ok=False, title="Clean up", before="", after="",
                                message="Nothing was selected.")
        free0 = self._free(locs[0][2])
        freed = deleted = skipped = 0
        for lid, title, path, why in locs:
            r = StorageCleaner.clean(path)
            freed += r["freed"]
            deleted += r["deleted"]
            skipped += r["skipped"]
            self.caches[lid] = StorageCleaner.scan(path)
        free1 = self._free(locs[0][2])
        title = f"Cleaned {len(locs)} location(s)"
        self.log.add({"t": time.time(), "kind": "storage", "title": title,
                      "before": "", "after": fmt_size(freed) + " freed",
                      "revert": None, "verified": True, "status": "applied"})
        return self._result(
            ok=True, title=title,
            before=f"{free0 / 1024 ** 3:.2f} GB free" if free0 is not None else "",
            after=f"{free1 / 1024 ** 3:.2f} GB free" if free1 is not None else "",
            message=f"{deleted} file(s) removed, {fmt_size(freed)} freed"
                    + (f"; {skipped} in use were left" if skipped else "")
                    + ". This cannot be undone.")

    @staticmethod
    def _to_recycle(path):
        script = ("Add-Type -AssemblyName Microsoft.VisualBasic; "
                  "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
                  "$env:LM_PATH,'OnlyErrorDialogs','SendToRecycleBin')")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        script], capture_output=True, stdin=subprocess.DEVNULL,
                       timeout=60, env={**os.environ, "LM_PATH": path},
                       creationflags=0x08000000 if os.name == "nt" else 0)

    def recycle(self, path):
        known = any(i["path"] == path for i in (self.large or []))
        if not known or not StorageGuard.deletable(path):
            return self._result(ok=False, title="Not deleted", before="", after="",
                                message="This file is not one Lmonitor may delete.")
        size = os.path.getsize(path)
        try:
            self._to_recycle(path)
        except Exception:
            Logger.error("recycle")
        gone = not os.path.exists(path)
        title = "Recycle: " + os.path.basename(path)
        self.log.add({"t": time.time(), "kind": "storage", "title": title,
                      "before": path, "after": "Recycle Bin" if gone else "kept",
                      "revert": None, "verified": gone,
                      "status": "applied" if gone else "failed"})
        if gone:
            self.large = [i for i in self.large if i["path"] != path]
        return self._result(
            ok=gone, title=title, before=fmt_size(size),
            after="in the Recycle Bin" if gone else "unchanged",
            message=("Restore it from the Recycle Bin if you need it: " + path)
            if gone else "Windows did not move the file - it was left where it is.")

    def show(self, path):
        known = any(i["path"] == path for i in (self.large or []) + (self.folders or []))
        if not known or not os.path.exists(path):
            return self._result(ok=False, title="Show", before="", after="",
                                message="That path is no longer there.")
        try:
            subprocess.Popen(["explorer", "/select,", path],
                             creationflags=0x08000000 if os.name == "nt" else 0)
        except Exception:
            Logger.error("show in explorer")
        return self._result(ok=True, title="Opened in Explorer", before="", after="",
                            message=path)

    @staticmethod
    def _free(path):
        try:
            return psutil.disk_usage(path).free
        except Exception:
            return None


# =============================================================== Reports
class ReportBuilder:
    """Builds one report from what was measured: the last Diagnostics scans,
    the game sessions and the Optimizer / Storage change log.

    The score is explainable: it starts at 100 and every deduction is listed
    with its reason. A check that could not be done is NEVER counted as
    healthy - it is listed as 'not counted', and with too little data there is
    no score at all. The point values are Lmonitor's own choice."""
    AREAS = ["Startup", "Power", "Storage", "Event Log", "Drivers", "Memory",
             "Services", "Settings"]
    WARN_PTS, NOTICE_PTS, AREA_CAP = 15, 5, 25
    MIN_COVERAGE = 0.5            # fewer answered areas than this: no score
    SESSIONS_SHOWN = 10

    @classmethod
    def score(cls, issues):
        """-> {'value': int|None, 'covered', 'total', 'deductions', 'unknown',
               'text'}"""
        if not issues:
            return {"value": None, "covered": 0, "total": len(cls.AREAS),
                    "deductions": [], "unknown": [],
                    "text": "No scan yet - run a Diagnostics scan first."}
        answered = {i["area"] for i in issues if i["sev"] != "unknown"}
        covered = len([a for a in cls.AREAS if a in answered])
        unknown = [{"area": i["area"], "title": i["title"]}
                   for i in issues if i["sev"] == "unknown"]
        per_area, deductions = {}, []
        for i in issues:
            pts = {"warn": cls.WARN_PTS, "notice": cls.NOTICE_PTS}.get(i["sev"], 0)
            if not pts:
                continue
            room = cls.AREA_CAP - per_area.get(i["area"], 0)
            take = min(pts, max(0, room))
            per_area[i["area"]] = per_area.get(i["area"], 0) + take
            deductions.append({"area": i["area"], "title": i["title"],
                               "sev": i["sev"], "points": take,
                               "why": (i.get("evidence") or [""])[0]})
        total = len(cls.AREAS)
        if covered / total < cls.MIN_COVERAGE:
            return {"value": None, "covered": covered, "total": total,
                    "deductions": deductions, "unknown": unknown,
                    "text": f"Only {covered} of {total} areas could be checked - "
                            "not enough data for a score."}
        value = max(0, 100 - sum(d["points"] for d in deductions))
        text = f"{value} / 100 - based on {covered} of {total} areas"
        if covered < total:
            text += f" ({total - covered} could not be checked and are not counted as healthy)"
        return {"value": value, "covered": covered, "total": total,
                "deductions": deductions, "unknown": unknown, "text": text}

    @staticmethod
    def compare_scans(old, new):
        """Issues by id: resolved / new / worse / better / unchanged."""
        rank = DiagAnalyzer.ORDER
        o = {i["id"]: i for i in old.get("issues", [])}
        n = {i["id"]: i for i in new.get("issues", [])}
        out = {"resolved": [], "new": [], "worse": [], "better": [], "unknown": [],
               "same": 0}
        for k, i in n.items():
            if k not in o:
                if i["sev"] in ("warn", "notice"):
                    out["new"].append(i["title"])
                continue
            if i["sev"] == "unknown":
                out["unknown"].append(i["title"])       # could not be checked now
                continue
            if o[k]["sev"] == "unknown":
                if i["sev"] in ("warn", "notice"):
                    out["new"].append(i["title"])
                continue
            a, b = rank[o[k]["sev"]], rank[i["sev"]]
            if b < a and i["sev"] in ("warn", "notice"):
                out["worse"].append(i["title"])
            elif b > a and o[k]["sev"] in ("warn", "notice"):
                out["resolved" if i["sev"] in ("ok", "info") else "better"].append(i["title"])
            else:
                out["same"] += 1
        for k, i in o.items():
            if k not in n and i["sev"] in ("warn", "notice"):
                out["resolved"].append(i["title"])
        return out

    @staticmethod
    def compare_sessions(old, new):
        """Differences between two session summaries of the same game."""
        def pick(s, key, idx=None):
            v = s.get(key)
            if idx is not None and isinstance(v, list):
                v = v[idx] if len(v) > idx else None
            return v
        rows = []
        for label, key, idx, unit, better in (
                ("Average FPS", "avg_fps", None, "", "up"),
                ("1% low FPS", "low1", None, "", "up"),
                ("0.1% low FPS", "low01", None, "", "up"),
                ("GPU temperature (max)", "g_temp", 1, " °C", "down"),
                ("CPU temperature (max)", "c_temp", 1, " °C", "down")):
            a, b = pick(old, key, idx), pick(new, key, idx)
            if a is None or b is None:
                rows.append({"label": label, "old": a, "new": b, "delta": None,
                             "verdict": "not comparable"})
                continue
            d = b - a
            same = abs(d) < max(0.5, abs(a) * 0.03)     # within 3 %: no change
            verdict = "about the same" if same else (
                "better" if (d > 0) == (better == "up") else "worse")
            rows.append({"label": label, "old": a, "new": b, "delta": d,
                         "unit": unit, "verdict": verdict})
        return rows

    @classmethod
    def latest_session_pair(cls, sessions):
        """The newest session and the one before it for the same game."""
        ss = sorted(sessions, key=lambda s: s["start"])
        for s in reversed(ss):
            prev = [p for p in ss if p["game"] == s["game"] and p["start"] < s["start"]]
            if prev:
                return prev[-1], s
        return None

    @classmethod
    def build(cls, scans, sessions, changes, app_version="", now=None):
        now = time.time() if now is None else now
        last = scans[-1] if scans else None
        issues = last["issues"] if last else []
        rep = {"generated": now, "app": "Lmonitor " + app_version,
               "scan_time": last["t"] if last else None,
               "score": cls.score(issues),
               "issues": [i for i in issues if i["sev"] != "ok"],
               "ok_count": sum(1 for i in issues if i["sev"] == "ok"),
               "scan_changes": None, "session_changes": None,
               "sessions": [], "changes": []}
        if len(scans) >= 2:
            a, b = scans[-2], scans[-1]
            rep["scan_changes"] = dict(cls.compare_scans(a, b), before=a["t"], after=b["t"])
            rep["scan_changes"]["made_between"] = [
                c["title"] for c in changes
                if a["t"] <= c["t"] <= b["t"] and c.get("status") == "applied"]
        pair = cls.latest_session_pair(sessions)
        if pair:
            o, n = pair
            rep["session_changes"] = {
                "game": n["game"], "before": o["start"], "after": n["start"],
                "rows": cls.compare_sessions(o["summary"], n["summary"])}
        for s in sorted(sessions, key=lambda s: -s["start"])[:cls.SESSIONS_SHOWN]:
            sm = s["summary"]
            rep["sessions"].append({
                "game": s["game"], "start": s["start"], "duration": s["duration"],
                "avg_fps": sm.get("avg_fps"), "low1": sm.get("low1"),
                "low01": sm.get("low01"),
                "findings": [f for f in sm.get("findings", [])
                             if f["sev"] in ("warn", "notice", "unknown")]})
        rep["changes"] = [{"t": c["t"], "title": c["title"], "before": c.get("before", ""),
                           "after": c.get("after", ""), "status": c.get("status", "")}
                          for c in reversed(changes[-30:])]
        return rep

    # ---- export
    @staticmethod
    def redact(text):
        """Hide the Windows user name in paths (C:\\Users\\name -> C:\\Users\\<user>)."""
        return re.sub(r"(?i)([A-Z]:[\\/]+Users[\\/]+)[^\\/\s\"']+", r"\1<user>", text)

    @classmethod
    def to_json(cls, rep):
        return cls.redact(json.dumps(rep, indent=2, ensure_ascii=False))

    @classmethod
    def to_html(cls, rep):
        import html
        e = lambda x: html.escape(str(x if x is not None else "-"))
        tm = lambda t: time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else "-"
        f1 = lambda v: "-" if v is None else f"{v:.0f}"
        sc = rep["score"]
        parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lmonitor report</title><style>
:root{{--bg:#fff;--card:#f4f5f7;--tx:#16181d;--dim:#5b6270;--ok:#1b8a3a;--warn:#c2410c;--note:#a16207}}
@media (prefers-color-scheme:dark){{:root{{--bg:#131417;--card:#1d1f24;--tx:#eceef2;--dim:#9aa1ad;--ok:#4ade80;--warn:#fb923c;--note:#facc15}}}}
body{{background:var(--bg);color:var(--tx);font:15px/1.5 Segoe UI,system-ui,sans-serif;margin:0;padding:24px 16px}}
main{{max-width:860px;margin:auto}}h1{{margin:0 0 4px}}h2{{margin:28px 0 8px;font-size:18px}}
.dim{{color:var(--dim)}}.card{{background:var(--card);border-radius:12px;padding:14px 16px;margin:10px 0}}
.big{{font-size:44px;font-weight:700}}table{{width:100%;border-collapse:collapse}}
td,th{{text-align:left;padding:6px 8px;border-bottom:1px solid rgba(128,128,128,.25);vertical-align:top}}
.warn{{color:var(--warn)}}.notice{{color:var(--note)}}.ok{{color:var(--ok)}}
</style></head><body><main>
<h1>Lmonitor report</h1><div class="dim">{e(rep['app'])} · generated {tm(rep['generated'])}
 · last scan {tm(rep['scan_time'])}</div>
<h2>Health score</h2><div class="card">"""]
        parts.append(f'<div class="big">{e(sc["value"]) if sc["value"] is not None else "No score"}</div>'
                     f'<div>{e(sc["text"])}</div>'
                     '<div class="dim">How: start at 100; a warning costs '
                     f'{cls.WARN_PTS}, a notice {cls.NOTICE_PTS} (at most {cls.AREA_CAP} per area). '
                     'These point values are Lmonitor\'s own choice, not a standard. '
                     'A check that could not be done is never counted as healthy.</div>')
        if sc["deductions"]:
            parts.append("<table><tr><th>Area</th><th>Item</th><th>Points</th><th>Evidence</th></tr>")
            for d in sc["deductions"]:
                parts.append(f'<tr><td>{e(d["area"])}</td><td class="{e(d["sev"])}">{e(d["title"])}</td>'
                             f'<td>-{e(d["points"])}</td><td>{e(d["why"])}</td></tr>')
            parts.append("</table>")
        if sc["unknown"]:
            parts.append('<p class="dim">Not counted (no answer from Windows): '
                         + e(", ".join(u["title"] for u in sc["unknown"])) + "</p>")
        parts.append("</div><h2>Issues</h2>")
        if not rep["issues"]:
            parts.append(f'<div class="card ok">No warnings or notices ({rep["ok_count"]} checks OK).</div>')
        for i in rep["issues"]:
            ev = "".join(f"<li>{e(x)}</li>" for x in i.get("evidence", []))
            parts.append(f'<div class="card"><b class="{e(i["sev"])}">{e(DiagAnalyzer.SEV_WORD.get(i["sev"], i["sev"]))}</b> · '
                         f'<b>{e(i["title"])}</b> <span class="dim">({e(i["area"])})</span>'
                         f'<ul>{ev}</ul><div>{e(i["explain"])}</div>'
                         f'<div class="dim">Safe fix: {e(i["fix"])}</div></div>')
        sc_ch = rep.get("scan_changes")
        parts.append("<h2>Before / after (last two scans)</h2>")
        if not sc_ch:
            parts.append('<div class="card dim">Needs two scans.</div>')
        else:
            def li(lbl, xs, cls_):
                return (f'<tr><td>{lbl}</td><td class="{cls_}">{e(", ".join(xs)) if xs else "-"}</td></tr>')
            parts.append(f'<div class="card dim">{tm(sc_ch["before"])} → {tm(sc_ch["after"])}</div><table>'
                         + li("Resolved", sc_ch["resolved"], "ok") + li("Better", sc_ch["better"], "ok")
                         + li("New", sc_ch["new"], "warn") + li("Worse", sc_ch["worse"], "warn")
                         + li("Could not be checked now", sc_ch["unknown"], "")
                         + li("Changes made in between", sc_ch["made_between"], "")
                         + f'<tr><td>Unchanged</td><td>{sc_ch["same"]}</td></tr></table>')
        parts.append("<h2>Game sessions</h2>")
        if rep["sessions"]:
            parts.append("<table><tr><th>Game</th><th>Date</th><th>Length</th><th>Avg FPS</th><th>1% low</th><th>0.1% low</th></tr>")
            for s in rep["sessions"]:
                parts.append(f'<tr><td>{e(s["game"])}</td><td>{tm(s["start"])}</td>'
                             f'<td>{int(s["duration"] // 60)} min</td><td>{f1(s["avg_fps"])}</td>'
                             f'<td>{f1(s["low1"])}</td><td>{f1(s["low01"])}</td></tr>')
                for fd in s["findings"]:
                    parts.append(f'<tr><td></td><td colspan="5" class="{e(fd["sev"])}">{e(fd["title"])}: {e(fd["text"])}</td></tr>')
            parts.append("</table>")
        else:
            parts.append('<div class="card dim">No sessions recorded.</div>')
        sn = rep.get("session_changes")
        if sn:
            parts.append(f'<h2>Latest vs previous session: {e(sn["game"])}</h2><table>'
                         "<tr><th></th><th>Before</th><th>After</th><th>Result</th></tr>")
            for r in sn["rows"]:
                parts.append(f'<tr><td>{e(r["label"])}</td><td>{f1(r["old"])}</td><td>{f1(r["new"])}</td>'
                             f'<td>{e(r["verdict"])}</td></tr>')
            parts.append("</table>")
        parts.append("<h2>Changes made with Lmonitor</h2>")
        if rep["changes"]:
            parts.append("<table><tr><th>When</th><th>Change</th><th>Before → After</th><th>Status</th></tr>")
            for c in rep["changes"]:
                parts.append(f'<tr><td>{tm(c["t"])}</td><td>{e(c["title"])}</td>'
                             f'<td>{e(c["before"])} → {e(c["after"])}</td><td>{e(c["status"])}</td></tr>')
            parts.append("</table>")
        else:
            parts.append('<div class="card dim">Nothing changed yet.</div>')
        parts.append('<p class="dim">Created locally by Lmonitor. Nothing was uploaded. '
                     'Windows user names in paths are hidden.</p></main></body></html>')
        return cls.redact("".join(parts))


class Reports:
    """Builds and saves reports in a worker thread (the window polls .busy)."""

    def __init__(self, scans, sessions, log):
        self.scans, self.sessions, self.log = scans, sessions, log
        self.report = None
        self.busy, self.version, self.last = False, 0, None

    @staticmethod
    def folder():
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        base = docs if os.path.isdir(docs) else Paths.CFG_DIR
        return os.path.join(base, "Lmonitor Reports")

    def run(self, fn, *args):
        if self.busy:
            return False
        self.busy = True

        def work():
            try:
                fn(*args)
            except Exception:
                Logger.error("report")
                self.last = {"ok": False, "title": "Report failed",
                             "message": "The report could not be made - see error.log."}
            finally:
                self.busy = False
                self.version += 1
        threading.Thread(target=work, daemon=True).start()
        return True

    def build(self):
        self.report = ReportBuilder.build(self.scans.load(), self.sessions.list(),
                                          self.log.load(), AppInfo.VERSION)
        self.version += 1
        return self.report

    def save(self, kind):
        rep = self.report or self.build()
        ext = {"html": ".html", "json": ".json"}[kind]
        folder = self.folder()
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, time.strftime("Lmonitor_report_%Y%m%d_%H%M%S") + ext)
        text = ReportBuilder.to_html(rep) if kind == "html" else ReportBuilder.to_json(rep)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        ok = os.path.isfile(path) and os.path.getsize(path) > 0
        self.last = {"ok": ok, "title": f"Saved {kind.upper()} report", "path": path,
                     "message": path + "  (private: nothing was uploaded; "
                                "Windows user names are hidden)"}
        return self.last

    def open_folder(self):
        folder = self.folder()
        if os.path.isdir(folder):
            try:
                os.startfile(folder)
            except Exception:
                Logger.error("open reports folder")


# =============================================================== Telemetry
class Telemetry:
    """One place that reads everything the window shows and keeps history.

    sample() is called by the App only while the window is open on a page that
    needs live data, at the user's Refresh interval. Nothing runs otherwise.
    """
    HISTORY = 120                       # samples kept per chart
    CHARTS = ("g_use", "c_use", "r_use", "g_temp", "c_temp", "net_down",
              "net_up")
    ALL = {k: True for k in Metrics.KEYS}

    def __init__(self, host, cpu, gpu, memory):
        self.host, self.cpu, self.gpu, self.memory = host, cpu, gpu, memory
        self.load = CpuLoad()
        self.storage = StorageReader()
        self.network = NetworkReader()
        self.battery = BatteryReader()
        self.sensors = SensorReader(host, gpu)
        self.info = SystemInfo(host, gpu)
        self.history = {k: deque(maxlen=self.HISTORY) for k in self.CHARTS}
        self.snap = {}
        self.interval = 1.0
        self.sample_ms = 0.0
        self._last = 0.0
        self.driver_ok = lambda: True   # the App connects these two
        self.is_admin = lambda: True

    # ---- sampling
    def set_interval(self, seconds):
        if seconds != self.interval:
            self.interval = float(seconds)
            for h in self.history.values():
                h.clear()  # samples of another interval would mislead

    def sample(self):
        self.info.start()
        t0, now = time.perf_counter(), time.time()
        if self._last and now - self._last > self.interval * 3 + 1:
            for h in self.history.values():
                h.append(None)  # the window was closed: show a gap
        self._last = now
        use, temp, pw, clk, mem = self.gpu.read(self.ALL)
        t, p, c, approx = self.cpu.read(True, True, True)
        self.network.read()
        down, up = self.network.total()
        self.storage.read()   # cached; read here so the window never waits
        vm, sw = self.memory.ram(), self.memory.swap()
        s = {"g_use": use, "g_temp": temp, "g_pow": pw, "g_clk": clk,
             "g_mem": mem, "g_fan": self.gpu.fan(),
             "c_use": self.load.read(), "c_temp": t, "c_pow": p, "c_clk": c,
             "c_approx": approx, "vm": vm, "sw": sw, "r_use": vm.percent,
             "net_down": down, "net_up": up}
        for k in self.CHARTS:
            self.history[k].append(s[k])
        self.snap = s
        self.sample_ms = (time.perf_counter() - t0) * 1000
        return s

    # ---- text rows for the Hardware page
    # ("head", title) | ("row", label, value[, color]) | ("bar", label, value, frac)
    def _cpu_hint(self, v):
        if v is not None:
            return None
        if self.cpu.available and not self.driver_ok():
            return "n/a (PawnIO driver missing)"
        if not self.cpu.available:
            return "n/a (sensor library not loaded)"
        return "n/a"

    def _gpu_vendor(self):
        v = self.gpu.vendor()
        if v == "other":
            return "Intel" if self.host.gpu_type.endswith("Intel") else "Unknown"
        return {"nvidia": "NVIDIA", "amd": "AMD"}[v]

    def rows_processor(self):
        s, h = self.snap, self.host
        name = h.cpu_name_raw or self.info.cpu_registry or "Unknown"
        low = name.lower()
        vendor = ("Intel" if "intel" in low else
                  "AMD" if ("amd" in low or "ryzen" in low) else "Unknown")
        phys, logical = psutil.cpu_count(logical=False), psutil.cpu_count()
        ct, cp, cc = s.get("c_temp"), s.get("c_pow"), s.get("c_clk")
        rows = [("head", "CPU"), ("row", "Model", name),
                ("row", "Vendor", vendor),
                ("row", "Cores", fmt_value(phys, "d")),
                ("row", "Threads", fmt_value(logical, "d")),
                ("row", "Usage", fmt_value(s.get("c_use"), ".0f", " %"),
                 Thresholds.use(s.get("c_use"))),
                ("row", "Temperature", self._cpu_hint(ct) or f"{ct:.0f} °C",
                 Thresholds.temp(ct)),
                ("row", "Clock", fmt_value(cc, ".0f", " MHz")
                 + (" (Windows value)" if cc and s.get("c_approx") else "")),
                ("row", "Power", self._cpu_hint(cp) or f"{cp:.0f} W"),
                ("head", "GPU"), ("row", "Vendor", self._gpu_vendor()),
                ("row", "Model", pretty_name(self.gpu.display_name())
                 if self.gpu.display_name() else
                 (self.info.gpu_drivers[0][0] if self.info.gpu_drivers
                  else "Not detected")),
                ("row", "Driver", self._gpu_driver()),
                ("row", "Usage", fmt_value(s.get("g_use"), ".0f", " %"),
                 Thresholds.use(s.get("g_use"))),
                ("row", "Temperature", fmt_value(s.get("g_temp"), ".0f", " °C"),
                 Thresholds.temp(s.get("g_temp"))),
                ("row", "Clock", fmt_value(s.get("g_clk"), ".0f", " MHz")),
                ("row", "Power", fmt_value(s.get("g_pow"), ".0f", " W"))]
        mem = s.get("g_mem")
        rows.append(("row", "VRAM", f"{mem[0]:.1f} / {mem[1]:.1f} GB"
                     if mem else "n/a"))
        if s.get("g_fan") is not None:
            rows.append(("row", "Fan", f"{s['g_fan']:.0f} %"))
        return rows

    def _gpu_driver(self):
        inf = self.info
        if inf.nvidia_driver:
            return f"{inf.nvidia_driver} (NVIDIA)"
        if inf.gpu_drivers:
            return inf.gpu_drivers[0][1] or "n/a"
        return "reading..." if not inf.ready else "n/a"

    def rows_memory(self):
        s = self.snap
        vm, sw = s.get("vm"), s.get("sw")
        rows = [("head", "Memory (RAM)")]
        if vm is not None:
            rows += [("row", "Total", fmt_size(vm.total)),
                     ("row", "Used", fmt_size(vm.used)),
                     ("row", "Free", fmt_size(vm.available)),
                     ("bar", "Usage", f"{vm.percent:.0f} %", vm.percent / 100)]
        if sw is not None:
            rows.append(("row", "Swap (page file)", "off" if not sw.total else
                         f"{fmt_size(sw.used)} of {fmt_size(sw.total)}"))
        return rows

    def rows_storage(self):
        rows = [("head", "Storage")]
        drives = self.storage.read()
        if not drives:
            rows.append(("row", "Drives", "n/a"))
        for d in drives:
            name = d["mount"].rstrip("\\") + (f"  {d['label']}" if d["label"]
                                              else "")
            disk = self.info.disk_for(d["mount"])
            kind = self.info.disk_kind(disk) if disk else ""
            rows.append(("bar", f"{name} ({d['fs']}{' · ' + kind if kind else ''})",
                         f"{fmt_size(d['used'])} used · {fmt_size(d['free'])} free"
                         f" of {fmt_size(d['total'])}", d["pct"] / 100))
        rows += self.rows_drive_health()
        return rows

    WEAR = ("remaining", "life", "spare", "percentage used", "wear",
            "written", "read", "power on", "power cycle")

    def rows_drive_health(self):
        """Health Windows reports + the wear / SMART values the drive exposes.

        Only what is really readable is shown; a drive that gives nothing
        says so (an empty value is never shown as "healthy")."""
        rows = [("row", " ", " "), ("head", "Drive health")]  # blank line first
        disks = self.info.disks
        if not disks:
            rows.append(("row", "Drives", "n/a (Windows did not answer)"
                         if self.info.ready else "reading..."))
            return rows
        self.host.enable_extras()
        data = [x for x in self.sensors.read() if x[0] == "Storage"]
        colors = {"Healthy": Theme.C_OK, "Warning": Theme.YELLOW,
                  "Unhealthy": Theme.RED}
        for dk in disks[:6]:
            kind = self.info.disk_kind(dk)
            title = f"{dk['name'][:26]}" + (f" ({kind})" if kind else "")
            health = dk["health"] or "unknown"
            rows.append(("row", title, health, colors.get(health)))
            if dk["state"] and dk["state"] not in ("OK", "Unknown"):
                rows.append(("row", "  Status", dk["state"], Theme.YELLOW))
            mine = [x for x in data if dk["name"] and (
                dk["name"].lower() in x[1].lower() or x[1].lower() in dk["name"].lower())]
            shown = 0
            for kind_, hw, st, name, v in mine:
                if st == "Temperature" or any(w in name.lower() for w in self.WEAR):
                    unit = SensorReader.UNITS.get(st, "")
                    rows.append(("row", f"  {name[:26]}", f"{v:.0f}{unit}",
                                 Thresholds.temp(v) if st == "Temperature" else None))
                    shown += 1
            if not shown:
                rows.append(("row", "  Wear / SMART", "not provided by this drive"))
        return rows

    def rows_network(self):
        rows = [("head", "Network")]
        net = self.network
        d, u = net.total()
        rows.append(("row", "Total", f"↓ {fmt_rate(d)}   ↑ {fmt_rate(u)}"))
        items = net.interfaces()
        if not items:
            rows.append(("row", "Interfaces", "none connected"))
        for name, speed, down, up in items:
            link = f"{speed} Mbit/s" if speed else "link speed n/a"
            rows.append(("head", f"{name[:36]}  ({link})"))
            rows.append(("row", "Speed", f"↓ {fmt_rate(down)}   ↑ {fmt_rate(up)}"))
        return rows

    def rows_sensors(self):
        rows = [("head", "Battery")]
        b = self.battery.read()
        if b is None:
            rows.append(("row", "Battery", "none detected"))
        else:
            if b.power_plugged is None:
                state = "unknown"
            else:
                state = ("charging" if b.power_plugged and b.percent < 100
                         else "fully charged" if b.power_plugged
                         else "on battery")
            left = ""
            if (not b.power_plugged and b.secsleft is not None
                    and b.secsleft >= 0):
                left = f" · {b.secsleft // 3600}h {b.secsleft % 3600 // 60}m left"
            rows += [("bar", "Charge", f"{b.percent:.0f} % ({state}){left}",
                      b.percent / 100),
                     ("row", "Health", self._battery_health())]
        rows.append(("head", "Fans and sensors"))
        self.host.enable_extras()
        data = self.sensors.read()
        fan = self.snap.get("g_fan")
        if fan is not None:
            rows.append(("row", "GPU fan", f"{fan:.0f} %"))
        shown = 0
        for kind, hw, st, name, v in data:
            if st == "Fan":
                rows.append(("row", f"{name[:28]}", f"{v:.0f} RPM"))
                shown += 1
        if not shown and fan is None:
            rows.append(("row", "Fans", "n/a (no readable fan sensor)"))
        board = [x for x in data if x[0] in ("Motherboard", "SuperIO",
                                             "EmbeddedController", "Cooler")]
        temps = [x for x in board if x[2] == "Temperature"][:5]
        for kind, hw, st, name, v in temps:
            rows.append(("row", f"Board · {name[:24]}", f"{v:.0f} °C",
                         Thresholds.temp(v)))
        for kind, hw, st, name, v in [x for x in data if x[0] == "Storage"
                                      and x[2] == "Temperature"][:4]:
            rows.append(("row", f"Drive · {hw[:18]}", f"{v:.0f} °C",
                         Thresholds.temp(v)))
        for kind, hw, st, name, v in [x for x in board
                                      if x[2] == "Voltage"][:4]:
            rows.append(("row", f"Voltage · {name[:22]}", f"{v:.2f} V"))
        if not board:
            why = ("run as Administrator" if not self.is_admin() else
                   "driver or board not supported")
            rows.append(("row", "Motherboard sensors", f"n/a ({why})"))
        return rows

    def _battery_health(self):
        wmi = self.info.battery_wmi
        if wmi and wmi[0] > 0:
            return f"{wmi[1] / wmi[0] * 100:.0f} % of design capacity"
        for kind, hw, st, name, v in self.sensors.read():
            if kind == "Battery" and "Degradation" in name:
                return f"{100 - v:.0f} % of design capacity"
        return "n/a" if self.info.ready else "reading..."

    def rows_system(self):
        inf, h = self.info, self.host
        gpus = inf.gpu_drivers or ([(pretty_name(self.gpu.display_name()), "")]
                                   if self.gpu.display_name() else [])
        rows = [("head", "Windows"),
                ("row", "Version", inf.windows or ("reading..." if not inf.ready
                                                   else "n/a")),
                ("row", "Administrator", "yes" if self.is_admin() else "no"),
                ("head", "Hardware"),
                ("row", "CPU", h.cpu_name_raw or inf.cpu_registry or "n/a"),
                ("row", "Motherboard", h.board_name or "n/a")]
        for i, (name, drv) in enumerate(gpus[:3]):
            rows.append(("row", f"GPU {i + 1}", name[:40]))
            rows.append(("row", "  driver", drv or (
                inf.nvidia_driver if "nvidia" in name.lower() else "") or "n/a"))
        if inf.nvidia_driver:
            rows.append(("row", "NVIDIA driver", inf.nvidia_driver))
        rows += [("row", "PawnIO driver", "installed" if self.driver_ok()
                  else "missing"),
                 ("head", AppInfo.NAME),
                 ("row", "Version", AppInfo.VERSION),
                 ("row", "Publisher", AppInfo.PUBLISHER or "Not set"),
                 ("row", "Python", sys.version.split()[0])]
        return rows


# =============================================================== Displays
Monitor = namedtuple("Monitor", "name index x y w h primary res_w res_h hz")




class CpuLoad:
    """CPU usage for the dashboard.

    Uses its own counters so it never disturbs the overlay's psutil reading.
    """

    def __init__(self):
        self.prev = psutil.cpu_times()

    def read(self):
        cur = psutil.cpu_times()
        a, b = self.prev, cur
        self.prev = cur
        total = sum(b) - sum(a)
        idle = b.idle - a.idle
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, (1 - idle / total) * 100))


def pretty_name(raw):
    """'nvidia geforce rtx 3060 laptop gpu' -> 'GeForce RTX 3060' (short)."""
    if not raw:
        return "Not detected"
    fix = {"geforce": "GeForce", "rtx": "RTX", "gtx": "GTX", "radeon": "Radeon",
           "ryzen": "Ryzen", "gpu": "GPU", "core": "Core", "graphics": "Graphics",
           "iris": "Iris", "arc": "Arc", "xe": "Xe", "uhd": "UHD", "rx": "RX",
           "ti": "Ti", "super": "Super", "xt": "XT", "ultra": "Ultra"}
    drop = {"nvidia", "amd", "intel", "(r)", "(tm)", "cpu", "processor", "@",
            "laptop", "with"}
    words = []
    for w in raw.split():
        low = w.lower().replace("(r)", "").replace("(tm)", "")
        if not low or low in drop or low.endswith("ghz"):
            continue
        if low in fix:
            words.append(fix[low])
        elif any(ch.isdigit() for ch in low):
            up = low.upper()
            words.append(up[0].lower() + up[1:] if low[:2] in
                         ("i3", "i5", "i7", "i9") else up)
        else:
            words.append(low.capitalize())
    while words and words[-1] in ("GPU", "Graphics"):
        words.pop()  # "... Laptop GPU" -> model name only
    text = " ".join(words) or raw
    return text if len(text) <= 24 else text[:23].rstrip() + "…"


# =============================================================== Card status
class CardStatus:
    """Status word of a dashboard card (shared by every UI).

    Limits are Lmonitor's own choices (see SessionAnalyzer / DiagAnalyzer):
    hot = GPU 80 / CPU 90 C, warm = 10 C below, high load = 90 %,
    RAM warm >= 80 %, disk low < 20 % free, almost full < 10 % free.
    Missing data is "none" - never a guess.
    """

    @staticmethod
    def heat(use, temp, hot):
        if use is None and temp is None:
            return "none"
        if temp is not None and temp >= hot:
            return "hot"
        if use is not None and use >= 90:
            return "high"
        if temp is not None and temp >= hot - 10:
            return "warm"
        return "ok"

    @staticmethod
    def ram(use):
        return "none" if use is None else "high" if use >= 90 else \
            "warm" if use >= 80 else "ok"

    @staticmethod
    def disk(free_pct):
        return "full" if free_pct < DiagAnalyzer.CRIT_FREE_PCT else \
            "low" if free_pct < DiagAnalyzer.LOW_FREE_PCT else "ok"


# =============================================================== Overlay data
class OverlayModel:
    """What the overlay bar shows: text + color per item, no drawing.

    Both the Tk bar and the Qt bar use this. ``color`` is a Thresholds color,
    or None for "normal" (the UI then uses the user's value color).
    """

    def __init__(self, settings, cpu, gpu, memory, fps):
        self.settings = settings
        self.cpu, self.gpu, self.memory, self.fps = cpu, gpu, memory, fps
        self.network = NetworkReader()      # its own counters

    def need(self):
        """group name -> is any item of it switched on"""
        show = self.settings.show
        return {g: any(show.get(k) for k, _, _ in items)
                for g, items in Metrics.GROUPS}

    def system(self, need=None):
        """GPU / CPU / RAM / NET items -> {key: (text, color|None)}."""
        show = self.settings.show
        need = self.need() if need is None else need
        out = {}
        if need.get("GPU"):
            use, temp, pw, clk, mem = self.gpu.read(show)
            out["g_use"] = (f"{use:.0f}%" if use is not None else "--", Thresholds.use(use))
            out["g_temp"] = (f"{temp:.0f}°C" if temp is not None else "--", Thresholds.temp(temp))
            out["g_pow"] = (f"{pw:.0f}W" if pw is not None else "--", None)
            out["g_clk"] = (f"{clk:.0f}MHz" if clk is not None else "--", None)
            if mem is not None:
                out["g_mem"] = (f"{mem[0]:.1f}/{mem[1]:.0f}GB",
                                Thresholds.use(mem[0] / mem[1] * 100))
            else:
                out["g_mem"] = ("--", None)
        if need.get("CPU"):
            if show["c_use"]:
                v = self.cpu.usage()
                out["c_use"] = (f"{v:.0f}%", Thresholds.use(v))
            if show["c_temp"] or show["c_pow"] or show["c_clk"]:
                t, p, c, approx = self.cpu.read(show["c_temp"], show["c_pow"],
                                                show["c_clk"])
                out["c_temp"] = (f"{t:.0f}°C" if t is not None else "--", Thresholds.temp(t))
                out["c_pow"] = (f"{p:.0f}W" if p is not None else "--", None)
                out["c_clk"] = ((f"{'~' if approx else ''}{c:.0f}MHz"
                                 if c is not None else "--"), None)
        if need.get("RAM"):
            if show["r_use"] or show["r_amt"]:
                vm = self.memory.ram()
                out["r_use"] = (f"{vm.percent:.0f}%", Thresholds.use(vm.percent))
                out["r_amt"] = (f"{vm.used / 1024**3:.1f}/{vm.total / 1024**3:.0f}GB", None)
            if show["r_swap"]:
                sw = self.memory.swap()
                if sw.total:
                    out["r_swap"] = (f"Swap {sw.percent:.0f}% {sw.used / 1024**3:.1f}GB",
                                     Thresholds.use(sw.percent))
                else:
                    out["r_swap"] = ("Swap off", None)
        if need.get("NET"):
            self.network.read()
            down, up = self.network.total()
            unit = self.settings["net_unit"]
            out["n_down"] = ("↓ " + fmt_net(down, unit), None)
            out["n_up"] = ("↑ " + fmt_net(up, unit), None)
        return out

    def frames(self, want_graph):
        """FPS items -> ({key: (text, color|None)}, graph list | None).
        graph is None when there is nothing to draw."""
        data = self.fps.snapshot(want_graph)
        if data is None:
            return ({"fps": ("N/A", None), "avg": ("Avg N/A", None),
                     "low": ("1%Low N/A", None), "ft": ("-- ms", None)}, None)
        fps, avg, low, ft, graph = data
        return ({"fps": (f"{fps:.0f}", None), "avg": (f"Avg {avg:.0f}", None),
                 "low": (f"1%Low {low:.0f}" if low else "1%Low --", None),
                 "ft": (f"{ft:.1f}ms", None)}, graph)

