"""ChatGPT Import Adapter.

Parses ChatGPT conversation export format and converts to MemoryItems.

ChatGPT export format (JSON array):
[
    {
        "title": "Conversation Title",
        "create_time": "2024-01-01T00:00:00.000Z",
        "mapping": {
            "message_id": {
                "id": "message_id",
                "author": {"role": "user"},
                "create_time": "2024-01-01T00:00:00.000Z",
                "content": {
                    "content_type": "text",
                    "parts": ["Message content"]
                }
            }
        },
        "command": "next",
        "parent": null,
        "children": ["message_id"]
    }
]

Each user message becomes a MemoryItem with:
- content: The user's message text
- metadata: Source info (conversation title, timestamp, model)
- tags: ["imported", "chatgpt"]
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from backend.ingest.base import (
    BaseImportAdapter,
    ImportResult,
    ImportSource,
    MemoryItem,
)
from backend.ingest.parser import extract_text_segments, sanitize_content, try_parse_json

logger = logging.getLogger(__name__)


class ChatGPTImportAdapter(BaseImportAdapter):
    """Import adapter for ChatGPT conversation exports.

    Stateless singleton — no mutable instance state.
    """

    @property
    def source(self) -> ImportSource:
        return ImportSource.CHATGPT

    def parse(self, data: bytes | str, **kwargs: Any) -> ImportResult:
        """Parse ChatGPT conversation export into MemoryItems.

        Args:
            data: Raw JSON string or bytes from ChatGPT export.
            **kwargs: Additional options.

        Returns:
            ImportResult with extracted MemoryItems.

        Raises:
            ValueError: If data cannot be parsed as ChatGPT format.
        """
        # Decode if bytes
        if isinstance(data, bytes):
            try:
                data = data.decode("utf-8")
            except UnicodeDecodeError as err:
                raise ValueError("Data is not valid UTF-8") from err

        # Parse JSON
        parsed = try_parse_json(data)
        if parsed is None:
            raise ValueError("Data is not valid JSON")

        # Extract conversations
        conversations = self._extract_conversations(parsed)
        if not conversations:
            logger.warning("No conversations found in ChatGPT export")
            return ImportResult(
                source=ImportSource.CHATGPT,
                items=[],
                raw_size_bytes=len(data.encode("utf-8")),
                parse_warnings=["No conversations found in exported data"],
            )

        # Convert each conversation to MemoryItems
        memory_items: list[MemoryItem] = []
        warnings: list[str] = []

        for conv_idx, conv in enumerate(conversations):
            conv_title = conv.get("title", f"Conversation {conv_idx + 1}")
            mapping = conv.get("mapping", {})

            for msg_id, msg in mapping.items():
                author = msg.get("author", {})
                role = author.get("role", "").lower()

                # Only import user messages (skip assistant/system)
                if role != "user":
                    continue

                # Extract content
                content = self._extract_message_content(msg)
                content = sanitize_content(content, max_length=10000)

                if not content:
                    warnings.append(
                        f"Conversation '{conv_title}', message {msg_id}: empty content, skipped"
                    )
                    continue

                # Extract metadata
                created_at = self._extract_timestamp(msg)
                recipient = msg.get("recipient", {}).get("id", "unknown") if isinstance(msg.get("recipient"), dict) else str(msg.get("recipient", "unknown"))

                # Build metadata
                metadata: dict[str, Any] = {
                    "source": "chatgpt",
                    "conversation_title": conv_title,
                    "message_id": msg_id,
                    "recipient": recipient,
                }

                if created_at:
                    metadata["original_timestamp"] = created_at

                # Create MemoryItem
                item = MemoryItem(
                    content=content,
                    entity_id=None,  # Will be resolved later if needed
                    level=1,  # Observation level
                    source="import",
                    metadata=metadata,
                    tags=["imported", "chatgpt", "conversation"],
                    created_at=created_at,
                )
                memory_items.append(item)

        result = ImportResult(
            source=ImportSource.CHATGPT,
            items=memory_items,
            raw_size_bytes=len(data.encode("utf-8")),
            parse_warnings=warnings,
        )

        logger.info(
            "ChatGPTImportAdapter: parsed %d items from %d conversations (%d warnings)",
            len(memory_items),
            len(conversations),
            len(warnings),
        )

        return result

    def validate_item(self, item: MemoryItem) -> list[str]:
        """Validate an imported memory item against ChatGPT-specific rules.

        Args:
            item: The memory item to validate.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        # Check required fields
        if not item.content or not item.content.strip():
            errors.append("content must be non-empty")

        # Validate metadata structure
        if not isinstance(item.metadata, dict):
            errors.append("metadata must be a dictionary")
        else:
            # Check for expected keys
            if "source" not in item.metadata:
                errors.append("metadata missing 'source' key")
            elif item.metadata["source"] != "chatgpt":
                errors.append(f"expected source='chatgpt', got '{item.metadata['source']}'")

        return errors

    def _extract_conversations(self, data: Any) -> list[dict[str, Any]]:
        """Extract conversations list from parsed JSON.

        Handles different possible JSON structures.

        Args:
            data: Parsed JSON data.

        Returns:
            List of conversation dictionaries.
        """
        # ChatGPT export is typically a JSON array of conversations
        if isinstance(data, list):
            return data

        # Try common keys for conversations array
        for key in ["conversations", "history", "data"]:
            value = data.get(key)
            if isinstance(value, list):
                return value

        return []

    def _extract_message_content(self, msg: dict[str, Any]) -> str:
        """Extract message content from ChatGPT message object.

        Args:
            msg: Message dictionary from ChatGPT export.

        Returns:
            Extracted message content string.
        """
        content = msg.get("content", {})

        # Handle different content types
        content_type = content.get("content_type", "text")

        if content_type == "text":
            parts = content.get("parts", [])
            if parts:
                return "\n".join(str(part) for part in parts)

        # Fallback to generic extraction
        return extract_text_segments(msg, ["content", "text", "message"])

    def _extract_timestamp(self, msg: dict[str, Any]) -> str | None:
        """Extract ISO timestamp from message.

        Args:
            msg: Message dictionary from ChatGPT export.

        Returns:
            ISO formatted timestamp string or None.
        """
        # Try create_time (ISO 8601 format in ChatGPT export)
        create_time = msg.get("create_time")
        if create_time:
            try:
                # ChatGPT uses ISO 8601 format
                dt = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
                return dt.isoformat()
            except (ValueError, AttributeError):
                pass

        # Try other common field names
        for key in ["timestamp", "date", "time", "updated_time"]:
            value = msg.get(key)
            if isinstance(value, str):
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return dt.isoformat()
                except (ValueError, AttributeError):
                    return value

        return None
