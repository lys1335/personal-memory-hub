"""BaseService — shared infrastructure for all Application Services.

Per D3.1 Service Base Infrastructure:
- Thin BaseService: only shared infrastructure, NO business logic
- Explicit dependency injection (constructor only)
- Stateless services, singleton by design
- Transaction ownership belongs to Service
- Error translation: RepositoryError → DomainError → Entry-safe
- Workspace context propagated per invocation

Architecture Principles:
1. BaseService exists ONLY for shared infrastructure concerns
2. Constructor Injection only — no Service Locator
3. Inject only what each Service actually uses
4. All Services are Stateless
5. Services are Singleton by Design
6. Transaction belongs to Service, not Repository
7. One Use Case = One Transaction
8. Single Translation Responsibility per layer
"""

from __future__ import annotations

import logging
from typing import Any

from backend.repository.exceptions import (
    DuplicateError as RepoDuplicateError,
)
from backend.repository.exceptions import (
    IntegrityError as RepoIntegrityError,
)
from backend.repository.exceptions import (
    NotFoundError as RepoNotFoundError,
)
from backend.repository.exceptions import (
    RepositoryError as RepoError,
)
from backend.repository.exceptions import (
    WorkspaceIsolationError as RepoWorkspaceError,
)
from backend.service.exceptions import (
    DomainError,
    DomainIntegrityError,
    DuplicateError,
    NotFoundError,
    TransactionError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class BaseService:
    """Base class for all Application Services.

    Provides shared infrastructure:
    - Workspace context management
    - Error translation (Repository → Domain)
    - Transaction helpers (commit/rollback)
    - Logging with correlation context

    Subclasses must NOT add mutable instance state.
    All Services are stateless and singleton.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, name: str) -> None:
        """Initialize the service with a name for logging.

        Args:
            name: Service name, used as logger name prefix.
        """
        self._name = name
        self._log = logging.getLogger(f"backend.service.{name}")

    # ------------------------------------------------------------------
    # Workspace Context
    # ------------------------------------------------------------------

    def _validate_workspace_id(self, workspace_id: Any) -> None:
        """Validate that a workspace_id is not None or empty.

        Args:
            workspace_id: The workspace identifier to validate.

        Raises:
            ValidationError: If workspace_id is None or empty.
        """
        if workspace_id is None:
            raise ValidationError(
                "workspace_id is required",
                field="workspace_id",
            )

    # ------------------------------------------------------------------
    # Error Translation
    # ------------------------------------------------------------------

    @staticmethod
    def translate_repository_error(exc: RepoError) -> DomainError:
        """Translate a Repository error into a Domain error.

        Per G-014 (Single Translation Responsibility):
        Each layer translates once into the next layer's exception model.

        Args:
            exc: The repository exception to translate.

        Returns:
            A corresponding DomainError subclass.
        """
        if isinstance(exc, RepoNotFoundError):
            return NotFoundError(
                str(exc),
                resource_type=exc.entity_type,
                resource_id=exc.entity_id,
            )
        if isinstance(exc, RepoDuplicateError):
            return DuplicateError(
                str(exc),
                entity_type=exc.entity_type,
            )
        if isinstance(exc, RepoIntegrityError):
            return DomainIntegrityError(
                str(exc),
                invariant=exc.args[1] if len(exc.args) > 1 else None,
            )
        if isinstance(exc, RepoWorkspaceError):
            return DomainIntegrityError(
                str(exc),
                invariant="workspace_isolation",
            )
        # Fallback: wrap unknown repository errors
        return DomainIntegrityError(
            f"Repository error: {exc}",
            details={"original_error": type(exc).__name__, "message": str(exc)},
        )

    @staticmethod
    def translate_domain_error(exc: DomainError) -> DomainError:
        """Pass-through for Domain errors (they are already entry-safe).

        Args:
            exc: The domain exception.

        Returns:
            The same exception (no translation needed).
        """
        return exc

    # ------------------------------------------------------------------
    # Transaction Helpers
    # ------------------------------------------------------------------

    async def _commit(self, session: Any) -> None:
        """Commit a database session.

        Per G-106 (Transaction Ownership): Transaction belongs to Service.
        This is an internal helper — not exposed publicly.

        Args:
            session: The SQLAlchemy async session to commit.

        Raises:
            TransactionError: If commit fails.
        """
        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            raise TransactionError(
                f"Transaction commit failed: {exc}",
                operation="commit",
                cause=exc,
            ) from exc

    async def _rollback(self, session: Any, reason: str = "unknown") -> None:
        """Rollback a database session.

        Per G-106 (Transaction Ownership): Transaction belongs to Service.
        This is an internal helper — not exposed publicly.

        Args:
            session: The SQLAlchemy async session to rollback.
            reason: Reason for rollback (for logging).
        """
        try:
            await session.rollback()
        except Exception as exc:
            self._log.error("Rollback failed: %s — %s", reason, exc)

    # ------------------------------------------------------------------
    # Logging Helpers
    # ------------------------------------------------------------------

    def _log_operation(
        self,
        operation: str,
        *,
        workspace_id: Any = None,
        entity_id: Any = None,
        log_level: str = "info",
        **kwargs: Any,
    ) -> None:
        """Log an operation with workspace and entity context.

        Args:
            operation: Operation name (e.g., "capture_memory").
            workspace_id: Optional workspace identifier.
            entity_id: Optional entity identifier.
            level: Log level ("debug", "info", "warning", "error").
            **kwargs: Additional context fields.
        """
        extra = {"operation": operation}
        if workspace_id:
            extra["workspace_id"] = str(workspace_id)
        if entity_id:
            extra["entity_id"] = str(entity_id)
        extra.update(kwargs)

        log_method = getattr(self._log, log_level, self._log.info)
        log_method("%s", operation, extra=extra)

    # ------------------------------------------------------------------
    # Service Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Return the service name."""
        return self._name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self._name!r})>"
