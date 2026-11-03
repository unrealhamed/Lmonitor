> **Historical development log.** The status tables in the first half were written while the Qt interface was being built and are outdated (they still say "not run" / "not started" for parts that were finished later). The newest status is at the bottom of this file and in `docs/RELEASE_NOTES_v1.15.2.md`.

# Migration plan: Tk -> PySide6 / QML (staged)

## Decision
PySide6 + Qt Quick is materially better here: GPU-rendered scene graph,
gradients, real transparency, smooth transitions, DPI scaling, reusable
components. The monitoring engine stays Python. The Tk window stays working
until the Qt window reaches parity, so nothing is lost on the way.

## Blocker found (honest status)
The environment where this work is done has no access to PyPI, so PySide6
could **not** be installed and **no QML or Qt Python code has ever been run**
by the author. Everything below marked "written, not run" must be tried on
your Windows PC first (`run_qt_dev.bat`). Expect small QML fixes in the first
run; send the console output.

## Phases and state

| Phase | Goal | State |
|---|---|---|
| 1 Audit | architecture, risks | **done** (docs/ARCHITECTURE.md) |
| 2a Engine split | `lmonitor/engine.py`, no UI imports | **done, tested** (17 test files green: 3, overlay, 4-18) |
| 2b Shell + design system | Qt app, tokens, sidebar, navigation | written, **not run** |
| 3 Dashboard | cards, sparklines, performance chart + ranges, status, network | written, **not run** |
| 4 Overlay + settings | Qt overlay window (click-through, multi-monitor, F9), font/colors/opacity/presets, live preview, persistence | **not started** (largest risk) |
| 5 Remaining pages | Performance, Hardware, Sessions/Diagnostics, Tools, Reports | **not started** |
| 6 Packaging | PyInstaller + Inno for Qt, README, release notes | `build_qt.bat` drafted, **not run** |

Pages are added only when their feature exists in the Qt UI: today the
sidebar has Dashboard and About.

## Risks
1. **Overlay** is a Tk Toplevel with Win32 styles. A Qt overlay
   (frameless, `WindowTransparentForInput`, always-on-top, DWM blur) must be
   re-verified in real games and on multi-monitor setups. Until then the Tk
   overlay is the only overlay; the Qt window does not control it.
2. Running Tk and Qt in one process is not supported. The Qt app will not
   start the Tk overlay; it needs its own overlay (Phase 4).
3. PyInstaller + PySide6 (QML plugins, size ~80-150 MB), antivirus false
   positives, `--uac-admin` needed for sensors (same as now).
4. Canvas-based charts are fine at 1 Hz; shader effects (MultiEffect glow)
   are deliberately not used yet to keep GPU use low.
5. Behavior parity for the Tools pages (Optimizer/Storage/Reports): large
   UI surface; they depend only on engine classes, so migration is mostly
   layout work.

## Run order (as requested)
1. `python -m lmonitor.qt` from source (`run_qt_dev.bat`) - fix until it works.
2. Only then `build_qt.bat`.

## Status update (v1.14.0-dev)

| Phase | State |
|---|---|
| 1 Audit / 2 Shell + design system | Done. Dashboard confirmed working on the author's PC. |
| 3 Dashboard | Written: welcome header with Overlay switch, 4 cards, performance chart, status, network, overlay preview, quick actions. **Not yet run after the latest polish (Unverified).** |
| 4 Overlay + settings | Written (`qt/overlay.py`, `OverlayWindow.qml`, `OverlayPage.qml`). **Never run (Unverified):** click-through, F9, multi-monitor, DWM blur must be checked on a real PC / in a game. |
| 5 Performance + Hardware pages | Written (`PerformancePage.qml`, `HardwarePage.qml`). **Not run (Unverified).** |
| 6 Packaging | `build_qt.bat` drafted, never run. |

Compatibility: both UIs use the same engine (`lmonitor/engine.py`, no UI imports) and the same
`%APPDATA%\Lmonitor\settings.json`; old files (including the removed "profiles" keys) still load.
Run only one UI at a time (Tk `monitor.py` or Qt `run_qt_dev.bat`). The Tk overlay remains the proven one.
Not migrated yet to Qt: Diagnostics, Optimizer, Storage, Reports, Sessions (still in Tk).

## v1.14.1-dev - new look
Qt UI redesigned after the "IQON" reference: neutral black panels, green accent, temperature rings,
status dots, Home with welcome card, Overlay page in two balanced columns (font list removed),
Performance page with six chart tiles (min / avg / max from the same readings), Hardware page as
section cards in two columns. All still **Unverified on real hardware** - run `run_qt_dev.bat`.
Not copied from the reference because there is no real feature behind it: Tooltip Mode, user avatar/email,
"Talk to a professional", Optimize / Debloat pages.

## v1.14.4-dev
- Qt tool pages ported from 1.13.1: Sessions, Diagnostics, Optimizer (presets, startup, power plan, game settings, history + undo),
  Storage (drives, cache cleaner, big folders / large files), Reports (HTML / JSON). They use the same engine classes as the
  classic window; every change asks first and is logged.
- Dropped as low value: Typography / Profiles / Display / Metrics settings pages of the Tk window (the Overlay page covers them).
- Resource use: sensor update at most ~1/s, overlay sensors at the Refresh interval, recorder reuses the telemetry reading,
  nothing is prepared while the window is hidden, charts slide from one shared 25 fps timer only while the window is in front.
- All Qt/QML parts are Unverified on real hardware until run on Windows.

## v1.15.0 (final)
Personalize page (app theme + accent via `Backend.ui_style`, Tokens made writable and driven by Bindings in Main.qml), Density on the Overlay page (`Backend.set_density`), `-dev` suffix removed. Tests: test_phase20.
