@echo off
rem Same as run_qt_dev.bat but as administrator (needed for CPU temperature).
cd /d "%~dp0"
call run_qt_dev.bat admin
