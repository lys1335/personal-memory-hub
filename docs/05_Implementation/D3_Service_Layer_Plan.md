# Personal Memory Hub — D3 Service Layer Plan

> **Version**: 2.0 (Post-Human-Review)
> **Date**: 2026-07-08
> **Phase**: Phase D — Document-Driven Implementation
> **Stage**: D3 — Service Layer
> **Status**: Approved — Human review completed, decisions integrated
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
| 12 | Exception Mapping Matrix | `docs/07_Architecture_Contracts/` | Architecture specification: Repository→Service→Entry exception mapping |
| 13 | Logging Schema Specification | `docs/07_Architecture_Contracts/` | Architecture specification: structured logging contract |

**Note**: Items 12–13 are architecture specifications, not implementation deliverables. They define version-controlled contracts for exception mapping and logging schema.

---

## 3. Work Breakdown

### D3.1 Service Base Infrastructure

**Purpose**: Implement the shared infrastructure that all Services inherit from.

**Dependencies**: D2 (Repositories available, frozen, verified).

**Expected outputs**:

- `backend/src/backend/service/base.py` — `BaseService` class with:
  - Repository access pattern (diagonal access: Service → Repository directly)
  - Workspace context propagation (workspace_id through repository calls)
  - Error translation pattern (`RepositoryError` → `DomainIntegrityError` → `EntrySafeError`)
  - Capability-oriented method signatures (no CRUD-style methods)
  - Transaction context helper (internal, not exposed as public commit()/rollback())
  - Exception translation helper
  - Workspace/context helper
  - Common non-domain utilities

- `backend/src/backend/service/__init__.py` — Service container/wiring:
  - Constructor DI registration for all Services
  - Repository bindings (each Service receives its required Repositories)
  - Engine bindings (placeholder for D4 Engine implementations)

**Architecture Principles** (approved by human review):

1. **Thin BaseService Principle**: BaseService exists only for shared infrastructure concerns. Explicitly prohibited: business workflow, domain logic, Repository registry, Service locator, cache, event bus, CRUD implementation, authorization, validation, factory behavior.

2. **Explicit Dependency Principle**: Constructor Injection only. No Service Locator, Property Injection, or Runtime dependency lookup.

3. **Inject What You Use**: Inject only the repositories actually required by each Service. Do NOT introduce Repository Registry.

4. **Infrastructure Independence**: Infrastructure dependencies (Logger, Transaction Manager, Metrics, Tracing) may be shared. Domain dependencies remain owned by each concrete Service.

5. **Stateless Service Principle**: All Services are Stateless. Services keep dependencies only. Never retain: workspace, request, transaction, user state, cache of mutable business objects.

6. **Singleton by Design**: Services are singleton instances managed by DI container.

7. **Context Belongs to Invocation**: Workspace Context belongs to each invocation. It never becomes Service state.

8. **No Lazy Mutable Initialization**: Services must not lazily initialize mutable state.

9. **Service Transaction Ownership**: Transaction belongs only to Application Service. Repositories never begin, commit or rollback transactions.

10. **Repository Transaction Neutrality**: Repositories are transaction-neutral. They operate within the transaction context provided by the Service.

11. **Engine Transaction Neutrality**: Engines remain transaction-neutral.

12. **One Use Case One Transaction**: Each public Service method defines one transaction boundary unless explicitly documented otherwise.

13. **No Hidden Transaction Boundary**: Transaction boundaries are explicit and documented.

14. **Single Translation Responsibility**: Each layer translates once into the exception model of the next layer. Preserve Root Cause.

15. **Stable Exception Taxonomy**: Exception types are version-controlled architecture contracts.

**Constraints**:
- Services must NOT contain business logic that belongs in Engines (Engines are D4)
- Services coordinate Repository reads/writes but do NOT implement domain algorithms
- All Services use the same error translation pattern
- All Services respect workspace isolation
- BaseService does NOT expose commit()/rollback() as public helpers

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
- No Query responsibilities: all Memory data reading goes through QueryService (Query Separation Principle)
- No direct Engine calls: Engine implementations are D4; Service coordinates Repositories directly
- Raw Evidence Preservation: raw evidence must never be lost due to downstream processing failure
- Task Ownership: MemoryService requests background work via TaskService.submit(), TaskService owns task registration/status/retry/cancellation, Task Runtime owns polling/dispatching/execution/handler selection, Domain Engine performs actual business work
- Export Boundary: Export stays within MemoryService (no ExportService). Execution mode (sync/async) determined by caller, not MemoryService
- Import Job Boundary: Import unified with Task lifecycle — MemoryService creates_import_job(), TaskService manages get_task/retry_task/cancel_task
- Repository Coordination: Repositories never coordinate each other. MemoryService coordinates multiple repositories. Repository remains persistence-only.
- Transaction Isolation: Background task execution always starts a completely new transaction. No async task may continue the transaction created by MemoryService.
- Background Failure Isolation: Once primary Memory transaction committed, background task failure never invalidates committed Memory. Failure only affects Task status and Retry scheduling.
- Minimum Service Guarantee: Successful Memory persistence satisfies Minimum Service Guarantee. Reflection/Embedding/Background processing are enhancements. Enhancement failure never invalidates successfully stored Raw Evidence.

**Engineering decisions referenced**:
- 10_2: MemoryService design (Capability taxonomy, Import pipeline, Transaction policy)
- 10_1 §4.2.1: Domain Service principle (not CRUD)
- 10_1 §4.2.2: Command/Query Separation
- IR-009: PerMemory Transaction (MVP default)
- IR-010: Continue-on-Error (Import batch)
- IR-011: Direct Job Dispatch (MemoryService → TaskService.submit())
- IR-012: Idempotent Import (batch-level uniqueness)

**Verification**: All 6 Capability groups have implemented methods. Command methods return Identity. Query methods are absent. Repository access respects workspace isolation. Capability verification, Repository coordination verification, Transaction boundary verification, Background failure isolation verification, Exception mapping verification, Workspace isolation verification, Raw Evidence Preservation verification, Minimum Service Guarantee verification, Service resilience verification.

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

**Unified Read Workflow** (frozen):

```
Validation
    ↓
Planning
    ↓
Repository Coordination
    ↓
Domain Processing
    ↓
Projection
    ↓
Result Assembly
```

**Repository Coordination**:
- QueryService is the **only** repository coordinator
- Repositories never coordinate each other, never know each other, never assemble cross-aggregate results
- Repository combinations determined by Query Planning
- Repositories return domain data only

**Read Pipeline Principles**:
- Single Read Flow — all reads follow the same pipeline
- Forward-Only — no backtracking, no loops
- Immutable Intermediate Results — each stage produces immutable output
- Stateless Execution — no cross-request state
- Pipeline differences only in: Planning, Repository Coordination, Domain Processing

**Projection Boundary**:
- Projection belongs to QueryService (not Engine, not Presentation/Entry layer)
- Three-level boundary: Domain Model → Domain View → Entry DTO
- Projection constraints: transforms representation only, never changes semantics, deterministic, stateless, side-effect free

**Side-Effect Free Principle**:
- QueryService MUST NOT modify any domain state or persist data
- QueryService always respects current persisted state as the single source of truth
- Allowed infrastructure behavior: cache reads, query metrics, performance tracing, access logging
- Prohibited hidden commands: automatic reflection, automatic embedding generation, automatic index rebuilding, automatic repairs

**Query Purity Principle**:
- 除基础设施侧效果外，QueryService 不得产生任何业务侧效果
- 所有侧效果必须通过显式 Command 或 Task 执行

**Observational Consistency**:
- Query results reflect the persisted business state at query time
- QueryService must not alter the observed business state during query execution

**Query Idempotence Principle**:
- The same query executed against the same persisted state shall always produce the same business result

**Capability Composition Principle**:
- Public Query capabilities may internally compose other Query capabilities
- Composition remains inside QueryService
- Entry Layer, Repository Layer and Engine Layer do not orchestrate business capability composition

**Transaction Strategy**:
- Read-Only Transaction
- Transaction owned by QueryService
- Repositories never own transactions
- Single consistent business snapshot
- No long-running read transactions
- Streaming is a delivery strategy, not a transaction strategy

**Error Mapping**:
- Repository errors are translated into Service errors (deterministic mapping)
- Business-oriented exception model
- Projection failures belong to QueryService
- Empty search results are not errors
- Partial failure recovery belongs to D4 QueryEngine, not D3 Service

**Language Preservation**:
- Preserve original language
- Cross-language retrieval relies on embeddings
- Memory Hub remains language-agnostic

**Constraints**:
- Query Returns State: query methods return full domain objects/views
- No Command responsibilities: all writes go through MemoryService/EntityService/ReflectionService
- Projection belongs to QueryService (not Engine, not Presentation/Entry layer)
- Pagination: all list-returning methods support OffsetPage/CursorPage
- QueryService is the only business read entry
- Domain algorithms belong to D4 Engine

**Engineering decisions referenced**:
- 10_3: QueryService design (Capability taxonomy, Pipeline, Engine interaction, Repository Coordination, Projection Boundary, Transaction Strategy, Error Mapping)
- 10_1 §4.2.2: Command/Query Separation
- G-001: One Capability, One Public API Family
- G-003: Consumer-Agnostic Interface
- G-071: Query Purity Principle
- G-072: Capability Composition Principle
- G-073: Query Idempotence Principle
- G-074: Language Preservation Principle
- G-075: Observational Consistency
- G-076: Repository Coordination Uniqueness
- G-077: Read Pipeline Principles
- G-078: Projection Three-Level Boundary
- G-079: Transaction Strategy
- G-080: Deterministic Error Mapping
- IR-005: Stable Result Contract (QueryResult model)
- IR-006: Continuation Semantics (pagination continuation)

**Verification**: All 5 Capability groups have implemented methods. No write methods exist. Side-effect free property verified. Projection methods return domain views, not DTOs. Unified read workflow followed. Repository coordination rules enforced. Query purity verified. Transaction ownership confirmed. Error mapping deterministic.

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

- **Exception Mapping Matrix** (architecture specification, not implementation):
  ```
  Repository Exception
    ↓
  Service Exception
    ↓
  HTTP / MCP / CLI
  ```
  Documented as a version-controlled architecture contract.

- **Logging Schema Specification** (architecture specification, not implementation):
  - Structured Logging adopted
  - Never log: Memory Content, Reflection Content, Embeddings, Prompts, Secrets, API Keys, Tokens
  - Prefer logging identifiers
  - Introduce Correlation ID
  - Define standard log levels
  - Logging belongs to Service layer
  - Repository logs persistence
  - Entry logs protocol/access

**Layer Responsibilities**:
- **Repository**: Repository Exception only
- **Service**: Domain Exception only
- **Entry**: Entry-safe Exception only
- **Exception translation responsibility belongs to Service**

**Constraints**:
- No ORM Model leakage to Entry layer
- No Entry DTO propagation between Services
- Entry DTO ↔ Domain Model ↔ Repository ORM Model (three distinct layers)
- All error codes are protocol-agnostic (Entry layer maps to HTTP/MCP/CLI codes)
- Single Translation Responsibility: Each layer translates once into the exception model of the next layer
- Preserve Root Cause in exception chaining
- Stable Exception Taxonomy as version-controlled architecture contract

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

**Verification Strategy** (expanded by human review):

Include the following test categories:
- Unit Test
- Transaction Verification
- Boundary Verification
- Dependency Verification
- Exception Contract Verification
- Logging Contract Verification
- Capability Verification
- Architecture Compliance Test

**Architecture tests should verify**:
- Layer Dependency
- Service DAG
- Engine DAG
- Repository Frozen
- Stateless Service
- DTO Boundary
- Exception Mapping
- Logging Contract

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

### 7.2 D3 ↔ D4 Boundary

**Strengthened boundary definition**:

- **D3 prepares stable Application Workflows**: D3 delivers fully functional Service Layer with capability-oriented APIs, transaction management, and error handling.
- **D4 fills Domain Engine capabilities**: D4 implements the shared domain Engines that D3 Services coordinate through interfaces.
- **D4 should not require restructuring D3**: Once D3 is complete, the Service Layer is frozen. D4 implementation must adapt to existing Service contracts.
- **Avoid misleading wording**: D4 does NOT move large portions of Service logic. D3 Services already contain the orchestration logic; D4 provides the domain computation logic through Engines.

### 7.3 What D4 Must NOT Assume

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
| **Thin BaseService Principle** | D3.1 Human Decision | BaseService exists only for shared infrastructure concerns |
| **Explicit Dependency Principle** | D3.1 Human Decision | Constructor Injection only |
| **Inject What You Use** | D3.1 Human Decision | Inject only required Repositories, no Registry |
| **Infrastructure Independence** | D3.1 Human Decision | Shared infrastructure, owned domain dependencies |
| **Stateless Service Principle** | D3.1 Human Decision | Services keep dependencies only, never retain state |
| **Singleton by Design** | D3.1 Human Decision | Services are singleton instances |
| **Context Belongs to Invocation** | D3.1 Human Decision | Workspace Context per invocation, not Service state |
| **No Lazy Mutable Initialization** | D3.1 Human Decision | No lazy initialization of mutable state |
| **Service Transaction Ownership** | D3.1 Human Decision | Transaction belongs only to Application Service |
| **Repository Transaction Neutrality** | D3.1 Human Decision | Repositories never begin/commit/rollback transactions |
| **Engine Transaction Neutrality** | D3.1 Human Decision | Engines remain transaction-neutral |
| **One Use Case One Transaction** | D3.1 Human Decision | Each public method defines one transaction boundary |
| **No Hidden Transaction Boundary** | D3.1 Human Decision | Transaction boundaries are explicit and documented |
| **Single Translation Responsibility** | D3.1 Human Decision | Each layer translates once into next layer's exception model |
| **Stable Exception Taxonomy** | D3.1 Human Decision | Exception types are version-controlled architecture contracts |

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

> **Status**: Document Updated — Human review decisions integrated
> **Date**: 2026-07-08
> **Reviewed by**: Human review completed
> **Changes**: 10 human decisions approved and integrated into D3.1

### 15.1 Human Review Decisions Integrated

The following decisions from human review have been integrated into this document:

1. **Thin BaseService Principle** — BaseService remains intentionally minimal
2. **Dependency Injection Strategy** — Constructor Injection only, no Service Locator
3. **Lifecycle & Stateless Rules** — All Services are Stateless, Singleton by Design
4. **Transaction Ownership** — Transaction belongs only to Application Service
5. **Exception Convention** — Clear layer responsibilities (Repository/Service/Entry)
6. **Exception Mapping Matrix** — Added as architecture specification
7. **Logging Strategy** — Structured Logging, Correlation ID, never log sensitive content
8. **Service Verification Strategy** — Expanded to include 8 test categories
9. **D3 ↔ D4 Boundary** — Strengthened wording, D4 should not restructure D3
10. **Documentation Assets** — Exception Mapping Matrix and Logging Schema added

### 15.2 Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-08 | Initial D3 Service Layer Plan |
| 2.0 | 2026-07-08 | Human review decisions integrated (10 principles, transaction ownership, exception convention, logging strategy, verification expansion) |

### 15.3 Service Layer Frozen

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

### 15.4 Service Contract Frozen

The Service interface contract defined in `10_2~10_6` is frozen. Any future changes to the contract require an Architecture Decision Record (ADR).

### 15.5 Handoff to D4

D3 has completed all planned work and passed verification. The Service Layer is ready for D4 (Domain Engine Layer) implementation.

**D4 Assumptions**:
- Services are stable and will not change without ADR
- 5 Services are callable via DI container
- Service exception hierarchy available for Engine error handling
- DTO boundaries enforced (Entry DTO ↔ Domain Model ↔ Repository ORM Model)
- Transaction boundaries managed at Service level

---

> **This document is now closed.** No further changes to D3 scope are permitted without ADR approval.
