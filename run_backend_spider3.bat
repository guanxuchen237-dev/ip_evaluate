@echo off
echo ===================================================
echo     Launching IP Lumina Backend (spider3_env)
echo ===================================================
echo.
echo Stopping any existing Python processes on port 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
echo.

cd /d D:\ip-lumina-main\integrated_system\backend
echo Starting backend with spider3_env...
D:\ANACONDA\envs\spider3_env\python.exe app.py

pause
