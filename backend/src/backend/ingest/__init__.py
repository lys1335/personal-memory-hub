"""Import Framework — Public API.

Per D5 Entry Layer Architecture:
- Import is a permanent product capability, not a migration tool
- Each import source uses an Adapter that parses → validates → yields MemoryItems
- The pipeline is source-agnostic; only the adapter knows source formats
- Imported memories enter the normal Memory pipeline (capture_memory)
"""

from __future__ import annotations

from backend.ingest.base import (
    BaseImportAdapter,
    ImportPipeline,
    ImportResult,
    ImportSource,
    ImportValidationLevel,
    MemoryItem,
)
from backend.ingest.registry import ImportRegistry

__all__ = [
    "BaseImportAdapter",
    "ImportPipeline",
    "ImportResult",
    "ImportSource",
    "ImportValidationLevel",
    "MemoryItem",
    "ImportRegistry",
]
