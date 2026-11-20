# Lmonitor 1.20.0 - a smarter companion, still simple

No new menu items: everything sits in the page it belongs to.

## New
- **A report after every game (Sessions):** the main numbers first - average FPS, 1% and
  0.1% lows (0.1% only with 10,000+ frames), hottest CPU / GPU, average CPU / GPU power,
  time played, frame times - then what slowed the game down in plain words with what to
  do, and every detail behind *Show all details*. *Save as picture* (Pictures\Lmonitor).
- **Compare two sessions** of a game: plain sentences ("Your average FPS increased by 12 %"),
  better in green, worse in yellow, small differences count as the same. Shows what changed
  in between when Lmonitor knows it: graphics driver, power plan, Optimizer changes.
  Different games or sessions under 2 minutes are not compared.
- **Warnings** (Hardware page switch, on by default): very hot CPU / GPU, heating up fast
  without more load, the GPU slowing down because of heat (NVIDIA's own signal), RAM or
  VRAM almost full, a big FPS drop. Shown next to the clock in plain words with what to do;
  once per problem, not again for 15 minutes; the last ones are listed on the Hardware page.
- **Settings for each game** (Overlay page, on by default): change the overlays while a game
  runs and that game keeps them; they come back by themselves next time.
- **Honest sensors:** a sensor that stops answering shows "not available", never an old value.
- **Update notes:** the release's own text is shown before you install. The installer is
  still checked (size, SHA-256); if anything fails the current version stays.
- **Your data and privacy** (About): what is kept on the PC, what goes over the internet
  (only the GitHub update check), and a button that opens the data folder.

## Not changed on purpose
- Dashboard and menu: as in 1.19.
- PC check and Optimizer: already explain each item and already undo every change; left as
  they are.
- PDF export: not added (a picture is enough and needs no extra library).

## Cost
Same PC, same conditions, % of one CPU core (2 runs each): tray 2.29 / 1.93 (1.19.1) vs
1.93 / 1.72 (1.20.0); window on Home 11.25 / 11.14 vs 10.47 / 11.98 - no measurable change.
