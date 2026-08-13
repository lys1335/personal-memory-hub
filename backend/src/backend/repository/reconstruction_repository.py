"""ReconstructionRepository — CRUD for Reconstruction aggregate.

Manages the Reconstruction aggregate root exclusively. Reconstructions are
semantic version objects that persist between Evidence and Candidate.

Phase 21.2: Reconstruction persistence layer.

Responsibilities:
- Reconstruction CRUD and lifecycle queries
- Version chain queries (parent/child lookups)
- Evidence refs management
- Candidate linkage (1:1 relationship)
- Workspace isolation

Must NOT perform:
- Context Window formation
- Semantic retrieval
- Evidence selection
- Candidate formation
- LLM calls

Inherits from BaseRepository.
Repository persists Reconstruction aggregate only.

Imported by: ReconstructionService, ReconstructionEngine
NOT imported by: Service Layer (boundary rule G-013).
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


class ReconstructionRepository(BaseRepository):  # type: ignore[type-arg]
    """Repository for the Reconstruction aggregate.

    Manages Reconstruction persistence only. Reconstructions are semantic
    version objects awaiting promotion to Candidate snapshots.
    """

    _model_class: type[Any]  # Reconstruction (imported lazily)
    _table_name = "reconstructions"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the reconstruction repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Reconstruction

        self._model_class = Reconstruction

    # ------------------------------------------------------------------
    # Reconstruction CRUD
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new reconstruction and persist it.

        Args:
            entity: The Reconstruction domain object to create.

        Returns:
            The UUID of the created reconstruction.

        Raises:
            DomainIntegrityError: If constraints are violated.
            IntegrityError: If a uniqueness or foreign key constraint fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            reconstruction_id = getattr(entity, "id", None)
            if reconstruction_id is None:
                raise DomainIntegrityError(
                    entity_type="reconstruction",
                    constraint="Created reconstruction has no id",
                )
            return UUID(reconstruction_id) if not isinstance(reconstruction_id, UUID) else reconstruction_id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_id(self, id: UUID) -> Any | None:
        """Find a reconstruction by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The Reconstruction if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, entity: Any) -> Any:
        """Update an existing reconstruction.

        Args:
            entity: The Reconstruction domain object to update.

        Returns:
            The updated Reconstruction.

        Raises:
            DomainIntegrityError: If reconstruction not found.
        """
        stmt = select(self._model_class).where(self._model_class.id == entity.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            raise DomainIntegrityError(
                entity_type="reconstruction",
                constraint=f"Reconstruction {entity.id} not found",
            )

        for key in ["semantic_summary", "decision_type", "confidence", "evidence_refs",
                    "evidence_count", "status", "candidate_id", "updated_at"]:
            if hasattr(entity, key):
                setattr(existing, key, getattr(entity, key))

        return existing

    # ------------------------------------------------------------------
    # Reconstruction Queries
    # ------------------------------------------------------------------

    async def soft_delete_impl(self, id: UUID) -> None:
        """Soft delete a reconstruction by setting status to 'archived'."""
        from sqlalchemy import update

        stmt = (
            update(self._model_class)
            .where(self._model_class.id == id)
            .values(status="archived", updated_at=datetime.utcnow())
        )
        await self.session.execute(stmt)

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        status: str | None = None,
        entity_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        """Find reconstructions by workspace with optional filters.

        Args:
            workspace_id: Workspace scope.
            status: Filter by status.
            entity_id: Filter by associated entity.
            limit: Maximum records.
            offset: Skip records.

        Returns:
            List of matching Reconstruction objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )

        if status:
            stmt = stmt.where(self._model_class.status == status)
        if entity_id:
            stmt = stmt.where(self._model_class.entity_id == str(entity_id))

        stmt = stmt.order_by(self._model_class.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_candidate_id(self, candidate_id: UUID) -> Any | None:
        """Find reconstruction linked to a candidate.

        Args:
            candidate_id: The candidate UUID.

        Returns:
            The Reconstruction if found, None otherwise.
        """
        stmt = select(self._model_class).where(
            self._model_class.candidate_id == str(candidate_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_parent(self, parent_id: UUID) -> list[Any]:
        """Find child reconstructions by parent ID.

        Args:
            parent_id: The parent reconstruction UUID.

        Returns:
            List of child Reconstruction objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.parent_reconstruction_id == str(parent_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_latest_by_entity(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
    ) -> Any | None:
        """Find the latest active reconstruction for an entity.

        Args:
            entity_id: The entity UUID.
            workspace_id: The workspace UUID.

        Returns:
            The latest active Reconstruction or None.
        """
        stmt = select(self._model_class).where(
            self._model_class.entity_id == str(entity_id),
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.status == "active",
        ).order_by(self._model_class.created_at.desc())

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_workspace(self, workspace_id: UUID) -> int:
        """Count reconstructions in a workspace.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            Count of reconstructions.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )
        result = await self.session.execute(stmt)
        return len(list(result.scalars().all()))

    def _raise_integrity_error(self, exc: IntegrityError) -> None:
        """Map SQLAlchemy IntegrityError to domain exceptions.

        Args:
            exc: The SQLAlchemy integrity error.
        """
        if "uk_reconstructions_one_active_per_candidate" in str(exc.orig):
            raise DuplicateError(
                entity_type="reconstruction",
                constraint="One active reconstruction per candidate",
                details=f"Active reconstruction already exists for this candidate",
            )
        raise DomainIntegrityError(
            entity_type="reconstruction",
            constraint=str(exc.orig) if hasattr(exc, 'orig') else str(exc),
        )
