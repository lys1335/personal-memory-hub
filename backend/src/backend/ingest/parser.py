"""Import Parser Utilities.

Common parsing helpers shared across adapters.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def try_parse_json(data: str) -> dict[str, Any] | list[Any] | None:
    """Attempt to parse a string as JSON.

    Args:
        data: String to parse.

    Returns:
        Parsed JSON object, or None if parsing fails.
    """
    try:
        result: dict[str, Any] | list[Any] | None = json.loads(data)
        return result
    except (json.JSONDecodeError, TypeError):
        return None


def sanitize_content(text: str | None, max_length: int = 10000) -> str:
    """Sanitize content for memory storage.

    - Strips leading/trailing whitespace
    - Replaces multiple newlines with single newline
    - Truncates to max_length

    Args:
        text: Raw text to sanitize.
        max_length: Maximum allowed length.

    Returns:
        Sanitized content string.
    """
    if not text:
        return ""

    # Strip and normalize whitespace
    text = text.strip()
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Truncate if too long
    if len(text) > max_length:
        logger.warning("Content truncated from %d to %d chars", len(text), max_length)
        text = text[:max_length]

    return text


def extract_text_segments(data: dict[str, Any], keys: list[str]) -> str:
    """Extract text segments from a dict by trying multiple key paths.

    Useful for flexible parsing where different sources use different key names.

    Args:
        data: Dictionary to search.
        keys: Ordered list of keys to try.

    Returns:
        First non-empty value found, or empty string.
    """
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = extract_text_segments(value, keys)
            if nested:
                return nested
    return ""
