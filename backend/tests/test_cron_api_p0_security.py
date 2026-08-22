
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import os

# Ensure src is on the Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.app import app, require_cron_admin, validate_no_test_task
from backend.shared.infrastructure.config.settings import AppSettings, get_settings

# Dummy API Key for testing
TEST_API_KEY = "test-secret-key"
WRONG_API_KEY = "wrong-key"
# Use non-test_ prefixed task IDs for normal operation tests
SAFE_TASK_ID = "prod_task_id"


@pytest.fixture(name="client")
def client_fixture():
    real_settings = AppSettings()
    real_settings.PMH_CRON_API_KEY = TEST_API_KEY
    real_settings.PMH_ALLOW_TEST_TASKS = False
    with patch("backend.app.get_settings", return_value=real_settings):
        with TestClient(app=app, base_url="http://test") as client:
            yield client

@pytest.fixture(autouse=True)
def mock_cron_lock():
    with patch("backend.app._cron_lock", new=MagicMock()):
        yield

@pytest.fixture(autouse=True)
def mock_save_cron_tasks():
    with patch("backend.app._save_cron_tasks", new=AsyncMock()):
        yield

@pytest.fixture(autouse=True)
def mock_cron_scheduler_loop():
    with patch("backend.app._cron_scheduler_loop", new=AsyncMock()):
        yield

@pytest.fixture(autouse=True)
def mock_cron_tasks():
    with patch("backend.app._cron_tasks", new={}) as mock_tasks:
        yield mock_tasks


class TestCronApiP0Security:
    """
    Phase 26-G-C-E Cron API P0 Verification Test
    Ensures all Cron mutation endpoints are protected by API Key authentication
    and test_* tasks are blocked.
    """

    # Use SAFE_TASK_ID (non-test_) for all auth protection tests
    cron_mutation_endpoints = [
        ("/api/cron/tasks", "POST"),
        (f"/api/cron/tasks/{SAFE_TASK_ID}", "PUT"),
        (f"/api/cron/tasks/{SAFE_TASK_ID}", "DELETE"),
        (f"/api/cron/tasks/{SAFE_TASK_ID}/start", "POST"),
        (f"/api/cron/tasks/{SAFE_TASK_ID}/stop", "POST"),
    ]

    @pytest.mark.parametrize("path, method", cron_mutation_endpoints)
    @pytest.mark.asyncio
    async def test_no_api_key_fail_closed(self, client, path, method):
        """Test: Missing API Key fails with 401 Unauthorized."""
        response = client.request(method, path, json={})
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    @pytest.mark.parametrize("path, method", cron_mutation_endpoints)
    @pytest.mark.asyncio
    async def test_wrong_api_key_rejected(self, client, path, method):
        """Test: Wrong API Key fails with 403 Forbidden."""
        response = client.request(method, path, headers={"X-CRON-API-KEY": WRONG_API_KEY}, json={})
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]

    @pytest.mark.parametrize("path, method", cron_mutation_endpoints)
    @pytest.mark.asyncio
    async def test_correct_api_key_allowed(self, client, path, method, mock_cron_tasks, mock_save_cron_tasks):
        """Test: Correct API Key allows access to mutation endpoints with non-test_ names."""
        # Pre-populate mock tasks for endpoints that require existing task
        if method != "POST" or path != "/api/cron/tasks":
            mock_cron_tasks[SAFE_TASK_ID] = {"id": SAFE_TASK_ID, "name": "prod_task", "enabled": False, "status": "idle"}

        body = {"name": "prod_task"} if method == "POST" and path == "/api/cron/tasks" else {}
        response = client.request(method, path, headers={"X-CRON-API-KEY": TEST_API_KEY}, json=body)

        assert response.status_code == 200, f"Expected 200 for {method} {path}, got {response.status_code}"
        if method == "POST" and path == "/api/cron/tasks":
            assert "task_id" in response.json()
        elif method == "PUT":
            assert response.json().get("id") == SAFE_TASK_ID
        elif method == "DELETE":
            assert response.json().get("deleted") == SAFE_TASK_ID
        elif method == "POST" and "/start" in path:
            assert response.json().get("status") == "started"
        elif method == "POST" and "/stop" in path:
            assert response.json().get("status") == "stopped"

    def test_run_now_no_api_key_rejected(self, client):
        """Test: run-now without API Key fails with 401."""
        response = client.post(f"/api/cron/tasks/{SAFE_TASK_ID}/run-now")
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_run_now_wrong_api_key_rejected(self, client):
        """Test: run-now with wrong API Key fails with 403."""
        response = client.post(f"/api/cron/tasks/{SAFE_TASK_ID}/run-now", headers={"X-CRON-API-KEY": WRONG_API_KEY})
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]

    def test_run_now_correct_key_nonexistent_task(self, client):
        """Test: run-now with correct API Key but non-existent task returns 404."""
        response = client.post(f"/api/cron/tasks/{SAFE_TASK_ID}/run-now", headers={"X-CRON-API-KEY": TEST_API_KEY})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_test_task_rejected(self, client, mock_cron_tasks):
        """Test: Creation of a task with name 'test_*' is rejected."""
        body = {"name": "test_my_new_task", "type": "evolution", "interval_seconds": 60}
        response = client.post("/api/cron/tasks", headers={"X-CRON-API-KEY": TEST_API_KEY}, json=body)
        assert response.status_code == 400
        assert "Test tasks not allowed in production environment" in response.json()["detail"]

    @pytest.mark.parametrize("path, method", [
        (f"/api/cron/tasks/{SAFE_TASK_ID}", "PUT"),
        (f"/api/cron/tasks/{SAFE_TASK_ID}/start", "POST"),
    ])
    @pytest.mark.asyncio
    async def test_update_start_test_task_rejected(self, client, path, method, mock_cron_tasks):
        """Test: Update or start of a task with name 'test_*' is rejected."""
        test_task_id = "test_existing_task"
        mock_cron_tasks[test_task_id] = {"id": test_task_id, "name": test_task_id, "enabled": False, "status": "idle"}

        path_with_test_id = path.replace(SAFE_TASK_ID, test_task_id)
        body = {"enabled": True} if method == "PUT" else {}

        response = client.request(method, path_with_test_id, headers={"X-CRON-API-KEY": TEST_API_KEY}, json=body)
        assert response.status_code == 400
        assert "Test tasks not allowed in production environment" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_audit_logging_triggered(self, client, caplog):
        """Test: Audit logging is triggered for authenticated and unauthenticated requests."""
        with caplog.at_level(os.environ.get("LOG_LEVEL", "INFO")):
            # Unauthorized request
            response_401 = client.post("/api/cron/tasks", json={})
            assert response_401.status_code == 401
            assert any("[CRON-AUDIT] Missing API key" in record.message for record in caplog.records)
            caplog.clear()

            # Forbidden request
            response_403 = client.post("/api/cron/tasks", headers={"X-CRON-API-KEY": WRONG_API_KEY}, json={})
            assert response_403.status_code == 403
            assert any("[CRON-AUDIT] Invalid API key" in record.message for record in caplog.records)
            caplog.clear()

            # Authorized request with valid task name
            body = {"name": "audit_task", "type": "evolution", "interval_seconds": 60}
            response_200 = client.post("/api/cron/tasks", headers={"X-CRON-API-KEY": TEST_API_KEY}, json=body)
            assert response_200.status_code == 200
            assert any("[CRON-AUDIT] Authorized mutation" in record.message for record in caplog.records)
