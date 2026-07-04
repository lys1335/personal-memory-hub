"""Alembic environment configuration.

Connects Alembic to the Personal Memory Hub's SQLAlchemy engine and
declarative base.  Reads DATABASE_URL from the .env file (via pydantic-
settings) so that migrations use the same connection as the application.
"""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Ensure src/ is on the Python path so we can import backend modules
# ---------------------------------------------------------------------------
_src = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(_src))

# ---------------------------------------------------------------------------
# Import application settings and database base
# ---------------------------------------------------------------------------
from backend.shared.infrastructure.config.settings import get_settings  # noqa: E402
from backend.shared.infrastructure.database.engine import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic CLI config (alembic.ini)
# ---------------------------------------------------------------------------
alembic_cfg = context.config

# If alembic.ini does not specify sqlalchemy.url, fall back to settings.
url = alembic_cfg.get_main_option("sqlalchemy.url")
if not url:
    s = get_settings()
    alembic_cfg.set_main_option("sqlalchemy.url", s.DATABASE_URL)

# Interpret the config file for Python logging.
if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

# Target metadata — Base includes all declarative models.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="memory_hub",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations against the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="memory_hub",
        render_as_batch=True,  # allows batch ops for SQLite
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = async_engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async)."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point — called by alembic CLI
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
