# Lmonitor 1.19.1 - much less RAM in the tray

## Fixed
- **RAM while Lmonitor sits in the tray:** after the window had been open once, Lmonitor kept
  ~160-210 MB in RAM even when only the tray icon (and maybe the overlays) were left - mostly
  the graphics driver's and Qt's memory for the closed window. Now, 4 s after the window is
  closed or minimized (and 20 s after a start at sign-in), Lmonitor gives the RAM it does not
  use back to Windows, and again every 5 minutes if it grew above 60 MB.
  Measured in Task Manager: **~160 MB -> ~17 MB** (overlays off), **~30 MB** with the overlay bar on.
  Nothing is lost: opening the window loads what it needs again.
- Graphs: a harmless "checkUpright is not a function" warning after switching pages.

## Also
- New README screenshots of the 1.19 design (dark and light).
