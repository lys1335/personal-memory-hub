"""TaskRepository — CRUD for the Task aggregate.

Manages the Task aggregate root exclusively. Tasks are the unified
work queue for the Personal Memory Hub — ingestion, reflection,
activation, and archive operations all flow through this table.

Per 10_9 §4.8 and 09 §09.4.15:
- Aggregate root: Task
- Tables: tasks
- Task types: INGESTION, REFLECTION, ACTIVATION, ARCHIVE
- Status: pending, running, completed, failed, dead_letter
- Debounce: UNIQUE (workspace_id, task_type, debounce_key) WHERE status IN ('pending', 'running')
- Retry: retry_count, max_retries, exponential backoff
- Payload: JSONB (Task Runtime does not parse)

Responsibilities:
- Task CRUD and lifecycle queries
- Status lookups (pending, running, completed, failed, dead_letter)
- Type-scoped queries (INGESTION, REFLECTION, ACTIVATION, ARCHIVE)
- Entity/area-scoped task queries
- Enabled task listing
- Pagination

Must NOT perform:
- Runtime scheduling
- Task execution
- Worker assignment
- Capability checks
- Business validation
- Retry logic (beyond persistence)
- Execution history
- Domain event publishing

Inherits from BaseRepository.
Repository persists Task aggregate only.

Imported by: TaskService, TaskRuntime.
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


class TaskRepository(BaseRepository):  # type: ignore[type-arg]
    """Repository for the Task aggregate.

    Manages Task persistence only. Tasks are the unified work queue
    for ingestion, reflection, activation, and archive operations.
    """

    _model_class: type[Any]  # Task (imported lazily)
    _table_name = "tasks"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the task repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import Task

        self._model_class = Task

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new task and persist it.

        Args:
            entity: The Task domain object to create.

        Returns:
            The UUID of the created task.

        Raises:
            DuplicateError: If (workspace_id, task_type, debounce_key)
                already exists with status pending/running.
            DomainIntegrityError: If task_type or status is invalid.
            IntegrityError: If a foreign key constraint fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            task_id = getattr(entity, "id", None)
            if task_id is None:
                raise DomainIntegrityError(
                    entity_type="task",
                    constraint="Created task has no id",
                )
            return UUID(task_id) if not isinstance(task_id, UUID) else task_id
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def find_by_id(self, id: UUID) -> Any | None:
        """Find a task by its primary key.

        Args:
            id: The UUID primary key.

        Returns:
            The Task if found, None otherwise.
        """
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Task Queries
    # ------------------------------------------------------------------

    async def find_by_workspace(
        self,
        *,
        workspace_id: UUID,
        task_types: list[str] | None = None,
        status: str | None = None,
        entity_id: UUID | None = None,
        area_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> list[Any]:
        """Find tasks by workspace with optional filters.

        Args:
            workspace_id: Workspace scope.
            task_types: Filter by task_type (INGESTION, REFLECTION, ACTIVATION, ARCHIVE).
            status: Filter by status (pending, running, completed, failed, dead_letter).
            entity_id: Filter by associated entity.
            area_id: Filter by associated area.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of matching Task objects.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )

        if task_types:
            stmt = stmt.where(self._model_class.task_type.in_(task_types))
        if status:
            stmt = stmt.where(self._model_class.status == status)
        if entity_id:
            stmt = stmt.where(self._model_class.entity_id == str(entity_id))
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

    async def find_by_type(
        self,
        *,
        task_type: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find tasks by type within a workspace.

        Args:
            task_type: Task type (INGESTION, REFLECTION, ACTIVATION, ARCHIVE).
            workspace_id: Workspace scope.

        Returns:
            List of Task objects of the given type.

        Raises:
            DomainIntegrityError: If task_type is not valid.
        """
        valid_types = ("INGESTION", "REFLECTION", "ACTIVATION", "ARCHIVE")
        if task_type not in valid_types:
            raise DomainIntegrityError(
                entity_type="task",
                constraint=f"Invalid task_type: {task_type}. Must be one of {valid_types}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.task_type == task_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_status(
        self,
        *,
        status: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find tasks by status within a workspace.

        Args:
            status: Status (pending, running, completed, failed, dead_letter).
            workspace_id: Workspace scope.

        Returns:
            List of Task objects with the given status.

        Raises:
            DomainIntegrityError: If status is not a valid value.
        """
        valid_statuses = ("pending", "running", "completed", "failed", "dead_letter")
        if status not in valid_statuses:
            raise DomainIntegrityError(
                entity_type="task",
                constraint=f"Invalid status: {status}. Must be one of {valid_statuses}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.status == status,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_pending_by_workspace(
        self,
        *,
        workspace_id: UUID,
        task_types: list[str] | None = None,
        entity_id: UUID | None = None,
        area_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Find pending tasks within a workspace.

        Convenience method for querying pending tasks, typically used
        by the TaskRuntime to fetch work items.

        Args:
            workspace_id: Workspace scope.
            task_types: Optional task type filter.
            entity_id: Optional entity filter.
            area_id: Optional area filter.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of pending Task objects.
        """
        return await self.find_by_workspace(
            workspace_id=workspace_id,
            task_types=task_types,
            status="pending",
            entity_id=entity_id,
            area_id=area_id,
            offset=offset,
            limit=limit,
            order_by="created_at",
            descending=False,
        )

    async def find_failed_for_retry(
        self,
        *,
        workspace_id: UUID,
        max_retries_threshold: int = 3,
        limit: int = 100,
    ) -> list[Any]:
        """Find failed tasks eligible for retry.

        Returns tasks with status 'failed' and retry_count < max_retries_threshold.

        Args:
            workspace_id: Workspace scope.
            max_retries_threshold: Maximum retries threshold (default 3).
            limit: Maximum number of records to return.

        Returns:
            List of failed Task objects eligible for retry.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.status == "failed",
            self._model_class.retry_count < max_retries_threshold,
        ).order_by(
            self._model_class.created_at.asc()
        ).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_entity(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all tasks for a specific entity.

        Args:
            entity_id: The entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of Task objects for the entity.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.entity_id == str(entity_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_enabled_tasks(
        self,
        *,
        workspace_id: UUID,
        task_types: list[str] | None = None,
        status: str | None = None,
    ) -> list[Any]:
        """Find enabled tasks within a workspace.

        Lists tasks that are not in a terminal state (completed, failed,
        dead_letter). Typically used for listing active/available tasks.

        Args:
            workspace_id: Workspace scope.
            task_types: Optional task type filter.
            status: Optional status filter.

        Returns:
            List of enabled Task objects.
        """
        # Enabled = not in terminal states
        terminal_statuses = ("completed", "failed", "dead_letter")
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.status.not_in(terminal_statuses),
        )

        if task_types:
            stmt = stmt.where(self._model_class.task_type.in_(task_types))
        if status:
            stmt = stmt.where(self._model_class.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def find_page(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        task_types: list[str] | None = None,
        status: str | None = None,
        entity_id: UUID | None = None,
        area_id: UUID | None = None,
        page_number: int = 1,
        page_size: int = 20,
        order_by: str = "created_at",
        descending: bool = False,
    ) -> Page[Any]:
        """Find tasks with pagination.

        Args:
            workspace_id: Workspace scope.
            task_types: Optional task type filter.
            status: Optional status filter.
            entity_id: Optional entity filter.
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
            task_types=task_types,
            status=status,
            entity_id=entity_id,
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
                entity_type="task",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="task",
            constraint=msg[:200],
        )
