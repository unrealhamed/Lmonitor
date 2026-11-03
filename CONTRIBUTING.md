# Contributing to Lmonitor

Thank you for your interest! Lmonitor is a small project by a new developer, so friendly and clear contributions are very welcome.

## Ways to help
- **Report a bug** or a missing sensor: open an [issue](https://github.com/unrealhamed/Lmonitor/issues) with the bug template.
- **Suggest a feature**: open an issue with the feature template. Please explain the problem you want solved, not only the solution.
- **Send a fix**: fork the repository, make your change on a branch, and open a pull request.

## Ground rules
- **No fake values.** If a sensor cannot be read, show `--`, `n/a` or *Unknown*. Never show a made-up number or a button that does nothing.
- **Nothing changes in Windows without the user's confirmation**, and every change must be reversible or say clearly that it is not.
- **No telemetry** and no network calls without a clear reason.
- Keep the **engine** (`lmonitor/engine.py`) free of any window / UI code. Interfaces talk to the engine through `lmonitor/backend.py`.
- Settings are shared by both interfaces (`%APPDATA%\Lmonitor\settings.json`). Do not break old settings files.
- Mark anything you could not test on real Windows hardware as *Unverified* in your pull request.

## Run the tests
The tests use small stand-ins for tkinter, the GPU driver and Windows-only parts, so they also run without a GPU:

```bat
python -m pip install psutil pillow
python tests/run_all.py
```

The QML interface cannot be tested by these tests - please run it (`run_qt_dev.bat`) and describe what you checked.

## Pull request checklist
- [ ] The change is small and focused on one thing.
- [ ] `python tests/run_all.py` still passes.
- [ ] New behavior is described in the pull request (and in the README if users will notice it).
- [ ] No personal data, passwords or large binaries are included.
