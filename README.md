# LMonitor

LMonitor is a Windows hardware-monitoring application with a customizable in-game overlay and a separate dashboard.

> **Release status:** Replace this section with the exact current version and verified download link before publishing.

## Features

Only list features that are implemented and tested in the published version. Update this list to match the actual release.

- Hardware monitoring overlay
- Customizable appearance and positioning
- Separate dashboard

## Download and install

1. Open the repository's **Releases** page.
2. Download the latest `Lmonitor_Setup_<version>.exe` installer.
3. Run the installer and follow its instructions.
4. If Windows displays a security warning, verify that the installer came from this official repository before deciding whether to continue.

**Releases:** https://github.com/unrealhamed/Lmonitor/releases

## Screenshots

Add genuine screenshots of LMonitor to `docs/screenshots/` and embed them here, for example:

```md
![LMonitor overlay](docs/screenshots/overlay.png)
```

## Run from source

The source entry point is expected to be `monitor.py`. The exact Python version and dependencies have not been verified in this template.

1. Install a compatible Python version after confirming the project's requirements.
2. Install dependencies listed in `requirements.txt`.
3. Run:

```bash
python monitor.py
```

Some hardware-monitoring features may require administrator privileges or additional tools. Document the actual requirements here after testing.

## Project structure

- `monitor.py` — application source
- `assets/` — icons and image assets used by the application
- `docs/screenshots/` — screenshots for documentation
- `installer/` — installer-related documentation or scripts

## Contributing and bug reports

Please use GitHub Issues to report reproducible bugs or suggest improvements. Include your Windows version, LMonitor version, steps to reproduce, and relevant screenshots or logs. Do not post personal information or sensitive system data.

## License

See `LICENSE`. Confirm that the selected license matches your intentions and that you have the right to license all included code and assets.
