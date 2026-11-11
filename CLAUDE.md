# Lmonitor – notes for Claude sessions

Gaming overlay + system monitor for Windows. Python engine + Qt (PySide6/QML) UI, packaged with PyInstaller and an Inno Setup installer. The owner works in Persian; reply in Persian unless asked otherwise.

## Layout
- `lmonitor/engine.py` – sensors, WinApi, settings; `AppInfo.VERSION` is the single version number (currently **1.17.0**).
- `lmonitor/backend.py`, `lmonitor/graphs.py` – data feed and chart history.
- `lmonitor/updater.py` – update check / download / silent install from GitHub Releases.
- `lmonitor/qt/` – Qt interface (`bridge.py`, `qml/Main.qml`, `qml/pages/*`, `qml/components/*`). Persian strings: `qml/Lmonitor/fa.js` + `Tr.qml`.
- `tests/run_all.py` – runs `tests/test_phase*.py`. `installer/Lmonitor.iss` – Inno Setup script.
- Build (Windows only): `build_qt.bat`, `build_installer_qt.bat`; `tools/trim_build.py` trims unused Qt modules. Dev run: `run_qt_dev.bat`.
- Docs: `docs/BUILD.md`, `docs/RELEASING.md`, `docs/ARCHITECTURE.md`.

## Running tests in a Linux cloud container
`pip install psutil nvidia-ml-py PySide6` then `python tests/run_all.py`. Expect 5/6 ok: `test_phase18.py` needs `ctypes.windll` (Windows only). Real builds and hardware checks happen on the owner's Windows PC (Remote Control session).

## History of work so far
- **v1.15.x** – Qt interface became the main UI; installer with PawnIO driver; release notes `docs/RELEASE_NOTES_v1.15.2.md`.
- Issue templates (PR #1), screenshots in README / README.fa (PR #3).
- **v1.16.0** (PR #4) – in-app update check and install from GitHub Releases; falls back to the `releases/latest` redirect when the GitHub API is rate limited; test `tests/test_phase21.py`.
- **v1.17.0** (commit 0594045, on main, 2026-11-09):
  - Graphs: constant-speed scrolling, new points roll in from outside the plot, click a chart to enlarge and overlay other lines, fixed dropped points / holes; Performance page merged into Graphs (with RAM and network).
  - Accuracy: network no longer double-counts VPN traffic; GPU memory excludes driver-reserved memory (matches nvidia-smi).
  - Persian UI language, chosen on the Personalize page.
  - Cleanup: removed the classic Tk interface (`monitor.py`, `build.bat`, `build_installer.bat`) and unused engine code; installer shrank 131 MB → 40 MB.

## Open items
- Owner uploads `Lmonitor_Setup_1.17.0.exe` as GitHub release `v1.17.0` themself.
- README.md / README.fa.md status line still says v1.15.2; there is no `docs/RELEASE_NOTES_v1.17.0.md` yet.
