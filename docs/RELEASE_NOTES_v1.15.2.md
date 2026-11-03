# Lmonitor v1.15.2

First release with the **new Qt interface** as the main interface. The classic Tk interface (`monitor.py`) is still in the source and uses the same settings.

## New
- New interface (PySide6 + QML) with a dark, panel-based design: Home, Performance, Hardware, Overlay, Sessions, Diagnostics, Optimizer, Storage, Reports, Personalize and About pages.
- Home dashboard with CPU / GPU / RAM / Storage cards, status words, a real-time chart and a live overlay preview.
- Overlay page: position and layout, text size, Liquid Glass or dark look, 10 backgrounds, value colors, regular/bold weights, density presets (Compact / Balanced / Detailed), what the bar shows (with animated reordering), F9 mode, monitor choice, live preview.
- Personalize page: 4 app themes (Default, Night, Day, Aurora) and 7 accent options.
- Sessions, Diagnostics, Optimizer, Storage and Reports pages ported from the classic interface; each Diagnostics problem has shortcuts to fix it (Optimizer / Storage / the right Windows page).
- Tray icon: closing the window keeps the overlay running; open, switch the overlay or exit from the icon. Only one copy of the program runs at a time.
- Installer script for the Qt build (`build_installer_qt.bat`).

## Changed
- Lower resource use: sensors are read less often while the window is hidden, history is recorded once per 5 s, and the CPU reader is throttled.

## Fixed
- Overlay and Home pages failed to load because of QML naming problems.

## Known limitations
- Early release: tested by the author on one Windows 11 laptop (NVIDIA GPU + Intel CPU). Other hardware may show `n/a` for some sensors.
- The Day (light) theme was not checked on a real screen; some small colors may look better in the dark themes.
- The installer is not code-signed; Windows SmartScreen may warn.
- CPU temperature needs administrator rights and, on many CPUs, the PawnIO driver.
