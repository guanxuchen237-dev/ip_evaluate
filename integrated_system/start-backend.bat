@echo off
chcp 65001 >nul
echo =========================================
echo IP Scout 集成系统
echo =========================================
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [警告] 虚拟环境不存在，正在创建...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请确保已安装 Python
        pause
        exit /b 1
    )
    echo [OK] 虚拟环境创建成功
    echo.
    echo [提示] 正在安装依赖，请稍候...
    .venv\Scripts\pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo [错误] 安装依赖失败
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成
) else (
    echo [OK] 虚拟环境已存在
)

echo.
echo =========================================
echo 启动后端服务 (Flask)
echo =========================================
cd backend
call ..\.venv\Scripts\python.exe app.py
