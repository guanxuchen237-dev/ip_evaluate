@echo off
echo ===================================================
echo     Launching IP Lumina Backend (Verified Env)
echo ===================================================
echo.
echo Stopping any existing Python processes...
taskkill /F /IM python.exe /T 2>nul
echo.

echo Starting backend with .venv/d:\ip-lumina-main\.venv\Scripts\python.exe...
d:\ip-lumina-main\.venv\Scripts\python.exe integrated_system/backend/app.py

pause
