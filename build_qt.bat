@echo off
setlocal
cd /d "%~dp0"
title Lmonitor (Qt) - build

rem ============================================================
rem  Builds the Qt version (folder version) into  _build_qt\dist\Lmonitor\
rem  Everything generated goes into _build_qt\ - the source stays clean.
rem  Needs the sensor DLLs, PresentMon and PawnIO next to this file.
rem ============================================================
set "ROOT=%~dp0"
set "BUILD=%ROOT%_build_qt"

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

rem --- PawnIO installer: downloaded once here, then bundled with the program
if not exist "PawnIO_setup.exe" (
    echo Downloading the official PawnIO installer...
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe' -OutFile 'PawnIO_setup.exe'"
)
if not exist "PawnIO_setup.exe" (
    echo.
    echo Could not download PawnIO_setup.exe.
    echo Download it by hand from this link and put it next to build_qt.bat:
    echo https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe
    if not "%1"=="nopause" pause
    exit /b 1
)

set "MISSING="
for %%F in (lmonitor\engine.py lmonitor\qt\__main__.py lmonitor\qt\qml\Main.qml tools\make_version.py Lmonitor.ico LibreHardwareMonitorLib.dll HidSharp.dll System.Memory.dll System.Buffers.dll System.Numerics.Vectors.dll System.Runtime.CompilerServices.Unsafe.dll System.Threading.Tasks.Extensions.dll PresentMon.exe PawnIO_setup.exe) do (
    if not exist "%%F" (
        echo Missing file: %%F
        set "MISSING=1"
    )
)
if defined MISSING (
    echo.
    echo Put the files listed above next to build_qt.bat and run again.
    if not "%1"=="nopause" pause
    exit /b 1
)

echo Checking Python libraries...
rem PySide6-Essentials holds every Qt part Lmonitor uses (the full PySide6 adds ~200 MB
rem of add-ons it never loads). Already installed = no download.
%PY% -m pip install --quiet pyinstaller psutil pythonnet nvidia-ml-py PySide6-Essentials
if errorlevel 1 (
    echo pip failed - check your internet connection.
    if not "%1"=="nopause" pause
    exit /b 1
)

rem a running copy (or its PresentMon helper) locks the old build folder
taskkill /F /IM Lmonitor.exe >nul 2>&1
taskkill /F /IM PresentMon.exe >nul 2>&1
timeout /t 2 /nobreak >nul
if exist "%BUILD%" rmdir /s /q "%BUILD%"
if exist "%BUILD%" (
    echo.
    echo Could not delete the old build folder: %BUILD%
    echo Lmonitor or PresentMon is still running. Exit it from the tray icon,
    echo or open this window as Administrator ^(right-click, Run as administrator^), then run again.
    if not "%1"=="nopause" pause
    exit /b 1
)
mkdir "%BUILD%"
%PY% tools\make_version.py lmonitor\engine.py "%BUILD%\version_info.txt"
if errorlevel 1 (
    echo Could not create the version info.
    if not "%1"=="nopause" pause
    exit /b 1
)

echo Building. This takes a few minutes...
%PY% -m PyInstaller --noconfirm --clean --onedir --noconsole --uac-admin ^
 --name Lmonitor --icon "%ROOT%Lmonitor.ico" --version-file "%BUILD%\version_info.txt" ^
 --distpath "%BUILD%\dist" --workpath "%BUILD%\work" --specpath "%BUILD%" ^
 --paths "%ROOT%." ^
 --hidden-import PySide6.QtWidgets --hidden-import PySide6.QtQml --hidden-import PySide6.QtQuick --exclude-module tkinter ^
 --add-data "%ROOT%lmonitor\qt\qml;lmonitor\qt\qml" --add-data "%ROOT%Lmonitor.ico;." ^
 --add-binary "%ROOT%LibreHardwareMonitorLib.dll;." --add-binary "%ROOT%HidSharp.dll;." ^
 --add-binary "%ROOT%System.Memory.dll;." --add-binary "%ROOT%System.Buffers.dll;." ^
 --add-binary "%ROOT%System.Numerics.Vectors.dll;." --add-binary "%ROOT%System.Runtime.CompilerServices.Unsafe.dll;." ^
 --add-binary "%ROOT%System.Threading.Tasks.Extensions.dll;." ^
 --add-binary "%ROOT%PresentMon.exe;." --add-binary "%ROOT%PawnIO_setup.exe;." ^
 "%ROOT%lmonitor\qt\__main__.py"
if errorlevel 1 goto :failed
if not exist "%BUILD%\dist\Lmonitor\Lmonitor.exe" goto :failed
%PY% tools\trim_build.py "%BUILD%\dist\Lmonitor"
if errorlevel 1 goto :failed

echo.
echo Done. Your program is here:
echo %BUILD%\dist\Lmonitor\Lmonitor.exe
echo Test it: double-click it (it asks for administrator rights).
if not "%1"=="nopause" pause
exit /b 0

:failed
echo.
echo Build failed. Send me the last lines above.
if not "%1"=="nopause" pause
exit /b 1
