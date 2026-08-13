"""TopicRepository — CRUD for the Topic aggregate.

Manages topics and topic_links tables. Topics are the aggregate root;
TopicLink is a child within the aggregate (many-to-many junction).

Per Phase 21.6 Stage 2.2 frozen design:
- Aggregate root: Topic
- Child: TopicLink (many-to-many junction)
- Status: initial, active, evolved, superseded, archived
- Source types: reconstruction, candidate, entity
- UNIQUE (workspace_id, name) on topics
- UNIQUE (topic_id, source_type, source_id) on topic_links
- Hierarchy: parent_topic_id self-reference (nullable)
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
    NotFoundError,
)
from backend.repository.exceptions import (
    IntegrityError as DomainIntegrityError,
)


class TopicRepository(BaseRepository):  # type: ignore[type-arg]
    """Repository for the Topic aggregate."""

    _model_class: type[Any]
    _table_name = "topics"

    async def soft_delete_impl(self, id: UUID) -> None:
        """Soft delete a topic by setting status to 'archived'."""
        from sqlalchemy import update

        stmt = (
            update(self._model_class)
            .where(self._model_class.id == id)
            .values(status="archived")
        )
        await self.session.execute(stmt)

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the topic repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Topic

        self._model_class = Topic

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new topic and persist it.

        Args:
            entity: The Topic domain object to create.

        Returns:
            The UUID of the created topic.

        Raises:
            DuplicateError: If a topic with the same name exists in the workspace.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            entity_id = getattr(entity, "id", None)
            if entity_id is None:
                raise DomainIntegrityError(
                    entity_type="topic",
                    constraint="Created topic has no id",
                )
            return UUID(entity_id) if not isinstance(entity_id, UUID) else entity_id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)

    async def get_by_id(self, id: UUID) -> Any | None:
        """Find a topic by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The Topic if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, entity: Any) -> None:
        """Update an existing topic.

        Args:
            entity: The Topic domain object to update.

        Raises:
            NotFoundError: If the topic does not exist.
        """
        stmt = select(self._model_class).where(self._model_class.id == entity.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            raise NotFoundError(
                entity_type="topic",
                entity_id=str(entity.id),
            )
        for key in entity.__mapper__.columns.keys():
            if hasattr(entity, key):
                setattr(existing, key, getattr(entity, key))
        await self.session.flush()

    async def delete(self, id: UUID) -> bool:
        """Delete a topic by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            True if deleted, False if not found.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        topic = result.scalar_one_or_none()
        if topic is None:
            return False
        await self.session.delete(topic)
        await self.session.flush()
        return True

    # ------------------------------------------------------------------
    # Topic Queries
    # ------------------------------------------------------------------

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> list[Any]:
        """Find topics by workspace with optional filters.

        Args:
            workspace_id: Workspace scope.
            status: Filter by status.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching Topic objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )

        if status:
            stmt = stmt.where(self._model_class.status == status)

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
        workspace_id: UUID,
        name: str,
    ) -> Any | None:
        """Find a topic by name within a workspace.

        Args:
            workspace_id: Workspace scope.
            name: Topic name (case-sensitive).

        Returns:
            The Topic if found, None otherwise.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_parent(
        self,
        *,
        parent_topic_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all child topics of a parent topic.

        Args:
            parent_topic_id: Parent topic UUID.
            workspace_id: Workspace scope.

        Returns:
            List of child Topic objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.parent_topic_id == str(parent_topic_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_root_topics(
        self,
        *,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all root topics (no parent) in a workspace.

        Args:
            workspace_id: Workspace scope.

        Returns:
            List of root Topic objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.parent_topic_id.is_(None),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # TopicLink Operations
    # ------------------------------------------------------------------

    async def create_link(
        self,
        *,
        topic_id: UUID,
        source_type: str,
        source_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Create a topic link.

        Args:
            topic_id: Topic UUID.
            source_type: Source type ('reconstruction', 'candidate', 'entity').
            source_id: Source UUID.
            workspace_id: Workspace scope.

        Raises:
            DuplicateError: If the link already exists.
            NotFoundError: If the topic does not exist.
        """
        from backend.shared.domain.memory_models import TopicLink

        # Verify topic exists
        topic = await self.get_by_id(topic_id)
        if topic is None:
            raise NotFoundError(
                entity_type="topic",
                entity_id=str(topic_id),
            )

        # Check workspace isolation
        if topic.workspace_id != str(workspace_id):
            raise DomainIntegrityError(
                entity_type="topic_link",
                constraint=f"Topic {topic_id} not in workspace {workspace_id}",
            )

        # Check duplicate
        existing = await self.session.execute(
            select(TopicLink).where(
                TopicLink.topic_id == str(topic_id),
                TopicLink.source_type == source_type,
                TopicLink.source_id == str(source_id),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateError(
                entity_type="topic_link",
                constraint=f"Link already exists: topic={topic_id}, source={source_type}:{source_id}",
            )

        link = TopicLink(
            id=self._generate_id(),
            topic_id=topic_id,
            source_type=source_type,
            source_id=source_id,
        )
        self.session.add(link)
        await self.session.flush()

    async def remove_link(
        self,
        *,
        topic_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> bool:
        """Remove a topic link.

        Args:
            topic_id: Topic UUID.
            source_type: Source type.
            source_id: Source UUID.

        Returns:
            True if removed, False if not found.
        """
        from backend.shared.domain.memory_models import TopicLink

        stmt = select(TopicLink).where(
            TopicLink.topic_id == str(topic_id),
            TopicLink.source_type == source_type,
            TopicLink.source_id == str(source_id),
        )
        result = await self.session.execute(stmt)
        link = result.scalar_one_or_none()
        if link is None:
            return False
        await self.session.delete(link)
        await self.session.flush()
        return True

    async def list_links(
        self,
        *,
        topic_id: UUID,
    ) -> list[Any]:
        """List all links for a topic.

        Args:
            topic_id: Topic UUID.

        Returns:
            List of TopicLink objects.
        """
        from backend.shared.domain.memory_models import TopicLink

        stmt = select(TopicLink).where(TopicLink.topic_id == str(topic_id))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_topics_for_source(
        self,
        *,
        source_type: str,
        source_id: UUID,
    ) -> list[Any]:
        """List all topics linked to a source.

        Args:
            source_type: Source type ('reconstruction', 'candidate', 'entity').
            source_id: Source UUID.

        Returns:
            List of Topic objects.
        """
        from backend.shared.domain.memory_models import TopicLink

        stmt = (
            select(self._model_class)
            .join(TopicLink, self._model_class.id == TopicLink.topic_id)
            .where(
                TopicLink.source_type == source_type,
                TopicLink.source_id == str(source_id),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_sources_for_topic(
        self,
        *,
        topic_id: UUID,
        source_type: str | None = None,
    ) -> list[Any]:
        """List all sources linked to a topic.

        Args:
            topic_id: Topic UUID.
            source_type: Optional filter by source type.

        Returns:
            List of TopicLink objects.
        """
        from backend.shared.domain.memory_models import TopicLink

        stmt = select(TopicLink).where(TopicLink.topic_id == str(topic_id))
        if source_type:
            stmt = stmt.where(TopicLink.source_type == source_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Cycle Detection for Hierarchy
    # ------------------------------------------------------------------

    async def is_valid_parent(
        self,
        *,
        topic_id: UUID,
        parent_topic_id: UUID | None,
        workspace_id: UUID,
    ) -> bool:
        """Check if parent_topic_id is valid (no cycles, same workspace).

        Args:
            topic_id: The topic being modified.
            parent_topic_id: Proposed parent topic ID.
            workspace_id: Workspace scope.

        Returns:
            True if valid, False if cycle detected or workspace mismatch.
        """
        if parent_topic_id is None:
            return True

        # Same workspace check
        topic = await self.get_by_id(topic_id)
        if topic is None:
            return False
        if topic.workspace_id != str(workspace_id):
            return False

        # Self-parent check
        if parent_topic_id == topic_id:
            return False

        # Cycle detection via BFS
        visited: set[UUID] = set()
        queue = [parent_topic_id]
        while queue:
            current = queue.pop(0)
            if current == topic_id:
                return False  # Cycle detected
            if current in visited:
                continue
            visited.add(current)
            parent = await self.get_by_id(current)
            if parent and parent.parent_topic_id:
                queue.append(UUID(parent.parent_topic_id))

        return True
