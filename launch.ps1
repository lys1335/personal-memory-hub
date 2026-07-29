# Personal Memory Hub Launch Script v2.0 (FIXED)
# Simple, clean, no Chinese paths

$ErrorActionPreference = "Stop"
$base = Split-Path $MyInvocation.MyCommand.Path -Parent

echo "=== Starting Personal Memory Hub ==="

# Check Docker is running
Try { 
    docker info | Out-Null 
    echo "[OK] Docker available" 
} Catch { 
    echo "[WARN] Docker not responding (check Desktop)" 
}

# Start Database container
echo "[DB] Database: starting container..."
docker compose up -d db --no-recreate 2>$null
Start-Sleep -Seconds 3

# API Configuration - set PYTHONPATH relative to backend directory
$apiDir = Join-Path $base "backend"
$env:PYTHONPATH = "$apiDir\src"

# Start API in separate process (new PowerShell window)
echo "[API] API: starting uvicorn..."
Start-Process -FilePath pwsh -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command `"$base\backend\start-uvicorn.ps1`"" 

# Wait a moment for API to start
Start-Sleep -Seconds 2

# Start Dashboard with port auto-detect
echo "[DASH] Dashboard: starting proxy..."
$dashPort = 5000
while ((Test-Connection -ComputerName localhost -Count 1 -Quiet -Port $dashPort) -eq $true) {
    $dashPort++
    if ($dashPort -gt 6000) { $dashPort = 5001; break }
}
Start-Process -FilePath python -ArgumentList "$base\dashboard_server.py --port $dashPort --no-browser" -PassThru -WindowStyle Normal

# Open browser
echo "[BROW] Opening browser at http://localhost:$dashPort..."
Start-Item "http://localhost:$dashPort"

echo ""
echo "=== ALL SERVICES LAUNCHED ==="
echo "API window: new PowerShell (keep open) - run: $base\backend\start-uvicorn.ps1"
echo "Dashboard window: new Python console (keep open)"
echo "Browser: http://localhost:$dashPort"
echo ""
echo "Press Enter to exit this launcher (services continue running)"
Read-Line
