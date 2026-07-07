"""EntityRepository — CRUD for the Entity aggregate.

Manages the Entity aggregate root including its scoped resources:
- Entity (entities)
- Area (areas)
- Workspace (workspace)
- UserProfile (user_profiles)

Per 10_9 §4.1 and 09 §09.4.1–09.4.4:
- Aggregate root: Entity
- Tables: entities, areas, workspace, user_profiles
- Unique constraint: (workspace_id, entity_type, canonical_name)
- Entity types: Project, Person, Organization, Tool, Technology,
  Concept, Event, Location, Object, Agent, Model, Document
- Hierarchical: parent_entity_id self-reference

Responsibilities:
- Entity CRUD and lifecycle queries
- Exists / Get-by-ID operations
- Area management (hierarchical via parent_area_id)
- Workspace singleton management
- UserProfile management

Must NOT perform:
- Entity Resolution
- Entity Merge
- Alias Resolution
- Graph Traversal
- Business Logic

Inherits from BaseRepository for Entity operations.
Area, Workspace, and UserProfile are managed as part of the same aggregate.

Imported by: EntityService, IngestionService, MemoryService.
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


class EntityRepository(BaseRepository):  # type: ignore[type-arg]
    """Repository for the Entity aggregate.

    Manages Entity, Area, Workspace, and UserProfile within the
    same aggregate scope. Entity is the aggregate root.
    """

    _model_class: type[Any]  # Entity (imported lazily)
    _table_name = "entities"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the entity repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Entity

        self._model_class = Entity

    # ------------------------------------------------------------------
    # Entity CRUD
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new entity and persist it.

        Args:
            entity: The Entity domain object to create.

        Returns:
            The UUID of the created entity.

        Raises:
            DuplicateError: If (workspace_id, entity_type, canonical_name)
                already exists.
            DomainIntegrityError: If entity_type is invalid.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            entity_id = getattr(entity, "id", None)
            if entity_id is None:
                raise DomainIntegrityError(
                    entity_type="entity",
                    constraint="Created entity has no id",
                )
            return UUID(entity_id) if not isinstance(entity_id, UUID) else entity_id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_id(self, id: UUID) -> Any | None:
        """Find an entity by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The Entity if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        entity_types: list[str] | None = None,
        area_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> list[Any]:
        """Find entities by workspace with optional filters.

        Args:
            workspace_id: Workspace scope.
            entity_types: Filter by entity_type.
            area_id: Filter by area.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching Entity objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )

        if entity_types:
            stmt = stmt.where(self._model_class.entity_type.in_(entity_types))
        if area_id:
            stmt = stmt.where(self._model_class.area_id == str(area_id))

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_name(
        self,
        *,
        canonical_name: str,
        workspace_id: UUID,
        entity_type: str | None = None,
    ) -> Any | None:
        """Find an entity by canonical name within a workspace.

        Args:
            canonical_name: The canonical name to look up.
            workspace_id: Workspace scope.
            entity_type: Optional entity type filter.

        Returns:
            The Entity if found, None otherwise.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.canonical_name == canonical_name,
        )
        if entity_type:
            stmt = stmt.where(self._model_class.entity_type == entity_type)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        # ARRAY contains operator: alias = ANY(aliases)
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.aliases.contains([alias]),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_area(
        self,
        *,
        area_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all entities in a given area.

        Args:
            area_id: The area UUID.
            workspace_id: Workspace scope.

        Returns:
            List of matching Entity objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.area_id == str(area_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_parent(
        self,
        *,
        parent_entity_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find child entities of a given parent entity.

        Args:
            parent_entity_id: The parent entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of child Entity objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.parent_entity_id == str(parent_entity_id),
        )
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
            entity_types: Optional entity type filter.
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
    # Soft Delete — Entities are never deleted, only marked
    # ------------------------------------------------------------------

    async def soft_delete_impl(self, id: UUID) -> None:
        """Entities are never soft-deleted.

        This method raises an error to enforce entity immutability.
        Entity lifecycle is managed through counters and relationships,
        not deletion.
        """
        raise DomainIntegrityError(
            entity_type="entity",
            constraint="Entities are never deleted — use status management instead",
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
                entity_type="entity",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="entity",
            constraint=msg[:200],
        )

    # ------------------------------------------------------------------
    # Area Management
    # ------------------------------------------------------------------

    async def create_area(
        self,
        area: Any,
        *,
        workspace_id: UUID,
    ) -> UUID:
        """Create a new area within a workspace.

        Args:
            area: The Area domain object.
            workspace_id: Workspace scope.

        Returns:
            The UUID of the created area.
        """
        self.session.add(area)
        await self.session.flush()
        area_id = getattr(area, "id", None)
        return UUID(area_id) if not isinstance(area_id, UUID) else area_id

    async def find_area_by_name(
        self,
        *,
        name: str,
        workspace_id: UUID,
    ) -> Any | None:
        """Find an area by name within a workspace.

        Args:
            name: Area name.
            workspace_id: Workspace scope.

        Returns:
            The Area if found, None otherwise.
        """
        from backend.shared.domain.memory_models import Area

        stmt = select(Area).where(
            Area.workspace_id == str(workspace_id),
            Area.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_child_areas(
        self,
        *,
        parent_area_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find child areas of a given area.

        Args:
            parent_area_id: Parent area UUID.
            workspace_id: Workspace scope.

        Returns:
            List of child Area objects.
        """
        from backend.shared.domain.memory_models import Area

        stmt = select(Area).where(
            Area.workspace_id == str(workspace_id),
            Area.parent_area_id == str(parent_area_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Workspace Management
    # ------------------------------------------------------------------

    async def get_or_create_workspace(
        self,
        *,
        name: str,
        description: str | None = None,
    ) -> Any:
        """Get the workspace singleton or create it if not exists.

        Args:
            name: Workspace name.
            description: Optional workspace description.

        Returns:
            The Workspace object.
        """
        from backend.shared.domain.memory_models import Workspace

        stmt = select(Workspace).limit(1)
        result = await self.session.execute(stmt)
        ws = result.scalar_one_or_none()

        if ws is None:
            ws = Workspace(
                id=UUID(int=0),  # Placeholder, will be replaced
                name=name,
                description=description,
            )
            self.session.add(ws)
            await self.session.flush()

        return ws

    # ------------------------------------------------------------------
    # UserProfile Management
    # ------------------------------------------------------------------

    async def create_user_profile(
        self,
        profile: Any,
        *,
        workspace_id: UUID,
    ) -> UUID:
        """Create a new user profile.

        Args:
            profile: The UserProfile domain object.
            workspace_id: Workspace scope.

        Returns:
            The UUID of the created profile.
        """
        self.session.add(profile)
        await self.session.flush()
        profile_id = getattr(profile, "id", None)
        return UUID(profile_id) if not isinstance(profile_id, UUID) else profile_id

    async def find_user_profile_by_external(
        self,
        *,
        external_user_id: str,
        workspace_id: UUID,
    ) -> Any | None:
        """Find a user profile by external user ID.

        Args:
            external_user_id: External user identifier.
            workspace_id: Workspace scope.

        Returns:
            The UserProfile if found, None otherwise.
        """
        from backend.shared.domain.memory_models import UserProfile

        stmt = select(UserProfile).where(
            UserProfile.workspace_id == str(workspace_id),
            UserProfile.external_user_id == external_user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_user_profile_by_id(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
    ) -> Any | None:
        """Find a user profile by internal ID.

        Args:
            user_id: The user profile UUID.
            workspace_id: Workspace scope.

        Returns:
            The UserProfile if found, None otherwise.
        """
        from backend.shared.domain.memory_models import UserProfile

        stmt = select(UserProfile).where(
            UserProfile.workspace_id == str(workspace_id),
            UserProfile.id == str(user_id),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
