# Building Lmonitor (program and installer)

Everything here is for **Windows 10 / 11, 64-bit**. The build scripts were written and used by the author on one PC; the Qt build and installer scripts are new in v1.15 (see "Status" at the end).

## 1. What you need

| Thing | Where from |
|---|---|
| Python 3, 64-bit, added to PATH | https://www.python.org/downloads/ |
| Python libraries | the build scripts install them (`pip`) |
| **Inno Setup 6.3+** (only for the installer) | https://jrsoftware.org/isdl.php |
| **Sensor files** (below) | put them in the project folder, next to `build_qt.bat` |

### Sensor files (not stored in this repository)
These third-party files are **not** in the repository (see `docs/THIRD_PARTY.md`). Put them in the project's main folder, next to `build_qt.bat`:

```
LibreHardwareMonitorLib.dll
HidSharp.dll
System.Memory.dll
System.Buffers.dll
System.Numerics.Vectors.dll
System.Runtime.CompilerServices.Unsafe.dll
System.Threading.Tasks.Extensions.dll
PresentMon.exe
PawnIO_setup.exe        <- the build script downloads this one for you
```

- `LibreHardwareMonitorLib.dll` and its companion DLLs come from [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (the library is also published as the *LibreHardwareMonitorLib* NuGet package). **Unverified:** which exact download the author used and which version; keep the same version you tested with.
- `PresentMon.exe` comes from [PresentMon](https://github.com/GameTechDev/PresentMon) (releases page). **Unverified:** the exact release file name and version the author used.
- `PawnIO_setup.exe` is the official installer from `https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe`; the scripts download it if it is missing.

These files are listed in `.gitignore`, so Git never uploads them by mistake.

## 2. Run from source (no build)

```bat
python -m pip install -r requirements.txt
python -m lmonitor.qt          :: Qt interface (open the prompt as Administrator for CPU temperature)
```

## 3. Build the program (Qt, recommended)

Double-click `build_qt.bat`. It checks the files, installs the libraries, and builds with PyInstaller into:

```
_build_qt\dist\Lmonitor\Lmonitor.exe
```

Keep the **whole** `Lmonitor` folder; the exe needs the files next to it. If an old copy of Lmonitor is still running (or its `PresentMon.exe`), the script tries to close it; if Windows refuses, exit Lmonitor from its tray icon or run the prompt as Administrator.

## 4. Build the installer

Install Inno Setup 6.3+, then double-click `build_installer_qt.bat`. It runs `build_qt.bat`, reads the version from `lmonitor/engine.py` (`AppInfo.VERSION`) and creates:

```
_output\Lmonitor_Setup_<version>.exe
```

Upload this file to **GitHub Releases** (see `docs/RELEASING.md`), not to the repository.

The installer keeps the same `AppId` as older versions, so it updates an existing installation. It never writes to `%APPDATA%\Lmonitor`; on uninstall it asks whether to delete your settings (default: keep).

## Status (what is not verified)
- `build_qt.bat` / `build_installer_qt.bat` (Qt): written for v1.15. At the time this package was prepared the first Qt build had hit a *locked old build folder* error (a running copy of the program) that the script now handles; a finished Qt build and installer have **not** been confirmed by the author yet.
- The tests in `tests/` do not build anything.
