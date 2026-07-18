"""Import DTOs — External-facing import request/response objects.

Per D5 §7 DTO Strategy:
- Entry Layer defines external DTOs (protocol-specific)
- Immutable after creation
- Serializable (standard JSON)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImportRequest:
    """External DTO for importing data from a source.

    Maps to MemoryService.import_from_source() command.

    Per D5 §3.3 One Operation → One Capability:
    Each import request targets exactly one source adapter.
    """

    workspace_id: str
    source_type: str  # e.g., "open_webui"
    data: str  # Base64-encoded or raw text payload
    format_hint: str | None = None  # Optional hint for parser selection
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_internal_dict(self) -> dict[str, Any]:
        """Translate to Service Layer command dict."""
        return {
            "workspace_id": self.workspace_id,
            "source_type": self.source_type,
            "data": self.data,
            "format_hint": self.format_hint,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ImportResponse:
    """External DTO for import operation response.

    Per D5 §5.2 Response Structure:
    - success_count: Items successfully ingested
    - failure_count: Items that failed (continue-on-error)
    - warnings: Non-fatal issues during parsing
    """

    success_count: int
    failure_count: int
    total_count: int
    warnings: list[str] = field(default_factory=list)
    job_id: str | None = None
