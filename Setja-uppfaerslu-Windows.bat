@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py update_install.py
) else (
  python update_install.py
)
pause
