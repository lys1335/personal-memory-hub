"""QueryService — Read Application Service.

Implements all read capabilities:
- Retrieval: Get memories/entities by ID, entity, or relationship
- Search: Keyword, similarity, and combined search
- Browse: Time-range, category, and tag browsing
- Projection: Summary, detail, graph, and timeline projections
- Analytics: Statistics and insights

Per D3.3 and 10_3 Implementation Design:
- QueryService is the ONLY business read entry
- Side-effect free: never modifies domain state
- Query purity: no business side effects
- Observational consistency: reflects persisted state at query time
- Query idempotence: same query + same state = same result
- Projection belongs to QueryService (not Engine, not Entry layer)
- Domain algorithms belong to D4 Engine
- Unified Read Workflow: Validation → Planning → Repository Coordination → Domain Processing → Projection → Result Assembly
- Repository Coordination: QueryService is the only repository coordinator
- Transaction: Read-only transaction

Architecture:
    QueryService (D3) → MemoryQueryRepository, EntityQueryRepository, VectorQueryRepository (D2)
    QueryService (D3) → MemoryNodeRepository, EntityRepository (D2)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.service.base import BaseService
from backend.service.dto import (
    AnalyticsInsight,
    AnalyticsStatistics,
    QueryResult,
)
from backend.service.exceptions import (
    NotFoundError,
    ValidationError,
)

if TYPE_CHECKING:
    from backend.repository.entity_query_repository import EntityQueryRepository
    from backend.repository.entity_repository import EntityRepository
    from backend.repository.memory_node_repository import MemoryNodeRepository
    from backend.repository.memory_query_repository import MemoryQueryRepository
    from backend.repository.vector_doc_repository import VectorDocRepository
    from backend.repository.vector_query_repository import VectorQueryRepository

logger = logging.getLogger(__name__)


class QueryService(BaseService):
    """Application service for all read operations.

    Coordinates Repository reads for retrieval, search, browse,
    projection, and analytics.

    Stateless singleton managed by DI container.
    """

    def __init__(
        self,
        memory_node_repo: MemoryNodeRepository,
        memory_query_repo: MemoryQueryRepository,
        entity_repo: EntityRepository,
        entity_query_repo: EntityQueryRepository,
        vector_query_repo: VectorQueryRepository,
        vector_doc_repo: VectorDocRepository,
    ) -> None:
        """Initialize QueryService with required repositories.

        Args:
            memory_node_repo: Repository for MemoryNode reads.
            memory_query_repo: Repository for complex memory queries.
            entity_repo: Repository for Entity reads.
            entity_query_repo: Repository for complex entity queries.
            vector_query_repo: Repository for vector similarity search.
            vector_doc_repo: Repository for vector document reads.
        """
        super().__init__("QueryService")
        self._memory_node_repo = memory_node_repo
        self._memory_query_repo = memory_query_repo
        self._entity_repo = entity_repo
        self._entity_query_repo = entity_query_repo
        self._vector_query_repo = vector_query_repo
        self._vector_doc_repo = vector_doc_repo

    # ------------------------------------------------------------------
    # Retrieval Capability
    # ------------------------------------------------------------------

    async def retrieve_by_id(
        self,
        *,
        workspace_id: UUID,
        memory_id: UUID,
    ) -> QueryResult[Any]:
        """Retrieve a memory node by its ID.

        Args:
            workspace_id: Workspace scope.
            memory_id: The memory node UUID.

        Returns:
            QueryResult with the memory node.

        Raises:
            NotFoundError: If memory not found.
        """
        self._validate_workspace_id(workspace_id)

        memory = await self._memory_node_repo.find_by_id(memory_id)
        if memory is None:
            raise NotFoundError(
                f"Memory {memory_id} not found",
                resource_type="memory_node",
                resource_id=str(memory_id),
            )

        return QueryResult(items=[memory])

    async def retrieve_by_entity(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
        level: int | None = None,
        limit: int = 100,
    ) -> QueryResult[Any]:
        """Retrieve all memories for a specific entity.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.
            level: Optional level filter (1=Observation, 2=Pattern, 3=Belief).
            limit: Maximum number of results.

        Returns:
            QueryResult with matching memory nodes.
        """
        self._validate_workspace_id(workspace_id)

        memories = await self._memory_node_repo.find_by_entity(
            entity_id=entity_id,
            workspace_id=workspace_id,
        )

        if level is not None:
            memories = [m for m in memories if getattr(m, "level", None) == level]

        return QueryResult(items=memories[:limit])

    async def retrieve_by_relationship(
        self,
        *,
        workspace_id: UUID,
        source_id: UUID,
        relationship_type: str | None = None,
    ) -> QueryResult[Any]:
        """Retrieve memories connected via relationships.

        Args:
            workspace_id: Workspace scope.
            source_id: Source entity or memory ID.
            relationship_type: Optional relationship type filter.

        Returns:
            QueryResult with related memories.
        """
        self._validate_workspace_id(workspace_id)

        results = await self._memory_query_repo.find_related_memories(  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            workspace_id=workspace_id,
            source_id=source_id,
            relationship_type=relationship_type,
        )

        return QueryResult(items=results)

    # ------------------------------------------------------------------
    # Search Capability
    # ------------------------------------------------------------------

    async def search_by_keyword(
        self,
        *,
        workspace_id: UUID,
        query: str,
        entity_id: UUID | None = None,
        level: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> QueryResult[Any]:
        """Search memories by keyword content.

        Args:
            workspace_id: Workspace scope.
            query: Search keyword.
            entity_id: Optional entity filter.
            level: Optional level filter.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            QueryResult with matching memories.
        """
        self._validate_workspace_id(workspace_id)

        if not query or not query.strip():
            raise ValidationError(
                "Search query cannot be empty",
                field="query",
            )

        results = await self._memory_query_repo.search_by_keyword(
            workspace_id=workspace_id,
            query=query.strip(),
            entity_id=entity_id,
            level=level,
            limit=limit,
            offset=offset,
        )

        return QueryResult(
            items=results,
            page_number=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit,
        )

    async def search_by_similarity(
        self,
        *,
        workspace_id: UUID,
        content: str,
        entity_id: UUID | None = None,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> QueryResult[Any]:
        """Search memories by semantic similarity.

        Uses vector embeddings for similarity search.

        Args:
            workspace_id: Workspace scope.
            content: Search content for embedding comparison.
            entity_id: Optional entity filter.
            limit: Maximum results.
            min_score: Minimum similarity score threshold.

        Returns:
            QueryResult with similar memories ranked by score.
        """
        self._validate_workspace_id(workspace_id)

        if not content or not content.strip():
            raise ValidationError(
                "Similarity search content cannot be empty",
                field="content",
            )

        results = await self._vector_query_repo.similarity_search(  # type: ignore[call-arg]
            workspace_id=workspace_id,
            content=content.strip(),
            entity_id=entity_id,
            limit=limit,
            min_score=min_score,
        )

        return QueryResult(items=results)

    async def search_combined(
        self,
        *,
        workspace_id: UUID,
        query: str,
        entity_id: UUID | None = None,
        limit: int = 50,
        boost_keywords: bool = True,
    ) -> QueryResult[Any]:
        """Combined search: keyword + similarity.

        Merges keyword search results with vector similarity results.

        Args:
            workspace_id: Workspace scope.
            query: Search query.
            entity_id: Optional entity filter.
            limit: Maximum results.
            boost_keywords: Whether to boost keyword matches.

        Returns:
            QueryResult with combined search results.
        """
        self._validate_workspace_id(workspace_id)

        if not query or not query.strip():
            raise ValidationError(
                "Search query cannot be empty",
                field="query",
            )

        results = await self._vector_query_repo.hybrid_search(  # type: ignore[call-arg]
            workspace_id=workspace_id,
            query=query.strip(),
            entity_id=entity_id,
            limit=limit,
            boost_keywords=boost_keywords,
        )

        return QueryResult(items=results)

    # ------------------------------------------------------------------
    # Browse Capability
    # ------------------------------------------------------------------

    async def browse_by_time_range(
        self,
        *,
        workspace_id: UUID,
        start_date: str,
        end_date: str,
        entity_id: UUID | None = None,
        limit: int = 100,
        descending: bool = True,
    ) -> QueryResult[Any]:
        """Browse memories within a time range.

        Args:
            workspace_id: Workspace scope.
            start_date: Start date (ISO 8601).
            end_date: End date (ISO 8601).
            entity_id: Optional entity filter.
            limit: Maximum results.
            descending: Order by created_at descending.

        Returns:
            QueryResult with memories in the time range.
        """
        self._validate_workspace_id(workspace_id)

        results = await self._memory_query_repo.browse_by_time_range(  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            entity_id=entity_id,
            limit=limit,
            descending=descending,
        )

        return QueryResult(items=results)

    async def browse_by_category(
        self,
        *,
        workspace_id: UUID,
        category: str,
        entity_id: UUID | None = None,
        limit: int = 100,
    ) -> QueryResult[Any]:
        """Browse memories by category (node_type or observation_type).

        Args:
            workspace_id: Workspace scope.
            category: Category name (e.g., "Observation", "Pattern", "decision", "preference").
            entity_id: Optional entity filter.
            limit: Maximum results.

        Returns:
            QueryResult with categorized memories.
        """
        self._validate_workspace_id(workspace_id)

        results = await self._memory_query_repo.browse_by_category(  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            workspace_id=workspace_id,
            category=category,
            entity_id=entity_id,
            limit=limit,
        )

        return QueryResult(items=results)

    async def browse_by_tag(
        self,
        *,
        workspace_id: UUID,
        tag_name: str,
        target_type: str = "memory_node",
        limit: int = 100,
    ) -> QueryResult[Any]:
        """Browse memories by tag.

        Args:
            workspace_id: Workspace scope.
            tag_name: Tag name to filter by.
            target_type: Target type ("memory_node", "entity", "archive").
            limit: Maximum results.

        Returns:
            QueryResult with tagged memories.
        """
        self._validate_workspace_id(workspace_id)

        results = await self._memory_query_repo.browse_by_tag(  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            workspace_id=workspace_id,
            tag_name=tag_name,
            target_type=target_type,
            limit=limit,
        )

        return QueryResult(items=results)

    # ------------------------------------------------------------------
    # Projection Capability
    # ------------------------------------------------------------------

    async def project_to_summary(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        level: int | None = None,
        max_items: int = 10,
    ) -> QueryResult[dict[str, Any]]:
        """Project memories into a summary view.

        Returns a condensed summary with counts and recent items.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity filter.
            level: Optional level filter.
            max_items: Maximum items per category in summary.

        Returns:
            QueryResult with summary dict containing counts and recent items.
        """
        self._validate_workspace_id(workspace_id)

        # Gather counts by level
        observations = await self._memory_node_repo.find_by_level(
            level=1,
            workspace_id=workspace_id,
        )
        patterns = await self._memory_node_repo.find_by_level(
            level=2,
            workspace_id=workspace_id,
        )
        beliefs = await self._memory_node_repo.find_by_level(
            level=3,
            workspace_id=workspace_id,
        )

        if entity_id:
            observations = [o for o in observations if getattr(o, "entity_id", None) == entity_id]
            patterns = [p for p in patterns if getattr(p, "entity_id", None) == entity_id]
            beliefs = [b for b in beliefs if getattr(b, "entity_id", None) == entity_id]

        summary = {
            "total_observations": len(observations),
            "total_patterns": len(patterns),
            "total_beliefs": len(beliefs),
            "recent_observations": observations[:max_items],
            "recent_patterns": patterns[:max_items],
            "recent_beliefs": beliefs[:max_items],
        }

        return QueryResult(items=[summary])

    async def project_to_detail(
        self,
        *,
        workspace_id: UUID,
        memory_id: UUID,
    ) -> QueryResult[Any]:
        """Project a single memory into a detailed view with evidence chain.

        Args:
            workspace_id: Workspace scope.
            memory_id: The memory node UUID.

        Returns:
            QueryResult with the memory and its full evidence chain.

        Raises:
            NotFoundError: If memory not found.
        """
        self._validate_workspace_id(workspace_id)

        result = await self._memory_node_repo.find_with_evidence_chain(
            memory_node_id=memory_id,
        )

        return QueryResult(items=[result])

    async def project_to_graph(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
        depth: int = 2,
    ) -> QueryResult[dict[str, Any]]:
        """Project entity relationships into a graph view.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.
            depth: Graph traversal depth.

        Returns:
            QueryResult with graph data (nodes and edges).
        """
        self._validate_workspace_id(workspace_id)

        graph_data = await self._entity_query_repo.get_entity_graph(
            workspace_id=workspace_id,
            entity_id=entity_id,
            depth=depth,
        )

        return QueryResult(items=[graph_data])

    async def project_to_timeline(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
    ) -> QueryResult[Any]:
        """Project memories into a chronological timeline view.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            limit: Maximum items.

        Returns:
            QueryResult with timeline items ordered by created_at.
        """
        self._validate_workspace_id(workspace_id)

        results = await self._memory_query_repo.project_to_timeline(  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            workspace_id=workspace_id,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return QueryResult(items=results)

    # ------------------------------------------------------------------
    # Analytics Capability
    # ------------------------------------------------------------------

    async def analyze_statistics(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
    ) -> QueryResult[AnalyticsStatistics]:
        """Analyze aggregate statistics for a workspace or entity.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity filter.

        Returns:
            QueryResult with AnalyticsStatistics.
        """
        self._validate_workspace_id(workspace_id)

        all_memories = await self._memory_node_repo.find_active_by_workspace(
            workspace_id=workspace_id,
        )

        if entity_id:
            all_memories = [
                m for m in all_memories
                if getattr(m, "entity_id", None) == entity_id
            ]

        observations = sum(1 for m in all_memories if getattr(m, "level", None) == 1)
        patterns = sum(1 for m in all_memories if getattr(m, "level", None) == 2)
        beliefs = sum(1 for m in all_memories if getattr(m, "level", None) == 3)

        stats = AnalyticsStatistics(
            total_memory_nodes=len(all_memories),
            observations=observations,
            patterns=patterns,
            beliefs=beliefs,
        )

        return QueryResult(items=[stats])

    async def analyze_insights(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
    ) -> QueryResult[AnalyticsInsight]:
        """Generate insights from analytics data.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity filter.

        Returns:
            QueryResult with insight objects.
        """
        self._validate_workspace_id(workspace_id)

        stats_result = await self.analyze_statistics(
            workspace_id=workspace_id,
            entity_id=entity_id,
        )

        insights: list[AnalyticsInsight] = []

        if stats_result.items:
            stats = stats_result.items[0]

            # Growth insight: ratio of patterns to observations
            if stats.observations > 0:
                pattern_ratio = stats.patterns / stats.observations
                if pattern_ratio > 0.3:
                    insights.append(AnalyticsInsight(
                        category="density",
                        title="High pattern density",
                        description=f"Pattern-to-observation ratio is {pattern_ratio:.1%}",
                        value=pattern_ratio,
                        unit="ratio",
                    ))

            # Activity insight: belief formation
            if stats.patterns > 0:
                insights.append(AnalyticsInsight(
                    category="growth",
                    title="Active belief formation",
                    description=f"{stats.beliefs} beliefs formed from {stats.patterns} patterns",
                    value=float(stats.beliefs),
                    unit="beliefs",
                ))

        return QueryResult(items=insights)
