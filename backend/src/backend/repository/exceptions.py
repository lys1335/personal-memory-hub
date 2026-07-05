"""Repository exceptions.

Domain-specific exceptions raised by Repository implementations.
Maps database-level errors to application-level domain exceptions.

Per G-013 (Repository Is Persistence Only): exceptions are purely about
persistence failures — no business logic is encoded here.
"""

from __future__ import annotations


class RepositoryError(Exception):
    """Base exception for all repository-level errors."""

    def __init__(self, message: str, *, entity_type: str | None = None, entity_id: str | None = None) -> None:
        super().__init__(message)
        self.entity_type = entity_type
        self.entity_id = entity_id


class NotFoundError(RepositoryError):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        super().__init__(
            f"{entity_type} with id {entity_id!r} not found",
            entity_type=entity_type,
            entity_id=entity_id,
        )


class DuplicateError(RepositoryError):
    """Raised when a uniqueness constraint is violated."""

    def __init__(self, entity_type: str, constraint: str, details: str | None = None) -> None:
        msg = f"Duplicate {entity_type}: constraint '{constraint}' violated"
        if details:
            msg += f" — {details}"
        super().__init__(msg, entity_type=entity_type)


class IntegrityError(RepositoryError):
    """Raised when a domain integrity constraint is violated."""

    def __init__(self, entity_type: str, constraint: str, message: str | None = None) -> None:
        msg = f"Integrity violation on {entity_type}: {constraint}"
        if message:
            msg += f" — {message}"
        super().__init__(msg, entity_type=entity_type)


class WorkspaceIsolationError(RepositoryError):
    """Raised when workspace isolation boundary is breached."""

    def __init__(self, workspace_id: str, requested_workspace: str | None = None) -> None:
        super().__init__(
            f"Workspace isolation breach: current={workspace_id!r}, requested={requested_workspace!r}",
            entity_type="Workspace",
        )


class ReadOnlyError(RepositoryError):
    """Raised when a write operation is attempted on a read-only repository."""

    def __init__(self, repository_name: str) -> None:
        super().__init__(
            f"Cannot write to read-only repository: {repository_name}",
            entity_type="QueryRepository",
        )
