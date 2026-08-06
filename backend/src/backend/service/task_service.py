"""TaskService — Task Execution Orchestration Service.

Implements the task execution orchestration layer:
- Task submission: Register new tasks
- Task status: Query task lifecycle status
- Task retry: Retry failed tasks
- Task cancellation: Cancel pending/running tasks
- Task health: Monitor task runtime health

Per D3.6 and 10_6 Implementation Design:
- TaskService owns execution lifecycle/scheduling/retry/context/history
- TaskService NEVER makes business decisions
- Execution Scope concept: immutable during execution
- Scheduling determines when, not what
- Periodic creates new Tasks
- Retry preserves Execution Scope
- Incremental Processing Principle
- One Task = One Transaction
- Failure Isolation: each task failure is isolated
- Completed Task Immutability: completed tasks are never modified

Architecture:
    TaskService (D3) → TaskRepository (D2) → Database
    TaskService (D3) ← Task Runtime (D4) — execution polling/dispatching
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.repository.exceptions import RepositoryError
from backend.service.base import BaseService
from backend.service.dto import (
    TaskStatus,
    TaskStatusResult,
    TaskSubmissionResult,
)
from backend.service.exceptions import (
    NotFoundError,
    TaskAlreadyRunningError,
    TaskCancellationError,
    TaskNotFoundError,
    ValidationError,
)

if TYPE_CHECKING:
    from backend.repository.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskService(BaseService):
    """Application service for task execution orchestration.

    Coordinates task lifecycle: submit, track, retry, cancel.

    Stateless singleton managed by DI container.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
    ) -> None:
        """Initialize TaskService with required repositories.

        Args:
            task_repo: Repository for Task CRUD.
        """
        super().__init__("TaskService")
        self._task_repo = task_repo

    def _generate_id(self) -> UUID:
        """Generate a unique ID."""
        from backend.shared.infrastructure.uuid import generate_uuid
        return generate_uuid()

    # ------------------------------------------------------------------
    # Task Submission
    # ------------------------------------------------------------------

    async def submit(
        self,
        *,
        workspace_id: UUID,
        task_type: str,
        payload: dict[str, Any],
        entity_id: UUID | None = None,
        max_retries: int = 3,
        debounce_key: str | None = None,
    ) -> TaskSubmissionResult:
        """Submit a new task for execution.

        Creates a task record with status='pending'.
        The Task Runtime (D4) is responsible for polling and dispatching.

        Per IR-011 (Direct Job Dispatch): MemoryService calls this
        directly to request background work.

        Args:
            workspace_id: Workspace scope.
            task_type: Task type (INGESTION, REFLECTION, ACTIVATION, ARCHIVE).
            payload: Task payload (implementation-specific parameters).
            entity_id: Optional associated entity.
            max_retries: Maximum retry attempts (default 3).
            debounce_key: Optional deduplication key.

        Returns:
            TaskSubmissionResult with the task ID.

        Raises:
            ValidationError: If task_type is invalid.
        """
        self._validate_workspace_id(workspace_id)

        valid_types = ("INGESTION", "REFLECTION", "ACTIVATION", "ARCHIVE")
        if task_type not in valid_types:
            raise ValidationError(
                f"Invalid task_type: {task_type}. Must be one of {valid_types}",
                field="task_type",
            )

        from backend.shared.domain.memory_models import Task as TaskModel

        task = TaskModel(
            id=self._generate_id(),
            workspace_id=workspace_id,
            entity_id=entity_id,
            task_type=task_type,
            status="pending",
            evidence_driven=True,
            debounce_key=debounce_key,
            max_retries=max_retries,
            retry_count=0,
            payload=payload,
        )

        try:
            task_id = await self._task_repo.create(task)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        self._log_operation(
            "submit_task",
            workspace_id=workspace_id,
            entity_id=task_id,
            level="debug",
            task_type=task_type,
        )

        return TaskSubmissionResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
        )

    # ------------------------------------------------------------------
    # Task Status
    # ------------------------------------------------------------------

    async def get_task(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
    ) -> TaskStatusResult:
        """Get the status of a task.

        Args:
            workspace_id: Workspace scope.
            task_id: The task UUID.

        Returns:
            TaskStatusResult with current status and metadata.

        Raises:
            TaskNotFoundError: If task not found.
        """
        self._validate_workspace_id(workspace_id)

        task = await self._task_repo.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(
                f"Task {task_id} not found",
                resource_type="task",
                resource_id=str(task_id),
            )

        return TaskStatusResult(
            task_id=task.id,
            task_type=getattr(task, "task_type", ""),
            status=TaskStatus(getattr(task, "status", "pending")),
            retry_count=getattr(task, "retry_count", 0),
            max_retries=getattr(task, "max_retries", 3),
            created_at=str(getattr(task, "created_at", "")),
            updated_at=str(getattr(task, "updated_at", "")),
            completed_at=str(getattr(task, "completed_at", "")) if getattr(task, "completed_at", None) else None,
            error_message=getattr(task, "error_message", None),
        )

    async def list_tasks(
        self,
        *,
        workspace_id: UUID,
        task_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskStatusResult]:
        """List tasks with optional filters.

        Args:
            workspace_id: Workspace scope.
            task_type: Optional task type filter.
            status: Optional status filter.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            List of TaskStatusResult objects.
        """
        self._validate_workspace_id(workspace_id)

        tasks = await self._task_repo.find_by_workspace(
            workspace_id=workspace_id,
            task_types=[task_type] if task_type else None,
            status=status,
            limit=limit,
            offset=offset,
        )

        return [
            TaskStatusResult(
                task_id=t.id,
                task_type=getattr(t, "task_type", ""),
                status=TaskStatus(getattr(t, "status", "pending")),
                retry_count=getattr(t, "retry_count", 0),
                max_retries=getattr(t, "max_retries", 3),
                created_at=str(getattr(t, "created_at", "")),
                updated_at=str(getattr(t, "updated_at", "")),
                completed_at=str(getattr(t, "completed_at", "")) if getattr(t, "completed_at", None) else None,
            )
            for t in tasks
        ]

    # ------------------------------------------------------------------
    # Task Retry
    # ------------------------------------------------------------------

    async def retry_task(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
    ) -> TaskSubmissionResult:
        """Retry a failed task.

        Resets retry count and sets status back to 'pending'.
        Preserves the original execution scope (payload).

        Per D3.6: Retry preserves Execution Scope.

        Args:
            workspace_id: Workspace scope.
            task_id: The task UUID.

        Returns:
            TaskSubmissionResult with the task ID.

        Raises:
            NotFoundError: If task not found.
            TaskAlreadyRunningError: If task is currently running.
        """
        self._validate_workspace_id(workspace_id)

        task = await self._task_repo.find_by_id(task_id)
        if task is None:
            raise NotFoundError(
                f"Task {task_id} not found",
                resource_type="task",
                resource_id=str(task_id),
            )

        current_status = getattr(task, "status", "pending")
        if current_status == "running":
            raise TaskAlreadyRunningError(
                f"Task {task_id} is already running",
            )

        # Reset task for retry

        task.retry_count = getattr(task, "retry_count", 0) + 1
        task.status = "pending"

        try:
            await self._task_repo.update(task)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        return TaskSubmissionResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
        )

    # ------------------------------------------------------------------
    # Task Cancellation
    # ------------------------------------------------------------------

    async def cancel_task(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
    ) -> TaskStatusResult:
        """Cancel a pending or running task.

        Args:
            workspace_id: Workspace scope.
            task_id: The task UUID.

        Returns:
            TaskStatusResult with CANCELLED status.

        Raises:
            NotFoundError: If task not found.
            TaskCancellationError: If task cannot be cancelled
                (e.g., already completed or failed).
        """
        self._validate_workspace_id(workspace_id)

        task = await self._task_repo.find_by_id(task_id)
        if task is None:
            raise NotFoundError(
                f"Task {task_id} not found",
                resource_type="task",
                resource_id=str(task_id),
            )

        current_status = getattr(task, "status", "pending")
        if current_status in ("completed", "failed", "dead_letter"):
            raise TaskCancellationError(
                f"Cannot cancel task in status '{current_status}'",
            )

        # Mark as cancelled

        task.status = "cancelled"

        try:
            await self._task_repo.update(task)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        return TaskStatusResult(
            task_id=task_id,
            task_type=getattr(task, "task_type", ""),
            status=TaskStatus.CANCELLED,
        )

    # ------------------------------------------------------------------
    # Task Health
    # ------------------------------------------------------------------

    async def get_health(self, workspace_id: UUID) -> dict[str, Any]:
        """Get task runtime health status.

        Returns counts of tasks by status for monitoring.

        Args:
            workspace_id: Workspace scope.

        Returns:
            Dict with health metrics.
        """
        self._validate_workspace_id(workspace_id)

        all_tasks = await self._task_repo.find_by_workspace(
            workspace_id=workspace_id,
        )

        health = {
            "total": len(all_tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "dead_letter": 0,
            "cancelled": 0,
        }

        for task in all_tasks:
            status = getattr(task, "status", "pending")
            if status in health:
                health[status] += 1

        return health
