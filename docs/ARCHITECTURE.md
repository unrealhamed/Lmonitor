# Lmonitor architecture (audit, v1.13.1 -> Qt migration)

## Layers

| Layer | Where | Contains | UI imports? |
|---|---|---|---|
| Engine | `lmonitor/engine.py` (~4900 lines) | Paths, Settings, Metrics, Thresholds, WinApi, LibreHardwareHost, CpuReader, GpuReader, MemoryReader, FpsMonitor (PresentMon), DriverManager, SystemInfo, Storage/Network/Battery readers, Telemetry, Recorder, SessionStore/Analyzer/Recorder, Diagnostics (DiagCollector/Analyzer/Runner), Optimizer, Storage (cleanup), Reports, DisplayManager, CardStatus | **None** (tested) |
| Backend facade | `lmonitor/backend.py` | `Backend`: builds the engine headless, `sample()` (worker thread), `dashboard()` (plain dict), `perf(range)` | None |
| Qt UI | `lmonitor/qt/` | `bridge.py` (QObject, sampler thread), `app.py`, `qml/` (tokens, components, pages) | PySide6 |

Rule: the engine never imports a UI module; the Qt UI talks to it through
`Backend` + `Bridge`.

## What was already separate, and what was not

* Sensors, history, sessions, scans, optimizer, storage, reports: pure engine
  classes (worker threads + `busy`/`version` polling). Moved as-is.

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
