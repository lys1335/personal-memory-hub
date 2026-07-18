"""Domain Engine Layer — Shared Infrastructure.

Per D4_Domain_Engine_Plan:
- Engine is a Stable Facade: public contract is stable, internal composition is private
- Stateless Engine: no mutable instance state
- Domain Result, not Protocol Result: returns domain-level results
- No Cross-Engine Calls: Engine A never calls Engine B
- Composition Over Inheritance: internal composition uses composition

This module provides:
- EngineBase: shared infrastructure for all Domain Engines
- DomainResult: result wrapper for engine computations
- DomainError: error taxonomy for engine-level failures
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type variables
# ---------------------------------------------------------------------------

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Domain Result
# ---------------------------------------------------------------------------


class DomainResult(Generic[T]):
    """Result returned by Engine public methods.

    Per D4 Principle 4 (Domain Result, Not Protocol Result):
    Engine returns domain-level results, not HTTP/status codes or DTOs.

    Attributes:
        success: Whether the operation succeeded.
        data: The domain result data (only valid if success=True).
        error: The domain error (only valid if success=False).
        metadata: Additional context (e.g., invariant violations).
    """

    __slots__ = ("_data", "_error", "_metadata", "_success")

    def __init__(
        self,
        success: bool,
        data: T | None = None,
        error: DomainError | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._success = success
        self._data = data
        self._error = error
        self._metadata = metadata or {}

    @property
    def success(self) -> bool:
        """Return True if the operation succeeded."""
        return self._success

    @property
    def data(self) -> T | None:
        """Return the domain result data. May be None."""
        return self._data

    @property
    def error(self) -> DomainError | None:
        """Return the domain error if failed. May be None."""
        return self._error

    @property
    def metadata(self) -> dict[str, Any]:
        """Return additional metadata about the result."""
        return self._metadata

    @classmethod
    def ok(cls, data: T) -> DomainResult[T]:
        """Create a successful DomainResult."""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: DomainError, metadata: dict[str, Any] | None = None) -> DomainResult[T]:
        """Create a failed DomainResult."""
        return cls(success=False, error=error, metadata=metadata or {})

    def is_ok(self) -> bool:
        """Return True if this result is successful."""
        return self._success

    def is_fail(self) -> bool:
        """Return True if this result is a failure."""
        return not self._success

    def unwrap(self) -> T:
        """Return the data, raising if this is a failure.

        Returns:
            The domain result data.

        Raises:
            DomainError: If this result represents a failure.
        """
        if self._error:
            raise self._error
        if self._data is None:
            raise DomainError(
                "Expected data but result is None",
                error_code="ENGINE_NO_DATA",
            )
        return self._data

    def unwrap_or(self, default: T) -> T:
        """Return the data if present, otherwise the default.

        Args:
            default: Default value to return on failure.

        Returns:
            The data or the default.
        """
        return self._data if self._data is not None else default

    def unwrap_or_raise(self, msg: str = "Operation failed") -> T:
        """Raise if this result is a failure, otherwise return data.

        Args:
            msg: Custom error message prefix.

        Returns:
            The domain result data.

        Raises:
            DomainError: If this result represents a failure.
        """
        if self._error:
            raise DomainError(
                f"{msg}: {self._error.message}",
                error_code=self._error.error_code,
                details=self._error.details,
                cause=self._error,
            )
        if self._data is None:
            raise DomainError(
                f"{msg}: expected data but got None",
                error_code="ENGINE_NO_DATA",
            )
        return self._data


# ---------------------------------------------------------------------------
# Domain Error
# ---------------------------------------------------------------------------


class DomainError(Exception):
    """Base exception for all Engine-level domain errors.

    Per D3.7 Error Taxonomy: Engine errors are classified per the
    frozen domain exception model. Each Engine error maps to a
    specific error code that Service can translate.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        invariant: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._default_error_code()
        self.invariant = invariant
        self.details = details or {}
        self.__cause__ = cause

    def _default_error_code(self) -> str:
        """Derive a default error code from the class name."""
        return self.__class__.__name__.replace("Error", "").upper()

    def to_entry_safe_dict(self) -> dict[str, Any]:
        """Convert to an entry-safe dictionary for external consumption.

        Returns:
            Dict with code, message, details, and invariant info.
        """
        result = {
            "code": self.error_code,
            "message": self.message,
            "details": self.details,
        }
        if self.invariant:
            result["invariant"] = self.invariant
        return result


class DomainInvariantViolation(DomainError):
    """Raised when a domain invariant is violated.

    Error code: DOMAIN_INVARIANT_VIOLATION
    """

    def __init__(
        self,
        message: str,
        *,
        invariant: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code="DOMAIN_INVARIANT_VIOLATION",
            invariant=invariant,
            details=details,
        )


class DomainRuleViolation(DomainError):
    """Raised when a domain rule is violated.

    Error code: DOMAIN_RULE_VIOLATION
    """

    def __init__(
        self,
        message: str,
        *,
        rule: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if rule:
            extra["rule"] = rule
        if details:
            extra.update(details)
        super().__init__(
            message,
            error_code="DOMAIN_RULE_VIOLATION",
            details=extra,
        )


class DomainAlgorithmError(DomainError):
    """Raised when a domain algorithm produces an unexpected result.

    Error code: DOMAIN_ALGORITHM_ERROR
    """

    def __init__(
        self,
        message: str,
        *,
        algorithm: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if algorithm:
            extra["algorithm"] = algorithm
        if details:
            extra.update(details)
        super().__init__(
            message,
            error_code="DOMAIN_ALGORITHM_ERROR",
            details=extra,
        )


class DomainConsistencyError(DomainError):
    """Raised when domain consistency check fails.

    Error code: DOMAIN_CONSISTENCY_ERROR
    """

    def __init__(
        self,
        message: str,
        *,
        consistency_check: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if consistency_check:
            extra["consistency_check"] = consistency_check
        if details:
            extra.update(details)
        super().__init__(
            message,
            error_code="DOMAIN_CONSISTENCY_ERROR",
            details=extra,
        )


# ---------------------------------------------------------------------------
# EngineBase
# ---------------------------------------------------------------------------


class EngineBase(ABC):
    """Base class for all Domain Engines.

    Per D4 Principles:
    1. Engine is a Stable Facade — internal composition is private
    2. Stateless Engine — no mutable instance state
    3. Domain Result, not Protocol Result — returns DomainResult
    4. No Cross-Engine Calls — never calls other Engines
    5. Composition Over Inheritance — internal use composition
    6. Domain Consistency, not Business Consistency — invariant enforcement
    7. Algorithm Isolation — domain algorithms isolated within Engine
    8. Transaction-Agnostic — no transaction awareness

    Subclasses MUST NOT:
    - Add mutable instance state
    - Call other Engines
    - Manage transactions
    - Return protocol-specific types
    - Perform workflow orchestration

    Subclasses SHOULD:
    - Use private internal Components, Policies, Strategies
    - Return DomainResult for all public methods
    - Enforce domain invariants
    - Be deterministic (same input → same result)
    """

    def __init__(self, name: str) -> None:
        """Initialize the engine with a name for logging.

        Args:
            name: Engine name, used as logger name prefix.
        """
        self._name = name
        self._log = logging.getLogger(f"backend.engine.{name}")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_domain_rule(
        self,
        rule: str,
        *,
        context: dict[str, Any] | None = None,
        level: str = "info",
    ) -> None:
        """Log a domain rule evaluation.

        Args:
            rule: Domain rule name or identifier.
            context: Optional context dict for structured logging.
            level: Log level.
        """
        extra = {"rule": rule}
        if context:
            extra.update(context)
        log_method = getattr(self._log, level, self._log.info)
        log_method("Domain rule: %s", rule, extra=extra)

    def _log_invariant_check(
        self,
        invariant: str,
        passed: bool,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log an invariant check result.

        Args:
            invariant: Invariant name.
            passed: Whether the invariant held.
            context: Optional context dict.
        """
        extra = {"invariant": invariant, "passed": passed}
        if context:
            extra.update(context)
        level = "warning" if not passed else "debug"
        self._log.log(
            getattr(logging, level.upper(), logging.DEBUG),
            "Invariant check: %s — %s",
            invariant,
            "PASSED" if passed else "VIOLATED",
            extra=extra,
        )

    # ------------------------------------------------------------------
    # Domain Result Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def domain_ok(data: Any) -> DomainResult[Any]:
        """Create a successful DomainResult.

        Args:
            data: Domain result data.

        Returns:
            A DomainResult with success=True.
        """
        return DomainResult.ok(data)

    @staticmethod
    def domain_fail(error: DomainError) -> DomainResult[Any]:
        """Create a failed DomainResult.

        Args:
            error: The domain error.

        Returns:
            A DomainResult with success=False.
        """
        return DomainResult.fail(error)

    # ------------------------------------------------------------------
    # Invariant Enforcement Helper
    # ------------------------------------------------------------------

    def _verify_invariant(
        self,
        condition: bool,
        invariant: str,
        *,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> DomainResult[Any]:
        """Verify a domain invariant and return DomainResult.

        If the invariant fails, returns a failed DomainResult with
        DomainInvariantViolation.

        Args:
            condition: Whether the invariant holds.
            invariant: Invariant name for error reporting.
            message: Optional custom error message.
            context: Optional context for the check.

        Returns:
            DomainResult.ok(None) if passed, DomainResult.fail() if violated.
        """
        if not condition:
            msg = message or f"Invariant violated: {invariant}"
            error = DomainInvariantViolation(
                msg,
                invariant=invariant,
                details=context or {},
            )
            self._log_invariant_check(invariant, False, context=context)
            return DomainResult.fail(error)

        self._log_invariant_check(invariant, True, context=context)
        return DomainResult.ok(None)

    # ------------------------------------------------------------------
    # Engine Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Return the engine name."""
        return self._name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self._name!r})>"
