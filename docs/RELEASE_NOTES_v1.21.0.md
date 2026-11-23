# Lmonitor 1.21.0 - reliable start, benchmark, what limited your FPS

No new menu items or pages.

## Fixed
- **Start with Windows** (reported by users):
  - The Windows task could get lost (an uninstall removes it); since 1.20.2 Lmonitor remembers
    the choice and makes the task again at its next start.
  - At sign-in the taskbar is often not ready yet; Lmonitor then made no tray icon at all and
    ran invisibly. Now it tries again every 2 s for 3 minutes, then opens its window.
  - Every start is noted in `%APPDATA%\Lmonitor\startup.log` (by Windows / by hand).
- `error.log` stopped for good at 200 KB; now it starts again (the old one is kept once), and
  lines carry the date. Sensor-reader errors while Lmonitor closes are no longer logged.

## New
- **Run a benchmark** (Sessions): one minute of the game in front, the same way every time.
  Works even when "Record games" is off. Benchmarks are compared only with benchmarks.
- **What limited the frame rate** in every report: graphics card at full power (normal),
  graphics card power limit (NVIDIA's own signal), or spare graphics power (then the
  processor, an FPS limit / V-Sync or the game) - worded as "may" / "probably", never certain
  without evidence, and only with a measured frame rate.
- **The same game over time**: FPS and hottest temperatures against your usual (median of up
  to 5 earlier sessions).
- **Windows updates** appear under "what changed" when comparing sessions.
- **PC check report**: This PC (processor, graphics card and driver, memory, Windows), which
  sensors work, and Lmonitor's own recent errors. Still saved only on your PC.
- **Delete my history** (About > Your data and privacy): game sessions, PC check results and
  network counts. Settings and the Optimizer's undo list stay.
- Sessions keep 200 summaries (samples only for the newest 60), so the history stays small.

## Checked and left as they were
- PC check already reads unexpected shutdowns, blue screens, hardware (WHEA), graphics driver
  and disk errors of the last 7 days, explains them plainly and compares two scans.
- Overlay: density presets (Compact = minimal), warnings for big FPS drops (1.20) and
  per-game settings already cover "overlay intelligence"; nothing added.

## Cost
Same PC, % of one CPU core, 2 runs each: tray 1.25 / 1.35 (1.20.1) vs 1.09 / 1.72 (1.21.0);
window 8.38 / 8.07 vs 8.44 / 7.76 - no measurable change.
