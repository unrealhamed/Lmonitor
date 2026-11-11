# Lmonitor v1.17.0

Smoother graphs, more accurate readings, a Persian interface and a much smaller installer. Includes the in-app update check from v1.16.0.

## New
- **Persian interface.** Choose the language on the *Personalize* page.
- **Graphs page** replaces the Performance page and adds RAM and network charts.
- Click a chart to enlarge it and draw other lines on top of it for comparison.
- **Update check (from v1.16.0):** *About* page checks GitHub Releases, then downloads and installs the new version. The sidebar shows when an update is available. If the GitHub API is rate limited, the check falls back to the `releases/latest` link.

## Changed
- Charts scroll at a constant speed. A new point is drawn outside the plot and rolls in, so nothing pops in at the edge.
- Installer size cut from 131 MB to 40 MB by leaving out unused Qt modules.
- The classic Tk interface (`monitor.py`) and its build scripts were removed. The Qt interface is the only interface.

## Fixed
- Network speed counted VPN traffic twice.
- GPU memory included memory reserved by the driver; it now matches `nvidia-smi`.
- The Home chart lost a point while it slid out.
- Holes and shape changes in charts caused by readings tied to the current time.

## Known limitations
- Tested by the author on one Windows 11 laptop (NVIDIA GPU + Intel CPU). Other hardware may show `n/a` for some sensors.
- The installer is not code-signed; Windows SmartScreen may warn.
- CPU temperature needs administrator rights and, on many CPUs, the PawnIO driver.
