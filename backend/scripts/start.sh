#!/bin/bash
# Start script for Personal Memory Hub
# Configures file logging BEFORE uvicorn starts

export PYTHONUNBUFFERED=1

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

echo 'Waiting for database...'
while ! python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect(('db', 5432)); s.close()" 2>/dev/null; do sleep 1; done
echo 'Starting application...'
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
