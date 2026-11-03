"""The Qt overlay bar: window placement, click-through, move mode, F9 slide,
blur. The look itself is QML (OverlayWindow.qml / OverlayBar.qml); the numbers
come from Backend.overlay_view.

Settings stay compatible with the classic Tk bar: pos/x/y/monitor/show_mode/
hotkey_secs/look/alpha. A custom position is saved in physical pixels relative
to its display, exactly like the Tk bar does.
"""
import time

from PySide6.QtCore import QObject, Qt, QTimer, Slot
from PySide6.QtGui import QGuiApplication

from lmonitor.engine import Logger, Theme, WinApi

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
                self._look()
            elif w.isVisible():
                w.hide()
        except Exception:
            Logger.error("qt overlay apply")

    def _look(self):
        """Blur-behind for the glass look (Windows 10 1803+), else plain."""
        S = self.b.settings
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
        self.b.set_setting("monitor", sc.name() if sc != QGuiApplication.primaryScreen() else "primary")
        self.b.set_setting("x", int((w.x() - g.x()) * dpr))
        self.b.set_setting("y", int((w.y() - g.y()) * dpr))
        self.b.set_setting("pos", "custom")
        self.bridge.settingsTouched()

    # ---- F9 slide (same behaviour as the Tk bar)
    def _poll(self):
        d = WinApi.key_down(VK_F9)
        if d and not self._f9:
            self.press()
        self._f9 = d

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
        """The user changed a setting: re-place and restyle."""
        if self.b.settings["show_mode"] != "hotkey":
            self.state, self.r = "hidden", 0.0
            self.anim.stop()
        self._pos = (0, 0)
        self.apply()
