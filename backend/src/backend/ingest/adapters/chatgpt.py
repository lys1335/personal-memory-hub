"""ChatGPT Import Adapter.

Parses ChatGPT conversation export format and converts to MemoryItems.

Supported formats:
1. conversations-*.json (JSON array of conversations)
   Each conversation has mapping[msg_id] = {message: {author, content, ...}, parent}
2. chat.html (HTML with embedded JSON in <script> tag)
   Same structure as conversations-*.json but extracted from HTML

Each user message becomes a MemoryItem with:
- content: The user's message text
- metadata: Source info (conversation title, timestamp, model)
- tags: ["imported", "chatgpt", "conversation"]
"""

from __future__ import annotations

import json
import logging
import re
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

        Supports multiple input formats:
        - Raw JSON array (conversations-*.json)
        - Single conversation JSON object
        - HTML file containing embedded JSON (chat.html)

        Args:
            data: Raw JSON string, bytes, or HTML file content.
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

        # Auto-detect format: HTML vs JSON
        if "<html" in data.lower() or "<script" in data.lower():
            logger.info("Detected HTML format, extracting JSON from script tags")
            extracted = self._extract_json_from_html(data)
            if extracted is None:
                raise ValueError("No JSON data found in HTML file")
            data = extracted

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

            for msg_id, entry in mapping.items():
                # Handle two possible structures:
                # 1. Direct: {author: {...}, content: {...}}
                # 2. Wrapped: {message: {author: {...}, content: {...}}, parent: ...}
                msg = self._resolve_message_entry(entry)
                if msg is None:
                    continue

                author = msg.get("author", {})
                role = ""
                if isinstance(author, dict):
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
                # raw_content stores the original message for evidence preservation
                # content is the extracted text summary
                item = MemoryItem(
                    content=content,
                    raw_content=content,  # Store original for evidence
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

    # ------------------------------------------------------------------
    # Format Detection & Extraction
    # ------------------------------------------------------------------

    def _extract_json_from_html(self, html: str) -> str | None:
        """Extract the largest JSON block from an HTML file.

        ChatGPT exports embed conversation data in a <script> tag as JSON.

        Args:
            html: HTML file content.

        Returns:
            JSON string, or None if not found.
        """
        # Find all script tag contents
        script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

        best_json: str | None = None
        best_len = 0

        for script_content in script_matches:
            if len(script_content) < 500:
                continue  # Skip small scripts

            # Try to find a large JSON object
            start = script_content.find('{')
            if start < 0:
                continue

            depth = 0
            end = start
            for i in range(start, len(script_content)):
                if script_content[i] == '{':
                    depth += 1
                elif script_content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            block = script_content[start:end]
            if len(block) > best_len:
                try:
                    json.loads(block)
                    best_json = block
                    best_len = len(block)
                except json.JSONDecodeError:
                    pass

        if best_json:
            return best_json

        # Fallback: try parsing entire script content as JSON
        for script_content in script_matches:
            stripped: str = script_content.strip()
            if stripped.startswith('{') or stripped.startswith('['):
                try:
                    json.loads(stripped)
                    return stripped
                except json.JSONDecodeError:
                    pass

        return None

    # ------------------------------------------------------------------
    # Message Resolution
    # ------------------------------------------------------------------

    def _resolve_message_entry(self, entry: Any) -> dict[str, Any] | None:
        """Resolve a mapping entry to its message dict.

        ChatGPT export uses two possible structures:
        1. Old/direct: {author: {...}, content: {...}}
        2. New/wrapped: {message: {author: {...}, content: {...}}, parent: ...}

        Args:
            entry: A value from conversation['mapping'].

        Returns:
            Resolved message dict, or None.
        """
        if not isinstance(entry, dict):
            return None

        # Check if wrapped in 'message' key
        if "message" in entry:
            msg = entry["message"]
            if isinstance(msg, dict):
                return msg

        # Direct format (fallback)
        if "author" in entry or "content" in entry:
            return entry

        return None

    # ------------------------------------------------------------------
    # Conversation Extraction
    # ------------------------------------------------------------------

    def _extract_conversations(self, data: Any) -> list[dict[str, Any]]:
        """Extract conversations list from parsed JSON.

        Handles different possible JSON structures:
        - JSON array of conversations (conversations-*.json)
        - Single conversation object
        - Object with 'conversations' key

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

        # Single conversation object
        if isinstance(data, dict) and "mapping" in data:
            return [data]

        return []

    # ------------------------------------------------------------------
    # Content Extraction
    # ------------------------------------------------------------------

    def _extract_message_content(self, msg: dict[str, Any]) -> str:
        """Extract message content from ChatGPT message object.

        Handles multimodal text by recursively extracting transcription text
        from parts array.

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

        # For multimodal_text, recursively extract text from parts
        if isinstance(content, dict):
            texts = self._extract_multimodal_text(content)
            if texts:
                return "\n".join(texts)

        # Handle image attachments
        if content_type == "image":
            return "[Image attachment]"

        # Fallback to generic extraction
        fallback = extract_text_segments(msg, ["content", "text", "message"])
        if fallback:
            return fallback

        # Indicate non-text content instead of returning raw JSON
        return ""

    def _extract_multimodal_text(self, data: dict[str, Any], depth: int = 0) -> list[str]:
        """Recursively extract text from multimodal content.

        Traverses the content structure looking for transcription text
        in parts array and other nested structures.

        Args:
            data: Content dictionary to traverse.
            depth: Current recursion depth (max 5).

        Returns:
            List of extracted text strings.
        """
        if depth > 5 or not isinstance(data, dict):
            return []

        texts = []

        # Skip metadata/pointer fields
        skip_keys = {"asset_pointer", "content_type", "metadata", "decoding_id",
                     "direction", "tool_audio_direction", "frames_asset_pointers",
                     "video_container_asset_pointer", "expiry_datetime"}

        for key, val in data.items():
            if key in skip_keys:
                continue

            if key == "parts" and isinstance(val, list):
                # Recursively extract from each part
                for part in val:
                    texts.extend(self._extract_multimodal_text(part, depth + 1))
            elif key == "text" and isinstance(val, str) and val.strip():
                texts.append(val.strip())
            elif isinstance(val, dict):
                texts.extend(self._extract_multimodal_text(val, depth + 1))
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item.strip() and len(item) > 2:
                        texts.append(item.strip())
                    elif isinstance(item, dict):
                        texts.extend(self._extract_multimodal_text(item, depth + 1))

        return texts

    # Timestamp Extraction
    # ------------------------------------------------------------------

    def _extract_timestamp(self, msg: dict[str, Any]) -> str | None:
        """Extract ISO timestamp from message.

        Args:
            msg: Message dictionary from ChatGPT export.

        Returns:
            ISO formatted timestamp string or None.
        """
        # Try create_time (Unix epoch in ChatGPT export)
        create_time = msg.get("create_time")
        if create_time:
            try:
                # ChatGPT uses Unix timestamp (float seconds since epoch)
                if isinstance(create_time, (int, float)):
                    dt = datetime.fromtimestamp(create_time)
                    return dt.isoformat()
                # Also try ISO format
                dt = datetime.fromisoformat(str(create_time).replace("Z", "+00:00"))
                return dt.isoformat()
            except (ValueError, AttributeError, OSError):
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
