"""Service Layer — Application Services for Personal Memory Hub.

This package implements the five core application services:
- MemoryService: Memory lifecycle (capture, import, merge, archive, restore)
- QueryService: All read capabilities (retrieval, search, browse, projection, analytics)
- EntityService: Identity management (create, resolve, merge, alias, relationships)
- ReflectionService: Memory evolution (reflect, consolidate, summarize, evaluate)
- TaskService: Task execution orchestration (submit, track, retry, cancel)

Architecture:
  Entry (D5) → Service (D3) → Engine (D4) → Repository (D2) → Database

Per D3 Frozen: Service contracts are stable. Changes require ADR.
"""

from __future__ import annotations

__all__ = [
    "base",
    "memory_service",
    "query_service",
    "entity_service",
    "reflection_service",
    "task_service",
    "exceptions",
    "dto",
]
