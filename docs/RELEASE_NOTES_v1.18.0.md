# Lmonitor 1.18.0

Everything since 1.17.7: a fix for freezes under full load, MSI Afterburner, and a check of the whole program for bugs and wasted work.

## Fixed
- **Freeze under full load:** when a benchmark (FurMark) or a game start kept every core busy, the overlays and the window stood still for 2 - 6 seconds. Cause: some Windows readings (network counters, the program list) held Python's lock for up to 4 s, and every part of Lmonitor waited. They are now read straight from Windows on their own threads, and Lmonitor runs at *above normal* priority. Measured with FurMark's CPU burner on the author's laptop: new overlay numbers every 0.26 s, no pause longer than 0.45 s.
- **MSI Afterburner / RivaTuner:** Afterburner's overlay was drawn inside Lmonitor's windows and misbehaved in games while Lmonitor was open. Lmonitor now gets RivaTuner's own *do not hook* profile (the same kind RivaTuner ships for HWiNFO and Discord). The installer writes it and the uninstaller removes it.
- The Hardware page could freeze the window for up to ~0.5 s under load: it waited for the sensor lock every second.
- An error at exit (*'MethodObject' object is not callable* in `error.log`): a sensor thread still used the sensor library while Lmonitor closed. Now the readers stop first and the library is closed cleanly, which also lets go of the PawnIO driver.
- *Start with Windows* no longer freezes the window while Windows' Task Scheduler answers.

## Lighter
Measured on the author's laptop, % of one CPU core:

| | 1.17.8 | 1.18.0 |
|---|---|---|
| Tray icon only | 1.41 | 0.55 |
| Overlay bar | 2.03 | 0.94 |
| Graph overlay, real time, smooth | 11.0 | 8.1 |
| Graph overlay, real time, power saver | 3.05 | 1.87 |
| Graph overlay, 1 minute | 3.59 | 1.72 |
| Window open on Home (Persian) | 2.69 | 1.44 |

- Overlays that are switched off no longer check the keyboard 25 times a second.
- The real-time graph overlay moves in half-pixel steps (45 a second instead of 60).
- Charts draw at most ~70 steps a second on 120 / 144 / 165 Hz screens.
- The Home and Graphs pages no longer rebuild their rows on every reading.
- Removed code that did nothing visible, including a 24-hour history that no page showed.

Not verified by the author: the effect inside real games, and the Afterburner fix with Afterburner's overlay running in a game.

## Install
Download `Lmonitor_Setup_1.18.0.exe` below and run it. It updates an older version in place and keeps your settings.
