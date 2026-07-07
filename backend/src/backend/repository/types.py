"""Shared typing definitions for the Repository layer.

Provides generic types, type aliases, and common data structures used
across all Repository implementations.

Per 10_9 §5.1: These types are consumed by all 12 Repositories.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

#: Primary key type — UUIDv7 throughout the project.
PrimaryKey = UUID

#: Filter value — can be a single value or a list for IN queries.
FilterValue = Any | list[Any]

#: Filter map — column name to filter value(s).
FilterMap = dict[str, FilterValue]

#: Sort specification: (column_name, ascending).
SortSpec = tuple[str, bool]


# ---------------------------------------------------------------------------
# Protocol: Entity with workspace isolation
# ---------------------------------------------------------------------------

@runtime_checkable
class WorkspaceScoped(Protocol):
    """Protocol for entities that carry a workspace_id for multi-tenancy."""

    workspace_id: UUID


# ---------------------------------------------------------------------------
# Utility: Column extraction
# ---------------------------------------------------------------------------

def get_table_columns(model_class: type[DeclarativeBase]) -> dict[str, Column]:
    """Extract column names and Column objects from a SQLAlchemy model class.

    Args:
        model_class: A SQLAlchemy declarative model class.

    Returns:
        Dict mapping column names to Column objects.
    """
    return {col.name: col for col in model_class.__table__.columns}  # type: ignore[attr-defined]


def get_primary_key_column(model_class: type[DeclarativeBase]) -> Column | None:
    """Get the primary key column from a SQLAlchemy model class.

    Args:
        model_class: A SQLAlchemy declarative model class.

    Returns:
        The primary key Column, or None if not found.
    """
    if hasattr(model_class, "__table__"):
        pk_cols = list(model_class.__table__.primary_key.columns)  # type: ignore[attr-defined]
        if pk_cols:
            return pk_cols[0]
    return None
