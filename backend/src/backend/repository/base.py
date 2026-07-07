"""BaseRepository — abstract base class for all Repository implementations.

Provides the standard CRUD interface defined in 10_9 §5.3:
- create(entity) → ID
- find_by_id(id) → T | None
- find_all(**filters) → list[T]
- update(entity) → T
- soft_delete(id) → None
- exists(id) → bool

Plus:
- AsyncSession integration (injected at construction)
- Per-operation transaction support
- Workspace isolation (via WorkspaceIsolationMixin)
- Exception mapping (database errors → domain exceptions)

Per 10_9 §5.1 and G-013: Repository is persistence only. No business
logic, no Engine calls, no Service calls, no Repository-to-Repository calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.exceptions import (
    DuplicateError,
    RepositoryError,
)
from backend.repository.exceptions import (
    IntegrityError as DomainIntegrityError,
)
from backend.repository.pagination import Page
from backend.repository.workspace import WorkspaceIsolationMixin

T = TypeVar("T")


class BaseRepository(WorkspaceIsolationMixin[T], ABC, Generic[T]):
    """Abstract base class for all Repository implementations.

    All D2 Repositories (EntityRepository, MemoryNodeRepository, etc.)
    inherit from this class. It provides:

    1. Standard CRUD interface (create, find_by_id, find_all, update, soft_delete, exists)
    2. AsyncSession management
    3. Transaction support (each operation is atomic)
    4. Workspace isolation enforcement
    5. Database exception → domain exception mapping

    Subclasses must implement:
    - ``_model_class``: The SQLAlchemy ORM model class
    - ``_table_name``: The database table name (for error messages)
    - ``soft_delete_impl(id)``: Domain-specific soft delete logic
    """

    _model_class: type[T]
    _table_name: str

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async session.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        self.session = session

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def create(self, entity: T) -> UUID:
        """Create a new entity and persist it.

        Args:
            entity: The domain object to create.

        Returns:
            The UUID of the created entity.

        Raises:
            DuplicateError: If a uniqueness constraint is violated.
            DomainIntegrityError: If a domain constraint is violated.
            RepositoryError: For other persistence failures.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            # Extract ID — assumes entity has an 'id' attribute
            entity_id = getattr(entity, "id", None)
            if entity_id is None:
                raise RepositoryError(f"Created entity has no id attribute: {self._table_name}")
            return UUID(entity_id) if not isinstance(entity_id, UUID) else entity_id
        except IntegrityError as exc:
            self.session.rollback()
            raise self._map_integrity_error(exc) from exc
        except OperationalError as exc:
            self.session.rollback()
            raise RepositoryError(
                f"Database operational error during create: {exc}",
                entity_type=self._table_name,
            ) from exc

    async def find_by_id(self, id: UUID) -> T | None:
        """Find an entity by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The entity if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        *,
        workspace_id: UUID | None = None,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[T]:
        """Find entities with optional filters and pagination.

        Args:
            workspace_id: Workspace scope (overrides instance workspace if set).
            filters: Additional filter conditions (column name → value).
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Whether to order in descending direction.

        Returns:
            List of matching entities.
        """
        stmt = select(self._model_class)

        # Workspace isolation
        effective_workspace = workspace_id or self._ensure_workspace()
        stmt = stmt.where(self._model_class.workspace_id == effective_workspace)  # type: ignore[attr-defined]

        # Additional filters
        if filters:
            for col_name, value in filters.items():
                if hasattr(self._model_class, col_name):
                    col = getattr(self._model_class, col_name)  # type: ignore[attr-defined]
                    if isinstance(value, list):
                        stmt = stmt.where(col.in_(value))  # type: ignore[union-attr]
                    else:
                        stmt = stmt.where(col == value)  # type: ignore[union-attr]

        # Ordering
        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)  # type: ignore[attr-defined]
            stmt = stmt.order_by(order_col.desc() if descending else order_col.asc())  # type: ignore[union-attr]

        # Pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, entity: T) -> T:
        """Update an existing entity.

        Args:
            entity: The domain object with updated values.

        Returns:
            The updated entity.

        Raises:
            NotFoundError: If the entity does not exist.
            DomainIntegrityError: If a constraint is violated.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            return entity
        except IntegrityError as exc:
            self.session.rollback()
            raise self._map_integrity_error(exc) from exc
        except OperationalError as exc:
            self.session.rollback()
            raise RepositoryError(
                f"Database operational error during update: {exc}",
                entity_type=self._table_name,
            ) from exc

    async def soft_delete(self, id: UUID) -> None:
        """Soft-delete an entity by marking it as deprecated/superseded.

        Domain-specific soft delete is delegated to subclasses.
        The default implementation raises NotImplementedError — subclasses
        must implement ``soft_delete_impl``.

        Args:
            id: The UUID of the entity to soft-delete.
        """
        await self.soft_delete_impl(id)

    async def exists(self, id: UUID) -> bool:
        """Check if an entity exists by primary key.

        Args:
            id: The UUID primary key.

        Returns:
            True if the entity exists, False otherwise.
        """
        stmt = select(1).where(self._model_class.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # Query Operations (bulk)
    # ------------------------------------------------------------------

    async def find_page(
        self,
        *,
        workspace_id: UUID | None = None,
        filters: dict[str, Any] | None = None,
        page_number: int = 1,
        page_size: int = 20,
        order_by: str | None = None,
        descending: bool = False,
    ) -> Page[T]:
        """Find entities with pagination, returning a Page object.

        Args:
            workspace_id: Workspace scope.
            filters: Additional filter conditions.
            page_number: 1-based page number.
            page_size: Number of items per page.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            A Page object containing the results and pagination metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_all(
            workspace_id=workspace_id,
            filters=filters,
            offset=offset,
            limit=page_size + 1,  # Fetch one extra to detect has_next
            order_by=order_by,
            descending=descending,
        )

        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]

        return Page(
            items=items,
            total=None,  # Total not computed for efficiency
            page_number=page_number,
            page_size=page_size,
            has_next=has_next,
            has_prev=page_number > 1,
        )

    # ------------------------------------------------------------------
    # Transaction Support
    # ------------------------------------------------------------------

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()

    async def refresh(self, entity: T) -> None:
        """Refresh an entity from the database.

        Args:
            entity: The entity to refresh.
        """
        await self.session.refresh(entity)

    # ------------------------------------------------------------------
    # Abstract Methods (to be implemented by subclasses)
    # ------------------------------------------------------------------

    @abstractmethod
    async def soft_delete_impl(self, id: UUID) -> None:
        """Domain-specific soft delete implementation.

        Subclasses implement this to apply the correct soft-delete strategy
        (e.g., setting status='deprecated', status='superseded', etc.).

        Args:
            id: The UUID of the entity to soft-delete.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _map_integrity_error(self, exc: IntegrityError) -> DomainIntegrityError | DuplicateError:
        """Map a SQLAlchemy IntegrityError to a domain exception.

        Args:
            exc: The SQLAlchemy IntegrityError.

        Returns:
            Either a DuplicateError (unique constraint) or
            DomainIntegrityError (check constraint / foreign key).
        """
        # Try to extract constraint name from the error
        orig = exc.orig
        msg = str(orig) if orig else str(exc)

        if "unique" in msg.lower() or "duplicate" in msg.lower() or "UNIQUE" in msg:
            return DuplicateError(
                entity_type=self._table_name,
                constraint=msg[:200],
            )

        return DomainIntegrityError(
            entity_type=self._table_name,
            constraint=msg[:200],
        )
