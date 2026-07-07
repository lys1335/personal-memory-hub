"""EntityQueryRepository — Read-only complex queries for the Entity domain.

Handles graph queries: entity traversal via relationships, name/alias/type
lookup, filtering, pagination, and relationship queries.

Per 10_9 §4.11 and 09 §09.4.4, §09.4.8:
- Tables (read-only): entities, relationships, areas
- Read-only: no write operations
- Complex multi-table JOIN queries for graph traversal preparation

Responsibilities:
- Name lookup (canonical_name + aliases)
- Alias lookup
- Type lookup and filtering
- Relationship queries (graph read preparation)
- Filtering by workspace, area, entity_type
- Pagination for complex results

Must NOT perform:
- Write operations (enforced by QueryRepository base)
- Graph algorithms (only read preparation)
- Business logic

Inherits from QueryRepository for read-only enforcement.

Imported by: EntityService, QueryService, EntityEngine.
NOT imported by: Engine Layer directly (boundary rule G-013).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.pagination import Page
from backend.repository.query import QueryRepository

if TYPE_CHECKING:
    pass


class EntityQueryRepository(QueryRepository):  # type: ignore[type-arg]
    """Read-only query repository for Entity graph queries.

    Handles complex multi-table JOIN queries for entity
    name/alias/type lookup, relationship queries, and
    graph read preparation.
    """

    _model_class: type[Any]  # Entity (imported lazily)
    _table_name = "entities"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the entity query repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Entity

        self._model_class = Entity

    # ------------------------------------------------------------------
    # Name Lookup
    # ------------------------------------------------------------------

    async def find_by_canonical_name(
        self,
        *,
        canonical_name: str,
        workspace_id: UUID,
        entity_type: str | None = None,
    ) -> list[Any]:
        """Find entities by canonical name.

        Args:
            canonical_name: The canonical name to search for.
            workspace_id: Workspace scope.
            entity_type: Optional entity type filter.

        Returns:
            List of matching Entity objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.canonical_name == canonical_name,
        )
        if entity_type:
            stmt = stmt.where(self._model_class.entity_type == entity_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Alias Lookup
    # ------------------------------------------------------------------

    async def find_by_alias(
        self,
        *,
        alias: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find entities that have a given alias.

        Args:
            alias: The alias string to search for.
            workspace_id: Workspace scope.

        Returns:
            List of matching Entity objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.aliases.contains([alias]),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_partial_alias(
        self,
        *,
        partial: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find entities whose aliases contain a partial match.

        Args:
            partial: Partial alias string (ILIKE match).
            workspace_id: Workspace scope.

        Returns:
            List of matching Entity objects.
        """
        from backend.shared.domain.memory_models import Entity

        stmt = select(Entity).where(
            Entity.workspace_id == str(workspace_id),
            Entity.aliases.any(partial),  # type: ignore[arg-type]  # ARRAY partial match
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Type Lookup
    # ------------------------------------------------------------------

    async def find_by_type(
        self,
        *,
        entity_type: str,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Find all entities of a given type.

        Args:
            entity_type: The entity type to filter by.
            workspace_id: Workspace scope.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of matching Entity objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.entity_type == entity_type,
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_type(
        self,
        *,
        workspace_id: UUID,
    ) -> dict[str, int]:
        """Count entities grouped by type within a workspace.

        Args:
            workspace_id: Workspace scope.

        Returns:
            Dict mapping entity_type to count.
        """
        stmt = select(
            self._model_class.entity_type,
            func.count(self._model_class.id).label("count"),
        ).where(
            self._model_class.workspace_id == str(workspace_id),
        ).group_by(self._model_class.entity_type)

        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    # ------------------------------------------------------------------
    # Relationship Queries
    # ------------------------------------------------------------------

    async def find_related_entities(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
        relationship_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find entities related to a given entity via relationships.

        Returns a list of dicts with entity + relationship info.

        Args:
            entity_id: The source entity UUID.
            workspace_id: Workspace scope.
            relationship_type: Optional type filter.

        Returns:
            List of dicts with 'entity', 'relationship', 'direction' keys.
        """
        from backend.shared.domain.memory_models import (
            Entity,
            EntityRelationship,
        )

        results = []

        # Outgoing relationships (this entity is source)
        stmt_out = (
            select(EntityRelationship, Entity)
            .join(
                Entity,
                EntityRelationship.target_id == Entity.id,
            )
            .where(
                EntityRelationship.workspace_id == str(workspace_id),
                EntityRelationship.source_id == str(entity_id),
            )
        )
        if relationship_type:
            stmt_out = stmt_out.where(
                EntityRelationship.relationship_type == relationship_type
            )
        result_out = await self.session.execute(stmt_out)
        for rel, ent in result_out.all():
            results.append({
                "entity": ent,
                "relationship": rel,
                "direction": "outgoing",
            })

        # Incoming relationships (this entity is target)
        stmt_in = (
            select(EntityRelationship, Entity)
            .join(
                Entity,
                EntityRelationship.source_id == Entity.id,
            )
            .where(
                EntityRelationship.workspace_id == str(workspace_id),
                EntityRelationship.target_id == str(entity_id),
            )
        )
        if relationship_type:
            stmt_in = stmt_in.where(
                EntityRelationship.relationship_type == relationship_type
            )
        result_in = await self.session.execute(stmt_in)
        for rel, ent in result_in.all():
            results.append({
                "entity": ent,
                "relationship": rel,
                "direction": "incoming",
            })

        return results

    async def find_relationships_for_entity(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all relationships involving an entity (as source or target).

        Args:
            entity_id: The entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of EntityRelationship objects.
        """
        from sqlalchemy import union_all

        from backend.shared.domain.memory_models import EntityRelationship

        stmt = union_all(
            select(EntityRelationship).where(
                EntityRelationship.workspace_id == str(workspace_id),
                EntityRelationship.source_id == str(entity_id),
            ),
            select(EntityRelationship).where(
                EntityRelationship.workspace_id == str(workspace_id),
                EntityRelationship.target_id == str(entity_id),
            ),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    async def find_filtered(
        self,
        *,
        workspace_id: UUID,
        entity_types: list[str] | None = None,
        area_id: UUID | None = None,
        has_alias: bool | None = None,
        min_relationship_count: int | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> list[Any]:
        """Find entities with complex filters.

        Args:
            workspace_id: Workspace scope.
            entity_types: Filter by entity types.
            area_id: Filter by area.
            has_alias: Filter entities that have/non-empty aliases.
            min_relationship_count: Filter entities with at least this many
                relationships (uses relationship_count column).
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching Entity objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
        )

        if entity_types:
            stmt = stmt.where(self._model_class.entity_type.in_(entity_types))
        if area_id:
            stmt = stmt.where(self._model_class.area_id == str(area_id))
        if has_alias is True:
            stmt = stmt.where(
                func.array_length(self._model_class.aliases) > 0
            )
        elif has_alias is False:
            stmt = stmt.where(
                func.array_length(self._model_class.aliases) == 0
                | (self._model_class.aliases == [])
            )
        if min_relationship_count is not None:
            stmt = stmt.where(
                self._model_class.relationship_count >= min_relationship_count
            )

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def find_page(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        entity_types: list[str] | None = None,
        area_id: UUID | None = None,
        page_number: int = 1,
        page_size: int = 20,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> Page[Any]:
        """Find entities with pagination.

        Args:
            workspace_id: Workspace scope.
            entity_types: Optional type filter.
            area_id: Optional area filter.
            page_number: 1-based page number.
            page_size: Items per page.
            order_by: Column to order by.
            descending: Descending order.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_filtered(
            workspace_id=workspace_id,
            entity_types=entity_types,
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
    # Graph Read Preparation
    # ------------------------------------------------------------------

    async def get_entity_graph(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Get an entity's neighborhood for graph read preparation.

        Retrieves the entity and its directly connected entities
        via relationships. Does NOT perform multi-hop traversal
        (that is a graph algorithm, not a persistence query).

        Args:
            entity_id: The center entity UUID.
            workspace_id: Workspace scope.
            depth: How many hops to traverse (1 = direct neighbors only).

        Returns:
            Dict with 'center' entity and 'neighbors' list.
        """
        if depth < 1:
            depth = 1

        # Center entity
        center = await self.find_by_id(entity_id)

        # Direct neighbors (depth=1)
        related = await self.find_related_entities(
            entity_id=entity_id,
            workspace_id=workspace_id,
        )

        return {
            "center": center,
            "neighbors": related,
            "depth": depth,
        }

    async def get_entity_count(
        self,
        *,
        workspace_id: UUID,
    ) -> int:
        """Get total entity count for a workspace.

        Args:
            workspace_id: Workspace scope.

        Returns:
            Total count of entities.
        """
        stmt = select(func.count(self._model_class.id)).where(
            self._model_class.workspace_id == str(workspace_id),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
