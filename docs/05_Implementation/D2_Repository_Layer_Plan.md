# Personal Memory Hub — D2 Repository Layer Plan

> **Version**: 1.0
> **Date**: 2026-07-07
> **Phase**: Phase D — Document-Driven Implementation
> **Stage**: D2 — Repository Layer
> **Status**: Planning (awaiting human approval)
> **Author**: System Architecture Group

---

## 1. Purpose

### 1.1 Objectives

Implement the complete Repository Layer for the Personal Memory Hub project. D2 establishes the data persistence layer that provides:

- 9 CRUD repositories implementing generic base operations for all aggregates
- 3 Query repositories providing complex read operations (multi-table joins, graph traversal, vector similarity)
- Shared infrastructure: `BaseRepository[T]`, `QueryRepository[T]`, pagination models, workspace isolation, type utilities
- Full type safety via mypy strict mode compliance
- Comprehensive test coverage (98 tests) using in-memory SQLite fixtures
- Repository freeze — no further changes to repository contracts without ADR approval

### 1.2 Scope

D2 covers **repository layer implementation only**:

- 9 CRUD repositories (Entity, MemoryNode, Evidence, Relationship, VectorDoc, Archive, Tag, Task, Candidate)
- 3 Query repositories (MemoryQuery, EntityQuery, VectorQuery)
- Shared infrastructure (base classes, pagination, workspace isolation, exceptions, type utilities)
- ORM model definitions (database table mappings)
- Database migration files (DDL execution)
- Repository test suite (98 tests)
- Release blocker documentation (native pgvector support)
- Architecture debt documentation (contract vs base signature alignment)

### 1.3 Out of Scope

D2 explicitly excludes:

- **Service Layer** — No service implementations (D3)
- **Engine Layer** — No domain engine implementations (D4)
- **API Endpoints** — No REST, MCP, or CLI adapters (D5)
- **Embedding Generation** — External LLM/Embedding API calls are deferred (D3+)
- **Production Deployment** — CD pipeline is intentionally deferred
- **Performance Optimization** — No load testing or benchmarking

---

## 2. Deliverables

The following outputs are expected upon D2 completion:

| # | Deliverable | Location | Description |
|---|-------------|----------|-------------|
| 1 | ORM Models | `backend/src/backend/repository/models/` | SQLAlchemy declarative models for all aggregates |
| 2 | BaseRepository | `backend/src/backend/repository/base.py` | Generic CRUD base with async operations |
| 3 | QueryRepository | `backend/src/backend/repository/query.py` | Read-only base for complex queries |
| 4 | Pagination | `backend/src/backend/repository/pagination.py` | OffsetPage and CursorPage models |
| 5 | Exceptions | `backend/src/backend/repository/exceptions.py` | NotFoundError, DuplicateError, ReadOnlyError |
| 6 | Workspace | `backend/src/backend/repository/workspace.py` | Multi-tenant workspace isolation mixin |
| 7 | Types | `backend/src/backend/repository/types.py` | Column type utilities |
| 8 | EntityRepository | `backend/src/backend/repository/entity_repository.py` | Entity/Area/Workspace/UserProfile CRUD |
| 9 | MemoryNodeRepository | `backend/src/backend/repository/memory_node_repository.py` | MemoryNode/Evidence CRUD |
| 10 | EvidenceRepository | `backend/src/backend/repository/evidence_repository.py` | Evidence CRUD |
| 11 | RelationshipRepository | `backend/src/backend/repository/relationship_repository.py` | Relationship/MemoryRelationship CRUD |
| 12 | VectorDocRepository | `backend/src/backend/repository/vector_doc_repository.py` | VectorDoc CRUD |
| 13 | ArchiveRepository | `backend/src/backend/repository/archive_repository.py` | Archive CRUD |
| 14 | TagRepository | `backend/src/backend/repository/tag_repository.py` | Tag CRUD |
| 15 | TaskRepository | `backend/src/backend/repository/task_repository.py` | Task CRUD |
| 16 | CandidateRepository | `backend/src/backend/repository/candidate_repository.py` | Candidate CRUD |
| 17 | MemoryQueryRepository | `backend/src/backend/repository/memory_query_repository.py` | Memory complex queries |
| 18 | EntityQueryRepository | `backend/src/backend/repository/entity_query_repository.py` | Entity graph queries |
| 19 | VectorQueryRepository | `backend/src/backend/repository/vector_query_repository.py` | Vector similarity queries |
| 20 | Migration Files | `backend/alembic/versions/` | DDL from 09 (Database Physical Design) |
| 21 | Test Suite | `backend/tests/` | 98 tests across 4 test files |
| 22 | Repository Inventory | `docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md` | Implementation inventory with Release Blocker and Architecture Debt |
| 23 | Verification Guide | `docs/06_Guides/D2_Repository_Verification_Guide.md` | Step-by-step verification instructions |

---

## 3. Work Breakdown

### D2.1 ORM Model Definitions

**Purpose**: Define SQLAlchemy declarative models for all aggregates per 09 (Database Physical Design).

**Dependencies**: D1 (engine, session factory, Base class available).

**Expected outputs**:

- `backend/src/backend/repository/models/entity.py` — Entity, Area, Workspace, UserProfile models
- `backend/src/backend/repository/models/memory.py` — MemoryNode, MemoryEvidence models
- `backend/src/backend/repository/models/evidence.py` — Evidence model
- `backend/src/backend/repository/models/relationship.py` — Relationship, MemoryRelationship models
- `backend/src/backend/repository/models/vector.py` — VectorDoc model
- `backend/src/backend/repository/models/archive.py` — Archive, ArchiveSource models
- `backend/src/backend/repository/models/tag.py` — Tag, TagLink models
- `backend/src/backend/repository/models/task.py` — Task model
- `backend/src/backend/repository/models/candidate.py` — Candidate model

**Constraints**:
- All models use UUIDv7 primary keys (ENG-015)
- All models include `created_at`, `updated_at`, `deleted_at` timestamps
- All models include `workspace_id` for multi-tenancy
- Table names are plural, snake_case (09 §9.3)
- Schema is `memory_hub` (09 §9.3)

**Verification**: Models are importable. `Base.metadata` contains all table definitions.

---

### D2.2 Shared Infrastructure — BaseRepository

**Purpose**: Implement the generic CRUD base class that all repositories inherit from.

**Dependencies**: D2.1 (models defined), D1 (engine/session available).

**Expected outputs**:

- `backend/src/backend/repository/base.py` — `BaseRepository[T]` class with:
  - `async def create(self, obj: T) -> T` — Insert new entity
  - `async def update(self, obj_id: UUID, data: dict) -> T` — Partial update
  - `async def soft_delete(self, obj_id: UUID) -> T` — Set deleted_at
  - `async def delete(self, obj_id: UUID) -> None` — Hard delete
  - `async def find_by_id(self, obj_id: UUID) -> Optional[T]` — Single entity lookup
  - `async def find_all(self, *, filters: FilterSpec, order_by: Optional[str] = None) -> Sequence[T]` — List with filters
  - `async def find_page(self, *, page: int, page_size: int, ...) -> OffsetPage[T]` — Paginated list
  - `async def count(self, *, filters: FilterSpec) -> int` — Count with filters
  - `async def exists(self, *, filters: FilterSpec) -> bool` — Existence check
  - `async def commit(self) -> None` — Flush and commit session
  - `async def rollback(self) -> None` — Rollback transaction
  - `async def refresh(self, obj: T) -> T` — Refresh from database

**Engineering decisions referenced**:
- G-013: Repository Is Persistence Only
- 10_1 §5: Repository Layer design
- ENG-001: Memory Hub = Infrastructure, Not Business Logic

**Verification**: `BaseRepository` passes all generic CRUD tests. Works with any model type.

---

### D2.3 Shared Infrastructure — QueryRepository

**Purpose**: Implement the read-only base class for complex query repositories.

**Dependencies**: D2.2 (BaseRepository exists).

**Expected outputs**:

- `backend/src/backend/repository/query.py` — `QueryRepository[T]` class with:
  - Inherits from `BaseRepository[T]`
  - Overrides write methods to raise `ReadOnlyError`
  - Provides read-only query methods: `find`, `find_page`, `count`, `get_entity_graph`
  - Supports complex filter specifications

**Constraints**:
- Write operations MUST raise `ReadOnlyError`
- Query methods use raw SQL or complex SQLAlchemy constructs
- No mutation allowed through this base

**Verification**: Attempting `create()` on a `QueryRepository` subclass raises `ReadOnlyError`.

---

### D2.4 Pagination and Type Utilities

**Purpose**: Provide pagination models and column type utilities shared across repositories.

**Dependencies**: D1 (base types available).

**Expected outputs**:

- `backend/src/backend/repository/pagination.py` — `OffsetPage[T]`, `CursorPage[T]` dataclasses
- `backend/src/backend/repository/types.py` — `get_table_columns()`, `get_primary_key_column()` utilities
- `backend/src/backend/repository/workspace.py` — `WorkspaceFilterMixin` for multi-tenant isolation
- `backend/src/backend/repository/exceptions.py` — `NotFoundError`, `DuplicateError`, `ReadOnlyError`, `IntegrityError`

**Verification**: Pagination models serialize to dict. Workspace filter correctly adds `workspace_id` condition.

---

### D2.5 CRUD Repositories — Entity Domain

**Purpose**: Implement repositories for the Entity domain aggregates.

**Dependencies**: D2.2 (BaseRepository), D2.1 (models defined).

**Expected outputs**:

#### EntityRepository (`entity_repository.py`)
- Aggregates: Entity, Area, Workspace, UserProfile
- Methods: `create_entity`, `find_by_id`, `find_by_workspace`, `find_by_name`, `find_by_alias`, `find_by_area`, `find_by_parent`, `create_area`, `find_area_by_name`, `create_user_profile`, `find_user_profile_by_external`, `find_page`
- Constraints: Soft delete prohibited (callers must use explicit delete)

#### RelationshipRepository (`relationship_repository.py`)
- Aggregates: Relationship, MemoryRelationship
- Methods: `find_by_source`, `find_by_source_type_filter`, `find_by_target`, `find_by_type`, `find_connections`, `create_memory_relationship`, `find_memory_by_source`, `find_memory_by_target`, `find_page`
- Constraints: Bidirectional relationship lookup support

**Engineering decisions referenced**:
- 09 §9.4: Entity domain tables
- 09 §9.5: Relationship tables
- G-013: Repository Is Persistence Only

**Verification**: 26 tests pass (16 Entity + 10 Relationship).

---

### D2.6 CRUD Repositories — Memory Domain

**Purpose**: Implement repositories for the Memory, Evidence, Archive, and Tag aggregates.

**Dependencies**: D2.2 (BaseRepository), D2.1 (models defined).

**Expected outputs**:

#### MemoryNodeRepository (`memory_node_repository.py`)
- Aggregates: MemoryNode, MemoryEvidence
- Methods: `create_memory`, `update_memory`, `find_by_entity`, `find_by_level`, `find_by_status`, `find_active_by_workspace`, `find_page`, `find_with_evidence_chain`
- Constraints: Update and soft delete prohibited (memory nodes are append-only)

#### EvidenceRepository (`evidence_repository.py`)
- Aggregates: Evidence
- Methods: `create_evidence`, `find_by_workspace`, `find_by_source`, `find_page`
- Constraints: Update and soft delete prohibited (evidence is immutable once created)

#### ArchiveRepository (`archive_repository.py`)
- Aggregates: Archive, ArchiveSource
- Methods: `create_archive`, `find_by_type`, `find_by_period`, `find_page`
- Constraints: Tag links for archive target_type handled here

#### TagRepository (`tag_repository.py`)
- Aggregates: Tag, TagLink
- Methods: `create_tag`, `find_by_workspace`, `find_by_name`, `find_page`
- Constraints: TagLink resolution for all target types

**Verification**: 23 tests pass (6 Evidence + 9 Memory + 4 Archive + 4 Tag).

---

### D2.7 CRUD Repositories — Other Domains

**Purpose**: Implement repositories for Vector, Task, and Candidate aggregates.

**Dependencies**: D2.2 (BaseRepository), D2.1 (models defined).

**Expected outputs**:

#### VectorDocRepository (`vector_doc_repository.py`)
- Aggregate: VectorDoc
- Methods: `create_vector_doc`, `find_by_workspace`, `find_by_document_id`, `find_page`
- Constraints: Vector embeddings stored as TEXT (JSON) until pgvector migration

#### TaskRepository (`task_repository.py`)
- Aggregate: Task
- Methods: `create_task`, `find_by_workspace`, `find_by_status`, `find_page`
- Constraints: Task lifecycle management (pending, running, completed, failed)

#### CandidateRepository (`candidate_repository.py`)
- Aggregate: Candidate
- Methods: `create_candidate`, `find_by_workspace`, `find_by_status`, `find_page`
- Constraints: Reflection candidate management

**Verification**: All repositories pass CRUD tests.

---

### D2.8 Query Repositories

**Purpose**: Implement read-only repositories for complex queries.

**Dependencies**: D2.5, D2.6, D2.7 (CRUD repositories exist for model references).

**Expected outputs**:

#### MemoryQueryRepository (`memory_query_repository.py`)
- Aggregate: MemoryNode (query-only)
- Methods: `find_with_evidence_linked`, `find_by_entity_and_workspace`, `multi_table_join_query`, `find_page`
- Purpose: Complex multi-table JOIN queries that exceed single-repository scope

#### EntityQueryRepository (`entity_query_repository.py`)
- Aggregate: Entity (query-only)
- Methods: `find_by_canonical_name`, `find_by_alias`, `find_by_type`, `count_by_type`, `find_related_entities_outgoing`, `find_related_entities_incoming`, `find_relationships_for_entity`, `find_filtered_by_type`, `find_filtered_by_min_relationship_count`, `get_entity_graph`, `get_entity_count`, `find_page`
- Purpose: Graph traversal via relationships

#### VectorQueryRepository (`vector_query_repository.py`)
- Aggregate: Vector (query-only)
- Methods: `similarity_search` (deferred — requires pgvector), `filter_by_source_type`, `filter_by_entity`, `hybrid_search`
- Purpose: Vector similarity search (deferred until pgvector available)
- **Release Blocker**: Native pgvector support required before MVP/Beta

**Engineering decisions referenced**:
- 10_1 §5.3: QueryRepository pattern (read-only, complex queries)
- G-013: Query repositories contain only query logic

**Verification**: 39 tests pass (13 EntityQuery + remaining MemoryQuery). VectorQueryRepository is read-only with deferred similarity_search.

---

### D2.9 Database Migration Files

**Purpose**: Create Alembic migration files that execute the DDL defined in 09 (Database Physical Design).

**Dependencies**: D2.1 (ORM models defined).

**Expected outputs**:

- `backend/alembic/versions/XXXX_ddl_initial_schema.py` — Initial migration containing:
  - `memory_hub` schema creation
  - All table definitions from 09
  - Indexes (including GIN for JSONB columns)
  - Foreign key constraints
  - Default values and NOT NULL constraints

**Constraints**:
- Migration must be reversible (downgrade to empty)
- Follows naming conventions from 09 §9.3
- Uses `uuid_extensions` for UUIDv7 generation

**Verification**: `alembic upgrade head` creates all tables. `alembic downgrade base` drops all tables.

---

### D2.10 Test Suite Implementation

**Purpose**: Implement comprehensive tests for all repositories and infrastructure.

**Dependencies**: D2.2–D2.8 (repositories implemented).

**Expected outputs**:

- `tests/test_repository_infrastructure.py` — 29 tests:
  - BaseRepository CRUD operations
  - QueryRepository read-only enforcement
  - Workspace isolation
  - Pagination (OffsetPage, CursorPage)
  - Error handling (NotFound, Duplicate, Integrity, ReadOnly)
  - Transaction management (commit, rollback, refresh)
  - Type utilities (get_table_columns, get_primary_key_column, build_workspace_filter)

- `tests/test_entity_domain_repositories.py` — 39 tests:
  - TestEntityRepository (16 tests)
  - TestRelationshipRepository (10 tests)
  - TestEntityQueryRepository (13 tests)

- `tests/test_memory_domain_repositories.py` — 25 tests:
  - TestEvidenceRepository (6 tests)
  - TestMemoryNodeRepository (9 tests)
  - TestArchiveRepository (4 tests)
  - TestTagRepository (4 tests)
  - TestImportBoundaries (2 tests — verify no service/engine imports)

- `tests/test_fixtures.py` — 3 tests:
  - DI container, settings, test engine fixtures

- `tests/test_smoke.py` — 1 test:
  - Basic smoke test

**Total: 98 tests**

**Verification**: `pytest tests/ -v` reports 98 passed, 0 failed.

---

### D2.11 Release Blocker Documentation

**Purpose**: Document the Release Blocker for native pgvector support.

**Dependencies**: D2.7 (VectorDocRepository implemented with TEXT storage).

**Expected outputs**:

- Section 9 in `docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md`:
  - Current String embedding storage approach
  - pgvector dependency requirement
  - ORM migration to `Vector(1536)`
  - PostgreSQL vector extension
  - HNSW / IVFFlat indexes
  - Native vector operators (cosine distance, `<->`)

**Verification**: All 6 required items documented in the Release Blocker section.

---

### D2.12 Architecture Debt Documentation

**Purpose**: Document the Architecture Debt for repository contract vs BaseRepository signature alignment.

**Dependencies**: D2.8 (Query repositories implemented).

**Expected outputs**:

- Section 10 in `docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md`:
  - Title: "Repository Contract vs BaseRepository Signature Alignment"
  - Status: Deferred
  - Priority: Low
  - Suggested Milestone: Post-MVP Architecture Review
  - Type: Design Debt (not a bug)
  - Description: `find_page` method override signatures in query repositories may diverge from BaseRepository

**Verification**: Architecture Debt section present with all metadata fields.

---

### D2.13 Documentation Updates

**Purpose**: Update project documentation to reflect D2 completion.

**Dependencies**: D2.1–D2.12 (all implementation complete).

**Expected outputs**:

- `docs/05_Implementation/README.md` — Updated with D2 status
- `docs/INDEX.md` — Updated with D2 cross-references
- `README.md` (root) — Updated with Phase D status
- `docs/06_Guides/D2_Repository_Verification_Guide.md` — Verification guide (EN)
- `docs/06_Guides/zh-CN/D2_Repository_Verification_Guide.md` — Verification guide (CN)

**Verification**: All documentation links resolve. Index is consistent.

---

## 4. Definition of Done

D2 is complete when **all** of the following criteria are met:

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 1 | All 12 repositories implemented | File existence check (Section 3.3 of Verification Guide) |
| 2 | `ruff check src/ tests/` passes zero violations | `uv run ruff check src/ tests/` → "All checks passed!" |
| 3 | `mypy src/` passes in strict mode | `uv run mypy src/` → "Success: no issues found in 36 source files" |
| 4 | All 98 tests pass | `uv run pytest tests/ -v` → "98 passed" |
| 5 | CRUD repos have write operations | grep for `async def create/soft_delete` in each CRUD repo |
| 6 | Query repos are read-only | Verify no `create/update/soft_delete` in query repos |
| 7 | No cross-layer dependencies | Verify no imports from `backend.service`, `backend.engine`, or `get_engine()` calls |
| 8 | Release Blocker documented | Check `10_9_Repository_Inventory.md` §9 |
| 9 | Architecture Debt documented | Check `10_9_Repository_Inventory.md` §10 |
| 10 | Migration files executable | `alembic upgrade head` succeeds (requires running PostgreSQL) |
| 11 | Documentation updated | README, INDEX, Implementation README reflect D2 status |
| 12 | Repository freeze confirmed | `10_9_Repository_Inventory.md` documents freeze policy |

---

## 5. Risks

### 5.1 ORM Model Complexity

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Too many relationships between models causing circular import issues | Define models in separate files. Use `TYPE_CHECKING` imports for type hints. Use string references in relationships (`relationship("Entity")` instead of `relationship(Entity)`). |
| Impact | High | **Severity: Medium** |
| Trigger | Circular import error during model import | Review model dependency graph before implementation. |

### 5.2 Query Repository Over-Scope

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Query repositories grow to include business logic, violating G-013 | Keep query methods focused on data retrieval only. No transformation, aggregation, or business rule evaluation. |
| Impact | Medium | **Severity: Medium** |
| Trigger | Query method body exceeds 50 lines | Refactor: move business logic to Service layer (D3). |

### 5.3 pgvector Integration Delay

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Native pgvector support not available, delaying MVP | Document as Release Blocker. Use TEXT storage as interim solution. Vector similarity search is deferred. |
| Impact | High | **Severity: Low** (deferred, not blocking D2) |
| Trigger | pgvector extension not installed in target PostgreSQL | D2 stores vectors as TEXT. Migration to `Vector(1536)` is a D3+ task. |

### 5.4 Test Coverage Gaps

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Insufficient test coverage for edge cases (workspace isolation, soft delete prohibition) | Each repository has explicit tests for boundary conditions. Import boundary tests verify architecture compliance. |
| Impact | Medium | **Severity: Low** |
| Trigger | `pytest` reveals untested paths | Add failing tests first, then fix. |

### 5.5 Migration Reversibility

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Migration downgrade fails, preventing rollbacks | Test `alembic downgrade base` immediately after migration creation. Keep migration simple — one `op.create_table` per table. |
| Impact | High | **Severity: Medium** |
| Trigger | `alembic downgrade` raises error | Simplify migration. Avoid complex SQL in downgrade. |

### 5.6 Document-Driven Drift

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Repository implementation diverges from 09 (Database Physical Design) or 10_1 (Repository Layer) | Each repository traces back to specific document sections. Verification Guide checks architecture boundaries. |
| Impact | High | **Severity: Medium** |
| Trigger | Repository contract differs from 10_1 §5 | Review against referenced documents before committing. |

---

## 6. Documentation Updates

The following documentation should be created or updated during D2 implementation:

| # | Document | Action | Reference |
|---|----------|--------|-----------|
| 1 | `docs/05_Implementation/README.md` | Update: Add D2 completion status, milestone mapping | 11 §4 |
| 2 | `docs/INDEX.md` | Update: Add D2 cross-references, mark D2 as in-progress | INDEX.md §Current Progress |
| 3 | `README.md` (root) | Update: Phase D status (D2 in progress) | 11 §5.1 |
| 4 | `docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md` | Create: Repository implementation inventory with Release Blocker and Architecture Debt | 11 §5.2 |
| 5 | `docs/06_Guides/D2_Repository_Verification_Guide.md` | Create: Step-by-step verification guide (EN) | 13 §5 |
| 6 | `docs/06_Guides/zh-CN/D2_Repository_Verification_Guide.md` | Create: Step-by-step verification guide (CN) | 13 §5 |
| 7 | `docs/07_Review/12_Architecture_Decisions.md` | Update: Add ADRs for D2 decisions (pagination strategy, query pattern) | 11 §10 |

**Principle**: Documentation updates are part of D2 deliverables, not afterthoughts. Each document change should be traceable to a specific engineering decision or architectural requirement.

---

## 7. Handoff to D3 (Service Layer)

Once D2 is complete, D3 (Service Layer) can safely assume:

### 7.1 Infrastructure Readiness

| Item | D2 Provides | D3 Assumes |
|------|-------------|------------|
| **Repositories** | 12 fully tested repositories | Repositories are stable and will not change without ADR |
| **Base classes** | `BaseRepository[T]`, `QueryRepository[T]` | Repositories can be instantiated via DI container |
| **Pagination** | `OffsetPage`, `CursorPage` models | Services receive paginated results |
| **Exceptions** | `NotFoundError`, `DuplicateError`, `ReadOnlyError` | Services catch and translate repository exceptions |
| **Workspace isolation** | `WorkspaceFilterMixin` | Services pass `workspace_id` through repository context |

### 7.2 Data Access Readiness

| Item | D2 Provides | D3 Assumes |
|------|-------------|------------|
| **CRUD operations** | All 9 CRUD repos have create/update/soft_delete | Services call repository methods directly |
| **Query operations** | 3 Query repos for complex reads | Services compose queries via QueryRepository |
| **Transaction management** | `commit()`, `rollback()`, `refresh()` | Services manage transactions at service level |
| **Multi-tenancy** | Workspace filter applied at repository level | Services set workspace context before calling repositories |

### 7.3 What D3 Must NOT Assume

| Item | Reason |
|------|--------|
| Repository contracts are mutable | Repository Layer is frozen after D2 |
| QueryRepository can write | Query repositories are read-only |
| VectorQueryRepository has similarity_search | Deferred until pgvector available |
| Embedding generation exists | External LLM/Embedding API is D3+ responsibility |

---

## 8. Engineering Principles Applied

During D2 implementation, the following principles govern all decisions:

| Principle | Source | Application in D2 |
|-----------|--------|-------------------|
| **Memory Hub = Infrastructure** | ENG-001 | Repositories are persistence-only; no business logic |
| **Document-Driven Design** | 11 §13.1 | Each repository traces to 10_1 §5 and 09 |
| **No Layer Skipping** | G-014 | D2 implements Repository only; no Service or Engine |
| **Repository Is Persistence Only** | G-013 | CRUD + Query logic only; no transformation or business rules |
| **Deterministic-by-Default** | 10_8 §5.1 | All 98 tests are deterministic (in-memory SQLite) |
| **One Aggregate = One Repository** | 10_1 §5.2 | Clear mapping between aggregates and repositories |
| **Query Repositories Are Read-Only** | 10_1 §5.3 | QueryRepository overrides write methods to raise ReadOnlyError |
| **Continuous Buildability** | 11 §Engineering Principles | Main branch is buildable after every D2 sub-task |
| **Human Decides, AI Executes** | 11 §13.2 | This plan requires human approval before coding |

---

## 9. Task Dependencies

```
D2.1 ORM Models ──────────────────────────────────┐
       ↓                                          │
D2.2 BaseRepository ←────────────────────────────┤
       ↓                                          │
D2.3 QueryRepository ←───────────────────────────┤
       ↓                                          │
D2.4 Pagination & Utilities ←────────────────────┤
       ↓                                          │
D2.5 Entity Domain Repos ────────────────────────┤
D2.6 Memory Domain Repos ←───────────────────────┼──→ D2.8 Query Repos
D2.7 Other Domain Repos  ←───────────────────────┤       ↓
       ↓                                  D2.11 Release Blocker Doc
D2.9 Migration Files                          D2.12 Architecture Debt Doc
       ↓                                  D2.13 Documentation Updates
D2.10 Test Suite (parallel with D2.5–D2.8)
       ↓
D2.11–D2.13 Documentation (parallel throughout)
```

**Parallel execution opportunities**:
- D2.5, D2.6, D2.7 (CRUD repositories) can proceed in parallel once D2.2–D2.4 are complete
- D2.10 (tests) can proceed in parallel with individual repository implementations
- D2.11–D2.13 (documentation) proceeds in parallel throughout

---

## 10. Implementation Order

The recommended implementation order follows dependency resolution:

| Order | Task | Description | Estimated Effort |
|-------|------|-------------|-----------------|
| 1 | D2.1 | ORM Model Definitions | ~2 hours |
| 2 | D2.2 | BaseRepository (generic CRUD) | ~3 hours |
| 3 | D2.3 | QueryRepository (read-only base) | ~1 hour |
| 4 | D2.4 | Pagination, Exceptions, Workspace, Types | ~1 hour |
| 5 | D2.5 | Entity + Relationship Repositories | ~3 hours |
| 6 | D2.6 | MemoryNode + Evidence + Archive + Tag Repos | ~4 hours |
| 7 | D2.7 | VectorDoc + Task + Candidate Repos | ~2 hours |
| 8 | D2.8 | MemoryQuery + EntityQuery + VectorQuery Repos | ~4 hours |
| 9 | D2.9 | Database Migration Files | ~2 hours |
| 10 | D2.10 | Test Suite (98 tests) | ~4 hours |
| 11 | D2.11 | Release Blocker Documentation | ~30 min |
| 12 | D2.12 | Architecture Debt Documentation | ~30 min |
| 13 | D2.13 | Documentation Updates | ~1 hour |

**Total estimated effort**: ~27 hours

---

## 11. Next Steps

1. **Human review** of this planning document
2. **Approval** to proceed with D2 implementation
3. **Implementation** of D2 tasks in dependency order
4. **Verification** against Definition of Done (Section 4)
5. **Handoff** to D3 (Service Layer) upon completion

---

> **This is a planning document only.** No production code, configuration files, or placeholder implementations are created by this task.
>
> **Git rules**: No commits. No pushes. Awaiting human review and approval before any coding work begins.
