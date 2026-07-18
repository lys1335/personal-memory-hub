"""Open WebUI Import Adapter.

Parses Open WebUI conversation export format and converts to MemoryItems.

Open WebUI export format (JSON):
{
    "conversations": [
        {
            "title": "Conversation Title",
            "chat_msg": [
                {
                    "id": "...",
                    "model": "...",
                    "content": "Message content...",
                    "role": "user|assistant",
                    "created_at": 1234567890,
                    ...
                },
                ...
            ]
        },
        ...
    ]
}

Each user message becomes a MemoryItem with:
- content: The user's message text
- metadata: Source info (conversation title, timestamp, model)
- tags: ["imported", "open_webui"]
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.ingest.base import (
    BaseImportAdapter,
    ImportResult,
    ImportSource,
    MemoryItem,
)
from backend.ingest.parser import extract_text_segments, sanitize_content, try_parse_json

logger = logging.getLogger(__name__)


class OpenWebUIAdapter(BaseImportAdapter):
    """Import adapter for Open WebUI conversation exports.

    Stateless singleton — no mutable instance state.
    """

    @property
    def source(self) -> ImportSource:
        return ImportSource.OPEN_WEBUI

    def parse(self, data: bytes | str, **kwargs: Any) -> ImportResult:
        """Parse Open WebUI conversation export into MemoryItems.

        Args:
            data: Raw JSON string or bytes from Open WebUI export.
            **kwargs: Additional options.

        Returns:
            ImportResult with extracted MemoryItems.

        Raises:
            ValueError: If data cannot be parsed as Open WebUI format.
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

        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object at root level")

        # Extract conversations
        conversations = self._extract_conversations(parsed)
        if not conversations:
            logger.warning("No conversations found in Open WebUI export")
            return ImportResult(
                source=ImportSource.OPEN_WEBUI,
                items=[],
                raw_size_bytes=len(data.encode("utf-8")),
                parse_warnings=["No conversations found in exported data"],
            )

        # Convert each conversation to MemoryItems
        memory_items: list[MemoryItem] = []
        warnings: list[str] = []

        for conv_idx, conv in enumerate(conversations):
            conv_title = conv.get("title", f"Conversation {conv_idx + 1}")
            messages = conv.get("chat_msg", [])

            for msg_idx, msg in enumerate(messages):
                role = msg.get("role", "").lower()

                # Only import user messages (skip assistant/system)
                if role != "user":
                    continue

                # Extract content
                content = extract_text_segments(msg, ["content", "text", "message"])
                content = sanitize_content(content, max_length=10000)

                if not content:
                    warnings.append(f"Conversation {conv_idx + 1}, message {msg_idx + 1}: empty content, skipped")
                    continue

                # Extract metadata
                created_at = self._extract_timestamp(msg)
                model = msg.get("model", "unknown")
                conversation_id = msg.get("conversation_id", "")

                # Build metadata
                metadata: dict[str, Any] = {
                    "source": "open_webui",
                    "conversation_title": conv_title,
                    "conversation_id": conversation_id,
                    "message_index": msg_idx,
                    "model": model,
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
                    tags=["imported", "open_webui", "conversation"],
                    created_at=created_at,
                )
                memory_items.append(item)

        result = ImportResult(
            source=ImportSource.OPEN_WEBUI,
            items=memory_items,
            raw_size_bytes=len(data.encode("utf-8")),
            parse_warnings=warnings,
        )

        logger.info(
            "OpenWebUIAdapter: parsed %d items from %d conversations (%d warnings)",
            len(memory_items),
            len(conversations),
            len(warnings),
        )

        return result

    def validate_item(self, item: MemoryItem) -> list[str]:
        """Validate an imported memory item against Open WebUI-specific rules.

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
            elif item.metadata["source"] != "open_webui":
                errors.append(f"expected source='open_webui', got '{item.metadata['source']}'")

        return errors

    def _extract_conversations(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract conversations list from parsed JSON.

        Handles different possible JSON structures.
        """
        # Try common keys for conversations array
        for key in ["conversations", "chats", "messages", "data"]:
            value = data.get(key)
            if isinstance(value, list):
                return value

        # If root is a list, treat it as conversations directly
        if isinstance(data, list):
            return data

        return []

    def _extract_timestamp(self, msg: dict[str, Any]) -> str | None:
        """Extract ISO timestamp from message.

        Handles both Unix timestamp (integer) and ISO string formats.
        """
        # Try created_at (Unix timestamp)
        created_at = msg.get("created_at")
        if created_at is not None:
            try:
                # Handle both int and float timestamps
                timestamp = float(created_at)
                # If it looks like milliseconds (> year 2100), convert to seconds
                if timestamp > 9999999999:  # After 2100 in seconds
                    timestamp = timestamp / 1000.0
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                return dt.isoformat()
            except (ValueError, OSError, OverflowError):
                pass

        # Try other common field names
        for key in ["timestamp", "date", "time", "created"]:
            value = msg.get(key)
            if isinstance(value, str):
                return value

        return None
