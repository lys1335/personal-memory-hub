"""VectorDocRepository — CRUD for the VectorDoc aggregate.

Manages the VectorDoc aggregate root exclusively. VectorDocs are the
independent vector layer storing embeddings for high-value content.

Per 10_9 §4.7 and 09 §09.4.9:
- Aggregate root: VectorDoc
- Tables: vector_documents
- Source types: memory_node, archive, entity_summary
- Memory levels: 1 (Observation), 2 (Pattern), 3 (Belief), 4 (State marker)
- Importance score: 0.0–1.0
- Embedding: VECTOR(1536) stored as text (pgvector extension enabled at DB level)

Relationship:
  Memory 1 → N VectorDoc
  Each VectorDoc belongs to exactly one Memory (via source_id + source_type).

Responsibilities:
- VectorDoc CRUD and lifecycle queries
- Source-type lookups (memory_node, archive, entity_summary)
- Memory-scoped vector document queries
- Entity-scoped vector document queries
- Workspace-scoped queries
- Importance score range queries
- Batch create
- Pagination

Must NOT perform:
- Embedding generation
- Chunking
- Similarity search
- Reranking
- Hybrid retrieval
- Vector ranking
- ANN / IVFFlat / HNSW operations

Those belong to VectorQueryRepository (D2.7).

Inherits from BaseRepository.
Repository persists VectorDoc aggregate only.

Imported by: QueryService, RetrievalEngine.
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


class VectorDocRepository(BaseRepository):  # type: ignore[type-arg]
    """Repository for the VectorDoc aggregate.

    Manages VectorDoc persistence only. VectorDocs are the independent
    vector layer storing embeddings for high-value content.
    """

    _model_class: type[Any]  # VectorDoc (imported lazily)
    _table_name = "vector_documents"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the vector doc repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import VectorDoc

        self._model_class = VectorDoc

    # ------------------------------------------------------------------
    # VectorDoc CRUD
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new vector doc and persist it.

        Args:
            entity: The VectorDoc domain object to create.

        Returns:
            The UUID of the created vector doc.

        Raises:
            DomainIntegrityError: If source_type, memory_level, or
                importance_score is invalid.
            IntegrityError: If a foreign key constraint fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            doc_id = getattr(entity, "id", None)
            if doc_id is None:
                raise DomainIntegrityError(
                    entity_type="vector_doc",
                    constraint="Created vector_doc has no id",
                )
            return UUID(doc_id) if not isinstance(doc_id, UUID) else doc_id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def create_many(self, entities: list[Any]) -> list[UUID]:
        """Create multiple vector docs in a single batch.

        Args:
            entities: List of VectorDoc domain objects to create.

        Returns:
            List of UUIDs of the created vector docs.

        Raises:
            DomainIntegrityError: If any entity is invalid.
            IntegrityError: If a foreign key constraint fails.
        """
        try:
            for entity in entities:
                self.session.add(entity)
            await self.session.flush()
            return [
                getattr(e, "id", None)  # type: ignore[misc]
                for e in entities
            ]
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_id(self, id: UUID) -> Any | None:
        """Find a vector doc by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The VectorDoc if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Soft Delete — VectorDoc is Replace-only (physical delete via impl)
    # ------------------------------------------------------------------

    async def update(self, entity: Any) -> Any:
        """VectorDoc is replace-only: update is prohibited.

        VectorDocs are regenerable computational artifacts (embeddings).
        Updates should be done via delete + recreate (delete old doc, create new).

        Raises:
            DomainIntegrityError: Always, because VectorDocs are replace-only.
        """
        raise DomainIntegrityError(
            entity_type="vector_doc",
            constraint="VectorDocs are replace-only - use delete+recreate",
        )

    async def soft_delete(self, id: UUID) -> None:
        """Contract Mapping: soft_delete() → physical DELETE.

        This method exists to satisfy the BaseRepository[T] interface contract.
        It does NOT perform a logical/soft delete.

        VectorDocs are transient pipeline outputs with no deleted_at column.
        The BaseRepository.soft_delete() contract is fulfilled here by delegating
        to soft_delete_impl(), which performs a PHYSICAL DELETE from the database.

        IMPORTANT FOR MAINTAINERS:
        Do NOT interpret this as a logical/soft-delete operation.
        The row is permanently removed from the database.
        If you need to "disable" a VectorDoc, do not use soft_delete().
        Instead, regenerate the VectorDoc (delete old + create new).
        This is consistent with VectorDoc's Replace-only capability model.

        Args:
            id: The UUID of the VectorDoc to physically delete.
        """
        await self.soft_delete_impl(id)

    async def soft_delete_impl(self, id: UUID) -> None:
        """Physical DELETE for VectorDoc.

        VectorDoc is a regenerable computational artifact (embedding,
        chunk, importance score). It has no soft-delete columns in the
        schema (no deleted_at, no is_deleted). Therefore the
        BaseRepository soft_delete() contract is fulfilled via physical
        DELETE.

        This is intentional and documented: unlike MemoryNode (immutable)
        or Entity (never deleted), VectorDocs are transient pipeline
        outputs that are safely removed rather than soft-deleted.

        This method implements the Contract Mapping:
        BaseRepository.soft_delete() → VectorDoc.physical_delete()

        Args:
            id: The UUID primary key of the VectorDoc to delete.

        Raises:
            DomainIntegrityError: If the entity does not exist.
            IntegrityError: If a foreign key constraint fails.
        """
        entity = await self.find_by_id(id)
        if entity is None:
            raise DomainIntegrityError(
                entity_type="vector_doc",
                constraint=f"No VectorDoc found with id={id}",
            )
        try:
            await self.session.delete(entity)
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    # ------------------------------------------------------------------
    # VectorDoc Queries
    # ------------------------------------------------------------------

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        source_types: list[str] | None = None,
        entity_id: UUID | None = None,
        area_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> list[Any]:
        """Find vector docs by workspace with optional filters.

        Args:
            workspace_id: Workspace scope.
            source_types: Filter by source_type
                (memory_node, archive, entity_summary).
            entity_id: Filter by associated entity.
            area_id: Filter by associated area.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching VectorDoc objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )

        if source_types:
            stmt = stmt.where(
                self._model_class.source_type.in_(source_types)
            )
        if entity_id:
            stmt = stmt.where(
                self._model_class.entity_id == str(entity_id)
            )
        if area_id:
            stmt = stmt.where(
                self._model_class.area_id == str(area_id)
            )

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_source(
        self,
        *,
        source_type: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find vector docs by source type within a workspace.

        Args:
            source_type: Source type (memory_node, archive, entity_summary).
            workspace_id: Workspace scope.

        Returns:
            List of VectorDoc objects of the given source type.

        Raises:
            DomainIntegrityError: If source_type is not valid.
        """
        valid_types = ("memory_node", "archive", "entity_summary")
        if source_type not in valid_types:
            raise DomainIntegrityError(
                entity_type="vector_doc",
                constraint=f"Invalid source_type: {source_type}. "
                f"Must be one of {valid_types}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_type == source_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_memory(
        self,
        *,
        source_id: UUID,
        source_type: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all vector docs for a specific memory/archive entity.

        Args:
            source_id: The source entity UUID (memory_node, archive, etc.).
            source_type: The source type.
            workspace_id: Workspace scope.

        Returns:
            List of VectorDoc objects for the source.

        Raises:
            DomainIntegrityError: If source_type is not valid.
        """
        valid_types = ("memory_node", "archive", "entity_summary")
        if source_type not in valid_types:
            raise DomainIntegrityError(
                entity_type="vector_doc",
                constraint=f"Invalid source_type: {source_type}. "
                f"Must be one of {valid_types}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_id == str(source_id),
            self._model_class.source_type == source_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_entity(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all vector docs associated with a specific entity.

        Args:
            entity_id: The entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of VectorDoc objects for the entity.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.entity_id == str(entity_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_importance_range(
        self,
        *,
        min_importance: float,
        max_importance: float | None = None,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find vector docs within an importance score range.

        Args:
            min_importance: Minimum importance score (0.0-1.0).
            max_importance: Optional maximum importance score.
            workspace_id: Workspace scope.

        Returns:
            List of VectorDoc objects within the range.

        Raises:
            DomainIntegrityError: If scores are out of valid range.
        """
        if not (0.0 <= min_importance <= 1.0):
            raise DomainIntegrityError(
                entity_type="vector_doc",
                constraint="min_importance must be between 0.0 and 1.0",
            )
        if max_importance is not None and not (0.0 <= max_importance <= 1.0):
            raise DomainIntegrityError(
                entity_type="vector_doc",
                constraint="max_importance must be between 0.0 and 1.0",
            )

        conditions = [
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.importance_score >= min_importance,
        ]
        if max_importance is not None:
            conditions.append(
                self._model_class.importance_score <= max_importance
            )

        stmt = select(self._model_class).where(*conditions).order_by(
            self._model_class.importance_score.desc()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_source(
        self,
        *,
        source_id: UUID,
        source_type: str,
        workspace_id: UUID,
    ) -> bool:
        """Check if a vector doc exists for a given source.

        This is a business-key existence check, distinct from the
        BaseRepository.exists(id: UUID) which checks by primary key.

        Args:
            source_id: The source entity UUID.
            source_type: The source type.
            workspace_id: Workspace scope.

        Returns:
            True if at least one matching vector doc exists.
        """
        valid_types = ("memory_node", "archive", "entity_summary")
        if source_type not in valid_types:
            raise DomainIntegrityError(
                entity_type="vector_doc",
                constraint=f"Invalid source_type: {source_type}. "
                f"Must be one of {valid_types}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_id == str(source_id),
            self._model_class.source_type == source_type,
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.first() is not None

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def find_page(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        source_types: list[str] | None = None,
        entity_id: UUID | None = None,
        area_id: UUID | None = None,
        page_number: int = 1,
        page_size: int = 20,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> Page[Any]:
        """Find vector docs with pagination.

        Args:
            workspace_id: Workspace scope.
            source_types: Optional source type filter.
            entity_id: Optional entity filter.
            area_id: Optional area filter.
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
            source_types=source_types,
            entity_id=entity_id,
            area_id=area_id,
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
                entity_type="vector_doc",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="vector_doc",
            constraint=msg[:200],
        )
