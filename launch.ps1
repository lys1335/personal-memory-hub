# Personal Memory Hub Launch Script v3.0 - Simple and reliable

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

# Start Database container (absolute path to compose file)
echo "[DB] Database: starting container..."
docker compose -f "$base/docker-compose.yml" up -d db --no-recreate 2>$null
Start-Sleep -Seconds 3

# Start API server in a new console window
echo "[API] API: starting uvicorn in separate window..."
Start-Process pwsh -NoNewWindow -ArgumentList "-ExecutionPolicy Bypass", "-File", "$base\backend\start-uvicorn.ps1"

# Wait for API to start
Start-Sleep -Seconds 5

# Start Dashboard proxy with port auto-detect
echo "[DASH] Starting dashboard proxy..."
$dashPort = 5000
while ((Test-Connection -ComputerName localhost -Count 1 -Quiet -Port $dashPort) -eq $true) {
    $dashPort++
    if ($dashPort -gt 6000) { $dashPort = 5001; break }
}

Start-Process python -ArgumentList "$base\dashboard_server.py", "--port", $dashPort, "--no-browser" -WindowStyle Normal

# Open browser
echo "[BROW] Opening browser at http://localhost:$dashPort..."
Start-Item "http://localhost:$dashPort"

echo ""
echo "=== ALL SERVICES LAUNCHED ==="
echo "API: new PowerShell window (keep open)"
echo "Dashboard: Python console (keep open)"
echo "Browser: http://localhost:$dashPort"
echo ""
echo "Press Enter to exit this launcher (services continue running)"
Read-Line
