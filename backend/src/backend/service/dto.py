"""DTO models for the Service Layer.

Provides:
- Internal result models (QueryResult, CaptureResult, etc.)
- Reflection execution result
- Import job status
- Entity profile
- Pagination result wrappers

Per D3.7 Error Handling & DTO Models:
- DTOs are immutable after creation
- DTOs support standard serialization
- DTOs include all necessary metadata
- DTOs are version-aware
- DTOs expose only what the contract requires

All DTOs use dataclasses with frozen=True for immutability where appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from backend.repository.pagination import Page

# ---------------------------------------------------------------------------
# Type variables for generic DTOs
# ---------------------------------------------------------------------------

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ImportStatus(str, Enum):
    """Import job lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class ReflectionStatus(str, Enum):
    """Reflection execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# Capture Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaptureResult:
    """Result returned by MemoryService.capture_memory().

    Contains the ID of the newly captured memory and metadata.
    """

    memory_id: UUID
    workspace_id: UUID
    entity_id: UUID | None
    level: int
    source: str
    confidence: float
    importance: float
    signal_strength: float
    evidence_count: int = 0

    @classmethod
    def from_memory_id(
        cls,
        memory_id: UUID,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        level: int = 1,
        source: str = "user",
        confidence: float = 0.0,
        importance: float = 0.0,
        signal_strength: float = 0.0,
        evidence_count: int = 0,
    ) -> CaptureResult:
        """Create a CaptureResult from a memory ID."""
        return cls(
            memory_id=memory_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
            level=level,
            source=source,
            confidence=confidence,
            importance=importance,
            signal_strength=signal_strength,
            evidence_count=evidence_count,
        )


# ---------------------------------------------------------------------------
# Query Result
# ---------------------------------------------------------------------------


@dataclass
class QueryResult(Generic[T]):
    """Wrapper for query results with pagination metadata.

    Per IR-005 (Stable Result Contract): All query results use this
    wrapper to provide consistent metadata across all capabilities.
    """

    items: list[T]
    total: int | None = None
    page_number: int = 1
    page_size: int = 20
    has_next: bool = False
    has_prev: bool = False
    next_cursor: str | None = None
    prev_cursor: str | None = None
    query_id: str | None = None
    execution_time_ms: float | None = None

    @property
    def is_empty(self) -> bool:
        """Return True if this result has no items."""
        return len(self.items) == 0

    @classmethod
    def from_page(cls, page: Page[T], query_id: str | None = None) -> QueryResult[T]:
        """Create a QueryResult from a Page object."""
        return cls(
            items=page.items,
            total=page.total,
            page_number=page.page_number,
            page_size=page.page_size,
            has_next=page.has_next,
            has_prev=page.has_prev,
            next_cursor=page.next_cursor,
            prev_cursor=page.prev_cursor,
            query_id=query_id,
        )


# ---------------------------------------------------------------------------
# Entity Profile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntityProfile:
    """Profile of an entity including its memory statistics.

    Returned by EntityService.get_entity_profile() and
    QueryService.retrieve_by_entity().
    """

    entity_id: UUID
    workspace_id: UUID
    entity_type: str
    canonical_name: str
    aliases: list[str]
    description: str | None
    metadata: dict[str, Any]
    observation_count: int
    pattern_count: int
    belief_count: int
    relationship_count: int
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Reflection Execution Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReflectionExecutionResult:
    """Result returned by ReflectionService methods.

    Per IR-013: Reflection methods return an execution report, not
    business data. The actual business data (newly generated memories)
    is accessed through QueryService.

    Attributes:
        status: Overall execution status.
        reflections_performed: Number of reflection operations executed.
        new_patterns: Number of new Pattern (L2) nodes created.
        new_beliefs: Number of new Belief (L3) nodes created.
        updated_beliefs: Number of existing Belief nodes updated.
        evidence_completeness: Ratio of evidence-complete reflections.
        scope: The scope that was reflected upon.
        duration_ms: Execution duration in milliseconds.
        metadata: Additional context about the reflection.
    """

    status: ReflectionStatus
    reflections_performed: int = 0
    new_patterns: int = 0
    new_beliefs: int = 0
    updated_beliefs: int = 0
    evidence_completeness: float = 0.0
    scope: str = ""
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Import Job Status
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImportJobStatus:
    """Status of an import job.

    Attributes:
        job_id: The import job UUID.
        status: Current import status.
        total_count: Total number of items to import.
        processed_count: Number of items processed so far.
        success_count: Number of items successfully imported.
        failure_count: Number of items that failed to import.
        error_messages: List of error messages for failed items.
        started_at: ISO 8601 timestamp when import started.
        completed_at: ISO 8601 timestamp when import completed (or None).
    """

    job_id: UUID
    status: ImportStatus
    total_count: int = 0
    processed_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    error_messages: list[str] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None


# ---------------------------------------------------------------------------
# Merge Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeResult:
    """Result of an entity merge operation.

    Attributes:
        target_entity_id: The surviving entity ID.
        source_entity_ids: List of merged-away entity IDs.
        relationships_migrated: Number of relationships migrated.
        aliases_consolidated: Number of aliases consolidated.
        memories_referenced: Number of memories now referencing the target.
    """

    target_entity_id: UUID
    source_entity_ids: list[UUID]
    relationships_migrated: int = 0
    aliases_consolidated: int = 0
    memories_referenced: int = 0


# ---------------------------------------------------------------------------
# Analytics Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalyticsStatistics:
    """Aggregate statistics for a workspace or entity.

    Attributes:
        total_entities: Total number of entities.
        total_memory_nodes: Total number of memory nodes.
        observations: Count of L1 nodes.
        patterns: Count of L2 nodes.
        beliefs: Count of L3 nodes.
        total_relationships: Total number of relationships.
        total_evidences: Total number of evidence records.
        total_archives: Total number of archive records.
        total_tags: Total number of tags.
    """

    total_entities: int = 0
    total_memory_nodes: int = 0
    observations: int = 0
    patterns: int = 0
    beliefs: int = 0
    total_relationships: int = 0
    total_evidences: int = 0
    total_archives: int = 0
    total_tags: int = 0


@dataclass(frozen=True)
class AnalyticsInsight:
    """A single insight derived from analytics.

    Attributes:
        category: Insight category (e.g., "growth", "density", "activity").
        title: Short title for the insight.
        description: Detailed description.
        value: Numeric value associated with the insight.
        unit: Unit of measurement (e.g., "nodes", "per_day").
    """

    category: str
    title: str
    description: str
    value: float
    unit: str = ""


# ---------------------------------------------------------------------------
# Task Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskSubmissionResult:
    """Result of submitting a task.

    Attributes:
        task_id: The UUID of the created task.
        status: Initial task status.
        scheduled_at: ISO 8601 timestamp when the task is scheduled.
    """

    task_id: UUID
    status: TaskStatus
    scheduled_at: str | None = None


@dataclass(frozen=True)
class TaskStatusResult:
    """Result of querying task status.

    Attributes:
        task_id: The task UUID.
        task_type: Type of task (INGESTION, REFLECTION, etc.).
        status: Current task status.
        retry_count: Number of retries attempted.
        max_retries: Maximum retry limit.
        created_at: ISO 8601 timestamp when the task was created.
        updated_at: ISO 8601 timestamp when the task was last updated.
        completed_at: ISO 8601 timestamp when the task completed (or None).
        error_message: Error message if the task failed (or None).
    """

    task_id: UUID
    task_type: str
    status: TaskStatus
    retry_count: int = 0
    max_retries: int = 3
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
