# PMH Deployment Issue: Stale .pyc Cache

## Issue
When source files are mounted via Docker volume (`./backend/src:/app/src`), Python's bytecode cache (`__pycache__`) may contain stale `.pyc` files from a previous deployment. This causes:
- `NameError: name 'datetime' is not defined`
- Server restart loop
- Dashboard unresponsive

## Root Cause
1. `__pycache__` directory is owned by `root:root` with `755` permissions
2. Application runs as `appuser` (uid=999)
3. Python prioritizes `.pyc` files over `.py` files
4. Old `.pyc` files don't have new imports (e.g., `from datetime import datetime`)
5. Result: `NameError` at runtime

## Evidence
```
/app/src/backend/app.py           Modify: 2026-08-10 10:27:31 (new)
/app/src/backend/__pycache__/app.cpython-311.pyc  Modify: 2026-08-02 11:37:48 (old)

Owner: root:root
Permissions: 755
App user: appuser (uid=999)
```

## Solution
1. **In start.sh**: Clear `__pycache__` before starting the application
2. **In Dockerfile**: Clear `__pycache__` during build
3. **Future deployments**: Always clear cache when source files change

## Prevention
- Add cache clearing to deployment script
- Consider using `PYTHONPYCACHEPREFIX` to isolate cache directories
- Monitor logs for `NameError` after deployments

## Related
- Diagnostic Phase 3 report: `docs/diagnostic-report-phase3-2026-08-10.md`
- Original incident: 2026-08-10 10:55+ JST
