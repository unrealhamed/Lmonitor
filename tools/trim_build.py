"""Removes the parts of Qt that Lmonitor never loads from a finished PyInstaller folder.

usage:  python tools/trim_build.py <folder holding _internal>

PyInstaller copies every Qt module, including the web browser engine (about 200 MB).
The list below is what the program really loads while every page is open.
"""
import fnmatch
import os
import shutil
import sys

KEEP_TOP = ("Qt6Core.dll", "Qt6Gui.dll", "Qt6Network.dll", "Qt6OpenGL.dll", "Qt6Qml.dll",
            "Qt6QmlMeta.dll", "Qt6QmlModels.dll", "Qt6QmlWorkerScript.dll", "Qt6Quick.dll",
            "Qt6Widgets.dll", "QtCore.pyd", "QtGui.pyd", "QtNetwork.pyd", "QtOpenGL.pyd",
            "QtQml.pyd", "QtQuick.pyd", "QtWidgets.pyd", "msvcp*.dll", "vcruntime*.dll", "concrt*.dll",
            "pyside6*.dll", "shiboken6*.dll", "*.py", "*.pyi", "*.json")
KEEP_PLUGINS = ("platforms/qwindows.dll", "platforms/qoffscreen.dll", "styles/*", "imageformats/qico.dll")
KEEP_QML = ("QtQml/*", "QtQuick/qmldir", "QtQuick/*.qmltypes", "QtQuick/qtquick2plugin.dll",
            "QtQuick/Window/*", "*.qmltypes")
DROP_DIRS = ("translations", "resources", "typesystems", "include", "glue", "doc", "metatypes")


def size(path):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(path) for f in fs)


def wanted(rel, patterns):
    return any(fnmatch.fnmatch(rel, p) for p in patterns)


def prune(base, patterns):
    for d, _, files in os.walk(base, topdown=False):
        for f in files:
            full = os.path.join(d, f)
            if not wanted(os.path.relpath(full, base).replace("\\", "/"), patterns):
                os.remove(full)
        if d != base and not os.listdir(d):
            os.rmdir(d)


def trim(folder):
    qt = os.path.join(folder, "_internal", "PySide6")
    if not os.path.isfile(os.path.join(qt, "Qt6Core.dll")):
        raise SystemExit("Qt was not found in " + qt)
    before = size(folder)
    for name in os.listdir(qt):
        full = os.path.join(qt, name)
        if os.path.isfile(full) and not wanted(name, KEEP_TOP):
            os.remove(full)
    for name in DROP_DIRS:
        shutil.rmtree(os.path.join(qt, name), ignore_errors=True)
    prune(os.path.join(qt, "plugins"), KEEP_PLUGINS)
    prune(os.path.join(qt, "qml"), KEEP_QML)
    print("trimmed %d MB -> %d MB" % (before / 2**20, size(folder) / 2**20))


if __name__ == "__main__":
    trim(sys.argv[1])
