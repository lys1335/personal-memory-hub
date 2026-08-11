"""Tests for cron scheduler deadlock fix (Phase 14/15)."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


class TestCronDeadlockFix:
    """Verify _save_cron_tasks() does not re-acquire _cron_lock."""

    def test_save_cron_tasks_no_reentrant_lock(self):
        """_save_cron_tasks() should work when called while holding _cron_lock.
        
        This is the core test that proves the deadlock is fixed.
        Before the fix, this test would hang forever because:
        1. Thread acquires _cron_lock
        2. Thread calls _save_cron_tasks()
        3. _save_cron_tasks() tries to acquire _cron_lock again
        4. Deadlock!
        
        After the fix, _save_cron_tasks() no longer acquires the lock,
        so the test completes quickly.
        """
        from backend.app import _save_cron_tasks, _cron_tasks, _cron_lock, _CRON_DATA_FILE

        # Ensure we have a task to save
        test_task_id = "test_deadlock_fix"
        _cron_tasks[test_task_id] = {
            "id": test_task_id,
            "name": "Test Task",
            "type": "evolution",
            "interval_seconds": 600,
            "enabled": True,
            "payload": {"workspace_id": "fd0223ed-7aa2-491e-8db5-b0de71b75219", "limit": 200},
            "last_run": None,
            "status": "idle",
        }

        # Simulate the pattern that caused the deadlock:
        # with _cron_lock:
        #     _save_cron_tasks()
        acquired = threading.Event()

        def holder_thread():
            with _cron_lock:
                acquired.set()
                # This should NOT deadlock
                _save_cron_tasks()
                # If we get here, the fix works

        t = threading.Thread(target=holder_thread)
        t.start()

        # Wait for lock acquisition
        assert acquired.wait(timeout=5), "Lock was not acquired within 5s"

        # Wait for thread to complete (should not hang)
        t.join(timeout=5)

        assert not t.is_alive(), "Thread is still alive after 5s - likely deadlock!"

        # Verify the task was saved
        with open(_CRON_DATA_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        assert test_task_id in saved, "Task was not saved to disk"
        assert saved[test_task_id]["name"] == "Test Task"

    def test_save_cron_tasks_without_lock(self):
        """_save_cron_tasks() should also work when called without holding the lock.
        
        This ensures backward compatibility for callers like
        _initialize_default_tasks() that don't hold the lock.
        """
        from backend.app import _save_cron_tasks, _cron_tasks, _CRON_DATA_FILE

        # Clear and re-create
        _cron_tasks.clear()
        _cron_tasks["test_no_lock"] = {
            "id": "test_no_lock",
            "name": "No Lock Test",
            "type": "evolution",
            "interval_seconds": 300,
            "enabled": False,
            "payload": {},
            "last_run": None,
            "status": "idle",
        }

        # Call without holding lock - should work
        _save_cron_tasks()

        with open(_CRON_DATA_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        assert "test_no_lock" in saved
        assert saved["test_no_lock"]["enabled"] is False

    def test_last_run_persists_after_update(self):
        """Verify last_run is updated and persisted correctly."""
        from backend.app import _save_cron_tasks, _cron_tasks, _cron_lock, _CRON_DATA_FILE
        from datetime import datetime, timezone

        test_task_id = "test_last_run"
        _cron_tasks[test_task_id] = {
            "id": test_task_id,
            "name": "Test Last Run",
            "type": "evolution",
            "interval_seconds": 600,
            "enabled": True,
            "payload": {},
            "last_run": None,
            "status": "idle",
        }

        # Update last_run while holding lock
        with _cron_lock:
            _cron_tasks[test_task_id]["last_run"] = datetime.now(timezone.utc).isoformat()
            _save_cron_tasks()

        # Verify persistence
        with open(_CRON_DATA_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)

        assert saved[test_task_id]["last_run"] is not None
        assert saved[test_task_id]["status"] == "idle"
