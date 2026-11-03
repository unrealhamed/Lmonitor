@echo off
setlocal
cd /d "%~dp0"
title Lmonitor - build

rem ============================================================
rem  Builds the program (folder version) into  _build\dist\Lmonitor\
rem  Everything generated goes into _build\ - the source stays clean.
rem  To make the Windows installer afterwards run  build_installer.bat
rem ============================================================
set "ROOT=%~dp0"
set "BUILD=%ROOT%_build"

echo.
echo === Lmonitor: build ===
echo.

rem --- Python
set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 (
    set "PY=py -3"
    %PY% --version >nul 2>&1
    if errorlevel 1 (
        echo Python was not found. Install Python 64-bit and tick "Add to PATH".
        pause
        exit /b 1
    )
)

rem --- 1) PawnIO installer: downloaded once here, then bundled with the program
if not exist "PawnIO_setup.exe" (
    echo Downloading the official PawnIO installer...
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe' -OutFile 'PawnIO_setup.exe'"
)
if not exist "PawnIO_setup.exe" (
    echo.
    echo Could not download PawnIO_setup.exe.
    echo Download it by hand from this link and put it next to build.bat:
    echo https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe
    pause
    exit /b 1
)
echo PawnIO_setup.exe found. SHA-256 for your records:
certutil -hashfile "PawnIO_setup.exe" SHA256
echo.

rem --- 2) make sure every file is here
set "MISSING="
for %%F in (monitor.py lmonitor\engine.py tools\make_version.py LibreHardwareMonitorLib.dll HidSharp.dll System.Memory.dll System.Buffers.dll System.Numerics.Vectors.dll System.Runtime.CompilerServices.Unsafe.dll System.Threading.Tasks.Extensions.dll PresentMon.exe PawnIO_setup.exe) do (
    if not exist "%%F" (
        echo Missing file: %%F
        set "MISSING=1"
    )
)
if defined MISSING (
    echo.
    echo Put the files listed above next to build.bat and run again.
    if not "%1"=="nopause" pause
    exit /b 1
)

rem --- 3) libraries
echo Checking Python libraries...
%PY% -m pip install --quiet --upgrade pyinstaller psutil pystray pillow pythonnet nvidia-ml-py
if errorlevel 1 (
    echo pip failed - check your internet connection.
    pause
    exit /b 1
)

rem --- 4) clean old build output, make icon + version info
if exist "%BUILD%" rmdir /s /q "%BUILD%"
mkdir "%BUILD%"

rem the exe / taskbar icon is generated from the logo code (Logo class)
%PY% monitor.py --make-icon
if not exist "Lmonitor.ico" (
    echo Could not create Lmonitor.ico - the exe would have the default icon.
    pause
    exit /b 1
)
%PY% tools\make_version.py lmonitor\engine.py "%BUILD%\version_info.txt"
if errorlevel 1 (
    echo Could not create the version info.
    pause
    exit /b 1
)

rem --- 5) build (folder version: starts faster, friendlier to antivirus)
echo Building. This takes a few minutes...
%PY% -m PyInstaller --noconfirm --clean --onedir --noconsole --uac-admin ^
 --name Lmonitor --icon "%ROOT%Lmonitor.ico" --version-file "%BUILD%\version_info.txt" ^
 --distpath "%BUILD%\dist" --workpath "%BUILD%\work" --specpath "%BUILD%" ^
 --hidden-import pystray._win32 ^
 --add-binary "%ROOT%LibreHardwareMonitorLib.dll;." --add-binary "%ROOT%HidSharp.dll;." ^
 --add-binary "%ROOT%System.Memory.dll;." --add-binary "%ROOT%System.Buffers.dll;." ^
 --add-binary "%ROOT%System.Numerics.Vectors.dll;." --add-binary "%ROOT%System.Runtime.CompilerServices.Unsafe.dll;." ^
 --add-binary "%ROOT%System.Threading.Tasks.Extensions.dll;." ^
 --add-binary "%ROOT%PresentMon.exe;." --add-binary "%ROOT%PawnIO_setup.exe;." ^
 "%ROOT%monitor.py"
if errorlevel 1 goto :failed
if not exist "%BUILD%\dist\Lmonitor\Lmonitor.exe" goto :failed

echo.
echo Done. Your program is here:
echo %BUILD%\dist\Lmonitor\Lmonitor.exe
echo Next: run build_installer.bat to make the installer.
if not "%1"=="nopause" pause
exit /b 0

:failed
echo.
echo Build failed. Send me the last lines above.
if not "%1"=="nopause" pause
exit /b 1
