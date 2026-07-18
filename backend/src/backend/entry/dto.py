"""Entry Layer DTOs — External-facing data transfer objects.

Per D5 §7 DTO Strategy:
- Entry Layer defines external DTOs (protocol-specific)
- Immutable after creation
- Serializable (standard JSON)
- Self-describing (include all necessary metadata)
- Minimal (expose only what contract requires)
- Version-aware (support backward compatibility)

Categories:
- External DTOs: Entry Layer owns these (protocol-specific contracts)
- Internal DTOs: Service Layer owns these (protocol-agnostic interfaces)
- Domain Models: Domain Engines own these (pure domain objects)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ResponseStatus(str, Enum):
    """Response status classification."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class ErrorCategory(str, Enum):
    """Error category per D5 §8.1."""

    CONTRACT_VALIDATION = "CONTRACT_VALIDATION"
    DOMAIN_ERROR = "DOMAIN_ERROR"
    INFRASTRUCTURE = "INFRASTRUCTURE"


# ---------------------------------------------------------------------------
# Type Variables
# ---------------------------------------------------------------------------

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Base Response
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaseResponse(Generic[T]):
    """Base response structure for all Entry Layer responses.

    Per D5 §5.2: Every response MUST include:
    - request_id: Request correlation
    - timestamp: Response time
    - status: Success/failure classification
    - data: Response payload (on success)
    - error: Error details (on failure)
    - metadata: Additional context (optional)
    """

    request_id: str
    timestamp: str
    status: ResponseStatus
    data: T | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, request_id: str, data: T, metadata: dict[str, Any] | None = None) -> BaseResponse[T]:
        """Create a success response."""
        return cls(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ResponseStatus.SUCCESS,
            data=data,
            error=None,
            metadata=metadata or {},
        )

    @classmethod
    def error_response(
        cls,
        request_id: str,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        category: ErrorCategory = ErrorCategory.DOMAIN_ERROR,
    ) -> BaseResponse[Any]:
        return cls(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ResponseStatus.ERROR,
            data=None,
            error={
                "code": code,
                "message": message,
                "details": details or {},
                "category": category.value,
            },
            metadata={},
        )


# ---------------------------------------------------------------------------
# Contract Validation Errors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractValidationError:
    """Error from Entry Layer contract validation.

    Per D5 §6.3: Contract validation errors are distinct from domain errors.
    """

    code: str  # CONTRACT_MISSING_FIELD, CONTRACT_INVALID_TYPE, etc.
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dict for JSON serialization."""
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Memory Entry DTOs (External)
# ---------------------------------------------------------------------------


@dataclass
class CaptureMemoryRequest:
    """External DTO for capturing a memory.

    Maps to MemoryService.capture_memory() command.
    """

    workspace_id: str
    content: str
    entity_id: str | None = None
    level: int = 1
    node_type: str = "Observation"
    source: str = "user"
    confidence: float = 0.0
    importance: float = 0.0
    signal_strength: float = 0.0
    observation_type: str | None = None
    metadata: dict[str, Any] | None = None

    def to_internal_dict(self) -> dict[str, Any]:
        """Translate to Service Layer command dict."""
        return {
            "workspace_id": UUID(self.workspace_id),
            "entity_id": UUID(self.entity_id) if self.entity_id else None,
            "content": self.content,
            "level": self.level,
            "node_type": self.node_type,
            "source": self.source,
            "confidence": self.confidence,
            "importance": self.importance,
            "signal_strength": self.signal_strength,
            "observation_type": self.observation_type,
            "metadata": self.metadata or {},
        }


@dataclass
class CaptureMemoryResponse:
    """External DTO for capture memory response."""

    memory_id: str
    workspace_id: str
    entity_id: str | None
    level: int
    source: str
    confidence: float
    importance: float
    signal_strength: float
    evidence_count: int


# ---------------------------------------------------------------------------
# Query Entry DTOs (External)
# ---------------------------------------------------------------------------


@dataclass
class SearchRequest:
    """External DTO for search queries."""

    workspace_id: str
    query: str
    entity_id: str | None = None
    level: int | None = None
    limit: int = 50
    offset: int = 0
    ranking_approach: str = "relevance"

    def to_internal_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": UUID(self.workspace_id),
            "query": self.query,
            "entity_id": UUID(self.entity_id) if self.entity_id else None,
            "level": self.level,
            "limit": self.limit,
            "offset": self.offset,
        }


@dataclass
class RetrieveRequest:
    """External DTO for retrieving a memory by ID."""

    workspace_id: str
    memory_id: str

    def to_internal_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": UUID(self.workspace_id),
            "memory_id": UUID(self.memory_id),
        }


# ---------------------------------------------------------------------------
# Entity Entry DTOs (External)
# ---------------------------------------------------------------------------


@dataclass
class CreateEntityRequest:
    """External DTO for creating an entity."""

    workspace_id: str
    entity_type: str
    canonical_name: str
    area_id: str | None = None
    parent_entity_id: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None
    aliases: list[str] | None = None

    def to_internal_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": UUID(self.workspace_id),
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "area_id": UUID(self.area_id) if self.area_id else None,
            "parent_entity_id": UUID(self.parent_entity_id) if self.parent_entity_id else None,
            "description": self.description,
            "metadata": self.metadata or {},
            "aliases": self.aliases or [],
        }


# ---------------------------------------------------------------------------
# Reflection Entry DTOs (External)
# ---------------------------------------------------------------------------


@dataclass
class TriggerReflectionRequest:
    """External DTO for triggering reflection."""

    workspace_id: str
    entity_id: str | None = None
    scope: str = "entity"

    def to_internal_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": UUID(self.workspace_id),
            "entity_id": UUID(self.entity_id) if self.entity_id else None,
            "scope": self.scope,
        }


# ---------------------------------------------------------------------------
# Task Entry DTOs (External)
# ---------------------------------------------------------------------------


@dataclass
class SubmitTaskRequest:
    """External DTO for submitting a task."""

    workspace_id: str
    task_type: str
    payload: dict[str, Any]
    entity_id: str | None = None
    max_retries: int = 3
    debounce_key: str | None = None

    def to_internal_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": UUID(self.workspace_id),
            "task_type": self.task_type,
            "payload": self.payload,
            "entity_id": UUID(self.entity_id) if self.entity_id else None,
            "max_retries": self.max_retries,
            "debounce_key": self.debounce_key,
        }
