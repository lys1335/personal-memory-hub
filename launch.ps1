# Personal Memory Hub Launch Script v2.0
# Simple, clean, no Chinese paths

$ErrorActionPreference = "Stop"
$base = Split-Path $MyInvocation.MyCommand.Path -Parent

echo "=== Starting Personal Memory Hub ==="

# Check Docker is running
Try { 
    docker info | Out-Null 
    echo "[✓] Docker available" 
} Catch { 
    echo "⚠ Docker not responding (check Desktop)" 
}

# Start Database container
echo "[🐳] Database: starting container..."
docker compose up -d db --no-recreate 2>$null
Start-Sleep -Seconds 3

# Start API in separate process
echo "[⚙️] API: starting uvicorn..."
$apiProcess = Start-Process -FilePath pwsh -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command 'cd \$base\backend; env PYTHONPATH=\$base\backend\src python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000'" -PassThru -WindowStyle Normal
Start-Sleep -Seconds 2

# Start Dashboard with port auto-detect
echo "[📊] Dashboard: starting proxy..."
$dashPort = 5000
while ((Test-Connection -ComputerName localhost -Count 1 -Quiet -Port $dashPort) -eq $true) {
    $dashPort++
    if ($dashPort -gt 6000) { $dashPort = 5001; break }
}
Start-Process -FilePath python -ArgumentList "$base\dashboard_server.py --port $dashPort --no-browser" -PassThru -WindowStyle Normal

# Open browser
echo "[🌐] Opening browser at http://localhost:$dashPort..."
Start-Item "http://localhost:$dashPort"

echo ""
echo "=== ALL SERVICES LAUNCHED ==="
echo "API window: new PowerShell (keep open)"
echo "Dashboard window: new Python console (keep open)"
echo "Browser: http://localhost:$dashPort"
echo ""
echo "Press Enter to exit this launcher (services continue running)"
Read-Line
