@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: Personal Memory Hub - 一键启动脚本
:: 功能：自动检查环境、启动 Docker、提示用户启动 Dashboard
:: 使用方法：双击此文件或从命令行运行
:: ==========================================

:: 清除屏幕
cls

:: ============================================================
:: 标题
:: ============================================================
echo.
echo ==========================================
echo     Personal Memory Hub - 启动管理工具
echo ==========================================
echo.

:: ============================================================
:: 步骤 0: 检查必要工具
:: ============================================================
echo [检查] 确认必要的工具...

where docker >nul 2>nul
if errorlevel 1 (
    echo ❌ 错误：未找到 Docker！请安装 Docker Desktop 后重试。
    echo.
    echo 下载: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo ✓ Docker 已安装

where python >nul 2>nul
if errorlevel 1 (
    echo ❌ 错误：未找到 Python！请安装 Python 3.11+ 并加入 PATH。
    echo.
    echo 下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✓ Python 已安装

echo.

:: ============================================================
:: 步骤 1: 检查容器状态
:: ============================================================
echo [Docker] 检查容器状态...
echo.
docker ps --filter "name=memory-hub" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

:: ============================================================
:: 步骤 2: 如果容器未运行，则启动
:: ============================================================
for /f "tokens=1 delims==" %%a in ('docker ps --filter "name=memory-hub-app" --format "{{.Status}}" 2^>nul') do set STATUS=%%a

if defined STATUS (
    if "!STATUS!" neq "" (
        echo [OK] memory-hub-app 已经在运行: !STATUS!
    ) else (
        echo ⚠️ 容器未检测到，正在启动 Docker Compose...
        echo.
        echo 正在执行: docker compose up -d db app
        echo.
        cd /d "%~dp0"
        docker compose up -d db app
        timeout /t 5 >nul
        echo.
    )
) else (
    echo ⚠️ 容器未检测到，正在启动 Docker Compose...
    echo.
    echo 正在执行: docker compose up -d db app
    echo.
    cd /d "%~dp0"
    docker compose up -d db app
    timeout /t 5 >nul
    echo.
)

:: ============================================================
:: 步骤 3: 验证 API 健康
:: ============================================================
echo [验证] 检查 API 健康状态...
curl -s -m 5 http://localhost:8000/health
if %errorlevel% neq 0 (
    echo ⚠️ API 可能尚未就绪或无法访问
    echo   请等待几秒钟后再次尝试。
    echo.
) else (
    echo ✓ API 健康检查通过
    echo.
)

:: ============================================================
:: 步骤 4: 检查 Ollama
:: ============================================================
echo [Ollama] 检查 Ollama 服务...
curl -s -m 3 http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Ollama 服务已检测到
    echo   建议确保模型 qwen2.5:7b 或 nomic-embed-text 已加载。
) else (
    echo ⚠️ Ollama 未检测到（端口 11434 不可达）
    echo   请在另一个终端窗口运行：
    echo.   ollama run qwen2.5:7b
    echo.   （另开一个终端可选：ollama run nomic-embed-text）
    echo.
)

:: ============================================================
:: 步骤 5: 给用户的最终指示
:: ============================================================
echo ==========================================
echo   接下来您需要手动执行的操作：
echo ==========================================
echo.
echo 步骤 A: 在 NEW 终端窗口中运行：
echo.   cd "%~dp0"
echo.   python dashboard_server.py --port 8080
echo.
echo 步骤 B: 打开浏览器访问：
echo.   http://localhost:8080
echo.
echo 小提示: 您可以将上述命令保存为一个单独的 .bat 文件来简化操作。
echo.

:: ============================================================
:: 保持窗口打开以便查看结果
:: ============================================================
echo [完成] 本脚本已结束。请按任意键关闭窗口！
echo.
注意：Dashboard Server 需要在独立终端中运行！
pause

endlocal
