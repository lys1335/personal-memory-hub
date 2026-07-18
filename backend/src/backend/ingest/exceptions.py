"""Import Exceptions.

Defines exception hierarchy for the Import Framework.
"""

from __future__ import annotations

from backend.service.exceptions import MemoryHubError


class ImportFrameworkError(MemoryHubError):
    """Base exception for import framework errors."""


class AdapterNotFoundError(ImportFrameworkError):
    """Raised when no adapter is registered for a source type."""

    def __init__(self, source: str) -> None:
        super().__init__(f"No import adapter registered for source: {source}")
        self.source = source


class ParseError(ImportFrameworkError):
    """Raised when import data cannot be parsed."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"Failed to parse {source} import data: {message}")
        self.source = source


class ValidationError(ImportFrameworkError):
    """Raised when imported items fail validation."""

    def __init__(self, items: list[str]) -> None:
        self.items = items
        super().__init__(f"Import validation failed for {len(items)} items")
