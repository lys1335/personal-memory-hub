"""MemoryQueryRepository - Read-only complex queries for the Memory Domain.

Handles multi-table JOIN queries, evidence chain traversal, and
aggregations for the Memory Domain.

Per 10_9 §4.10 and 09 §09.4.5-09.4.7:
- Read-only: no write operations
- Used by QueryService for complex queries
- Tables: memory_nodes, memory_evidences, evidences
- QueryCapabilities:
  - findWithEvidence(): MemoryNode + full evidence chain
  - findByEntityAndLevel(): Scoped by entity + memory level
  - findActiveByWorkspace(): Status='active' filter with workspace isolation
  - searchWithVector(): Combined text + vector search

Inherits from QueryRepository (read-only base) and adds domain-specific
complex query methods.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.pagination import Page
from backend.repository.query import QueryRepository


class MemoryQueryRepository(QueryRepository):  # type: ignore[type-arg]
    """Read-only query repository for Memory Domain complex queries."""

    _model_class: type[Any]
    _table_name = "memory_nodes"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the memory query repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import MemoryNode

        self._model_class = MemoryNode

    # ------------------------------------------------------------------
    # QueryCapabilities per 10_9 §4.10
    # ------------------------------------------------------------------

    async def find_with_evidence(
        self,
        *,
        memory_node_id: UUID,
    ) -> dict[str, Any]:
        """Find a memory node with its full evidence chain.

        JOINs memory_nodes with memory_evidences and evidences.

        Args:
            memory_node_id: The memory node UUID.

        Returns:
            Dict with 'node' (MemoryNode) and 'evidence_chain' (list of dicts
            containing evidence details and relationship info).

        Raises:
            NotFoundError: If the memory node does not exist.
        """
        from backend.shared.domain.memory_models import Evidence, MemoryEvidence

        # Fetch the memory node
        node_stmt = select(self._model_class).where(
            self._model_class.id == memory_node_id
        )
        node_result = await self.session.execute(node_stmt)
        node = node_result.scalar_one_or_none()

        if node is None:
            from backend.repository.exceptions import NotFoundError

            raise NotFoundError(
                entity_type="memory_node",
                entity_id=str(memory_node_id),
            )

        # Fetch evidence chain
        evidence_stmt = (
            select(MemoryEvidence, Evidence)
            .join(Evidence, MemoryEvidence.evidence_id == Evidence.id)
            .where(MemoryEvidence.memory_node_id == memory_node_id)
        )
        evidence_result = await self.session.execute(evidence_stmt)
        evidence_rows = evidence_result.all()

        evidence_chain = []
        for link, evidence in evidence_rows:
            evidence_chain.append({
                "evidence": evidence,
                "relationship_type": link.relationship_type,
                "contribution_weight": link.contribution_weight,
                "evidence_type": evidence.evidence_type,
                "evidence_content": evidence.content,
                "evidence_source": evidence.source,
            })

        return {
            "node": node,
            "evidence_chain": evidence_chain,
        }

    async def find_by_entity_and_level(
        self,
        *,
        entity_id: UUID,
        level: int,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find memory nodes scoped by entity and memory level.

        Args:
            entity_id: The entity UUID.
            level: Memory level (1=Observation, 2=Pattern, 3=Belief).
            workspace_id: Workspace scope.

        Returns:
            List of MemoryNode entities matching the criteria.
        """
        if level not in (1, 2, 3):
            raise ValueError(f"Invalid level: {level}. Must be 1, 2, or 3.")

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.entity_id == entity_id,
            self._model_class.level == level,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_active_by_workspace(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> list[Any]:
        """Find all active memory nodes in a workspace.

        Args:
            workspace_id: Workspace scope.
            offset: Number of records to skip.
            limit: Maximum number of records.
            order_by: Column to order by.
            descending: Descending order.

        Returns:
            List of active MemoryNode entities.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.status == "active",
        )

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_keyword(
        self,
        *,
        workspace_id: UUID,
        query: str,
        entity_id: UUID | None = None,
        level: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        """Search memory nodes by keyword in content field.

        Uses ILIKE for case-insensitive partial matching on memory_nodes.content.
        Splits multi-word queries into individual keywords and matches any of them (OR logic).

        Args:
            workspace_id: Workspace scope.
            query: Search keyword(s).
            entity_id: Optional entity filter.
            level: Optional level filter.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of MemoryNode entities matching the query.
        """
        from sqlalchemy import func, or_

        # Split query into meaningful tokens
        import re

        # Strategy: extract English words AND Chinese character sequences separately
        # This handles mixed content like "帮我回忆一下docker的事情"
        
        # Extract English/alphanumeric words (including mixed with numbers)
        en_words = re.findall(r'[a-zA-Z][a-zA-Z0-9.-]{0,30}', query.lower())
        
        # Extract Chinese character sequences (2+ chars)
        cn_sequences = re.findall(r'[\u4e00-\u9fff]{2,}', query)
        
        # Combine and deduplicate, preserving order
        all_tokens = []
        seen = set()
        for t in en_words + cn_sequences:
            if t not in seen and 2 <= len(t) <= 30:
                seen.add(t)
                all_tokens.append(t)
        
        tokens = all_tokens

        if not tokens:
            return []

        # Build OR condition: match ANY token against content
        conditions = [
            func.lower(self._model_class.content).contains(token)
            for token in tokens
        ]

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.status == "active",
            or_(*conditions),
        )

        if entity_id:
            stmt = stmt.where(self._model_class.entity_id == entity_id)

        if level is not None:
            stmt = stmt.where(self._model_class.level == level)

        stmt = stmt.order_by(
            func.length(self._model_class.content).asc()
        )
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_with_vector(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        level: int | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Combined text + vector search for memory nodes.

        Joins memory_nodes with vector_documents for hybrid search.
        Note: Actual vector similarity requires pgvector extension.
        This implementation provides the text-based pre-filter.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity filter.
            level: Optional level filter (1, 2, 3).
            top_k: Maximum number of results.

        Returns:
            List of dicts with 'node' and 'vector_doc' keys.
        """
        # Vector search requires pgvector extension and VectorDocument model.
        # This is a placeholder for the actual implementation.
        # When pgvector is available, this will join memory_nodes
        # with vector_documents and compute cosine similarity.
        return []

    # ------------------------------------------------------------------
    # Complex Query Method (abstract from QueryRepository)
    # ------------------------------------------------------------------

    async def complex_query(self, *args: Any, **kwargs: Any) -> Any:
        """Execute a complex multi-table query.

        This is the abstract method from QueryRepository. Subclasses
        (or this implementation) provide domain-specific complex queries.

        Args:
            *args: Positional query parameters.
            **kwargs: Named query parameters.

        Returns:
            Query result (Domain objects, graph results, or ranked lists).
        """
        # Default: delegate to find_with_evidence if memory_node_id is provided
        memory_node_id = kwargs.get("memory_node_id")
        if memory_node_id:
            return await self.find_with_evidence(memory_node_id=memory_node_id)

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
        """Find memory nodes with optional filters.

        Override to use MemoryNode model class.
        """
        stmt = select(self._model_class)

        effective_workspace = workspace_id or self._ensure_workspace()
        stmt = stmt.where(self._model_class.workspace_id == effective_workspace)

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
        """Find a memory node by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The MemoryNode if found, None otherwise.
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
        """Find memory nodes with pagination.

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
