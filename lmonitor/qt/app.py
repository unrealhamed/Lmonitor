"""Starts the Qt window. Dev run:  python -m lmonitor.qt"""
import os
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QIcon, QWindow
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PySide6.QtQml import QQmlApplicationEngine


def qml_dir():
    if getattr(sys, "frozen", False):              # PyInstaller build
        base = os.path.join(sys._MEIPASS, "lmonitor", "qt")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "qml")


def _fail(text):
    """Show the error where a double-clicked program can be seen."""
    try:
        d = os.path.join(os.environ.get("APPDATA", "."), "Lmonitor")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "qt_error.log"), "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass
    print(text)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text[-1500:], "Lmonitor (Qt) error", 0x10)
    except Exception:
        pass


def main():
    try:
        return _run()
    except SystemExit:
        raise
    except BaseException:
        import traceback
        _fail(traceback.format_exc())
        return 1


def _make_tray(app, win, bridge, backend, ico):
    """Icon next to the clock: open the window, switch the overlay, exit."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    tray = QSystemTrayIcon(ico, app)
    tray.setToolTip("Lmonitor")
    menu = QMenu()
    a_open = QAction("Open Lmonitor", menu)
    a_ovl = QAction("Show overlay", menu)
    a_ovl.setCheckable(True)
    a_exit = QAction("Exit", menu)
    menu.addAction(a_open)
    menu.addAction(a_ovl)
    menu.addSeparator()
    menu.addAction(a_exit)

    def show_window():
        if win.visibility() == QWindow.Visibility.Minimized:
            win.showNormal()
        else:
            win.show()
        win.raise_()
        win.requestActivate()

    a_open.triggered.connect(show_window)
    a_ovl.triggered.connect(lambda on: bridge.setSetting("on", bool(on)))
    a_exit.triggered.connect(app.quit)
    menu.aboutToShow.connect(lambda: a_ovl.setChecked(bool(backend.settings["on"])))
    tray.activated.connect(lambda r: show_window() if r in (
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick) else None)
    tray.setContextMenu(menu)
    tray.show()
    app._tray_menu = menu              # keep references alive
    told = []

    def on_visibility(_v=None):
        if not win.isVisible() and not told:
            told.append(1)
            tray.showMessage("Lmonitor", "Still running here. Click the icon to open it, "
                             "right-click to exit.", QSystemTrayIcon.MessageIcon.Information, 4000)
    win.visibleChanged.connect(on_visibility)
    return tray


def _run():
    from lmonitor.engine import WinApi
    from lmonitor.backend import Backend
    from lmonitor.qt.bridge import Bridge
    from lmonitor.qt.overlay import OverlayHost
    WinApi.setup()
    if "--no-admin" in sys.argv:       # dev run: UI only, no CPU temperature
        WinApi.admin = WinApi.is_admin()
    else:
        WinApi.ensure_admin()          # sensors need admin (same as the Tk app)
    WinApi.single_instance()           # a second copy just exits (same as the Tk app)
    app = QApplication(sys.argv)
    app.setApplicationName("Lmonitor")
    app.setQuitOnLastWindowClosed(False)   # closing the window keeps the overlay + tray
    from lmonitor.engine import Paths
    ico = QIcon(os.path.join(Paths.HERE, "Lmonitor.ico"))
    if not ico.isNull():
        app.setWindowIcon(ico)
    backend = Backend()
    bridge = Bridge(backend)
    engine = QQmlApplicationEngine()
    engine.addImportPath(qml_dir())
    engine.warnings.connect(lambda errs: [bridge.addQmlError(e.toString()) for e in errs])
    engine.rootContext().setContextProperty("backend", bridge)
    engine.rootContext().setContextProperty("tools", bridge.tools)
    engine.load(QUrl.fromLocalFile(os.path.join(qml_dir(), "Main.qml")))
    if not engine.rootObjects():
        _fail("The QML interface failed to load. Look at the lines above "
              "(QML errors are printed in this console).")
        return 1
    host = OverlayHost(bridge, backend)
    bridge.host = host
    engine.load(QUrl.fromLocalFile(os.path.join(qml_dir(), "OverlayWindow.qml")))
    if len(engine.rootObjects()) < 2:
        _fail("The overlay window failed to load (see the QML errors above). "
              "The main window still works.")
    else:
        host.attach(engine.rootObjects()[1])
    app.aboutToQuit.connect(bridge.stop)
    tray = _make_tray(app, engine.rootObjects()[0], bridge, backend, ico)
    bridge.start()
    return app.exec()
