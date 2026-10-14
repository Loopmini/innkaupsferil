@echo off
cd /d "%~dp0"
py market_sync.py --husa-limit 100
pause
