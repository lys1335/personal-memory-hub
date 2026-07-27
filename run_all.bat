@echo off
setlocal enabledelayedexpansion

:: Personal Memory Hub - Windows 一键启动 (适用于 CMD/PowerShell)
:: 本脚本自动检测并启动所有必要服务，然后打开浏览器。

cls
echo ==========================================
echo   Personal Memory Hub 一键启动
echo ==========================================
echo.

:: Check if Docker is available
where docker >nul 2>nul
if errorlevel 1 (
    echo ERROR: Docker not found! Please install Docker Desktop.
    pause
    exit /b 1
)

echo [OK] Docker available.

:: Start services if not running
echo Checking containers...
docker ps --filter "name=memory-hub-app" --format "{{.Names}}" | findstr /i memory-hub-app >nul
if errorlevel 1 (
    echo Containers not running. Starting Docker Compose...
    cd /d %~dp0
    docker compose up -d db app
    timeout /t 5 >nul
) else (
    echo Containers already running.
)

:: Verify API health
echo Checking API...
curl -s -m 5 http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: API may not be ready yet.
) else (
    echo [OK] API healthy.
)

echo.

:: Determine correct Python path to use
set PY_EXE=python
:: Prefer backend venv's python if exists
if exist ".\backend\.venv\Scripts\python.exe" set PY_EXE=".\\backend\\.venv\\Scripts\\python.exe"

:: Dashboard server command
set DASH_CMD=%PY_EX% dashboard_server.py --port 8080

echo Starting Dashboard Server on port 8080...
echo Command: %DASH_CMD%
echo.

:: Launch Dashboard in a new console window so this script can keep running and open browser
start "" "%PY_EXE%" "%~dp0dashboard_server.py" --port 8080

:: Wait a moment for Dashboard to start
timeout /t 2 >nul

:: Open browser
echo Opening browser...
start "" "http://localhost:8080"

echo.
echo Dashboard should be opening in your default browser.
echo If it doesn't, manually visit http://localhost:8080
echo.
echo Press any key to continue...
pause
