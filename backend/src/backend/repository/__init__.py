"""Repository Layer — Shared Infrastructure (D2.1).

This module provides the shared persistence foundation for all Repository
implementations in the Personal Memory Hub.

Components:
- BaseRepository: Abstract base with standard CRUD, transaction support,
  workspace isolation, and exception mapping
- QueryRepository: Read-only base for complex multi-table queries
- Pagination: CursorPage and OffsetPage for paginated result sets
- Exceptions: Domain-specific repository exceptions
- Types: Shared typing definitions (PrimaryKey, FilterMap, etc.)
- Workspace: WorkspaceIsolationMixin for multi-tenancy enforcement

Boundary Rules (per G-013, G-014, 10_9 §5.2):
- Repository Layer may depend only on: SQLAlchemy, Database infrastructure, Shared infrastructure
- Repository Layer must NOT depend on: Service Layer, Engine Layer, other Repository implementations

Per 10_9 §6: This infrastructure supports all 12 Repositories:
9 Core Repositories (Entity, MemoryNode, Evidence, Relationship,
 VectorDoc, Archive, Tag, Task, Candidate) +
3 QueryRepositories (MemoryQuery, EntityQuery, VectorQuery).
"""

from __future__ import annotations

from backend.repository.base import BaseRepository
from backend.repository.exceptions import (
    DuplicateError,
    IntegrityError,
    NotFoundError,
    ReadOnlyError,
    RepositoryError,
    WorkspaceIsolationError,
)
from backend.repository.pagination import CursorPage, OffsetPage, Page
from backend.repository.query import QueryRepository
from backend.repository.types import (
    FilterMap,
    FilterValue,
    PrimaryKey,
    SortSpec,
    WorkspaceScoped,
    get_primary_key_column,
    get_table_columns,
)
from backend.repository.workspace import WorkspaceIsolationMixin

__all__ = [
    # Base classes
    "BaseRepository",
    "QueryRepository",
    "WorkspaceIsolationMixin",
    # Pagination
    "Page",
    "OffsetPage",
    "CursorPage",
    # Exceptions
    "RepositoryError",
    "NotFoundError",
    "DuplicateError",
    "IntegrityError",
    "WorkspaceIsolationError",
    "ReadOnlyError",
    # Types
    "PrimaryKey",
    "FilterValue",
    "FilterMap",
    "SortSpec",
    "WorkspaceScoped",
    "get_primary_key_column",
    "get_table_columns",
]
