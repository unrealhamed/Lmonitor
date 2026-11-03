"""QML <-> engine glue for the tool pages (Diagnostics, Optimizer, Storage,
Reports, Sessions).

The engine classes do the work in their own worker threads and expose
.busy / .version; this object only starts them, polls those counters while a
tool page is open and hands finished plain dictionaries to QML. Nothing is
polled while no tool page is open.
"""
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from lmonitor.engine import Logger, WinApi

PAGES = ("diag", "opt", "storage", "reports", "sessions")


class Tools(QObject):
    diagChanged = Signal()
    optChanged = Signal()
    storageChanged = Signal()
    reportsChanged = Signal()
    sessionsChanged = Signal()

    def __init__(self, backend, bridge, parent=None):
        super().__init__(parent)
        self._b, self._bridge = backend, bridge
        self._page = ""
        self._state = {p: {} for p in PAGES}
        self._sig = {}
        self._timer = QTimer(self)
        self._timer.setInterval(600)
        self._timer.timeout.connect(self._poll)

    # ---- state the pages read
    def _get(self, name):
        return self._state[name]

    @Property("QVariantMap", notify=diagChanged)
    def diag(self):
        return self._get("diag")

    @Property("QVariantMap", notify=optChanged)
    def opt(self):
        return self._get("opt")

    @Property("QVariantMap", notify=storageChanged)
    def storage(self):
        return self._get("storage")

    @Property("QVariantMap", notify=reportsChanged)
    def reports(self):
        return self._get("reports")

    @Property("QVariantMap", notify=sessionsChanged)
    def sessions(self):
        return self._get("sessions")

    # ---- which page is open
    @Slot(str)
    def setPage(self, name):
        self._page = name if name in PAGES else ""
        if not self._page:
            self._timer.stop()
            return
        b = self._b
        try:
            if name == "opt" and not b.optimizer.refreshed and not b.optimizer.busy:
                b.optimizer.run(b.optimizer.refresh)
            elif name == "storage" and not b.storage.scanned and not b.storage.busy:
                b.storage.run(b.storage.scan_caches)
            elif name == "reports" and b.reports.report is None and not b.reports.busy:
                b.reports.run(b.reports.build)
        except Exception:
            Logger.error("qt tools open")
        self._sig.pop(name, None)
        self._poll()
        self._timer.start()

    def _signature(self, name):
        b = self._b
        if name == "diag":
            r = b.scanner
            return (r.running, r.progress, r.version)
        if name == "opt":
            return (b.optimizer.busy, b.optimizer.version, id(b.optimizer.last))
        if name == "storage":
            s = b.storage
            return (s.busy, s.progress, s.version, id(s.last))
        if name == "reports":
            return (b.reports.busy, b.reports.version, id(b.reports.last))
        return (b.sessions.version, b.sessions.status()[0], b.settings["sessions_on"], self._sess_gen)

    _sess_gen = 0

    def _poll(self):
        name = self._page
        if not name:
            return
        try:
            sig = self._signature(name)
            if self._sig.get(name) == sig:
                return
            self._sig[name] = sig
            self._state[name] = getattr(self._b, "tools_" + name if name != "opt" else "tools_opt")()
            getattr(self, name + "Changed").emit()
        except Exception:
            Logger.error("qt tools poll " + name)

    def _bump(self, name=None):
        self._sig.pop(name or self._page, None)
        self._poll()

    # ---- Diagnostics
    @Slot()
    def diagScan(self):
        self._b.scanner.start()
        self._bump("diag")

    @Slot(str)
    def diagOpen(self, target):
        """Open a Windows settings page for an issue (fixed kinds of target only)."""
        WinApi.open_target(target)

    # ---- Optimizer (every action asks first in the page; here it just runs)
    @Slot()
    def optRefresh(self):
        o = self._b.optimizer
        o.run(o.refresh)
        self._bump("opt")

    @Slot(str, bool)
    def optStartup(self, key, enable):
        o = self._b.optimizer
        o.run(o.set_startup, key, enable)
        self._bump("opt")

    @Slot(str)
    def optPower(self, guid):
        o = self._b.optimizer
        o.run(o.set_power, guid)
        self._bump("opt")

    @Slot(str)
    def optSetting(self, sid):
        o = self._b.optimizer
        o.run(o.set_setting, sid)
        self._bump("opt")

    @Slot(str)
    def optPreset(self, name):
        o = self._b.optimizer
        o.run(o.apply_preset, name)
        self._bump("opt")

    @Slot(int)
    def optUndo(self, cid):
        o = self._b.optimizer
        o.run(o.revert, cid)
        self._bump("opt")

    @Slot()
    def optDismiss(self):
        self._b.optimizer.last = None
        self._bump("opt")

    # ---- Storage
    @Slot()
    def storScanCaches(self):
        s = self._b.storage
        s.run(s.scan_caches)
        self._bump("storage")

    @Slot()
    def storScanFolders(self):
        s = self._b.storage
        s.run(s.scan_folders)
        self._bump("storage")

    @Slot()
    def storScanLarge(self):
        s = self._b.storage
        s.run(s.scan_large)
        self._bump("storage")

    @Slot("QVariantList")
    def storClean(self, ids):
        s = self._b.storage
        s.run(s.clean_many, [str(i) for i in ids])
        self._bump("storage")

    @Slot(str)
    def storRecycle(self, path):
        s = self._b.storage
        s.run(s.recycle, path)
        self._bump("storage")

    @Slot(str)
    def storShow(self, path):
        self._b.storage.show(path)
        self._bump("storage")

    @Slot()
    def storDismiss(self):
        self._b.storage.last = None
        self._bump("storage")

    # ---- Reports
    @Slot()
    def repBuild(self):
        r = self._b.reports
        r.run(r.build)
        self._bump("reports")

    @Slot(str)
    def repSave(self, kind):
        r = self._b.reports
        r.run(r.save, kind)
        self._bump("reports")

    @Slot()
    def repOpen(self):
        self._b.reports.open_folder()

    @Slot()
    def repDismiss(self):
        self._b.reports.last = None
        self._bump("reports")

    # ---- Sessions
    @Slot(int, result="QVariantList")
    def sessionDetail(self, sid):
        try:
            return self._b.session_detail(sid)
        except Exception:
            Logger.error("qt session detail")
            return []

    @Slot(int)
    def sessionDelete(self, sid):
        try:
            self._b.session_store.delete([sid])
        except Exception:
            Logger.error("qt session delete")
        Tools._sess_gen += 1
        self._bump("sessions")

    @Slot(bool)
    def sessionsOn(self, on):
        self._b.set_setting("sessions_on", bool(on))
        self._bridge.settingsTouched()
        self._bump("sessions")
