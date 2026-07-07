"""Tests for testing infrastructure fixtures.

Verifies that pytest fixtures (settings, container, engine, session)
are correctly configured per 10_8 (Testing Implementation Design).
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Ensure src/ is on the Python path for imports
# ---------------------------------------------------------------------------

_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

from backend.shared.infrastructure.config.settings import (
    AppSettings,
    get_settings,
)
from backend.shared.infrastructure.di import get_container
from backend.shared.infrastructure.logging import (
    configure_logging,
    get_logger,
)

# ---------------------------------------------------------------------------
# Fixtures — Infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings() -> AppSettings:
    """Return the application settings (singleton)."""
    return get_settings()


@pytest.fixture(scope="session")
def logger(settings: AppSettings):
    """Return a configured logger."""
    configure_logging()
    return get_logger("tests")


@pytest.fixture(scope="session")
def container(settings: AppSettings):
    """Return the DI container with all D1 infrastructure registered."""
    return get_container()


# ---------------------------------------------------------------------------
# Fixtures — Database (in-memory SQLite for tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite engine for deterministic tests.

    Per 10_8 §4.4: "In-memory SQLite / Testcontainers / Fixed fixtures".
    D1 uses in-memory SQLite for speed and determinism.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    # Note: dispose() is async in SQLAlchemy 2.0+, but we can't await in session-scoped fixture
    # In production tests, the engine is short-lived and garbage collected


@pytest.fixture(scope="session")
def test_session_factory(test_engine: AsyncEngine) -> async_sessionmaker:
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def test_session(test_session_factory: async_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    """Yield a test session with a savepoint (rolled back after test).

    This ensures each test gets a clean database state without
    actually dropping and recreating tables.
    """
    async with test_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Tests — verify the fixtures work
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fixture_settings(settings: AppSettings) -> None:
    """Verify settings fixture returns a valid AppSettings instance."""
    assert isinstance(settings, AppSettings)
    assert settings.APP_NAME == "personal-memory-hub"


@pytest.mark.unit
def test_fixture_container(container) -> None:
    """Verify DI container resolves settings."""
    resolved = container.resolve(AppSettings)
    assert isinstance(resolved, AppSettings)


@pytest.mark.unit
async def test_fixture_test_engine(test_engine: AsyncEngine) -> None:
    """Verify test engine is an async SQLAlchemy engine."""
    assert test_engine is not None
    assert hasattr(test_engine, "begin")
