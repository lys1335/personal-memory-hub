# start-uvicorn.ps1
# Simple script to run uvicorn in its own process

$base = Split-Path $MyInvocation.MyCommand.Path -Parent
$env:PYTHONPATH = "$base\src"

echo "Starting uvicorn on port 8000..."
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
