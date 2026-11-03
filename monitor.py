"""Lmonitor - lightweight gaming overlay for Windows.

QUICK MAP  (press Ctrl+F and search for the class name)
  Paths ............ where files live (settings, log, DLLs, installers)
  Theme ............ colors, fonts and sizes (overlay + settings window)
  Metrics .......... the list of overlay items; add or remove an item here
  Thresholds ....... white / yellow / red limits for temperature and usage
  Logger ........... writes errors to error.log (the app has no console)
  Settings ......... saved options (settings.json)
  WinApi ........... Windows tricks: admin, click-through, always-on-top
  LibreHardwareHost  loads the LibreHardwareMonitor DLL and finds the sensors
  CpuReader ........ CPU usage / temperature / power / clock
  GpuReader ........ GPU numbers (NVML first, LibreHardwareMonitor fills gaps)
  MemoryReader ..... RAM and Swap
  FpsMonitor ....... PresentMon -> FPS, average, 1% low, frametime
  DriverManager .... PawnIO driver check / install
  Diagnostics ...... "Save sensor report"
  AppInfo, SystemInfo, StorageReader, NetworkReader, BatteryReader,
  SensorReader, Telemetry ... real data for the Performance / Hardware pages
  DisplayManager ... connected monitors (plug / unplug / resolution)
  Overlay .......... the bar drawn on screen
  MetricsUpdater ... turns numbers into text and colors on the overlay
  Logo, Icons ...... the Lmonitor logo / .ico and the menu icons (PIL)
  Gfx, Segmented, Switch, Slider, Chip, Bar, LineChart, InfoTable, NavMenu,
  ReorderList ... drawing + widgets
  SettingsWindow ... the main window: Dashboard, Performance, Hardware, Display,
                    Appearance, Metrics, Order, Personalize
  TrayIcon ......... the icon next to the clock
  App .............. connects everything; timers; start / stop
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
import tkinter as tk
import tkinter.font as tkfont
import tkinter.messagebox as mbox
from collections import deque, namedtuple
from copy import deepcopy
from ctypes import wintypes

import clr
import psutil
import pystray
from PIL import Image, ImageDraw, ImageFilter, ImageTk

try:
    import pynvml
except Exception:
    pynvml = None

BOX = getattr(Image, "Resampling", Image).BOX


# The data engine lives in lmonitor/engine.py (no window code there).
from lmonitor.engine import *  # noqa: F401,F403,E402


# =============================================================== Overlay
class Overlay:
    """The bar drawn on screen (pure view, no sensor code).

    Looks:  "dark"  - solid tinted bar with -alpha transparency.
            "glass" - Windows blur-behind (acrylic) with a tint; the labels sit
                      on a see-through key color so the blur shows between them.
    Move mode: the click-through flag is removed, the bar gets a solid panel
    and an accent outline, and it can be dragged with the mouse.
    """
    KEY = "#010101"          # see-through color in glass mode
    EDGE = "#3c404b"         # thin glass edge

    def __init__(self, root, settings, group_colors, displays=None):
        self.root = root
        self.settings = settings
        self.colors = group_colors
        self.displays = displays or DisplayManager(root)
        self.fallback = False               # chosen display is not connected
        self.moving = False
        self.glass_ok = WinApi.blur_supported()
        self.x = self.y = 0                 # where the bar really is
        self.slide = 1.0                    # 1 = in place, 0 = above the screen
        self.on_move_end = None             # callback(x, y) after a drag
        self.on_move_done = None            # callback() right-click / double-click
        self._drag = None
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg=self.bg)
        self.top.withdraw()
        self.font = tkfont.Font(family=Theme.OVERLAY_FONT, size=settings["text"],
                                weight="bold")            # values
        self.label_font = tkfont.Font(family=Theme.OVERLAY_FONT,
                                      size=settings["text"], weight="bold")
        self.apply_font()
        self.labels = {}   # key -> Label
        self.cache = {}    # key -> (text, color) currently shown
        self.need = {}     # group name -> any item visible
        self.canvas = None
        self.canvas_item = None
        self.photo = None
        self.gw, self.gh = Theme.GRAPH_W, Theme.GRAPH_H
        self.graph_dirty = True
        self.last_geo = ""

    # ---- look
    @property
    def tint(self):
        return Theme.overlay_bg(self.settings["bg"])

    @property
    def glass(self):
        """True while the blur look is really in use."""
        return (self.settings["look"] == "glass" and self.glass_ok
                and not self.moving)

    @property
    def bg(self):
        return self.KEY if self.glass else self.tint

    @property
    def has_content(self):
        return bool(self.labels) or self.canvas is not None

    def invalidate(self):
        self.last_geo = ""

    def apply_look(self):
        """Apply transparency / blur / outline for the current settings."""
        top, S = self.top, self.settings
        alpha = S["alpha"] / 100
        glass = self.glass
        thick = 2                         # constant: the bar never changes size
        if self.moving:
            edge = Theme.ACCENT_HI
        elif glass:
            edge = self.EDGE
        else:
            edge = self.tint
        try:
            top.configure(bg=self.bg, highlightthickness=thick,
                          highlightbackground=edge)
            if glass:
                top.attributes("-transparentcolor", self.KEY)
                top.attributes("-alpha", 1.0)
            else:
                top.attributes("-transparentcolor", "")
                top.attributes("-alpha", alpha)   # same opacity while moving
        except Exception:
            Logger.error("overlay look")
        if glass:
            # the tint opacity follows the Opacity slider (40..100 %)
            if not WinApi.set_blur(top, self.tint, int(255 * alpha * 0.9)):
                self.glass_ok = False   # Windows refused: fall back to dark
                self.build()
                self.apply_look()
                return
        else:
            WinApi.set_blur(top, None)
        WinApi.round_corners(top)

    # ---- building
    def build(self):
        """Create the widgets for the visible metrics, in the saved order."""
        T = Theme
        show = self.settings.show
        bg = self.bg
        for child in self.top.winfo_children():
            child.destroy()
        self.labels.clear()
        self.cache.clear()
        self.need.clear()
        self.canvas = self.canvas_item = None
        self.top.configure(bg=bg)
        horizontal = self.settings["layout"] == "h"
        side = "left" if horizontal else "top"
        first = True
        for gname, items in Metrics.ordered(self.settings["order"]):
            vis = [it for it in items if show[it[0]]]
            self.need[gname] = bool(vis)
            if not vis:
                continue
            labels = [it for it in vis if it[0] != "graph"]
            has_graph = len(labels) != len(vis)
            if horizontal and not first:
                tk.Label(self.top, text="|", font=self.label_font, fg=T.GRAY,
                         bg=bg, padx=0).pack(side="left")
            first = False
            if has_graph and not horizontal and vis[0][0] == "graph":
                self._make_graph(self.top, False)
            frame = self.top
            if labels:
                frame = tk.Frame(self.top, bg=bg)
                frame.pack(side=side, anchor="w")
                tk.Label(frame, text=gname, font=self.label_font,
                         fg=self.colors[gname], bg=bg,
                         width=0 if horizontal else 4, anchor="w",
                         padx=3 if horizontal else 1).pack(side="left")
            for key, _, width in vis:
                if key == "graph":
                    if horizontal:   # sits where the item is in the order
                        self._make_graph(frame, True)
                    continue
                lbl = tk.Label(frame, text="--", font=self.font, fg=self.value_hex(),
                               bg=bg, width=0 if horizontal else width,
                               anchor="w", padx=3 if horizontal else 1)
                lbl.pack(side="left")
                self.labels[key] = lbl
            if has_graph and not horizontal and vis[0][0] != "graph":
                self._make_graph(self.top, False)
        if self.moving:
            self._bind_drag(self.top)
            for w in self._all_widgets(self.top):
                self._bind_drag(w)
        self.invalidate()

    def _make_graph(self, parent, horizontal):
        self.canvas = tk.Canvas(parent, bg=self.bg, highlightthickness=0,
                                width=1, height=1)
        if horizontal:
            self.canvas.pack(side="left", padx=6)
        else:
            self.canvas.pack(side="top", anchor="w", padx=4, pady=2)
        self.canvas_item = self.canvas.create_image(0, 0, anchor="nw")
        self.resize_graph()

    def _all_widgets(self, w):
        out = []
        for c in w.winfo_children():
            out.append(c)
            out += self._all_widgets(c)
        return out

    # ---- window
    def monitor(self):
        """The display the bar belongs on (Primary if the chosen one is gone)."""
        mon, self.fallback = self.displays.resolve(self.settings["monitor"])
        return mon

    def clamp(self, x, y, w, h, mon=None):
        """Keep the whole bar inside one display."""
        mon = mon or self.displays.at(x + w // 2, y + h // 2)
        return (max(mon.x, min(mon.x + mon.w - w, x)),
                max(mon.y, min(mon.y + mon.h - h, y)))

    def relative(self):
        """Bar position relative to its display (what is saved)."""
        mon, _ = self.displays.resolve(self.settings["monitor"])
        return self.x - mon.x, self.y - mon.y

    def place(self):
        top = self.top
        top.update_idletasks()
        w, h = top.winfo_reqwidth(), top.winfo_reqheight()
        S, mon = self.settings, self.monitor()
        pos, y = S["pos"], mon.y
        if pos == "custom" and S["x"] is not None and S["y"] is not None:
            x, y = self.clamp(mon.x + S["x"], mon.y + S["y"], w, h, mon)
        elif pos == "center":
            x = mon.x + (mon.w - w) // 2
        elif pos == "right":
            x = mon.x + mon.w - w - Theme.MARGIN
        else:
            x = mon.x + Theme.MARGIN
        self.x, self.y = x, y
        geo = f"{w}x{h}+{x}+{self._draw_y(h)}"
        if geo != self.last_geo:
            self.last_geo = geo
            top.geometry(geo)

    def _draw_y(self, h):
        """Where the bar is drawn: slide 1 = its place, 0 = just above the top
        edge of its display (F9 mode)."""
        if self.slide >= 1.0:
            return self.y
        y0 = self.monitor().y - h - 6
        return int(y0 + (self.y - y0) * Gfx.ease(max(0.0, self.slide)))

    def set_slide(self, r):
        """Move the bar between 'above the screen' (0) and its place (1)."""
        self.slide = max(0.0, min(1.0, r))
        top = self.top
        w, h = top.winfo_reqwidth(), top.winfo_reqheight()
        geo = f"{w}x{h}+{self.x}+{self._draw_y(h)}"
        if geo != self.last_geo:
            self.last_geo = geo
            top.geometry(geo)

    def show(self):
        self.place()
        self.top.deiconify()
        self.top.update_idletasks()
        self.apply_look()
        if self.moving:
            WinApi.make_interactive(self.top)
        else:
            WinApi.make_click_through(self.top)

    def hide(self):
        self.top.withdraw()

    def value_hex(self):
        for k, _, col in Theme.VALUE_COLORS:
            if k == self.settings["value_color"]:
                return col or Theme.ACCENT
        return Theme.WHITE

    FALLBACKS = ("Consolas", "Cascadia Mono", "Courier New")

    def families(self):
        try:
            return {f.lower(): f for f in tkfont.families(self.top)}
        except Exception:
            return {}

    def resolve_font(self, name):
        """The installed family to use: the chosen one, else a safe fallback."""
        fams = self.families()
        for cand in (name,) + self.FALLBACKS:
            if cand and cand.lower() in fams:
                return fams[cand.lower()]
        return "Courier New"

    def apply_font(self):
        """Family / weight / size from the settings - live, no restart."""
        S = self.settings
        fam = self.resolve_font(S["font"])
        self.font.configure(family=fam, size=S["text"], weight=S["weight"])
        self.label_font.configure(family=fam, size=S["text"],
                                  weight=S["label_weight"])
        self.invalidate()

    def set_font_size(self, size):
        self.font.configure(size=size)
        self.label_font.configure(size=size)
        self.invalidate()

    def set_alpha(self, percent=None):
        self.apply_look()

    # ---- move with the mouse
    def _bind_drag(self, w):
        w.bind("<ButtonPress-1>", self._drag_start)
        w.bind("<B1-Motion>", self._drag_move)
        w.bind("<ButtonRelease-1>", self._drag_end)
        w.bind("<Double-Button-1>", self._done)
        w.bind("<Button-3>", self._done)
        try:
            w.configure(cursor="fleur")
        except Exception:
            pass

    def _drag_start(self, e):
        self._drag = (e.x_root - self.x, e.y_root - self.y)

    def _drag_move(self, e):
        if not self._drag:
            return
        w, h = self.top.winfo_reqwidth(), self.top.winfo_reqheight()
        ax, ay = e.x_root - self._drag[0], e.y_root - self._drag[1]
        mon = self.displays.at(ax + w // 2, ay + h // 2)  # display under the bar
        x, y = self.clamp(ax, ay, w, h, mon)
        if (x, y) != (self.x, self.y):
            self.x, self.y = x, y
            S = self.settings
            keep_auto = mon.primary and S["monitor"] == "primary"
            S["monitor"] = "primary" if keep_auto else mon.name
            S["x"], S["y"], S["pos"] = x - mon.x, y - mon.y, "custom"
            self.last_geo = f"{w}x{h}+{x}+{y}"
            self.top.geometry(self.last_geo)

    def _drag_end(self, e):
        if self._drag:
            self._drag = None
            if self.on_move_end:
                self.on_move_end(self.x, self.y)

    def _done(self, e=None):
        if self.on_move_done:
            self.on_move_done()

    # ---- values
    def put(self, key, text, color=Theme.WHITE):
        """Show text on one label; returns True when something changed."""
        lbl = self.labels.get(key)
        if lbl is None:
            return False
        if color == Theme.WHITE:          # "normal" value: the chosen color
            color = self.value_hex()
        k = (text, color)
        if self.cache.get(key) == k:
            return False
        self.cache[key] = k
        lbl.config(text=text, fg=color)
        return True

    # ---- graph
    def resize_graph(self):
        T = Theme
        self.gw = int(T.GRAPH_W * self.settings["graph"] / 100)
        self.gh = int(T.GRAPH_H * self.settings["graph"] / 100)
        self.canvas.config(width=self.gw, height=self.gh)
        self.photo = ImageTk.PhotoImage(Image.new("RGB", (self.gw, self.gh),
                                                  self.bg))
        self.canvas.itemconfig(self.canvas_item, image=self.photo)
        self.graph_dirty = True

    def draw_graph(self, vals):
        T = Theme
        gw, gh, ss = self.gw, self.gh, T.GRAPH_SS
        n = len(vals)
        im = Image.new("RGB", (gw * ss, gh * ss), self.bg)
        if n >= 2:
            step = gw * ss / T.GRAPH_POINTS
            k = (gh * ss - 2) / T.GRAPH_TOP_MS
            pts = [(gw * ss - (n - i) * step,
                    gh * ss - 1 - min(v, T.GRAPH_TOP_MS) * k)
                   for i, v in enumerate(vals)]
            ImageDraw.Draw(im).line(pts, fill=T.NVIDIA_GREEN, width=ss,
                                    joint="curve")
        self.photo.paste(im.resize((gw, gh), BOX))

    # ---- preview picture used by the Appearance page
    @staticmethod
    def preview(look, tint, accent, w, h):
        """A small picture of the bar over a colorful scene (PIL, RGBA)."""
        s = 2
        W, H = w * s, h * s
        scene = Image.new("RGB", (W, H))
        sd = ImageDraw.Draw(scene)
        c1, c2 = (38, 70, 160), (150, 62, 200)
        for x in range(W):
            t = x / max(1, W - 1)
            sd.line([(x, 0), (x, H)], fill=tuple(
                int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
        for cx, cy, r, col in ((0.2, 0.3, 0.22, (255, 170, 60)),
                               (0.75, 0.75, 0.3, (40, 200, 190)),
                               (0.55, 0.2, 0.15, (255, 90, 120))):
            sd.ellipse([(cx - r) * W, (cy - r) * H * 1.6,
                        (cx + r) * W, (cy + r) * H * 1.6], fill=col)
        box = (int(W * .10), int(H * .30), int(W * .90), int(H * .70))
        bw, bh = box[2] - box[0], box[3] - box[1]
        crop = scene.crop(box)
        tint_img = Image.new("RGB", (bw, bh), tint)
        if look == "glass":
            panel = Image.blend(crop.filter(ImageFilter.GaussianBlur(7 * s)),
                                tint_img, 0.55)
            sheen = Image.new("RGBA", (bw, bh), (255, 255, 255, 0))
            sh = ImageDraw.Draw(sheen)
            for y in range(int(bh * .5)):
                sh.line([(0, y), (bw, y)],
                        fill=(255, 255, 255, int(46 * (1 - y / (bh * .5)))))
            panel = Image.alpha_composite(panel.convert("RGBA"), sheen)
        else:
            panel = Image.blend(crop, tint_img, 0.84).convert("RGBA")
        mask = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1],
                                               radius=10 * s, fill=255)
        scene = scene.convert("RGBA")
        scene.paste(panel, box[:2], mask)
        d = ImageDraw.Draw(scene)
        edge = (255, 255, 255, 90) if look == "glass" else (255, 255, 255, 25)
        d.rounded_rectangle([box[0], box[1], box[2] - 1, box[3] - 1],
                            radius=10 * s, outline=edge, width=s)
        bars = ((0.28, (255, 255, 255)), (0.18, Gfx._rgb(accent)),
                (0.22, (255, 212, 0)), (0.14, (176, 176, 176)))
        x = box[0] + 12 * s
        cy = (box[1] + box[3]) // 2
        for frac, col in bars:
            bar_w = int(bw * frac * .8)
            d.rounded_rectangle([x, cy - 3 * s, x + bar_w, cy + 3 * s],
                                radius=3 * s, fill=col + (255,))
            x += bar_w + 8 * s
        out = Image.new("L", (W, H), 0)
        ImageDraw.Draw(out).rounded_rectangle([0, 0, W - 1, H - 1],
                                              radius=14 * s, fill=255)
        scene.putalpha(out)
        return scene.resize((w, h), BOX)


# =============================================================== MetricsUpdater
class RevealController:
    """F9 mode: the bar slides down from the top edge of its display, stays
    N seconds, then slides back up. Press F9 again while it is down to keep it
    N more seconds. The motion follows the clock, so it stays smooth even if
    a frame is late."""
    VK_F9 = 0x78
    SLIDE = 0.35            # seconds for one slide
    FRAME_MS = 15

    def __init__(self, app):
        self.app = app
        self.state = "hidden"       # hidden / in / shown / out
        self.r = 0.0
        self.hold_until = 0.0
        self.last = 0.0
        self.down = False
        self.job = None

    @property
    def active(self):
        return self.state != "hidden"

    def enabled(self):
        return self.app.settings["show_mode"] == "hotkey"

    def poll(self):
        """Called every ~40 ms: a new press of F9 starts / extends the show."""
        d = WinApi.key_down(self.VK_F9)
        if d and not self.down:
            self.press()
        self.down = d

    def press(self, now=None):
        if not self.enabled() or not self.app.shown or self.app.moving:
            return False
        now = time.time() if now is None else now
        if self.state == "hidden":
            self.state, self.r, self.last = "in", 0.0, now
            ov = self.app.overlay
            ov.slide = 0.0
            self.app.refresh()          # fresh numbers before it appears
            ov.show()                   # placed above the screen, then slides
            self._loop()
        elif self.state == "out":
            self.state = "in"
        elif self.state == "shown":
            self.hold_until = now + self.app.settings["hotkey_secs"]
        return True

    def step(self, now):
        """One animation step; False when the bar is hidden again."""
        dt, self.last = max(0.0, now - self.last), now
        ov = self.app.overlay
        if self.state == "in":
            self.r = min(1.0, self.r + dt / self.SLIDE)
            if self.r >= 1.0:
                self.state = "shown"
                self.hold_until = now + self.app.settings["hotkey_secs"]
        elif self.state == "shown":
            if now >= self.hold_until:
                self.state = "out"
        elif self.state == "out":
            self.r = max(0.0, self.r - dt / self.SLIDE)
            if self.r <= 0.0:
                self.state = "hidden"
        ov.set_slide(self.r)
        if self.state == "hidden":
            ov.hide()
            return False
        return True

    def _loop(self):
        try:
            more = self.step(time.time())
        except Exception:
            Logger.error("reveal")
            more = False
            self.reset()
        self.job = self.app.root.after(self.FRAME_MS, self._loop) if more else None

    def reset(self):
        """Stop any slide (mode changed): the bar goes back to its place."""
        if self.job is not None:
            try:
                self.app.root.after_cancel(self.job)
            except Exception:
                pass
            self.job = None
        self.state, self.r = "hidden", 0.0
        self.app.overlay.slide = 1.0


class MetricsUpdater:
    """Reads the sensors (through OverlayModel) and writes text + colors to
    the Tk overlay."""

    def __init__(self, settings, overlay, cpu, gpu, memory, fps):
        self.settings = settings
        self.overlay = overlay
        self.model = OverlayModel(settings, cpu, gpu, memory, fps)
        self.cpu, self.gpu, self.memory, self.fps = cpu, gpu, memory, fps
        self.network = self.model.network

    def update_system(self):
        """GPU / CPU / RAM / NET (once per second, only what is visible)."""
        o = self.overlay
        ch = False
        for key, (text, color) in self.model.system(o.need).items():
            ch |= o.put(key, text) if color is None else o.put(key, text, color)
        if ch:
            o.place()

    def update_fps(self):
        """FPS group (twice per second)."""
        o = self.overlay
        items, graph = self.model.frames(o.canvas is not None)
        ch = False
        for key, (text, color) in items.items():
            ch |= o.put(key, text)
        if graph is None:
            if o.canvas is not None and o.graph_dirty:
                o.draw_graph(())
                o.graph_dirty = False
        else:
            o.draw_graph(graph)
            o.graph_dirty = True
        if ch:
            o.place()


# =============================================================== Brand: Logo + Icons
class Logo:
    """The Lmonitor logo, drawn with PIL so it is always sharp.

    A rounded dark tile, a white "L" stem and a foot that turns into a
    frametime pulse. The pulse uses the accent color of the active theme.
    """
    _cache = {}
    ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

    @staticmethod
    def _rgb(c, a=255):
        return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), a)

    @classmethod
    def render(cls, size=64, accent=None):
        """-> RGBA PIL image (size x size)."""
        accent = accent or Theme.ACCENT
        key = (size, accent)
        if key in cls._cache:
            return cls._cache[key]
        s = 8 if size <= 64 else 4
        N = size * s
        im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # tile with a soft vertical gradient
        tile = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        top, bot = cls._rgb("#262932"), cls._rgb("#101116")
        gd = ImageDraw.Draw(tile)
        for y in range(N):
            t = y / max(1, N - 1)
            gd.line([(0, y), (N, y)], fill=tuple(
                int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
        mask = Image.new("L", (N, N), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, N - 1, N - 1], radius=int(N * 0.23), fill=255)
        im.paste(tile, (0, 0), mask)
        d.rounded_rectangle([s // 2, s // 2, N - 1 - s // 2, N - 1 - s // 2],
                            radius=int(N * 0.23), outline=cls._rgb(accent, 90),
                            width=max(1, int(N * 0.018)))
        w = int(N * 0.095)

        def P(x, y):
            return (x * N, y * N)

        def stroke(points, color):
            d.line([P(*p) for p in points], fill=color, width=w, joint="curve")
            for x, y in (points[0], points[-1]):  # round caps
                cx, cy = P(x, y)
                d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2],
                          fill=color)

        stroke([(0.31, 0.22), (0.31, 0.70)], cls._rgb("#f4f4f7"))
        stroke([(0.31, 0.70), (0.47, 0.70), (0.56, 0.45), (0.65, 0.80),
                (0.71, 0.70), (0.79, 0.70)], cls._rgb(accent))
        out = im.resize((size, size), BOX)
        cls._cache[key] = out
        return out

    @classmethod
    def photo(cls, size, accent=None):
        return ImageTk.PhotoImage(cls.render(size, accent))

    @classmethod
    def save_ico(cls, path, accent=None):
        """Multi-size .ico (used by the exe, taskbar and shortcuts)."""
        big = cls.render(256, accent or Theme.NEUTRAL["accent"])
        big.save(path, format="ICO", sizes=[(n, n) for n in cls.ICO_SIZES])
        return path


class Icons:
    """Small flat icons for the menu (drawn with PIL, cached)."""
    _cache = {}

    @classmethod
    def get(cls, name, color, size=20):
        key = (name, color, size)
        if key not in cls._cache:
            cls._cache[key] = ImageTk.PhotoImage(cls.render(name, color, size))
        return cls._cache[key]

    @staticmethod
    def render(name, color, size=20):
        s = 8
        N = size * s
        im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
        lw = max(2, int(N * 0.09))

        def box(x1, y1, x2, y2, r=0.08, fill=None, width=0):
            d.rounded_rectangle([x1 * N, y1 * N, x2 * N, y2 * N],
                                radius=r * N, fill=fill,
                                outline=c if width else None, width=width)

        def line(pts):
            d.line([(x * N, y * N) for x, y in pts], fill=c, width=lw)
            for x, y in (pts[0], pts[-1]):
                d.ellipse([x * N - lw / 2, y * N - lw / 2,
                           x * N + lw / 2, y * N + lw / 2], fill=c)

        if name == "dashboard":
            for x, y in ((0.12, 0.12), (0.54, 0.12), (0.12, 0.54), (0.54, 0.54)):
                box(x, y, x + 0.34, y + 0.34, 0.09, fill=c)
        elif name == "display":
            box(0.1, 0.16, 0.9, 0.68, 0.1, width=lw)
            line([(0.5, 0.70), (0.5, 0.84)])
            line([(0.32, 0.86), (0.68, 0.86)])
        elif name == "metrics":
            for y, kx in ((0.24, 0.66), (0.5, 0.34), (0.76, 0.7)):
                line([(0.12, y), (0.88, y)])
                d.ellipse([kx * N - 0.13 * N, y * N - 0.13 * N,
                           kx * N + 0.13 * N, y * N + 0.13 * N],
                          fill=(0, 0, 0, 0), outline=c, width=lw)
        elif name == "appearance":
            d.ellipse([0.12 * N, 0.12 * N, 0.88 * N, 0.88 * N], outline=c,
                      width=lw)
            d.pieslice([0.12 * N, 0.12 * N, 0.88 * N, 0.88 * N], 90, 270, fill=c)
        elif name == "personalize":
            d.ellipse([0.1 * N, 0.12 * N, 0.9 * N, 0.88 * N], outline=c,
                      width=lw)
            for cx, cy in ((0.34, 0.38), (0.62, 0.34), (0.7, 0.58)):
                d.ellipse([(cx - .075) * N, (cy - .075) * N,
                           (cx + .075) * N, (cy + .075) * N], fill=c)
            d.ellipse([0.4 * N, 0.56 * N, 0.58 * N, 0.76 * N],
                      fill=(0, 0, 0, 0), outline=c, width=lw)
        elif name == "order":
            for y, x2 in ((0.26, 0.88), (0.5, 0.7), (0.74, 0.52)):
                line([(0.12, y), (x2, y)])
        elif name == "grip":
            for cx in (0.34, 0.66):
                for cy in (0.22, 0.5, 0.78):
                    d.ellipse([(cx - .08) * N, (cy - .08) * N,
                               (cx + .08) * N, (cy + .08) * N], fill=c)
        elif name == "gpu":
            box(0.06, 0.2, 0.94, 0.7, 0.1, width=lw)
            d.ellipse([0.3 * N, 0.28 * N, 0.62 * N, 0.62 * N], outline=c,
                      width=lw)
            line([(0.16, 0.82), (0.84, 0.82)])
        elif name == "performance":
            line([(0.1, 0.78), (0.34, 0.46), (0.54, 0.62), (0.9, 0.2)])
            line([(0.1, 0.9), (0.9, 0.9)])
        elif name in ("cpu", "hardware"):
            box(0.24, 0.24, 0.76, 0.76, 0.08, width=lw)
            box(0.4, 0.4, 0.6, 0.6, 0.03, fill=c)
            for t in (0.36, 0.5, 0.64):
                line([(t, 0.08), (t, 0.2)])
                line([(t, 0.8), (t, 0.92)])
                line([(0.08, t), (0.2, t)])
                line([(0.8, t), (0.92, t)])
        elif name == "storage":
            box(0.1, 0.16, 0.9, 0.44, 0.1, width=lw)
            box(0.1, 0.56, 0.9, 0.84, 0.1, width=lw)
            for y in (0.3, 0.7):
                d.ellipse([0.72 * N, (y - .04) * N, 0.8 * N, (y + .04) * N],
                          fill=c)
        elif name == "network":
            d.ellipse([0.1 * N, 0.1 * N, 0.9 * N, 0.9 * N], outline=c, width=lw)
            d.ellipse([0.34 * N, 0.1 * N, 0.66 * N, 0.9 * N], outline=c, width=lw)
            line([(0.1, 0.5), (0.9, 0.5)])
        elif name == "sessions":
            d.ellipse([0.1 * N, 0.1 * N, 0.9 * N, 0.9 * N], outline=c, width=lw)
            line([(0.5, 0.28), (0.5, 0.52), (0.68, 0.64)])
        elif name == "optimizer":
            for y, kx in ((0.24, 0.62), (0.5, 0.34), (0.76, 0.7)):
                line([(0.12, y), (0.88, y)])
                d.ellipse([kx * N - 0.1 * N, y * N - 0.1 * N, kx * N + 0.1 * N,
                           y * N + 0.1 * N], fill=c)
        elif name == "storage":
            box(0.1, 0.3, 0.9, 0.74, 0.12, width=lw)
            line([(0.1, 0.52), (0.9, 0.52)])
            d.ellipse([0.72 * N, 0.58 * N, 0.8 * N, 0.66 * N], fill=c)
        elif name == "reports":
            box(0.2, 0.1, 0.8, 0.9, 0.1, width=lw)
            for y in (0.34, 0.5, 0.66):
                line([(0.32, y), (0.68, y)])
        elif name == "diagnostics":
            box(0.12, 0.12, 0.88, 0.88, 0.14, width=lw)
            line([(0.3, 0.52), (0.45, 0.68), (0.72, 0.34)])
        elif name == "branch":
            for cx, cy in ((0.28, 0.2), (0.28, 0.8), (0.74, 0.34)):
                d.ellipse([(cx - .12) * N, (cy - .12) * N, (cx + .12) * N,
                           (cy + .12) * N], outline=c, width=lw)
            line([(0.28, 0.32), (0.28, 0.68)])
            line([(0.74, 0.46), (0.74, 0.52), (0.28, 0.66)])
        elif name == "ram":
            box(0.06, 0.28, 0.94, 0.7, 0.07, width=lw)
            for x in (0.22, 0.42, 0.62):
                box(x, 0.4, x + 0.12, 0.58, 0.02, fill=c)
            for x in (0.2, 0.4, 0.6, 0.8):
                line([(x, 0.78), (x, 0.88)])
        return im.resize((size, size), BOX)


# =============================================================== Gfx + widgets
class Gfx:
    """Drawing helpers for the menu canvas."""

    def __init__(self, canvas):
        self.ui = canvas
        self.tab = ""     # tag of the page being drawn
        self._img = {}

    @staticmethod
    def _rgb(c):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))

    def rr(self, w, h, r, color):
        """Anti-aliased rounded rectangle (drawn big, scaled down)."""
        k = (w, h, r, color)
        if k not in self._img:
            s = 6
            im = Image.new("RGBA", (w * s, h * s), self._rgb(color) + (0,))
            ImageDraw.Draw(im).rounded_rectangle(
                [0, 0, w * s - 1, h * s - 1], radius=r * s,
                fill=self._rgb(color) + (255,))
            self._img[k] = ImageTk.PhotoImage(im.resize((w, h), BOX))
        return self._img[k]

    def tags(self, *extra):
        return tuple(t for t in (self.tab,) + extra if t)

    def hand(self, tag):
        ui = self.ui
        ui.tag_bind(tag, "<Enter>", lambda e: ui.config(cursor="hand2"), add="+")
        ui.tag_bind(tag, "<Leave>", lambda e: ui.config(cursor=""), add="+")

    def card(self, x, y, w, h, r=16, color=None):
        return self.ui.create_image(
            x, y, anchor="nw", tags=self.tags(),
            image=self.rr(w, h, r, color or Theme.C_CARD))

    def label(self, x, y, text, color=None, font=None, anchor="w", **kw):
        return self.ui.create_text(x, y, text=text, fill=color or Theme.SUB,
                                   font=font or Theme.F_LABEL,
                                   anchor=anchor, tags=self.tags(), **kw)

    def title(self, text, sub):
        """Page heading (title + one-line description)."""
        self.label(Theme.PAGE_X, 34, text, Theme.TXT, Theme.F_TITLE)
        self.label(Theme.PAGE_X, 60, sub, Theme.DIM, Theme.F_SMALL)

    @staticmethod
    def ease(t):
        return 1 - (1 - t) ** 3

    def animate(self, owner, start, end, steps, apply):
        """Smooth value animation; cancels the previous one of the owner."""
        ui = self.ui
        if getattr(owner, "job", None):
            ui.after_cancel(owner.job)
            owner.job = None
        i = [0]

        def step():
            i[0] += 1
            apply(start + (end - start) * self.ease(i[0] / steps))
            owner.job = ui.after(14, step) if i[0] < steps else None
        step()


class Tooltip:
    """Small help bubble on the canvas: shows after a short hover, hides on
    leave, click or page change. One bubble at most; nothing is created until
    it is needed."""
    DELAY, LINE, MAXC = 450, 17, 36

    def __init__(self, gfx, width, height):
        self.g, self.ui, self.W, self.H = gfx, gfx.ui, width, height
        self.job = None
        self.texts = {}

    def bind(self, tag, text):
        """Show `text` when the mouse rests on items tagged `tag` (each tag
        must belong to one control, like every other binding here)."""
        ui = self.ui
        self.texts[tag] = text
        ui.tag_bind(tag, "<Enter>", lambda e, t=tag: self._arm(t, e), add="+")
        ui.tag_bind(tag, "<Leave>", lambda e: self.hide(), add="+")
        ui.tag_bind(tag, "<Button-1>", lambda e: self.hide(), add="+")

    def _arm(self, tag, e):
        self.hide()
        self.job = self.ui.after(self.DELAY, lambda: self.show(
            self.texts.get(tag, ""), e.x, e.y))

    def show(self, text, x, y):
        self.job = None
        if not text:
            return
        ui, T = self.ui, Theme
        lines = textwrap.wrap(text, self.MAXC) or [text]
        w = min(300, max(len(l) for l in lines) * 7 + 24)
        h = len(lines) * self.LINE + 16
        bx = max(6, min(x + 14, self.W - w - 6))
        by = y + 22 if y + 22 + h < self.H - 6 else y - h - 10
        ui.create_image(bx, by, anchor="nw", tags=("tip",),
                        image=self.g.rr(int(w), int(h), 8, T.mix(T.C_CARD, "#ffffff", .16)))
        ui.create_text(bx + 12, by + 8, anchor="nw", text="\n".join(lines),
                       fill=T.TXT, font=T.F_SMALL, tags=("tip",))
        ui.tag_raise("tip")

    def hide(self):
        if self.job is not None:
            try:
                self.ui.after_cancel(self.job)
            except Exception:
                pass
            self.job = None
        self.ui.delete("tip")


class LiveChart:
    """Live line/area chart drawn with native canvas items (no image is
    rebuilt per sample). New samples slide in smoothly: the lines are only
    moved with ``coords`` a few times per second, so it stays light."""

    SEGS = 3     # gaps in the data split a line; only the newest 3 parts are drawn

    def __init__(self, gfx, x, y, w, h, colors, fill=False, dot=False,
                 grid=0, width=2):
        self.ui, self.tags = gfx.ui, gfx.tags()
        self.x0, self.y0, self.w, self.h = x, y, w, h
        self.colors, self.fill, self.width = list(colors), fill, width
        for i in range(grid):
            gy = y + (h - 1) * i / max(1, grid - 1)
            self.ui.create_line(x, gy, x + w, gy, width=1, tags=self.tags,
                                fill=Theme.lift(Theme.C_CARD, 0.1))
        self.lines = [[] for _ in colors]
        self.areas = [[] for _ in colors]
        for i in range(len(colors)):       # fixed pool: nothing is created later
            self._pool(self.lines, i, "line", self.SEGS, fill="")
            if fill:
                self._pool(self.areas, i, "poly", self.SEGS, outline="", fill="")
        self.dots = ([self.ui.create_oval(0, 0, 0, 0, outline="", fill="",
                                          tags=self.tags) for _ in colors]
                     if dot else [])
        self.job = None
        self.last = None
        self.cur = None
        self.frames = 0

    # ---- geometry
    def _segments(self, vals, n, top, off):
        step = self.w / (n - 1)
        segs, seg = [], []
        for i, v in enumerate(vals):
            if v is None:
                if seg:
                    segs.append(seg)
                seg = []
                continue
            px = self.x0 + self.w - (len(vals) - 1 - i) * step + off
            seg.append((px, self.y0 + self.h - 3 - min(v, top) / top * (self.h - 6)))
        if seg:
            segs.append(seg)
        return [c for c in (self._clip(sg) for sg in segs) if len(c) >= 2][-self.SEGS:]

    def _clip(self, pts):
        lo, hi = self.x0, self.x0 + self.w
        out = []
        for i, (x, y) in enumerate(pts):
            if lo <= x <= hi:
                if not out and i and pts[i - 1][0] < lo:
                    px, py = pts[i - 1]
                    out.append((lo, py + (y - py) * (lo - px) / (x - px)))
                out.append((x, y))
            elif x > hi and i and pts[i - 1][0] <= hi:
                px, py = pts[i - 1]
                out.append((hi, py + (y - py) * (hi - px) / (x - px)))
        return out

    def _pool(self, pool, idx, kind, count, **kw):
        ui, items = self.ui, pool[idx]
        while len(items) < count:
            f = ui.create_line if kind == "line" else ui.create_polygon
            first = (0, 0, 0, 0) if kind == "line" else (0, 0, 0, 0, 0, 0)
            if kind == "line":
                kw = dict(kw, width=self.width, capstyle="round",
                          joinstyle="round", smooth=True, splinesteps=3)
            items.append(f(*first, tags=self.tags, **kw))
        return items

    def _draw(self, series, n, top, off, colors):
        ui = self.ui
        for idx, vals in enumerate(series):
            color = colors[idx]
            segs = self._segments(vals, n, top, off)
            lines, areas = self.lines[idx], self.areas[idx]
            base = self.y0 + self.h
            for k, item in enumerate(lines):
                if k < len(segs):
                    flat = [v for p in segs[k] for v in p]
                    ui.coords(item, *flat)
                    ui.itemconfig(item, fill=color)
                    if self.fill:
                        ui.coords(areas[k], *flat, segs[k][-1][0], base,
                                  segs[k][0][0], base)
                        ui.itemconfig(areas[k],
                                      fill=Theme.mix(Theme.C_CARD, color, 0.22))
                else:
                    ui.coords(item, 0, 0, 0, 0)
                    ui.itemconfig(item, fill="")
                    if self.fill:
                        ui.coords(areas[k], 0, 0, 0, 0, 0, 0)
                        ui.itemconfig(areas[k], fill="")
            if self.dots:
                if segs:
                    px, py = segs[-1][-1]
                    ui.coords(self.dots[idx], px - 3, py - 3, px + 3, py + 3)
                    ui.itemconfig(self.dots[idx], fill=color)
                else:
                    ui.itemconfig(self.dots[idx], fill="")

    # ---- public
    def set(self, series, n, top=100.0, colors=None, period=1.0):
        """series: lists oldest first (None = no data); n: samples that fit."""
        n = max(2, n)
        series = [list(v)[-n:] for v in series]
        colors = list(colors or self.colors)
        key = (tuple(tuple(v) for v in series), n, top, tuple(colors))
        if key == self.last:
            return
        prev = self.cur
        self.last = key
        self.cur = (series, n, top, colors)
        if self.job:
            self.ui.after_cancel(self.job)
            self.job = None
        slide = False
        if prev is not None and prev[1] == n and prev[2] == top:
            a, b = prev[0][0], series[0]
            slide = (len(b) > 1 and len(a) >= len(b) - 1 and
                     b[:-1] == a[len(a) - (len(b) - 1):])
        if not slide:
            self._draw(series, n, top, 0.0, colors)
            return
        step = self.w / (n - 1)
        self.frames = max(3, min(24, int(period * 800 / 33)))
        i = [0]

        def tick():
            i[0] += 1
            self._draw(series, n, top, step * (1 - i[0] / self.frames), colors)
            self.job = self.ui.after(33, tick) if i[0] < self.frames else None
        self._draw(series, n, top, step, colors)
        self.job = self.ui.after(33, tick)


class Spark:
    """A small area chart for the last samples."""
    N = 60

    def __init__(self, gfx, x, y, w, h, color):
        self.color = color
        self.chart = LiveChart(gfx, x, y, w, h, [color], fill=True)

    def update(self, vals, vmax=100.0, color=None):
        """vals: oldest first, None = no data. vmax None = automatic."""
        vals = list(vals)
        top = vmax or max([v for v in vals if v is not None] + [1.0]) * 1.15
        self.chart.set([vals], self.N, top, [color or self.color])


class Gauge:
    """Round usage gauge (open ring) with the value in the middle."""
    BOX_W, BOX_H = 112, 100

    def __init__(self, gfx, x, y, w, h, icon, title, color):
        self.g, self.ui, self.color = gfx, gfx.ui, color
        gfx.card(x, y, w, h)
        self.ui.create_image(x + 14, y + 22, anchor="w", tags=gfx.tags(),
                             image=Icons.get(icon, color, 20))
        gfx.label(x + 40, y + 22, title, Theme.TXT, Theme.F_HEAD)
        gx, gy = x + (w - self.BOX_W) // 2, y + 36
        self.photo = ImageTk.PhotoImage(Image.new(
            "RGB", (self.BOX_W, self.BOX_H), Theme.C_CARD))
        self.ui.create_image(gx, gy, anchor="nw", image=self.photo,
                             tags=gfx.tags())
        cx = gx + self.BOX_W / 2
        self.value = gfx.label(cx, gy + 46, "--", Theme.TXT,
                               ("Segoe UI Semibold", 21), anchor="center")
        self.sub = gfx.label(cx, gy + 92, "", Theme.DIM, Theme.F_SMALL,
                             anchor="center")
        self.last = None

    def update(self, pct, sub):
        shown = None if pct is None else int(round(pct))
        color = Theme.RED if (shown or 0) >= 90 else self.color
        text = "--" if shown is None else f"{shown}%"
        if self.ui.itemcget(self.value, "text") != text:
            self.ui.itemconfig(self.value, text=text)
        if self.ui.itemcget(self.sub, "text") != sub:
            self.ui.itemconfig(self.sub, text=sub)
        key = (shown, color)
        if key != self.last:
            self.last = key
            self.photo.paste(self._render(shown, color))

    def _render(self, pct, color):
        s = 4
        W, H = self.BOX_W * s, self.BOX_H * s
        im = Image.new("RGB", (W, H), Gfx._rgb(Theme.C_CARD))
        d = ImageDraw.Draw(im)
        cx, cy, r, th = W / 2, H * 0.5, 42 * s, 8 * s
        box = [cx - r, cy - r, cx + r, cy + r]
        d.arc(box, 135, 405, fill=Gfx._rgb(Theme.C_TRACK), width=th)

        def cap(angle, col):
            a = math.radians(angle)
            px, py = cx + (r - th / 2) * math.cos(a), cy + (r - th / 2) * math.sin(a)
            d.ellipse([px - th / 2, py - th / 2, px + th / 2, py + th / 2],
                      fill=col)
        cap(135, Gfx._rgb(Theme.C_TRACK))
        cap(405, Gfx._rgb(Theme.C_TRACK))
        if pct:
            sweep = 270 * min(100, pct) / 100
            c1, c2 = color, Theme.mix(color, "#ffffff", 0.38)
            a = 0.0
            while a < sweep:
                col = Gfx._rgb(Theme.mix(c1, c2, a / 270))
                d.arc(box, 135 + a, 135 + min(sweep, a + 4), fill=col, width=th)
                a += 3
            cap(135, Gfx._rgb(c1))
            cap(135 + sweep, Gfx._rgb(Theme.mix(c1, c2, sweep / 270)))
        return im.resize((self.BOX_W, self.BOX_H), BOX)


class StatCard:
    """One dashboard card: title + status word, a big value, two short lines and
    a small history chart (or a usage bar). Missing data shows "--", never a
    made-up number."""
    STATUS = {"ok": ("Normal", "#3ddc84"), "warm": ("Warm", "#ffd24d"),
              "hot": ("Hot", "#ff5c5c"), "high": ("High load", "#ff5c5c"),
              "low": ("Low space", "#ffd24d"), "full": ("Almost full", "#ff5c5c"),
              "none": ("No data", None)}

    def __init__(self, gfx, x, y, w, h, icon, title, color, bar=False, tip=None):
        self.g, self.ui, self.color, self.bar = gfx, gfx.ui, color, bar
        self.w = w
        self.tag = f"card{id(self)}"
        gfx.card(x, y, w, h)
        self.ui.create_image(x + 14, y + 22, anchor="w", tags=gfx.tags(self.tag),
                             image=Icons.get(icon, color, 20))
        self.ui.create_text(x + 40, y + 22, text=title, fill=Theme.TXT,
                            font=Theme.F_HEAD, anchor="w", tags=gfx.tags(self.tag))
        self.value = gfx.label(x + 14, y + 56, "--", Theme.TXT, Theme.F_BIG)
        self.chip = gfx.label(x + 14, y + 82, "", Theme.DIM, Theme.F_SMALL_B)
        self.sub = gfx.label(x + 14, y + 102, "", Theme.SUB, Theme.F_SMALL)
        self.sub2 = gfx.label(x + 14, y + 120, "", Theme.DIM, Theme.F_SMALL)
        if bar:
            self.blank = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            bx, by, self.bw = x + 14, y + h - 22, w - 28
            self.ui.create_image(bx, by, anchor="nw", tags=gfx.tags(),
                                 image=gfx.rr(self.bw, 8, 4, Theme.C_TRACK))
            self.fill = self.ui.create_image(bx, by, anchor="nw", image=self.blank,
                                             tags=gfx.tags())
            self.spark = None
        else:
            self.spark = Spark(gfx, x + 10, y + h - 44, w - 20, 34, color)
        self.last = None

    def set_loading(self):
        """Before the first sample: say so instead of 'No data'."""
        self.ui.itemconfig(self.chip, text="Loading…", fill=Theme.DIM)

    def update(self, pct, sub, sub2="", status="none", hist=None):
        ui = self.ui
        text = "--" if pct is None else f"{int(round(pct))}%"
        word, col = self.STATUS[status]
        for item, val in ((self.value, text), (self.sub, sub), (self.sub2, sub2)):
            if ui.itemcget(item, "text") != val:
                ui.itemconfig(item, text=val)
        if ui.itemcget(self.chip, "text") != word:
            ui.itemconfig(self.chip, text=word, fill=col or Theme.DIM)
        ui.itemconfig(self.chip, fill=col or Theme.DIM)
        if self.spark is not None:
            self.spark.update(list(hist or [])[-Spark.N:],
                              color=Theme.RED if status in ("hot", "high") else None)
        elif pct is None:
            self.last = None
            ui.itemconfig(self.fill, image=self.blank)
        elif (pct, status) != self.last:
            self.last = (pct, status)
            n = max(8, int(self.bw * min(100, pct) / 100))
            c = {"low": Theme.YELLOW, "full": Theme.RED}.get(status, self.color)
            ui.itemconfig(self.fill, image=self.g.rr(n, 8, 4, c))


class PerfChart:
    """Real-Time Performance card: CPU / RAM / GPU lines + time range tabs."""
    RANGES = (("1 min", 60), ("5 min", 300), ("1 hr", 3600), ("24 hr", 86400))

    def __init__(self, gfx, x, y, w, h, colors, on_range, index=0):
        self.g, self.ui, self.colors = gfx, gfx.ui, colors
        gfx.card(x, y, w, h)
        self.ui.create_image(x + 14, y + 22, anchor="w", tags=gfx.tags(),
                             image=Icons.get("performance", Theme.ACCENT, 20))
        gfx.label(x + 40, y + 22, "Real-Time Performance", Theme.TXT,
                  Theme.F_HEAD)
        Segmented(gfx, x + w - 16 - 212, y + 8, 212, 28,
                  [n for n, _ in self.RANGES], index, on_range)
        for i, (name, col) in enumerate(zip(("CPU", "RAM", "GPU"), colors)):
            lx = x + 56 + i * 62
            self.ui.create_image(lx, y + 46, anchor="w", tags=gfx.tags(),
                                 image=gfx.rr(8, 8, 4, col))
            gfx.label(lx + 12, y + 46, name, Theme.SUB, Theme.F_SMALL)
        self.iw, self.ih = w - 62, h - 68
        self.ix, self.iy = x + 48, y + 58
        for t, txt in ((0, "100"), (0.5, "50"), (1, "0")):
            gfx.label(self.ix - 6, self.iy + 3 + t * (self.ih - 6), txt,
                      Theme.DIM, Theme.F_SMALL, anchor="e")
        self.chart = LiveChart(gfx, self.ix, self.iy, self.iw, self.ih, colors,
                               dot=True, grid=3, width=2)

    def update(self, series, n=None, period=1.0):
        """series: [cpu, ram, gpu] lists (oldest first, None = no data)."""
        n = n or max([len(v) for v in series] + [2])
        self.chart.set(series, n, 100.0, period=period)


class ThemePreview:
    """A tiny picture of the window in a theme (PIL)."""

    @staticmethod
    def render(spec, accent, w, h):
        s = 3
        W, H = w * s, h * s
        rgb = Gfx._rgb
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, W - 1, H - 1], radius=14 * s,
                            fill=rgb(spec["C_BG"]) + (255,))
        side = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(side)
        sd.rounded_rectangle([0, 0, 62 * s, H - 1], radius=14 * s,
                             fill=rgb(spec["C_SIDE"]) + (255,))
        sd.rectangle([40 * s, 0, 62 * s, H], fill=rgb(spec["C_SIDE"]) + (255,))
        im = Image.alpha_composite(im, side)
        d = ImageDraw.Draw(im)
        a = rgb(accent) + (255,)
        # logo dot + sidebar rows (the first one is the selected page)
        d.ellipse([10 * s, 9 * s, 22 * s, 21 * s], fill=a)
        d.rounded_rectangle([6 * s, 30 * s, 56 * s, 42 * s], radius=6 * s,
                            fill=rgb(Theme.mix(spec["C_SIDE"], accent, .22)) + (255,))
        d.rounded_rectangle([10 * s, 34 * s, 30 * s, 38 * s], radius=2 * s, fill=a)
        for k in range(3):
            y = (48 + k * 12) * s
            d.rounded_rectangle([10 * s, y, (34 + k * 4) * s, y + 4 * s],
                                radius=2 * s, fill=rgb(spec["DIM"]) + (255,))
        # content: title, three cards with bars, a button
        d.rounded_rectangle([72 * s, 10 * s, 112 * s, 16 * s], radius=3 * s,
                            fill=rgb(spec["TXT"]) + (255,))
        cw = (w - 72 - 10 - 2 * 6) / 3
        for k in range(3):
            x = (72 + k * (cw + 6)) * s
            d.rounded_rectangle([x, 24 * s, x + cw * s, 66 * s], radius=7 * s,
                                fill=rgb(spec["C_CARD"]) + (255,))
            d.rounded_rectangle([x + 6 * s, 31 * s, x + 26 * s, 35 * s],
                                radius=2 * s, fill=rgb(spec["TXT"]) + (255,))
            d.rounded_rectangle([x + 6 * s, 52 * s, x + (cw - 6) * s, 56 * s],
                                radius=2 * s, fill=rgb(spec["C_TRACK"]) + (255,))
            fill_w = (cw - 12) * (0.35 + 0.25 * k)
            d.rounded_rectangle([x + 6 * s, 52 * s, x + (6 + fill_w) * s, 56 * s],
                                radius=2 * s, fill=a)
        d.rounded_rectangle([72 * s, 74 * s, (w - 10) * s, 88 * s], radius=7 * s,
                            fill=rgb(spec["C_CARD"]) + (255,))
        d.rounded_rectangle([(w - 58) * s, 77 * s, (w - 14) * s, 85 * s],
                            radius=4 * s, fill=a)
        # a thin edge so a light theme is visible on a light card
        d.rounded_rectangle([0, 0, W - 1, H - 1], radius=14 * s,
                            outline=rgb(spec["C_TRACK"]) + (255,), width=s)
        return im.resize((w, h), BOX)


class Segmented:
    """Pill selector: Left | Center | Right."""

    def __init__(self, gfx, x, y, w, h, labels, index, cb):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.cb, self.index = x, y, cb, index
        self.n = len(labels)
        self.sw = w / self.n
        self.pad = 4
        kw, kh = int(self.sw) - 2 * self.pad, h - 2 * self.pad
        self.tag = f"seg{id(self)}"
        self.job = None
        ui, tg, rr = self.ui, gfx.tags, gfx.rr
        ui.create_image(x, y, anchor="nw", image=rr(w, h, h // 2, Theme.C_TRACK),
                        tags=tg(self.tag))
        self.cx = self.knob_x(max(0, index))
        self.knob = ui.create_image(self.cx, y + self.pad, anchor="nw",
                                    image=rr(kw, kh, kh // 2, Theme.ACCENT),
                                    tags=tg(self.tag),
                                    state="normal" if index >= 0 else "hidden")
        self.texts = [ui.create_text(x + self.sw * (i + 0.5), y + h / 2,
                                     text=t, font=Theme.F_SEG, tags=tg(self.tag))
                      for i, t in enumerate(labels)]
        self.colors()
        ui.tag_bind(self.tag, "<Button-1>", self.click)
        gfx.hand(self.tag)

    def knob_x(self, i):
        return self.x + i * self.sw + self.pad

    def colors(self):
        for i, t in enumerate(self.texts):
            self.ui.itemconfig(
                t, fill=Theme.C_ON if i == self.index else Theme.SUB)

    def click(self, e):
        i = min(self.n - 1, max(0, int((e.x - self.x) // self.sw)))
        if i != self.index:
            self._to(i)
            self.cb(i)

    def move(self, x):
        self.cx = x
        self.ui.coords(self.knob, x, self.y + self.pad)

    def select(self, i):
        """Move the pill to entry i (-1 = none) without calling the callback."""
        if i != self.index:
            self._to(i)

    def _to(self, i):
        self.index = i
        self.colors()
        self.ui.itemconfigure(self.knob, state="normal" if i >= 0 else "hidden")
        if i >= 0:
            self.g.animate(self, self.cx, self.knob_x(i), 9, self.move)


class Switch:
    """On/off switch."""

    def __init__(self, gfx, x, y, value, cb):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.value, self.cb = x, y, value, cb
        self.tag = f"sw{id(self)}"
        self.job = None
        self.track = self.ui.create_image(x, y, anchor="nw",
                                          tags=gfx.tags(self.tag),
                                          image=self.track_img())
        self.cx = x + (23 if value else 3)
        self.knob = self.ui.create_image(
            self.cx, y + 3, anchor="nw", tags=gfx.tags(self.tag),
            image=gfx.rr(20, 20, 10, "#ffffff"))
        self.ui.tag_bind(self.tag, "<Button-1>",
                         lambda e: self.set(not self.value, True))
        gfx.hand(self.tag)

    def track_img(self):
        return self.g.rr(46, 26, 13,
                         Theme.ACCENT if self.value else Theme.C_TRACK)

    def set(self, value, notify=False):
        if value == self.value:
            return
        self.value = value
        self.ui.itemconfig(self.track, image=self.track_img())
        self.g.animate(self, self.cx, self.x + (23 if value else 3), 8,
                       self.move)
        if notify:
            self.cb(value)

    def move(self, x):
        self.cx = x
        self.ui.coords(self.knob, x, self.y + 3)


class Slider:
    """Horizontal slider; `live` runs while dragging, `release` when let go."""

    def __init__(self, gfx, x1, x2, y, vmin, vmax, step, value, live, release):
        self.g, self.ui = gfx, gfx.ui
        self.x1, self.w, self.y = x1, x2 - x1, y
        self.vmin, self.vmax, self.step = vmin, vmax, step
        self.value, self.live = value, live
        self.tag = f"sl{id(self)}"
        ui, tg, rr = self.ui, gfx.tags, gfx.rr
        ui.create_rectangle(x1 - 14, y - 16, x2 + 14, y + 16, fill=Theme.C_CARD,
                            outline="", tags=tg(self.tag))
        ui.create_image(x1, y - 3, anchor="nw",
                        image=rr(self.w, 6, 3, Theme.C_TRACK), tags=tg(self.tag))
        self.fill = ui.create_image(x1, y - 3, anchor="nw", tags=tg(self.tag),
                                    image=self.fill_img(value))
        self.knob = ui.create_image(self.px(value) - 11, y - 11, anchor="nw",
                                    image=rr(22, 22, 11, "#ffffff"),
                                    tags=tg(self.tag))
        ui.tag_bind(self.tag, "<Button-1>", self.drag)
        ui.tag_bind(self.tag, "<B1-Motion>", self.drag)
        ui.tag_bind(self.tag, "<ButtonRelease-1>", lambda e: release())
        gfx.hand(self.tag)

    def px(self, v):
        return self.x1 + self.w * (v - self.vmin) / (self.vmax - self.vmin)

    def fill_img(self, v):
        return self.g.rr(max(6, int(self.px(v) - self.x1)), 6, 3, Theme.ACCENT)

    def drag(self, e):
        frac = min(1.0, max(0.0, (e.x - self.x1) / self.w))
        v = self.vmin + round(frac * (self.vmax - self.vmin) / self.step) * self.step
        v = max(self.vmin, min(self.vmax, v))
        if v != self.value:
            self.value = v
            self.ui.itemconfig(self.fill, image=self.fill_img(v))
            self.ui.coords(self.knob, self.px(v) - 11, self.y - 11)
            self.live(v)


class Chip:
    """Small on/off button for one metric."""
    W, H = 108, 28

    def __init__(self, gfx, settings, x, y, text, key, on_click):
        self.g, self.ui, self.settings, self.key = gfx, gfx.ui, settings, key
        self.tag = f"chip_{key}"
        self.img = self.ui.create_image(x, y, anchor="nw",
                                        tags=gfx.tags(self.tag))
        self.txt = self.ui.create_text(x + self.W / 2, y + self.H / 2,
                                       text=text, font=Theme.F_LABEL,
                                       tags=gfx.tags(self.tag))
        self.refresh()
        self.ui.tag_bind(self.tag, "<Button-1>", lambda e: on_click(key))
        gfx.hand(self.tag)

    def refresh(self):
        on = self.settings.show[self.key]
        self.ui.itemconfig(self.img, image=self.g.rr(
            self.W, self.H, self.H // 2,
            Theme.ACCENT if on else Theme.C_TRACK))
        self.ui.itemconfig(self.txt, fill=Theme.C_ON if on else Theme.SUB)


class Bar:
    """Thin progress bar that glides to its new value."""

    def __init__(self, gfx, x, y, w, h=6):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.w, self.h = x, y, w, h
        self.cur = 0.0
        self.color = Theme.ACCENT
        self.job = None
        self.ui.create_image(x, y, anchor="nw", tags=gfx.tags(),
                             image=gfx.rr(w, h, h // 2, Theme.C_TRACK))
        self.fill = self.ui.create_image(x, y, anchor="nw", tags=gfx.tags())
        self._draw(0.0)

    def _draw(self, frac):
        self.cur = frac
        # even widths keep the image cache small; never touch "state" so a
        # bar on a hidden page cannot show up on another page
        px = max(self.h, int(self.w * frac) // 4 * 4)
        self.ui.itemconfig(self.fill, image=self.g.rr(
            px, self.h, self.h // 2, self.color))

    def set(self, frac, color=None):
        frac = min(1.0, max(0.0, frac or 0.0))
        color = color or Theme.ACCENT
        if abs(frac - self.cur) < 0.004 and color == self.color:
            return
        self.color = color
        self.g.animate(self, self.cur, frac, 10, self._draw)


class LineChart:
    """Live line chart in a card. One PIL image per chart, updated in place."""

    def __init__(self, gfx, x, y, w, h, title, vmax=100.0, series=1,
                 colors=None, fmt=None, value_font=None):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.w, self.h = x, y, w, h
        self.vmax, self.fmt = vmax, fmt or (lambda v: f"{v:.0f}")
        self.colors = colors or [Theme.ACCENT, "#7aa2ff"]
        self.iw, self.ih = w - 24, h - 52
        gfx.card(x, y, w, h)
        gfx.label(x + 14, y + 20, title, Theme.SUB, Theme.F_LABEL)
        self.value = gfx.label(x + w - 14, y + 20, "n/a", Theme.TXT,
                               value_font or Theme.F_HEAD, anchor="e")
        self.photo = ImageTk.PhotoImage(Image.new(
            "RGB", (self.iw, self.ih), Theme.C_CARD))
        self.item = self.ui.create_image(x + 12, y + 38, anchor="nw",
                                         image=self.photo, tags=gfx.tags())
        self.last = None

    def _scale(self, series):
        if self.vmax:
            return self.vmax
        top = max((v for s in series for v in s if v is not None), default=0)
        step = 1024 * 64  # auto scale in 64 KB/s steps, at least 256 KB/s
        return max(256 * 1024, (int(top / step) + 1) * step)

    def update(self, series, text):
        """series: list of lists (oldest first, None = no data)."""
        key = (tuple(tuple(s) for s in series), text)
        if key == self.last:
            return
        self.last = key
        if self.ui.itemcget(self.value, "text") != text:
            self.ui.itemconfig(self.value, text=text)
        self.photo.paste(self._render(series))

    def _render(self, series):
        s = 2
        W, H = self.iw * s, self.ih * s
        base = Image.new("RGBA", (W, H), Theme.C_CARD)
        d = ImageDraw.Draw(base)
        grid = Theme.lift(Theme.C_CARD, 0.08)
        for i in range(4):
            y = int((H - s) * i / 3)
            d.line([(0, y), (W, y)], fill=grid, width=s)
        top = self._scale(series)
        n = Telemetry.HISTORY
        step = W / (n - 1)
        for idx, vals in enumerate(series):
            color = Gfx._rgb(self.colors[idx % len(self.colors)])
            seg = []
            segments = []
            for i, v in enumerate(vals):
                px = W - (len(vals) - 1 - i) * step
                if v is None:
                    if seg:
                        segments.append(seg)
                    seg = []
                    continue
                seg.append((px, H - 2 - min(v, top) / top * (H - 6 * s)))
            if seg:
                segments.append(seg)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            for sg in segments:
                if len(sg) >= 2:
                    ld.polygon(sg + [(sg[-1][0], H), (sg[0][0], H)],
                               fill=color + (46,))
                    ld.line(sg, fill=color + (255,), width=2 * s, joint="curve")
                px, py = sg[-1]
                ld.ellipse([px - 3 * s, py - 3 * s, px + 3 * s, py + 3 * s],
                           fill=color + (255,))
            base = Image.alpha_composite(base, layer)
        return base.convert("RGB").resize((self.iw, self.ih), BOX)


class InfoTable:
    """A list of "label ... value" rows (and section headers / usage bars).

    Rows are a fixed pool of canvas items that are re-used: nothing is
    created or destroyed while the numbers change, and unchanged rows are
    not touched. (The pool never uses item "state", so page switching keeps
    working.)
    """

    def __init__(self, gfx, x, y, w, rows=20, row_h=22, tag=""):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.w, self.row_h, self.cap = x, y, w, row_h, rows
        self.uid = f"it{id(self)}"
        tg = gfx.tags(tag, self.uid)
        self.all, self.off = [], 0
        self.blank = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
        ui = self.ui
        ui.create_rectangle(x - 6, y, x + w + 6, y + rows * row_h, fill=Theme.C_CARD,
                            outline="", tags=tg)               # click / wheel area
        ui.tag_bind(self.uid, "<Button-1>", lambda e: self.page())
        try:
            ui.bind("<MouseWheel>", self._wheel, add="+")
        except Exception:
            pass
        self.pool = []
        for i in range(rows):
            ry = y + i * row_h + row_h / 2
            lab = ui.create_text(x, ry, anchor="w", text="", font=Theme.F_SMALL,
                                 fill=Theme.DIM, tags=tg)
            val = ui.create_text(x + w, ry, anchor="e", text="",
                                 font=Theme.F_SMALL_B, fill=Theme.TXT, tags=tg)
            track = ui.create_image(x, ry + 9, anchor="nw", image=self.blank,
                                    tags=tg)
            fill = ui.create_image(x, ry + 9, anchor="nw", image=self.blank,
                                   tags=tg)
            self.pool.append((lab, val, track, fill))
        self.cache = [None] * rows
        self.track_img = gfx.rr(w, 4, 2, Theme.C_TRACK)

    def _wheel(self, e):
        try:
            if self.ui.itemcget(self.pool[0][0], "state") == "hidden":
                return
        except Exception:
            pass
        if self.x - 6 <= e.x <= self.x + self.w + 6 and \
                self.y <= e.y <= self.y + self.cap * self.row_h:
            self.scroll(-3 if e.delta > 0 else 3)

    def scroll(self, d):
        room = max(0, len(self.all) - (self.cap - 1))
        off = max(0, min(self.off + d, room))
        if off != self.off:
            self.off = off
            self.set(self.all, keep=True)

    def page(self):
        """Click: the next page of rows, back to the top after the last."""
        if len(self.all) <= self.cap:
            return
        room = len(self.all) - (self.cap - 1)
        self.off = 0 if self.off >= room else min(room, self.off + self.cap - 1)
        self.set(self.all, keep=True)

    def set(self, rows, keep=False):
        ui, g = self.ui, self.g
        self.all = rows
        if not keep and len(rows) <= self.cap:
            self.off = 0
        if len(rows) > self.cap:
            n = self.cap - 1
            self.off = max(0, min(self.off, len(rows) - n))
            left = len(rows) - self.off - n
            rows = rows[self.off:self.off + n] + [(
                "row", "▼ " + (f"{left} more - click or scroll" if left else "click for the top"), "")]
        for i in range(self.cap):
            row = rows[i] if i < len(rows) else None
            if self.cache[i] == row:
                continue
            self.cache[i] = row
            lab, val, track, fill = self.pool[i]
            if row is None:
                ui.itemconfig(lab, text="")
                ui.itemconfig(val, text="")
                ui.itemconfig(track, image=self.blank)
                ui.itemconfig(fill, image=self.blank)
                continue
            kind = row[0]
            if kind == "head":
                ui.itemconfig(lab, text=row[1].upper(), fill=Theme.ACCENT,
                              font=Theme.F_LABEL)
                ui.itemconfig(val, text="")
                ui.itemconfig(track, image=self.blank)
                ui.itemconfig(fill, image=self.blank)
                continue
            ui.itemconfig(lab, text=row[1], fill=Theme.DIM, font=Theme.F_SMALL)
            ui.itemconfig(val, text=row[2],
                          fill=Theme.ui_color(row[3]) if len(row) > 3
                          and kind == "row" and row[3] else Theme.TXT)
            if kind == "bar":
                frac = min(1.0, max(0.0, row[3]))
                px = max(8, int(self.w * frac) // 8 * 8)  # few distinct images
                color = (Theme.ACCENT if Thresholds.use(frac * 100) == Theme.WHITE
                         else Thresholds.use(frac * 100))
                ui.itemconfig(track, image=self.track_img)
                ui.itemconfig(fill, image=g.rr(px, 4, 2, color))
            else:
                ui.itemconfig(track, image=self.blank)
                ui.itemconfig(fill, image=self.blank)


class NavMenu:
    """Left navigation in five groups. The group you are in is open and shows
    its pages; the others show one line each. Page numbers never change.

    groups = [(title, icon, [(page index, text), ...])]"""
    W, H, GAP = 168, 26, 0
    MAX_KIDS = 8

    def __init__(self, gfx, x, y, groups, index, cb):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.cb, self.index = x, y, cb, index
        self.groups = groups
        self.group_of = {pg: gi for gi, (_, _, pgs) in enumerate(groups) for pg, _ in pgs}
        self.open = self.group_of[index]
        self.job = None
        self.hov = None
        ui, rr = self.ui, gfx.rr
        self.pill = ui.create_image(
            x, y, anchor="nw", tags=("side",),
            image=rr(self.W, self.H, 12, Theme.mix(Theme.C_SIDE, Theme.ACCENT, .16)))
        self.bar = ui.create_image(x, y + 8, anchor="nw", tags=("side",),
                                   image=rr(4, self.H - 16, 2, Theme.ACCENT))
        self.h_icon, self.h_text, self.h_chev = [], [], []
        for gi in range(len(groups)):
            self.h_icon.append(ui.create_image(x + 20, y, tags=("side",), anchor="w"))
            self.h_text.append(ui.create_text(x + 52, y, anchor="w", font=Theme.F_NAV,
                                              text=groups[gi][0], tags=("side",)))
            self.h_chev.append(ui.create_text(x + self.W - 14, y, anchor="e",
                                              font=Theme.F_SMALL_B, text="",
                                              tags=("side",)))
        self.k_text = [ui.create_text(x + 52, y, anchor="w", font=Theme.F_SMALL_B,
                                      text="", tags=("side",))
                       for _ in range(self.MAX_KIDS)]
        ui.tag_bind("side", "<Button-1>", self.on_click)
        ui.tag_bind("side", "<Motion>", self.on_motion)
        ui.tag_bind("side", "<Leave>", lambda e: self.hover_to(None))
        self.cy = self.layout()
        ui.coords(self.pill, x, self.cy)
        ui.coords(self.bar, x, self.cy + 8)
        self.colors()

    # ---- layout: rows = [(kind, page-or-group, y)]
    def layout(self):
        ui, x, H = self.ui, self.x, self.H
        self.rows, y, sel_y = [], self.y, self.y
        for k in self.k_text:
            ui.itemconfig(k, text="")
        for gi, (title, icon, pgs) in enumerate(self.groups):
            multi = len(pgs) > 1
            self.rows.append(("g", gi, y))
            cy = y + H / 2
            ui.coords(self.h_icon[gi], x + 20, cy)
            ui.coords(self.h_text[gi], x + 52, cy)
            ui.coords(self.h_chev[gi], x + self.W - 14, cy)
            ui.itemconfig(self.h_chev[gi], text=("⌄" if gi == self.open else "›") if multi else "")
            if not multi and pgs[0][0] == self.index:
                sel_y = y
            y += H
            if gi == self.open and multi:
                for n, (pg, text) in enumerate(pgs):
                    self.rows.append(("p", pg, y))
                    ui.coords(self.k_text[n], x + 52, y + H / 2)
                    ui.itemconfig(self.k_text[n], text=text)
                    if pg == self.index:
                        sel_y = y
                    y += H
        self.bottom = y
        return sel_y

    def row_at(self, e):
        if not (self.x <= e.x <= self.x + self.W):
            return None
        for kind, ref, ry in self.rows:
            if ry <= e.y < ry + self.H:
                return kind, ref
        return None

    def index_at(self, e):
        """Page under the mouse (a group line -> the group's first page)."""
        r = self.row_at(e)
        if r is None:
            return None
        return r[1] if r[0] == "p" else self.groups[r[1]][2][0][0]

    def on_click(self, e):
        r = self.row_at(e)
        if r is None:
            return
        if r[0] == "g" and r[1] == self.open and len(self.groups[r[1]][2]) > 1:
            return                                   # already open
        self.click(self.index_at(e))

    def on_motion(self, e):
        self.hover_to(self.row_at(e))

    def hover_to(self, r):
        if r == self.hov:
            return
        self.hov = r
        self.colors()
        self.ui.config(cursor="" if r is None else "hand2")

    def colors(self):
        ui, T = self.ui, Theme
        for gi, (title, icon, pgs) in enumerate(self.groups):
            here = gi == self.open
            hot = self.hov == ("g", gi)
            single_on = len(pgs) == 1 and pgs[0][0] == self.index
            ui.itemconfig(self.h_text[gi], fill=T.TXT if (here or hot) else T.SUB)
            ui.itemconfig(self.h_chev[gi], fill=T.DIM)
            ui.itemconfig(self.h_icon[gi], image=Icons.get(
                icon, T.ACCENT if (here or single_on) else T.SUB))
        for n, (pg, text) in enumerate(self.groups[self.open][2][:self.MAX_KIDS]):
            on = pg == self.index
            ui.itemconfig(self.k_text[n], fill=T.TXT if on else (
                T.TXT if self.hov == ("p", pg) else T.SUB))

    def click(self, i):
        if i != self.index:
            self.select(i, True)

    def select(self, i, notify=False):
        self.index = i
        self.open = self.group_of[i]
        target = self.layout()
        self.colors()
        self.g.animate(self, self.cy, target, 9, self.move)
        if notify:
            self.cb(i)

    def move(self, y):
        self.cy = y
        self.ui.coords(self.pill, self.x, y)
        self.ui.coords(self.bar, self.x, y + 8)


class ReorderList:
    """Rows that can be dragged up and down; on_change(keys) runs on drop."""
    ROW, ROW_HI = None, None   # colors are taken from Theme when drawn

    def __init__(self, gfx, x, y, w, rows, on_change, row_h=38, gap=6,
                 is_visible=lambda: True):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.w, self.h = x, y, w, row_h
        self.step = row_h + gap
        self.on_change, self.is_visible = on_change, is_visible
        self.page_tag = gfx.tab
        self.tag = f"rl{id(self)}"
        self.gen = 0
        self.rows, self.ids, self.d = [], [], None
        self.set_rows(rows)

    def slot_y(self, i):
        return self.y + i * self.step

    def _color(self, hi=False):
        return Theme.lift(Theme.C_CARD, 0.14 if hi else 0.06)

    def set_rows(self, rows):
        """rows = [(key, text, visible_on_overlay)]; redraws the list."""
        g, ui = self.g, self.ui
        ui.delete(self.tag)
        self.gen += 1
        old_tab, g.tab = g.tab, self.page_tag
        self.rows, self.ids = list(rows), []
        for i, (key, text, on) in enumerate(self.rows):
            t = f"{self.tag}g{self.gen}r{i}"
            tg = g.tags(self.tag, t)
            y, mid = self.slot_y(i), self.slot_y(i) + self.h / 2
            bg = ui.create_image(self.x, y, anchor="nw", tags=tg,
                                 image=g.rr(self.w, self.h, 12, self._color()))
            grip = ui.create_image(self.x + 18, mid, tags=tg,
                                   image=Icons.get("grip", Theme.DIM, 16))
            txt = ui.create_text(self.x + 38, mid, text=text, anchor="w",
                                 tags=tg, font=Theme.F_LABEL,
                                 fill=Theme.TXT if on else Theme.DIM)
            dot = ui.create_image(self.x + self.w - 18, mid, tags=tg,
                                  image=g.rr(8, 8, 4,
                                             Theme.ACCENT if on else Theme.C_TRACK))
            self.ids.append((bg, grip, txt, dot))
            ui.tag_bind(t, "<Button-1>", lambda e, i=i: self.press(i, e))
            ui.tag_bind(t, "<B1-Motion>", self.move)
            ui.tag_bind(t, "<ButtonRelease-1>", self.release)
            g.hand(t)
        g.tab = old_tab
        if not self.is_visible():  # created on a page that is not shown
            ui.itemconfigure(self.tag, state="hidden")

    def put(self, i, y):
        bg, grip, txt, dot = self.ids[i]
        mid = y + self.h / 2
        ui = self.ui
        ui.coords(bg, self.x, y)
        ui.coords(grip, self.x + 18, mid)
        ui.coords(txt, self.x + 38, mid)
        ui.coords(dot, self.x + self.w - 18, mid)

    def press(self, i, e):
        self.d = {"i": i, "grab": e.y - self.slot_y(i), "slot": i}
        self.ui.itemconfig(self.ids[i][0], image=self.g.rr(
            self.w, self.h, 12, self._color(True)))
        for item in self.ids[i]:
            self.ui.tag_raise(item)

    def move(self, e):
        d = self.d
        if not d:
            return
        n = len(self.rows)
        top = min(max(e.y - d["grab"], self.y), self.slot_y(n - 1))
        self.put(d["i"], top)
        slot = min(n - 1, max(0, int(round((top - self.y) / self.step))))
        if slot != d["slot"]:
            d["slot"] = slot
            rest = [r for r in range(n) if r != d["i"]]
            rest.insert(slot, d["i"])
            for p, r in enumerate(rest):
                if r != d["i"]:
                    self.put(r, self.slot_y(p))

    def release(self, e):
        d, self.d = self.d, None
        if not d:
            return
        i, slot = d["i"], d["slot"]
        if slot == i:
            self.put(i, self.slot_y(i))
            self.ui.itemconfig(self.ids[i][0], image=self.g.rr(
                self.w, self.h, 12, self._color()))
            return
        rows = list(self.rows)
        rows.insert(slot, rows.pop(i))
        self.set_rows(rows)
        self.on_change([r[0] for r in rows])


# =============================================================== SettingsWindow
class SessionList:
    """The newest game sessions as clickable rows. Click up to two to look at
    one or compare two (A, B). The rows are a fixed pool of canvas items."""
    ROWS, ROW_H, H = 4, 30, 212

    def __init__(self, gfx, x, y, w, on_pick, on_delete):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.w = x, y, w
        self.on_pick, self.on_delete = on_pick, on_delete
        self.sessions, self.sel, self.top = [], [], 0
        self.confirm = None
        ui, tg = self.ui, gfx.tags
        self.blank = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
        ui.create_text(x + 20, y + 24, text="RECENT SESSIONS", anchor="w",
                       fill=Theme.ACCENT, font=Theme.F_LABEL, tags=tg())
        self.count = ui.create_text(x + 176, y + 24, text="", anchor="w",
                                    fill=Theme.DIM, font=Theme.F_SMALL, tags=tg())
        for tag, text, dx in (("sl_dn", "▼", 20 + 28), ("sl_up", "▲", 20 + 28 + 32)):
            bx = x + w - dx
            ui.create_image(bx, y + 12, anchor="nw", tags=tg(tag),
                            image=gfx.rr(28, 24, 8, Theme.C_TRACK))
            ui.create_text(bx + 14, y + 24, text=text, fill=Theme.SUB,
                           font=Theme.F_SMALL_B, tags=tg(tag))
        ui.tag_bind("sl_dn", "<Button-1>", lambda e: self.scroll(1))
        ui.tag_bind("sl_up", "<Button-1>", lambda e: self.scroll(-1))
        gfx.hand("sl_dn")
        gfx.hand("sl_up")
        self.empty = ui.create_text(
            x + w / 2, y + 100, text="", fill=Theme.DIM, font=Theme.F_SMALL,
            width=w - 80, justify="center", tags=tg())
        self.pool = []
        for i in range(self.ROWS):
            ry = y + 46 + i * self.ROW_H
            t = tg(f"sl_r{i}")
            ui.create_rectangle(x + 10, ry, x + w - 10, ry + self.ROW_H - 2,
                                fill=Theme.C_CARD, outline="", tags=t)  # click area
            bg = ui.create_image(x + 10, ry, anchor="nw", image=self.blank, tags=t)
            badge = ui.create_text(x + 28, ry + 14, text="", anchor="w",
                                   fill=Theme.C_ON, font=Theme.F_LABEL, tags=t)
            name = ui.create_text(x + 54, ry + 14, text="", anchor="w",
                                  fill=Theme.TXT, font=Theme.F_LABEL, tags=t)
            meta = ui.create_text(x + w - 26, ry + 14, text="", anchor="e",
                                  fill=Theme.DIM, font=Theme.F_SMALL, tags=t)
            self.pool.append((bg, badge, name, meta))
            ui.tag_bind(f"sl_r{i}", "<Button-1>", lambda e, i=i: self.click(i))
            gfx.hand(f"sl_r{i}")
        # footer: hint + delete
        fy = y + self.H - 40
        ui.create_text(x + 20, fy + 14, text="Click one to view it, two to compare (A / B).",
                       anchor="w", fill=Theme.DIM, font=Theme.F_SMALL, tags=tg())
        self.del_bg = ui.create_image(x + w - 20 - 140, fy, anchor="nw",
                                      image=gfx.rr(140, 28, 14, Theme.C_TRACK),
                                      tags=tg("sl_del"))
        self.btn_del = ui.create_text(x + w - 20 - 70, fy + 14, text="Delete selected",
                                      fill=Theme.DIM, font=Theme.F_SMALL_B,
                                      tags=tg("sl_del"))
        ui.tag_bind("sl_del", "<Button-1>", lambda e: self.delete())
        gfx.hand("sl_del")

    # ---- data
    def set_sessions(self, sessions, select_newest=False):
        self.sessions = sessions
        ids = {s["id"] for s in sessions}
        self.sel = [i for i in self.sel if i in ids]
        if select_newest and not self.sel and sessions:
            self.sel = [sessions[0]["id"]]
        self.top = max(0, min(self.top, len(sessions) - self.ROWS))
        self.draw()
        self.on_pick(self.picked())

    def picked(self):
        by = {s["id"]: s for s in self.sessions}
        return [by[i] for i in self.sel if i in by]

    # ---- actions
    def click(self, i):
        idx = self.top + i
        if idx >= len(self.sessions):
            return
        sid = self.sessions[idx]["id"]
        if sid in self.sel:
            self.sel.remove(sid)
        else:
            self.sel.append(sid)
            if len(self.sel) > 2:
                self.sel.pop(0)
        self.draw()
        self.on_pick(self.picked())

    def scroll(self, d):
        top = max(0, min(self.top + d, len(self.sessions) - self.ROWS))
        if top != self.top:
            self.top = top
            self.draw()

    def delete(self):
        if not self.sel:
            return
        if self.confirm is None:    # first click only asks
            self.ui.itemconfig(self.btn_del, text="Sure? Click again",
                               fill=Theme.RED)
            self.confirm = self.ui.after(3000, self._unconfirm)
            return
        self._unconfirm()
        self.on_delete(list(self.sel))

    def _unconfirm(self):
        if self.confirm is not None:
            try:
                self.ui.after_cancel(self.confirm)
            except Exception:
                pass
        self.confirm = None
        self.ui.itemconfig(self.btn_del, text="Delete selected",
                           fill=Theme.TXT if self.sel else Theme.DIM)

    # ---- drawing
    def draw(self):
        ui, g = self.ui, self.g
        n = len(self.sessions)
        ui.itemconfig(self.count, text=f"{n} saved" if n else "")
        ui.itemconfig(self.empty, text="" if n else
                      "No sessions yet. Start a game - Lmonitor records it "
                      "automatically\n(needs PresentMon; sessions under 1 minute "
                      "are not saved).")
        hl = Theme.mix(Theme.C_CARD, Theme.ACCENT, .28)
        if self.confirm is None:
            ui.itemconfig(self.btn_del, fill=Theme.TXT if self.sel else Theme.DIM)
        for i, (bg, badge, name, meta) in enumerate(self.pool):
            idx = self.top + i
            if idx >= n:
                ui.itemconfig(bg, image=self.blank)
                for it in (badge, name, meta):
                    ui.itemconfig(it, text="")
                continue
            s = self.sessions[idx]
            title, info = SessionView.title(s)
            on = s["id"] in self.sel
            ui.itemconfig(bg, image=g.rr(self.w - 20, self.ROW_H - 2, 9, hl)
                          if on else self.blank)
            ui.itemconfig(badge, text=("A", "B")[self.sel.index(s["id"])]
                          if on else "")
            ui.itemconfig(name, text=title[:26])
            ui.itemconfig(meta, text=info)


class IssueList:
    """The problems found by a scan: one clickable row each (worst first)."""
    ROWS, ROW_H = 7, 19
    COLORS = {"warn": "RED", "notice": "YELLOW", "unknown": "DIM", "info": "SUB",
              "ok": "C_OK"}

    def __init__(self, gfx, x, y, w, on_pick):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.w, self.on_pick = x, y, w, on_pick
        self.issues, self.sel, self.top = [], None, 0
        ui, tg = self.ui, gfx.tags
        self.blank = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
        ui.create_text(x + 18, y + 20, text="WHAT WAS FOUND", anchor="w",
                       fill=Theme.ACCENT, font=Theme.F_LABEL, tags=tg())
        self.count = ui.create_text(x + 170, y + 20, text="", anchor="w",
                                    fill=Theme.DIM, font=Theme.F_SMALL, tags=tg())
        for tag, text, dx, d in (("is_dn", "▼", 18, 1), ("is_up", "▲", 36, -1)):
            ui.create_text(x + w - dx, y + 20, text=text, anchor="e", fill=Theme.SUB,
                           font=Theme.F_SMALL_B, tags=tg(tag))
            ui.tag_bind(tag, "<Button-1>", lambda e, d=d: self.scroll(d))
            gfx.hand(tag)
        self.empty = ui.create_text(
            x + w / 2, y + 90, text="", fill=Theme.DIM, font=Theme.F_SMALL,
            width=w - 60, justify="center", tags=tg())
        self.pool = []
        for i in range(self.ROWS):
            ry = y + 38 + i * self.ROW_H
            t = tg(f"is_r{i}")
            ui.create_rectangle(x + 10, ry, x + w - 10, ry + self.ROW_H - 2,
                                fill=Theme.C_CARD, outline="", tags=t)  # click area
            bg = ui.create_image(x + 10, ry, anchor="nw", image=self.blank, tags=t)
            dot = ui.create_image(x + 24, ry + 10, image=self.blank, tags=t)
            name = ui.create_text(x + 38, ry + 10, text="", anchor="w",
                                  fill=Theme.TXT, font=Theme.F_SMALL_B, tags=t)
            area = ui.create_text(x + w - 100, ry + 10, text="", anchor="e",
                                  fill=Theme.DIM, font=Theme.F_SMALL, tags=t)
            sev = ui.create_text(x + w - 22, ry + 10, text="", anchor="e",
                                 fill=Theme.DIM, font=Theme.F_SMALL_B, tags=t)
            self.pool.append((bg, dot, name, area, sev))
            ui.tag_bind(f"is_r{i}", "<Button-1>", lambda e, i=i: self.click(i))
            gfx.hand(f"is_r{i}")

    def set_issues(self, issues, empty_text=""):
        keep = self.selected()
        self.issues = issues
        ids = [i["id"] for i in issues]
        self.sel = keep["id"] if keep and keep["id"] in ids else (ids[0] if ids else None)
        self.top = max(0, min(self.top, len(issues) - self.ROWS))
        self.empty_text = empty_text
        self.draw()
        self.on_pick(self.selected())

    def selected(self):
        for i in self.issues:
            if i["id"] == self.sel:
                return i
        return None

    def click(self, i):
        idx = self.top + i
        if idx < len(self.issues):
            self.sel = self.issues[idx]["id"]
            self.draw()
            self.on_pick(self.selected())

    def scroll(self, d):
        top = max(0, min(self.top + d, len(self.issues) - self.ROWS))
        if top != self.top:
            self.top = top
            self.draw()

    def draw(self):
        ui, g = self.ui, self.g
        n = len(self.issues)
        ui.itemconfig(self.count, text=f"{n} checked" if n else "")
        ui.itemconfig(self.empty, text="" if n else getattr(self, "empty_text", ""))
        hl = Theme.mix(Theme.C_CARD, Theme.ACCENT, .28)
        for i, (bg, dot, name, area, sev) in enumerate(self.pool):
            idx = self.top + i
            if idx >= n:
                ui.itemconfig(bg, image=self.blank)
                ui.itemconfig(dot, image=self.blank)
                for it in (name, area, sev):
                    ui.itemconfig(it, text="")
                continue
            s = self.issues[idx]
            col = getattr(Theme, self.COLORS[s["sev"]])
            ui.itemconfig(bg, image=g.rr(self.w - 20, self.ROW_H - 2, 7, hl)
                          if s["id"] == self.sel else self.blank)
            ui.itemconfig(dot, image=g.rr(8, 8, 4, col))
            ui.itemconfig(name, text=s["title"][:44])
            ui.itemconfig(area, text=s["area"])
            ui.itemconfig(sev, text=DiagAnalyzer.SEV_WORD[s["sev"]], fill=col)


class ActionList:
    """A clean list of things you can change.

    Columns that never run into each other:
        [checkbox] [ title / small text ......... ] [ state ] [ button ]
    A text is cut with "…" only when it really does not fit (measured in
    pixels). Clicking a row (not its button) shows the full text in the detail
    card. A row can be a group heading ("header") or have a checkbox ("check").
    A thin scrollbar shows where you are; the mouse wheel scrolls too."""
    ROWS, ROW_H = 6, 44
    TOP = 52                       # where the first row starts (note above it)
    BTN_W, BTN_H = 104, 28
    CHK = 20

    def __init__(self, gfx, x, y, w, on_action, on_preview=None,
                 on_info=None, on_toggle=None):
        self.g, self.ui = gfx, gfx.ui
        self.x, self.y, self.w = x, y, w
        self.on_action, self.on_preview = on_action, on_preview
        self.on_info, self.on_toggle = on_info, on_toggle
        self.rows, self.top = [], 0
        self.pending, self.pending_job = None, None
        self.f_title = tkfont.Font(font=Theme.F_HEAD)
        self.f_sub = tkfont.Font(font=Theme.F_SMALL)
        self.f_state = tkfont.Font(font=Theme.F_SMALL_B)
        ui, tg = self.ui, gfx.tags
        self.uid = f"al{id(self)}"          # tags must be unique per list
        self.blank = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
        self.note = ui.create_text(x + 20, y + 16, text="", anchor="nw",
                                   fill=Theme.SUB, font=Theme.F_SMALL,
                                   width=w - 44, tags=tg())
        self.empty = ui.create_text(x + w / 2, y + 170, text="", fill=Theme.DIM,
                                    font=Theme.F_SMALL, width=w - 90,
                                    justify="center", tags=tg())
        line_col = Theme.mix(Theme.C_CARD, Theme.C_BG, .55)
        self.pool = []
        for i in range(self.ROWS):
            ry = y + self.TOP + i * self.ROW_H
            hit = ui.create_rectangle(x + 10, ry + 1, x + w - 26, ry + self.ROW_H - 1,
                                      fill=Theme.C_CARD, outline="",
                                      tags=tg(f"{self.uid}_r{i}"))
            line = ui.create_line(x + 20, ry, x + w - 20, ry, fill=line_col,
                                  tags=tg())
            ct = tg(f"{self.uid}_c{i}")
            cimg = ui.create_image(x + 20, ry + self.ROW_H / 2, anchor="w",
                                   image=self.blank, tags=ct)
            ctxt = ui.create_text(x + 20 + self.CHK / 2, ry + self.ROW_H / 2,
                                  text="", fill=Theme.C_ON, font=Theme.F_SMALL_B,
                                  tags=ct)
            title = ui.create_text(x + 20, ry + 14, text="", anchor="w",
                                   fill=Theme.TXT, font=Theme.F_HEAD, tags=tg(f"{self.uid}_r{i}"))
            sub = ui.create_text(x + 20, ry + 32, text="", anchor="w",
                                 fill=Theme.DIM, font=Theme.F_SMALL, tags=tg(f"{self.uid}_r{i}"))
            state = ui.create_text(x + w - 140, ry + 22, text="", anchor="e",
                                   fill=Theme.DIM, font=Theme.F_SMALL_B, tags=tg(f"{self.uid}_r{i}"))
            t = tg(f"{self.uid}_b{i}")
            img = ui.create_image(x + w - 24 - self.BTN_W, ry + 8, anchor="nw",
                                  image=self.blank, tags=t)
            txt = ui.create_text(x + w - 24 - self.BTN_W / 2, ry + 22, text="",
                                 fill=Theme.SUB, font=Theme.F_LABEL, tags=t)
            self.pool.append((line, title, sub, state, img, txt, cimg, ctxt, hit))
            ui.tag_bind(f"{self.uid}_b{i}", "<Button-1>", lambda e, i=i: self.click(i))
            ui.tag_bind(f"{self.uid}_r{i}", "<Button-1>", lambda e, i=i: self.row_click(i))
            ui.tag_bind(f"{self.uid}_c{i}", "<Button-1>", lambda e, i=i: self.row_click(i))
            gfx.hand(f"{self.uid}_b{i}")
            gfx.hand(f"{self.uid}_r{i}")
            gfx.hand(f"{self.uid}_c{i}")
        # scrollbar (only when the list is longer than the window)
        self.bar_h = self.ROWS * self.ROW_H - 12
        self.bar_y = y + self.TOP + 6
        self.track = ui.create_image(x + w - 12, self.bar_y, anchor="nw",
                                     image=self.blank, tags=tg(f"{self.uid}_track"))
        self.thumb = ui.create_image(x + w - 12, self.bar_y, anchor="nw",
                                     image=self.blank, tags=tg(f"{self.uid}_track"))
        ui.tag_bind(f"{self.uid}_track", "<Button-1>", self._track_click)
        gfx.hand(f"{self.uid}_track")
        try:
            ui.bind("<MouseWheel>", self._wheel, add="+")
        except Exception:
            pass

    @staticmethod
    def cut(text, n):
        return text if len(text) <= n else text[:n - 1].rstrip() + "…"

    @staticmethod
    def fit(font, text, px):
        """The text, shortened with … only if it is wider than px."""
        if px <= 12:
            return ""
        if font.measure(text) <= px:
            return text
        lo, hi = 0, len(text)
        while lo < hi:                      # longest prefix that still fits
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid].rstrip() + "…") <= px:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…" if lo else "…"

    def set_rows(self, note, rows, empty=""):
        self.rows = rows
        self.top = max(0, min(self.top, len(rows) - self.ROWS))
        self.ui.itemconfig(self.note, text=note)
        self.ui.itemconfig(self.empty, text="" if rows else empty)
        self._clear_pending()
        self.draw()

    # ---- scrolling
    def scroll(self, d):
        top = max(0, min(self.top + d, len(self.rows) - self.ROWS))
        if top != self.top:
            self.top = top
            self.draw()

    def _wheel(self, e):
        if len(self.rows) > self.ROWS and self.x <= e.x <= self.x + self.w \
                and self.y <= e.y <= self.y + self.TOP + self.ROWS * self.ROW_H:
            try:
                if self.ui.itemcget(self.note, "state") == "hidden":
                    return
            except Exception:
                pass
            self.scroll(-1 if e.delta > 0 else 1)

    def _track_click(self, e):
        n = len(self.rows) - self.ROWS
        if n > 0:
            frac = (e.y - self.bar_y) / self.bar_h
            self.top = max(0, min(n, round(frac * n)))
            self.draw()

    # ---- clicking a row: toggle its checkbox, or show its full text
    def row_click(self, i):
        idx = self.top + i
        if idx >= len(self.rows):
            return
        row = self.rows[idx]
        if row.get("header"):
            return
        if row.get("check") is not None and self.on_toggle:
            self.on_toggle(row["key"])
        elif self.on_info:
            self.on_info(row)

    # ---- buttons: the first click asks, the second acts
    def click(self, i):
        idx = self.top + i
        if idx >= len(self.rows) or not self.rows[idx].get("button"):
            return
        row = self.rows[idx]
        if not row.get("confirm", True) or self.pending == row["key"]:
            self._clear_pending()
            self.on_action(row["key"])
            return
        self._clear_pending()
        self.pending = row["key"]
        self.pending_job = self.ui.after(6000, self._expire)
        if self.on_preview:
            self.on_preview(row)
        self.draw()

    def _expire(self):
        self.pending_job = None
        self.pending = None
        if self.on_preview:
            self.on_preview(None)
        self.draw()

    def _clear_pending(self):
        if self.pending_job is not None:
            try:
                self.ui.after_cancel(self.pending_job)
            except Exception:
                pass
        was = self.pending
        self.pending_job = self.pending = None
        if was is not None and self.on_preview:
            self.on_preview(None)

    # ---- drawing
    def draw(self):
        ui, g, T = self.ui, self.g, Theme
        right = self.x + self.w - 24
        for i, (line, title, sub, state, img, txt, cimg, ctxt, hit) in enumerate(self.pool):
            idx = self.top + i
            ry = self.y + self.TOP + i * self.ROW_H
            if idx >= len(self.rows):
                ui.itemconfig(line, fill=T.C_CARD)
                for it in (title, sub, state, txt, ctxt):
                    ui.itemconfig(it, text="")
                ui.itemconfig(img, image=self.blank)
                ui.itemconfig(cimg, image=self.blank)
                continue
            r = self.rows[idx]
            ui.itemconfig(line, fill=Theme.mix(T.C_CARD, T.C_BG, .55) if i else T.C_CARD)
            head = r.get("header")
            check = r.get("check")
            btn = r.get("button", "")
            tx = self.x + 20 + (self.CHK + 12 if check is not None else 0)
            # checkbox
            if check is None:
                ui.itemconfig(cimg, image=self.blank)
                ui.itemconfig(ctxt, text="")
            else:
                ui.itemconfig(cimg, image=g.rr(self.CHK, self.CHK, 6,
                                               T.ACCENT if check else T.C_TRACK))
                ui.itemconfig(ctxt, text="✓" if check else "")
            # state column takes only the room it needs
            st_txt = r.get("state", "")
            st_right = (right - self.BTN_W - 12) if btn else right
            st_w = self.f_state.measure(st_txt) if st_txt else 0
            ui.coords(state, st_right, ry + 22)
            ui.itemconfig(state, text=st_txt, fill=r.get("color") or T.DIM)
            limit = st_right - st_w - 16 - tx
            ui.coords(title, tx, ry + (22 if head or not r.get("sub") else 14))
            ui.coords(sub, tx, ry + 32)
            ui.itemconfig(title, text=self.fit(self.f_title if not head else self.f_state,
                                               r["title"], limit),
                          font=T.F_LABEL if head else T.F_HEAD,
                          fill=T.SUB if head else T.TXT)
            ui.itemconfig(sub, text="" if head else self.fit(
                self.f_sub, r.get("sub", ""), limit))
            if not btn:
                ui.itemconfig(img, image=self.blank)
                ui.itemconfig(txt, text="")
            elif self.pending == r["key"]:
                ui.itemconfig(img, image=g.rr(self.BTN_W, self.BTN_H, 14, T.YELLOW))
                ui.itemconfig(txt, text="Confirm?", fill="#1b1b1b")
            else:
                ui.itemconfig(img, image=g.rr(self.BTN_W, self.BTN_H, 14, T.C_TRACK))
                ui.itemconfig(txt, text=btn, fill=T.TXT)
        n = len(self.rows)
        if n > self.ROWS:
            th = max(24, int(self.bar_h * self.ROWS / n))
            ty = self.bar_y + int((self.bar_h - th) * self.top / (n - self.ROWS))
            ui.itemconfig(self.track, image=g.rr(4, self.bar_h, 2, T.C_TRACK))
            ui.itemconfig(self.thumb, image=g.rr(4, th, 2, T.SUB))
            ui.coords(self.thumb, self.x + self.w - 12, ty)
        else:
            ui.itemconfig(self.track, image=self.blank)
            ui.itemconfig(self.thumb, image=self.blank)


class SettingsWindow:
    """The Lmonitor window: sidebar + Dashboard, Display and Metrics pages."""

    PAGES = [("dashboard", "Dashboard"), ("performance", "Performance"),
             ("hardware", "Hardware"), ("display", "Display"),
             ("appearance", "Appearance"), ("metrics", "Metrics"),
             ("order", "Order"), ("personalize", "Personalize"),
             ("sessions", "Sessions"), ("diagnostics", "Diagnostics"),
             ("optimizer", "Optimizer"), ("storage", "Storage"),
             ("reports", "Reports"), ("typography", "Typography"),
             ("profiles", "Profiles")]
    PAGE_PERF, PAGE_HW, PAGE_DISPLAY, PAGE_ORDER, PAGE_SESS, PAGE_DIAG, \
        PAGE_OPT, PAGE_STORE, PAGE_REPORT, PAGE_TYPO, PAGE_PROFILES = 1, 2, 3, 6, 8, 9, 10, 11, 12, 13, 14
    # the order of the menu (page numbers above never change)
    NAV_GROUPS = [("Dashboard", "dashboard", [0]),
                  ("Monitor", "performance", [1, 2]),
                  ("Game", "sessions", [8, 9]),
                  ("Tools", "optimizer", [10, 11, 12]),
                  ("Customize", "personalize", [3, 4, 13, 14, 5, 6, 7])]
    HW_TABS = [("CPU / GPU", "rows_processor"),
               ("Memory", "rows_memory"), ("Storage", "rows_storage"),
               ("Network", "rows_network"), ("Sensors", "rows_sensors"),
               ("System", "rows_system")]
    REPORT_TEXT = "Save sensor report"
    SLIDE = False              # page slide-in animation (off: instant switch)

    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.settings = app.settings
        T = Theme
        self.root.title("Lmonitor")
        self.root.resizable(False, False)
        self.root.configure(bg=T.C_BG)
        self.canvas = tk.Canvas(self.root, width=T.WIN_W, height=T.WIN_H,
                                bg=T.C_BG, highlightthickness=0)
        self.canvas.pack()
        self.g = Gfx(self.canvas)
        self.tips = Tooltip(self.g, Theme.WIN_W, Theme.WIN_H)
        self.is_open = False
        self.first_show = True
        self.page = 0
        self.chips = {}
        self.group_sw = {}
        self.live = {}
        self.cpu_load = CpuLoad()
        self.slide = None          # (tag, pixels still to move back)
        self.slide_job = None
        self.nav = self.overlay_sw = None
        self.pos_seg = self.move_img = self.move_txt = self.move_hint = None
        self.look_rings, self.look_items, self.bg_rings = [], [], {}
        self.pal_rings, self.theme_rings, self.acc_rings = {}, {}, {}
        self.net_seg = None
        self._visible = None       # page that is currently shown
        self.gauges, self.sparks = {}, {}
        self.perf = self.store_tbl = None
        self.range_idx = 0
        self._pics = []
        self.blur_id = None
        self.order_groups = self.order_items = None
        self.order_group = "FPS"
        self.charts, self.net_chart, self.perf_info = [], None, None
        self.hw_tab, self.hw_tables = 0, []
        self.screen_note = None
        self.status_id = self.driver_id = self.report_id = None
        self.text_val = self.graph_val = self.alpha_val = None
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind("<Escape>", self.hide)

    # ---- drawing
    def draw(self):
        T, g, ui = Theme, self.g, self.canvas
        self._finish_slide()
        self._visible = None
        ui.delete("all")
        self.chips.clear()
        self.group_sw.clear()
        self.live.clear()
        start = self.page  # a redraw (Reset) stays on the same page

        # sidebar
        g.tab = ""
        ui.create_rectangle(0, 0, T.SIDE_W, T.WIN_H, fill=T.C_SIDE, outline="",
                            tags=("side",))
        self._logo = Logo.photo(44, T.ACCENT)  # keep a reference
        ui.create_image(20, 22, anchor="nw", tags=("side",), image=self._logo)
        ui.create_text(76, 36, text="Lmonitor", anchor="w", fill=T.TXT,
                       font=T.F_BRAND, tags=("side",))
        ui.create_text(76, 56, text="System overlay", anchor="w", fill=T.DIM,
                       font=T.F_SMALL, tags=("side",))
        self.nav = NavMenu(g, 16, 88,
                           [(t, ic, [(i, self.PAGES[i][1]) for i in pgs])
                            for t, ic, pgs in self.NAV_GROUPS],
                           start, self.show_page)

        # pages
        for name, _ in self.PAGES:
            g.tab = f"p_{name}"
            getattr(self, f"_draw_{name}")()

        # right side: quick settings (on every page)
        g.tab = ""
        self._draw_panel()

        # bottom of the sidebar
        g.tab = ""
        self.driver_id = ui.create_text(
            20, 408, text="", fill=T.YELLOW, font=T.F_SMALL_B,
            anchor="nw", width=T.SIDE_W - 40, tags=("driver",))
        ui.tag_bind("driver", "<Button-1>", lambda e: self.app.driver.click())
        g.hand("driver")
        ui.create_image(16, 460, anchor="nw", tags=("side",), image=g.rr(
            168, 56, 14, T.mix(T.C_SIDE, T.ACCENT, .14)))
        self._logo_s = Logo.photo(32, T.ACCENT)
        ui.create_image(28, 488, anchor="w", tags=("side",), image=self._logo_s)
        ui.create_text(68, 478, text=AppInfo.NAME, anchor="w", fill=T.TXT,
                       font=T.F_HEAD, tags=("side",))
        ui.create_text(68, 497, text=f"Version {AppInfo.VERSION}", anchor="w",
                       fill=T.DIM, font=T.F_SMALL, tags=("side",))
        # link to the project page (own small design: a pill with a branch icon)
        self.gh_bg = ui.create_image(16, 522, anchor="nw", tags=("gh",),
                                     image=g.rr(168, 28, 14, T.C_TRACK))
        self._gh_icon = Icons.get("branch", T.SUB, 16)
        ui.create_image(30, 536, anchor="w", tags=("gh",), image=self._gh_icon)
        self.gh_txt = ui.create_text(54, 536, text="Lmonitor on GitHub  ↗",
                                     anchor="w", fill=T.SUB, font=T.F_SMALL_B,
                                     tags=("gh",))
        ui.tag_bind("gh", "<Button-1>", lambda e: self.open_github())
        ui.tag_bind("gh", "<Enter>", lambda e: self._gh_hover(True))
        ui.tag_bind("gh", "<Leave>", lambda e: self._gh_hover(False))
        self.report_id = ui.create_text(
            100, 568, text=self.REPORT_TEXT, fill=T.DIM, width=T.SIDE_W - 32,
            justify="center", font=("Segoe UI", 9, "underline"),
            tags=("report",))
        ui.tag_bind("report", "<Button-1>", lambda e: self.app.save_report())
        g.hand("report")
        ui.create_text(100, 586, text="Exit: right-click the tray icon",
                       fill=T.DIM, font=("Segoe UI", 9), tags=("side",))
        self.show_page(start, animate=False)

    # ---- right panel: the overlay's quick settings (same as the Display and
    #      Appearance pages used to have, now always visible)
    def _draw_panel(self):
        T, g, ui, S, app = Theme, self.g, self.canvas, self.settings, self.app
        px, pw = T.PANEL_X, T.PANEL_W
        g.card(px, 24, pw, 316)
        g.label(px + 16, 46, "POSITION")
        pos = Settings.POS.index(S["pos"])
        self.pos_seg = Segmented(g, px + 16, 60, pw - 32, 34,
                                 ["Left", "Center", "Right"],
                                 pos if pos < 3 else -1, app.set_position)
        g.label(px + 16, 114, "LAYOUT")
        Segmented(g, px + 16, 128, pw - 32, 32, ["Horizontal", "Vertical"],
                  0 if S["layout"] == "h" else 1, app.set_layout)
        sx1, sx2 = px + 26, px + pw - 26
        g.label(px + 16, 184, "TEXT SIZE")
        self.text_val = g.label(px + pw - 16, 184, f"{S['text']} pt", T.TXT,
                                anchor="e")
        Slider(g, sx1, sx2, 208, 8, 18, 1, S["text"], self._on_text, S.save)
        g.label(px + 16, 238, "GRAPH SIZE")
        self.graph_val = g.label(px + pw - 16, 238, f"{S['graph']}%", T.TXT,
                                 anchor="e")
        Slider(g, sx1, sx2, 262, 50, 200, 10, S["graph"], self._on_graph, S.save)
        g.label(px + 16, 292, "OPACITY")
        self.alpha_val = g.label(px + pw - 16, 292, f"{S['alpha']}%", T.TXT,
                                 anchor="e")
        Slider(g, sx1, sx2, 316, 40, 100, 5, S["alpha"], self._on_alpha, S.save)

        g.card(px, 352, pw, 228)
        ui.create_image(px + 16, 368, anchor="nw", tags=g.tags("reset"),
                        image=g.rr(pw - 32, 38, 14, T.C_TRACK))
        ui.create_text(px + pw / 2, 387, text="Reset to defaults", fill=T.SUB,
                       font=T.F_SEG, tags=g.tags("reset"))
        ui.tag_bind("reset", "<Button-1>", lambda e: app.reset_defaults())
        g.hand("reset")
        img = ui.create_image(px + 16, 414, anchor="nw", tags=("save",),
                              image=g.rr(pw - 32, 46, 16, T.ACCENT))
        ui.create_text(px + pw / 2, 437, text="Save & close", fill=T.C_ON,
                       font=("Segoe UI Semibold", 12), tags=("save",))
        ui.tag_bind("save", "<Enter>", lambda e: ui.itemconfig(
            img, image=g.rr(pw - 32, 46, 16, T.ACCENT_HI)), add="+")
        ui.tag_bind("save", "<Leave>", lambda e: ui.itemconfig(
            img, image=g.rr(pw - 32, 46, 16, T.ACCENT)), add="+")
        ui.tag_bind("save", "<Button-1>", lambda e: self.hide())
        g.hand("save")
        g.label(px + 16, 488, "Overlay", T.TXT, T.F_HEAD)
        self.overlay_sw = Switch(g, px + pw - 16 - 46, 477, bool(S["on"]),
                                 app.set_overlay)
        self.live["dot"] = ui.create_image(px + 22, 524, tags=g.tags(),
                                           image=g.rr(10, 10, 5, T.C_OK))
        self.live["hero"] = g.label(px + 38, 524, "", T.TXT, T.F_SMALL_B)
        self.live["upd"] = g.label(px + 38, 545, "", T.DIM, T.F_SMALL)

    # ---- page 1: dashboard        self.show_page(start, animate=False)

    # ---- page 1: dashboard
    CARD_TIPS = {
        "cpu": "CPU load now, with temperature and clock. 'Hot' starts at 90 °C, "
               "'High load' at 90 %. Unknown values show '--', never a guess.",
        "gpu": "GPU load now, with temperature, power and clock. 'Hot' starts at "
               "80 °C, 'High load' at 90 %.",
        "ram": "Memory in use. 'Warm' from 80 %, 'High load' from 90 %.",
        "disk": "The first drive. 'Low space' under 20 % free, 'Almost full' "
                "under 10 % free. Details are in Tools > Storage."}

    def _draw_dashboard(self):
        T, g, ui, app = Theme, self.g, self.canvas, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Dashboard", "Live view of your system")
        cpu_c, gpu_c, ram_c = app.cpu.brand_color(), app.gpu.brand_color(), "#a78bfa"
        if cpu_c == T.WHITE:       # unknown CPU vendor: no brand color
            cpu_c = T.INTEL_BLUE
        if gpu_c == T.WHITE:
            gpu_c = T.ACCENT
        self.gauges, self.sparks = {}, {}
        cw, gap = 122, 8
        for i, (key, title, col, bar) in enumerate((("cpu", "CPU", cpu_c, False),
                                                    ("gpu", "GPU", gpu_c, False),
                                                    ("ram", "RAM", ram_c, False),
                                                    ("disk", "Storage", T.ACCENT, True))):
            self.gauges[key] = StatCard(g, X + i * (cw + gap), 84, cw, 170, key if key != "disk" else "storage",
                                        title, col, bar)
            self.tips.bind(self.gauges[key].tag, self.CARD_TIPS[key])
            self.gauges[key].set_loading()
        self.perf = PerfChart(g, X, 262, W, 136, [cpu_c, ram_c, gpu_c],
                              self._pick_range, self.range_idx)
        y, h = 406, 178
        # system status: real facts only
        sw_ = 200
        g.card(X, y, sw_, h)
        ui.create_image(X + 14, y + 22, anchor="w", tags=g.tags(),
                        image=Icons.get("diagnostics", T.ACCENT, 20))
        g.label(X + 40, y + 22, "System status", T.TXT, T.F_HEAD)
        self.live["score"] = g.label(X + 14, y + 54, "", T.TXT, T.F_BIG)
        self.live["score_sub"] = g.label(X + 14, y + 80, "", T.SUB, T.F_SMALL)
        for i, (key, name) in enumerate((("st_cpu", "CPU sensor"), ("st_gpu", "GPU sensor"),
                                         ("st_fps", "FPS capture"))):
            ry = y + 106 + i * 24
            g.label(X + 14, ry, name, T.DIM, T.F_SMALL)
            self.live[key] = g.label(X + sw_ - 14, ry, "--", T.TXT, T.F_SMALL_B, anchor="e")
        # network
        nx, nw = X + sw_ + 8, 150
        g.card(nx, y, nw, h)
        ui.create_image(nx + 14, y + 22, anchor="w", tags=g.tags(),
                        image=Icons.get("network", T.ACCENT, 20))
        g.label(nx + 40, y + 22, "Network", T.TXT, T.F_HEAD)
        for i, (key, name) in enumerate((("net_d", "↓ Download"), ("net_u", "↑ Upload"))):
            ry = y + 52 + i * 40
            g.label(nx + 14, ry, name, T.DIM, T.F_SMALL)
            self.live[key] = g.label(nx + 14, ry + 18, "--", T.TXT, T.F_HEAD)
        self.sparks["net"] = Spark(g, nx + 10, y + h - 44, nw - 20, 34, T.ACCENT)
        # quick actions: each one really goes somewhere
        qx, qw = nx + nw + 8, W - sw_ - nw - 16
        g.card(qx, y, qw, h)
        ui.create_image(qx + 14, y + 22, anchor="w", tags=g.tags(),
                        image=Icons.get("optimizer", T.ACCENT, 20))
        g.label(qx + 40, y + 22, "Actions", T.TXT, T.F_HEAD)
        for i, (label, fn) in enumerate((
                ("Scan PC", lambda: (app.scan_now(), self.show_page(self.PAGE_DIAG))),
                ("Hardware", lambda: self.show_page(self.PAGE_HW)),
                ("Sessions", lambda: self.show_page(self.PAGE_SESS)),
                ("Reports", lambda: self.show_page(self.PAGE_REPORT)))):
            by = y + 40 + i * 34
            tag = f"qa{i}"
            t = g.tags(tag)
            ui.create_image(qx + 12, by, anchor="nw", tags=t,
                            image=g.rr(qw - 24, 28, 14, T.C_TRACK))
            ui.create_text(qx + qw / 2, by + 14, text=label, fill=T.TXT,
                           font=T.F_LABEL, tags=t)
            ui.tag_bind(tag, "<Button-1>", lambda e, fn=fn: fn())
            g.hand(tag)
            self.tips.bind(tag, ("Start a read-only PC scan and open the results.",
                                 "Real values from your PC; n/a means not available.",
                                 "See why a game was slow, or compare two sessions.",
                                 "An explained score and files you can keep.")[i])

    def _pick_range(self, i):
        self.range_idx = i
        self._update_perf()

    # ---- page 4: display (move with the mouse, screens)
    def _draw_display(self):
        T, g, ui, S, app = Theme, self.g, self.canvas, self.settings, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Display", "Where the bar is, and when it is visible")
        # ---- move
        g.card(X, 92, W, 112)
        g.label(X + 20, 114, "MOVE THE BAR")
        g.label(X + 20, 136, "Drag it anywhere on the screen. The position is saved.",
                T.DIM, T.F_SMALL, width=W - 40)
        self.move_img = ui.create_image(X + 20, 154, anchor="nw", tags=g.tags("move"),
                                        image=g.rr(150, 40, 20, T.C_TRACK))
        self.move_txt = ui.create_text(X + 95, 174, text="Move with mouse", fill=T.SUB,
                                       font=T.F_LABEL, tags=g.tags("move"))
        ui.tag_bind("move", "<Button-1>", lambda e: app.set_moving(not app.moving))
        g.hand("move")
        self.move_hint = g.label(X + 186, 174, "", T.DIM, T.F_SMALL, width=W - 206)
        # ---- screens (rebuilt when monitors change)
        g.card(X, 216, W, 140)
        g.label(X + 20, 238, "SHOW ON")
        self.screen_note = g.label(X + W - 20, 238, "", T.DIM, T.F_SMALL, anchor="e")
        self.rebuild_screens()
        self.update_move_button()
        # ---- visibility
        g.card(X, 368, W, 216)
        g.label(X + 20, 390, "WHEN IS THE BAR VISIBLE")
        self.reveal_hint = g.label(X + W - 20, 390, "", T.DIM, T.F_SMALL, anchor="e")
        self.mode_seg = Segmented(g, X + 20, 410, W - 40, 38,
                                  ["Always visible", "F9 slides it in"],
                                  0 if S["show_mode"] == "always" else 1,
                                  app.set_show_mode)
        g.label(X + 20, 466, "Press F9 in any game: the bar glides down from the top, "
                "stays for a few seconds, then glides back up.", T.DIM, T.F_SMALL,
                width=W - 40, anchor="nw")
        g.label(X + 20, 516, "STAY ON SCREEN")
        self.secs_seg = Segmented(g, X + 20, 534, 210, 34, ["3 s", "5 s", "10 s"],
                                  (3, 5, 10).index(S["hotkey_secs"]),
                                  app.set_hotkey_secs)
        ui.create_image(X + W - 20 - 132, 534, anchor="nw", tags=g.tags("tryit"),
                        image=g.rr(132, 34, 17, T.C_TRACK))
        ui.create_text(X + W - 20 - 66, 551, text="Try it now", fill=T.SUB,
                       font=T.F_LABEL, tags=g.tags("tryit"))
        ui.tag_bind("tryit", "<Button-1>", lambda e: app.try_reveal())
        g.hand("tryit")
        self.update_reveal_hint()
        self.tips.bind("move", "Unlocks the bar so you can drag it. Press Done "
                       "(or right-click the bar) to lock it again.")
        self.tips.bind(self.mode_seg.tag, "Always visible keeps the bar on screen. "
                       "F9 hides it until you press F9.")
        self.tips.bind(self.secs_seg.tag, "How long the bar stays after F9.")
        self.tips.bind("tryit", "Plays the F9 slide once (needs F9 mode).")

    def open_github(self):
        try:
            webbrowser.open(AppInfo.URL)
        except Exception:
            Logger.error("open github")

    def _gh_hover(self, on):
        ui, T = self.canvas, Theme
        ui.itemconfig(self.gh_bg, image=self.g.rr(
            168, 28, 14, T.mix(T.C_TRACK, T.ACCENT, .35) if on else T.C_TRACK))
        ui.itemconfig(self.gh_txt, fill=T.TXT if on else T.SUB)
        ui.config(cursor="hand2" if on else "")

    def update_reveal_hint(self, warn=False):
        if getattr(self, "reveal_hint", None) is None:
            return
        on = self.settings["show_mode"] == "hotkey"
        if warn:
            text, col = ("Choose 'F9 slides it in' first" if not on else
                         "Overlay is off or being moved"), Theme.YELLOW
        else:
            text, col = ("F9 mode is on" if on else "Always on screen"), Theme.DIM
        self.canvas.itemconfig(self.reveal_hint, text=text, fill=col)

    def rebuild_screens(self):
        """Draw one chip per connected display (call again after a change)."""
        T, g, ui, S, app = Theme, self.g, self.canvas, self.settings, self.app
        if self.screen_note is None:
            return
        ui.delete("scr")
        X = T.PAGE_X
        old, g.tab = g.tab, "p_display"
        mons = app.displays.monitors[:4]
        chosen = S["monitor"]
        _, missing = app.displays.resolve(chosen)
        fit = lambda t, n: t if len(t) <= n else t[:n - 1] + "…"
        chips = [("primary", "Primary", "automatic", "Windows")]
        chips += [(m.name, fit(app.displays.title(m), 11),
                   f"{m.res_w}×{m.res_h}",
                   f"{m.hz} Hz" if m.hz else "") for m in mons]
        for i, (name, l1, l2, l3) in enumerate(chips):
            x, y, w, h = X + 20 + i * 96, 262, 88, 78
            on = name == chosen
            tg = g.tags("scr", f"scr{i}")
            ui.create_image(x - 2, y - 2, anchor="nw", tags=tg,
                            image=g.rr(w + 4, h + 4, 14,
                                       T.ACCENT if on else T.C_TRACK))
            ui.create_image(x, y, anchor="nw", tags=tg, image=g.rr(
                w, h, 12, T.lift(T.C_CARD, 0.06)))
            lines = [(l1, T.TXT, T.F_LABEL), (l2, T.SUB, T.F_SMALL_B),
                     (l3, T.DIM, T.F_SMALL)]
            m = next((mm for mm in mons if mm.name == name), None)
            if m is not None and m.primary:
                lines.append(("Primary", T.ACCENT, T.F_SMALL_B))
            for k, (txt, col, fnt) in enumerate(lines):
                if txt:
                    ui.create_text(x + w / 2, y + 15 + k * 17, text=txt, fill=col,
                                   font=fnt, tags=tg)
            ui.tag_bind(f"scr{i}", "<Button-1>",
                        lambda e, n=name: app.set_monitor(n))
            self.tips.bind(f"scr{i}", "Show the bar on this display." if name != "primary"
                           else "Follow the Windows primary display.")
            ui.tag_bind(f"scr{i}", "<Enter>", lambda e: ui.config(cursor="hand2"))
            ui.tag_bind(f"scr{i}", "<Leave>", lambda e: ui.config(cursor=""))
        extra = len(app.displays.monitors) - len(mons)
        if missing:
            note = "Chosen display is not connected - using Primary"
        elif extra > 0:
            note = f"{extra} more display(s) not listed - drag the bar there"
        else:
            note = f"{len(app.displays.monitors)} display(s) connected"
        ui.itemconfig(self.screen_note, text=note,
                      fill=T.YELLOW if missing else T.DIM)
        g.tab = old
        if self.page != self.PAGE_DISPLAY:  # created while the page is hidden
            ui.itemconfigure("scr", state="hidden")

    # ---- page 2: performance (charts)
    def _draw_performance(self):
        T, g, S, app = Theme, self.g, self.settings, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Performance", "Live charts while this window is open")
        Segmented(g, X + W - 168, 22, 168, 32, ["1 s", "2 s", "5 s"],
                  Settings.REFRESH.index(S["refresh"]), app.set_refresh)
        self.perf_info = g.label(X, 76, "", T.DIM, T.F_SMALL)
        cw, ch, gap = 248, 152, 16
        specs = [("g_use", "GPU USAGE", lambda v: f"{v:.0f} %"),
                 ("c_use", "CPU USAGE", lambda v: f"{v:.0f} %"),
                 ("g_temp", "GPU TEMPERATURE", lambda v: f"{v:.0f} °C"),
                 ("c_temp", "CPU TEMPERATURE", lambda v: f"{v:.0f} °C"),
                 ("r_use", "RAM USAGE", lambda v: f"{v:.0f} %")]
        self.charts = []
        for n, (key, title, fmt) in enumerate(specs):
            x = X + (n % 2) * (cw + gap)
            y = 92 + (n // 2) * (ch + gap)
            self.charts.append((key, fmt, LineChart(g, x, y, cw, ch, title)))
        self.net_chart = LineChart(g, X + cw + gap, 92 + 2 * (ch + gap), cw, ch,
                                   "NETWORK", vmax=None,
                                   colors=[T.ACCENT, "#7aa2ff"],
                                   value_font=T.F_SMALL_B)

    @staticmethod
    def _card_text(row, info):
        """Text for the detail card: everything that did not fit in the row."""
        body = (row.get("info") if info else None) or row.get("detail") or row.get("sub", "")
        if len(row["title"]) > 34 and info:
            body = row["title"] + " - " + body
        lines = textwrap.wrap(body, 74)
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1][:70].rstrip() + "…"
        return "\n".join(lines)

    # ---- page: optimizer
    OPT_TABS = ["Startup", "Power", "Gaming", "History"]

    def _draw_optimizer(self):
        T, g, ui, app = Theme, self.g, self.canvas, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Optimizer", "Safe, reversible changes - nothing happens without your OK")
        self.opt_seg = Segmented(g, X, 76, W, 32, self.OPT_TABS, 0, self._pick_opt_tab)
        self.opt_tab = 0
        g.card(X, 118, W, 326)
        self.opt_list = ActionList(g, X, 118, W, self._opt_action, self._opt_preview,
                                   lambda r: self._opt_preview(r, True))
        g.card(X, 452, W, 132)
        self.opt_head = g.label(X + 18, 472, "LAST CHANGE")
        self.opt_res_title = g.label(X + 18, 494, "", T.TXT, T.F_HEAD)
        self.opt_res_ba = g.label(X + 18, 516, "", T.SUB, T.F_SMALL_B)
        self.opt_res_msg = g.label(X + 18, 548, "", T.DIM, T.F_SMALL,
                                   width=W - 36, anchor="nw")
        self.opt_version = -1
        self._fill_opt()

    def _pick_opt_tab(self, i):
        self.opt_tab = i
        self._fill_opt()

    def _fill_opt(self):
        opt, T = self.app.optimizer, Theme
        tab = self.opt_tab
        rows, note, empty = [], "", ""
        if not opt.refreshed:
            empty = "Reading the current state..."
        elif tab == 0:
            note = ("Programs that start with Windows. Disabling keeps the entry, "
                    "so you can enable it again here at any time.")
            items = sorted(opt.startup, key=lambda i: (not i["enabled"], i["name"].lower()))
            for i in items:
                locked = i["hive"] == "HKLM" and not WinApi.admin
                exe = re.split(r'[\\/]', i["cmd"].strip().strip('"').split('"')[0].strip())[-1] \
                    if i.get("cmd") else ""
                rows.append({"title": i["name"], "sub": f"{i['where']} · {exe}".strip(" ·"),
                             "info": f"{i['where']} - {i['cmd']}",
                             "detail": (f"{'Disable' if i['enabled'] else 'Enable'} this "
                                        f"startup entry. Program: {i['cmd']}. "
                                        "The entry is kept, so you can reverse it in History."),
                             "state": "Enabled" if i["enabled"] else "Disabled",
                             "color": T.C_OK if i["enabled"] else T.DIM,
                             "button": "" if locked else
                             ("Disable" if i["enabled"] else "Enable"),
                             "key": ("startup", i["key"], not i["enabled"])})
            empty = "No startup programs found in the Run keys or Startup folders."
        elif tab == 1:
            note = "The power plans Windows offers. Switching takes effect at once."
            for pl in (opt.plans or []):
                rows.append({"title": pl["name"], "sub": "Windows power plan",
                             "detail": f"Switch the active power plan to {pl['name']} "
                                       f"({pl['guid']}). Undo returns to the previous plan.",
                             "state": "Active" if pl["active"] else "",
                             "color": T.C_OK, "button": "" if pl["active"] else "Use this plan",
                             "key": ("power", pl["guid"])})
            empty = "Windows did not list any power plan."
        elif tab == 2:
            note = ("Suggestions for gaming and daily use. Each one is shown first, "
                    "and every change can be undone in History.")
            for sid, it in GameSettings.ITEMS.items():
                st = opt.settings.get(sid)
                if not st:
                    continue
                rows.append({"title": it["title"], "sub": it["sub"], "detail": it["sub"],
                             "state": st[2],
                             "color": T.C_OK if st[1] else T.YELLOW,
                             "button": "" if st[1] else it["button"],
                             "key": ("setting", sid)})
            for name, label in (("gaming", "Gaming preset"), ("daily", "Daily preset")):
                steps = opt.preset_steps(name)
                sub = "; ".join(s[0] for s in steps) if steps else \
                    "Already set" + ((" - " + opt.preset_note(name)) if opt.preset_note(name) else "")
                short = f"{len(steps)} change(s)" if steps else sub
                rows.append({"title": label, "sub": short,
                             "detail": ("Will do: " + sub) if steps else sub, "state": "",
                             "button": "Apply" if steps else "",
                             "key": ("preset", name)})
        else:
            note = "Everything Lmonitor changed. Undo puts the old value back."
            log = list(reversed(self.app.change_log.load()))
            word = {"applied": ("Applied", T.C_OK), "reverted": ("Undone", T.DIM),
                    "failed": ("Not kept", T.RED)}
            for e in log:
                w_, c_ = word.get(e["status"], (e["status"], T.DIM))
                when = time.strftime("%d %b %H:%M", time.localtime(e["t"]))
                ba = f"{e['before']} → {e['after']}" if e.get("before") else e.get("after", "")
                rows.append({"title": e["title"], "sub": f"{when} · {ba}", "state": w_,
                             "detail": f"Put the old value back: {e.get('before', '')}.",
                             "color": c_,
                             "button": "Undo" if e["status"] == "applied" and e.get("revert") else "",
                             "key": ("undo", e["id"])})
            empty = "Nothing has been changed yet."
        self.opt_list.set_rows(note, rows, empty)
        self._show_last()

    def _opt_preview(self, row, info=False):
        """First click on a button: show exactly what will happen.
        info=True: a click on the row itself - show its full text."""
        ui, T = self.canvas, Theme
        if row is None:
            self._show_last()
            return
        ui.itemconfig(self.opt_head, text="DETAILS" if info else
                      "PLEASE CONFIRM - press the yellow button again")
        ui.itemconfig(self.opt_res_title, text=row["title"][:48] + ("…" if len(row["title"]) > 48 else ""))
        ui.itemconfig(self.opt_res_ba, text=row.get("state", ""),
                      fill=T.SUB if info else T.YELLOW)
        ui.itemconfig(self.opt_res_msg, text=self._card_text(row, info))

    def _show_last(self):
        r = self.app.optimizer.last
        ui, T = self.canvas, Theme
        ui.itemconfig(self.opt_head, text="LAST CHANGE")
        if not r:
            ui.itemconfig(self.opt_res_title, text="No change yet")
            ui.itemconfig(self.opt_res_ba, text="")
            ui.itemconfig(self.opt_res_msg, text="Pick a tab, choose what you want and "
                          "press its button.")
            return
        ui.itemconfig(self.opt_res_title, text=r["title"][:56])
        ba = (f"Before: {r['before']}    After: {r['after']}" if r.get("before") or r.get("after") else "")
        mark = ("   ✓ checked" if r["ok"] and r.get("id") else "") if ba else ""
        ui.itemconfig(self.opt_res_ba, text=ba + mark, fill=T.C_OK if r["ok"] else T.RED)
        ui.itemconfig(self.opt_res_msg, text=textwrap.fill(r.get("message", ""), 74))

    def _opt_action(self, key):
        opt = self.app.optimizer
        kind = key[0]
        fn = {"startup": lambda: opt.run(opt.set_startup, key[1], key[2]),
              "power": lambda: opt.run(opt.set_power, key[1]),
              "setting": lambda: opt.run(opt.set_setting, key[1]),
              "preset": lambda: opt.run(opt.apply_preset, key[1]),
              "temp": lambda: opt.run(opt.clean_temp, [key[1]]),
              "temp_scan": lambda: opt.run(opt.scan_temp),
              "undo": lambda: opt.run(opt.revert, key[1])}[kind]
        if fn():
            self._poll_opt()

    def _poll_opt(self):
        """While an action runs, look at it every 200 ms."""
        opt = self.app.optimizer
        if opt.busy:
            self.root.after(200, self._poll_opt)
            return
        self.opt_version = opt.version
        self._fill_opt()

    def _update_opt(self):
        if getattr(self, "opt_list", None) is None:
            return
        opt = self.app.optimizer
        if opt.version != self.opt_version and not opt.busy:
            self.opt_version = opt.version
            self._fill_opt()

    # ---- page: profiles (density, value color, saved looks)
    def _draw_profiles(self):
        T, g, ui, S, app = Theme, self.g, self.canvas, self.settings, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Profiles", "How much the bar shows, and the color of its values")
        g.card(X, 92, W, 150)
        g.label(X + 20, 114, "DENSITY")
        g.label(X + 20, 136, "How many metrics the bar shows", T.DIM, T.F_SMALL)
        dens = [n for _, n, _ in Profiles.DENSITY]
        cur = Profiles.density_of(S.show)
        self.pf_density = Segmented(
            g, X + 20, 160, 360, 40, dens,
            [k for k, _, _ in Profiles.DENSITY].index(cur) if cur else 1,
            lambda i: self.app.set_density(Profiles.DENSITY[i][0]))
        self.pf_dens_note = g.label(X + 20, 218, "", T.SUB, T.F_SMALL, width=W - 40)
        g.card(X, 254, W, 150)
        g.label(X + 20, 276, "VALUE COLOR")
        g.label(X + 20, 298, "The color of the numbers on the bar", T.DIM, T.F_SMALL)
        self.pf_rings = {}
        for i, (key, name, col) in enumerate(T.VALUE_COLORS):
            x, y = X + 24 + i * 84, 330
            on = S["value_color"] == key
            self.pf_rings[key] = ui.create_image(
                x - 3, y - 3, anchor="nw", tags=g.tags(f"vc_{key}"),
                image=g.rr(78, 46, 15, T.ACCENT if on else T.C_TRACK))
            ui.create_image(x, y, anchor="nw", tags=g.tags(f"vc_{key}"),
                            image=g.rr(72, 40, 12, col or T.ACCENT))
            ui.create_text(x + 36, y + 20, text=name, fill=Theme._on_color(col or T.ACCENT),
                           font=T.F_SMALL_B, tags=g.tags(f"vc_{key}"))
            ui.tag_bind(f"vc_{key}", "<Button-1>", lambda e, k=key: self.app.set_value_color(k))
            g.hand(f"vc_{key}")
            self.tips.bind(f"vc_{key}", "Warnings (hot, low FPS) keep their own red/yellow." if key == "white"
                           else f"Numbers on the bar use {name.lower()}. Warnings keep their own color.")
        self.tips.bind(self.pf_density.tag, "Compact: FPS + usage. Balanced: adds "
                       "temperatures and lows. Detailed: everything.")
        self._fill_profiles()

    def _fill_profiles(self):
        S, T = self.settings, Theme
        cur = Profiles.density_of(S.show)
        self.canvas.itemconfig(self.pf_dens_note, text={
            "compact": "Compact: FPS and usage only.",
            "balanced": "Balanced: usage, temperatures and FPS lows.",
            "detailed": "Detailed: everything, plus the graph.",
            "": "Custom: you picked metrics yourself (Metrics page)."}[cur])
        for k, ring in self.pf_rings.items():
            self.canvas.itemconfig(ring, image=self.g.rr(
                78, 46, 15, T.ACCENT if S["value_color"] == k else T.C_TRACK))

    def refresh_profiles(self):
        if getattr(self, "pf_rings", None):
            self._fill_profiles()

    # ---- page: typography (overlay text preview + weight)
    def _draw_typography(self):
        T, g, ui, S = Theme, self.g, self.canvas, self.settings
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Typography", "How the text on the bar looks - applied live")
        g.card(X, 92, W, 190)
        g.label(X + 20, 114, "PREVIEW")
        self.ty_prev = ui.create_text(X + 20, 158, text="CPU 42%  62°C", anchor="w",
                                      fill=T.TXT, tags=g.tags("ty_prev"),
                                      font=("Consolas", 18, "bold"))
        self.ty_prev3 = ui.create_text(X + 20, 196, text="GPU 67%  71°C   FPS 144", anchor="w",
                                       fill=T.TXT, tags=g.tags("ty_prev3"),
                                       font=("Consolas", 18, "bold"))
        self.ty_prev2 = ui.create_text(X + 20, 250, text="", anchor="w", fill=T.DIM,
                                       font=T.F_SMALL, tags=g.tags("ty_prev2"))
        g.card(X, 294, W, 150)
        g.label(X + 20, 316, "WEIGHT")
        g.label(X + 20, 350, "Values", T.SUB, T.F_HEAD)
        self.ty_val = Segmented(g, X + 130, 334, 220, 36, ["Regular", "Bold"],
                                1 if S["weight"] == "bold" else 0,
                                lambda i: self.app.set_font(weight="bold" if i else "normal"))
        g.label(X + 20, 402, "Labels", T.SUB, T.F_HEAD)
        self.ty_lab = Segmented(g, X + 130, 386, 220, 36, ["Regular", "Bold"],
                                1 if S["label_weight"] == "bold" else 0,
                                lambda i: self.app.set_font(label_weight="bold" if i else "normal"))
        self.tips.bind(self.ty_val.tag, "Weight of the numbers on the bar.")
        self.tips.bind(self.ty_lab.tag, "Weight of the labels (CPU, GPU, FPS...).")
        self._fill_typo()

    def _fill_typo(self):
        S, ov = self.settings, self.app.overlay
        cur = ov.resolve_font(S["font"])
        f = (cur, 18, S["weight"])
        self.canvas.itemconfig(self.ty_prev, font=f)
        self.canvas.itemconfig(self.ty_prev3, font=f)
        note = f"Font: {cur}. Values {S['weight'].replace('normal', 'regular')}, " \
               f"labels {S['label_weight'].replace('normal', 'regular')}."
        if S["font"].lower() != cur.lower():
            note = f"'{S['font']}' is not installed - showing {cur} instead."
        self.canvas.itemconfig(self.ty_prev2, text=note)

    def refresh_typography(self):
        if getattr(self, "ty_prev", None) is not None:
            self._fill_typo()

    # ---- page: reports
    REPORT_TABS = ["Score", "Before / after", "Sessions", "Export"]

    def _draw_reports(self):
        T, g = Theme, self.g
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Reports", "An explained score, comparisons, and files you can keep")
        self.rp_seg = Segmented(g, X, 76, W, 32, self.REPORT_TABS, 0, self._pick_report_tab)
        self.rp_tab = 0
        g.card(X, 118, W, 326)
        self.rp_list = ActionList(g, X, 118, W, self._report_action, self._report_preview,
                                  self._report_preview)
        g.card(X, 452, W, 132)
        self.rp_head = g.label(X + 18, 472, "DETAIL")
        self.rp_res_title = g.label(X + 18, 494, "", T.TXT, T.F_HEAD)
        self.rp_res_ba = g.label(X + 18, 516, "", T.SUB, T.F_SMALL_B)
        self.rp_res_msg = g.label(X + 18, 540, "", T.DIM, T.F_SMALL,
                                  width=W - 36, anchor="nw")
        self.rp_version = -1
        self._fill_report()

    def _pick_report_tab(self, i):
        self.rp_tab = i
        self._fill_report()

    @staticmethod
    def _fmt1(v):
        return "-" if v is None else f"{v:.0f}"

    def _fill_report(self):
        T, rp = Theme, self.app.reports.report
        tab, rows, note, empty = self.rp_tab, [], "", ""
        tm = lambda t: time.strftime("%d %b %H:%M", time.localtime(t))
        if rp is None:
            empty = "Building the report..."
        elif tab == 0:
            sc = rp["score"]
            note = sc["text"]
            for d in sc["deductions"]:
                rows.append({"title": d["title"], "sub": f"{d['area']} · {d['why']}",
                             "detail": f"{d['title']} ({d['area']}): {d['why']}. "
                                       f"Costs {d['points']} point(s); "
                                       "point values are Lmonitor's own choice.",
                             "state": f"-{d['points']}",
                             "color": T.RED if d["sev"] == "warn" else T.YELLOW})
            for u in sc["unknown"]:
                rows.append({"title": u["title"], "sub": f"{u['area']} · no answer from Windows",
                             "detail": "This check could not be done. It is not counted "
                                       "as healthy and costs no points.",
                             "state": "not counted", "color": T.DIM})
            if sc["value"] is not None and not sc["deductions"]:
                rows.append({"title": "No deductions", "sub": f"{rp['ok_count']} checks are OK",
                             "state": "OK", "color": T.C_OK})
            empty = "Run a scan on the Diagnostics page first."
        elif tab == 1:
            note = "What changed between your last two scans, and between your last two sessions of one game."
            sc = rp["scan_changes"]
            if sc:
                for lbl, key, col in (("Resolved", "resolved", T.C_OK), ("Better", "better", T.C_OK),
                                      ("New", "new", T.RED), ("Worse", "worse", T.RED)):
                    for t in sc[key]:
                        rows.append({"title": t, "sub": f"Scan {tm(sc['before'])} → {tm(sc['after'])}",
                                     "state": lbl, "color": col})
                for t in sc["unknown"]:
                    rows.append({"title": t, "sub": "Could not be checked in the newer scan",
                                 "state": "unknown", "color": T.DIM})
                for t in sc["made_between"]:
                    rows.append({"title": t, "sub": "Changed with Lmonitor in between",
                                 "state": "change", "color": T.SUB})
                if not rows:
                    rows.append({"title": "No change between the scans",
                                 "sub": f"{sc['same']} items unchanged", "state": "same", "color": T.DIM})
            sn = rp["session_changes"]
            if sn:
                for r in sn["rows"]:
                    if r["delta"] is None:
                        sub, st, col = "not comparable (missing data)", "n/a", T.DIM
                    else:
                        sub = f"{self._fmt1(r['old'])} → {self._fmt1(r['new'])}{r.get('unit', '')}"
                        st = {"better": "better", "worse": "worse"}.get(r["verdict"], "same")
                        col = {"better": T.C_OK, "worse": T.RED}.get(r["verdict"], T.DIM)
                    rows.append({"title": f"{sn['game']}: {r['label']}", "sub": sub,
                                 "state": st, "color": col})
            empty = "Needs two Diagnostics scans, or two sessions of the same game."
        elif tab == 2:
            note = "Your latest recorded game sessions (details are on the Sessions page)."
            for s in rp["sessions"]:
                bad = [f["title"] for f in s["findings"] if f["sev"] in ("warn", "notice")]
                rows.append({"title": s["game"],
                             "sub": f"{tm(s['start'])} · {int(s['duration'] // 60)} min · 1% low {self._fmt1(s['low1'])}"
                                    + (f" · {len(bad)} finding(s)" if bad else ""),
                             "detail": ("Findings: " + "; ".join(bad)) if bad else "No warnings or notices.",
                             "state": (self._fmt1(s["avg_fps"]) + " FPS") if s["avg_fps"] else "no FPS",
                             "color": T.TXT})
            empty = "No game sessions recorded yet."
        else:
            note = (f"Reports are saved to {ReportBuilder.redact(Reports.folder())}. They stay on this PC; "
                    "Windows user names are hidden.")
            for key, title, sub in (("html", "HTML report", "Readable page: score, issues, sessions"),
                                    ("json", "JSON report", "The same data for other tools")):
                rows.append({"title": title, "sub": sub, "state": "", "button": "Save",
                             "confirm": False, "key": ("save", key)})
            rows.append({"title": "Reports folder", "sub": "Open it in Explorer", "state": "",
                         "button": "Open", "confirm": False, "key": ("folder",)})
            rows.append({"title": "Refresh data", "sub": "Rebuild from the latest scan and sessions",
                         "state": "", "button": "Refresh", "confirm": False, "key": ("refresh",)})
        self.rp_list.set_rows(note, rows, empty)
        self._show_report_last()

    def _report_preview(self, row):
        ui, T = self.canvas, Theme
        if row is None:
            self._show_report_last()
            return
        ui.itemconfig(self.rp_head, text="DETAIL")
        ui.itemconfig(self.rp_res_title, text=row["title"][:70])
        ui.itemconfig(self.rp_res_ba, text=row.get("state", ""))
        ui.itemconfig(self.rp_res_msg, text=textwrap.fill(row.get("detail") or row.get("sub", ""), 74))

    def _show_report_last(self):
        r, ui, T = self.app.reports.last, self.canvas, Theme
        ui.itemconfig(self.rp_head, text="LAST FILE")
        if not r:
            ui.itemconfig(self.rp_res_title, text="Nothing saved yet")
            ui.itemconfig(self.rp_res_ba, text="")
            ui.itemconfig(self.rp_res_msg, text="Open the Export tab to save a report.")
            return
        ui.itemconfig(self.rp_res_title, text=r["title"])
        ui.itemconfig(self.rp_res_ba, text="saved" if r["ok"] else "failed",
                      fill=T.C_OK if r["ok"] else T.RED)
        ui.itemconfig(self.rp_res_msg, text=textwrap.fill(r.get("message", ""), 74))

    def _report_action(self, key):
        rp = self.app.reports
        fn = {"save": lambda: rp.run(rp.save, key[1] if len(key) > 1 else "html"),
              "folder": lambda: rp.run(rp.open_folder),
              "refresh": lambda: rp.run(rp.build)}[key[0]]
        if fn():
            self._poll_report()

    def _poll_report(self):
        rp = self.app.reports
        if rp.busy:
            self.root.after(200, self._poll_report)
            return
        self.rp_version = rp.version
        self._fill_report()

    def _update_report(self):
        if getattr(self, "rp_list", None) is None:
            return
        rp = self.app.reports
        if rp.version != self.rp_version and not rp.busy:
            self.rp_version = rp.version
            self._fill_report()

    # ---- page: storage
    STORE_TABS = ["Cleanup", "Big folders", "Large files"]

    @staticmethod
    def _mid(path, n=46):
        if len(path) <= n:
            return path
        k = (n - 1) // 2
        return path[:k] + "…" + path[-(n - 1 - k):]

    def _draw_storage(self):
        T, g, ui = Theme, self.g, self.canvas
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Storage", "See what takes space - only safe items can be removed")
        self.st_seg = Segmented(g, X, 76, W, 32, self.STORE_TABS, 0, self._pick_store_tab)
        self.st_tab = 0
        g.card(X, 118, W, 326)
        self.st_list = ActionList(g, X, 118, W, self._store_action, self._store_preview,
                                  lambda r: self._store_preview(r, True),
                                  self._store_toggle)
        # the summary: how much can be freed, what is selected, one Clean up button
        self.st_big_font = tkfont.Font(font=T.F_BIG)
        self.st_big = ui.create_text(X + 20, 118 + 8, text="", anchor="nw", fill=T.TXT,
                                     font=T.F_BIG, tags=g.tags())
        self.st_sel = ui.create_text(X + 20, 118 + 18, text="", anchor="nw", fill=T.SUB,
                                     font=T.F_SMALL, tags=g.tags())
        bt = g.tags("st_clean")
        self.st_btn_img = ui.create_image(X + W - 24 - 124, 118 + 10, anchor="nw",
                                          image=self.st_list.blank, tags=bt)
        self.st_btn_txt = ui.create_text(X + W - 24 - 62, 118 + 26, text="",
                                         fill=T.C_ON, font=T.F_LABEL, tags=bt)
        ui.tag_bind("st_clean", "<Button-1>", lambda e: self._store_clean_click())
        g.hand("st_clean")
        self.st_checked = None          # ids ticked in Cleanup (None = use the defaults)
        self.st_clean_pending = None
        g.card(X, 452, W, 132)
        self.st_head = g.label(X + 18, 472, "LAST ACTION")
        self.st_res_title = g.label(X + 18, 494, "", T.TXT, T.F_HEAD)
        self.st_res_ba = g.label(X + 18, 516, "", T.SUB, T.F_SMALL_B)
        self.st_res_msg = g.label(X + 18, 540, "", T.DIM, T.F_SMALL,
                                  width=W - 36, anchor="nw")
        self.st_version = -1
        self._fill_store()

    def _pick_store_tab(self, i):
        self.st_tab = i
        self.st_clean_pending = None
        self._fill_store()
        st = self.app.storage
        if i == 1 and st.folders is None and not st.busy:
            st.run(st.scan_folders)
            self._poll_store()
        if i == 2 and st.large is None and not st.busy:
            st.run(st.scan_large)
            self._poll_store()

    def _fill_store(self):
        st, T = self.app.storage, Theme
        tab = self.st_tab
        rows, note, empty = [], "", ""
        if tab == 0:
            have = [l for l in Storage.cache_locations() if st.caches.get(l[0])]
            if self.st_checked is None and st.scanned:
                self.st_checked = {l[0] for l in have if l[0] in Storage.RECOMMENDED
                                   and st.caches[l[0]]["old_bytes"]}
            chk = self.st_checked or set()
            groups = (("RECOMMENDED", [l for l in have if l[0] in Storage.RECOMMENDED]),
                      ("OTHER - REBUILT AUTOMATICALLY",
                       [l for l in have if l[0] not in Storage.RECOMMENDED]))
            for gname, locs in groups:
                if not locs:
                    continue
                rows.append({"title": gname, "header": True, "color": T.DIM,
                             "state": fmt_size(sum(st.caches[l[0]]["old_bytes"] for l in locs)),
                             "key": ("hdr", gname)})
                for lid, title, path, why in locs:
                    r = st.caches[lid]
                    can = r["old_files"] > 0
                    rows.append({
                        "title": title, "sub": why,
                        "detail": (f"Deletes files older than one day in {path}. "
                                   f"About {fmt_size(r['old_bytes'])} will be freed; files in "
                                   "use are skipped. This cannot be undone."),
                        "info": f"{path} - {r['files']} files, {r['old_files']} older than a day",
                        "state": fmt_size(r["old_bytes"]), "color": T.TXT,
                        "check": (lid in chk) if can else None,
                        "key": ("cache", lid)})
            empty = "Measuring..." if not st.scanned else "No cache folders found."
        elif tab == 1:
            note = ("The biggest folders in your user folder (and other drives). "
                    "Nothing here is deleted - use Show to look.")
            for d in (st.folders or []):
                sub = d["reason"] or self._mid(d["path"])
                rows.append({"title": os.path.basename(d["path"]) or d["path"],
                             "sub": sub, "state": fmt_size(d["bytes"]) +
                             ("+" if d["partial"] else ""), "color": T.TXT,
                             "button": "Show", "confirm": False,
                             "key": ("show", d["path"])})
            empty = ("Scanning" + (f" {st.progress}" if st.progress else "") + "...") \
                if st.folders is None else "No folders found."
        else:
            note = (f"Files of {fmt_size(Storage.LARGE_MIN)} or more. Only files in your "
                    "Downloads folder can be moved to the Recycle Bin.")
            for d in (st.large or []):
                can = d["deletable"]
                rows.append({
                    "title": os.path.basename(d["path"]),
                    "sub": (d["reason"] + " · " if d["reason"] else "") + self._mid(os.path.dirname(d["path"]), 38),
                    "detail": (f"Move this file to the Recycle Bin: {d['path']} "
                               f"({fmt_size(d['bytes'])}). You can restore it from there."
                               if can else d["path"]),
                    "state": fmt_size(d["bytes"]), "color": T.TXT,
                    "button": "Recycle" if can else "Show", "confirm": can,
                    "key": ("recycle" if can else "show", d["path"])})
            empty = ("Scanning" + (f" {st.progress}" if st.progress else "") + "...") \
                if st.large is None else "No large files found."
        self.st_list.set_rows(note, rows, empty)
        self._fill_store_summary()
        self._show_store_last()

    def _store_selected(self):
        st = self.app.storage
        return [l for l in Storage.cache_locations() if l[0] in (self.st_checked or set())
                and (st.caches.get(l[0]) or {}).get("old_bytes")]

    def _fill_store_summary(self):
        ui, T, st = self.canvas, Theme, self.app.storage
        if self.st_tab != 0 or not st.scanned:
            ui.itemconfig(self.st_big, text="")
            ui.itemconfig(self.st_sel, text="")
            ui.itemconfig(self.st_btn_img, image=self.st_list.blank)
            ui.itemconfig(self.st_btn_txt, text="")
            return
        total = st.reclaimable()
        sel = sum(st.caches[l[0]]["old_bytes"] for l in self._store_selected())
        big = fmt_size(total)
        ui.itemconfig(self.st_big, text=big)
        ui.coords(self.st_sel, Theme.PAGE_X + 20 + self.st_big_font.measure(big) + 14, 118 + 24)
        ui.itemconfig(self.st_sel, text=f"can be cleaned up  ·  selected: {fmt_size(sel)}")
        armed = self.st_clean_pending
        ui.itemconfig(self.st_btn_img, image=self.g.rr(
            124, 32, 16, T.YELLOW if armed else (T.ACCENT if sel else T.C_TRACK)))
        ui.itemconfig(self.st_btn_txt, text="Confirm?" if armed else "Clean up",
                      fill="#1b1b1b" if armed else (T.C_ON if sel else T.DIM))

    def _store_toggle(self, key):
        if key[0] != "cache":
            return
        chk = set(self.st_checked or set())
        chk.symmetric_difference_update({key[1]})
        self.st_checked = chk
        self.st_clean_pending = None
        self._fill_store()

    def _store_clean_click(self):
        st = self.app.storage
        if self.st_tab != 0 or st.busy:
            return
        sel = self._store_selected()
        if not sel:
            self._store_preview({"title": "Nothing selected",
                                 "detail": "Tick the items you want to clean, then press Clean up.",
                                 "state": ""}, True)
            return
        if self.st_clean_pending:
            self.st_clean_pending = None
            ids = [l[0] for l in sel]
            if st.run(st.clean_many, ids):
                self._poll_store()
            return
        self.st_clean_pending = True
        self.root.after(6000, self._store_unarm)
        total = sum(st.caches[l[0]]["old_bytes"] for l in sel)
        self._store_preview({
            "title": f"Clean {len(sel)} location(s) - {fmt_size(total)}",
            "state": "",
            "detail": "; ".join(f"{l[1]} ({fmt_size(st.caches[l[0]]['old_bytes'])})" for l in sel)
                      + ". Only files older than a day; this cannot be undone."})
        self._fill_store_summary()

    def _store_unarm(self):
        if self.st_clean_pending:
            self.st_clean_pending = None
            self._fill_store_summary()
            self._show_store_last()

    def _store_preview(self, row, info=False):
        ui, T = self.canvas, Theme
        if row is None:
            self._show_store_last()
            return
        ui.itemconfig(self.st_head, text="DETAILS" if info else
                      "PLEASE CONFIRM - press the yellow button again")
        ui.itemconfig(self.st_res_title, text=row["title"][:48] + ("…" if len(row["title"]) > 48 else ""))
        ui.itemconfig(self.st_res_ba, text=row.get("state", ""),
                      fill=T.SUB if info else T.YELLOW)
        ui.itemconfig(self.st_res_msg, text=self._card_text(row, info))

    def _show_store_last(self):
        r = self.app.storage.last
        ui, T = self.canvas, Theme
        ui.itemconfig(self.st_head, text="LAST ACTION")
        if not r:
            ui.itemconfig(self.st_res_title, text="Nothing deleted yet")
            ui.itemconfig(self.st_res_ba, text="")
            ui.itemconfig(self.st_res_msg, text="Sizes are measured first. Nothing is "
                          "removed until you confirm one item.")
            return
        ui.itemconfig(self.st_res_title, text=r["title"][:70])
        ba = f"Before: {r['before']}    After: {r['after']}" if r.get("before") or r.get("after") else ""
        ui.itemconfig(self.st_res_ba, text=ba, fill=T.C_OK if r["ok"] else T.RED)
        ui.itemconfig(self.st_res_msg, text=textwrap.fill(r.get("message", ""), 74))

    def _store_action(self, key):
        st = self.app.storage
        kind = key[0]
        fn = {"cache": lambda: st.run(st.clean_cache, key[1]),
              "recycle": lambda: st.run(st.recycle, key[1]),
              "show": lambda: st.run(st.show, key[1])}[kind]
        if fn():
            self._poll_store()

    def _poll_store(self):
        st = self.app.storage
        if st.busy:
            self.root.after(300, self._poll_store)
            if st.progress and self.st_tab:
                self._fill_store()
            return
        self.st_version = st.version
        self._fill_store()

    def _update_store(self):
        if getattr(self, "st_list", None) is None:
            return
        st = self.app.storage
        if st.version != self.st_version and not st.busy:
            self.st_version = st.version
            self._fill_store()

    # ---- page: diagnostics
    OPEN_TEXT = {"ms-settings:startupapps": "Open Startup Apps",
                 "control powercfg.cpl": "Open Power Options",
                 "ms-settings:storagesense": "Open Storage Sense",
                 "devmgmt.msc": "Open Device Manager",
                 "eventvwr.msc": "Open Event Viewer",
                 "services.msc": "Open Services",
                 "ms-settings:gaming-gamemode": "Open Game Mode",
                 "SystemPropertiesPerformance.exe": "Open Performance options"}

    def _draw_diagnostics(self):
        T, g, ui, app = Theme, self.g, self.canvas, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Diagnostics", "Real problems only - each with proof and a safe fix")
        self.dg_status = g.label(X, 87, "", T.SUB, T.F_SMALL)
        self.dg_btn = ui.create_image(X + W - 120, 72, anchor="nw",
                                      tags=g.tags("dg_scan"),
                                      image=g.rr(120, 28, 14, T.ACCENT))
        self.dg_btn_txt = ui.create_text(X + W - 60, 86, text="Scan now",
                                         fill=T.C_ON, font=T.F_LABEL,
                                         tags=g.tags("dg_scan"))
        ui.tag_bind("dg_scan", "<Button-1>", lambda e: app.scan_now())
        g.hand("dg_scan")
        g.card(X, 108, W, 176)
        self.dg_list = IssueList(g, X, 108, W, self._picked_issue)
        g.card(X, 292, W, 292)
        self.dg_title = g.label(X + 18, 312, "", T.TXT, T.F_HEAD)
        self.dg_sev = g.label(X + 18, 330, "", T.DIM, T.F_SMALL_B)
        self.dg_open_img = ui.create_image(X + W - 18 - 150, 300, anchor="nw",
                                           tags=g.tags("dg_open"),
                                           image=g.rr(150, 28, 14, T.C_TRACK))
        self.dg_open_txt = ui.create_text(X + W - 18 - 75, 314, text="",
                                          fill=T.SUB, font=T.F_LABEL,
                                          tags=g.tags("dg_open"))
        ui.tag_bind("dg_open", "<Button-1>", lambda e: self._open_issue())
        g.hand("dg_open")
        self.dg_table = InfoTable(g, X + 18, 346, W - 36, rows=12, row_h=19,
                                  tag="dgt")
        self.dg_issue = None
        self.dg_version = -1
        self._show_issue(None)

    @staticmethod
    def _fit(lines, n):
        if len(lines) > n:
            lines = lines[:n]
            lines[-1] = lines[-1].rstrip(" .,;")[:-1] + "…"
        return lines

    @classmethod
    def issue_rows(cls, s):
        """Rows of the detail table: proof, meaning, fix (each in a few lines)."""
        if s is None:
            return [("row", "Select a line above to see the proof and the fix", "")]
        wrap = lambda t, k: [("row", "  " + ln, "") for ln in cls._fit(
            textwrap.wrap(t, 70) or [""], k)]
        ev = [("row", "  " + ln, "") for e in s["evidence"]
              for ln in (textwrap.wrap(e, 70) or [""])[:1]]
        if len(ev) > 4:
            ev = ev[:3] + [("row", "  …", "")]
        rows = [("head", "Proof (what was measured)")] + ev
        rows += [("head", "What it means")] + wrap(s["explain"], 3)
        rows += [("head", "Suggested fix")] + wrap(s["fix"], 2)
        return rows

    def _picked_issue(self, s):
        self.dg_issue = s
        self._show_issue(s)

    def _show_issue(self, s):
        ui, T = self.canvas, Theme
        if s is None:
            ui.itemconfig(self.dg_title, text="")
            ui.itemconfig(self.dg_sev, text="")
            ui.itemconfig(self.dg_open_txt, text="")
            ui.itemconfig(self.dg_open_img, state="hidden")
        else:
            col = getattr(T, IssueList.COLORS[s["sev"]])
            ui.itemconfig(self.dg_title, text=s["title"][:52])
            ui.itemconfig(self.dg_sev, text=DiagAnalyzer.SEV_WORD[s["sev"]].upper(),
                          fill=col)
            op = s.get("open")
            ui.itemconfig(self.dg_open_txt, text=self.OPEN_TEXT.get(op, "") if op else "")
            ui.itemconfig(self.dg_open_img, state="normal" if op else "hidden")
        self.dg_table.set(self.issue_rows(s))

    def _open_issue(self):
        s = self.dg_issue
        if s and s.get("open"):
            WinApi.open_target(s["open"])

    def _refresh_diag(self):
        sc = self.app.scanner
        self.dg_version = sc.version
        self.dg_list.set_issues(
            sc.issues, "No scan yet. Press Scan now - it takes about 10 s and "
                       "changes nothing on your PC.")

    def _update_diag(self):
        if getattr(self, "dg_list", None) is None:
            return
        sc, ui, T = self.app.scanner, self.canvas, Theme
        if sc.running:
            text, btn = sc.progress or "Scanning", "Scanning..."
        elif sc.when:
            c = sc.summary or {}
            parts = [f"{c.get(k, 0)} {w}" for k, w in (
                ("warn", "warning(s)"), ("notice", "notice(s)"),
                ("unknown", "unknown"), ("ok", "OK")) if c.get(k)]
            text = ("Last scan " + time.strftime("%H:%M", time.localtime(sc.when))
                    + "  -  " + ", ".join(parts))
            btn = "Scan again"
        else:
            text, btn = "No scan yet", "Scan now"
        if ui.itemcget(self.dg_status, "text") != text:
            ui.itemconfig(self.dg_status, text=text)
        if ui.itemcget(self.dg_btn_txt, "text") != btn:
            ui.itemconfig(self.dg_btn_txt, text=btn)
        if sc.version != self.dg_version:
            self._refresh_diag()

    # ---- page: game sessions
    SESS_TABS = ["Summary", "Findings", "Drops", "Apps", "Compare"]

    def _draw_sessions(self):
        T, g, ui, S, app = Theme, self.g, self.canvas, self.settings, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Sessions", "Every game is recorded - see why it was slow")
        self.sess_status = g.label(X, 87, "", T.SUB, T.F_SMALL)
        g.label(X + W - 58, 87, "Record games", T.DIM, T.F_SMALL, anchor="e")
        self.sess_sw = Switch(g, X + W - 46, 74, bool(S["sessions_on"]),
                              app.set_sessions_on)
        g.card(X, 108, W, SessionList.H)
        self.sess_list = SessionList(g, X, 108, W, self._picked_sessions,
                                     self._delete_sessions)
        dy = 108 + SessionList.H + 8
        g.card(X, dy, 512, 584 - dy)
        self.sess_seg = Segmented(g, X + 12, dy + 10, W - 24, 30, self.SESS_TABS, 0,
                                  self._pick_sess_tab)
        self.sess_tab = 0
        self.sess_sel = []
        self.sess_tables = [InfoTable(g, X + 20, dy + 52, W - 40, rows=10, row_h=20,
                                      tag=f"ss{i}") for i in range(5)]
        self.sess_version = -1
        self.tips.bind("sl_del", "Deletes only the sessions you picked, after a second click. "
                       "Game files are never touched.")
        self.tips.bind("sl_up", "Scroll up")
        self.tips.bind("sl_dn", "Scroll down")
        self._apply_sess_tabs()

    def _apply_sess_tabs(self):
        if self.page != self.PAGE_SESS:
            return
        for i in range(len(self.SESS_TABS)):
            self.canvas.itemconfigure(
                f"ss{i}", state="normal" if i == self.sess_tab else "hidden")

    def _pick_sess_tab(self, i):
        self.sess_tab = i
        self._apply_sess_tabs()
        self._fill_sessions()

    def _picked_sessions(self, sel):
        self.sess_sel = sel
        if len(sel) == 2 and self.sess_tab != 4:      # two chosen: compare
            self.sess_tab = 4
            self.sess_seg.select(4)
        elif len(sel) != 2 and self.sess_tab == 4:
            self.sess_tab = 0
            self.sess_seg.select(0)
        self._apply_sess_tabs()
        self._fill_sessions()

    def _fill_sessions(self):
        sel = [s["summary"] for s in self.sess_sel]
        a = sel[0] if sel else None
        V = SessionView
        rows = [V.rows_summary, V.rows_findings, V.rows_drops, V.rows_apps]
        if self.sess_tab < 4:
            self.sess_tables[self.sess_tab].set(rows[self.sess_tab](a))
        else:
            self.sess_tables[4].set(V.rows_compare(a, sel[1] if len(sel) > 1
                                                   else None))

    def _delete_sessions(self, ids):
        self.app.session_store.delete(ids)
        self.sess_list.sel = []
        self._refresh_sessions()

    def _refresh_sessions(self, first=False):
        self.sess_version = self.app.sessions.version
        self.sess_list.set_sessions(self.app.session_store.list(),
                                    select_newest=first)

    def _update_sessions(self):
        if getattr(self, "sess_list", None) is None:
            return
        rec = self.app.sessions
        text, live = rec.status()
        if self.canvas.itemcget(self.sess_status, "text") != text:
            self.canvas.itemconfig(self.sess_status, text=text,
                                   fill=Theme.C_OK if live else Theme.SUB)
        if rec.version != self.sess_version:
            self._refresh_sessions()

    # ---- page 3: hardware (details)
    def _draw_hardware(self):
        T, g, ui = Theme, self.g, self.canvas
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Hardware", "Real values from your PC - n/a means not available")
        Segmented(g, X, 76, W, 32, [n for n, _ in self.HW_TABS], 0,
                  self._pick_hw_tab)
        g.card(X, 120, W, 464)
        self.hw_tables = []
        for i, _ in enumerate(self.HW_TABS):
            self.hw_tables.append(InfoTable(g, X + 18, 132, W - 36, rows=20,
                                            row_h=22, tag=f"hw{i}"))
        self.hw_tab = 0
        self._apply_hw_tabs()

    def _apply_hw_tabs(self):
        if self.page != self.PAGE_HW:
            return
        for i in range(len(self.HW_TABS)):
            self.canvas.itemconfigure(
                f"hw{i}", state="normal" if i == self.hw_tab else "hidden")

    def _pick_hw_tab(self, i):
        self.hw_tab = i
        self._apply_hw_tabs()
        self._update_hardware()

    # ---- page 3: appearance
    def _draw_appearance(self):
        T, g, ui, S, app = Theme, self.g, self.canvas, self.settings, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Appearance", "Overlay style, background, label colors, opacity")
        self._pics.clear()
        self.look_items = []
        self.look_rings.clear()
        self.bg_rings.clear()
        self.pal_rings.clear()
        # style tiles
        g.card(X, 84, W, 140)
        g.label(X + 16, 104, "STYLE")
        tint = T.overlay_bg(S["bg"])
        for i, (look, name) in enumerate((("dark", "Dark Transparent"),
                                          ("glass", "Liquid Glass"))):
            x, y, tw, th = X + 12 + i * 248, 118, 240, 72
            on = S["look"] == look
            ring = ui.create_image(x - 3, y - 3, anchor="nw",
                                   tags=g.tags(f"look{i}"),
                                   image=g.rr(tw + 6, th + 6, 18,
                                              T.ACCENT if on else T.C_TRACK))
            self.look_rings.append(ring)
            pic = ImageTk.PhotoImage(Overlay.preview(look, tint, T.ACCENT, tw, th))
            self._pics.append(pic)
            self.look_items.append(ui.create_image(
                x, y, anchor="nw", image=pic, tags=g.tags(f"look{i}")))
            ui.create_text(x + tw / 2, y + th + 17, text=name, fill=T.TXT,
                           font=T.F_LABEL, tags=g.tags(f"look{i}"))
            ui.tag_bind(f"look{i}", "<Button-1>", lambda e, i=i: self._pick_look(i))
            g.hand(f"look{i}")
        # background swatches: two rows of five
        g.card(X, 236, W, 132)
        g.label(X + 16, 256, "BACKGROUND")
        for i, (key, name, _) in enumerate(T.OVERLAY_BGS):
            x, y = X + 19 + (i % 5) * 98, 272 + (i // 5) * 48
            on = S["bg"] == key
            self.bg_rings[key] = ui.create_image(
                x - 3, y - 3, anchor="nw", tags=g.tags(f"bg_{key}"),
                image=g.rr(96, 44, 15, T.ACCENT if on else T.C_TRACK))
            ui.create_image(x, y, anchor="nw", tags=g.tags(f"bg_{key}"),
                            image=g.rr(90, 38, 12, T.overlay_bg(key)))
            ui.create_text(x + 45, y + 19, text=name, fill="#f2f2f5",
                           font=T.F_LABEL, tags=g.tags(f"bg_{key}"))
            ui.tag_bind(f"bg_{key}", "<Button-1>",
                        lambda e, k=key: self._pick_bg(k))
            g.hand(f"bg_{key}")
        # label color palettes
        g.card(X, 380, W, 76)
        g.label(X + 16, 400, "LABEL COLORS")
        for i, (key, name, cols) in enumerate(T.OVERLAY_PALETTES):
            x, y = X + 19 + i * 80, 414
            on = S["palette"] == key
            self.pal_rings[key] = ui.create_image(
                x - 3, y - 3, anchor="nw", tags=g.tags(f"pal_{key}"),
                image=g.rr(80, 44, 15, T.ACCENT if on else T.C_TRACK))
            ui.create_image(x, y, anchor="nw", tags=g.tags(f"pal_{key}"),
                            image=g.rr(74, 38, 12, T.lift(T.C_CARD, 0.06)))
            ui.create_text(x + 37, y + 11, text=name, fill=T.TXT,
                           font=T.F_SMALL_B, tags=g.tags(f"pal_{key}"))
            colors = list((cols or {}).values()) or [
                T.WHITE, app.gpu.brand_color(), app.cpu.brand_color(),
                T.GRAY, T.NET_COLOR]
            for j, col in enumerate(colors[:5]):
                cx = x + 37 + (j - 2) * 11
                ui.create_image(cx - 4, y + 25, anchor="nw",
                                image=g.rr(8, 8, 4, col),
                                tags=g.tags(f"pal_{key}"))
            ui.tag_bind(f"pal_{key}", "<Button-1>",
                        lambda e, k=key: self._pick_palette(k))
            g.hand(f"pal_{key}")
        self.blur_id = g.label(X, 472, "", T.DIM, T.F_SMALL, width=W)

    def _pick_look(self, i):
        self.settings["look"] = Settings.LOOKS[i]
        for n, ring in enumerate(self.look_rings):
            self.canvas.itemconfig(ring, image=self.g.rr(
                246, 78, 18, Theme.ACCENT if n == i else Theme.C_TRACK))
        self.app.set_look(i)
        self.update_status()

    def _pick_bg(self, key):
        for k, ring in self.bg_rings.items():
            self.canvas.itemconfig(ring, image=self.g.rr(
                96, 44, 15, Theme.ACCENT if k == key else Theme.C_TRACK))
        self.app.set_background(key)
        # redraw the two preview pictures with the new tint
        tint = Theme.overlay_bg(key)
        for i, look in enumerate(Settings.LOOKS):
            self._pics[i] = ImageTk.PhotoImage(
                Overlay.preview(look, tint, Theme.ACCENT, 240, 72))
            self.canvas.itemconfig(self.look_items[i], image=self._pics[i])

    def _pick_palette(self, key):
        for k, ring in self.pal_rings.items():
            self.canvas.itemconfig(ring, image=self.g.rr(
                80, 44, 15, Theme.ACCENT if k == key else Theme.C_TRACK))
        self.app.set_palette(key)

    # ---- page 8: personalize (the look of the whole app)
    def _draw_personalize(self):
        T, g, ui, S, app = Theme, self.g, self.canvas, self.settings, self.app
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Personalize", "Choose how Lmonitor itself looks")
        self._tprev = []
        self.theme_rings.clear()
        self.acc_rings.clear()
        g.card(X, 84, W, 328)
        g.label(X + 16, 104, "APP THEME")
        for i, (key, name, note, spec) in enumerate(T.UI_THEMES):
            x = X + 12 + (i % 2) * 248
            y = 122 + (i // 2) * 144
            tw, th = 240, 98
            on = S["ui_theme"] == key
            ring = ui.create_image(x - 3, y - 3, anchor="nw",
                                   tags=g.tags(f"th_{key}"),
                                   image=g.rr(tw + 6, th + 6, 18,
                                              T.ACCENT if on else T.C_TRACK))
            self.theme_rings[key] = ring
            acc = self._theme_accent(spec)
            pic = ImageTk.PhotoImage(ThemePreview.render(spec, acc, tw, th))
            self._tprev.append(pic)
            ui.create_image(x, y, anchor="nw", image=pic, tags=g.tags(f"th_{key}"))
            ui.create_text(x + 4, y + th + 16, text=name, anchor="w", fill=T.TXT,
                           font=T.F_HEAD, tags=g.tags(f"th_{key}"))
            ui.create_text(x + 4, y + th + 33, text=note, anchor="w", fill=T.DIM,
                           font=T.F_SMALL, tags=g.tags(f"th_{key}"))
            ui.tag_bind(f"th_{key}", "<Button-1>",
                        lambda e, k=key: self._pick_theme(k))
            g.hand(f"th_{key}")
        g.card(X, 424, W, 112)
        g.label(X + 16, 444, "ACCENT COLOR")
        for i, (key, name, col) in enumerate(T.UI_ACCENTS):
            x, y = X + 19 + i * 68, 462
            on = S["ui_accent"] == key
            self.acc_rings[key] = ui.create_image(
                x - 3, y - 3, anchor="nw", tags=g.tags(f"ac_{key}"),
                image=g.rr(68, 44, 15, T.ACCENT if on else T.C_TRACK))
            ui.create_image(x, y, anchor="nw", tags=g.tags(f"ac_{key}"),
                            image=g.rr(62, 38, 12, col or T.lift(T.C_CARD, 0.06)))
            ui.create_text(x + 31, y + 19, text=name,
                           fill=T.TXT if col is None else Theme._on_color(col),
                           font=T.F_SMALL_B, tags=g.tags(f"ac_{key}"))
            ui.tag_bind(f"ac_{key}", "<Button-1>",
                        lambda e, k=key: self._pick_accent(k))
            g.hand(f"ac_{key}")
        g.label(X + 16, 520, "Auto = the theme's own color (your GPU's brand "
                "color for Default, Night and Day).", T.DIM, T.F_SMALL,
                width=W - 32)

    @staticmethod
    def _theme_accent(spec):
        """Accent the theme card shows (what the theme would really use)."""
        return spec["accent"] or Theme.VENDOR["accent"]

    def _pick_theme(self, key):
        if key != self.settings["ui_theme"]:
            self.app.set_ui_style(theme=key)

    def _pick_accent(self, key):
        if key != self.settings["ui_accent"]:
            self.app.set_ui_style(accent=key)

    def restyle(self):
        """The app theme / accent changed: redraw the whole window."""
        T = Theme
        self.root.configure(bg=T.C_BG)
        self.canvas.configure(bg=T.C_BG)
        self.g._img.clear()          # old colors; every item is redrawn below
        self.draw()
        WinApi.dark_titlebar(self.root, not T.LIGHT, T.C_BG)
        if self.is_open:
            self.app.sample_now()
            self.update_status()

    # ---- page 5: order
    def _draw_order(self):
        T, g, S = Theme, self.g, self.settings
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Order", "Drag a row up or down to change the overlay order")
        half = (W - 16) // 2
        shown = lambda: self.page == self.PAGE_ORDER
        g.card(X, 84, half, 340)
        g.label(X + 16, 104, "SECTIONS")
        self.order_groups = ReorderList(
            g, X + 12, 124, half - 24, self._group_rows(),
            self._on_group_order, is_visible=shown)
        x2 = X + half + 16
        g.card(x2, 84, half, 340)
        g.label(x2 + 16, 104, "ITEMS IN")
        Segmented(g, x2 + 16, 120, half - 32, 32,
                  [n for n, _ in Metrics.GROUPS], 0, self._pick_order_group)
        self.order_group = Metrics.GROUPS[0][0]
        self.order_items = ReorderList(
            g, x2 + 12, 166, half - 24, self._item_rows(self.order_group),
            self._on_item_order, is_visible=shown)

    def _group_rows(self):
        show = self.settings.show
        return [(n, n, any(show[k] for k, _, _ in items))
                for n, items in Metrics.ordered(self.settings["order"])]

    def _item_rows(self, group):
        show = self.settings.show
        by = dict(Metrics.ordered(self.settings["order"]))
        return [(k, label, show[k]) for k, label, _ in by[group]]

    def _refresh_order(self):
        if self.order_groups is not None:
            self.order_groups.set_rows(self._group_rows())
            self.order_items.set_rows(self._item_rows(self.order_group))

    def _pick_order_group(self, i):
        self.order_group = Metrics.GROUPS[i][0]
        self.order_items.set_rows(self._item_rows(self.order_group))

    def _on_group_order(self, names):
        self.app.set_order(groups=names)

    def _on_item_order(self, keys):
        self.app.set_order(group=self.order_group, items=keys)

    # ---- page 3: metrics
    def _draw_metrics(self):
        T, g, S = Theme, self.g, self.settings
        X, W = T.PAGE_X, T.PAGE_W
        g.title("Metrics", "Choose what the overlay shows")
        half = (W - 16) // 2
        y = 84
        for row in (Metrics.GROUPS[0:2], Metrics.GROUPS[2:4],
                    Metrics.GROUPS[4:5]):
            tallest = 0
            for col, (gname, items) in enumerate(row):
                x = X + col * (half + 16)
                h = 52 + ((len(items) + 1) // 2) * 36 + 6
                if gname == "NET":
                    h += 44                      # room for the unit selector
                tallest = max(tallest, h)
                g.card(x, y, half, h)
                g.label(x + 16, y + 26, gname, T.TXT, T.F_HEAD)
                self.group_sw[gname] = Switch(
                    g, x + half - 16 - 46, y + 13,
                    any(S.show[k] for k, _, _ in items),
                    lambda on, nm=gname: self.toggle_group(nm, on))
                for i, (key, text, _) in enumerate(items):
                    self.chips[key] = Chip(
                        g, S, x + 12 + (i % 2) * (Chip.W + 8),
                        y + 52 + (i // 2) * 36, text, key, self.toggle_key)
                if gname == "NET":
                    sy = y + 52 + ((len(items) + 1) // 2) * 36 + 4
                    self.net_seg = Segmented(
                        g, x + 12, sy, half - 24, 32, ["MB/s", "Mbps"],
                        0 if S["net_unit"] == "bytes" else 1,
                        self.app.set_net_unit)
            y += tallest + 16

    # ---- slider callbacks (update the number, then tell the app)
    def _on_text(self, v):
        self.canvas.itemconfig(self.text_val, text=f"{v} pt")
        self.app.set_text_size(v)

    def _on_graph(self, v):
        self.canvas.itemconfig(self.graph_val, text=f"{v}%")
        self.app.set_graph_size(v)

    def _on_alpha(self, v):
        self.canvas.itemconfig(self.alpha_val, text=f"{v}%")
        self.app.set_opacity(v)

    # ---- metric toggles
    def toggle_key(self, key):
        show = self.settings.show
        show[key] = not show[key]
        self.chips[key].refresh()
        group = Metrics.group_of(key)
        items = Metrics.items(group)
        self.group_sw[group].set(any(show[k] for k, _, _ in items))
        self._refresh_order()
        self.app.metrics_changed()

    def toggle_group(self, group, on):
        show = self.settings.show
        for k, _, _ in Metrics.items(group):
            show[k] = on
            self.chips[k].refresh()
        self._refresh_order()
        self.app.metrics_changed()

    # ---- pages
    def show_tab(self, i):  # kept for older callers
        self.show_page(i)

    def show_page(self, i, animate=True):
        ui = self.canvas
        self._finish_slide()
        self.tips.hide()
        if self._visible is None:          # after a (re)draw: set every page
            for n, (name, _) in enumerate(self.PAGES):
                ui.itemconfigure(f"p_{name}",
                                 state="normal" if n == i else "hidden")
        elif self._visible != i:           # normally only two pages change
            ui.itemconfigure(f"p_{self.PAGES[self._visible][0]}", state="hidden")
            ui.itemconfigure(f"p_{self.PAGES[i][0]}", state="normal")
        self._visible = i
        self.page = i
        self._apply_hw_tabs()
        self._apply_sess_tabs()
        if i == self.PAGE_ORDER:
            self._refresh_order()
        if i == self.PAGE_SESS and self.is_open:
            self._refresh_sessions(first=True)
        if i == self.PAGE_DIAG and self.is_open:
            self._refresh_diag()
            self._update_diag()
        if i == self.PAGE_OPT and self.is_open:
            opt = self.app.optimizer
            opt.run(opt.refresh)
            self._poll_opt()
        if i == self.PAGE_REPORT and self.is_open:
            self.app.reports.run(self.app.reports.build)
            self._poll_report()
        if i == self.PAGE_STORE and self.is_open:
            st = self.app.storage
            if not st.scanned:
                st.run(st.scan_caches)
            self._poll_store()
        if self.nav is not None and self.nav.index != i:
            self.nav.select(i)
        if animate and self.SLIDE:
            self._start_slide(f"p_{self.PAGES[i][0]}")
        if self.is_open and i in (0, self.PAGE_PERF, self.PAGE_HW):
            self.app.sample_now()  # fresh numbers (read in the background)
        if i == 0 and self.is_open:
            self.update_status()

    def _finish_slide(self):
        if self.slide_job:
            self.canvas.after_cancel(self.slide_job)
            self.slide_job = None
        if self.slide:
            tag, left = self.slide
            self.canvas.move(tag, -left, 0)
            self.slide = None

    def _start_slide(self, tag, dist=18, steps=7):
        ui = self.canvas
        ui.move(tag, dist, 0)
        self.slide = (tag, dist)
        i = [0]

        def step():
            i[0] += 1
            left = dist * (1 - Gfx.ease(i[0] / steps))
            tag_, old = self.slide
            ui.move(tag_, left - old, 0)
            self.slide = (tag_, left)
            if i[0] < steps:
                self.slide_job = ui.after(16, step)
            else:
                self.slide_job = None
                self.slide = None
        self.slide_job = ui.after(16, step)

    # ---- window
    def show(self):
        r = self.root
        if self.first_show:
            self.first_show = False
            sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
            W, H = Theme.WIN_W, Theme.WIN_H
            r.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
        r.deiconify()
        r.update_idletasks()
        WinApi.dark_titlebar(r, not Theme.LIGHT, Theme.C_BG)
        r.lift()
        r.attributes("-topmost", True)
        r.after(300, lambda: r.attributes("-topmost", False))
        self.is_open = True
        self.update_status()

    def hide(self, event=None):
        if self.app.moving:
            self.app.set_moving(False)
        self.settings.save()
        self.is_open = False
        self.root.withdraw()

    # ---- live data
    def _set(self, key, text=None, fill=None):
        """Change a text item only when it really changed."""
        ui, item = self.canvas, self.live[key]
        if text is not None and ui.itemcget(item, "text") != text:
            ui.itemconfig(item, text=text)
        fill = Theme.ui_color(fill) if fill is not None else None
        if fill is not None and ui.itemcget(item, "fill") != fill:
            ui.itemconfig(item, fill=fill)

    def _dot(self, key, color):
        self.canvas.itemconfig(self.live[f"{key}_dot"],
                               image=self.g.rr(8, 8, 4, color))

    @staticmethod
    def _bar_color(pct):
        c = Thresholds.use(pct)
        return Theme.ACCENT if c == Theme.WHITE else c

    def update_status(self):
        app, ui = self.app, self.canvas
        app.driver.poll()
        note = app.driver.notice()
        if ui.itemcget(self.driver_id, "text") != note:
            ui.itemconfig(self.driver_id, text=note)
        if self.live:
            self._update_hero()
        if self.page == self.PAGE_SESS:
            self._update_sessions()
        if self.page == self.PAGE_DIAG:
            self._update_diag()
        if self.page == self.PAGE_OPT:
            self._update_opt()
        if self.page == self.PAGE_STORE:
            self._update_store()
        if self.page == self.PAGE_REPORT:
            self._update_report()
        if self.blur_id is not None:
            S, o = self.settings, app.overlay
            if S["look"] != "glass":
                text = ""
            elif o.glass_ok:
                text = "Liquid Glass: Windows blur is on"
            else:
                text = ("Blur is not available on this Windows - using a "
                        "translucent dark bar instead")
            if ui.itemcget(self.blur_id, "text") != text:
                ui.itemconfig(self.blur_id, text=text)

    def on_sample(self):
        """New telemetry arrived: refresh the page that is open."""
        if not self.is_open:
            return
        if self.page == 0:
            self._update_dashboard()
        elif self.page == self.PAGE_PERF:
            self._update_charts()
        elif self.page == self.PAGE_HW:
            self._update_hardware()

    def _update_hero(self):
        app, S, T = self.app, self.settings, Theme
        on = bool(S["on"])
        if self.overlay_sw is not None:
            self.overlay_sw.set(on)
        if not on:
            text, dot = "Overlay hidden", T.DIM
        elif not app.overlay.has_content:
            text, dot = "No metrics selected", T.YELLOW
        elif app.overlay.need.get("FPS") and not app.fps.alive:
            text, dot = self._fit("FPS: " + app.fps.status.replace(
                "PresentMon.exe not found", "PresentMon missing"), 26), T.YELLOW
        else:
            text, dot = "Monitoring Active", T.C_OK
        self._set("hero", text)
        self.canvas.itemconfig(self.live["dot"], image=self.g.rr(10, 10, 5, dot))
        last = app.telemetry._last
        self._set("upd", "Last update  " + time.strftime("%H:%M:%S",
                  time.localtime(last)) if last else "Last update  --")

    @staticmethod
    def _fit(text, n=20):
        return text if len(text) <= n else text[:n - 1] + "…"

    def _update_perf(self):
        if self.perf is None:
            return
        app = self.app
        sec = PerfChart.RANGES[self.range_idx][1]
        if self.range_idx == 0:      # live samples (as often as Refresh)
            h = app.telemetry.history
            n = max(8, int(sec / app.telemetry.interval))
            series = [list(h[k])[-n:] for k in ("c_use", "r_use", "g_use")]
            self.perf.update(series, n, app.telemetry.interval)
        else:
            series = app.recorder.series(sec)
            self.perf.update(series)

    def _update_dashboard(self):
        app, tel = self.app, self.app.telemetry
        s = tel.snap
        if not s or not self.gauges:
            return
        self._update_hero()
        h = tel.history
        T_ = Theme
        t, temp, vm = s["c_temp"], s["g_temp"], s["vm"]

        heat = CardStatus.heat
        cpu_sub = f"{t:.0f}°C" if t is not None else "no temperature"
        c = s["c_clk"]
        cpu_sub2 = f"{'~' if s['c_approx'] else ''}{c / 1000:.1f} GHz" if c else ""
        self.gauges["cpu"].update(s["c_use"], cpu_sub, cpu_sub2,
                                  heat(s["c_use"], t, SessionAnalyzer.CPU_HOT), h["c_use"])
        gsub = f"{temp:.0f}°C" if temp is not None else "no temperature"
        gclk = (f"{s['g_clk'] / 1000:.1f} GHz" if s["g_clk"] and s["g_clk"] >= 1000
                else f"{s['g_clk']:.0f} MHz" if s["g_clk"] is not None else "")
        gsub2 = " · ".join(x for x in ((f"{s['g_pow']:.0f} W" if s["g_pow"] is not None else ""), gclk) if x)
        self.gauges["gpu"].update(s["g_use"], gsub, gsub2,
                                  heat(s["g_use"], temp, SessionAnalyzer.GPU_HOT), h["g_use"])
        ru = s["r_use"]
        self.gauges["ram"].update(
            ru, f"{vm.used / 1024**3:.1f} / {vm.total / 1024**3:.0f} GB",
            "", CardStatus.ram(ru), h["r_use"])
        rows = tel.storage._rows
        if rows:
            d = rows[0]
            disk = tel.info.disk_for(d["mount"])
            kind = tel.info.disk_kind(disk) if disk else ""
            free_pct = 100 - d["pct"]
            st = CardStatus.disk(free_pct)
            self.gauges["disk"].update(d["pct"], f"{d['free'] / 1024**3:.0f} GB free",
                                       d["mount"].rstrip("\\") + (f" · {kind}" if kind else ""), st)
        else:
            self.gauges["disk"].update(None, "", "", "none")
        self._update_perf()
        sc = ReportBuilder.score(self.app.scanner.issues)
        self._set("score", "--" if sc["value"] is None else f"{sc['value']}")
        self._set("score_sub", "Health score - run a scan" if sc["value"] is None else
                  f"Health score · {sc['covered']} of {sc['total']} areas")
        self._set("st_cpu", "OK" if t is not None else "Unavailable",
                  T_.C_OK if t is not None else T_.YELLOW)
        self._set("st_gpu", "OK" if temp is not None else "Unavailable",
                  T_.C_OK if temp is not None else T_.YELLOW)
        fps = self.app.fps
        self._set("st_fps", "Ready" if fps.alive else
                  ("Missing" if "not found" in (fps.status or "") else "Idle"),
                  T_.C_OK if fps.alive else T_.YELLOW if "not found" in (fps.status or "") else T_.DIM)
        unit = self.settings["net_unit"]
        self._set("net_d", fmt_net(s["net_down"], unit))
        self._set("net_u", fmt_net(s["net_up"], unit))
        self.sparks["net"].update(list(h["net_down"])[-Spark.N:], vmax=None)

    def _update_charts(self):
        tel = self.app.telemetry
        for key, fmt, chart in self.charts:
            vals = list(tel.history[key])
            last = vals[-1] if vals else None
            chart.update([vals], fmt(last) if last is not None else "n/a")
        down, up = tel.history["net_down"], tel.history["net_up"]
        d = down[-1] if down else None
        u = up[-1] if up else None
        self.net_chart.update(
            [list(down), list(up)],
            f"↓ {fmt_rate(d)}  ↑ {fmt_rate(u)}" if d is not None else "n/a")
        text = (f"Updates every {int(tel.interval)} s · last {Telemetry.HISTORY}"
                f" samples · one update takes {tel.sample_ms:.0f} ms")
        if self.canvas.itemcget(self.perf_info, "text") != text:
            self.canvas.itemconfig(self.perf_info, text=text)

    def _update_hardware(self):
        name, method = self.HW_TABS[self.hw_tab]
        self.hw_tables[self.hw_tab].set(getattr(self.app.telemetry, method)())

    # ---- position / move mode
    def sync_position(self):
        """Show the real position + move state (after a drag or a reset)."""
        if self.pos_seg is not None:
            i = Settings.POS.index(self.settings["pos"])
            self.pos_seg.select(i if i < 3 else -1)
        self.update_move_button()

    def update_move_button(self):
        if self.move_img is None:
            return
        on = self.app.moving
        self.canvas.itemconfig(self.move_img, image=self.g.rr(
            150, 40, 20, Theme.ACCENT if on else Theme.C_TRACK))
        self.canvas.itemconfig(self.move_txt, text="Done" if on else
                               "Move with mouse",
                               fill=Theme.C_ON if on else Theme.SUB)
        self.canvas.itemconfig(
            self.move_hint, text="Drag the bar, then right-click it or press Done"
            if on else "")

    def flash_report(self, msg):
        try:
            self.canvas.itemconfig(self.report_id, text=msg)
            self.root.after(4000, lambda: self.canvas.itemconfig(
                self.report_id, text=self.REPORT_TEXT))
        except Exception:
            pass


# =============================================================== TrayIcon
class TrayIcon:
    def __init__(self, app):
        self.app = app
        self.image = self.make_image()
        self.icon = pystray.Icon(
            "Lmonitor", self.image, "Lmonitor",
            menu=pystray.Menu(
                pystray.MenuItem("Open Lmonitor", self._settings, default=True),
                pystray.MenuItem("Show overlay", self._toggle,
                                 checked=lambda item: app.settings["on"]),
                pystray.MenuItem("Save sensor report", self._report),
                pystray.MenuItem("Exit", self._exit),
            ))

    @staticmethod
    def make_image():
        return Logo.render(64, Theme.ACCENT)

    def start(self):
        threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self):
        self.icon.stop()

    # menu callbacks run on the tray thread -> hand over to the Tk thread
    def _settings(self, icon=None, item=None):
        self.app.root.after(0, self.app.window.show)

    def _toggle(self, icon=None, item=None):
        self.app.root.after(0, self.app.set_overlay, not self.app.settings["on"])

    def _report(self, icon=None, item=None):
        self.app.root.after(0, self.app.save_report)

    def _exit(self, icon=None, item=None):
        self.app.root.after(0, self.app.quit)  # tray runs in its own thread


# =============================================================== App
class App:
    """Creates every part, connects them and runs the timers."""

    def __init__(self):
        self.settings = Settings()
        self.moving = False
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.report_callback_exception = self._tk_error

        self.host = LibreHardwareHost()
        self.cpu = CpuReader(self.host)
        self.gpu = GpuReader(self.host)
        Theme.apply_vendor(self.gpu.vendor())  # before any window is drawn
        Theme.apply_ui(self.settings["ui_theme"], self.settings["ui_accent"])
        self.memory = MemoryReader()
        self.fps = FpsMonitor()
        self.recorder = Recorder(self.gpu)
        self.session_store = SessionStore()
        self.session_store.clear_live()
        self.scanner = DiagRunner(ScanStore())
        self.change_log = ChangeLog()
        self.optimizer = Optimizer(self.change_log)
        self.storage = Storage(self.change_log)
        self.reports = Reports(self.scanner.store, self.session_store, self.change_log)
        self.sessions = SessionRecorder(self.fps, self.cpu, self.gpu,
                                        self.session_store,
                                        lambda: self.settings["sessions_on"])

        self.displays = DisplayManager(self.root)
        self.overlay = Overlay(self.root, self.settings, self.group_colors(),
                               self.displays)
        self.telemetry = Telemetry(self.host, self.cpu, self.gpu, self.memory)
        self.telemetry.set_interval(self.settings["refresh"])
        self.telemetry.is_admin = lambda: WinApi.admin
        self.telemetry.driver_ok = lambda: self.driver.ok
        self.updater = MetricsUpdater(self.settings, self.overlay, self.cpu,
                                      self.gpu, self.memory, self.fps)
        self.driver = DriverManager(self)
        self.diagnostics = Diagnostics(self)
        self.reveal = RevealController(self)
        self.overlay.on_move_end = self._moved
        self.overlay.on_move_done = lambda: self.set_moving(False)
        self.window = SettingsWindow(self)
        self.tray = TrayIcon(self)
        # window + taskbar icon (several sizes, references kept)
        self._icons = [Logo.photo(n, Theme.ACCENT) for n in (256, 48, 32, 16)]
        self.root.iconphoto(True, *self._icons)

        self.shown = False
        self._sampling = self._sample_done = False
        self._tick = 0
        self._dtick = 0
        self._pending = {}

    def group_colors(self):
        """Overlay label color of every group (palette or the GPU/CPU brand)."""
        cols = {"FPS": Theme.WHITE, "GPU": self.gpu.brand_color(),
                "CPU": self.cpu.brand_color(), "RAM": Theme.GRAY,
                "NET": Theme.NET_COLOR}
        cols.update(Theme.palette(self.settings["palette"]) or {})
        return cols

    @staticmethod
    def _tk_error(exc, val, tb):
        Logger.error("tk callback",
                     "".join(traceback.format_exception(exc, val, tb)))

    # ---- scheduling
    def schedule(self, key, fn, delay=40):
        """Run fn once after a short delay (collapses rapid changes)."""
        if key in self._pending:
            return

        def run():
            self._pending.pop(key, None)
            try:
                fn()
            except Exception:
                Logger.error(key)
        self._pending[key] = self.root.after(delay, run)

    # ---- overlay state
    def apply_state(self):
        """Show/hide the overlay and start/stop PresentMon as needed."""
        self.shown = bool(self.settings["on"] and self.overlay.has_content)
        hotkey = (self.settings["show_mode"] == "hotkey" and not self.moving)
        if self.shown and hotkey:
            if self.reveal.active:
                self.overlay.show()         # a slide is running: re-place it
            else:
                self.overlay.slide = 0.0
                self.overlay.hide()         # waits for F9
        else:
            self.reveal.reset()             # always visible (or off): in place
            if self.shown:
                self.overlay.show()
            else:
                self.overlay.hide()
        if (self.shown and self.overlay.need.get("FPS")) \
                or self.settings["sessions_on"]:
            self.fps.start()    # the overlay or the session recorder needs it
        else:
            self.fps.stop()

    def overlay_visible(self):
        """Is the bar on screen now (so it is worth updating)?"""
        return self.shown and (self.settings["show_mode"] == "always"
                               or self.moving or self.reveal.active)

    def refresh(self):
        if self.overlay_visible():
            self.updater.update_system()
            if self.overlay.need.get("FPS"):
                self.updater.update_fps()

    def rebuild(self):
        self.overlay.build()
        if self.settings.show["c_use"]:
            self.cpu.usage()  # prime the counter
        self.apply_state()
        self.refresh()

    def set_overlay(self, on):
        self.settings["on"] = on
        self.apply_state()
        self.refresh()
        self.settings.save()

    # ---- actions from the settings window
    def set_position(self, i):
        if self.moving:
            self.set_moving(False)
        pos = Settings.POS[i]
        if pos == "custom" and self.settings["x"] is None:
            self.overlay.place()  # start from where the bar is now
            self.settings["x"], self.settings["y"] = self.overlay.relative()
        self.settings["pos"] = pos
        self.overlay.invalidate()
        if self.shown:
            self.overlay.place()
        self.schedule("save", self.settings.save, 300)

    def set_moving(self, on):
        """Move mode: drag the bar with the mouse (click-through is off)."""
        on = bool(on)
        if on:
            if not self.overlay.has_content:
                return False
            self.settings["on"] = True
            if self.settings["pos"] != "custom" or self.settings["x"] is None:
                self.overlay.place()
                self.settings["x"], self.settings["y"] = self.overlay.relative()
                self.settings["pos"] = "custom"
        self.moving = self.overlay.moving = on
        self.rebuild()
        if not on:
            self.settings.save()
        self.window.sync_position()
        return True

    def _moved(self, x, y):
        """The bar was dropped somewhere: remember it (display + offset)."""
        self.settings["x"], self.settings["y"] = self.overlay.relative()
        self.settings["pos"] = "custom"
        self.schedule("save", self.settings.save, 300)
        self.window.sync_position()

    def set_monitor(self, name):
        """Show the overlay on "primary" or on one display (device name)."""
        self.settings["monitor"] = name
        self.overlay.invalidate()
        if self.shown:
            self.overlay.place()
        self.window.rebuild_screens()
        self.schedule("save", self.settings.save, 300)

    def set_refresh(self, i):
        """How often the window's live data and charts update (1 / 2 / 5 s)."""
        self.settings["refresh"] = Settings.REFRESH[i]
        self.telemetry.set_interval(self.settings["refresh"])
        self.schedule("save", self.settings.save, 300)

    def sample_now(self, wait=False):
        """Read the sensors once and update the open page.

        The reading runs in a worker thread so the window never freezes
        (wait=True reads on the spot - used by tests and the report).
        """
        if wait:
            try:
                self.telemetry.sample()
                self.window.on_sample()
            except Exception:
                Logger.error("sample")
            return
        if self._sampling:
            return
        self._sampling, self._sample_done = True, False

        def work():
            try:
                self.telemetry.sample()
            except Exception:
                Logger.error("sample")
            finally:
                self._sample_done = True
        threading.Thread(target=work, daemon=True).start()
        self.root.after(25, self._sample_wait)

    def _sample_wait(self):
        """Back on the UI thread: show the numbers once the worker is done."""
        if not self._sample_done:
            self.root.after(25, self._sample_wait)
            return
        self._sampling = False
        try:
            self.window.on_sample()
        except Exception:
            Logger.error("sample show")

    def set_palette(self, key):
        self.settings["palette"] = key
        self.overlay.colors.update(self.group_colors())
        self.schedule("rebuild", self.rebuild)
        self.schedule("save", self.settings.save, 300)

    def scan_now(self):
        """'Scan now': read the facts in a worker thread (changes nothing)."""
        if self.scanner.start():
            self.window._update_diag()

    def set_show_mode(self, i):
        self.settings["show_mode"] = ("always", "hotkey")[i]
        self.apply_state()
        self.refresh()
        self.window.update_reveal_hint()
        self.schedule("save", self.settings.save, 300)

    def set_hotkey_secs(self, i):
        self.settings["hotkey_secs"] = (3, 5, 10)[i]
        self.schedule("save", self.settings.save, 300)

    def try_reveal(self):
        """'Try it now' button: same as pressing F9."""
        if not self.reveal.press():
            self.window.update_reveal_hint(True)

    def set_sessions_on(self, on):
        self.settings["sessions_on"] = bool(on)
        if not on:
            self.sessions.stop()        # save what was recorded so far
        self.apply_state()
        self.schedule("save", self.settings.save, 300)

    def set_net_unit(self, i):
        self.settings["net_unit"] = ("bytes", "bits")[i]
        self.schedule("save", self.settings.save, 300)

    def set_ui_style(self, theme=None, accent=None):
        """Change the theme / accent of the whole app window."""
        if theme is not None:
            self.settings["ui_theme"] = theme
        if accent is not None:
            self.settings["ui_accent"] = accent

        def apply():
            Theme.apply_ui(self.settings["ui_theme"], self.settings["ui_accent"])
            self._icons = [Logo.photo(n, Theme.ACCENT) for n in (256, 48, 32, 16)]
            self.root.iconphoto(True, *self._icons)
            self.window.restyle()
            if self.settings["bg"] == "accent":   # its tint follows the accent
                self.rebuild()
        self.root.after(10, apply)  # after the click that asked for it
        self.schedule("save", self.settings.save, 300)

    def _displays_changed(self):
        """A monitor was plugged / unplugged or its resolution changed."""
        self.overlay.invalidate()
        if self.shown:
            self.overlay.place()  # moves to Primary if the chosen one is gone
        self.window.rebuild_screens()

    def set_look(self, i):
        self.settings["look"] = Settings.LOOKS[i]
        self.schedule("rebuild", self.rebuild)
        self.schedule("save", self.settings.save, 300)

    def set_background(self, key):
        self.settings["bg"] = key
        self.schedule("rebuild", self.rebuild)
        self.schedule("save", self.settings.save, 300)

    def set_order(self, groups=None, group=None, items=None):
        """New order of the sections and/or of the items inside one section."""
        order = deepcopy(self.settings["order"])
        if groups:
            order["groups"] = list(groups)
        if group and items:
            order["items"][group] = list(items)
        self.settings["order"] = Metrics.clean_order(order)
        self.schedule("rebuild", self.rebuild)
        self.schedule("save", self.settings.save, 300)

    def set_layout(self, i):
        self.settings["layout"] = "h" if i == 0 else "v"
        self.schedule("rebuild", self.rebuild)
        self.schedule("save", self.settings.save, 300)

    # ---- density, value color and profiles
    def _apply_look_all(self):
        self.overlay.colors.update(self.group_colors())
        self.overlay.apply_font()
        self.overlay.set_alpha(self.settings["alpha"])
        self.window.draw()
        self.rebuild()
        self.settings.save()

    def set_density(self, key):
        show = Profiles.density_show(key)
        if show is None:
            return
        self.settings.data["show"] = show
        self.rebuild()
        self.window.refresh_profiles()
        self.schedule("save", self.settings.save, 300)

    def set_value_color(self, key):
        self.settings["value_color"] = key
        self.rebuild()
        self.window.refresh_profiles()
        self.schedule("save", self.settings.save, 300)

    def set_font(self, font=None, weight=None, label_weight=None):
        """Overlay font family / weight, live; saved a moment later."""
        if font is not None:
            self.settings["font"] = font
        if weight in ("normal", "bold"):
            self.settings["weight"] = weight
        if label_weight in ("normal", "bold"):
            self.settings["label_weight"] = label_weight

        def apply():
            self.overlay.apply_font()
            if self.shown:
                self.overlay.place()
            self.window.refresh_typography()
        self.schedule("font", apply)
        self.schedule("save", self.settings.save, 300)

    def set_text_size(self, v):
        self.settings["text"] = v

        def apply():
            self.overlay.set_font_size(self.settings["text"])
            if self.shown:
                self.overlay.place()
        self.schedule("text", apply)

    def set_graph_size(self, v):
        self.settings["graph"] = v

        def apply():
            if self.overlay.canvas is not None:
                self.overlay.resize_graph()
                self.overlay.invalidate()
                self.overlay.place()
        self.schedule("graph", apply)

    def set_opacity(self, v):
        self.settings["alpha"] = v
        self.schedule("alpha",
                      lambda: self.overlay.set_alpha(self.settings["alpha"]))

    def metrics_changed(self):
        self.schedule("rebuild", self.rebuild)
        self.schedule("save", self.settings.save, 300)

    def reset_defaults(self):
        self.moving = self.overlay.moving = False
        keep = {k: self.settings[k] for k in ("ui_theme", "ui_accent")}
        self.settings.reset()
        self.settings.data.update(keep)   # the app theme is not an overlay setting
        self.overlay.colors.update(self.group_colors())
        self.telemetry.set_interval(self.settings["refresh"])
        self.overlay.set_font_size(self.settings["text"])
        self.overlay.set_alpha(self.settings["alpha"])
        self.window.draw()
        self.rebuild()
        self.settings.save()

    def save_report(self):
        self.window.flash_report(self.diagnostics.save())

    # ---- timers
    def _sys_loop(self):
        try:
            if self.overlay_visible():
                self.updater.update_system()
                self._tick += 1
                if self._tick % 3 == 0:  # keep the overlay above the game
                    WinApi.keep_on_top(self.overlay.top)
                if (self._tick % 5 == 0 and self.overlay.need.get("FPS")
                        and not self.fps.alive):
                    self.fps.start()  # PresentMon died: try again
            if self.window.is_open:
                self.window.update_status()
            self._dtick += 1
            if self._dtick % 2 == 0 and self.displays.refresh():
                self._displays_changed()
        except Exception:
            Logger.error("system loop")
        finally:
            self.root.after(1000, self._sys_loop)

    def _mon_loop(self):
        """Live data for the window: only while it is open on a live page."""
        try:
            w = self.window
            if w.is_open and w.page in (0, w.PAGE_PERF, w.PAGE_HW):
                self.sample_now()
        except Exception:
            Logger.error("monitor loop")
        finally:
            self.root.after(int(self.settings["refresh"] * 1000),
                            self._mon_loop)

    def _rec_loop(self):
        """History for the dashboard chart: one light reading every 5 s."""
        try:
            self.recorder.tick()
        except Exception:
            Logger.error("record loop")
        finally:
            self.root.after(int(Recorder.STEP * 1000), self._rec_loop)

    def _ses_loop(self):
        """Game sessions: one cycle every 2 s in a worker thread."""
        try:
            if self.settings["sessions_on"]:
                if not self.fps.alive:
                    self.fps.start()
                self.sessions.tick()
        except Exception:
            Logger.error("session loop")
        finally:
            self.root.after(int(SessionRecorder.STEP * 1000), self._ses_loop)

    def _hot_loop(self):
        """Watches F9 (only in F9 mode - nothing is polled otherwise)."""
        try:
            if self.settings["show_mode"] == "hotkey":
                self.reveal.poll()
        except Exception:
            Logger.error("hotkey loop")
        finally:
            self.root.after(40, self._hot_loop)

    def _fps_loop(self):
        try:
            if self.overlay_visible() and self.overlay.need.get("FPS"):
                self.updater.update_fps()
        except Exception:
            Logger.error("fps loop")
        finally:
            self.root.after(500, self._fps_loop)

    # ---- life cycle
    def quit(self):
        try:
            self.settings.save()
        except Exception:
            Logger.error("save on quit")
        try:
            self.sessions.stop()        # a game running now is saved
        except Exception:
            Logger.error("session save on quit")
        self.fps.stop()
        self.tray.stop()
        self.root.after(0, self.root.destroy)

    def restart(self):
        if getattr(sys, "frozen", False):
            cmd = [sys.executable] + sys.argv[1:]
        else:
            cmd = [sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:]
        if "--elevated" not in cmd:
            cmd.append("--elevated")  # the new copy waits for this one to close
        try:
            subprocess.Popen(
                cmd, close_fds=True, stdin=subprocess.DEVNULL,
                env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"))
        except Exception:
            Logger.error("restart")
            return
        self.quit()

    def run(self):
        self.window.draw()
        self.rebuild()
        self.tray.start()
        self.window.show()
        self.root.after(1500, self.driver.first_run_prompt)
        self.root.after(1000, self._sys_loop)
        self.root.after(500, self._fps_loop)
        self.root.after(1200, self._mon_loop)
        self.root.after(2000, self._rec_loop)
        self.root.after(3000, self._ses_loop)
        self.root.after(500, self._hot_loop)
        self.root.mainloop()


# =============================================================== start
def main():
    if "--make-icon" in sys.argv:  # used by build.bat: writes Lmonitor.ico
        print(Logo.save_ico(os.path.join(os.path.dirname(
            os.path.abspath(__file__)), Paths.ICON)))
        return
    WinApi.setup()
    WinApi.ensure_admin()
    WinApi.single_instance()
    WinApi.lower_priority()
    App().run()


if __name__ == "__main__":
    main()
