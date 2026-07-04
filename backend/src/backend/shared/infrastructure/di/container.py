"""Dependency Injection container.

Provides a simple, lightweight DI container for wiring infrastructure
components (settings, logger, engine, session factory).

D1 only: Registers infrastructure singletons.
D2+: Domain services and engines are registered here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.shared.infrastructure.config.settings import (
    AppSettings,
    get_settings,
)
from backend.shared.infrastructure.database.engine import (
    Base,
    get_async_session,
    get_engine,
    get_session_factory,
)
from backend.shared.infrastructure.logging import get_logger


class Container:
    """Simple DI container for singleton resolution.

    Components are registered by class/type and resolved via
    ``container.resolve(MyClass)``.  D1 registers:
    - ``AppSettings``  → settings singleton
    - ``type(logger)`` → logger (bound to module name)
    - ``Base``         → SQLAlchemy declarative base
    - ``engine``       → async SQLAlchemy engine
    - ``session_factory`` → async session factory
    - ``get_async_session`` → async session generator
    """

    def __init__(self) -> None:
        self._registry: dict[type, Callable[[], Any]] = {}
        self._instances: dict[type, Any] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, cls: type, resolver: Callable[[], Any]) -> None:
        """Register a resolver for a given class/type.

        Args:
            cls: The type that will be resolved.
            resolver: A callable that returns the instance.
        """
        self._registry[cls] = resolver

    def resolve(self, cls: type) -> Any:
        """Resolve a registered component.

        Returns the cached instance if already resolved, otherwise
        calls the resolver and caches the result.

        Args:
            cls: The type to resolve.

        Raises:
            KeyError: If no resolver is registered for ``cls``.
        """
        if cls not in self._instances:
            if cls not in self._registry:
                raise KeyError(f"No resolver registered for {cls.__name__}")
            self._instances[cls] = self._registry[cls]()
        return self._instances[cls]

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def resolve_all(self, *classes: type) -> tuple[Any, ...]:
        """Resolve multiple components at once."""
        return tuple(self.resolve(cls) for cls in classes)


# ---------------------------------------------------------------------------
# Global container — initialized with D1 infrastructure
# ---------------------------------------------------------------------------

_container: Container | None = None


def get_container() -> Container:
    """Return the global DI container (singleton).

    Creates and populates the container on first call with all D1
    infrastructure components.
    """
    global _container
    if _container is None:
        _container = Container()
        # Register D1 infrastructure singletons
        _container.register(AppSettings, get_settings)
        _container.register(type(get_logger()), lambda: get_logger("backend"))
        _container.register(type(Base), lambda: Base)
        _container.register(type(get_engine()), get_engine)
        _container.register(type(get_session_factory()), get_session_factory)
        _container.register(type(get_async_session()), get_async_session)
    return _container


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

__all__ = ["Container", "get_container"]
