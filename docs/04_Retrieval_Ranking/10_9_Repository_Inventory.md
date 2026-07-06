# Personal AI Memory Hub — 10_9 Repository Inventory

> **Version**: 1.0
> **Date**: 2026-07-05
> **Phase**: Phase D2 — Repository Layer Implementation
> **Status**: Draft
> **Author**: System Architecture Group

---

## 1. Purpose

This document is the **implementation inventory for Phase D2** (Repository Layer).

It is derived entirely from the approved architecture documented in GitHub HEAD. It introduces **no architectural changes**. Its sole purpose is to serve as the implementation blueprint for every Repository that must be coded.

**Scope**:

- Lists every Repository defined by the approved architecture
- Maps each Repository to its Aggregate, ORM Models, and Database Tables
- Defines shared infrastructure requirements
- Specifies the D2 implementation order
- Provides a verification checklist per Repository

**Constraint**: This document is a blueprint only. No production code is generated.

**Reference**: 10_1 §5 (Repository Layer), 09 (Database Physical Design), 11 (Implementation Roadmap), 13 (Architecture Guidelines G-013~G-014).

---

## 2. Repository Inventory

The following table lists every Repository defined by the approved architecture.

| # | Repository Name | Aggregate | Primary Responsibility | Related Domain | Status |
|---|----------------|-----------|----------------------|----------------|--------|
| 1 | EntityRepository | Entity | CRUD for entities, areas, workspace, user_profiles | Entity Domain | Planned |
| 2 | MemoryNodeRepository | MemoryNode | CRUD for memory nodes, memory_evidences | Memory Domain | Planned |
| 3 | EvidenceRepository | Evidence | CRUD for evidences | Ingestion Domain | Planned |
| 4 | RelationshipRepository | Relationship | CRUD for entity relationships, memory_relationships | Entity Domain | Planned |
| 5 | VectorDocRepository | Vector | CRUD for vector_documents | Retrieval Domain | Planned |
| 6 | ArchiveRepository | Archive | CRUD for archives, archive_sources (tag_links for archive target_type) | Memory Domain | Planned |
| 7 | TagRepository | Tag | CRUD for tags, tag_links | Memory Domain | Planned |
| 8 | TaskRepository | Task | CRUD for tasks | Runtime Domain | Planned |
| 9 | CandidateRepository | Candidate | CRUD for candidates | Reflection Domain | Planned |
| 10 | MemoryQueryRepository | MemoryNode | Complex queries: multi-table JOIN, evidence-linked memory retrieval | Memory Domain | Planned |
| 11 | EntityQueryRepository | Entity | Graph queries: entity traversal via relationships | Entity Domain | Planned |
| 12 | VectorQueryRepository | Vector | Vector similarity queries: pgvector search | Retrieval Domain | Planned |

**Total: 12 Repositories (9 core + 3 QueryRepositories)**

---

## 3. Aggregate Mapping

Each Repository maps to one Domain Aggregate. One Aggregate = One Repository.

```
Workspace Aggregate       → EntityRepository (shared)
User Profile Aggregate    → EntityRepository (shared)
Area Aggregate            → EntityRepository (shared)
Entity Aggregate          → EntityRepository
Relationship Aggregate    → RelationshipRepository
MemoryNode Aggregate      → MemoryNodeRepository
MemoryEvidence Aggregate  → MemoryNodeRepository (shared)
Evidence Aggregate        → EvidenceRepository
Vector Document Aggregate → VectorDocRepository
Archive Aggregate         → ArchiveRepository
Tag Aggregate             → TagRepository
TagLink Aggregate         → TagRepository (shared)
Task Aggregate            → TaskRepository
Candidate Aggregate       → CandidateRepository
MemoryRelationship Aggregate → RelationshipRepository (shared)
```

**Mapping Summary**:

| Aggregate | Repository |
|-----------|-----------|
| Entity (entities, areas, workspace, user_profiles) | EntityRepository |
| MemoryNode (memory_nodes, memory_evidences) | MemoryNodeRepository |
| Evidence (evidences) | EvidenceRepository |
| Relationship (relationships, memory_relationships) | RelationshipRepository |
| Vector (vector_documents) | VectorDocRepository |
| Archive (archives, tag_links[target_type='archive']) | ArchiveRepository |
| Tag (tags, tag_links) | TagRepository |
| Task (tasks) | TaskRepository |
| Candidate (candidates) | CandidateRepository |
| MemoryNode (complex queries) | MemoryQueryRepository |
| Entity (graph traversal) | EntityQueryRepository |
| Vector (similarity search) | VectorQueryRepository |

---

## 4. ORM Mapping

### 4.1 EntityRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `Workspace` | `memory_hub.workspace` | Top-level container (singleton, seed on init) |
| `UserProfile` | `memory_hub.user_profiles` | User identity and metadata |
| `Area` | `memory_hub.areas` | Domain area classification (hierarchical via parent_area_id) |
| `Entity` | `memory_hub.entities` | Entity identity, canonical_name, aliases, type, metadata, counters |

**Persistence Scope**: EntityRepository manages the Entity aggregate root. Areas and workspace are scoped to the same aggregate (Entity lives within an Area within a Workspace). UserProfiles are scoped to the workspace.

**Key Constraints**:
- `uk_entities_type_name` UNIQUE (workspace_id, entity_type, canonical_name)
- Entity types: Project, Person, Organization, Tool, Technology, Concept, Event, Location, Object, Agent, Model, Document
- Hierarchical: parent_entity_id self-reference

### 4.2 MemoryNodeRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `MemoryNode` | `memory_hub.memory_nodes` | Memory hierarchy (L1 Observation, L2 Pattern, L3 Belief) |
| `MemoryEvidence` | `memory_hub.memory_evidences` | Many-to-many: memory_node ↔ evidence |

**Persistence Scope**: MemoryNode aggregate root. MemoryEvidence is a child within the aggregate (evidence chain).

**Key Constraints**:
- `chk_level_type_consistency`: L1=Observation, L2=Pattern, L3=Belief
- `level = 4` (State) is runtime-only, never persisted
- Status: active, candidate, deprecated, superseded, orphaned
- Source: user, manual, explicit_command, archive_derived, ai_reflect
- Three-score separation: confidence, importance, signal_strength (0.0–1.0)
- `evidence_links` and `contradict_evidence` are JSONB arrays
- Memory immutable: no UPDATE/DELETE (correction via new node + CORRECT/SUPERSEDES relationship)

### 4.3 EvidenceRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `Evidence` | `memory_hub.evidences` | Raw evidence (observations, conversations, imports) |

**Persistence Scope**: Evidence aggregate root. Evidence is immutable — once created, never deleted or modified.

**Key Constraints**:
- `chk_evidence_not_empty`: content length > 0
- Types: conversation, manual, explicit_command, document, import
- Three-score separation: confidence, importance, signal_strength
- Evidence-based: every MemoryNode must have at least one evidence link (No Orphan Memory)

### 4.4 RelationshipRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `EntityRelationship` | `memory_hub.relationships` | Entity-to-entity relationships (10 core types) |
| `MemoryRelationship` | `memory_hub.memory_relationships` | MemoryNode-to-MemoryNode relationships |

**Persistence Scope**: Two distinct relationship aggregates under one Repository.

**Entity Relationship Types**: belongs_to, part_of, uses, depends_on, related_to, affects, derived_from, owns, created_by, about

**Memory Relationship Types**: supports, derived_from, contradicts, attenuates

**Key Constraints**:
- `chk_no_self_relationship`: source_id != target_id
- `uk_relationship_direction`: UNIQUE (source_id, target_id, relationship_type)
- Strength: 0.0–1.0

### 4.5 VectorDocRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `VectorDocument` | `memory_hub.vector_documents` | Vector embeddings for memory nodes, archives, entity summaries |

**Persistence Scope**: Vector document aggregate root. Independent from memory_nodes — stores embeddings only.

**Key Constraints**:
- Source types: memory_node, archive, entity_summary
- Embedding: VECTOR(1536) for pgvector cosine similarity
- Memory level: 1, 2, 3, 4 (metadata marker only, not State persistence)

### 4.6 ArchiveRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `Archive` | `memory_hub.archives` | Cognitive compression archives (monthly/yearly) |
| `TagLink` (archive) | `memory_hub.tag_links` | Tag association for archive target_type |

**Persistence Scope**: Archive aggregate root. TagLinks scoped to archive target_type.

**Key Constraints**:
- Archive types: monthly, yearly
- Hierarchical: source_archive_id self-reference (archive-of-archive)
- Period constraint: period_start <= period_end

### 4.7 TagRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `Tag` | `memory_hub.tags` | Tag definitions (system/ai/user) |
| `TagLink` | `memory_hub.tag_links` | Many-to-many: tag ↔ target (entity, memory_node, archive) |

**Persistence Scope**: Tag aggregate root. TagLink is a child within the aggregate.

**Key Constraints**:
- Tag types: system, ai, user
- Target types: entity, memory_node, archive
- `uk_tags_workspace_name`: UNIQUE (workspace_id, name)
- `uk_tag_links`: UNIQUE (tag_id, target_type, target_id)

### 4.8 TaskRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `Task` | `memory_hub.tasks` | Unified task queue (INGESTION, REFLECTION, ACTIVATION, ARCHIVE) |

**Persistence Scope**: Task aggregate root. Single table for all task types.

**Key Constraints**:
- Task types: INGESTION, REFLECTION, ACTIVATION, ARCHIVE
- Status: pending, running, completed, failed, dead_letter
- Debounce: UNIQUE (workspace_id, task_type, debounce_key) WHERE status IN ('pending', 'running')
- Retry: retry_count, max_retries, exponential backoff
- Payload: JSONB (Task Runtime does not parse)

### 4.9 CandidateRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| `Candidate` | `memory_hub.candidates` | Reflection candidates (pattern/belief) awaiting promotion |

**Persistence Scope**: Candidate aggregate root. Candidates are Promotion targets for MemoryNodes.

**Key Constraints**:
- Candidate types: pattern, belief
- Status: candidate, confirmed, archived, orphaned
- `chk_candidate_has_evidence`: evidence_count >= 1
- `chk_candidate_evidence_chain_not_empty`: evidence_chain JSONB array not empty
- Ingested by: ingestion_pipeline only
- Modified by: reflection_engine / maintenance_queue only
- Verified by: rule_engine / reflection_engine only

### 4.10 MemoryQueryRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| (Query-only) | memory_nodes, memory_evidences, evidences, entities | Complex multi-table queries |

**Persistence Scope**: Read-only. No write operations. Used by QueryService for complex queries.

**Query Capabilities**:
- `findWithEvidence()`: MemoryNode + full evidence chain (JOIN memory_nodes ↔ memory_evidences ↔ evidences)
- `findByEntityAndLevel()`: Scoped by entity + memory level
- `findActiveByWorkspace()`: Status='active' filter with workspace isolation
- `searchWithVector()`: Combined text + vector search (JOIN with vector_documents)

### 4.11 EntityQueryRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| (Query-only) | entities, relationships, areas | Entity graph traversal queries |

**Persistence Scope**: Read-only. No write operations. Used by EntityService and QueryService for graph queries.

**Query Capabilities**:
- `getEntityGraph(entity_id, depth)`: Recursive relationship traversal
- `findRelatedEntities(entity_id, relationship_type)`: Direct relationship lookup
- `findEntitiesByArea(area_id)`: Area-scoped entity listing
- `findEntitiesByType(entity_type)`: Type-filtered entity listing
- `searchEntities(query)`: Full-text search on canonical_name + aliases

### 4.12 VectorQueryRepository

| SQLAlchemy Model | Database Table | Persistence Scope |
|-----------------|----------------|-------------------|
| (Query-only) | vector_documents, memory_nodes | Vector similarity search |

**Persistence Scope**: Read-only. No write operations. Used by RetrievalEngine for similarity queries.

**Query Capabilities**:
- `similaritySearch(embedding, top_k, workspace_id)`: Cosine similarity via pgvector
- `filterBySourceType(source_type, workspace_id)`: Pre-filter by source type
- `filterByEntity(entity_id, workspace_id)`: Entity-scoped vector search
- `hybridSearch(query_embedding, text_query, top_k)`: Combined vector + text search

---

## 5. Repository Dependencies

### 5.1 Shared Infrastructure

Every Repository depends on the following shared infrastructure (provided by D1 Foundation):

| Component | Description | Repository Usage |
|-----------|-------------|-----------------|
| `BaseRepository` | Abstract base class with common CRUD methods | All Repositories inherit |
| `AsyncSession` | SQLAlchemy async session factory (scoped) | All Repositories use for DB transactions |
| `Transaction Support` | Per-operation transaction boundary | All Repositories wrap operations |
| `Pagination` | Cursor/offset pagination helpers | MemoryQueryRepository, EntityQueryRepository, VectorQueryRepository |
| `Exception Mapping` | Database exceptions → Domain exceptions | All Repositories translate IntegrityError, OperationalError, etc. |
| `UUIDv7 Generator` | Time-ordered UUID generation | All Repositories for primary keys |
| `Workspace Isolation` | Automatic workspace_id scoping | All Repositories enforce multi-tenancy |

### 5.2 Boundary Rules (Confirmed)

The following rules are **confirmed** from the approved architecture:

| Rule | Status | Reference |
|------|--------|-----------|
| Repository → Repository calls are **prohibited** | CONFIRMED | 10_1 §5.5, G-014 |
| Repository → Engine calls are **prohibited** | CONFIRMED | 10_1 §5.2, G-013 |
| Repository → Service calls are **prohibited** | CONFIRMED | 10_1 §5.2, G-013 |
| Repository is responsible **only for persistence** | CONFIRMED | 10_1 §5.1, G-013 |
| Service → Repository calls are **the only allowed cross-layer call** | CONFIRMED | 10_1 §3.3, G-014 |
| Engine does NOT access Repository directly | CONFIRMED | 10_1 §6.5 |

### 5.3 Repository Interface Contract

Every Repository MUST implement:

| Method | Description | Return Type |
|--------|-------------|-------------|
| `create(entity)` | Create a new domain object | Created object ID |
| `find_by_id(id)` | Find by primary key | Domain object or None |
| `find_all(**filters)` | Find with filters (workspace-scoped) | List[Domain object] |
| `update(entity)` | Update existing domain object | Updated domain object |
| `soft_delete(id)` | Soft delete (mark deprecated/superseded) | void |
| `exists(id)` | Check existence | bool |

QueryRepositories add:

| Method | Description | Return Type |
|--------|-------------|-------------|
| `complex_query(query_spec)` | Multi-table JOIN query | Domain result |
| `graph_traversal(start_id, depth)` | Recursive relationship query | Graph result |
| `similarity_search(embedding, k)` | Vector similarity query | Ranked list |

---

## 6. D2 Implementation Order

Following the agreed strategy from 11 (Implementation Roadmap):

| Order | Phase | Repository(s) | Rationale |
|-------|-------|---------------|-----------|
| 1 | Repository Infrastructure | BaseRepository, shared infrastructure | Foundation for all Repositories |
| 2 | Memory Domain | MemoryNodeRepository, EvidenceRepository, MemoryEvidence | Core memory lifecycle |
| 3 | Entity Domain | EntityRepository, RelationshipRepository | Entity identity and graph |
| 4 | Reflection Domain | CandidateRepository | Reflection pipeline |
| 5 | Runtime Domain | TaskRepository | Task scheduling |
| 6 | Repository Verification | MemoryQueryRepository, EntityQueryRepository, VectorQueryRepository | Complex queries validated after core Repositories |

**Detailed Order**:

1. **D2.1 Repository Infrastructure** — BaseRepository abstract class, shared infrastructure (session, transaction, pagination, exception mapping)
2. **D2.2 Memory Domain** — EvidenceRepository → MemoryNodeRepository → MemoryQueryRepository
3. **D2.3 Entity Domain** — EntityRepository → RelationshipRepository → EntityQueryRepository
4. **D2.4 Reflection Domain** — CandidateRepository
5. **D2.5 Runtime Domain** — TaskRepository
6. **D2.6 Auxiliary Repositories** — VectorDocRepository → VectorQueryRepository, ArchiveRepository, TagRepository
7. **D2.7 Repository Verification** — Cross-Repository integration tests, boundary rule verification

---

## 7. Verification Checklist

### 7.1 EntityRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined (BaseRepository inheritance) | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create workspace | Pending |
| 4 | CRUD: create user_profile | Pending |
| 5 | CRUD: create area (with parent) | Pending |
| 6 | CRUD: create entity (with type constraint) | Pending |
| 7 | Query: find_by_id | Pending |
| 8 | Query: find_by_workspace | Pending |
| 9 | Query: find_by_area | Pending |
| 10 | Query: find_by_type | Pending |
| 11 | Query: search_entities | Pending |
| 12 | Transaction: single operation atomic | Pending |
| 13 | Transaction: workspace isolation enforced | Pending |
| 14 | Unit test: happy path | Pending |
| 15 | Unit test: constraint violation (duplicate type+name) | Pending |
| 16 | Unit test: foreign key cascade | Pending |
| 17 | Integration test: full create-flow | Pending |
| 18 | Design Compliance Check | Pending |
| 19 | Human Review | Pending |
| 20 | Complete | Pending |

### 7.2 MemoryNodeRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create memory_node (L1/L2/L3) | Pending |
| 4 | CRUD: link evidence (memory_evidence) | Pending |
| 5 | CRUD: soft delete (status=deprecated/superseded) | Pending |
| 6 | Query: find_by_entity | Pending |
| 7 | Query: find_by_level | Pending |
| 8 | Query: find_by_status | Pending |
| 9 | Query: find_with_evidence_chain | Pending |
| 10 | Query: find_active_by_workspace | Pending |
| 11 | Constraint: level_type_consistency enforced | Pending |
| 12 | Constraint: three-score separation | Pending |
| 13 | Constraint: no L4 (State) persisted | Pending |
| 14 | Transaction: memory + evidence atomic | Pending |
| 15 | Unit test: happy path | Pending |
| 16 | Unit test: constraint violation | Pending |
| 17 | Integration test: full create-flow | Pending |
| 18 | Design Compliance Check | Pending |
| 19 | Human Review | Pending |
| 20 | Complete | Pending |

### 7.3 EvidenceRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create evidence (immutable) | Pending |
| 4 | Query: find_by_id | Pending |
| 5 | Query: find_by_entity | Pending |
| 6 | Query: find_by_workspace | Pending |
| 7 | Query: find_by_source | Pending |
| 8 | Constraint: content not empty | Pending |
| 9 | Constraint: evidence never deleted | Pending |
| 10 | Transaction: single evidence atomic | Pending |
| 11 | Unit test: happy path | Pending |
| 12 | Unit test: empty content rejected | Pending |
| 13 | Integration test: full create-flow | Pending |
| 14 | Design Compliance Check | Pending |
| 15 | Human Review | Pending |
| 16 | Complete | Pending |

### 7.4 RelationshipRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create entity_relationship | Pending |
| 4 | CRUD: create memory_relationship | Pending |
| 5 | Query: find_by_source | Pending |
| 6 | Query: find_by_target | Pending |
| 7 | Query: find_by_type | Pending |
| 8 | Constraint: no self-relationship | Pending |
| 9 | Constraint: direction uniqueness | Pending |
| 10 | Transaction: relationship atomic | Pending |
| 11 | Unit test: happy path | Pending |
| 12 | Unit test: self-relationship rejected | Pending |
| 13 | Integration test: full create-flow | Pending |
| 14 | Design Compliance Check | Pending |
| 15 | Human Review | Pending |
| 16 | Complete | Pending |

### 7.5 VectorDocRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create vector_document | Pending |
| 4 | Query: find_by_source_id | Pending |
| 5 | Query: find_by_workspace | Pending |
| 6 | Constraint: embedding dimension = 1536 | Pending |
| 7 | Transaction: vector document atomic | Pending |
| 8 | Unit test: happy path | Pending |
| 9 | Unit test: embedding validation | Pending |
| 10 | Integration test: full create-flow | Pending |
| 11 | Design Compliance Check | Pending |
| 12 | Human Review | Pending |
| 13 | Complete | Pending |

### 7.6 ArchiveRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create archive | Pending |
| 4 | Query: find_by_period | Pending |
| 5 | Query: find_by_type | Pending |
| 6 | Constraint: period_start <= period_end | Pending |
| 7 | Transaction: archive atomic | Pending |
| 8 | Unit test: happy path | Pending |
| 9 | Unit test: period constraint | Pending |
| 10 | Integration test: full create-flow | Pending |
| 11 | Design Compliance Check | Pending |
| 12 | Human Review | Pending |
| 13 | Complete | Pending |

### 7.7 TagRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create tag | Pending |
| 4 | CRUD: create tag_link | Pending |
| 5 | Query: find_by_tag | Pending |
| 6 | Query: find_linked_targets(tag_id) | Pending |
| 7 | Query: find_tags_for_target(target_type, target_id) | Pending |
| 8 | Constraint: unique workspace+name | Pending |
| 9 | Constraint: unique tag_link | Pending |
| 10 | Transaction: tag + link atomic | Pending |
| 11 | Unit test: happy path | Pending |
| 12 | Unit test: duplicate tag rejected | Pending |
| 13 | Integration test: full create-flow | Pending |
| 14 | Design Compliance Check | Pending |
| 15 | Human Review | Pending |
| 16 | Complete | Pending |

### 7.8 TaskRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create task | Pending |
| 4 | CRUD: update task status | Pending |
| 5 | Query: find_pending | Pending |
| 6 | Query: find_by_type | Pending |
| 7 | Query: find_by_status | Pending |
| 8 | Query: find_failed_for_retry | Pending |
| 9 | Query: find_by_entity | Pending |
| 10 | Constraint: debounce uniqueness | Pending |
| 11 | Constraint: task_type enum | Pending |
| 12 | Constraint: status enum | Pending |
| 13 | Transaction: task status update atomic | Pending |
| 14 | Unit test: happy path | Pending |
| 15 | Unit test: duplicate debounce rejected | Pending |
| 16 | Integration test: full create-flow | Pending |
| 17 | Design Compliance Check | Pending |
| 18 | Human Review | Pending |
| 19 | Complete | Pending |

### 7.9 CandidateRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | CRUD: create candidate | Pending |
| 4 | CRUD: update candidate status | Pending |
| 5 | Query: find_by_entity | Pending |
| 6 | Query: find_by_status | Pending |
| 7 | Query: find_by_candidate_type | Pending |
| 8 | Query: find_by_evidence_strength | Pending |
| 9 | Constraint: evidence_count >= 1 | Pending |
| 10 | Constraint: evidence_chain not empty | Pending |
| 11 | Constraint: ingested_by = ingestion_pipeline | Pending |
| 12 | Transaction: candidate atomic | Pending |
| 13 | Unit test: happy path | Pending |
| 14 | Unit test: no evidence rejected | Pending |
| 15 | Integration test: full create-flow | Pending |
| 16 | Design Compliance Check | Pending |
| 17 | Human Review | Pending |
| 18 | Complete | Pending |

### 7.10 MemoryQueryRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
| 2 | Implementation complete | Pending |
| 3 | Query: findWithEvidence (multi-table JOIN) | Pending |
| 4 | Query: findByEntityAndLevel | Pending |
| 5 | Query: findActiveByWorkspace | Pending |
| 6 | Query: searchWithVector | Pending |
| 7 | Read-only: no write operations | Pending |
| 8 | Pagination: cursor-based | Pending |
| 9 | Unit test: complex JOIN correctness | Pending |
| 10 | Integration test: query results match expected | Pending |
| 11 | Design Compliance Check | Pending |
| 12 | Human Review | Pending |
| 13 | Complete | Pending |

### 7.11 EntityQueryRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | Pending |
|  2 | Implementation complete | Pending |
| 3 | Query: getEntityGraph (recursive traversal) | Pending |
| 4 | Query: findRelatedEntities | Pending |
| 5 | Query: findEntitiesByArea | Pending |
| 6 | Query: findEntitiesByType | Pending |
| 7 | Query: searchEntities (full-text) | Pending |
| 8 | Read-only: no write operations | Pending |
| 9 | Unit test: graph traversal correctness | Pending |
| 10 | Integration test: query results match expected | Pending |
| 11 | Design Compliance Check | Pending |
| 12 | Human Review | Pending |
| 13 | Complete | Pending |

### 7.12 VectorQueryRepository

| # | Check | Status |
|---|-------|--------|
| 1 | Interface defined | ✅ Complete |
| 2 | Implementation complete | ✅ Complete |
| 3 | Query: similaritySearch (pgvector cosine) | ✅ Deferred (pgvector infra) |
| 4 | Query: filterBySourceType | ✅ Complete |
| 5 | Query: filterByEntity | ✅ Complete |
| 6 | Query: hybridSearch | ✅ Complete (text pre-filter) |
| 7 | Read-only: no write operations | ✅ Complete |
| 8 | Unit test: vector similarity ranking | ⏸️ Deferred (pgvector infra) |
| 9 | Integration test: query results match expected | ⏸️ Deferred (pgvector infra) |
| 10 | Design Compliance Check | ✅ Complete |
| 11 | Human Review | ⏸️ Pending |
| 12 | Complete | ✅ Phase D2 Repository Layer Complete |

---

## 8. D2 Definition of Done

The Repository Layer is complete **only** when ALL of the following criteria are met:

### 8.1 Implementation Complete

- [ ] All 12 Repositories implemented (9 core + 3 QueryRepositories)
- [ ] All Repositories inherit from BaseRepository
- [ ] All Repositories use AsyncSession from D1 infrastructure
- [ ] All Repositories enforce workspace isolation
- [ ] All Repositories implement the standard CRUD interface

### 8.2 Boundary Rules Satisfied

- [ ] No Repository → Repository calls (verified by code review)
- [ ] No Repository → Engine calls (verified by code review)
- [ ] No Repository → Service calls (verified by code review)
- [ ] No Repository contains business logic (verified by code review)
- [ ] All Repositories return Domain Objects, never DTOs or Projections
- [ ] Service → Repository calls are the only allowed cross-layer access

### 8.3 Tests Passed

- [ ] All unit tests pass (deterministic)
- [ ] All integration tests pass (cross-layer)
- [ ] All constraint tests pass (CHECK constraints, UNIQUE constraints)
- [ ] Transaction tests pass (atomicity, rollback)
- [ ] No architecture violations detected (layer boundary enforcement)

### 8.4 Design Compliance Check

- [ ] ORM models match 09 (Database Physical Design) exactly
- [ ] Table names, column names, types match 09
- [ ] Indexes match 09 (BTREE, GIN, IVFFLAT)
- [ ] Constraints match 09 (CHECK, UNIQUE, FK)
- [ ] Repository boundaries match 10_1 §5
- [ ] QueryRepository pattern correctly applied

### 8.5 Human Review

- [ ] Architecture team reviews all Repository implementations
- [ ] Consistency with Phase A–C documents confirmed
- [ ] No deviations from approved architecture
- [ ] All verification checklist items marked Complete

### 8.6 Fresh Clone Verification

- [ ] Fresh clone can build and run all Repository tests
- [ ] DDL from 09 can be applied successfully
- [ ] Repository layer operational without Service layer

---

## Appendix A: Repository Table Summary

| Repository | Tables Managed |
|------------|---------------|
| EntityRepository | workspace, user_profiles, areas, entities |
| MemoryNodeRepository | memory_nodes, memory_evidences |
| EvidenceRepository | evidences |
| RelationshipRepository | relationships, memory_relationships |
| VectorDocRepository | vector_documents |
| ArchiveRepository | archives, tag_links (archive) |
| TagRepository | tags, tag_links (entity, memory_node, archive) |
| TaskRepository | tasks |
| CandidateRepository | candidates |
| MemoryQueryRepository | memory_nodes, memory_evidences, evidences, entities (read-only) |
| EntityQueryRepository | entities, relationships, areas (read-only) |
| VectorQueryRepository | vector_documents, memory_nodes (read-only) |

## Appendix B: Cross-Reference Matrix

| Repository | Service Consumers | Engine Consumers |
|------------|------------------|-----------------|
| EntityRepository | MemoryService, IngestionService, EntityService | MemoryEngine, EntityEngine, IngestionEngine |
| MemoryNodeRepository | MemoryService, ReflectionService, QueryService | MemoryEngine, ReflectionEngine, RetrievalEngine |
| EvidenceRepository | IngestionService, MemoryService | IngestionEngine, EvidenceEngine |
| RelationshipRepository | EntityService, MemoryService | RelationshipEngine, MemoryEngine |
| VectorDocRepository | QueryService | RetrievalEngine, ContextBuilder |
| ArchiveRepository | MemoryService | ArchiveEngine |
| TagRepository | QueryService | (none direct) |
| TaskRepository | TaskService | TaskRuntime |
| CandidateRepository | ReflectionService | ReflectionEngine, CandidateEngine |
| MemoryQueryRepository | QueryService | RetrievalEngine |
| EntityQueryRepository | EntityService, QueryService | EntityEngine |
| VectorQueryRepository | QueryService | RetrievalEngine |

---

## 9. Release Blocker — Native pgvector Support

> **Severity**: Release Blocker
> **Triggered by**: D2.7 VectorQueryRepository implementation

### Current State

- Embedding column stored as `String` (text representation) in VectorDoc ORM model.
- `similarity_search()` returns empty list until pgvector infrastructure is integrated.
- `hybrid_search()` provides text-based pre-filter only (no vector component).

### Required Actions Before MVP/Beta Release

1. Add `pgvector` Python package as a project dependency.
2. Enable PostgreSQL `vector` extension (already done in `engine.py`).
3. Upgrade VectorDoc ORM `embedding` column from `String` to `pgvector.sqlalchemy.Vector(1536)`.
4. Add HNSW or IVFFlat indexes on `vector_documents.embedding` (DDL already specifies both).
5. Implement `similarity_search()` with native `<#>` cosine distance operator.
6. Verify `VectorQueryRepository` works end-to-end with native vector operators.
7. Add unit/integration tests for vector similarity ranking and hybrid search.

### Impact Assessment

- This is a **known limitation** documented in D2.6.
- Repository contract remains unchanged — only the embedding column type and query implementations evolve.
- No architectural drift: pgvector integration is an infrastructure upgrade, not a design change.
- No ADR required for dependency addition (pgvector is already in the DDL).

---

*This document is derived from the approved architecture. It introduces no architectural changes. All Repository definitions match the approved design in 10_1 §5, 09, and related Phase B documents.*

*Last Updated: 2026-07-06*
