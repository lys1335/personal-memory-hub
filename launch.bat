@echo off
setlocal enabledelayedexpansion

:: Personal Memory Hub - 启动指南
:: 双击后显示环境检查和启动说明，请手动启动 Dashboard Server

cls
echo ==========================================
echo   Personal Memory Hub - 启动指南
echo ==========================================
echo.

:: Check if Docker is available
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker not found! Please install Docker Desktop first.
    echo.
    pause
    exit /b 1
)
echo [OK] Docker available.

:: Check if Python is available
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    echo.
    pause
    exit /b 1
)
echo [OK] Python available.

echo.
echo [检查] Docker 容器状态：
docker ps --filter "name=memory-hub" --format "table {{.Names}}\t{{.Status}}" || echo 无法获取容器信息
echo.

:: Check API health
echo [检查] API 健康状况 (8000):
curl -s -m 3 http://localhost:8000/health || echo 超时或未运行
echo.

:: Check Ollama
echo [检查] Ollama 状态 (11434):
curl -s -m 3 http://localhost:11434/api/tags 2>nul && echo Ollama 已响应 || echo Ollama 未运行或未响应
echo.

:: Instructions
echo ==========================================
echo   操作步骤
echo ==========================================
echo.

echo 步骤 1: 确保所有服务已启动
echo   - Database: docker ps | check memory-hub-db (healthy)
echo   - API:      curl http://localhost:8000/health should return "healthy"
echo   - Ollama:   在另一个终端运行: ollama run qwen2.5:7b
echo.

echo 步骤 2: 启动 Dashboard Server (在新 CMD 窗口中执行)
echo   cd F:\LI_YONGSHUN\AI\personal-memory-hub
echo   backend\venv\Scripts\activate
echo   python dashboard_server.py --port 5000 --no-browser
echo.

echo 步骤 3: 打开浏览器访问
echo   http://localhost:5000
echo.

echo 注意：如果访问失败，请检查：
echo   1. 端口 5000 是否被占用 (netstat | findstr :5000)
echo   2. 防火墙设置
echo   3. Dashboard Server 是否有错误输出
echo.
echo ==========================================
pause
