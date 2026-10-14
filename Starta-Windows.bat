@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py app.py --open
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python vantar. Settu upp Python 3.11 eda nyrra og reyndu aftur.
  ) else (
      python app.py --open
  )
)
pause
