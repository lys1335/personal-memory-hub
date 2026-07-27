@echo off
setlocal enabledelayedexpansion

:: Personal Memory Hub - Windows 启动快捷方式
:: 双键执行 start_hub.py，自动带交互模式

:: 检查是否安装了 Python
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ 错误：系统中未找到 Python！
    echo.
    echo 请先安装 Python 3.11+：
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查 requirements（dashboard_server.py 应在同一目录）
if not exist "dashboard_server.py" (
    echo ❌ 错误：找不到 dashboard_server.py！
    echo.
    echo 请确保此脚本在项目根目录下运行。
    pause
    exit /b 1
)

echo ==========================================
echo   正在启动 Personal Memory Hub ...
echo ==========================================
echo.

:: 用 python 直接运行脚本
python "%~dp0start_hub.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 启动过程中出现错误。
    pause
    exit /b 1
)

echo.
echo 🎉 启动完成！请按 Ctrl+C 关闭窗口以停止服务。
endlocal
