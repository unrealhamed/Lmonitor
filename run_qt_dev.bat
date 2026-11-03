@echo off
cd /d "%~dp0"
title Lmonitor Qt - dev run
rem Dev run of the NEW Qt interface. First time only:
rem     python -m pip install -r requirements.txt
rem Runs WITHOUT admin (UI check; CPU temperature may be missing).
rem Use  run_qt_dev.bat admin  to run elevated like the real program.
set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 set "PY=py -3"
%PY% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo PySide6 is not installed. Installing...
    %PY% -m pip install -r requirements.txt
)
if /i "%1"=="admin" (
    %PY% -m lmonitor.qt
) else (
    %PY% -m lmonitor.qt --no-admin
)
echo.
echo Exit code: %errorlevel%
pause
