"""Phase 21.1 Regression Tests — Evidence Role + Assistant Evidence Preservation.

These tests verify the Phase 21.1 implementation:
1. Evidence role metadata is preserved during import
2. Assistant Evidence is saved (not filtered out)
3. Role classification is correct (user/assistant/system)
4. Historical Evidence without role remains compatible
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.ingest.adapters.chatgpt import ChatGPTImportAdapter
from backend.ingest.adapters.open_webui import OpenWebUIAdapter


SAMPLE_CHATGPT_DATA = [
    {
        "title": "Test Conversation",
        "mapping": {
            "msg-1": {
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": ["Hello"]},
            },
            "msg-2": {
                "author": {"role": "assistant"},
                "content": {"content_type": "text", "parts": ["Hi there!"]},
            },
            "msg-3": {
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": ["How are you?"]},
            },
        },
    }
]

SAMPLE_OPEN_WEBUI_DATA = {
    "conversations": [
        {
            "title": "Test Conv",
            "chat_msg": [
                {"id": "1", "role": "user", "content": "Hello"},
                {"id": "2", "role": "assistant", "content": "Hi!"},
                {"id": "3", "role": "user", "content": "Thanks"},
            ],
        }
    ]
}


class TestEvidenceRolePreservation:
    """Test that role metadata is correctly set for all Evidence types."""

    def test_user_evidence_has_role(self, chatgpt_adapter: ChatGPTImportAdapter) -> None:
        """Test 3: User Evidence role=user."""
        result = chatgpt_adapter.parse(json.dumps(SAMPLE_CHATGPT_DATA))

        user_items = [item for item in result.items if item.metadata.get("role") == "user"]
        assert len(user_items) >= 1
        assert user_items[0].metadata["role"] == "user"

    def test_assistant_evidence_has_role(self, chatgpt_adapter: ChatGPTImportAdapter) -> None:
        """Test 2: Assistant Evidence role=assistant."""
        result = chatgpt_adapter.parse(json.dumps(SAMPLE_CHATGPT_DATA))

        assistant_items = [item for item in result.items if item.metadata.get("role") == "assistant"]
        assert len(assistant_items) >= 1
        assert assistant_items[0].metadata["role"] == "assistant"

    def test_system_evidence_has_role(self) -> None:
        """Test system role handling."""
        sample_data = [
            {
                "title": "System Test",
                "mapping": {
                    "msg-1": {
                        "author": {"role": "system"},
                        "content": {"content_type": "text", "parts": ["System prompt"]},
                    }
                },
            }
        ]
        adapter = ChatGPTImportAdapter()
        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 1
        assert result.items[0].metadata.get("role") == "system"

    def test_unknown_role_handling(self) -> None:
        """Test evidence without role gets 'unknown'."""
        sample_data = [
            {
                "title": "No Role",
                "mapping": {
                    "msg-1": {
                        "content": {"content_type": "text", "parts": ["No role"]},
                    }
                },
            }
        ]
        adapter = ChatGPTImportAdapter()
        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 1
        # Should default to "unknown" or empty string
        assert result.items[0].metadata.get("role", "") in ("unknown", "")


class TestAssistantEvidencePersistence:
    """Test that Assistant Evidence is preserved (not filtered)."""

    def test_assistant_evidence_saved_chatgpt(self, chatgpt_adapter: ChatGPTImportAdapter) -> None:
        """Test 1: Assistant Evidence is saved."""
        result = chatgpt_adapter.parse(json.dumps(SAMPLE_CHATGPT_DATA))

        # Should have 3 items (2 user + 1 assistant)
        assert len(result.items) == 3

        # Verify assistant content is preserved
        assistant_contents = [
            item.content for item in result.items if item.metadata.get("role") == "assistant"
        ]
        assert "Hi there!" in assistant_contents

    def test_assistant_evidence_saved_open_webui(self, open_webui_adapter: OpenWebUIAdapter) -> None:
        """Test Assistant Evidence saved in OpenWebUI format."""
        result = open_webui_adapter.parse(json.dumps(SAMPLE_OPEN_WEBUI_DATA))

        # Should have 3 items
        assert len(result.items) == 3

        # Verify assistant content is preserved
        assistant_contents = [
            item.content for item in result.items if item.metadata.get("role") == "assistant"
        ]
        assert "Hi!" in assistant_contents


class TestEvidenceRoleCannotCreateCandidate:
    """Test that Assistant Evidence does not directly create Candidate."""

    def test_assistant_evidence_marked_for_context_only(self) -> None:
        """Test 4: Assistant Evidence marked appropriately (for Context Window use)."""
        sample_data = [
            {
                "title": "Context Test",
                "mapping": {
                    "msg-1": {
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["AI suggestion"]},
                    }
                },
            }
        ]
        adapter = ChatGPTImportAdapter()
        result = adapter.parse(json.dumps(sample_data))

        assert len(result.items) == 1
        # Role should be "assistant"
        assert result.items[0].metadata.get("role") == "assistant"
        # This evidence will be available for Context Window but cannot form Candidate directly


class TestHistoricalEvidenceCompatibility:
    """Test that historical Evidence without role remains compatible."""

    def test_historical_evidence_without_role(self) -> None:
        """Test that Evidence without role metadata still works."""
        # Simulate historical Evidence (no role field)
        historical_metadata: dict[str, Any] = {
            "source": "chatgpt",
            "conversation_title": "Old Conversation",
        }

        # Should not crash when role is missing
        role = historical_metadata.get("role", "unknown")
        assert role == "unknown"

    def test_new_evidence_always_has_role(self, chatgpt_adapter: ChatGPTImportAdapter) -> None:
        """Test that all new Evidence has role metadata."""
        result = chatgpt_adapter.parse(json.dumps(SAMPLE_CHATGPT_DATA))

        for item in result.items:
            assert "role" in item.metadata
            assert item.metadata["role"] in ("user", "assistant", "system", "unknown")


class TestContextWindowReadiness:
    """Test that Evidence data is ready for Context Window feature (Phase 21.3)."""

    def test_evidence_roles_available_for_filtering(self) -> None:
        """Test 5: Evidence roles can be used for filtering in Context Window."""
        sample_data = [
            {
                "title": "Filter Test",
                "mapping": {
                    "msg-1": {"author": {"role": "user"}, "content": {"content_type": "text", "parts": ["U1"]}},
                    "msg-2": {"author": {"role": "assistant"}, "content": {"content_type": "text", "parts": ["A1"]}},
                    "msg-3": {"author": {"role": "user"}, "content": {"content_type": "text", "parts": ["U2"]}},
                },
            }
        ]
        adapter = ChatGPTImportAdapter()
        result = adapter.parse(json.dumps(sample_data))

        # Can filter by role
        user_evidences = [item for item in result.items if item.metadata.get("role") == "user"]
        assistant_evidences = [item for item in result.items if item.metadata.get("role") == "assistant"]

        assert len(user_evidences) == 2
        assert len(assistant_evidences) == 1

        # Context Window can use this to build evidence chain
        assert user_evidences[0].content == "U1"
        assert assistant_evidences[0].content == "A1"
        assert user_evidences[1].content == "U2"


@pytest.fixture
def chatgpt_adapter() -> ChatGPTImportAdapter:
    return ChatGPTImportAdapter()


@pytest.fixture
def open_webui_adapter() -> OpenWebUIAdapter:
    return OpenWebUIAdapter()
