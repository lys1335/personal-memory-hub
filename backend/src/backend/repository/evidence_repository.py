"""EvidenceRepository - CRUD for the Evidence aggregate.

Evidence is immutable: once created, never deleted or modified.
Every MemoryNode must have at least one evidence link (No Orphan Memory).

Per 10_9 §4.3 and 09 §09.4.6:
- Aggregate root: Evidence
- Table: memory_hub.evidences
- Immutable: no update(), no soft_delete()
- Constraint: content not empty (chk_evidence_not_empty)
- Three-score separation: confidence, importance, signal_strength (0.0-1.0)
- Types: conversation, manual, explicit_command, document, import
- Source: conversation, manual, explicit_command, document, import

Inherits from BaseRepository but overrides write operations to enforce
immutability.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.base import BaseRepository
from backend.repository.exceptions import (
    IntegrityError as DomainIntegrityError,
)
from backend.repository.pagination import Page


class EvidenceRepository(BaseRepository):
    """Repository for the Evidence aggregate.

    Evidence is IMMUTABLE: no update or soft_delete.
    Every MemoryNode must have at least one evidence link.
    """

    _model_class: type[Any]  # Evidence (imported lazily to avoid circular)
    _table_name = "evidences"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the evidence repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        # Import here to avoid circular dependency
        from backend.shared.domain.memory_models import Evidence

        self._model_class = Evidence

    # ------------------------------------------------------------------
    # Immutable Enforcement - Evidence cannot be modified or deleted
    # ------------------------------------------------------------------

    async def update(self, entity: Any) -> Any:
        """Evidence is immutable: update is prohibited.

        Raises:
            DomainIntegrityError: Always, because evidence cannot be modified.
        """
        raise DomainIntegrityError(
            entity_type="evidence",
            constraint="Evidence is immutable - no UPDATE allowed",
        )

    async def soft_delete(self, id: UUID) -> None:
        """Evidence is immutable: soft_delete is prohibited.

        Raises:
            DomainIntegrityError: Always, because evidence cannot be deleted.
        """
        raise DomainIntegrityError(
            entity_type="evidence",
            constraint="Evidence is immutable - no DELETE allowed",
        )

    async def exists(self, id: UUID) -> bool:
        """Evidence exists check is not applicable for immutable evidence.

        Use find_by_id() instead to check existence.
        """
        entity = await self.find_by_id(id)
        return entity is not None

    async def soft_delete_impl(self, id: UUID) -> None:
        """Evidence is immutable: soft_delete_impl is prohibited.

        Raises:
            DomainIntegrityError: Always.
        """
        raise DomainIntegrityError(
            entity_type="evidence",
            constraint="Evidence is immutable - no soft delete allowed",
        )

    # ------------------------------------------------------------------
    # Create (the only write operation)
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new evidence and persist it.

        Evidence is immutable - this is the ONLY write operation allowed.

        Args:
            entity: The Evidence domain object to create.

        Returns:
            The UUID of the created evidence.

        Raises:
            DomainIntegrityError: If content is empty or constraints violated.
            IntegrityError: If a uniqueness or foreign key constraint fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            entity_id = getattr(entity, "id", None)
            if entity_id is None:
                raise DomainIntegrityError(
                    entity_type="evidence",
                    constraint="Created evidence has no id",
                )
            return UUID(entity_id) if not isinstance(entity_id, UUID) else entity_id
        except IntegrityError as exc:
            self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover — _raise_integrity_error always raises

    # ------------------------------------------------------------------
    # Read Operations
    # ------------------------------------------------------------------

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        evidence_types: list[str] | None = None,
        sources: list[str] | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> list[Any]:
        """Find evidence by workspace with optional filters.

        Args:
            workspace_id: Workspace scope.
            evidence_types: Filter by evidence_type (e.g., ['conversation', 'manual']).
            sources: Filter by source (e.g., ['user', 'ai_reflect']).
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching Evidence entities.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id
        )

        if evidence_types:
            stmt = stmt.where(self._model_class.evidence_type.in_(evidence_types))
        if sources:
            stmt = stmt.where(self._model_class.source.in_(sources))

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
        """Find all evidence linked to a specific entity.

        Args:
            entity_id: The entity UUID to filter by.
            workspace_id: Workspace scope.

        Returns:
            List of Evidence entities for the given entity.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.entity_id == entity_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_source(
        self,
        *,
        source: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find evidence by source type.

        Args:
            source: Source type (conversation, manual, explicit_command, document, import).
            workspace_id: Workspace scope.

        Returns:
            List of Evidence entities matching the source.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.source == source,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def find_page(
        self,
        *,
        workspace_id: UUID,
        evidence_types: list[str] | None = None,
        sources: list[str] | None = None,
        page_number: int = 1,
        page_size: int = 20,
    ) -> Page[Any]:
        """Find evidence with pagination.

        Args:
            workspace_id: Workspace scope.
            evidence_types: Optional filter by evidence type.
            sources: Optional filter by source.
            page_number: 1-based page number.
            page_size: Items per page.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_by_workspace(
            workspace_id=workspace_id,
            evidence_types=evidence_types,
            sources=sources,
            offset=offset,
            limit=page_size + 1,
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

        Raises:
            DomainIntegrityError: Always (for evidence, all integrity errors
                indicate constraint violations on immutable data).
        """
        orig = exc.orig
        msg = str(orig) if orig else str(exc)

        if "unique" in msg.lower() or "duplicate" in msg.lower():
            raise DomainIntegrityError(
                entity_type="evidence",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="evidence",
            constraint=msg[:200],
        )
