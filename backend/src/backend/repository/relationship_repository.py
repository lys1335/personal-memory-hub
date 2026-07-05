"""RelationshipRepository — CRUD for the Relationship aggregate.

Manages two distinct relationship aggregates under one Repository:
- EntityRelationship (relationships) — Entity-to-entity relationships
- MemoryRelationship (memory_relationships) — MemoryNode-to-MemoryNode

Per 10_9 §4.4 and 09 §09.4.8, §09.4.14:
- Entity Relationship Types: belongs_to, part_of, uses, depends_on,
  related_to, affects, derived_from, owns, created_by, about
- Memory Relationship Types: supports, derived_from, contradicts, attenuates
- Key Constraints:
  - chk_no_self_relationship: source_id != target_id
  - uk_relationship_direction: UNIQUE (source_id, target_id, relationship_type)
  - strength: 0.0–1.0
- Multiple relationships per entity pair ARE allowed (different types).
  No uniqueness constraint on (source_id, target_id) alone.

Responsibilities:
- EntityRelationship CRUD
- MemoryRelationship CRUD
- Basic relationship lookup by source/target/type

Must NOT perform:
- Relationship inference
- Graph algorithms
- Multi-hop traversal
- Business logic

Imported by: EntityService, MemoryService, RelationshipEngine.
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
    IntegrityError as DomainIntegrityError,
    NotFoundError,
)
from backend.repository.pagination import Page


class RelationshipRepository(BaseRepository):
    """Repository for the Relationship aggregate.

    Manages both EntityRelationship and MemoryRelationship.
    """

    _model_class: type[Any]  # EntityRelationship (imported lazily)
    _table_name = "relationships"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the relationship repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import (  # noqa: PLC0415
            EntityRelationship,
        )

        self._model_class = EntityRelationship

    # ------------------------------------------------------------------
    # EntityRelationship CRUD
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new entity relationship and persist it.

        Args:
            entity: The EntityRelationship domain object.

        Returns:
            The UUID of the created relationship.

        Raises:
            DuplicateError: If (source_id, target_id, relationship_type)
                already exists.
            DomainIntegrityError: If relationship_type is invalid
                or source == target.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            rel_id = getattr(entity, "id", None)
            if rel_id is None:
                raise DomainIntegrityError(
                    entity_type="relationship",
                    constraint="Created relationship has no id",
                )
            return UUID(rel_id) if not isinstance(rel_id, UUID) else rel_id
        except IntegrityError as exc:
            self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_id(self, id: UUID) -> Any | None:
        """Find an entity relationship by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The EntityRelationship if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_source(
        self,
        *,
        source_id: UUID,
        workspace_id: UUID,
        relationship_type: str | None = None,
    ) -> list[Any]:
        """Find relationships where this entity is the source.

        Args:
            source_id: The source entity UUID.
            workspace_id: Workspace scope.
            relationship_type: Optional type filter.

        Returns:
            List of matching EntityRelationship objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_id == str(source_id),
        )
        if relationship_type:
            stmt = stmt.where(
                self._model_class.relationship_type == relationship_type
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_target(
        self,
        *,
        target_id: UUID,
        workspace_id: UUID,
        relationship_type: str | None = None,
    ) -> list[Any]:
        """Find relationships where this entity is the target.

        Args:
            target_id: The target entity UUID.
            workspace_id: Workspace scope.
            relationship_type: Optional type filter.

        Returns:
            List of matching EntityRelationship objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.target_id == str(target_id),
        )
        if relationship_type:
            stmt = stmt.where(
                self._model_class.relationship_type == relationship_type
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_type(
        self,
        *,
        relationship_type: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all relationships of a given type.

        Args:
            relationship_type: The relationship type to filter by.
            workspace_id: Workspace scope.

        Returns:
            List of matching EntityRelationship objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.relationship_type == relationship_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_connections(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all relationships connecting to/from an entity.

        Both source and target directions.

        Args:
            entity_id: The entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of matching EntityRelationship objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_id == str(entity_id),
        ) | select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.target_id == str(entity_id),
        )
        # Use union for proper SQL
        from sqlalchemy import union_all  # noqa: PLC0415

        stmt = union_all(
            select(self._model_class).where(
                self._model_class.workspace_id == str(workspace_id),
                self._model_class.source_id == str(entity_id),
            ),
            select(self._model_class).where(
                self._model_class.workspace_id == str(workspace_id),
                self._model_class.target_id == str(entity_id),
            ),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_pair(
        self,
        *,
        source_id: UUID,
        target_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all relationships between two entities (any type).

        Supports multiple relationship types between the same pair.

        Args:
            source_id: Source entity UUID.
            target_id: Target entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of matching EntityRelationship objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_id == str(source_id),
            self._model_class.target_id == str(target_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # MemoryRelationship CRUD
    # ------------------------------------------------------------------

    async def create_memory_relationship(
        self,
        relationship: Any,
    ) -> UUID:
        """Create a new memory relationship and persist it.

        Args:
            relationship: The MemoryRelationship domain object.

        Returns:
            The UUID of the created relationship.
        """
        from backend.shared.domain.memory_models import MemoryRelationship  # noqa: PLC0415

        self.session.add(relationship)
        await self.session.flush()
        rel_id = getattr(relationship, "id", None)
        return UUID(rel_id) if not isinstance(rel_id, UUID) else rel_id

    async def find_memory_relationships_by_source(
        self,
        *,
        source_node_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find memory relationships where this node is the source.

        Args:
            source_node_id: The source memory node UUID.
            workspace_id: Workspace scope.

        Returns:
            List of matching MemoryRelationship objects.
        """
        from backend.shared.domain.memory_models import MemoryRelationship  # noqa: PLC0415

        stmt = select(MemoryRelationship).where(
            MemoryRelationship.workspace_id == str(workspace_id),
            MemoryRelationship.source_node_id == str(source_node_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_memory_relationships_by_target(
        self,
        *,
        target_node_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find memory relationships where this node is the target.

        Args:
            target_node_id: The target memory node UUID.
            workspace_id: Workspace scope.

        Returns:
            List of matching MemoryRelationship objects.
        """
        from backend.shared.domain.memory_models import MemoryRelationship  # noqa: PLC0415

        stmt = select(MemoryRelationship).where(
            MemoryRelationship.workspace_id == str(workspace_id),
            MemoryRelationship.target_node_id == str(target_node_id),
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
        relationship_type: str | None = None,
        page_number: int = 1,
        page_size: int = 20,
    ) -> Page[Any]:
        """Find entity relationships with pagination.

        Args:
            workspace_id: Workspace scope.
            relationship_type: Optional type filter.
            page_number: 1-based page number.
            page_size: Items per page.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_by_workspace_filtered(
            workspace_id=workspace_id,
            relationship_type=relationship_type,
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

    async def find_by_workspace_filtered(
        self,
        *,
        workspace_id: UUID,
        relationship_type: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Find relationships by workspace with optional type filter.

        Args:
            workspace_id: Workspace scope.
            relationship_type: Optional type filter.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of matching EntityRelationship objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
        )
        if relationship_type:
            stmt = stmt.where(
                self._model_class.relationship_type == relationship_type
            )
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Soft Delete — Relationships are never deleted
    # ------------------------------------------------------------------

    async def soft_delete_impl(self, id: UUID) -> None:
        """Relationships are never soft-deleted.

        This method raises an error to enforce relationship immutability.
        """
        raise DomainIntegrityError(
            entity_type="relationship",
            constraint="Relationships are never deleted",
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
                entity_type="relationship",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="relationship",
            constraint=msg[:200],
        )
