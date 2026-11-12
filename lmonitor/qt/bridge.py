"""Python <-> QML bridge. The only place that knows both Qt and the backend.

Rules: hardware is read in worker threads (dashboard sampler, overlay
sampler); the UI thread only receives finished dictionaries through Qt
signals. Settings are validated by the engine and saved (debounced) through
the same Settings class as the classic window, so both windows share
%APPDATA%\\Lmonitor\\settings.json.
"""
import subprocess
import sys
import tempfile
import threading
import time

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, Signal, Slot
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase

from lmonitor.backend import HW_TABS, RANGES, Backend
from lmonitor import updater
from lmonitor.engine import AppInfo, Autostart, Hud, Logger, Metrics, Settings, Theme, WinApi
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
    coveredChanged = Signal()
    hudChanged = Signal()
    hudStateChanged = Signal()
    _sampled = Signal(dict)            # worker thread -> UI thread
    _overlay_sampled = Signal(dict)
    _hud_sampled = Signal(list)
    _covered_seen = Signal(bool)
    updateChanged = Signal()
    updateFound = Signal(str)          # a new version was just found (tray message)
    autostartChanged = Signal()
    _update_done = Signal(dict)

    HUD_EMPTY = {"items": [], "accent": "#35d6ff", "window": 60}
    FALLBACK_FONTS = ("Consolas", "Cascadia Mono", "Courier New")

    def __init__(self, backend: Backend, parent=None):
        super().__init__(parent)
        self._b = backend
        self._d = {"ready": False}
        self._ov = {"groups": [], "graph": None}
        self._range = 0
        self._hw_tab, self._hw, self._hw_open = 0, [[], []], False
        self._glass = False
        self._ui_visible = "--startup" not in sys.argv
        self._autostart, self._autostart_err = None, ""
        self._covered = False            # a full-screen program (game) is in front
        self._active = True              # a Lmonitor window has the focus
        self._qml_errors = []
        self._set_cache = self._prev_cache = self._fonts = None
        self._last_texts = {}
        self.host = None                         # OverlayHost (set by app.py)
        self.hud_hosts = []                      # HudHost x2: the graph overlays (set by app.py)
        self._hud = [dict(self.HUD_EMPTY), dict(self.HUD_EMPTY)]
        self._hud_page = False                   # the Graph overlay page is open (preview)
        self._graph_fast = False                 # a page shows real-time charts
        self.tools = Tools(backend, self, self)
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._sampled.connect(self._on_sampled)
        self._overlay_sampled.connect(self._on_overlay)
        self._update_done.connect(self._on_update)
        self._covered_seen.connect(self._on_covered)
        self._hud_sampled.connect(self._on_hud)
        self._upd = {"state": "idle", "text": ""}
        self._info = None
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
        self.checkUpdate()
        # ...and again every 3 hours while Lmonitor runs, so a release that comes out
        # later is noticed without pressing "Check for updates"
        self._upd_timer = QTimer(self)
        self._upd_timer.setInterval(self.UPDATE_EVERY_MS)
        self._upd_timer.timeout.connect(self._auto_check)
        self._upd_timer.start()

    # ---- updates (GitHub Releases, see lmonitor/updater.py)
    @Property("QVariantMap", notify=updateChanged)
    def update(self):
        return self._upd

    UPDATE_EVERY_MS = 3 * 3600 * 1000
    _told = ""                               # version already announced

    def _auto_check(self):
        if self._upd["state"] in ("none", "error", "idle"):
            self.checkUpdate()

    @Property(bool, constant=True)
    def startHidden(self):
        """Started by Windows at sign-in: stay in the tray, no window."""
        return "--startup" in sys.argv

    @Property(bool, notify=autostartChanged)
    def autostart(self):
        if self._autostart is None:
            self._autostart = Autostart.is_on()
        return self._autostart

    @Property(str, notify=autostartChanged)
    def autostartError(self):
        return self._autostart_err

    @Slot(bool)
    def setAutostart(self, on):
        self._autostart_err = Autostart.set(bool(on))
        self._autostart = Autostart.is_on()
        self.autostartChanged.emit()

    def _on_update(self, d):
        self._upd = d
        self.updateChanged.emit()
        if d["state"] == "available" and d.get("version") != self._told:
            self._told = d.get("version") or ""
            self.updateFound.emit(self._told)
        if d["state"] == "ready":                # installer downloaded and checked
            subprocess.Popen('cmd /c "%s"' % updater.install_command(d["path"], sys.executable),
                             creationflags=0x08000000 | 0x00000008)    # no window, detached
            QCoreApplication.quit()

    def _update_job(self, download):
        try:
            if download:
                d = {"state": "ready", "path": updater.download(self._info, tempfile.gettempdir())}
            else:
                self._info = updater.latest(AppInfo.VERSION)
                d = ({"state": "available", "version": self._info["version"]} if self._info
                     else {"state": "none"})
        except Exception as e:
            d = {"state": "error", "text": ("Download failed: " if download else "Could not check: ") + (str(e) or type(e).__name__)}
        self._update_done.emit(d)

    @Slot()
    def checkUpdate(self):
        if self._upd["state"] not in ("checking", "downloading"):
            self._upd = {"state": "checking"}
            self.updateChanged.emit()
            threading.Thread(target=self._update_job, args=(False,), daemon=True).start()

    @Slot()
    def installUpdate(self):
        if not getattr(sys, "frozen", False):            # from source: no installer run
            QDesktopServices.openUrl(QUrl(self._info["page"]))
        elif self._upd["state"] == "available":
            self._upd = dict(self._upd, state="downloading")
            self.updateChanged.emit()
            threading.Thread(target=self._update_job, args=(True,), daemon=True).start()

    def stop(self):
        self._stop.set()
        self._wake.set()
        for t in self._threads:
            t.join(timeout=3)
        self._b.save_settings()
        self._b.close()

    # ---- worker threads
    HIDDEN_PERIOD = 3.5        # s between samples while nobody looks (stays under the gap limit)

    def _game_check(self):
        """Is a full-screen program (a game) in front? Then the window is not drawn at
        all, and while Lmonitor is not in front it runs in background mode."""
        covered = WinApi.fullscreen_app()
        if covered != self._covered:
            self._covered = covered            # read by this thread right away
            self._covered_seen.emit(covered)   # the QML side on the UI thread
        WinApi.set_background_mode(not self._active)
        return covered

    def _loop(self):
        while not self._stop.is_set():
            started = time.monotonic()
            shown = self._ui_visible
            try:
                covered = self._game_check()
                shown = self._ui_visible and not covered
                self._b.sample()
                if shown:                       # nobody sees it otherwise: skip the work
                    self._sampled.emit(self._b.dashboard(self._range))
            except Exception:
                Logger.error("qt sampler")
            busy = shown or (self.host is not None and self.host.wanted()) or self._hud_wanted()
            period = self._b.telemetry.interval if busy else self.HIDDEN_PERIOD
            # the time spent reading counts, so the readings stay evenly spaced
            self._wake.wait(max(0.05, period - (time.monotonic() - started)))
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
                hud = self._hud_wanted()
                fps_in_bar = wanted and b.overlay_model.need().get("FPS")
                now = time.monotonic()
                if now - housekeeping >= 2.0:
                    housekeeping = now
                    was = b.safe_active
                    if b.safe_tick() != was:            # anti-cheat safe mode switched
                        self._wake.set()
                    b.ensure_fps(fps_in_bar or (hud and b.hud_wants_fps()))
                    if b.settings["sessions_on"]:
                        b.sessions.tick()
                if wanted:
                    texts = b.overlay_read()
                    self._last_texts = texts
                    self._overlay_sampled.emit(b.overlay_view(texts))
                    wait = 0.5 if fps_in_bar else max(0.5, float(b.settings["refresh"]))
                b.graph_fast = self._graph_fast and self._ui_visible and not self._covered
                if hud or self._hud_page or b.graph_fast:
                    # the graph overlay (or its settings page): new data once per reading -
                    # once a second, or 4x a second in real time
                    if b.hud_tick():
                        self._hud_sampled.emit(b.hud_views())
                    wait = min(wait, b.hud_period() / 3)
            except Exception:
                Logger.error("qt overlay sampler")
            self._stop.wait(wait)

    def _hud_wanted(self):
        return any(h.wanted() for h in self.hud_hosts)

    # ---- UI thread: game in front / focus
    def _on_covered(self, covered):
        self.coveredChanged.emit()
        if not covered:
            self._wake.set()                   # fresh numbers as soon as the game is gone

    @Property(bool, notify=coveredChanged)
    def covered(self):
        """A full-screen program is in front: no chart animation, no window updates."""
        return self._covered

    def setAppActive(self, active):
        """Called by app.py when a Lmonitor window gains / loses the focus."""
        self._active = bool(active)
        WinApi.set_background_mode(not self._active)
        if active:
            self._wake.set()

    # ---- UI thread: data
    def _on_sampled(self, data):
        self._d = data
        self.dashboardChanged.emit()
        if self._hw_tab >= 0 and self._hw_open:
            self._load_hw()

    def _on_overlay(self, data):
        self._ov = data
        self.overlayChanged.emit()

    # ---- graph overlays (HUD 1 and 2); n = 0 / 1
    def _on_hud(self, data):
        self._hud = data
        self.hudChanged.emit()

    @Property("QVariantList", notify=hudChanged)
    def huds(self):
        """Charts of both graph overlays (new data once per reading while one is shown)."""
        return self._hud

    def _hud_now(self):
        try:
            return self._b.hud_views()
        except Exception:
            Logger.error("hud preview")
            return [dict(self.HUD_EMPTY), dict(self.HUD_EMPTY)]

    @Slot(bool)
    def setHudPageOpen(self, on):
        """The settings page shows a live preview: read the HUD values while it is open."""
        self._hud_page = self._b.hud_page_open = bool(on)
        if on:
            self._on_hud(self._hud_now())

    @Property("QVariantList", notify=settingsChanged)
    def hudStyles(self):
        """Settings of each graph overlay under the same names (hud_items, hud_size...)."""
        d = self._b.settings.data
        return [{"hud_" + k[len(p):]: v for k, v in d.items() if k.startswith(p)}
                for p in Settings.HUD_PREFIXES]

    @Property("QVariantList", notify=hudStateChanged)
    def hudStates(self):
        """Per overlay: grab (takes the mouse now), shown, rel (place on its screen 0..1)."""
        out = []
        for i in range(len(Settings.HUD_PREFIXES)):
            h = self.hud_hosts[i] if i < len(self.hud_hosts) else None
            try:
                rel = h.relative() if h else {"x": 1.0, "y": 0.0}
            except Exception:
                rel = {"x": 1.0, "y": 0.0}
            out.append({"grab": bool(h and h.grab), "shown": bool(h and h.wanted()), "rel": rel})
        return out

    @Slot(int, str, "QVariant")
    def setHudSetting(self, n, key, value):
        """key is the plain name ("hud_size"); n picks the overlay."""
        if not (0 <= n < len(Settings.HUD_PREFIXES)) or not key.startswith("hud_"):
            return
        self.setSetting(Settings.HUD_PREFIXES[n] + key[4:], value)

    @Slot(int, float, float)
    def placeHud(self, n, fx, fy):
        """Dragged in the preview: put the overlay at this place of its screen (0..1)."""
        if 0 <= n < len(self.hud_hosts):
            self.hud_hosts[n].place(fx, fy)

    @Property("QVariantList", constant=True)
    def hudCatalog(self):
        return [{"key": k, "title": Hud.ITEMS[k][0], "unit": Hud.ITEMS[k][1]} for k in Hud.ORDER]

    @Property("QVariantList", constant=True)
    def hudThemes(self):
        return [{"key": k, "name": n, "accent": a, "colors": c} for k, n, a, c in Hud.THEMES]

    @Property(int, constant=True)
    def hudMaxItems(self):
        return Hud.MAX_ITEMS

    @Slot(int, str, bool)
    def setHudItem(self, n, key, on):
        if not (0 <= n < len(Settings.HUD_PREFIXES)):
            return
        name = Settings.HUD_PREFIXES[n] + "items"
        items = list(self._b.settings[name])
        if on and key not in items:
            items.append(key)
        elif not on and key in items and len(items) > 1:      # one chart always stays
            items.remove(key)
        if self._b.set_setting(name, items):
            self.settingsTouched()

    def hudShownChanged(self):
        self.hudStateChanged.emit()

    @Slot(int)
    def resetHud(self, n):
        if not (0 <= n < len(Settings.HUD_PREFIXES)):
            return
        p = Settings.HUD_PREFIXES[n]
        for k, v in Settings.DEFAULTS.items():
            if k.startswith(p):
                self._b.set_setting(k, v)
        self.settingsTouched()

    # ---- window look (Personalize)
    @Property("QVariantList", constant=True)
    def uiScales(self):
        return list(Theme.UI_SCALES)

    @Property("QStringList", constant=True)
    def uiFonts(self):
        return list(Theme.UI_FONTS)

    @Slot(int, result=str)
    def hueHex(self, h):
        return Theme.hue_hex(h)

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
        """Time span of the Home chart: 0 = real time, 1 = 1 minute."""
        if 0 <= i < len(RANGES) and i != self._range:
            self._range = i
            self.rangeChanged.emit()

    @Slot(bool)
    def setGraphFast(self, on):
        """A page shows real-time charts (4 readings a second while it is visible)."""
        self._graph_fast = bool(on)

    # ---- performance charts
    @Slot(int, result="QVariantMap")
    def graphs(self, seconds):
        return self._b.graph_series(seconds)

    @Slot(bool)
    def setGraphsOpen(self, on):
        self._b.graph_fans = bool(on)

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
        for h in self.hud_hosts:
            h.settingsChanged()
        if self.hud_hosts:
            self.hudStateChanged.emit()
            self._wake.set()                 # the sampler may need to run faster now

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
