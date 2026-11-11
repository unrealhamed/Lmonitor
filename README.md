# Lmonitor

**A gaming overlay and system monitor for Windows.**
It puts a small click-through bar over your game (FPS, 1% lows, CPU / GPU / RAM load, temperatures, power, clocks, network speed) and gives you a full dashboard window with charts, game sessions, diagnostics and safe cleanup tools.

[فارسی](README.fa.md) · [Download](https://github.com/unrealhamed/Lmonitor/releases) · [Report a bug](https://github.com/unrealhamed/Lmonitor/issues/new?template=bug_report.md) · [Request a feature](https://github.com/unrealhamed/Lmonitor/issues/new?template=feature_request.md)

> **Status: early release (v1.17.0).** The new Qt interface and the installer are young and have been tested by the author on one Windows 11 laptop (NVIDIA GPU + Intel CPU). Some sensors may show `n/a` on other hardware. Bug reports are welcome.

## Screenshots

![Lmonitor home page: CPU, GPU, RAM and storage cards, a performance chart and the overlay preview](docs/screenshots/dashboard.png)

| Overlay settings | Optimizer |
|---|---|
| ![Overlay page: live preview of the bar, density, position, appearance and the metrics it shows](docs/screenshots/overlay-settings.png) | ![Optimizer page: quick presets, Windows game settings, power plan, startup programs and undo history](docs/screenshots/optimizer.png) |

## Download and install

1. Open the [**Releases**](https://github.com/unrealhamed/Lmonitor/releases) page and download `Lmonitor_Setup_x.y.z.exe` from the newest release.
2. Run it and follow the wizard. Keep **Install the PawnIO driver** ticked: it installs the sensor driver that CPU temperature and power need on many CPUs. Desktop and Start Menu shortcuts are created.
3. Start **Lmonitor**. Windows asks for administrator rights (needed to read the sensors) - choose *Yes*.
4. Uninstall from *Settings > Apps*. The uninstaller asks whether to delete your settings (default: keep them).

> The installer is not code-signed, so Windows SmartScreen or your antivirus may show a warning. Choose *More info > Run anyway* only if you trust the download source (this repository's Releases page).

## What the overlay can show

| Group | Items |
|---|---|
| **FPS** | FPS, average, 1% low, frametime, live frametime graph |
| **GPU** | usage, temperature, power, clock, VRAM used/total |
| **CPU** | usage, temperature, power, clock |
| **RAM** | usage %, used / total, swap |
| **NET** | download and upload speed (MB/s or Mbps) |

Every item can be switched on or off. *Density* presets (Compact / Balanced / Detailed) change the whole set with one click.

Values turn from white to warning colors with load and temperature (these limits are Lmonitor's own choices, not Windows or vendor limits):

| Level | Usage (CPU / GPU / RAM / VRAM) | Temperature |
|---|---|---|
| Normal | below 30 % - white | below 40 °C - white |
| Warm | 30 % and up - yellow | 40 °C and up - yellow |
| High | 50 % and up - red | 60 °C and up - red |
| Critical | 70 % and up - dark red | 75 °C and up - dark red |

### Customize the overlay
- **Two styles:** *Dark Transparent* and *Liquid Glass* (Windows blur-behind; needs Windows 10 version 1803 or newer, otherwise a translucent dark bar is used).
- **10 backgrounds**, 6 value colors, **opacity**, **text size**, regular/bold weights.
- **Layout:** horizontal or vertical. **Position:** Left, Center, Right or custom - drag the bar with the mouse; the position is saved and kept inside the screen.
- **Order:** reorder the sections.
- **F9 mode:** instead of staying on screen, the bar can slide down from the top edge when you press **F9** (it works while a game has focus), stay for 3 / 5 / 10 seconds, then slide back. F9 is not blocked, so a game that uses F9 still sees the key.
- **Multi-monitor:** choose the display for the bar; if it is unplugged the bar falls back to the main display.
- **Click-through:** the bar never blocks your game input (except while you are moving it).

## The window

- **Home:** CPU / GPU / RAM / Storage cards with status words, a real-time chart (1 min / 5 min / 1 hr / 24 hr), network, and a live overlay preview.
- **Graphs** and **Hardware:** live charts and detailed CPU, GPU, memory, storage, network and system information.
- **Overlay:** every overlay setting above, with a live preview.
- **Sessions:** every game is recorded automatically (a program drawing frames in front, seen by PresentMon; browsers and players are ignored; sessions under 1 minute are dropped). Each session stores average FPS, 1% / 0.1% lows from real frame times, load, temperatures and clocks. Findings only appear when the sensors prove them; a missing sensor is shown as *Unknown*, never as "fine". Data stays in `%APPDATA%\Lmonitor\sessions.db` and can be switched off.
- **Diagnostics:** one click scans the PC (the scan changes nothing) and lists real problems, worst first, each with the measured proof, a plain explanation and shortcuts to fix it (open the right Windows page, or go to Optimizer / Storage).
- **Optimizer:** safe, reversible changes - nothing happens without a second confirming click. Startup programs, power plans, *Gaming* and *Daily* presets (they show what they would change first), and old files in the Windows temp folders. Every change shows before / after and has an **Undo** (temp cleaning cannot be undone and says so). Lmonitor does not disable services, edit the registry in bulk, or overclock.
- **Storage:** shows what takes space. Cleanup measures known cache/temp folders and shows how much can be freed *before* deleting anything. Big folders and large files are only listed and shown in Explorer.
- **Reports:** an explainable health score from the last Diagnostics scan (every deduction is listed with its evidence; checks Windows could not answer are never counted as healthy), before/after of your last two scans, and HTML / JSON export to `Documents\Lmonitor Reports`.
- **Personalize:** 4 app themes (*Default*, *Night*, *Day*, *Aurora*) and 7 accent options.
- **Tray icon:** closing the window keeps the overlay running; the tray icon opens the window, switches the overlay or exits.

Everything is saved automatically in `%APPDATA%\Lmonitor\settings.json`.

## Requirements

- Windows 10 / 11, 64-bit.
- **Administrator rights.** Lmonitor asks for them at start because the hardware sensors (especially CPU temperature) cannot be read without them.
- **CPU temperature and power** need the [PawnIO](https://pawnio.eu) driver on many CPUs (the installer offers it).
- **FPS** is captured with the bundled [PresentMon](https://github.com/GameTechDev/PresentMon). Anti-cheat software in some online games may dislike overlays and hardware drivers - use at your own risk.
- Lmonitor has no telemetry. It contacts the internet only to check GitHub Releases for a newer version (at start and when you press *Check for updates* in *About*) and, if you choose to update, to download the installer from there. The PawnIO download link is opened in your browser only if the bundled installer is missing.

## Run from source

You need Windows, 64-bit Python 3 and the sensor files described in [docs/BUILD.md](docs/BUILD.md) (LibreHardwareMonitor DLLs and PresentMon next to `build_qt.bat`).

```bat
git clone https://github.com/unrealhamed/Lmonitor.git
cd Lmonitor
python -m pip install -r requirements.txt

:: new Qt interface (open the command prompt as Administrator for CPU temperature)
python -m lmonitor.qt

```

`run_qt_dev.bat` starts the Qt interface without administrator rights (useful to look at the UI; CPU temperature will be missing). `run_qt_admin.bat` starts it elevated.

## Build the program and the installer

See [docs/BUILD.md](docs/BUILD.md). In short: `build_qt.bat` builds the program folder, `build_installer_qt.bat` also builds `Lmonitor_Setup_<version>.exe` (needs [Inno Setup 6.3+](https://jrsoftware.org/isdl.php)).

## Project layout

| Path | What it is |
|---|---|
| `lmonitor/engine.py` | the data engine: sensors, settings, history, sessions, diagnostics, optimizer, storage, reports (no window code) |
| `lmonitor/backend.py` | headless layer between the engine and the interfaces |
| `lmonitor/qt/` | the Qt (PySide6 + QML) interface - the main interface from v1.15 |
| `installer/` | Inno Setup script |
| `tools/` | build helper (writes the version info of the exe) |
| `tests/` | development tests (use stand-ins for tkinter / drivers; run `python tests/run_all.py`) |
| `docs/` | architecture, build, release and migration notes |

## Report a bug or suggest a feature

Open an [issue](https://github.com/unrealhamed/Lmonitor/issues). For bugs please include your Windows version, GPU / CPU model, the Lmonitor version (sidebar or *About*) and, if they exist, the files `error.log` / `qt_error.log` in `%APPDATA%\Lmonitor`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and third-party software

[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (sensors, MPL-2.0), [PresentMon](https://github.com/GameTechDev/PresentMon) (FPS, MIT), [PawnIO](https://pawnio.eu) (driver, GPL-2.0 with an exception), PySide6 / Qt, psutil, pythonnet, nvidia-ml-py, Pillow and pystray. Details and notes: [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md). Please read their licenses before redistributing.

Made by a new developer named [unrealhamed](https://github.com/unrealhamed).


