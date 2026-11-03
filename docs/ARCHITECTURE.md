# Lmonitor architecture (audit, v1.13.1 -> Qt migration)

## Layers

| Layer | Where | Contains | UI imports? |
|---|---|---|---|
| Engine | `lmonitor/engine.py` (~4900 lines) | Paths, Settings, Metrics, Thresholds, WinApi, LibreHardwareHost, CpuReader, GpuReader, MemoryReader, FpsMonitor (PresentMon), DriverManager, SystemInfo, Storage/Network/Battery readers, Telemetry, Recorder, SessionStore/Analyzer/Recorder, Diagnostics (DiagCollector/Analyzer/Runner), Optimizer, Storage (cleanup), Reports, DisplayManager, CardStatus | **None** (tested) |
| Backend facade | `lmonitor/backend.py` | `Backend`: builds the engine headless, `sample()` (worker thread), `dashboard()` (plain dict), `perf(range)` | None |
| Classic UI | `monitor.py` (~5000 lines) | Tk: Overlay (the bar), SettingsWindow, widgets, TrayIcon, App (timers, wiring) | Tk, PIL, pystray |
| Qt UI | `lmonitor/qt/` | `bridge.py` (QObject, sampler thread), `app.py`, `qml/` (tokens, components, pages) | PySide6 |

Rule: the engine never imports a UI module; UIs only talk to the engine
(Tk through `App`, Qt through `Backend` + `Bridge`).

## What was already separate, and what was not

* Sensors, history, sessions, scans, optimizer, storage, reports: pure engine
  classes (worker threads + `busy`/`version` polling). Moved as-is.
* Coupled to the Tk window and left in `monitor.py`: `Overlay` (a Tk Toplevel
  with Win32 click-through / blur calls), `MetricsUpdater` (turns numbers into
  overlay text), `RevealController` (F9 slide), `App` (owns the Tk root and the
  timers). `DriverManager` asked questions through Tk message boxes: it now
  calls `engine.ask_yes_no`, which defaults to the Tk dialog and can be
  replaced by a UI.
* Duplicated UI-side logic found during the audit: status words of the
  dashboard cards. Now one `CardStatus` class in the engine, used by both UIs.
  The text formatting of card sub-lines is still duplicated (Tk `_update_dashboard`
  and `Backend.dashboard`/QML) - to be removed when the Tk dashboard retires.

## Data flow in the Qt UI

```
worker thread: Backend.sample() -> Backend.dashboard(range) -> Signal(dict)
UI thread:     Bridge._on_sampled -> property `dashboard` -> QML bindings
```
No hardware call ever runs on the UI thread. Changing the chart range only
re-reads in-memory history.

## Settings
Same `%APPDATA%\Lmonitor\settings.json` through `Settings` (validated, unknown
keys dropped). The Qt UI adds no new keys yet.

## Known limits of this audit
Read from source only. Nothing was run on Windows or with real sensors; the
Qt layer has not been executed at all (see MIGRATION_PLAN.md, "Blocker").
