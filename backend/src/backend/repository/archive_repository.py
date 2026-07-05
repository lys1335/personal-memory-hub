"""ArchiveRepository - CRUD for the Archive aggregate.

Manages the archives table and tag_links for archive target_type.
Archives are cognitive compression records (monthly/yearly) with
hierarchical self-referencing (archive-of-archive).

Per 10_9 §4.6 and 09 §09.4.12:
- Aggregate root: Archive
- Table: memory_hub.archives
- Types: monthly, yearly
- Hierarchical: source_archive_id self-reference
- Period constraint: period_start <= period_end
- TagLinks scoped to archive target_type
"""

from __future__ import annotations

from datetime import date
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


class ArchiveRepository(BaseRepository):
    """Repository for the Archive aggregate."""

    _model_class: type[Any]
    _table_name = "archives"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the archive repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Archive  # noqa: PLC0415

        self._model_class = Archive

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new archive and persist it.

        Args:
            entity: The Archive domain object to create.

        Returns:
            The UUID of the created archive.

        Raises:
            DomainIntegrityError: If period constraint or type is invalid.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            entity_id = getattr(entity, "id", None)
            if entity_id is None:
                raise DomainIntegrityError(
                    entity_type="archive",
                    constraint="Created archive has no id",
                )
            return UUID(entity_id) if not isinstance(entity_id, UUID) else entity_id
        except IntegrityError as exc:
            self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_period(
        self,
        *,
        period_start: date,
        period_end: date,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find archives overlapping a given period.

        Args:
            period_start: Start of the period to search.
            period_end: End of the period to search.
            workspace_id: Workspace scope.

        Returns:
            List of Archive entities overlapping the period.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.period_start <= period_end,
            self._model_class.period_end >= period_start,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_type(
        self,
        *,
        archive_type: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find archives by type (monthly or yearly).

        Args:
            archive_type: Archive type ('monthly' or 'yearly').
            workspace_id: Workspace scope.

        Returns:
            List of Archive entities of the given type.
        """
        valid_types = ("monthly", "yearly")
        if archive_type not in valid_types:
            raise DomainIntegrityError(
                entity_type="archive",
                constraint=f"Invalid archive_type: {archive_type}. Must be one of {valid_types}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.archive_type == archive_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_parent_archives(
        self,
        *,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find root-level archives (no parent).

        Args:
            workspace_id: Workspace scope.

        Returns:
            List of Archive entities that have no parent.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.source_archive_id.is_(None),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_child_archives(
        self,
        *,
        parent_archive_id: UUID,
    ) -> list[Any]:
        """Find child archives of a given parent.

        Args:
            parent_archive_id: The parent archive UUID.

        Returns:
            List of Archive entities that reference the parent.
        """
        stmt = select(self._model_class).where(
            self._model_class.source_archive_id == parent_archive_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # TagLink Operations (archive target_type)
    # ------------------------------------------------------------------

    async def link_tag(
        self,
        *,
        archive_id: UUID,
        tag_id: UUID,
        workspace_id: UUID,
    ) -> UUID:
        """Link a tag to an archive.

        Creates a TagLink record with target_type='archive'.

        Args:
            archive_id: The archive UUID.
            tag_id: The tag UUID.
            workspace_id: Workspace scope.

        Returns:
            The UUID of the created TagLink.

        Raises:
            DuplicateError: If the tag-link already exists.
        """
        from backend.shared.domain.memory_models import TagLink  # noqa: PLC0415

        # Verify archive exists
        archive = await self.find_by_id(archive_id)
        if archive is None:
            raise NotFoundError(
                entity_type="archive",
                entity_id=str(archive_id),
            )

        # Check for duplicate tag_link
        stmt = select(TagLink).where(
            TagLink.tag_id == tag_id,
            TagLink.target_type == "archive",
            TagLink.target_id == archive_id,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise DuplicateError(
                entity_type="tag_link",
                constraint=f"Tag {tag_id} already linked to archive {archive_id}",
            )

        tag_link = TagLink(
            id=UUID(int=hash((str(workspace_id), str(tag_id), "archive", str(archive_id))) % (2**128)),
            workspace_id=workspace_id,
            tag_id=tag_id,
            target_type="archive",
            target_id=archive_id,
        )

        try:
            self.session.add(tag_link)
            await self.session.flush()
            return tag_link.id  # type: ignore[return-value]
        except IntegrityError as exc:
            self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def unlink_tag(
        self,
        *,
        archive_id: UUID,
        tag_id: UUID,
    ) -> None:
        """Remove a tag link from an archive.

        Args:
            archive_id: The archive UUID.
            tag_id: The tag UUID.

        Raises:
            NotFoundError: If the link does not exist.
        """
        from backend.shared.domain.memory_models import TagLink  # noqa: PLC0415

        stmt = select(TagLink).where(
            TagLink.tag_id == tag_id,
            TagLink.target_type == "archive",
            TagLink.target_id == archive_id,
        )
        result = await self.session.execute(stmt)
        link = result.scalar_one_or_none()

        if link is None:
            raise NotFoundError(
                entity_type="tag_link",
                entity_id=f"archive={archive_id}, tag={tag_id}",
            )

        await self.session.delete(link)
        await self.session.flush()

    async def get_tags_for_archive(
        self,
        *,
        archive_id: UUID,
    ) -> list[Any]:
        """Get all tags linked to an archive.

        Args:
            archive_id: The archive UUID.

        Returns:
            List of TagLink records.
        """
        from backend.shared.domain.memory_models import TagLink  # noqa: PLC0415

        stmt = select(TagLink).where(
            TagLink.target_type == "archive",
            TagLink.target_id == archive_id,
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
        archive_type: str | None = None,
        page_number: int = 1,
        page_size: int = 20,
    ) -> Page[Any]:
        """Find archives with pagination.

        Args:
            workspace_id: Workspace scope.
            archive_type: Optional filter by type.
            page_number: 1-based page number.
            page_size: Items per page.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_all_filtered(
            workspace_id=workspace_id,
            archive_type=archive_type,
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

    async def find_all_filtered(
        self,
        *,
        workspace_id: UUID,
        archive_type: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Find archives with optional type filter.

        Args:
            workspace_id: Workspace scope.
            archive_type: Optional type filter.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            List of matching Archive entities.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
        )

        if archive_type is not None:
            valid_types = ("monthly", "yearly")
            if archive_type not in valid_types:
                raise DomainIntegrityError(
                    entity_type="archive",
                    constraint=f"Invalid archive_type: {archive_type}",
                )
            stmt = stmt.where(self._model_class.archive_type == archive_type)

        stmt = stmt.order_by(self._model_class.period_start.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _raise_integrity_error(self, exc: IntegrityError) -> None:
        """Map SQLAlchemy IntegrityError to domain exception.

        Args:
            exc: The SQLAlchemy IntegrityError.

        Raises:
            DomainIntegrityError or DuplicateError.
        """
        orig = exc.orig
        msg = str(orig) if orig else str(exc)

        if "unique" in msg.lower() or "duplicate" in msg.lower():
            raise DuplicateError(
                entity_type="archive",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="archive",
            constraint=msg[:200],
        )
