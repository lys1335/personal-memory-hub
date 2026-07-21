"""TagRepository — CRUD for the Tag aggregate.

Manages tags and tag_links tables. Tags are the aggregate root;
TagLink is a child within the aggregate (many-to-many junction).

Per 10_9 §4.7 and 09 §09.4.10-09.4.11:
- Aggregate root: Tag
- Child: TagLink (many-to-many junction)
- Tag types: system, ai, user
- Target types: entity, memory_node, archive
- UNIQUE (workspace_id, name) on tags
- UNIQUE (tag_id, target_type, target_id) on tag_links
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
from backend.repository.pagination import Page


class TagRepository(BaseRepository):  # type: ignore[type-arg]
    """Repository for the Tag aggregate."""

    _model_class: type[Any]
    _table_name = "tags"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the tag repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Tag

        self._model_class = Tag

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new tag and persist it.

        Args:
            entity: The Tag domain object to create.

        Returns:
            The UUID of the created tag.

        Raises:
            DuplicateError: If a tag with the same name exists in the workspace.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            entity_id = getattr(entity, "id", None)
            if entity_id is None:
                raise DomainIntegrityError(
                    entity_type="tag",
                    constraint="Created tag has no id",
                )
            return UUID(entity_id) if not isinstance(entity_id, UUID) else entity_id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        tag_types: list[str] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Find tags by workspace with optional type filter.

        Args:
            workspace_id: Workspace scope.
            tag_types: Optional list of tag types to filter by.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of Tag entities.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
        )

        if tag_types:
            valid_types = ("system", "ai", "user")
            for t in tag_types:
                if t not in valid_types:
                    raise DomainIntegrityError(
                        entity_type="tag",
                        constraint=f"Invalid tag_type: {t}. Must be one of {valid_types}",
                    )
            stmt = stmt.where(self._model_class.tag_type.in_(tag_types))

        stmt = stmt.order_by(self._model_class.name.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_name(
        self,
        *,
        name: str,
        workspace_id: UUID,
    ) -> Any | None:
        """Find a tag by name within a workspace.

        Args:
            name: The tag name.
            workspace_id: Workspace scope.

        Returns:
            The Tag entity if found, None otherwise.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # TagLink Operations
    # ------------------------------------------------------------------

    async def link_tag(
        self,
        *,
        tag_id: UUID,
        target_type: str,
        target_id: UUID,
        workspace_id: UUID,
    ) -> UUID:
        """Link a tag to a target (entity, memory_node, or archive).

        Creates a TagLink record within the Tag aggregate.

        Args:
            tag_id: The tag UUID.
            target_type: Target type ('entity', 'memory_node', 'archive').
            target_id: The target entity UUID.
            workspace_id: Workspace scope.

        Returns:
            The UUID of the created TagLink.

        Raises:
            DuplicateError: If the tag-link already exists.
            NotFoundError: If the tag does not exist.
        """
        from backend.shared.domain.memory_models import TagLink

        # Verify tag exists
        tag = await self.find_by_id(tag_id)
        if tag is None:
            raise NotFoundError(
                entity_type="tag",
                entity_id=str(tag_id),
            )

        # Validate target_type
        valid_targets = ("entity", "memory_node", "archive")
        if target_type not in valid_targets:
            raise DomainIntegrityError(
                entity_type="tag_link",
                constraint=f"Invalid target_type: {target_type}. Must be one of {valid_targets}",
            )

        # Check for duplicate tag_link
        stmt = select(TagLink).where(
            TagLink.tag_id == tag_id,
            TagLink.target_type == target_type,
            TagLink.target_id == target_id,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise DuplicateError(
                entity_type="tag_link",
                constraint=f"Tag {tag_id} already linked to {target_type}:{target_id}",
            )

        tag_link = TagLink(
            id=UUID(int=hash((str(workspace_id), str(tag_id), target_type, str(target_id))) % (2**128)),
            workspace_id=workspace_id,
            tag_id=tag_id,
            target_type=target_type,
            target_id=target_id,
        )

        try:
            self.session.add(tag_link)
            await self.session.flush()
            return tag_link.id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def unlink_tag(
        self,
        *,
        tag_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> None:
        """Remove a tag link.

        Args:
            tag_id: The tag UUID.
            target_type: Target type.
            target_id: The target entity UUID.

        Raises:
            NotFoundError: If the link does not exist.
        """
        from backend.shared.domain.memory_models import TagLink

        stmt = select(TagLink).where(
            TagLink.tag_id == tag_id,
            TagLink.target_type == target_type,
            TagLink.target_id == target_id,
        )
        result = await self.session.execute(stmt)
        link = result.scalar_one_or_none()

        if link is None:
            raise NotFoundError(
                entity_type="tag_link",
                entity_id=f"tag={tag_id}, {target_type}={target_id}",
            )

        await self.session.delete(link)
        await self.session.flush()

    async def find_linked_targets(
        self,
        *,
        tag_id: UUID,
    ) -> list[Any]:
        """Find all targets linked to a tag.

        Args:
            tag_id: The tag UUID.

        Returns:
            List of TagLink records.
        """
        from backend.shared.domain.memory_models import TagLink

        stmt = select(TagLink).where(
            TagLink.tag_id == tag_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_tags_for_target(
        self,
        *,
        target_type: str,
        target_id: UUID,
    ) -> list[Any]:
        """Find all tags linked to a target.

        Args:
            target_type: Target type ('entity', 'memory_node', 'archive').
            target_id: The target entity UUID.

        Returns:
            List of TagLink records.
        """
        from backend.shared.domain.memory_models import TagLink

        stmt = select(TagLink).where(
            TagLink.target_type == target_type,
            TagLink.target_id == target_id,
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
        tag_types: list[str] | None = None,
        page_number: int = 1,
        page_size: int = 20,
    ) -> Page[Any]:
        """Find tags with pagination.

        Args:
            workspace_id: Workspace scope.
            tag_types: Optional filter by tag types.
            page_number: 1-based page number.
            page_size: Items per page.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_by_workspace(
            workspace_id=workspace_id,
            tag_types=tag_types,
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


    async def soft_delete_impl(self, id):
        """Tagss are immutable: soft_delete_impl is prohibited.

        Args:
            id: The entity ID to soft-delete.

        Raises:
            DomainIntegrityError: Always, because entities cannot be deleted.
        """
        raise DomainIntegrityError(
            entity_type="tags",
            constraint="Tags are immutable - no DELETE allowed",
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _raise_integrity_error(self, exc: IntegrityError) -> None:
        """Map SQLAlchemy IntegrityError to domain exception.

        Args:
            exc: The SQLAlchemy IntegrityError.

        Raises:
            DuplicateError or DomainIntegrityError.
        """
        orig = exc.orig
        msg = str(orig) if orig else str(exc)

        if "unique" in msg.lower() or "duplicate" in msg.lower():
            raise DuplicateError(
                entity_type="tag",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="tag",
            constraint=msg[:200],
        )
