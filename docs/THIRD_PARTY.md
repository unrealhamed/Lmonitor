# Third-party software

Lmonitor uses the following projects. **Their files are not stored in this repository.** The build scripts expect some of them next to `build_qt.bat` (see `docs/BUILD.md`), and the installer and the program bundle them. Licenses below were read from each project's GitHub page when this package was prepared; always check the project's own `LICENSE` before you redistribute.

| Project | Used for | License | Status |
|---|---|---|---|
| [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (`LibreHardwareMonitorLib.dll`) | hardware sensors | MPL-2.0 (stated on its GitHub page) | verified on the project page |
| [PresentMon](https://github.com/GameTechDev/PresentMon) (`PresentMon.exe`) | FPS capture | MIT, "Copyright (C) 2017-2024 Intel Corporation" (stated on its GitHub page); the MIT notice must be included when redistributing | verified on the project page |
| [PawnIO](https://github.com/namazso/PawnIO) driver and [PawnIO.Setup](https://github.com/namazso/PawnIO.Setup) installer (`PawnIO_setup.exe`) | driver for CPU temperature / power | The driver repository states GPL-2.0 (or later) with a special exception for programs that talk to it only through its device IO control interface. **The PawnIO.Setup repository states no license.** | **Needs review** before bundling the setup file in your own release; the build script downloads it from the official repository instead of storing it in git |
| HidSharp, System.Memory, System.Buffers, System.Numerics.Vectors, System.Runtime.CompilerServices.Unsafe, System.Threading.Tasks.Extensions (DLLs) | companions of LibreHardwareMonitorLib | **Not checked** | **Needs review** (they are normally distributed with LibreHardwareMonitor) |
| PySide6 / Qt | Qt interface | LGPL-3.0 / GPL / commercial (Qt for Python) - **not checked** by the author | **Needs review**: PyInstaller bundles Qt libraries into the installer |
| psutil, pythonnet, nvidia-ml-py, Pillow, pystray | Python libraries | **Not checked** | **Needs review** |

## What this means for you (the project owner)
- Keep this file and a `LICENSE` file in the repository.
- When you publish an installer that contains these files, include their license texts (for example in a `licenses` folder inside the installer) and mention them in the release notes. This is **not done yet**.
- If you are unsure about a file, remove it from the release and let users download it from the original project.
