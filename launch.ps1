# Personal Memory Hub Launch Script v4.1 - Fixed error handling

$base = Split-Path $MyInvocation.MyCommand.Path -Parent

Write-Host "=== Starting Personal Memory Hub v4.1 ===" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
try {
    docker info | Out-Null
    Write-Host "[OK] Docker available" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Docker not responding (check Desktop)" -ForegroundColor Yellow
}

# Start Docker containers using docker-compose
Write-Host "[DB] Starting database container..." -ForegroundColor Cyan
docker compose -f "$base\docker-compose.yml" up -d db --no-recreate
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Database container may already be running" -ForegroundColor Yellow
}

Write-Host "[APP] Starting application container..." -ForegroundColor Cyan
docker compose -f "$base\docker-compose.yml" up -d app --no-recreate
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Application container may already be running" -ForegroundColor Yellow
}

# Wait for services to start
Write-Host ""
Write-Host "[WAIT] Waiting for services to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Check if services are ready
Write-Host "[CHECK] Verifying services..." -ForegroundColor Cyan
$apiReady = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $apiReady = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 2
}

if ($apiReady) {
    Write-Host "[OK] API server is ready at http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "[WARN] API server not responding, check Docker logs" -ForegroundColor Yellow
}

# Open browser
Write-Host ""
Write-Host "[BROW] Opening browser at http://localhost:8000/dashboard..." -ForegroundColor Cyan
Start-Process "http://localhost:8000/dashboard"

Write-Host ""
Write-Host "=== ALL SERVICES LAUNCHED ===" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8000/dashboard"
Write-Host "API:       http://localhost:8000/api/proposals"
Write-Host "Health:    http://localhost:8000/health"
Write-Host ""
Write-Host "Press Enter to exit this launcher (services continue running)"
Read-Host
