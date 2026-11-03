@echo off
setlocal
cd /d "%~dp0"
title Lmonitor - installer

rem ============================================================
rem  1) builds the program (build.bat)   2) builds the installer
rem  Result:  _output\Lmonitor_Setup_<version>.exe
rem  Needs Inno Setup 6.3+  (https://jrsoftware.org/isdl.php)
rem ============================================================
set "ROOT=%~dp0"

set "ISCC="
if defined ISCC_PATH if exist "%ISCC_PATH%" set "ISCC=%ISCC_PATH%"
for %%R in ("%ProgramFiles(x86)%" "%ProgramFiles%" "%LocalAppData%\Programs") do (
    for /d %%D in ("%%~R\Inno Setup*") do (
        if not defined ISCC if exist "%%~D\ISCC.exe" set "ISCC=%%~D\ISCC.exe"
    )
)
if not defined ISCC where ISCC.exe >nul 2>&1 && set "ISCC=ISCC.exe"
if not defined ISCC (
    echo Inno Setup 6 was not found.
    echo Install it from https://jrsoftware.org/isdl.php and run this file again.
    echo If it is installed elsewhere, run:  set ISCC_PATH=full\path\to\ISCC.exe
    pause
    exit /b 1
)

call "%ROOT%build.bat" nopause
if errorlevel 1 (
    echo Program build failed - installer not made.
    pause
    exit /b 1
)

set "PY=python"
%PY% --version >nul 2>&1 || set "PY=py -3"
for /f "usebackq delims=" %%V in (`%PY% tools\make_version.py lmonitor\engine.py "%ROOT%_build\version_info.txt"`) do set "VER=%%V"
if not defined VER set "VER=1.0.0"

if exist "%ROOT%_output" rmdir /s /q "%ROOT%_output"
"%ISCC%" /Qp "/DAppVersion=%VER%" "%ROOT%installer\Lmonitor.iss"
if errorlevel 1 (
    echo Installer build failed. Send me the last lines above.
    pause
    exit /b 1
)
if not exist "%ROOT%_output\Lmonitor_Setup_%VER%.exe" (
    echo Installer file was not created.
    pause
    exit /b 1
)

echo.
echo Done. Your installer is here:
echo %ROOT%_output\Lmonitor_Setup_%VER%.exe
pause
exit /b 0
