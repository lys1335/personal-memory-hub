"""Tests for ChatGPTImportAdapter.

Tests the ChatGPT conversation export parser and adapter functionality,
including support for both JSON array format (conversations-*.json)
and HTML format (chat.html with embedded JSON).
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
    # Parse Tests — JSON Array Format
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
    # Parse Tests — Wrapped Message Format (actual ChatGPT export)
    # ------------------------------------------------------------------

    def test_parse_wrapped_message_format(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing actual ChatGPT export format where mapping values have a 'message' key."""
        sample_data = [
            {
                "title": "Wrapped Format Test",
                "mapping": {
                    "msg-1": {
                        "id": "msg-1",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"content_type": "text", "parts": ["Wrapped user message"]},
                            "create_time": 1704067200.0,
                        },
                        "parent": "parent-id",
                    },
                    "msg-2": {
                        "id": "msg-2",
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"content_type": "text", "parts": ["Assistant reply"]},
                        },
                        "parent": "parent-id",
                    },
                },
            }
        ]

        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 1
        assert result.items[0].content == "Wrapped user message"
        assert result.items[0].metadata["conversation_title"] == "Wrapped Format Test"

    def test_parse_single_conversation_object(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing a single conversation object (not wrapped in array)."""
        sample_data = {
            "title": "Single Conv",
            "mapping": {
                "msg-1": {
                    "id": "msg-1",
                    "message": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Single conv msg"]},
                    },
                }
            },
        }

        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 1
        assert result.items[0].content == "Single conv msg"

    # ------------------------------------------------------------------
    # Parse Tests — HTML Format
    # ------------------------------------------------------------------

    def test_parse_html_with_embedded_json(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing chat.html with embedded JSON in <script> tag."""
        html_content = f"""<!DOCTYPE html>
<html>
<head><title>ChatGPT Export</title></head>
<body>
<script>
var data = {json.dumps([{
    "title": "HTML Test Conversation",
    "mapping": {
        "msg-1": {
            "id": "msg-1",
            "message": {
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": ["From HTML"]},
            },
        }
    },
}] * 5)};
</script>
</body>
</html>"""

        result = adapter.parse(html_content)

        assert len(result.items) == 1
        assert result.items[0].content == "From HTML"
        assert result.items[0].metadata["conversation_title"] == "HTML Test Conversation"

    def test_parse_html_no_json_fails(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing HTML without JSON data raises ValueError."""
        html_content = "<html><body>No JSON here</body></html>"

        with pytest.raises(ValueError, match="No JSON data found in HTML file"):
            adapter.parse(html_content)

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

    def test_timestamp_extraction_unix_epoch(self, adapter: ChatGPTImportAdapter) -> None:
        """Test extraction of Unix epoch timestamp (ChatGPT export format)."""
        msg = {"create_time": 1704067200.0}  # 2024-01-01 00:00:00 UTC
        timestamp = adapter._extract_timestamp(msg)

        assert timestamp is not None
        assert "2024-01-01" in timestamp

    def test_timestamp_extraction_invalid(self, adapter: ChatGPTImportAdapter) -> None:
        """Test handling of invalid timestamp."""
        msg = {"create_time": "invalid-date"}
        timestamp = adapter._extract_timestamp(msg)

        assert timestamp is None

    # ------------------------------------------------------------------
    # Content Type Tests
    # ------------------------------------------------------------------

    def test_image_attachment_content(self, adapter: ChatGPTImportAdapter) -> None:
        """Test that image attachments produce placeholder text."""
        msg = {
            "author": {"role": "user"},
            "content": {"content_type": "image", "parts": []},
        }
        content = adapter._extract_message_content(msg)
        assert content == "[Image attachment]"

    def test_text_with_multiple_parts(self, adapter: ChatGPTImportAdapter) -> None:
        """Test text content with multiple parts joined by newline."""
        msg = {
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": ["Line 1", "Line 2", "Line 3"]},
        }
        content = adapter._extract_message_content(msg)
        assert content == "Line 1\nLine 2\nLine 3"

    # ------------------------------------------------------------------
    # Integration Test — Real ChatGPT Data Structure
    # ------------------------------------------------------------------

    def test_parse_real_chatgpt_structure(self, adapter: ChatGPTImportAdapter) -> None:
        """Test parsing with realistic ChatGPT export structure."""
        # Simulates the actual structure from conversations-000.json
        sample_data = [
            {
                "conversation_id": "test-conv-1",
                "title": "NISA Investment Discussion",
                "create_time": 1739080363.848759,
                "current_node": "node-1",
                "default_model_slug": "gpt-4o",
                "id": "conv-id-1",
                "is_archived": False,
                "is_do_not_remember": False,
                "is_read_only": False,
                "is_starred": False,
                "is_study_mode": False,
                "mapping": {
                    "msg-1": {
                        "id": "msg-1",
                        "message": {
                            "author": {"name": None, "role": "user"},
                            "content": {
                                "content_type": "text",
                                "parts": ["我现在的 NISA 配置中，有哪三只基金？具体比例是多少？"],  # noqa: RUF001
                            },
                            "create_time": 1739103059.933212,
                            "id": "msg-1",
                            "metadata": {"serialization_metadata": {"custom_symbol_offsets": []}},
                        },
                        "parent": "parent-1",
                    },
                    "msg-2": {
                        "id": "msg-2",
                        "message": {
                            "author": {"name": None, "role": "assistant"},
                            "content": {
                                "content_type": "text",
                                "parts": ["根据你之前的对话，你的 NISA 配置如下：\n🌍 全世界股票基金：每月 4 万日元\n🇺🇸 S&P500 指数基金：每月 4 万日元\n⚖️ バランス型：每月 2 万日元"],  # noqa: RUF001
                            },
                            "create_time": 1739103100.0,
                            "id": "msg-2",
                        },
                        "parent": "msg-1",
                    },
                    "msg-3": {
                        "id": "msg-3",
                        "message": {
                            "author": {"name": None, "role": "user"},
                            "content": {
                                "content_type": "text",
                                "parts": ["好的，帮我记录一下。"],  # noqa: RUF001
                            },
                            "create_time": 1739103200.0,
                            "id": "msg-3",
                        },
                        "parent": "msg-2",
                    },
                },
            }
        ]

        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 2  # Only user messages (msg-1, msg-3)
        assert result.items[0].content == "我现在的 NISA 配置中，有哪三只基金？具体比例是多少？"  # noqa: RUF001
        assert result.items[1].content == "好的，帮我记录一下。"  # noqa: RUF001
        assert result.items[0].metadata["conversation_title"] == "NISA Investment Discussion"
        assert result.items[0].metadata["message_id"] == "msg-1"
        assert result.items[1].metadata["message_id"] == "msg-3"
        assert "2025-02-09" in result.items[0].metadata["original_timestamp"]  # Unix epoch converted
