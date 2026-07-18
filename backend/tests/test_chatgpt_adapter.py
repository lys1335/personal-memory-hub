"""Tests for ChatGPTImportAdapter.

Tests the ChatGPT conversation export parser and adapter functionality.
"""

from __future__ import annotations

import json

import pytest

from backend.ingest.adapters.chatgpt import ChatGPTImportAdapter
from backend.ingest.base import ImportResult, ImportSource, MemoryItem


class TestChatGPTAdapter:
    """Test suite for ChatGPTImportAdapter."""

    @pytest.fixture
    def adapter(self) -> ChatGPTImportAdapter:
        return ChatGPTImportAdapter()

    # ------------------------------------------------------------------
    # Source Property
    # ------------------------------------------------------------------

    def test_source_property(self, adapter: ChatGPTImportAdapter) -> None:
        assert adapter.source == ImportSource.CHATGPT

    # ------------------------------------------------------------------
    # Parse Tests
    # ------------------------------------------------------------------

    def test_parse_valid_json(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing valid ChatGPT export JSON."""
        sample_data = [
            {
                "title": "Test Conversation",
                "create_time": "2024-01-01T00:00:00.000Z",
                "mapping": {
                    "msg-1": {
                        "id": "msg-1",
                        "author": {"role": "user"},
                        "create_time": "2024-01-01T00:00:00.000Z",
                        "content": {"content_type": "text", "parts": ["Hello, how are you?"]},
                    }
                },
                "children": [],
            }
        ]

        result = adapter.parse(json.dumps(sample_data))

        assert isinstance(result, ImportResult)
        assert result.source == ImportSource.CHATGPT
        assert len(result.items) == 1
        assert result.items[0].content == "Hello, how are you?"
        assert result.items[0].metadata["source"] == "chatgpt"
        assert result.items[0].metadata["conversation_title"] == "Test Conversation"
        assert "original_timestamp" in result.items[0].metadata
        assert "imported" in result.items[0].tags
        assert "chatgpt" in result.items[0].tags

    def test_parse_bytes_input(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing bytes input."""
        sample_data = [
            {
                "title": "Bytes Test",
                "mapping": {
                    "msg-1": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Bytes message"]},
                    }
                },
            }
        ]

        result = adapter.parse(json.dumps(sample_data).encode("utf-8"))

        assert len(result.items) == 1
        assert result.items[0].content == "Bytes message"

    def test_parse_skips_assistant_messages(self, adapter: ChatGPTImportAdapter) -> None:
        """Test that assistant messages are skipped."""
        sample_data = [
            {
                "title": "Mixed Conversation",
                "mapping": {
                    "msg-1": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["User message"]},
                    },
                    "msg-2": {
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["Assistant reply"]},
                    },
                    "msg-3": {
                        "author": {"role": "system"},
                        "content": {"content_type": "text", "parts": ["System prompt"]},
                    },
                },
            }
        ]

        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 1
        assert result.items[0].content == "User message"

    def test_parse_empty_conversations(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing empty conversations list."""
        sample_data = []

        result = adapter.parse(json.dumps(sample_data))

        assert result.items == []
        assert len(result.parse_warnings) > 0

    def test_parse_invalid_json(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Data is not valid JSON"):
            adapter.parse("not valid json")

    def test_parse_missing_content(self, adapter: ChatGPTImportAdapter) -> None:
        """Test handling messages without content."""
        sample_data = [
            {
                "title": "No Content",
                "mapping": {
                    "msg-1": {
                        "author": {"role": "user"},
                        "content": {},
                    }
                },
            }
        ]

        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 0
        assert len(result.parse_warnings) > 0

    def test_parse_multiple_conversations(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing multiple conversations."""
        sample_data = [
            {
                "title": "Conversation 1",
                "mapping": {
                    "msg-1": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Message 1"]},
                    }
                },
            },
            {
                "title": "Conversation 2",
                "mapping": {
                    "msg-2": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Message 2"]},
                    }
                },
            },
        ]

        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 2
        assert result.items[0].metadata["conversation_title"] == "Conversation 1"
        assert result.items[1].metadata["conversation_title"] == "Conversation 2"

    # ------------------------------------------------------------------
    # Validation Tests
    # ------------------------------------------------------------------

    def test_validate_item_valid(self, adapter: ChatGPTImportAdapter) -> None:
        """Test validation of valid item."""
        item = MemoryItem(
            content="Valid content",
            metadata={"source": "chatgpt", "conversation_title": "Test"},
        )

        errors = adapter.validate_item(item)

        assert errors == []

    def test_validate_item_empty_content(self, adapter: ChatGPTImportAdapter) -> None:
        """Test validation of item with empty content."""
        item = MemoryItem(
            content="",
            metadata={"source": "chatgpt"},
        )

        errors = adapter.validate_item(item)

        assert len(errors) > 0
        assert any("content must be non-empty" in e for e in errors)

    def test_validate_item_wrong_source(self, adapter: ChatGPTImportAdapter) -> None:
        """Test validation of item with wrong source."""
        item = MemoryItem(
            content="Content",
            metadata={"source": "open_webui"},
        )

        errors = adapter.validate_item(item)

        assert len(errors) > 0
        assert any("expected source='chatgpt'" in e for e in errors)

    def test_metadata_preserved(self, adapter: ChatGPTImportAdapter) -> None:
        """Test that metadata is properly preserved."""
        sample_data = [
            {
                "title": "Metadata Test",
                "create_time": "2024-01-01T12:00:00.000Z",
                "mapping": {
                    "msg-1": {
                        "id": "msg-1",
                        "author": {"role": "user"},
                        "create_time": "2024-01-01T12:00:00.000Z",
                        "content": {"content_type": "text", "parts": ["Test"]},
                    }
                },
            }
        ]

        result = adapter.parse(json.dumps(sample_data))

        assert result.items[0].metadata["source"] == "chatgpt"
        assert result.items[0].metadata["conversation_title"] == "Metadata Test"
        assert result.items[0].metadata["message_id"] == "msg-1"
        assert result.items[0].created_at == "2024-01-01T12:00:00+00:00"

    # ------------------------------------------------------------------
    # Timestamp Extraction Tests
    # ------------------------------------------------------------------

    def test_timestamp_extraction_iso_format(self, adapter: ChatGPTImportAdapter) -> None:
        """Test extraction of ISO format timestamp."""
        msg = {"create_time": "2024-01-01T12:00:00.000Z"}
        timestamp = adapter._extract_timestamp(msg)

        assert timestamp == "2024-01-01T12:00:00+00:00"

    def test_timestamp_extraction_invalid(self, adapter: ChatGPTImportAdapter) -> None:
        """Test handling of invalid timestamp."""
        msg = {"create_time": "invalid-date"}
        timestamp = adapter._extract_timestamp(msg)

        assert timestamp is None
