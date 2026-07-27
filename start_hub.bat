@echo off
setlocal enabledelayedexpansion

:: Personal Memory Hub - Windows 启动快捷方式
:: Double-click to execute start_hub.py with interactive mode

:: Check if Python is installed
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Error: Python not found!
    echo.
    echo Please install Python 3.11+:
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check that dashboard_server.py exists
if not exist "dashboard_server.py" (
    echo ❌ Error: dashboard_server.py not found!
    echo.
    echo Please run this script from project root directory.
    pause
    exit /b 1
)

echo ==========================================
echo   Starting Personal Memory Hub ...
echo ==========================================
echo.

:: Run the Python script (interactive mode by default)
python "%~dp0start_hub.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    ❌ Startup failed with error code %ERRORLEVEL%
    pause
    exit /b 1
)

echo.
echo 🎉 Dashboard is running at http://localhost:8080
echo.
echo Press Ctrl+C in this window to stop, or close the window.
pause
endlocal
