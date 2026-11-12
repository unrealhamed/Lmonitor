# Lmonitor 1.17.6

Everything since 1.17.0.

## Lighter on games
- The window is drawn on the GPU that drives the screen (on most laptops the integrated one), not on the game GPU.
- A full-screen game in front stops the window completely (no animation, no updates).
- When Lmonitor is not the window in use it runs at lower priority in Windows' efficiency mode.
- The overlay bar no longer resizes itself each time a number gets longer.

## Graph overlay (new)
- Live line charts over the game: FPS, frame time, GPU / CPU temperature, usage and power. Up to 6 charts.
- Two overlays (Graph 1 and Graph 2), each with its own charts, place and look.
- It floats: drag it by its top edge. Clicks on the rest go through to the game.
- Time span from "Real time" (last 10 s, 4 readings a second) to 5 minutes; smooth motion or power saver.
- 7 color themes, gaming or clean style, 3 sizes, column / row / grid.

## Anti-cheat safe mode (new)
- While a known protected game runs (Warzone, Valorant, Fortnite, Apex and others) Lmonitor stops using the sensor driver. CPU temperature, power and clock show `--`; everything else keeps working. On "Automatic" by default (Overlay page).
- Lmonitor never injects into a game or reads game memory. No tool can promise what an anti-cheat accepts.

## Window
- Personalize: 10 themes, 17 accent colors and your own color, interface size 90 - 120 %, corner style, 6 fonts.
- Start with Windows (Personalize): starts at sign-in and waits in the tray.
- A new version is announced by itself (bar on every page and a tray message).
- Persian: the whole window is right-to-left and Lmonitor's own texts are translated.
- "PC check" replaces the Diagnostics and Reports pages (scan, findings, health score, export).
- Fixed: light themes had a dark window background; a dragged overlay jumped back to its old place; no taskbar icon for the pinned app.

## Not verified by the author
- Behaviour inside games with kernel anti-cheat.
- CPU temperature / power / clock and FPS against an independent reference.
- Hardware other than one Windows 11 laptop (RTX 4070 Laptop + Core i7-12700H).

## Install
Download `Lmonitor_Setup_1.17.6.exe` below and run it. It updates an older version in place and keeps your settings. The installer is not code-signed, so Windows SmartScreen may warn.
