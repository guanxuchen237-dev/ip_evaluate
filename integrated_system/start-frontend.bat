@echo off
chcp 65001 >nul
echo =========================================
echo IP Scout 集成系统 - 前端
echo =========================================
echo.

REM 检查 node_modules
if not exist "frontend\node_modules" (
    echo [提示] 正在安装前端依赖，请稍候...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo [错误] 安装前端依赖失败，请确保已安装 Node.js
        pause
        exit /b 1
    )
    cd ..
    echo [OK] 前端依赖安装完成
) else (
    echo [OK] 前端依赖已存在
)

echo.
echo =========================================
echo 启动前端开发服务器 (Vite)
echo =========================================
cd frontend
call npm run dev
