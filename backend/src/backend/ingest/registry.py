"""Import Registry — Adapter registration and lookup.

Provides a centralized registry for import adapters.
Adapters are registered by ImportSource enum value.

Usage:
    registry = ImportRegistry()
    registry.register(OpenWebUIAdapter())
    adapter = registry.get_adapter(ImportSource.OPEN_WEBUI)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.ingest.base import BaseImportAdapter, ImportSource


class ImportRegistry:
    """Registry for import adapters.

    Stateless singleton — no mutable instance state beyond the
    internal mapping (which is set at construction time).
    """

    def __init__(self) -> None:
        self._adapters: dict[ImportSource, BaseImportAdapter] = {}

    def register(self, adapter: BaseImportAdapter) -> None:
        """Register an adapter.

        Args:
            adapter: The adapter to register.

        Raises:
            ValueError: If an adapter for this source is already registered.
        """
        if adapter.source in self._adapters:
            raise ValueError(
                f"Adapter already registered for {adapter.source.value}"
            )
        self._adapters[adapter.source] = adapter

    def get_adapter(self, source: ImportSource) -> BaseImportAdapter | None:
        """Get adapter by source type.

        Args:
            source: The import source type.

        Returns:
            The registered adapter, or None if not found.
        """
        return self._adapters.get(source)

    def list_sources(self) -> list[ImportSource]:
        """List all registered source types.

        Returns:
            List of registered ImportSource values.
        """
        return list(self._adapters.keys())

    def has_adapter(self, source: ImportSource) -> bool:
        """Check if an adapter is registered for a source.

        Args:
            source: The import source type.

        Returns:
            True if an adapter is registered.
        """
        return source in self._adapters


# ---------------------------------------------------------------------------
# Default Registry (pre-registers known adapters)
# ---------------------------------------------------------------------------


def create_default_registry() -> ImportRegistry:
    """Create an ImportRegistry with all currently available adapters.

    This function should be updated whenever new adapters are added.

    Returns:
        A fully configured ImportRegistry.
    """
    registry = ImportRegistry()

    # Register Open WebUI adapter
    from backend.ingest.adapters.open_webui import OpenWebUIAdapter
    registry.register(OpenWebUIAdapter())

    return registry
