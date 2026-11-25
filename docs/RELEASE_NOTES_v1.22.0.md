# Lmonitor 1.22.0 - smarter Home, one row per game, tidier overlay, new installer

No new menu items or pages.

## Home
- Redesigned layout (same colors and identity): a welcome card with the state of the PC in four
  lines (temperatures, PC check, stability, graphics driver) and **Smart insights**; processor,
  memory, storage, graphics card and network cards; chart, Right now and This PC below.
- **Start with Windows** sits next to the Overlay / Graph overlay switches (same setting as in
  Personalize).
- **Smart insights** - built only from what Lmonitor measured: a game running better or worse than
  its usual, hotter than usual, almost-full graphics memory, warnings of the last day, unexpected
  restarts from PC check, and **what changed** on the PC (graphics driver, Windows build,
  processor, graphics card, RAM - a small local baseline) with how each game ran before / after
  across comparable sessions. A change is never named as the cause.

## Sessions
- **One row per game** (never two games in one row) with the number of sessions, total time and
  whether it runs as usual (its "fingerprint": the middle of up to 5 earlier sessions). The arrow
  opens its sessions; **Select** deletes several games / sessions at once, after asking.
- **One launch = one session**: alt-tab or minimize no longer ends the session (it pauses while
  the game still runs), and frames are not lost when PresentMon forgets a game in the background.
- Reports: **what would likely help** (directions from measured data, never numbers), the game
  getting slower during a session (and whether heat explains it), background programs with what
  made them heavy (processor, memory or disk), more fingerprint metrics (1% low, GPU usage,
  graphics memory).
- A name you give a game applies to all its sessions (1.21.4).

## Overlay
- The background always fits its numbers. The window still only grows (resizing a window above a
  game every second costs the game frames), but the background used to fill the whole window and
  stayed too wide; now it hugs the content, and the window shrinks again after the content stayed
  smaller for a while.
- **Left / right** placement sits flush against the screen edge (there was a 20 px margin), with
  square corners on that side.

## Installer
- Windows 11 style that follows Windows' light / dark mode, Lmonitor's own pictures (made by
  `tools/make_installer_art.py` at build time), plain texts, fewer pages (no "ready" page), the
  desktop icon is optional, clearer messages. A test build (`/DTestBuild`) can be installed next to
  the real one to check the installer.

## Text
- About: spelling corrected; shorter admin note on the processor card; new texts in Persian.

## Not added on purpose
- Per-process GPU / VRAM use: Windows gives no reliable per-program numbers here; processor,
  memory and disk per program are measured.
- An online / AI service: all analysis is local and rule-based.
