"""Python <-> QML bridge. The only place that knows both Qt and the backend.

Rules: hardware is read in worker threads (dashboard sampler, overlay
sampler); the UI thread only receives finished dictionaries through Qt
signals. Settings are validated by the engine and saved (debounced) through
the same Settings class as the classic window, so both windows share
%APPDATA%\\Lmonitor\\settings.json.
"""
import os
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
from lmonitor.engine import Alerts, AppInfo, Autostart, Hud, Logger, Metrics, Settings, Theme, WinApi
from lmonitor.qt.tools import Tools


class Bridge(QObject):
    dashboardChanged = Signal()
    rangeChanged = Signal()
    settingsChanged = Signal()
    overlayChanged = Signal()
    movingChanged = Signal()
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
    _autostart_done = Signal(bool, str)
    netUsageChanged = Signal()
    alertRaised = Signal(str, str)     # a warning (title, what to do) for the tray
    alertsChanged = Signal()
    _alerts_new = Signal(list)         # worker thread -> UI thread
    _game_switched = Signal()          # a game started / ended: its own overlay settings
    _bench_finished = Signal(str)      # worker thread -> UI thread
    trayInfo = Signal(str, str)        # a calm message next to the clock (title, text)

    HUD_EMPTY = {"items": [], "accent": "#35d6ff", "window": 60}
    FALLBACK_FONTS = ("Consolas", "Cascadia Mono", "Courier New")

    def __init__(self, backend: Backend, parent=None):
        super().__init__(parent)
        self._b = backend
        self._d = {"ready": False}
        self._ov = {"groups": [], "graph": None}
        self._range = 0
        self._hw_tab, self._hw, self._hw_open = 0, [[], []], False
        self._ui_visible = "--startup" not in sys.argv
        self._autostart, self._autostart_err = None, ""
        self._covered = False            # a full-screen program (game) is in front
        self._active = True              # a Lmonitor window has the focus
        self._qml_errors = []
        self._set_cache = self._prev_cache = self._fonts = self._ui_cache = None
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
        self._alerts_new.connect(self._on_alerts)
        self._game_switched.connect(self.settingsTouched)
        self._bench_finished.connect(self._on_bench)
        self._nu = {"days": 1, "day": None, "hour": -1, "seen": -1}
        self._nu_view = {"state": "idle"}
        self._nu_timer = QTimer(self)
        self._nu_timer.setInterval(400)
        self._nu_timer.timeout.connect(self._nu_poll)
        self._autostart_done.connect(self._on_autostart)
        self._upd = {"state": "idle", "text": ""}
        self._info = None
        self._threads = [
            threading.Thread(target=self._loop, name="sampler", daemon=True),
            threading.Thread(target=self._overlay_loop, name="overlay", daemon=True)]
        self._save = QTimer(self)
        self._save.setSingleShot(True)
        self._save.setInterval(400)
        self._save.timeout.connect(self._b.save_settings)
        self._trim_once = QTimer(self)
        self._trim_once.setSingleShot(True)
        self._trim_once.setInterval(self.TRIM_AFTER_MS)
        self._trim_once.timeout.connect(self._trim)
        self._trim_timer = QTimer(self)
        self._trim_timer.setInterval(self.TRIM_EVERY_MS)
        self._trim_timer.timeout.connect(lambda: self._trim(True))

    # ---- lifecycle
    def start(self):
        for t in self._threads:
            t.start()
        self._autostart_job(None)
        self._b.net_meter.start()               # Network usage: the hours Windows has not written yet
        self._trim_timer.start()
        if not self._ui_visible:                # started at sign-in, only the tray
            QTimer.singleShot(20000, self._trim)
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
        return bool(self._autostart)

    @Property(str, notify=autostartChanged)
    def autostartError(self):
        return self._autostart_err

    def _autostart_job(self, on):
        """Ask (on = None) or switch the Windows task on a worker thread."""
        st = self._b.settings
        wanted = st["autostart_on"]

        def work():
            err = ""
            try:
                if on is not None:
                    err = Autostart.set(bool(on))
                    state = Autostart.is_on()
                elif wanted:                          # chosen before: make sure the task is there
                    state, err = Autostart.repair(True)
                else:
                    state = Autostart.is_on()
            except Exception as e:
                state, err = bool(self._autostart), str(e)[:200]
            self._autostart_done.emit(state, err)
        threading.Thread(target=work, name="autostart", daemon=True).start()

    def _on_autostart(self, state, err):
        self._autostart, self._autostart_err = state, err
        st = self._b.settings
        if st["autostart_on"] is None and state:      # 1.20.1 and older: the task tells the choice
            st["autostart_on"] = True
            self._save.start()
        self.autostartChanged.emit()

    @Slot(bool)
    def setAutostart(self, on):
        self._autostart = bool(on)                    # the switch moves at once
        self._b.settings["autostart_on"] = bool(on)   # remembered: a lost task is made again
        self._save.start()
        self.autostartChanged.emit()
        self._autostart_job(bool(on))

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
                d = ({"state": "available", "version": self._info["version"],
                      "notes": self._info.get("notes", "")} if self._info
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
        """Is a full-screen program (a game) in front? Then the window is not drawn at all."""
        covered = WinApi.fullscreen_app()
        if covered != self._covered:
            self._covered = covered            # read by this thread right away
            self._covered_seen.emit(covered)   # the QML side on the UI thread
        return covered

    def _loop(self):
        while not self._stop.is_set():
            started = time.monotonic()
            shown = self._ui_visible
            try:
                covered = self._game_check()
                shown = self._ui_visible and not covered
                self._b.sample()
                new = self._b.alerts.take()
                if new:
                    self._alerts_new.emit(new)
                if shown:                       # nobody sees it otherwise: skip the work
                    self._sampled.emit(self._b.dashboard(self._range))
            except Exception:
                Logger.error("qt sampler")
            # behind a full-screen game the window is not drawn, but the readings go on
            # at their normal pace, so the charts have no holes when you come back
            busy = self._ui_visible or (self.host is not None and self.host.wanted()) or self._hud_wanted()
            period = self._b.telemetry.interval if busy else self.HIDDEN_PERIOD
            # the time spent reading counts, so the readings stay evenly spaced
            self._wake.wait(max(0.05, period - (time.monotonic() - started)))
            self._wake.clear()

    BAR_FPS_PERIOD = 0.33

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
                    if b.game_tick():                   # a game started / ended
                        self._game_switched.emit()
                    if b.settings["sessions_on"] or b.sessions.bench:
                        b.sessions.tick()
                    if b.sessions.bench_done:           # a benchmark ended: say so next to the clock
                        done, b.sessions.bench_done = b.sessions.bench_done, None
                        self._bench_finished.emit(done[1])
                if wanted:
                    texts = b.overlay_read()
                    self._last_texts = texts
                    self._overlay_sampled.emit(b.overlay_view(texts))
                    # FPS in the bar: 3 times a second, so the number and its graph move
                    # steadily (the reading itself is cheap - frames are already in memory)
                    wait = self.BAR_FPS_PERIOD if fps_in_bar else max(0.5, float(b.settings["refresh"]))
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

    # ---- What's new: shown once after an update (components/WhatsNew.qml)
    _wn = None

    @Property("QVariantMap", constant=True)
    def whatsNew(self):
        if self._wn is None:
            try:
                self._wn = self._b.whats_new() or {}
            except Exception:
                Logger.error("whats new")
                self._wn = {}
        return self._wn

    @Property("QVariantMap", constant=True)
    def whatsNewLatest(self):
        """The newest What's new, for the button on the About page."""
        from lmonitor.engine import WhatsNew
        e = WhatsNew.ENTRIES[0] if WhatsNew.ENTRIES else None
        return {"version": e["version"], "since": e["since"], "slides": [dict(x) for x in e["slides"]]} if e else {}

    @Slot()
    def whatsNewDone(self):
        self._b.whats_new_seen()

    # ---- network usage (Home > Network): Windows' own records, read when the view opens
    @Property("QVariantMap", notify=netUsageChanged)
    def netUsage(self):
        return self._nu_view

    def _nu_build(self):
        n = self._nu
        try:
            self._nu_view = self._b.net_usage_view(n["days"], n["day"], n["hour"])
        except Exception:
            Logger.error("network usage view")
            self._nu_view = {"state": "error", "error": "See error.log"}
        n["seen"] = self._b.net_usage.version
        self.netUsageChanged.emit()

    def _nu_poll(self):
        if self._b.net_usage.version != self._nu["seen"]:
            self._nu_build()
        if not self._b.net_usage.busy:
            self._nu_timer.stop()

    @Slot(bool)
    def setNetUsageOpen(self, on):
        if on:
            self._b.net_usage.refresh()
            self._nu_build()
            self._nu_timer.start()
        else:
            self._nu_timer.stop()

    @Slot()
    def netUsageRefresh(self):
        self._b.net_usage.refresh(force=True)
        self._nu_build()
        self._nu_timer.start()

    @Slot(int)
    def netUsageRange(self, days):
        self._nu.update(days=days, day=None, hour=-1)
        self._nu_build()

    @Slot(float)
    def netUsageDay(self, start):
        self._nu.update(day=start, hour=-1)
        self._nu_build()

    @Slot(int)
    def netUsageHour(self, hour):
        self._nu["hour"] = -1 if hour == self._nu["hour"] else hour     # a second click: whole day
        self._nu_build()

    # ---- window look (Personalize)
    @Property("QVariantList", constant=True)
    def uiScales(self):
        return list(Theme.UI_SCALES)


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

    @Property("QVariantMap", notify=settingsChanged)
    def ui(self):
        if self._ui_cache is None:                   # built once per change
            self._ui_cache = self._b.ui_style()
        return self._ui_cache

    @Property("QVariantList", notify=settingsChanged)
    def uiAccents(self):
        """The accent choices in the colors of the current mode."""
        light = self._b.settings["ui_mode"] == "light"
        return [{"key": k, "name": n, "hex": lt if light else dk} for k, n, dk, lt in Theme.UI_ACCENTS]

    @Property(str, notify=settingsChanged)
    def density(self):
        return self._b.density()

    @Slot(str)
    def setDensity(self, key):
        if self._b.set_density(key):
            self.settingsTouched()

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
        self._set_cache = self._prev_cache = self._ui_cache = None
        self.settingsChanged.emit()
        self._save.start()
        if self.host:
            self.host.settingsChanged()
        for h in self.hud_hosts:
            h.settingsChanged()
        if self.hud_hosts:
            self.hudStateChanged.emit()
            self._wake.set()                 # the sampler may need to run faster now

    # ---- warnings (see engine.Alerts)
    def _on_alerts(self, new):
        fa = self._b.settings["language"] == "fa"
        for a in new:
            title, tip = (Alerts.FA.get(a["key"], (a["title"], a["tip"])) if fa else (a["title"], a["tip"]))
            self.alertRaised.emit(title, tip)
        self.alertsChanged.emit()

    @Property("QVariantMap", notify=alertsChanged)
    def alerts(self):
        rec = [{"key": a["key"], "title": a["title"], "tip": a["tip"],
                "when": time.strftime("%H:%M", time.localtime(a["t"]))} for a in list(self._b.alerts.recent)]
        return {"on": bool(self._b.settings["alerts_on"]), "recent": rec}

    @Slot(bool)
    def setAlertsOn(self, on):
        self._b.set_setting("alerts_on", bool(on))
        self.settingsTouched()
        self.alertsChanged.emit()

    def _on_bench(self, text):
        fa = self._b.settings["language"] == "fa"
        msgs = {"Benchmark finished": ("بنچمارک تمام شد", "نتیجه را در «جلسه‌ها» ببین."),
                "Benchmark cancelled: no game was started": ("بنچمارک لغو شد", "هیچ بازی‌ای اجرا نشد."),
                "Benchmark stopped: the game was closed before the minute was over":
                    ("بنچمارک متوقف شد", "بازی قبل از تمام شدن یک دقیقه بسته شد.")}
        en = {"Benchmark finished": ("Benchmark finished", "Open Sessions to see the result.")}
        title, body = (msgs.get(text) if fa else en.get(text)) or (text, "")
        self.trayInfo.emit(title, body)
        self.tools._bump("sessions")

    @Slot()
    def clearHistory(self):
        self._b.clear_history()
        self.tools._bump("sessions")
        self.tools._bump("reports")
        self.dashboardChanged.emit()

    @Slot()
    def openDataFolder(self):
        from lmonitor.engine import Paths
        os.makedirs(Paths.CFG_DIR, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(Paths.CFG_DIR))

    # ---- every game keeps its own overlay settings
    @Property("QVariantMap", notify=settingsChanged)
    def gameProfile(self):
        return self._b.game_profile()

    @Slot()
    def forgetGameProfile(self):
        self._b.forget_game_profile()
        self.settingsTouched()

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
        self._b.reset_settings()
        self.settingsTouched()

    # ---- overlay host
    @Property(bool, notify=movingChanged)
    def moving(self):
        return bool(self.host and self.host.moving)

    @Slot(bool)
    def setUiVisible(self, visible):
        """The main window is minimized / hidden: stop preparing data for it."""
        if visible != self._ui_visible:
            self._ui_visible = bool(visible)
            if visible:
                self._wake.set()
                self._trim_once.stop()
            else:
                self._trim_once.start()          # closed / minimized: give the RAM back

    # ---- memory while only the tray / overlays run (see WinApi.trim_memory)
    TRIM_AFTER_MS = 4000                         # after the window was closed
    TRIM_EVERY_MS = 5 * 60 * 1000                # then now and then, if it grew again
    TRIM_ABOVE_MB = 60

    def _trim(self, only_if_big=False):
        if self._ui_visible:
            return
        if only_if_big and (WinApi.memory_mb() or 0) < self.TRIM_ABOVE_MB:
            return
        WinApi.trim_memory()

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
