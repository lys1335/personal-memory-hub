@echo off
setlocal enabledelayedexpansion

:: Personal Memory Hub - Dashboard Launch Guide (Read-Only Mode)
:: This script checks your environment and shows manual startup instructions.
:: Double-click to view, then follow the on-screen instructions manually.

cls
echo ==========================================
echo   Personal Memory Hub - 启动指南
echo ==========================================
echo.

echo [环境检查]
where docker >nul 2>nul && echo ✓ Docker available || echo ⚠ Docker not found
where python >nul 2>nud && echo ✓ Python available || echo ⚠ Python not found
echo.

echo [容器状态]
docker ps --filter "name=memory-hub" --format "table {{.Names}}\t{{.Status}}" 2>nul || echo 无法获取容器状态
echo.

echo ==========================================
echo 手动启动步骤：
echo ==========================================
echo.
echo 1. 确保 Docker 容器正在运行（如有需要执行：docker compose up -d db app）
echo.
echo 2. 在 NEW 终端窗口中激活 backend venv：
echo    cd F:\LI_YONGSHUN\AI\personal-memory-hub\backend
echo    .\venv\Scripts\Activate.ps1      （PowerShell）
echo    或在 CMD 中使用：.\venv\Scripts\activate
echo.
echo 3. 启动 Dashboard Server（端口 5000，避开 Windows 排除端口）：
echo    cd ..
echo    python dashboard_server.py --port 5000
echo.
echo 4. 打开浏览器访问：http://localhost:5000
echo.

如果页面上加载数据，请确保：
- Ollama 正在运行（ollama run qwen2.5:7b）
- Memory Hub API (http://localhost:8000) 可访问
echo.

echo [完成] 请按任意键关闭窗口...
pause
