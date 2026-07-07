"""Workspace isolation mixin.

Ensures all Repository operations are scoped to a single workspace.
Every Repository inherits this mixin to enforce multi-tenancy at the
persistence layer.

Per 10_9 §5.1: Workspace isolation is a shared infrastructure requirement
for all 12 Repositories.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select

from backend.repository.exceptions import WorkspaceIsolationError

if TYPE_CHECKING:
    from backend.repository.types import FilterMap

T = TypeVar("T")


class WorkspaceIsolationMixin(Generic[T]):
    """Mixin that enforces workspace_id scoping on all queries.

    When a repository implements this mixin, every query automatically
    appends ``WHERE workspace_id = :workspace_id`` unless explicitly
    overridden (e.g. for seed data like workspace itself).

    Usage::

        class EntityRepository(WorkspaceIsolationMixin[Entity], BaseRepository[Entity]):
            ...
    """

    _workspace_id: UUID | None

    def set_workspace(self, workspace_id: UUID) -> None:
        """Set the workspace scope for this repository instance.

        Args:
            workspace_id: The workspace UUID to scope queries to.

        Raises:
            WorkspaceIsolationError: If workspace_id is None or empty.
        """
        if workspace_id is None:
            raise WorkspaceIsolationError(
                workspace_id="",
                requested_workspace="any",
            )
        self._workspace_id = workspace_id

    def get_workspace(self) -> UUID | None:
        """Return the current workspace scope, or None if not set."""
        return getattr(self, "_workspace_id", None)

    def _apply_workspace_filter(self, stmt: Select) -> Select:
        """Apply workspace_id WHERE clause to a SELECT statement.

        Args:
            stmt: The SELECT statement to filter.

        Returns:
            The filtered SELECT statement.

        Raises:
            WorkspaceIsolationError: If no workspace is set.
        """
        if not hasattr(self, "_workspace_id") or self._workspace_id is None:
            raise WorkspaceIsolationError(
                workspace_id="",
                requested_workspace="any",
            )
        return stmt.where(self.__class__.__table__.c.workspace_id == self._workspace_id)  # type: ignore[attr-defined]

    def _ensure_workspace(self) -> UUID:
        """Ensure a workspace is set and return it, raising if not.

        Returns:
            The workspace UUID.

        Raises:
            WorkspaceIsolationError: If no workspace is set.
        """
        ws = getattr(self, "_workspace_id", None)
        if ws is None:
            raise WorkspaceIsolationError(
                workspace_id="",
                requested_workspace="any",
            )
        return ws

    @staticmethod
    def build_workspace_filter(workspace_id: UUID) -> FilterMap:
        """Build a filter map with workspace_id for use in find_all().

        Args:
            workspace_id: The workspace to filter by.

        Returns:
            A filter map containing the workspace_id.
        """
        return {"workspace_id": workspace_id}
