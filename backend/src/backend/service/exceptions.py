"""Service Layer exceptions.

Provides domain exceptions that bridge Repository errors and Entry-layer
errors. All exceptions are entry-safe (no internal details leaked).

Per D3.7 Error Handling & DTO Models:
- Exception types are version-controlled architecture contracts
- Each layer translates once into the next layer's exception model
- Preserve root cause through exception chaining
- Entry-safe error codes for external consumption

Exception Hierarchy:
    DomainError (base)
    ├── ValidationError
    ├── NotFoundError
    ├── DuplicateError
    ├── DomainIntegrityError
    ├── TransactionError
    ├── ServiceUnavailableError
    └── ReflectionError
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Base: DomainError
# ---------------------------------------------------------------------------


class MemoryHubError(Exception):
    """Base exception for all MemoryHub errors.

    All service-level exceptions inherit from this class.
    Entry Layer translates MemoryHubError subclasses into protocol-specific
    error responses.
    """


class DomainError(MemoryHubError):
    """Base exception for all domain-level errors.

    All service-level exceptions inherit from this class.
    Entry Layer translates DomainError subclasses into protocol-specific
    error responses.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._default_error_code()
        self.details = details or {}
        self.__cause__ = cause

    def _default_error_code(self) -> str:
        """Derive a default error code from the class name."""
        return self.__class__.__name__.replace("Error", "").upper()

    def to_entry_safe_dict(self) -> dict[str, Any]:
        """Convert to an entry-safe dictionary for external consumption.

        Only includes error_code, message, and details.
        Does NOT include stack traces or internal implementation details.
        """
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------


class ValidationError(DomainError):
    """Raised when input validation fails.

    Error code: VALIDATION_ERROR
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if field:
            extra["field"] = field
        if value is not None:
            extra["value"] = str(value)
        if details:
            extra.update(details)
        super().__init__(message, details=extra)


class InvalidInputError(ValidationError):
    """Raised when a command contains invalid input data."""

    def _default_error_code(self) -> str:
        return "INVALID_INPUT"


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing."""

    def _default_error_code(self) -> str:
        return "MISSING_REQUIRED_FIELD"


# ---------------------------------------------------------------------------
# Not Found Errors
# ---------------------------------------------------------------------------


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist.

    Error code: NOT_FOUND
    """

    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if resource_type:
            extra["resource_type"] = resource_type
        if resource_id:
            extra["resource_id"] = resource_id
        super().__init__(message, details=extra)

    def _default_error_code(self) -> str:
        return "NOT_FOUND"


# ---------------------------------------------------------------------------
# Conflict / Duplicate Errors
# ---------------------------------------------------------------------------


class DuplicateError(DomainError):
    """Raised when a uniqueness constraint is violated.

    Error code: DUPLICATE
    """

    def __init__(
        self,
        message: str,
        *,
        entity_type: str | None = None,
        constraint: str | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if entity_type:
            extra["entity_type"] = entity_type
        if constraint:
            extra["constraint"] = constraint
        super().__init__(message, details=extra)

    def _default_error_code(self) -> str:
        return "DUPLICATE"


# ---------------------------------------------------------------------------
# Integrity Errors
# ---------------------------------------------------------------------------


class DomainIntegrityError(DomainError):
    """Raised when a domain invariant is violated.

    Error code: DOMAIN_INTEGRITY
    """

    def __init__(
        self,
        message: str,
        *,
        invariant: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if invariant:
            extra["invariant"] = invariant
        if details:
            extra.update(details)
        super().__init__(message, details=extra)

    def _default_error_code(self) -> str:
        return "DOMAIN_INTEGRITY"


# ---------------------------------------------------------------------------
# Transaction Errors
# ---------------------------------------------------------------------------


class TransactionError(DomainError):
    """Raised when a transaction fails.

    Error code: TRANSACTION_ERROR
    """

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if operation:
            extra["operation"] = operation
        super().__init__(message, cause=cause, details=extra)

    def _default_error_code(self) -> str:
        return "TRANSACTION_ERROR"


# ---------------------------------------------------------------------------
# Service Availability Errors
# ---------------------------------------------------------------------------


class ServiceUnavailableError(DomainError):
    """Raised when a required service is unavailable.

    Error code: SERVICE_UNAVAILABLE
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if service_name:
            extra["service_name"] = service_name
        super().__init__(message, details=extra)

    def _default_error_code(self) -> str:
        return "SERVICE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Reflection Errors
# ---------------------------------------------------------------------------


class ReflectionError(DomainError):
    """Raised when reflection execution fails.

    Error code: REFLECTION_ERROR
    """

    def __init__(
        self,
        message: str,
        *,
        scope: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if scope:
            extra["scope"] = scope
        if details:
            extra.update(details)
        super().__init__(message, details=extra)

    def _default_error_code(self) -> str:
        return "REFLECTION_ERROR"


# ---------------------------------------------------------------------------
# Import Errors
# ---------------------------------------------------------------------------


class ImportError(DomainError):
    """Raised when an import operation fails.

    Error code: IMPORT_ERROR
    """

    def __init__(
        self,
        message: str,
        *,
        job_id: str | None = None,
        item_index: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if job_id:
            extra["job_id"] = job_id
        if item_index is not None:
            extra["item_index"] = item_index
        if details:
            extra.update(details)
        super().__init__(message, details=extra)

    def _default_error_code(self) -> str:
        return "IMPORT_ERROR"


# ---------------------------------------------------------------------------
# Task Errors
# ---------------------------------------------------------------------------


class TaskNotFoundError(NotFoundError):
    """Raised when a requested task does not exist."""

    def _default_error_code(self) -> str:
        return "TASK_NOT_FOUND"


class TaskAlreadyRunningError(DomainIntegrityError):
    """Raised when attempting to operate on an already-running task."""

    def _default_error_code(self) -> str:
        return "TASK_ALREADY_RUNNING"


class TaskCancellationError(DomainError):
    """Raised when task cancellation fails."""

    def _default_error_code(self) -> str:
        return "TASK_CANCEL_ERROR"
