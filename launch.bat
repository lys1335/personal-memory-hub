@echo off
setlocal enabledelayedexpansion

:: Personal Memory Hub Launch Script
:: Double-click to run, follow on-screen instructions.
:: This script starts Docker services and gives you Dashboard startup instructions.

cls
echo ==========================================
echo   Personal Memory Hub - Launch Manager
echo ==========================================
echo.

:: Check if Docker is available
where docker >nul 2>nul
if errorlevel 1 (
    echo ERROR: Docker not found! Please install Docker Desktop.
    echo.
    echo Download: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo [OK] Docker found.

:: Check if Python is available
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.11+.
    echo.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python found.

echo.

:: Check current container status
echo Checking Docker containers...
echo.
docker ps --filter "name=memory-hub" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

:: Start containers if they are not running
for /f "tokens=1 delims==" %%a in ('docker ps --filter "name=memory-hub-app" --format "{{.Status}}" 2^>nul') set STATUS=%%a
if defined STATUS if "!STATUS!" neq "" (
    echo Container memory-hub-app is running: !STATUS!
) else (
    echo Containers not found. Starting Docker Compose...
    echo.
    echo Running: docker compose up -d db app
    cd /d %~dp0
    docker compose up -d db app
    timeout /t 5 >nul
    echo.
)

:: Verify API health
echo Checking API health (http://localhost:8000/health)...
curl -s -m 5 http://localhost:8000/health
if %errorlevel% neq 0 (
    echo WARNING: API may not be ready yet.
) else (
    echo [OK] API healthy.
)

echo.

:: Check Ollama
echo Checking Ollama service (port 11434)...
curl -s -m 3 http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama service detected.
) else (
    echo WARNING: Ollama not detected. Run in another terminal:
    echo.   ollama run qwen2.5:7b
    echo.
)

:: Instructions
echo ==========================================
echo   NEXT STEPS (MANUAL):
echo ==========================================
echo.
echo Step A: In a NEW terminal window, navigate to this folder:
echo.   cd "%~dp0"
echo.
echo Step B: Start the Dashboard Server:
echo.   python dashboard_server.py --port 8080
echo.
echo Step C: Open your browser and go to:
echo.   http://localhost:8080
echo.
echo TIP: If you get permission error on port 8080,
echo edit dashboard_server.py line 222 and change '0.0.0.0' to '127.0.0.1'.
echo.

echo [INFO] Launch script finished.
echo Press any key to close this window...
pause
endlocal
