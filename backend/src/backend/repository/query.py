"""QueryRepository base class for read-only complex queries.

QueryRepositories handle multi-table JOIN queries, graph traversal,
and vector similarity search. They are read-only — no write operations.

Per 10_9 §4.10-4.12 and G-015 (Side-Effect Free Query):
- QueryRepositories never modify domain state or persistent data
- They return Domain Objects, never DTOs or Projections
- They may depend on the same AsyncSession but use read-only transactions
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.exceptions import ReadOnlyError
from backend.repository.pagination import Page
from backend.repository.workspace import WorkspaceIsolationMixin

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class QueryRepository(WorkspaceIsolationMixin[T], ABC, Generic[T]):
    """Abstract base class for read-only query repositories.

    QueryRepositories are specialized Repository implementations that
    handle complex queries which cannot be expressed through simple CRUD.

    Key differences from BaseRepository:
    1. Read-only: no create/update/delete operations
    2. Multi-table: may JOIN across multiple entity tables
    3. Complex: graph traversal, vector similarity, aggregations
    4. Pagination: cursor-based and offset-based pagination support

    Subclasses must implement:
    - ``_model_class``: The primary SQLAlchemy ORM model class
    - ``_table_name``: The primary database table name (for error messages)
    """

    _model_class: type[T]
    _table_name: str

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the query repository with an async session.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Read-Only Enforcement
    # ------------------------------------------------------------------

    async def create(self, *args: Any, **kwargs: Any) -> None:
        """Read-only: write operations are prohibited."""
        raise ReadOnlyError(repository_name=self.__class__.__name__)

    async def update(self, *args: Any, **kwargs: Any) -> None:
        """Read-only: write operations are prohibited."""
        raise ReadOnlyError(repository_name=self.__class__.__name__)

    async def soft_delete(self, *args: Any, **kwargs: Any) -> None:
        """Read-only: write operations are prohibited."""
        raise ReadOnlyError(repository_name=self.__class__.__name__)

    async def exists(self, *args: Any, **kwargs: Any) -> bool:
        """Read-only: exists() is not applicable to QueryRepositories."""
        raise ReadOnlyError(repository_name=self.__class__.__name__)

    # ------------------------------------------------------------------
    # Read Operations
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
    ) -> list[T]:
        """Find entities with optional filters and pagination.

        Args:
            workspace_id: Workspace scope.
            filters: Additional filter conditions.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching entities.
        """
        stmt = select(self._model_class)

        effective_workspace = workspace_id or self._ensure_workspace()
        stmt = stmt.where(self._model_class.workspace_id == effective_workspace)  # type: ignore[attr-defined]

        if filters:
            for col_name, value in filters.items():
                if hasattr(self._model_class, col_name):
                    col = getattr(self._model_class, col_name)  # type: ignore[attr-defined]
                    if isinstance(value, list):
                        stmt = stmt.where(col.in_(value))  # type: ignore[union-attr]
                    else:
                        stmt = stmt.where(col == value)  # type: ignore[union-attr]

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)  # type: ignore[attr-defined]
            stmt = stmt.order_by(order_col.desc() if descending else order_col.asc())  # type: ignore[union-attr]

        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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

    # ------------------------------------------------------------------
    # Pagination
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
        """Find entities with pagination.

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
            limit=page_size + 1,  # Fetch one extra to determine has_next
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
    # Transaction Support (read-only)
    # ------------------------------------------------------------------

    async def commit(self) -> None:
        """Commit is a no-op for read-only query repositories."""
        pass

    async def rollback(self) -> None:
        """Rollback is a no-op for read-only query repositories."""
        pass

    async def refresh(self, entity: T) -> None:
        """Refresh an entity from the database.

        Args:
            entity: The entity to refresh.
        """
        await self.session.refresh(entity)

    # ------------------------------------------------------------------
    # Abstract: Complex Query Methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def complex_query(self, *args: Any, **kwargs: Any) -> Any:
        """Execute a complex multi-table query.

        Subclasses implement this for domain-specific complex queries:
        - MemoryQueryRepository: findWithEvidence, findByEntityAndLevel
        - EntityQueryRepository: getEntityGraph, findRelatedEntities
        - VectorQueryRepository: similaritySearch, hybridSearch

        Args:
            *args: Positional query parameters.
            **kwargs: Named query parameters.

        Returns:
            Query result (Domain objects, graph results, or ranked lists).
        """
        raise NotImplementedError
