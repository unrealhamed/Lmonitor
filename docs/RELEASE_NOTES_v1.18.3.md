# Lmonitor 1.18.3

## New: Network usage
Click the **Network** card on Home: how much you downloaded and uploaded in the last **1, 15 or 30 days**. A bar per day - click a day to see it hour by hour, and click an hour to see which programs used how much.

- The numbers are **Windows' own records** (the same ones as Settings > Network > Data usage), written by Windows about once an hour and kept for 30 - 60 days - so you also see days from before Lmonitor was installed. Windows sometimes writes them hours late; for the time after its newest record, Lmonitor shows its own count (*Measured by Lmonitor*: it reads the real adapters' counters once a minute - totals only, no per-program split).
- Lmonitor reads them only while this page is open (a copy takes a few seconds); nothing runs while you play. Needs administrator rights, like the sensors.
- Only real adapters (Wi-Fi, Ethernet, USB tethering) are counted, so traffic through a VPN is not counted twice. *System (Windows)* is Windows itself and traffic Windows carries for a VPN.

## Fixed (1.18.1)
- Graph overlay over a game: *Frame time* kept switching to `--` and its line had holes (and FPS showed `--` for a moment) at a steady frame rate. PresentMon gets frames from Windows in batches about once a second; frames now get their own time instead of the time they arrived.
- Graphs page: after another page was open, the real-time charts came back with a hole.

Not verified by the author: the frame-time fix inside a game, and the Network usage page in the installed app.

## Install
Download `Lmonitor_Setup_1.18.3.exe` below and run it. It updates an older version in place and keeps your settings.
