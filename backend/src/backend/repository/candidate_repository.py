"""CandidateRepository — CRUD for the Candidate aggregate.

Manages the Candidate aggregate root exclusively. Candidates are Reflection
pipeline work objects — patterns or beliefs awaiting promotion to formal
MemoryNodes.

Per 10_9 §4.9 and 09 §09.4.13:
- Aggregate root: Candidate
- Tables: candidates
- Candidate types: pattern, belief
- Status: candidate, confirmed, archived, orphaned
- Evidence-based: evidence_count >= 1, evidence_chain not empty
- Ingested by: ingestion_pipeline only
- Verified by: rule_engine / reflection_engine only

Responsibilities:
- Candidate CRUD and lifecycle queries
- Status lookups (candidate, confirmed, archived, orphaned)
- Entity-scoped candidate queries
- Type-scoped queries (pattern, belief)
- Evidence strength queries
- Pagination

Must NOT perform:
- Reflection logic
- Memory materialization
- Entity updates
- Vector operations
- Cross-domain operations
- Business ranking

Inherits from BaseRepository.
Repository persists Candidate aggregate only.

Imported by: ReflectionService, ReflectionEngine, CandidateEngine.
NOT imported by: Engine Layer (boundary rule G-013).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.base import BaseRepository
from backend.repository.exceptions import (
    DuplicateError,
)
from backend.repository.exceptions import (
    IntegrityError as DomainIntegrityError,
)
from backend.repository.pagination import Page


class CandidateRepository(BaseRepository):  # type: ignore[type-arg]
    """Repository for the Candidate aggregate.

    Manages Candidate persistence only. Candidates are Reflection pipeline
    work objects awaiting promotion to MemoryNodes.
    """

    _model_class: type[Any]  # Candidate (imported lazily)
    _table_name = "candidates"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the candidate repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Candidate

        self._model_class = Candidate

    # ------------------------------------------------------------------
    # Candidate CRUD
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new candidate and persist it.

        Args:
            entity: The Candidate domain object to create.

        Returns:
            The UUID of the created candidate.

        Raises:
            DomainIntegrityError: If candidate_type or status is invalid,
                or evidence constraints are violated.
            IntegrityError: If a uniqueness or foreign key constraint fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            candidate_id = getattr(entity, "id", None)
            if candidate_id is None:
                raise DomainIntegrityError(
                    entity_type="candidate",
                    constraint="Created candidate has no id",
                )
            return UUID(candidate_id) if not isinstance(candidate_id, UUID) else candidate_id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_id(self, id: UUID) -> Any | None:
        """Find a candidate by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The Candidate if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Candidate Queries
    # ------------------------------------------------------------------

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        candidate_types: list[str] | None = None,
        status: str | None = None,
        entity_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> list[Any]:
        """Find candidates by workspace with optional filters.

        Args:
            workspace_id: Workspace scope.
            candidate_types: Filter by candidate_type (pattern, belief).
            status: Filter by status (candidate, confirmed, archived, orphaned).
            entity_id: Filter by associated entity.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching Candidate objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )

        if candidate_types:
            stmt = stmt.where(self._model_class.candidate_type.in_(candidate_types))
        if status:
            stmt = stmt.where(self._model_class.status == status)
        if entity_id:
            stmt = stmt.where(self._model_class.entity_id == str(entity_id))

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_entity(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all candidates for a specific entity.

        Args:
            entity_id: The entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of Candidate objects for the entity.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.entity_id == str(entity_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_status(
        self,
        *,
        status: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find candidates by status within a workspace.

        Args:
            status: Status (candidate, confirmed, archived, orphaned).
            workspace_id: Workspace scope.

        Returns:
            List of Candidate objects with the given status.

        Raises:
            DomainIntegrityError: If status is not a valid value.
        """
        valid_statuses = ("candidate", "confirmed", "archived", "orphaned")
        if status not in valid_statuses:
            raise DomainIntegrityError(
                entity_type="candidate",
                constraint=f"Invalid status: {status}. Must be one of {valid_statuses}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.status == status,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_candidate_type(
        self,
        *,
        candidate_type: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find candidates by type within a workspace.

        Args:
            candidate_type: Candidate type (pattern, belief).
            workspace_id: Workspace scope.

        Returns:
            List of Candidate objects of the given type.

        Raises:
            DomainIntegrityError: If candidate_type is not valid.
        """
        valid_types = ("pattern", "belief")
        if candidate_type not in valid_types:
            raise DomainIntegrityError(
                entity_type="candidate",
                constraint=f"Invalid candidate_type: {candidate_type}. Must be one of {valid_types}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.candidate_type == candidate_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_evidence_strength(
        self,
        *,
        min_strength: float,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find candidates with evidence strength above a threshold.

        Args:
            min_strength: Minimum evidence strength (0.0-1.0).
            workspace_id: Workspace scope.

        Returns:
            List of Candidate objects meeting the threshold.

        Raises:
            DomainIntegrityError: If min_strength is out of range.
        """
        if not (0.0 <= min_strength <= 1.0):
            raise DomainIntegrityError(
                entity_type="candidate",
                constraint="min_strength must be between 0.0 and 1.0",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.evidence_strength >= min_strength,
        ).order_by(self._model_class.evidence_strength.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def find_page(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        candidate_types: list[str] | None = None,
        status: str | None = None,
        entity_id: UUID | None = None,
        page_number: int = 1,
        page_size: int = 20,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> Page[Any]:
        """Find candidates with pagination.

        Args:
            workspace_id: Workspace scope.
            candidate_types: Optional candidate type filter.
            status: Optional status filter.
            entity_id: Optional entity filter.
            page_number: 1-based page number.
            page_size: Items per page.
            order_by: Column to order by.
            descending: Descending order.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_by_workspace(
            workspace_id=workspace_id,
            candidate_types=candidate_types,
            status=status,
            entity_id=entity_id,
            offset=offset,
            limit=page_size + 1,
            order_by=order_by,
            descending=descending,
        )

        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]

        return Page(
            items=items,
            total=None,
            page_number=page_number,
            page_size=page_size,
            has_next=has_next,
            has_prev=page_number > 1,
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _raise_integrity_error(self, exc: IntegrityError) -> None:
        """Map SQLAlchemy IntegrityError to domain exception.

        Args:
            exc: The SQLAlchemy IntegrityError.
        """
        orig = exc.orig
        msg = str(orig) if orig else str(exc)

        if "unique" in msg.lower() or "duplicate" in msg.lower():
            raise DuplicateError(
                entity_type="candidate",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="candidate",
            constraint=msg[:200],
        )
