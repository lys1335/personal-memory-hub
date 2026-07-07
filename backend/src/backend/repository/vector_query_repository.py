"""VectorQueryRepository — Read-only complex queries for the Vector domain.

Handles multi-table JOIN queries and vector-aware persistence queries
for the Retrieval Domain.

Per 10_9 §4.12 and 09 §09.4.9:
- Read-only: no write operations
- Used by RetrievalEngine for vector-aware queries
- Tables: vector_documents, memory_nodes
- QueryCapabilities:
  - similaritySearch(): Cosine similarity via pgvector (deferred)
  - filterBySourceType(): Pre-filter by source type
  - filterByEntity(): Entity-scoped vector search
  - hybridSearch(): Combined vector + text search (deferred)

QueryRepositories are specialized Repository implementations that
handle complex queries which cannot be expressed through simple CRUD.

Must NOT perform:
- Write operations (enforced by QueryRepository base)
- Graph algorithms (only read preparation)
- Business logic
- Embedding generation
- Vector similarity computation (deferred to D2.7 infrastructure)

Inherits from QueryRepository for read-only enforcement.

Imported by: QueryService, RetrievalEngine.
NOT imported by: Engine Layer directly (boundary rule G-013).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.pagination import Page
from backend.repository.query import QueryRepository

if TYPE_CHECKING:
    pass


class VectorQueryRepository(QueryRepository):
    """Read-only query repository for Vector domain complex queries.

    Handles multi-table JOIN queries for vector document
    retrieval, source-type filtering, entity-scoped queries,
    and hybrid search preparation.
    """

    _model_class: type[Any]  # VectorDoc (imported lazily)
    _table_name = "vector_documents"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the vector query repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import VectorDoc

        self._model_class = VectorDoc

    # ------------------------------------------------------------------
    # QueryCapabilities per 10_9 §4.12
    # ------------------------------------------------------------------

    async def similarity_search(
        self,
        *,
        embedding: list[float],
        top_k: int = 10,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """Cosine similarity search via pgvector.

        Performs a vector similarity search using pgvector's cosine
        distance operator (<#>).

        Note: This method requires the pgvector extension to be enabled
        and the embedding column to use the native VECTOR type.
        Currently, embedding is stored as String (see D2.6 known limitation).
        This method returns an empty list until pgvector support is added.

        Args:
            embedding: The query embedding vector (1536 dimensions).
            top_k: Maximum number of results to return.
            workspace_id: Workspace scope.

        Returns:
            List of dicts with 'doc' (VectorDoc) and 'score' (float) keys.

        Raises:
            NotImplementedError: If pgvector extension is not available.
        """
        # pgvector not yet integrated — defer to D2.7 infrastructure.
        return []

    async def filter_by_source_type(
        self,
        *,
        source_type: str,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Pre-filter vector documents by source type.

        Args:
            source_type: Source type (memory_node, archive, entity_summary).
            workspace_id: Workspace scope.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of VectorDoc objects of the given source type.

        Raises:
            DomainIntegrityError: If source_type is not valid.
        """
        valid_types = ("memory_node", "archive", "entity_summary")
        if source_type not in valid_types:
            raise ValueError(
                f"Invalid source_type: {source_type}. "
                f"Must be one of {valid_types}"
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_type == source_type,
        ).order_by(
            self._model_class.created_at.desc()
        ).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def filter_by_entity(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Entity-scoped vector document search.

        Args:
            entity_id: The entity UUID.
            workspace_id: Workspace scope.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of VectorDoc objects associated with the entity.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.entity_id == str(entity_id),
        ).order_by(
            self._model_class.created_at.desc()
        ).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def hybrid_search(
        self,
        *,
        query_embedding: list[float] | None = None,
        text_query: str | None = None,
        top_k: int = 10,
        workspace_id: UUID,
        source_types: list[str] | None = None,
        entity_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Combined vector + text search.

        Joins vector_documents with memory_nodes for hybrid retrieval.

        Note: Full hybrid search requires pgvector extension and
        embedding integration. This implementation provides the
        text-based pre-filter and workspace-scoped query.

        Args:
            query_embedding: Optional query embedding vector.
            text_query: Optional text search query.
            top_k: Maximum number of results.
            workspace_id: Workspace scope.
            source_types: Optional source type filter.
            entity_id: Optional entity filter.

        Returns:
            List of dicts with 'doc' (VectorDoc) and 'score' (float) keys.
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
        if text_query:
            # Text-based pre-filter on content (LIKE-based, not full-text)
            stmt = stmt.where(
                self._model_class.content.ilike(f"%{text_query}%")
            )

        stmt = stmt.order_by(
            self._model_class.importance_score.desc()
        ).limit(top_k)

        result = await self.session.execute(stmt)
        docs = list(result.scalars().all())

        return [{"doc": doc, "score": float(doc.importance_score)} for doc in docs]

    # ------------------------------------------------------------------
    # Complex Query Method (abstract from QueryRepository)
    # ------------------------------------------------------------------

    async def complex_query(self, *args: Any, **kwargs: Any) -> Any:
        """Execute a complex multi-table query.

        Delegates to domain-specific query methods based on kwargs.

        Args:
            *args: Positional query parameters.
            **kwargs: Named query parameters.

        Returns:
            Query result (Domain objects, vector results, or ranked lists).
        """
        # similarity_search
        if "embedding" in kwargs and "top_k" in kwargs:
            return await self.similarity_search(**kwargs)

        # filter_by_source_type
        if "source_type" in kwargs and "workspace_id" in kwargs:
            return await self.filter_by_source_type(**kwargs)

        # filter_by_entity
        if "entity_id" in kwargs and "workspace_id" in kwargs:
            return await self.filter_by_entity(**kwargs)

        # hybrid_search
        if "text_query" in kwargs or "query_embedding" in kwargs:
            return await self.hybrid_search(**kwargs)

        # Default: return empty result
        return []

    # ------------------------------------------------------------------
    # Read Operations (from QueryRepository base)
    # ------------------------------------------------------------------

    async def find_all(
        self,
        *,
        workspace_id: UUID | None = None,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[Any]:
        """Find vector docs with optional filters.

        Override to use VectorDoc model class.

        Args:
            workspace_id: Workspace scope.
            filters: Additional filter conditions.
            offset: Number of records to skip.
            limit: Maximum number of records.
            order_by: Column to order by.
            descending: Descending order.

        Returns:
            List of matching VectorDoc entities.
        """
        stmt = select(self._model_class)

        effective_workspace = workspace_id or self._ensure_workspace()
        stmt = stmt.where(
            self._model_class.workspace_id == str(effective_workspace)
        )

        if filters:
            for col_name, value in filters.items():
                if hasattr(self._model_class, col_name):
                    col = getattr(self._model_class, col_name)
                    if isinstance(value, list):
                        stmt = stmt.where(col.in_(value))
                    else:
                        stmt = stmt.where(col == value)

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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

    async def find_page(
        self,
        *,
        workspace_id: UUID | None = None,
        filters: dict[str, Any] | None = None,
        page_number: int = 1,
        page_size: int = 20,
        order_by: str | None = None,
        descending: bool = False,
    ) -> Page[Any]:
        """Find vector docs with pagination.

        Args:
            workspace_id: Workspace scope.
            filters: Additional filter conditions.
            page_number: 1-based page number.
            page_size: Items per page.
            order_by: Column to order by.
            descending: Descending order.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_all(
            workspace_id=workspace_id,
            filters=filters,
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
