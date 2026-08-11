#!/bin/bash
# Start script for Personal Memory Hub
# Configures file logging BEFORE uvicorn starts

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Clear Python bytecode cache to prevent stale .pyc issues
# This is critical when source files are mounted via volume
find /app/src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Configure logging before any imports
python3 -c "
import logging, os
log_dir = '/app/logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'memory_hub.log')
fh = logging.FileHandler(log_file, encoding='utf-8', mode='a')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
logging.root.addHandler(fh)
logging.root.setLevel(logging.DEBUG)
print(f'[STARTUP] Logging configured to {log_file}')
"

# Inject scheduler trace instrumentation BEFORE starting the server
python3 -c "
import sys
sys.path.insert(0, '/app/src')

# Import instrumentation module
import scheduler_trace

# Clear the trace log
with open('/tmp/scheduler_trace.log', 'w') as f:
    f.write('')

print('[STARTUP] Scheduler trace instrumentation injected')
"

# Inject uvicorn instrumentation BEFORE starting the server
python3 -c "
import sys
sys.path.insert(0, '/app/src')

# Import instrumentation module
import instrument

# Clear the trace log
with open('/tmp/uvicorn_trace.log', 'w') as f:
    f.write('')

print('[STARTUP] Uvicorn instrumentation injected')
"

echo 'Waiting for database...'
DB_HOST="${DATABASE_HOST:-memory-hub-db}"
while ! python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect(('$DB_HOST', 5432)); s.close()" 2>/dev/null; do sleep 1; done
echo 'Starting application...'
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
