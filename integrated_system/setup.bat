@echo off
chcp 65001 >nul
echo =========================================
echo IP Scout 集成系统 - 初始化
echo =========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 已安装

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 16+
    pause
    exit /b 1
)
echo [OK] Node.js 已安装

echo.
echo =========================================
echo 创建 Python 虚拟环境
echo =========================================
if exist ".venv" (
    echo [提示] 虚拟环境已存在，跳过创建
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [OK] 虚拟环境创建成功
)

echo.
echo =========================================
echo 安装 Python 依赖
echo =========================================
.venv\Scripts\pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [错误] 安装 Python 依赖失败
    pause
    exit /b 1
)
echo [OK] Python 依赖安装完成

echo.
echo =========================================
echo 安装前端依赖
echo =========================================
cd frontend
call npm install
if errorlevel 1 (
    echo [错误] 安装前端依赖失败
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] 前端依赖安装完成

echo.
echo =========================================
echo 初始化完成！
echo =========================================
echo.
echo 现在可以启动系统：
echo   - 启动后端：start-backend.bat
echo   - 启动前端：start-frontend.bat
echo.
pause
