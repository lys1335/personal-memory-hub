# Personal Memory Hub Launch Script v5.0 - Smart container management
$base = Split-Path $MyInvocation.MyCommand.Path -Parent
Write-Host "=== Starting Personal Memory Hub v5.0 ===" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
        Write-Host ""
        Write-Host "To start Docker Desktop:" -ForegroundColor Yellow
        Write-Host "  1. Open Docker Desktop from Start Menu"
        Write-Host "  2. Wait for the whale icon to appear in system tray"
        Write-Host "  3. Run this script again"
        Write-Host ""
        exit 1
    }
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to connect to Docker" -ForegroundColor Red
    exit 1
}

# Check if containers are already running
Write-Host ""
Write-Host "[CHECK] Checking existing containers..." -ForegroundColor Cyan
$existingContainers = docker ps --filter "name=memory-hub" --format "{{.Names}}: {{.Status}}" 2>&1

if ($existingContainers -match "memory-hub-app.*Up") {
    Write-Host "[OK] memory-hub-app is already running" -ForegroundColor Green
} else {
    Write-Host "[INFO] memory-hub-app is not running, will start it" -ForegroundColor Yellow
}

if ($existingContainers -match "memory-hub-db.*Up") {
    Write-Host "[OK] memory-hub-db is already running" -ForegroundColor Green
} else {
    Write-Host "[INFO] memory-hub-db is not running, will start it" -ForegroundColor Yellow
}

# Only start containers if they're not already running
if (-not ($existingContainers -match "memory-hub-app.*Up")) {
    Write-Host ""
    Write-Host "[DB] Starting database container..." -ForegroundColor Cyan
    docker compose -f "$base\docker-compose.yml" up -d db
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Database container may already be running or failed to start" -ForegroundColor Yellow
    }
} else {
    Write-Host "[SKIP] Database container already running" -ForegroundColor Gray
}

if (-not ($existingContainers -match "memory-hub-app.*Up")) {
    Write-Host "[APP] Starting application container..." -ForegroundColor Cyan
    docker compose -f "$base\docker-compose.yml" up -d app
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Application container may already be running or failed to start" -ForegroundColor Yellow
    }
} else {
    Write-Host "[SKIP] Application container already running" -ForegroundColor Gray
}

# Wait for services to start
Write-Host ""
Write-Host "[WAIT] Waiting for services to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Check if services are ready
Write-Host "[CHECK] Verifying services..." -ForegroundColor Cyan
$apiReady = $false
for ($i = 0; $i -lt 15; $i++) {
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
    Write-Host "       Run 'docker logs memory-hub-app' to debug" -ForegroundColor Gray
}

# Open browser
Write-Host ""
Write-Host "[BROW] Opening browser at http://localhost:8000/dashboard..." -ForegroundColor Cyan
Start-Process "http://localhost:8000/dashboard"

Write-Host ""
Write-Host "=== SERVICES READY ===" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8000/dashboard"
Write-Host "API:       http://localhost:8000/api/proposals"
Write-Host "Health:    http://localhost:8000/health"
Write-Host "Logs:      docker logs -f memory-hub-app"
Write-Host ""
Write-Host "Press Enter to exit (services continue running)"
Read-Host
