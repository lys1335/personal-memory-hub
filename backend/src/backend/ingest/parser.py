"""Import Parser Utilities.

Common parsing helpers shared across adapters.
"""

from __future__ import annotations

import ast
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Keys skipped by extract_multimodal_text (shared by app.py and chatgpt adapter).
_SKIP_KEYS = frozenset({
    "asset_pointer",
    "content_type",
    "metadata",
    "decoding_id",
    "direction",
    "tool_audio_direction",
    "frames_asset_pointers",
    "video_container_asset_pointer",
    "expiry_datetime",
})


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


def extract_multimodal_text(
    data: Any,
    *,
    depth: int = 0,
    max_depth: int = 5,
    min_length: int = 0,
) -> list[str]:
    """Recursively extract text segments from multimodal content structures.

    Unified replacement for the previously duplicated _extract_multimodal_text
    implementations in app.py and the chatgpt adapter.

    Returns list[str] (NOT joined string) — callers decide join strategy.

    min_length (v3 A1):
        Applies ONLY to the list-of-str branch (top-level list of strings).
        Does NOT apply to dict["text"] branch.
        Required to express the asymmetry between 0e4cf20 app.py (no len>2)
        and 0e4cf20 chatgpt.py (len>2 only in list-of-str branch).

    Args:
        data: Input data (typically a dict; None / str / list are tolerated).
        depth: Current recursion depth.
        max_depth: Maximum recursion depth (default 5).
        min_length: Minimum length filter applied ONLY in list-of-str branch.

    Returns:
        List of extracted text strings.
    """
    if depth >= max_depth or not isinstance(data, dict):
        return []

    texts: list[str] = []
    for key, val in data.items():
        if key in _SKIP_KEYS:
            continue

        if key == "parts" and isinstance(val, list):
            for part in val:
                texts.extend(
                    extract_multimodal_text(
                        part,
                        depth=depth + 1,
                        max_depth=max_depth,
                        min_length=min_length,
                    )
                )
        elif key == "text" and isinstance(val, str) and val.strip():
            # dict["text"] branch: only strip(), min_length does NOT apply.
            texts.append(val.strip())
        elif isinstance(val, dict):
            texts.extend(
                extract_multimodal_text(
                    val,
                    depth=depth + 1,
                    max_depth=max_depth,
                    min_length=min_length,
                )
            )
        elif isinstance(val, list):
            for item in val:
                if (
                    isinstance(item, str)
                    and item.strip()
                    and len(item) > min_length
                ):
                    # list-of-str branch: min_length DOES apply.
                    texts.append(item.strip())
                elif isinstance(item, dict):
                    texts.extend(
                        extract_multimodal_text(
                            item,
                            depth=depth + 1,
                            max_depth=max_depth,
                            min_length=min_length,
                        )
                    )

    return texts


def try_parse_python_dict(text: str) -> dict[str, Any] | list[Any] | None:
    """Parse JSON or Python literal; return None on failure.

    Top-level result must be dict or list (anything else returns None).
    Falls back to ast.literal_eval if json.loads fails.
    Never raises — returns None on any failure.

    Args:
        text: String to parse (may be empty/None).

    Returns:
        Parsed dict or list, or None if parsing fails or top-level is not a
        dict/list.
    """
    if not text:
        return None

    # Try JSON first.
    try:
        result = json.loads(text)
        if isinstance(result, (dict, list)):
            return result
        return None
    except (json.JSONDecodeError, TypeError):
        pass

    # Fall back to Python literal_eval.
    try:
        result = ast.literal_eval(text)
        if isinstance(result, (dict, list)):
            return result
        return None
    except (ValueError, SyntaxError):
        pass

    return None
