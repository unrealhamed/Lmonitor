"""The Qt overlay bar: window placement, click-through, move mode, F9 slide,
blur. The look itself is QML (OverlayWindow.qml / OverlayBar.qml); the numbers
come from Backend.overlay_view.

Settings stay compatible with the classic Tk bar: pos/x/y/monitor/show_mode/
hotkey_secs/look/alpha. A custom position is saved in physical pixels relative
to its display, exactly like the Tk bar does.
"""
import sys
import time

from PySide6.QtCore import QObject, Qt, QTimer, Slot
from PySide6.QtGui import QCursor, QGuiApplication

from lmonitor.engine import Logger, Settings, Theme, WinApi

VK_F9 = 0x78
SLIDE = 0.35            # seconds for one slide
FRAME_MS = 15


def ease(t):
    return 1 - (1 - t) ** 3


class OverlayHost(QObject):
    def __init__(self, bridge, backend, parent=None):
        super().__init__(parent)
        self.bridge, self.b = bridge, backend
        self.win = None
        self.moving = False
        self.state, self.r, self.hold_until, self.last = "hidden", 0.0, 0.0, 0.0
        self._f9 = False
        self._pos = (0, 0)
        self._look_key = None
        self.poll = QTimer(self)
        self.poll.setInterval(40)
        self.poll.timeout.connect(self._poll)
        self.anim = QTimer(self)
        self.anim.setInterval(FRAME_MS)
        self.anim.timeout.connect(self._step)

    # ---- wiring
    def attach(self, window):
        self.win = window
        window.setFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                        | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        window.widthChanged.connect(self.apply)
        window.heightChanged.connect(self.apply)
        self.poll.start()
        self.apply()

    # ---- monitor / geometry
    def screen(self):
        want = self.b.settings["monitor"]
        for s in QGuiApplication.screens():
            if s.name() == want:
                return s
        return QGuiApplication.primaryScreen()

    def screen_names(self):
        return [s.name() for s in QGuiApplication.screens()]

    def _target(self):
        """Resting position (logical px) of the bar."""
        S, sc, w = self.b.settings, self.screen(), self.win
        g, dpr = sc.geometry(), sc.devicePixelRatio()
        ww, wh = int(w.width()), int(w.height())
        if S["pos"] == "custom" and S["x"] is not None and S["y"] is not None:
            x, y = g.x() + S["x"] / dpr, g.y() + S["y"] / dpr
        elif S["pos"] == "center":
            x, y = g.x() + (g.width() - ww) / 2, g.y()
        elif S["pos"] == "right":
            x, y = g.x() + g.width() - ww - Theme.MARGIN / dpr, g.y()
        else:
            x, y = g.x() + Theme.MARGIN / dpr, g.y()
        x = max(g.x(), min(g.x() + g.width() - ww, x))      # stay on the display
        y = max(g.y(), min(g.y() + g.height() - wh, y))
        return int(x), int(y)

    def _slide_y(self, y, h):
        """F9 mode: 0 = just above the display's top edge, 1 = resting place."""
        if self.b.settings["show_mode"] != "hotkey" or self.moving:
            return y
        y0 = self.screen().geometry().y() - h - 6
        return int(y0 + (y - y0) * ease(max(0.0, min(1.0, self.r))))

    def wanted(self):
        """Should the bar be on screen right now?"""
        S = self.b.settings
        if not S["on"]:
            return False
        if not any(S.show.values()):
            return False
        return S["show_mode"] == "always" or self.moving or self.state != "hidden"

    # ---- apply everything (cheap; called on size / setting changes)
    @Slot()
    def apply(self):
        w = self.win
        if w is None:
            return
        try:
            show = self.wanted()
            if self.moving:
                w.setFlag(Qt.WindowTransparentForInput, False)
            else:
                w.setFlag(Qt.WindowTransparentForInput, True)
            if show:
                x, y = self._target()
                if not self.moving or self._pos == (0, 0):
                    w.setPosition(x, self._slide_y(y, int(w.height())))
                    self._pos = (x, y)
                if not w.isVisible():
                    w.show()
                    self._look_key = None          # a new native window: style it again
                self._look()
            elif w.isVisible():
                w.hide()
        except Exception:
            Logger.error("qt overlay apply")

    def _look(self):
        """Blur-behind for the glass look (Windows 10 1803+), else plain.
        Done only when something it depends on changed: these window-manager calls
        (blur, corners, always-on-top) disturb a game when repeated."""
        S = self.b.settings
        old_windows = sys.getwindowsversion().build < 22000   # corners need the size there
        key = (S["look"], S["bg"], S["alpha"], int(self.win.winId()),
               (self.win.width(), self.win.height()) if old_windows else None)
        if key == self._look_key:
            return
        self._look_key = key
        try:
            h = int(self.win.winId())
            dpr = self.screen().devicePixelRatio()
            if S["look"] == "glass" and WinApi.blur_supported():
                # light tint so the blurred background shows through
                ok = WinApi.blur_hwnd(h, Theme.overlay_bg(S["bg"]), int(S["alpha"] * 1.2))
                WinApi.round_hwnd(h, True, self.win.width() * dpr,
                                  self.win.height() * dpr, int(10 * dpr))
                self.bridge.setGlassOk(bool(ok))
            else:
                WinApi.blur_hwnd(h, None)
                WinApi.round_hwnd(h, False)
                self.bridge.setGlassOk(False)
            WinApi.keep_on_top_hwnd(h)
        except Exception:
            Logger.error("qt overlay look")

    # ---- move mode
    @Slot(bool)
    def setMoving(self, on):
        self.moving = bool(on)
        self.bridge.movingChanged.emit()
        self._pos = (0, 0)
        self.apply()

    @Slot()
    def saveMoved(self):
        """After a drag: remember the position (physical px, relative)."""
        w = self.win
        sc = QGuiApplication.screenAt(w.position()) or self.screen()
        g, dpr = sc.geometry(), sc.devicePixelRatio()
        self.b.set_many({"monitor": sc.name() if sc != QGuiApplication.primaryScreen() else "primary",
                         "x": int((w.x() - g.x()) * dpr), "y": int((w.y() - g.y()) * dpr),
                         "pos": "custom"})
        self.bridge.settingsTouched()

    # ---- F9 slide (same behaviour as the Tk bar)
    def _poll(self):
        d = WinApi.key_down(VK_F9)
        if d and not self._f9:
            self.press()
        self._f9 = d
        self._ticks = getattr(self, "_ticks", 0) + 1
        if self._ticks % 125 == 0 and self.win is not None and self.win.isVisible():
            try:                                   # every 5 s: stay above a game window
                WinApi.keep_on_top_hwnd(int(self.win.winId()))
            except Exception:
                pass

    def press(self, now=None):
        S = self.b.settings
        if S["show_mode"] != "hotkey" or not S["on"] or self.moving:
            return False
        now = time.time() if now is None else now
        if self.state == "hidden":
            self.state, self.r, self.last = "in", 0.0, now
            self.apply()
            self.anim.start()
        elif self.state == "out":
            self.state = "in"
        elif self.state == "shown":
            self.hold_until = now + S["hotkey_secs"]
        return True

    def _step(self):
        now = time.time()
        dt, self.last = max(0.0, now - self.last), now
        S = self.b.settings
        if self.state == "in":
            self.r = min(1.0, self.r + dt / SLIDE)
            if self.r >= 1.0:
                self.state, self.hold_until = "shown", now + S["hotkey_secs"]
        elif self.state == "shown" and now >= self.hold_until:
            self.state = "out"
        elif self.state == "out":
            self.r = max(0.0, self.r - dt / SLIDE)
            if self.r <= 0.0:
                self.state = "hidden"
        if self.state == "hidden":
            self.anim.stop()
            self.apply()
            return
        x, y = self._target()
        self.win.setPosition(x, self._slide_y(y, int(self.win.height())))

    @Slot()
    def settingsChanged(self):
        """The user changed a setting: re-place and restyle (bar)."""
        if self.b.settings["show_mode"] != "hotkey":
            self.state, self.r = "hidden", 0.0
            self.anim.stop()
        self._pos = (0, 0)
        self.apply()


VK_F10 = 0x79
VK_CONTROL = 0x11
VK_LBUTTON = 0x01
HUD_MARGIN = 16          # px from the screen edge (logical)


class HudHost(QObject):
    """One graph overlay window (there are two): placement, click-through, F10, and
    dragging. It floats: put the mouse on its top edge and drag it - no button, no key.
    (Not while a full-screen game is in front, so it can never take a click from a game;
    holding Ctrl makes the whole overlay draggable anywhere, also over a game.)

    Its size depends on the settings only, so it never resizes over a game."""
    HANDLE = 26                              # px: the top edge that takes the mouse

    def __init__(self, bridge, backend, index=0, parent=None):
        super().__init__(parent)
        self.bridge, self.b = bridge, backend
        self.index = index
        self.p = Settings.HUD_PREFIXES[index]    # "hud_" / "hud2_"
        self.win = None
        self.toggled = True                  # F10 mode: shown / hidden
        self.grab = False                    # the window takes the mouse right now
        self._drag = False                   # the button is down on it
        self._key = False
        self._ticks = 0
        self.poll = QTimer(self)
        self.poll.setInterval(40)
        self.poll.timeout.connect(self._poll)

    def S(self, key):
        return self.b.settings[self.p + key]

    def attach(self, window):
        self.win = window
        window.setFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                        | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        window.widthChanged.connect(self.apply)
        window.heightChanged.connect(self.apply)
        self.poll.start()
        self.apply()

    def screen(self):
        want = self.S("monitor")
        for s in QGuiApplication.screens():
            if s.name() == want:
                return s
        return QGuiApplication.primaryScreen()

    def wanted(self):
        if not self.S("on") or not self.S("items"):
            return False
        return self.S("mode") == "always" or self.toggled

    def _target(self):
        sc, w = self.screen(), self.win
        g, dpr = sc.geometry(), sc.devicePixelRatio()
        ww, wh = int(w.width()), int(w.height())
        pos = self.S("pos")
        if pos == "custom" and self.S("x") is not None and self.S("y") is not None:
            x, y = g.x() + self.S("x") / dpr, g.y() + self.S("y") / dpr
        else:
            x = g.x() + HUD_MARGIN if pos in ("tl", "bl") else g.x() + g.width() - ww - HUD_MARGIN
            y = g.y() + HUD_MARGIN if pos in ("tl", "tr") else g.y() + g.height() - wh - HUD_MARGIN
        x = max(g.x(), min(g.x() + g.width() - ww, x))
        y = max(g.y(), min(g.y() + g.height() - wh, y))
        return int(x), int(y)

    @Slot()
    def apply(self):
        w = self.win
        if w is None:
            return
        try:
            if self.wanted():
                if not self.grab:                  # never pull it away from the mouse
                    w.setPosition(*self._target())
                if not w.isVisible():
                    w.show()
                    WinApi.keep_on_top_hwnd(int(w.winId()))
                    self._through(not self.grab)
            elif w.isVisible():
                w.hide()
        except Exception:
            Logger.error("qt hud apply")

    def _through(self, on):
        """Mouse clicks go through the window (on) or the window takes them (off)."""
        try:
            # Qt itself also ignores the mouse while this flag is set, so both are switched
            self.win.setFlag(Qt.WindowTransparentForInput, on)
            WinApi.click_through_hwnd(int(self.win.winId()), on)
            if not on:
                WinApi.keep_on_top_hwnd(int(self.win.winId()))
        except Exception:
            Logger.error("qt hud click-through")

    def _poll(self):
        d = WinApi.key_down(VK_F10)
        if d and not self._key and self.S("mode") == "hotkey":
            self.toggled = not self.toggled
            self.apply()
            self.bridge.hudShownChanged()
        self._key = d
        self._grab_check()
        self._ticks += 1
        if self._ticks % 125 == 0 and self.win is not None and self.win.isVisible():
            try:                                   # every 5 s: stay above a game window
                WinApi.keep_on_top_hwnd(int(self.win.winId()))
            except Exception:
                pass

    def want_grab(self, inside, on_handle, ctrl, down, fullscreen):
        """Should the window take the mouse now? (plain rule, tested without a screen)"""
        if self.grab and down:
            return True                            # being dragged: keep it
        if not inside or down:
            return False                           # a drag that started elsewhere passes by
        if ctrl:
            return True
        return on_handle and not fullscreen

    def _grab_check(self):
        w = self.win
        if w is None:
            return
        down = WinApi.key_down(VK_LBUTTON)
        grab = False
        if w.isVisible():
            p, g = QCursor.pos(), w.geometry()
            inside = g.contains(p)
            on_handle = inside and p.y() - g.y() <= self.HANDLE
            ctrl = inside and WinApi.key_down(VK_CONTROL)
            full = WinApi.fullscreen_app(True) if (on_handle and not ctrl and not self.grab) else False
            grab = self.want_grab(inside, on_handle, ctrl, down, full)
        # After a drag (the mouse was on it, the button is up again, and it is not where the
        # settings say): remember the new place. Windows moves the window itself while the
        # button is down, and this timer may not run during that time - so the check is
        # made afterwards, from where the window really is.
        if self.grab:
            self._drag = True
        if self._drag and not down and w.isVisible():
            if (w.x(), w.y()) != self._target():
                self.saveMoved()
            if not grab:
                self._drag = False
        if grab != self.grab:
            self.grab = grab
            self._through(not grab)
            self.bridge.hudShownChanged()

    def relative(self):
        """The resting place as fractions of the free room on its screen (0..1)."""
        w = self.win
        if w is None:
            return {"x": 1.0, "y": 0.0}
        x, y = self._target()
        g = self.screen().geometry()
        fw, fh = max(1, g.width() - w.width()), max(1, g.height() - w.height())
        return {"x": max(0.0, min(1.0, (x - g.x()) / fw)), "y": max(0.0, min(1.0, (y - g.y()) / fh))}

    def _save_place(self, sc, x, y):
        dpr = sc.devicePixelRatio()
        b, p = self.b, self.p
        b.set_many({p + "monitor": sc.name() if sc != QGuiApplication.primaryScreen() else "primary",
                    p + "x": int(x * dpr), p + "y": int(y * dpr), p + "pos": "custom"})
        self.bridge.settingsTouched()

    def place(self, fx, fy):
        """Put it at a place of its screen given as fractions (0..1), e.g. from the preview."""
        w, sc = self.win, self.screen()
        if w is None:
            return
        g = sc.geometry()
        fx, fy = max(0.0, min(1.0, fx)), max(0.0, min(1.0, fy))
        self._save_place(sc, fx * max(0, g.width() - w.width()), fy * max(0, g.height() - w.height()))

    def saveMoved(self):
        """After a drag on the screen: remember where it is now."""
        w = self.win
        sc = QGuiApplication.screenAt(w.position()) or self.screen()
        g = sc.geometry()
        self._save_place(sc, w.x() - g.x(), w.y() - g.y())

    @Slot()
    def settingsChanged(self):
        if self.S("mode") != "hotkey":
            self.toggled = True
        self.apply()
