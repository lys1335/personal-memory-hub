"""Repository Layer — Shared Infrastructure (D2.1) + Memory Domain (D2.2).

This module provides the shared persistence foundation for all Repository
implementations in the Personal Memory Hub.

D2.1 Shared Infrastructure:
- BaseRepository: Abstract base with standard CRUD, transaction support,
  workspace isolation, and exception mapping
- QueryRepository: Read-only base for complex multi-table queries
- Pagination: CursorPage and OffsetPage for paginated result sets
- Exceptions: Domain-specific repository exceptions
- Types: Shared typing definitions (PrimaryKey, FilterMap, etc.)
- Workspace: WorkspaceIsolationMixin for multi-tenancy enforcement

D2.2 Memory Domain Repositories:
- MemoryNodeRepository: CRUD for memory_nodes + memory_evidences
- EvidenceRepository: Immutable evidence CRUD
- ArchiveRepository: CRUD for archives + tag_links (archive)
- TagRepository: CRUD for tags + tag_links (many-to-many)
- MemoryQueryRepository: Read-only complex queries (multi-table JOIN)

Boundary Rules (per G-013, G-014, 10_9 §5.2):
- Repository Layer may depend only on: SQLAlchemy, Database infrastructure, Shared infrastructure
- Repository Layer must NOT depend on: Service Layer, Engine Layer, other Repository implementations

Per 10_9 §6: This infrastructure supports all 12 Repositories:
9 Core Repositories (Entity, MemoryNode, Evidence, Relationship,
 VectorDoc, Archive, Tag, Task, Candidate) +
3 QueryRepositories (MemoryQuery, EntityQuery, VectorQuery).
"""

from __future__ import annotations

# D2.1 Shared Infrastructure
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

# D2.2 Memory Domain Repositories
from backend.repository.archive_repository import ArchiveRepository
from backend.repository.evidence_repository import EvidenceRepository
from backend.repository.memory_node_repository import MemoryNodeRepository
from backend.repository.memory_query_repository import MemoryQueryRepository
from backend.repository.tag_repository import TagRepository

__all__ = [
    # D2.1 Shared Infrastructure — Base Classes
    "BaseRepository",
    "QueryRepository",
    "WorkspaceIsolationMixin",
    # D2.1 Shared Infrastructure — Pagination
    "Page",
    "OffsetPage",
    "CursorPage",
    # D2.1 Shared Infrastructure — Exceptions
    "RepositoryError",
    "NotFoundError",
    "DuplicateError",
    "IntegrityError",
    "WorkspaceIsolationError",
    "ReadOnlyError",
    # D2.1 Shared Infrastructure — Types
    "PrimaryKey",
    "FilterValue",
    "FilterMap",
    "SortSpec",
    "WorkspaceScoped",
    "get_primary_key_column",
    "get_table_columns",
    # D2.2 Memory Domain Repositories
    "MemoryNodeRepository",
    "EvidenceRepository",
    "ArchiveRepository",
    "TagRepository",
    "MemoryQueryRepository",
]
