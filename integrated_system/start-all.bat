@echo off
chcp 65001 >nul
echo =========================================
echo IP Scout 集成系统 - 一键启动
echo =========================================
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [提示] 首次运行，正在初始化...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo 启动后端服务...
start "IP Scout 后端" cmd /k "start-backend.bat"

echo 启动前端服务...
timeout /t 3 /nobreak >nul
start "IP Scout 前端" cmd /k "start-frontend.bat"

echo.
echo =========================================
echo 服务启动中...
echo =========================================
echo 后端: http://localhost:5000
echo 前端: http://localhost:5173
echo.
echo 请等待几秒钟让服务完全启动
echo 然后访问 http://localhost:5173 使用系统
echo.
