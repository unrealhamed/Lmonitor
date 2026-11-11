# How to publish a new version

Short version: change the version number, run the tests, build the installer, tag it, upload the installer to **Releases**.

## 1. Prepare
1. Edit `lmonitor/engine.py`, class `AppInfo`: `VERSION = "1.17.0"` -> your new number (for example `1.17.1`). This one number is used by the program, the exe's version info, the installer and the *About* page.
2. Update `docs/RELEASE_NOTES_vX.Y.Z.md` (copy the previous file and edit it) and the version line in `README.md` / `README.fa.md`.
3. Run `python tests/run_all.py`. Every line should say `ok`.

## 2. Build
1. Run `build_installer_qt.bat` (see `docs/BUILD.md`).
2. Install the result `_output\Lmonitor_Setup_<version>.exe` on your own PC and check: the program starts, the tray icon appears, the overlay works, Uninstall works. **Do this before publishing.**

## 3. Publish on GitHub
1. Upload your changed files to the repository (see the upload guide).
2. On GitHub: *Releases > Draft a new release*.
3. *Choose a tag*: type `v1.17.1` and choose *Create new tag on publish*. Target: `main`.
4. Release title: `Lmonitor v1.17.1`. Description: paste `docs/RELEASE_NOTES_v1.17.1.md`.
5. Drag `Lmonitor_Setup_1.17.1.exe` into the *Attach binaries* box and wait until the upload finishes.
6. Tick *Set as the latest release* and press **Publish release**.

## 4. After publishing
- Open the Releases page in a private/incognito window and download the file to check that it works for others.
- Optionally add the SHA-256 of the installer to the release text: in a command prompt run `certutil -hashfile Lmonitor_Setup_1.17.1.exe SHA256`.
- Never upload the installer into the repository itself, only to Releases.
