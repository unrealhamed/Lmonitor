"""Python <-> QML bridge. The only place that knows both Qt and the backend.

Rules: hardware is read in worker threads (dashboard sampler, overlay
sampler); the UI thread only receives finished dictionaries through Qt
signals. Settings are validated by the engine and saved (debounced) through
the same Settings class as the classic window, so both windows share
%APPDATA%\\Lmonitor\\settings.json.
"""
import threading
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QFontDatabase

from lmonitor.backend import HW_TABS, RANGES, Backend
from lmonitor.engine import Logger, Metrics, Theme
from lmonitor.qt.tools import Tools


class Bridge(QObject):
    dashboardChanged = Signal()
    rangeChanged = Signal()
    settingsChanged = Signal()
    overlayChanged = Signal()
    movingChanged = Signal()
    glassChanged = Signal()
    hardwareChanged = Signal()
    qmlErrorsChanged = Signal()
    _sampled = Signal(dict)            # worker thread -> UI thread
    _overlay_sampled = Signal(dict)

    FALLBACK_FONTS = ("Consolas", "Cascadia Mono", "Courier New")

    def __init__(self, backend: Backend, parent=None):
        super().__init__(parent)
        self._b = backend
        self._d = {"ready": False}
        self._ov = {"groups": [], "graph": None}
        self._range = 0
        self._hw_tab, self._hw, self._hw_open = 0, [[], []], False
        self._glass = False
        self._ui_visible = True
        self._qml_errors = []
        self._set_cache = self._prev_cache = self._fonts = None
        self._last_texts = {}
        self.host = None                         # OverlayHost (set by app.py)
        self.tools = Tools(backend, self, self)
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._sampled.connect(self._on_sampled)
        self._overlay_sampled.connect(self._on_overlay)
        self._threads = [
            threading.Thread(target=self._loop, name="sampler", daemon=True),
            threading.Thread(target=self._overlay_loop, name="overlay", daemon=True)]
        self._save = QTimer(self)
        self._save.setSingleShot(True)
        self._save.setInterval(400)
        self._save.timeout.connect(self._b.save_settings)

    # ---- lifecycle
    def start(self):
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()
        self._wake.set()
        for t in self._threads:
            t.join(timeout=3)
        self._b.save_settings()
        self._b.close()

    # ---- worker threads
    HIDDEN_PERIOD = 3.5        # s between samples while nobody looks (stays under the gap limit)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._b.sample()
                if self._ui_visible:            # nobody sees it otherwise: skip the work
                    self._sampled.emit(self._b.dashboard(self._range))
            except Exception:
                Logger.error("qt sampler")
            busy = self._ui_visible or (self.host is not None and self.host.wanted())
            self._wake.wait(self._b.telemetry.interval if busy else self.HIDDEN_PERIOD)
            self._wake.clear()

    def _overlay_loop(self):
        """The bar's numbers (only while the bar is on screen) and, every 2 s,
        PresentMon / game-session housekeeping."""
        housekeeping = 0.0
        while not self._stop.is_set():
            wait = 2.0
            try:
                b = self._b
                wanted = self.host is not None and self.host.wanted()
                fps_in_bar = wanted and b.overlay_model.need().get("FPS")
                now = time.monotonic()
                if now - housekeeping >= 2.0:
                    housekeeping = now
                    b.ensure_fps(fps_in_bar)
                    if b.settings["sessions_on"]:
                        b.sessions.tick()
                if wanted:
                    texts = b.overlay_read()
                    self._last_texts = texts
                    self._overlay_sampled.emit(b.overlay_view(texts))
                    wait = 0.5 if fps_in_bar else max(0.5, float(b.settings["refresh"]))
            except Exception:
                Logger.error("qt overlay sampler")
            self._stop.wait(wait)

    # ---- UI thread: data
    def _on_sampled(self, data):
        self._d = data
        self.dashboardChanged.emit()
        if self._hw_tab >= 0 and self._hw_open:
            self._load_hw()

    def _on_overlay(self, data):
        self._ov = data
        self.overlayChanged.emit()

    @Property("QVariantMap", notify=dashboardChanged)
    def dashboard(self):
        return self._d

    @Property("QVariantMap", notify=overlayChanged)
    def overlay(self):
        return self._ov

    @Property(str, constant=True)
    def version(self):
        return self._b.version()

    def addQmlError(self, text):
        """QML load / runtime errors: shown in the window and kept in qt_error.log."""
        self._qml_errors = (self._qml_errors + [text])[-8:]
        self.qmlErrorsChanged.emit()
        Logger.error("qml", text)

    @Property(str, notify=qmlErrorsChanged)
    def qmlErrors(self):
        return "\n\n".join(self._qml_errors)

    @Property(int, constant=True)
    def interval(self):
        """Milliseconds between samples (the charts slide over this time)."""
        return self._b.interval_ms()

    @Property("QStringList", constant=True)
    def rangeNames(self):
        return [n for n, _ in RANGES]

    @Property(int, notify=rangeChanged)
    def rangeIndex(self):
        return self._range

    @Slot(int)
    def setRange(self, i):
        if 0 <= i < len(RANGES) and i != self._range:
            self._range = i
            self.rangeChanged.emit()
            if self._d.get("ready"):           # cheap: reads history only
                d = dict(self._d)
                d["perf"] = self._b.perf(i)
                self._on_sampled(d)

    # ---- performance charts
    @Slot(result="QVariantList")
    def charts(self):
        return self._b.charts()

    # ---- hardware page (cached telemetry rows)
    @Property("QStringList", constant=True)
    def hardwareTabs(self):
        return [n for n, _ in HW_TABS]

    @Property("QVariantList", notify=hardwareChanged)     # [column, column] of sections
    def hardware(self):
        return self._hw

    @Slot(int, bool)
    def openHardware(self, tab, opened):
        self._hw_open = opened
        self._hw_tab = max(0, min(tab, len(HW_TABS) - 1))
        if opened:
            self._load_hw()

    def _load_hw(self):
        try:
            cols = self._b.hardware_sections(self._hw_tab)
        except Exception:
            Logger.error("qt hardware")
            cols = [[], []]
        if cols != self._hw:
            self._hw = cols
            self.hardwareChanged.emit()

    # ---- settings
    @Property("QVariantMap", notify=settingsChanged)
    def settings(self):
        if self._set_cache is None:                  # built once per change
            d = self._b.settings_view()
            d["font_resolved"] = self.resolveFont(d["font"])
            d["bg_hex"] = Theme.overlay_bg(d["bg"])
            self._set_cache = d
        return self._set_cache

    @Property("QVariantMap", notify=settingsChanged)
    def preview(self):
        """Bar structure for the live preview: real readings when the bar has
        been reading, otherwise "--" (never a made-up number)."""
        if self._prev_cache is None:
            self._prev_cache = self._b.overlay_view(dict(self._last_texts))
        return self._prev_cache

    @Property("QVariantList", constant=True)
    def groups(self):
        return [{"name": g, "items": [{"key": k, "label": l} for k, l, _ in items]}
                for g, items in Metrics.GROUPS]

    @Property("QVariantList", constant=True)
    def backgrounds(self):
        return [{"key": k, "name": n, "hex": Theme.overlay_bg(k)}
                for k, n, _ in Theme.OVERLAY_BGS]

    @Property("QVariantMap", notify=settingsChanged)
    def ui(self):
        return self._b.ui_style()

    @Property("QVariantList", constant=True)
    def uiThemes(self):
        out = []
        for k, n, note, _ in Theme.UI_THEMES:
            d = self._b.ui_style(k, "auto")
            d.update(key=k, name=n, note=note)
            out.append(d)
        return out

    @Property("QVariantList", constant=True)
    def uiAccents(self):
        return [{"key": k, "name": n, "hex": c or ""} for k, n, c in Theme.UI_ACCENTS]

    @Property(str, notify=settingsChanged)
    def density(self):
        return self._b.density()

    @Slot(str)
    def setDensity(self, key):
        if self._b.set_density(key):
            self.settingsTouched()

    @Property("QVariantList", constant=True)
    def valueColors(self):
        return [{"key": k, "name": n, "hex": c or Theme.ACCENT}
                for k, n, c in Theme.VALUE_COLORS]

    @Property("QStringList", constant=True)
    def fonts(self):
        bad = {"wingdings", "wingdings 2", "wingdings 3", "webdings", "marlett",
               "symbol", "mt extra", "holo mdl2 assets", "segoe mdl2 assets",
               "segoe fluent icons", "bookshelf symbol 7"}
        return sorted({f for f in QFontDatabase.families()
                       if not f.startswith("@") and f.lower() not in bad},
                      key=str.lower)

    def resolveFont(self, want):
        if self._fonts is None:
            self._fonts = {f.lower(): f for f in QFontDatabase.families()}
        have = self._fonts
        for name in (want,) + self.FALLBACK_FONTS:
            if str(name).lower() in have:
                return have[str(name).lower()]
        return want

    @Property("QStringList", notify=hardwareChanged)
    def screens(self):
        return self.host.screen_names() if self.host else []

    def settingsTouched(self):
        self._set_cache = self._prev_cache = None
        self.settingsChanged.emit()
        self._save.start()
        if self.host:
            self.host.settingsChanged()

    @Slot(str, "QVariant")
    def setSetting(self, key, value):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if self._b.set_setting(key, value):
            self.settingsTouched()

    @Slot(str, bool)
    def setShow(self, key, on):
        if self._b.set_show(key, on):
            self.settingsTouched()

    @Slot(str, int)
    def moveGroup(self, name, d):
        order = self._b.settings["order"]
        g = list(order["groups"])
        if name in g:
            i = g.index(name)
            j = max(0, min(len(g) - 1, i + d))
            g[i], g[j] = g[j], g[i]
            self._b.set_order(dict(order, groups=g))
            self.settingsTouched()

    @Slot()
    def resetSettings(self):
        keep = {k: self._b.settings[k] for k in ("ui_theme", "ui_accent")}
        self._b.reset_settings()
        for k, v in keep.items():
            self._b.set_setting(k, v)
        self.settingsTouched()

    # ---- overlay host
    @Property(bool, notify=movingChanged)
    def moving(self):
        return bool(self.host and self.host.moving)

    @Property(bool, notify=glassChanged)
    def glassOk(self):
        return self._glass

    def setGlassOk(self, ok):
        if ok != self._glass:
            self._glass = ok
            self.glassChanged.emit()

    @Slot(bool)
    def setUiVisible(self, visible):
        """The main window is minimized / hidden: stop preparing data for it."""
        if visible != self._ui_visible:
            self._ui_visible = bool(visible)
            if visible:
                self._wake.set()

    @Slot(bool)
    def setMoving(self, on):
        if self.host:
            self.host.setMoving(on)

    @Slot()
    def saveMoved(self):
        if self.host:
            self.host.saveMoved()

    @Slot()
    def tryReveal(self):
        if self.host:
            self.host.press()
