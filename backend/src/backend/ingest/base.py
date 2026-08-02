"""Import Framework — Base classes and core interfaces.

Per D5 Entry Layer Architecture:
- Import is a permanent product capability, not a migration tool
- Each import source uses an Adapter that parses → validates → yields MemoryItems
- The pipeline is source-agnostic; only the adapter knows source formats
- Imported memories enter the normal Memory pipeline (capture_memory)

Architecture:
    External Data → ImportAdapter.parse() → MemoryItem[] → MemoryService.import_memories()
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ImportSource(str, Enum):
    """Known import source types."""

    OPEN_WEBUI = "open_webui"
    CHATGPT = "chatgpt"
    # Future: CLAUDE, GEMINI, HERMES, MARKDOWN, JSON, MEMORYHUB_BACKUP


class ImportValidationLevel(str, Enum):
    """How strictly to validate imported items."""

    STRICT = "strict"
    LENIENT = "lenient"
    PERMISSIVE = "permissive"


# ---------------------------------------------------------------------------
# Core DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryItem:
    """A single memory unit extracted from any import source.

    This is the canonical intermediate representation between adapters
    and MemoryService. Adapters produce MemoryItems; MemoryService consumes them.
    """

    content: str
    entity_id: UUID | None = None
    level: int = 1
    source: str = "import"
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: str | None = None
    raw_content: str | None = None  # Original content for evidence preservation

    def validate(self, strict: bool = True) -> list[str]:
        """Return list of validation error messages (empty if valid)."""
        errors: list[str] = []
        if not self.content or not self.content.strip():
            errors.append("content must be non-empty")
        if strict and not self.entity_id:
            errors.append("entity_id is required in strict mode")
        if self.level not in (1, 2, 3):
            errors.append(f"level must be 1, 2, or 3, got {self.level}")
        return errors


@dataclass(frozen=True)
class ImportResult:
    """Result of parsing a single import source file/payload."""

    source: ImportSource
    items: list[MemoryItem]
    raw_size_bytes: int = 0
    parse_warnings: list[str] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0


# ---------------------------------------------------------------------------
# Base Adapter Interface
# ---------------------------------------------------------------------------


class BaseImportAdapter(ABC):
    """Base class for all import adapters.

    Stateless singleton — no mutable instance state.
    """

    @property
    @abstractmethod
    def source(self) -> ImportSource:
        pass

    @abstractmethod
    def parse(self, data: bytes | str, **kwargs: Any) -> ImportResult:
        pass

    def validate_item(self, item: MemoryItem) -> list[str]:
        return item.validate(strict=False)

    def get_supported_mime_types(self) -> list[str]:
        return ["application/json", "text/plain"]


# ---------------------------------------------------------------------------
# Pipeline Orchestrator
# ---------------------------------------------------------------------------


class ImportPipeline:
    """Orchestrates: parse → validate → yield.

    Stateless singleton — no mutable instance state.
    """

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def execute(self, source_type: ImportSource, data: bytes | str, **kwargs: Any) -> ImportResult:
        adapter = self._registry.get_adapter(source_type)
        if adapter is None:
            available = [s.value for s in self._registry.list_sources()]
            raise ValueError(
                f"No adapter for source '{source_type.value}'. Available: {available}"
            )

        logger.info(
            "ImportPipeline: parsing %d bytes from source=%s",
            len(data.encode() if isinstance(data, str) else data),
            source_type.value,
        )

        result: ImportResult = adapter.parse(data, **kwargs)

        valid_items: list[MemoryItem] = []
        for item in result.items:
            errors = adapter.validate_item(item)
            if errors:
                result.parse_warnings.extend(
                    f"Item skipped: {'; '.join(errors)}"
                )
            else:
                valid_items.append(item)

        # Rebuild the result with only valid items (since it's a frozen dataclass)
        from dataclasses import replace
        result = replace(result, items=valid_items)
        logger.info(
            "ImportPipeline: %d/%d items valid for source=%s",
            len(valid_items),
            result.item_count + len(result.parse_warnings),
            source_type.value,
        )

        return result
