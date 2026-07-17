"""Engine Layer — Domain Engines for Personal Memory Hub.

This package implements the six Domain Engines defined in D4:
- EntityEngine: Entity identity resolution, canonical semantics, evolution
- MemoryEngine: Memory domain rules, evidence integrity, lifecycle
- RelationshipEngine: Relationship graph analysis, link validation
- ReflectionEngine: Reflection algorithms, proposal generation
- SearchEngine: Search algorithms, relevance ranking
- ProjectionEngine: Projection algorithms, view assembly

Architecture:
    Entry (D5) → Service (D3) → Engine (D4) → Repository (D2) → Database

Per D4 Frozen: Engine contracts are stable. Changes require ADR.
"""

from __future__ import annotations

__all__ = [
    "base",
    "entity_engine",
    "memory_engine",
    "relationship_engine",
    "reflection_engine",
    "search_engine",
    "projection_engine",
]
