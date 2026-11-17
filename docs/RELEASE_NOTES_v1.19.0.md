# Lmonitor 1.19.0 - a new look

A full redesign of the window, with fewer and clearer settings. Everything Lmonitor did
before still works; menus and options stay where they were.

## New
- **New design ("Slate")** for every page: flat cards, clear type (Segoe UI Variable),
  Windows' own icons in the menu, new switches, buttons, sliders and choices.
- **Light and Dark** - one design made for both. Text contrast checked (body text 7:1 or more,
  secondary text and text on buttons 4.5:1 or more).
- **New Home:** four cards (CPU, GPU, memory, storage) with a centered temperature gauge,
  the performance chart, *Right now*, **Network** (adapter, link speed, since start-up, usage
  history) and **This PC** (up time, battery, power plan, PC check score).
- **Simpler Personalize:** Light / Dark, six accent colors, interface size 100 / 110 / 125 %,
  language and Start with Windows.
- *What's new* shows these changes once after the update.

## Removed (and why)
- **10 app themes, 17 accents + own hue, 3 corner styles, 6 fonts, 90 % size** - too many
  choices that mostly gave a worse looking window. Old settings move over by themselves
  (light themes -> Light, others -> Dark, accents to the nearest new one, 90 -> 100 %, 120 -> 125 %).
- **Overlay: Liquid glass, 10 backgrounds, 6 value colors, regular / bold** - the glass needed
  Windows blur calls behind a game window and was hard to read over bright games. The overlay
  now has one dark, see-through look; opacity and text size stay.
- Unused window parts (old cards, rings and charts) were deleted.

## Faster
Same PC, same conditions (% of one CPU core): tray only 3.94 % -> 2.62 %,
window open on Home 12.06 % -> 9.00 %.
