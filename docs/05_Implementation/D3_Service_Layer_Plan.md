# Personal Memory Hub — D3 Service Layer Plan

> **Version**: 1.0
> **Date**: 2026-07-08
> **Phase**: Phase D — Document-Driven Implementation
> **Stage**: D3 — Service Layer
> **Status**: Planning (awaiting human approval)
> **Author**: System Architecture Group

---

## 1. Purpose

### 1.1 Objectives

Implement the complete Application Service Layer for the Personal Memory Hub project. D3 establishes the business orchestration layer that provides:

- 5 core Services implementing domain capabilities (Capture, Import, Merge, Archive, Lifecycle, Retrieve, Search, Browse, Project, Analyze, Reflect, Consolidate, Summarize, Evaluate, Resolve, Merge Entities, Submit Tasks)
- Service-to-Repository coordination (read/write orchestration, no business logic in Repositories)
- Service-to-Engine coordination (shared domain engines called by Services)
- Transaction boundary management (synchronous commit/rollback, asynchronous retry/fail)
- Domain validation and error translation (Repository exceptions → Domain exceptions → Entry-safe errors)
- DTO boundaries (Entry DTO ↔ Domain Model ↔ Repository ORM Model)
- Capability-oriented public APIs (organized around domain capabilities, not persistence operations)

### 1.2 Scope

D3 covers **Service Layer implementation only**:

- 5 Services: MemoryService, QueryService, EntityService, ReflectionService, TaskService
- Service Infrastructure: base service class, DI wiring, workspace context propagation
- Transaction Management: synchronous transaction boundaries, async retry strategy
- Error Handling: Repository exception translation, Domain exception propagation, Entry-safe errors
- DTO Boundaries: Entry DTO conversion, Domain Model preservation, No ORM leakage
- Service Tests: unit tests, integration tests, capability compliance tests

### 1.3 Out of Scope

D3 explicitly excludes:

- **Domain Engine implementations** — Engines remain abstract/interface-only (D4)
- **API Entry Layer** — No REST, MCP, CLI adapters (D5)
- **Embedding Generation** — External LLM/Embedding API calls are deferred (D3+)
- **Production Deployment** — CD pipeline is intentionally deferred
- **Performance Optimization** — No load testing or benchmarking

---

## 2. Deliverables

The following outputs are expected upon D3 completion:

| # | Deliverable | Location | Description |
|---|-------------|----------|-------------|
| 1 | Service Base Infrastructure | `backend/src/backend/service/base.py` | BaseService[T], workspace context, transaction helpers |
| 2 | DI Wiring | `backend/src/backend/service/__init__.py` | Service container/wiring, dependency injection |
| 3 | MemoryService | `backend/src/backend/service/memory_service.py` | Capture/Import/Merge/Archive/Lifecycle/Restore capabilities |
| 4 | QueryService | `backend/src/backend/service/query_service.py` | Retrieval/Search/Browse/Projection/Analytics capabilities |
| 5 | EntityService | `backend/src/backend/service/entity_service.py` | Identity Management/Merge/Alias/Relationship/Profile Update capabilities |
| 6 | ReflectionService | `backend/src/backend/service/reflection_service.py` | Reflect/Consolidate/Summarize/Evaluate capabilities |
| 7 | TaskService | `backend/src/backend/service/task_service.py` | Task submission, status tracking, runtime health |
| 8 | Error Translation | `backend/src/backend/service/exceptions.py` | Domain exceptions, entry-safe error codes, retry classification |
| 9 | DTO Models | `backend/src/backend/service/dto.py` | Entry DTOs, internal result models, query result models |
| 10 | Test Suite | `backend/tests/` | Service unit tests, integration tests, capability compliance tests |
| 11 | Verification Guide Update | `docs/06_Guides/` | Updated verification guide for D3 |

---

## 3. Work Breakdown

### D3.1 Service Base Infrastructure

**Purpose**: Implement the shared infrastructure that all Services inherit from.

**Dependencies**: D2 (Repositories available, frozen, verified).

**Expected outputs**:

- `backend/src/backend/service/base.py` — `BaseService` class with:
  - Repository access pattern (diagonal access: Service → Repository directly)
  - Workspace context propagation (workspace_id through repository calls)
  - Transaction helpers (`commit()`, `rollback()`)
  - Error translation pattern (`RepositoryError` → `DomainIntegrityError` → `EntrySafeError`)
  - Capability-oriented method signatures (no CRUD-style methods)

- `backend/src/backend/service/__init__.py` — Service container/wiring:
  - DI registration for all Services
  - Repository bindings (each Service receives its required Repositories)
  - Engine bindings (placeholder for D4 Engine implementations)

**Constraints**:
- Services must NOT contain business logic that belongs in Engines (Engines are D4)
- Services coordinate Repository reads/writes but do NOT implement domain algorithms
- All Services use the same error translation pattern
- All Services respect workspace isolation

**Engineering decisions referenced**:
- 10_1 §4.2: Service Responsibilities (orchestration, transaction, coordination)
- 10_1 §5: Repository Layer design (persistence only, no business logic)
- G-013: Repository Is Persistence Only
- G-014: No Layer Skipping (Service → Repository allowed; Service → Engine allowed)
- ENG-001: Memory Hub = Infrastructure, Not Business Logic

**Verification**: `BaseService` can be instantiated via DI. All Services inherit from `BaseService`. Error translation works correctly.

---

### D3.2 MemoryService

**Purpose**: Implement the Memory Domain Service — the primary write orchestration for the Memory lifecycle.

**Dependencies**: D3.1 (BaseService available), D2 (MemoryNodeRepository, EvidenceRepository, RelationshipRepository, ArchiveRepository, TagRepository available).

**Expected outputs**:

- `backend/src/backend/service/memory_service.py` — `MemoryService` class with:
  - **Capture Capability**: `capture_memory()`, `capture_conversation()`
  - **Import Capability**: `import_memories()`, `create_import_job()`, `get_import_status()`, `cancel_import()`, `retry_import()`
  - **Merge Capability**: `merge_memories()`
  - **Archive Capability**: `archive_memory()`
  - **Lifecycle Capability**: `trigger_reflection()`, `schedule_archive()`, `reprocess_memory()`
  - **Restore Capability**: `restore_archived_memory()`

**Capability-Oriented API**:

```
MemoryService
│
├── Capture Capability
│   ├── capture_memory()
│   └── capture_conversation()
│
├── Import Capability
│   ├── import_memories()
│   ├── create_import_job()
│   ├── get_import_status()
│   ├── cancel_import()
│   └── retry_import()
│
├── Merge Capability
│   └── merge_memories()
│
├── Archive Capability
│   └── archive_memory()
│
├── Lifecycle Capability
│   ├── trigger_reflection()
│   ├── schedule_archive()
│   └── reprocess_memory()
│
└── Restore Capability
    └── restore_archived_memory()
```

**Repository Coordination**:
- MemoryNodeRepository: create (capture), read (find_by_id, find_by_workspace)
- EvidenceRepository: create (evidence linking), read (find_by_memory)
- RelationshipRepository: create (memory relationships), read (find_memory_by_source/target)
- ArchiveRepository: create (archive records), read (find_archived)
- TagRepository: read (find tags for memory), link_tag/unlink_tag

**Transaction Policy**:
- Per-Memory transaction (default): each captured memory is an independent transaction
- Import batch: each memory within the batch is an independent transaction (continue-on-error)
- Merge: single transaction for all related memory updates
- Archive: single transaction for archive creation + source update

**Constraints**:
- Command Returns Identity: `capture_memory()` returns `MemoryId`, not full Memory entity
- No Query responsibilities: all Memory data reading goes through QueryService
- No direct Engine calls: Engine implementations are D4; Service coordinates Repositories directly
- Raw Evidence Preservation: raw evidence must never be lost due to downstream processing failure

**Engineering decisions referenced**:
- 10_2: MemoryService design (Capability taxonomy, Import pipeline, Transaction policy)
- 10_1 §4.2.1: Domain Service principle (not CRUD)
- 10_1 §4.2.2: Command/Query Separation
- IR-009: PerMemory Transaction (MVP default)
- IR-010: Continue-on-Error (Import batch)
- IR-011: Direct Job Dispatch (MemoryService → TaskService.submit())
- IR-012: Idempotent Import (batch-level uniqueness)

**Verification**: All 6 Capability groups have implemented methods. Command methods return Identity. Query methods are absent. Repository access respects workspace isolation.

---

### D3.3 QueryService

**Purpose**: Implement the application-level read orchestration service — all read capabilities flow through QueryService.

**Dependencies**: D3.1 (BaseService available), D2 (MemoryQueryRepository, EntityQueryRepository, VectorQueryRepository, MemoryNodeRepository, EntityRepository available).

**Expected outputs**:

- `backend/src/backend/service/query_service.py` — `QueryService` class with:
  - **Retrieval Capability**: `retrieve_by_id()`, `retrieve_by_entity()`, `retrieve_by_relationship()`
  - **Search Capability**: `search_by_keyword()`, `search_by_similarity()`, `search_combined()`
  - **Browse Capability**: `browse_by_time_range()`, `browse_by_category()`, `browse_by_tag()`
  - **Projection Capability**: `project_to_summary()`, `project_to_detail()`, `project_to_graph()`, `project_to_timeline()`
  - **Analytics Capability**: `analyze_statistics()`, `analyze_insights()`

**Capability-Oriented API**:

```
QueryService
│
├── Retrieval Capability
│   ├── retrieve_by_id()
│   ├── retrieve_by_entity()
│   └── retrieve_by_relationship()
│
├── Search Capability
│   ├── search_by_keyword()
│   ├── search_by_similarity()
│   └── search_combined()
│
├── Browse Capability
│   ├── browse_by_time_range()
│   ├── browse_by_category()
│   └── browse_by_tag()
│
├── Projection Capability
│   ├── project_to_summary()
│   ├── project_to_detail()
│   ├── project_to_graph()
│   └── project_to_timeline()
│
└── Analytics Capability
    ├── analyze_statistics()
    └── analyze_insights()
```

**Repository Coordination**:
- MemoryQueryRepository: complex multi-table JOIN queries, evidence-linked retrieval
- EntityQueryRepository: graph traversal queries (entity relationships)
- VectorQueryRepository: similarity search (deferred until pgvector available)
- MemoryNodeRepository: basic single-entity reads (for projection enrichment)
- EntityRepository: single-entity reads (for projection enrichment)

**Side-Effect Free Principle**:
- QueryService MUST NOT modify any domain state or persist data
- QueryService always respects current persisted state as the single source of truth
- Allowed infrastructure behavior: cache reads, query metrics, performance tracing, access logging

**Constraints**:
- Query Returns State: query methods return full domain objects (MemoryView, EntityView, etc.)
- No Command responsibilities: all writes go through MemoryService/EntityService/ReflectionService
- Projection belongs to QueryService (not Engine, not Presentation/Entry layer)
- Pagination: all list-returning methods support OffsetPage/CursorPage

**Engineering decisions referenced**:
- 10_3: QueryService design (Capability taxonomy, Pipeline, Engine interaction)
- 10_1 §4.2.2: Command/Query Separation
- G-001: One Capability, One Public API Family
- G-003: Consumer-Agnostic Interface
- IR-005: Stable Result Contract (QueryResult model)
- IR-006: Continuation Semantics (pagination continuation)

**Verification**: All 5 Capability groups have implemented methods. No write methods exist. Side-effect free property verified. Projection methods return domain views, not DTOs.

---

### D3.4 EntityService

**Purpose**: Implement the Identity Management Service — Entity lifecycle and relationship management.

**Dependencies**: D3.1 (BaseService available), D2 (EntityRepository, RelationshipRepository, TagRepository available).

**Expected outputs**:

- `backend/src/backend/service/entity_service.py` — `EntityService` class with:
  - **Identity Management Capability**: `create_entity()`, `resolve_entity()`, `get_entity_profile()`
  - **Merge Capability**: `merge_entities()`, `get_merge_status()`
  - **Alias Capability**: `add_alias()`, `remove_alias()`, `get_aliases()`
  - **Relationship Capability**: `add_relationship()`, `remove_relationship()`, `get_relationships()`
  - **Profile Update Capability**: `update_canonical_name()`, `update_metadata()`

**Capability-Oriented API**:

```
EntityService
│
├── Identity Management Capability
│   ├── create_entity()
│   ├── resolve_entity()
│   └── get_entity_profile()
│
├── Merge Capability
│   ├── merge_entities()
│   └── get_merge_status()
│
├── Alias Capability
│   ├── add_alias()
│   ├── remove_alias()
│   └── get_aliases()
│
├── Relationship Capability
│   ├── add_relationship()
│   ├── remove_relationship()
│   └── get_relationships()
│
└── Profile Update Capability
    ├── update_canonical_name()
    └── update_metadata()
```

**Repository Coordination**:
- EntityRepository: create_entity, find_by_id, find_by_name, find_by_alias, find_by_area, find_by_parent, create_area, create_user_profile, find_page
- RelationshipRepository: find_by_source, find_by_target, find_connections, create_relationship, find_by_type
- TagRepository: link_tag, unlink_tag (for entity tagging)

**Transaction Policy**:
- Create entity: single transaction
- Merge entities: single transaction (entity update + relationship migration + alias consolidation)
- Add/remove alias: single transaction per operation
- Add/remove relationship: single transaction per operation

**Constraints**:
- Command Returns Identity: `create_entity()` returns `EntityId`, `merge_entities()` returns `MergeResult`
- Entity identity evolves, does not mutate (EntityID remains stable)
- Entity is never soft-deleted (status management via relationships)
- No Memory management (belongs to MemoryService)
- No Reflection generation (belongs to ReflectionService)
- No Query Projection (belongs to QueryService)

**Engineering decisions referenced**:
- 10_5: EntityService design (Identity philosophy, Merge strategy, Lifecycle)
- 10_1 §4.2.1: Domain Service principle
- IR-003: Asynchronous Reference Migration (merge workflow)
- IR-004: Entity Status Management (never deleted, only status transition)

**Verification**: All 5 Capability groups have implemented methods. No Memory or Reflection methods exist. Entity identity stability verified. Merge uses asynchronous reference migration pattern.

---

### D3.5 ReflectionService

**Purpose**: Implement the Memory Evolution Service — semantic quality, evidence consistency, and continuous knowledge evolution.

**Dependencies**: D3.1 (BaseService available), D3.4 (EntityService available for entity updates), D2 (MemoryNodeRepository, CandidateRepository, RelationshipRepository available).

**Expected outputs**:

- `backend/src/backend/service/reflection_service.py` — `ReflectionService` class with:
  - **Reflect Capability**: `reflect()`, `reflect_by_entity()`, `reflect_by_time_window()`, `reflect_by_scope()`
  - **Consolidate Capability**: `consolidate()`, `consolidate_by_entity()`
  - **Summarize Capability**: `summarize()`, `summarize_by_level()`
  - **Evaluate Capability**: `evaluate()`, `evaluate_by_entity()`

**Capability-Oriented API**:

```
ReflectionService
│
├── Reflect Capability
│   ├── reflect()
│   ├── reflect_by_entity()
│   ├── reflect_by_time_window()
│   └── reflect_by_scope()
│
├── Consolidate Capability
│   ├── consolidate()
│   └── consolidate_by_entity()
│
├── Summarize Capability
│   ├── summarize()
│   └── summarize_by_level()
│
└── Evaluate Capability
    ├── evaluate()
    └── evaluate_by_entity()
```

**Repository Coordination**:
- MemoryNodeRepository: read candidate memories, create new summary memories, update memory levels
- CandidateRepository: create candidates, find_candidates_by_scope, update_candidate_status
- RelationshipRepository: create/update memory relationships (CORRECTS, SUPERSEDES, PART_OF)

**Transaction Policy**:
- Reflect: single transaction for all generated memories within one reflection run
- Consolidate: single transaction for merged memories
- Summarize: single transaction per level update
- Evaluate: read-only (no transaction needed)

**Constraints**:
- Command Returns Identity: reflection methods return `ReflectionExecutionResult` (execution report, not business data)
- True business data (newly generated memories, updated entities) accessed through QueryService
- Reflection is evolution, not mutation (produces proposals, not direct modifications)
- Higher-level Memory stores evolving explanations, not historical snapshots
- Semantic uniqueness within same abstraction level
- Incremental propagation (only upward when necessary)
- Raw Evidence Preservation: raw L0 memories are never modified or deleted by Reflection

**Engineering decisions referenced**:
- 10_4: ReflectionService design (Philosophy, Capability taxonomy, Pipeline)
- 10_1 §4.2.1: Domain Service principle
- IR-008: Reflection Pipeline (scope → collect → analyze → generate → validate → persist → propagate)
- IR-013: Reflection Execution Result (Status, Statistics, Metadata)

**Verification**: All 4 Capability groups have implemented methods. No direct Memory modification without evidence chain. Raw evidence preservation verified. Execution results are reports, not business data.

---

### D3.6 TaskService

**Purpose**: Implement the Task Scheduling Service — task submission, status tracking, and runtime health monitoring.

**Dependencies**: D3.1 (BaseService available), D2 (TaskRepository, CandidateRepository available).

**Expected outputs**:

- `backend/src/backend/service/task_service.py` — `TaskService` class with:
  - **Submission Capability**: `submit_task()` — submit a task to the runtime
  - **Tracking Capability**: `get_task()` — get task status and metadata
  - **Health Capability**: `query_runtime_status()` — query runtime health
  - **Recovery Capability**: `retry_task()` — retry a failed task

**Capability-Oriented API**:

```
TaskService
│
├── Submission Capability
│   └── submit_task()
│
├── Tracking Capability
│   └── get_task()
│
├── Health Capability
│   └── query_runtime_status()
│
└── Recovery Capability
    └── retry_task()
```

**Repository Coordination**:
- TaskRepository: create task record, find_by_id, find_by_status, find_by_workspace, update_status, find_pending, find_failed
- CandidateRepository: read candidate tasks (for reflection pipeline)

**Transaction Policy**:
- Submit task: single transaction (create task record)
- Retry task: single transaction (reset status to Pending, clear last_error)
- Status tracking: read-only (no transaction needed)

**Constraints**:
- TaskService is the ONLY entry point for task submission from other Services
- Other Services call `TaskService.submit()`, never `TaskRepository.create()` directly
- Task Runtime is generic infrastructure — TaskService does not understand payload content
- All Services use TaskService for: Import jobs, Reflection jobs, Archive jobs, Entity merge jobs

**Engineering decisions referenced**:
- 10_6: TaskRuntime design (Task model, State machine, Retry policy, Idempotency)
- 10_7 §11: Long-Running Task Tracking (Submit → Poll → Complete pattern)
- IR-007: Task State Machine (Pending → Running → Completed/Failed → Dead)
- IR-006: Retry vs Re-trigger distinction
- IR-015: Domain Event → Task Registry pattern

**Verification**: All 4 Capability groups have implemented methods. No Service bypasses TaskService for task submission. Task status transitions follow state machine.

---

### D3.7 Error Handling & DTO Models

**Purpose**: Implement consistent error handling and DTO boundaries across all Services.

**Dependencies**: D3.1–D3.6 (all Services implemented).

**Expected outputs**:

- `backend/src/backend/service/exceptions.py` — Domain exception hierarchy:
  - `ServiceError` (base)
  - `ValidationError` (invalid input)
  - `NotFoundError` (entity not found)
  - `DomainIntegrityError` (business rule violation)
  - `DuplicateError` (duplicate entity)
  - `ReadOnlyError` (write attempted on read-only resource)
  - `EntrySafeError` (mapped to HTTP/protocol error codes)

- `backend/src/backend/service/dto.py` — DTO models:
  - Entry DTOs: `CaptureRequest`, `SearchRequest`, `ImportRequest`, `MergeRequest`, `ReflectRequest`, `TaskSubmitRequest`
  - Internal Results: `CaptureResult`, `SearchResult`, `ImportReport`, `MergeResult`, `ReflectionExecutionResult`, `TaskInfo`
  - Query Results: `QueryResult[T]`, `MemoryView`, `EntityView`, `RankedMemoryView`

**Constraints**:
- No ORM Model leakage to Entry layer
- No Entry DTO propagation between Services
- Entry DTO ↔ Domain Model ↔ Repository ORM Model (three distinct layers)
- All error codes are protocol-agnostic (Entry layer maps to HTTP/MCP/CLI codes)

**Engineering decisions referenced**:
- 10_1 §3.3: Call direction rules (Entry → Service → Engine/Repository)
- 10_1 §8: API Entry Layer (DTO conversion, protocol adaptation)
- 10_7 §4: Error code catalog
- IR-005: Stable Result Contract

**Verification**: All Services use the same exception hierarchy. No Service returns ORM models directly. All Entry DTOs have corresponding internal result models.

---

### D3.8 Service Test Suite

**Purpose**: Implement comprehensive tests for all Services.

**Dependencies**: D3.1–D3.7 (all Services and infrastructure implemented).

**Expected outputs**:

- `tests/test_memory_service.py` — MemoryService tests:
  - Capture capability tests (valid capture, duplicate detection, evidence linking)
  - Import capability tests (batch import, continue-on-error, idempotency)
  - Merge capability tests (merge workflow, reference migration trigger)
  - Archive capability tests (archive creation, source update)
  - Lifecycle capability tests (reflection trigger, schedule archive)
  - Restore capability tests (archived memory restoration)

- `tests/test_query_service.py` — QueryService tests:
  - Retrieval capability tests (by ID, by entity, by relationship)
  - Search capability tests (keyword, similarity placeholder, combined)
  - Browse capability tests (time range, category, tag)
  - Projection capability tests (summary, detail, graph, timeline views)
  - Analytics capability tests (statistics, insights)
  - Side-effect free verification (no write operations)

- `tests/test_entity_service.py` — EntityService tests:
  - Identity management tests (create, resolve, profile)
  - Merge tests (merge workflow, reference migration)
  - Alias tests (add, remove, get)
  - Relationship tests (add, remove, get)
  - Profile update tests (canonical name, metadata)

- `tests/test_reflection_service.py` — ReflectionService tests:
  - Reflect capability tests (full scope, by entity, by time window)
  - Consolidate tests (manual consolidation, entity-scoped)
  - Summarize tests (by level, auto-summarization)
  - Evaluate tests (importance, confidence, freshness, archive candidate)
  - Raw evidence preservation tests (L0 memories unchanged)

- `tests/test_task_service.py` — TaskService tests:
  - Submission tests (valid task, invalid payload)
  - Tracking tests (status lookup, workspace filter)
  - Health tests (runtime status query)
  - Recovery tests (retry failed task)

- `tests/test_service_errors.py` — Error handling tests:
  - Repository exception translation
  - Domain exception propagation
  - Entry-safe error mapping
  - Retryable vs non-retryable classification

- `tests/test_service_boundaries.py` — Boundary tests:
  - No ORM leakage (Services return Domain Models, not ORM objects)
  - No cross-Service calls (Service Independence Principle)
  - Workspace isolation enforcement
  - Capability API compliance (no CRUD-style methods exposed)

**Verification**: All 6 test files pass. Coverage meets project standards. No cross-layer violations detected.

---

## 4. Definition of Done

D3 is complete when **all** of the following criteria are met:

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 1 | All 5 Services implemented | File existence check: `memory_service.py`, `query_service.py`, `entity_service.py`, `reflection_service.py`, `task_service.py` |
| 2 | `ruff check src/ tests/` passes zero violations | `uv run ruff check src/ tests/` → "All checks passed!" |
| 3 | `mypy src/` passes in strict mode | `uv run mypy src/` → "Success: no issues found" |
| 4 | All Service tests pass | `uv run pytest tests/ -v` → all tests pass |
| 5 | Capability-oriented APIs | Verify no CRUD-style methods (`create()`, `update()`, `delete()`, `find()`) exposed by any Service |
| 6 | Command Returns Identity | MemoryService/EntityService/ReflectionService command methods return Identity/Result, not full entities |
| 7 | Query Returns State | QueryService query methods return full domain objects/views |
| 8 | Side-Effect Free Query | QueryService has NO write operations (no create, update, delete, soft_delete calls) |
| 9 | No cross-Service calls | Verify no Service → Service synchronous calls (Service Independence Principle) |
| 10 | No ORM leakage | Services return Domain Models, not ORM objects |
| 11 | No Entry DTO propagation | Entry DTOs do not leak between Services |
| 12 | Transaction policy enforced | PerMemory transaction for capture, batch transaction for import |
| 13 | Error translation consistent | All Services use same exception hierarchy |
| 14 | Repository Layer not modified | `git diff HEAD -- backend/src/backend/repository/` shows no changes |
| 15 | Service Dependency Graph valid | DAG verification: no circular dependencies |

---

## 5. Risks

### 5.1 Engine Abstraction Gap

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Services depend on Engines that are not yet implemented (D4) | Services accept Engine interfaces/protocols. During D3, Services coordinate Repositories directly. Engine integration points are defined but not called. |
| Impact | High | **Severity: Medium** |
| Trigger | Service needs to call an Engine method | Service uses Repository directly as interim. D4 adds Engine implementation behind the same interface. |

### 5.2 Service Over-Scope

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Services grow to include business logic that belongs in Engines | Each Service traces back to 10_X design documents. Domain algorithms stay in Engines (D4). Services coordinate, do not compute. |
| Impact | Medium | **Severity: Medium** |
| Trigger | Service method body exceeds 100 lines | Refactor: move algorithm to Engine interface, keep Service orchestration only. |

### 5.3 Transaction Complexity

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Complex multi-Repository transactions causing deadlocks or long locks | Use PerMemory transaction (single Repository per transaction). Multi-Repository transactions limited to merge/archive workflows. |
| Impact | High | **Severity: Low** |
| Trigger | Deadlock during concurrent writes | PerMemory isolation prevents cross-memory deadlocks. Merge transactions are short-lived. |

### 5.4 DTO Boundary Violations

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | ORM models leaking to Entry layer, or Entry DTOs propagating between Services | Define three distinct layers: Entry DTO, Domain Model, Repository ORM Model. Services operate on Domain Models only. |
| Impact | Medium | **Severity: Medium** |
| Trigger | Test reveals ORM object in Service return value | Add boundary test. Refactor Service to return Domain Model. |

### 5.5 Service Independence Violation

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Services calling each other synchronously, creating tight coupling | Enforce Service Independence Principle (G-005). Services collaborate through shared Domain Engines (D4), not direct calls. |
| Impact | High | **Severity: Low** |
| Trigger | New Service method calls another Service | Architecture review blocks the change. Redirect to shared Engine pattern. |

### 5.6 Raw Evidence Loss

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Reflection or higher-level processing causes loss of raw L0 evidence | Raw Evidence Preservation Principle: L0 memories are immutable. Reflection creates new nodes (CORRECTS/SUPERSEDES), never modifies existing ones. |
| Impact | Critical | **Severity: Low** |
| Trigger | MemoryNodeRepository soft_delete or update on L0 memory | MemoryNodeRepository enforces immutability (raises DomainIntegrityError). |

---

## 6. Documentation Updates

Upon D3 completion, update the following documents:

| Document | Change |
|----------|--------|
| `docs/05_Implementation/README.md` | Update status: D3 Service Layer — ✅ Complete |
| `docs/INDEX.md` | Add D3 cross-references (10_2~10_6 → D3 implementation) |
| `docs/04_Retrieval_Ranking/10_1_Implementation_Service_Layer.md` | Add implementation status per Service |
| `docs/04_Retrieval_Ranking/10_2_Implementation_MemoryService.md` | Add implementation status |
| `docs/04_Retrieval_Ranking/10_3_Implementation_QueryService.md` | Add implementation status |
| `docs/04_Retrieval_Ranking/10_4_Implementation_ReflectionService.md` | Add implementation status |
| `docs/04_Retrieval_Ranking/10_5_Implementation_EntityService.md` | Add implementation status |
| `docs/04_Retrieval_Ranking/10_6_Implementation_TaskRuntime.md` | Add TaskService implementation status |
| `docs/04_Retrieval_Ranking/10_7_Implementation_API_Entry.md` | Add Service Layer completion reference |
| `docs/04_Retrieval_Ranking/10_8_Implementation_Testing.md` | Add Service Layer test status |
| `docs/04_Retrieval_Ranking/11_Implementation_Roadmap.md` | Update Milestone 3 status |

---

## 7. Handoff to D4 (Domain Engine Layer)

### 7.1 What D3 Provides

| Item | D3 Provides | D4 Assumes |
|------|-------------|------------|
| **Services** | 5 fully implemented Services with capability-oriented APIs | Services exist and are callable |
| **Repository access** | Services call Repositories directly | Repositories are available and stable |
| **Engine interfaces** | Service method signatures accept Engine-compatible inputs | Engines will implement the same interface |
| **Transaction boundaries** | PerMemory, batch, merge transaction policies defined | Engines operate within Service-managed transactions |
| **Error handling** | Consistent exception hierarchy across all Services | Engines raise the same exceptions |
| **DTO boundaries** | Three-layer DTO/Domain/ORM separation enforced | Engines receive Domain Models, return Domain Models |

### 7.2 What D4 Must NOT Assume

| Item | Reason |
|------|--------|
| Services will change their public APIs | Service Layer is frozen after D3 (requires ADR for changes) |
| Repository contracts are mutable | Repository Layer is frozen after D2 |
| QueryService will handle writes | QueryService is strictly read-only |
| MemoryService handles query operations | Query responsibilities belong to QueryService |

---

## 8. Engineering Principles Applied

During D3 implementation, the following principles govern all decisions:

| Principle | Source | Application in D3 |
|-----------|--------|-------------------|
| **Memory Hub = Infrastructure** | ENG-001 | Services are orchestration, not computation |
| **Document-Driven Design** | 11 §13.1 | Each Service traces to 10_2~10_6 |
| **No Layer Skipping** | G-014 | Service → Repository (allowed); Service → Engine (allowed via interface) |
| **Repository Is Persistence Only** | G-013 | Services coordinate Repositories; Repositories do NOT contain business logic |
| **Capability-Based Verification** | D2 Capability Matrix | Services organized by domain capabilities, not CRUD operations |
| **Command Returns Identity** | 10_1 §4.2.2 | Command methods return IDs/results, not full entities |
| **Query Returns State** | 10_1 §4.2.2 | Query methods return full domain objects/views |
| **Service Independence** | G-005 | No Service → Service synchronous calls |
| **Shared Domain Engine** | 10_1 §7.2 | Services collaborate through shared Engines (defined as interfaces) |
| **Raw Evidence Preservation** | IR-016 | L0 memories are never modified by ReflectionService |
| **Minimum Service Guarantee** | IR-017 | Raw factual memories always retrievable even if Reflection fails |
| **Deterministic-by-Default** | 10_8 §5.1 | All Service tests are deterministic |
| **Human Decides, AI Executes** | 11 §13.2 | This plan requires human approval before coding |

---

## 9. Task Dependencies

```
D3.1 Service Base Infrastructure ──────────────────┐
       ↓                                          │
D3.2 MemoryService ←──────────────────────────────┤
D3.3 QueryService ←───────────────────────────────┤
D3.4 EntityService ←──────────────────────────────┤
D3.5 ReflectionService ←──────────────────────────┤
D3.6 TaskService ←────────────────────────────────┤       ↓
       ↓                                  D3.7 Error & DTO Models
D3.8 Service Test Suite (parallel with D3.2–D3.6)
       ↓
D3.9 Documentation Updates (parallel throughout)
```

**Parallel execution opportunities**:
- D3.2 (MemoryService), D3.3 (QueryService), D3.4 (EntityService) can proceed in parallel once D3.1 is complete
- D3.5 (ReflectionService) depends on D3.1 + D3.4 (EntityService for entity updates during reflection)
- D3.6 (TaskService) can proceed in parallel with D3.2–D3.5 (independent capability)
- D3.7 (Error & DTO) can proceed in parallel with D3.2–D3.6 (shared infrastructure)
- D3.8 (tests) can proceed in parallel with individual Service implementations
- D3.9 (documentation) proceeds in parallel throughout

---

## 10. Implementation Order

The recommended implementation order follows dependency resolution:

| Order | Task | Description | Estimated Effort |
|-------|------|-------------|-----------------|
| 1 | D3.1 | Service Base Infrastructure | ~3 hours |
| 2 | D3.2 | MemoryService (largest Service) | ~6 hours |
| 3 | D3.3 | QueryService (read-only, simpler) | ~4 hours |
| 4 | D3.4 | EntityService (identity management) | ~4 hours |
| 5 | D3.5 | ReflectionService (evolution orchestration) | ~5 hours |
| 6 | D3.6 | TaskService (task scheduling) | ~3 hours |
| 7 | D3.7 | Error Handling & DTO Models | ~2 hours |
| 8 | D3.8 | Service Test Suite | ~8 hours |
| 9 | D3.9 | Documentation Updates | ~1 hour |

**Total estimated effort**: ~36 hours

---

## 11. Next Steps

1. **Human review** of this planning document
2. **Approval** to proceed with D3 implementation
3. **Implementation** of D3 tasks in dependency order
4. **Verification** against Definition of Done (Section 4)
5. **Handoff** to D4 (Domain Engine Layer) upon completion

---

## 15. Closing Confirmation

> **Status**: Closed
> **Date**: 2026-07-08
> **Verified by**: Human verification (D3 Verification Guide, §1–14)

### 15.1 D3 Service Layer Completed

All D3 deliverables have been implemented and verified:

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | 5 Services (Memory, Query, Entity, Reflection, Task) | ✅ Implemented |
| 2 | Service Base Infrastructure | ✅ Implemented |
| 3 | DI Wiring / Container | ✅ Implemented |
| 4 | Error Handling & DTO Models | ✅ Implemented |
| 5 | Service Test Suite | ✅ All passing |
| 6 | Verification Guide | ✅ Complete |

### 15.2 Service Layer Frozen

The Service Layer is officially frozen after D3 completion.

**Allowed changes**:
- Bug fixes (mypy errors, runtime errors)
- Security fixes
- Framework compatibility updates (dependency version bumps)

**Prohibited changes without ADR**:
- Service redesign
- Capability addition/removal
- Service contract changes (method signatures, return types)
- Adding new Services
- Modifying Service dependencies (DAG edges)

### 15.3 Service Contract Frozen

The Service interface contract defined in `10_2~10_6` is frozen. Any future changes to the contract require an Architecture Decision Record (ADR).

### 15.4 Handoff to D4

D3 has completed all planned work and passed verification. The Service Layer is ready for D4 (Domain Engine Layer) implementation.

**D4 Assumptions**:
- Services are stable and will not change without ADR
- 5 Services are callable via DI container
- Service exception hierarchy available for Engine error handling
- DTO boundaries enforced (Entry DTO ↔ Domain Model ↔ Repository ORM Model)
- Transaction boundaries managed at Service level

---

> **This document is now closed.** No further changes to D3 scope are permitted without ADR approval.
