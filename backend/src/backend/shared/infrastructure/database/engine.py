"""SQLAlchemy engine and session factories.

Provides:
- ``get_engine()`` — async SQLAlchemy engine
- ``get_session_factory()`` — scoped session factory
- ``get_async_session()`` — async session generator (for DI)
- ``Base`` — declarative base for all ORM models

D1 only: Base is empty. Domain models are added in D2.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.shared.infrastructure.config.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    All D2+ models will inherit from this class.
    Table names are derived from the class name (snake_case).
    """

    pass


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_engine: Any = None


def get_engine() -> Any:
    """Return the global async engine (singleton).

    Creates the engine on first call.  The engine reads DATABASE_URL
    from settings and enables echo if DATABASE_ECHO is True.
    """
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_async_engine(
            s.DATABASE_URL,
            echo=s.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        # Enable pgvector extension on connect (for PostgreSQL)
        @event.listens_for(_engine.sync_engine, "connect")
        def _enable_pgvector(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.close()
    return _engine


# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------

_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the global async session factory (singleton).

    Uses scoped session with expire_on_commit=False for performance.
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# Async session generator (for use outside DI, e.g. scripts)
# ---------------------------------------------------------------------------


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session and close it afterwards.

    Usage::

        async for session in get_async_session():
            ...

    Note: This is a convenience generator.  In production code, prefer
    injecting the session factory via the DI container (D1.6).
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session


__all__ = ["Base", "get_async_session", "get_engine", "get_session_factory"]
