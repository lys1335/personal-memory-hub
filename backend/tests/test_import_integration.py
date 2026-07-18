"""Integration tests for the Import Framework end-to-end pipeline.

Tests verify that the full import flow works correctly:
- REST endpoint receives request
- Validation passes
- Pipeline parses and validates data
- Memories are imported through the normal service layer
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.entry.rest_adapter import RESTAdapter
from backend.ingest.base import ImportSource
from backend.ingest.registry import create_default_registry

# ---------------------------------------------------------------------------
# Sample Data
# ---------------------------------------------------------------------------

SAMPLE_OPEN_WEBUI_JSON = {
    "conversations": [
        {
            "title": "Test Conversation",
            "chat_msg": [
                {
                    "id": "msg-001",
                    "model": "llama3",
                    "content": "Hello, how are you?",
                    "role": "user",
                    "created_at": 1700000000,
                    "conversation_id": "conv-001",
                },
                {
                    "id": "msg-002",
                    "model": "llama3",
                    "content": "I'm doing well, thanks!",
                    "role": "assistant",
                    "created_at": 1700000001,
                    "conversation_id": "conv-001",
                },
            ],
        },
    ]
}


# ---------------------------------------------------------------------------
# REST Endpoint Integration Tests
# ---------------------------------------------------------------------------


class TestImportEndpoint:
    """Integration tests for the /memories/import endpoint."""

    @pytest.fixture
    def mock_services(self) -> dict[str, MagicMock]:
        """Create mock services for testing."""
        from backend.service.dto import ImportStatus

        memory_service = MagicMock()
        memory_service.import_memories = AsyncMock(return_value=MagicMock(
            job_id="test-job-id",
            status=ImportStatus.COMPLETED,
            total_count=1,
            processed_count=1,
            success_count=1,
            failure_count=0,
            error_messages=[],
        ))

        task_service = MagicMock()
        entity_service = MagicMock()
        query_service = MagicMock()
        analytics_service = MagicMock()

        return {
            "memory": memory_service,
            "task": task_service,
            "entity": entity_service,
            "query": query_service,
            "analytics": analytics_service,
        }

    @pytest.fixture
    def api(self, mock_services: dict[str, MagicMock]) -> RESTAdapter:
        """Create a RESTAdapter with mocked services."""
        return RESTAdapter(services=mock_services)

    @pytest.mark.asyncio
    async def test_handle_import_valid_request(
        self,
        api: RESTAdapter,
        mock_services: dict[str, MagicMock],
    ) -> None:
        """Test that a valid import request is processed correctly."""
        body = {
            "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
            "source_type": "open_webui",
            "data": json.dumps(SAMPLE_OPEN_WEBUI_JSON),
        }

        response = await api.handle_import_memories(body)

        # Verify the response structure
        assert response.request_id is not None
        assert response.status.value == "success"
        assert response.data["job_id"] == "test-job-id"
        assert response.data["status"] == "completed"
        assert response.data["total_count"] == 1

        # Verify the service was called
        mock_services["memory"].import_memories.assert_called_once()
        call_kwargs = mock_services["memory"].import_memories.call_args.kwargs
        assert str(call_kwargs["workspace_id"]) == "550e8400-e29b-41d4-a716-446655440000"
        assert call_kwargs["source_type"] == "open_webui"
        assert "conversations" in call_kwargs["data"]

    @pytest.mark.asyncio
    async def test_handle_import_missing_source_type(
        self,
        api: RESTAdapter,
    ) -> None:
        """Test that a missing source_type field returns validation error."""
        body = {
            "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
            "data": json.dumps(SAMPLE_OPEN_WEBUI_JSON),
        }

        response = await api.handle_import_memories(body)

        # Should fail validation
        assert response.status.value == "error"
        assert response.error["code"] == "CONTRACT_VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_handle_import_invalid_workspace_id(
        self,
        api: RESTAdapter,
    ) -> None:
        """Test that an invalid workspace_id raises ValueError."""
        body = {
            "workspace_id": "not-a-uuid",
            "source_type": "open_webui",
            "data": json.dumps(SAMPLE_OPEN_WEBUI_JSON),
        }

        with pytest.raises(ValueError, match="badly formed"):
            await api.handle_import_memories(body)

    @pytest.mark.asyncio
    async def test_handle_import_empty_data(
        self,
        api: RESTAdapter,
    ) -> None:
        """Test that empty data still goes through (validation passes, import runs)."""
        body = {
            "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
            "source_type": "open_webui",
            "data": "",
        }

        response = await api.handle_import_memories(body)

        # Empty data should still be accepted by the endpoint
        # The actual parsing will handle the empty content
        assert response.request_id is not None


# ---------------------------------------------------------------------------
# Pipeline Integration Tests
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Integration tests for the import pipeline."""

    def test_full_pipeline_open_webui(self) -> None:
        """Test the full pipeline with Open WebUI data."""
        from backend.ingest.base import ImportPipeline

        registry = create_default_registry()
        pipeline = ImportPipeline(registry)

        data = json.dumps(SAMPLE_OPEN_WEBUI_JSON)
        result = pipeline.execute(ImportSource.OPEN_WEBUI, data)

        # Verify parsing results
        assert len(result.items) == 1  # Only user messages
        assert result.items[0].content == "Hello, how are you?"
        assert result.items[0].metadata["source"] == "open_webui"
        assert result.items[0].metadata["conversation_title"] == "Test Conversation"

    def test_pipeline_with_multiple_conversations(self) -> None:
        """Test pipeline with multiple conversations."""
        from backend.ingest.base import ImportPipeline
        from backend.ingest.registry import create_default_registry

        multi_conv_data = {
            "conversations": [
                {
                    "title": "Conv 1",
                    "chat_msg": [
                        {"role": "user", "content": "Message 1"},
                        {"role": "user", "content": "Message 2"},
                    ],
                },
                {
                    "title": "Conv 2",
                    "chat_msg": [
                        {"role": "user", "content": "Message 3"},
                    ],
                },
            ]
        }

        registry = create_default_registry()
        pipeline = ImportPipeline(registry)

        result = pipeline.execute(ImportSource.OPEN_WEBUI, json.dumps(multi_conv_data))

        assert len(result.items) == 3
        titles = {item.metadata.get("conversation_title") for item in result.items}
        assert "Conv 1" in titles
        assert "Conv 2" in titles
