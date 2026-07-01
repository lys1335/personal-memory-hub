# Personal AI Memory Hub — Testing Implementation Design

> **Version**: 1.0
> **Date**: 2026-07-01
> **Phase**: Phase B-8 — Implementation Testing
> **Status**: Draft
> **Author**: System Architecture Group

---

## 1. Purpose

This document defines the **Testing Architecture** for the Personal AI Memory Hub.

It establishes:

- Testing Philosophy and Principles
- Testing Responsibilities per Layer
- Mock Strategy and Boundaries
- Deterministic vs Evaluation Testing
- Test Data Management
- Regression Strategy
- Future Extensibility

This document is the **single source of truth** for all testing practices in the project. It applies to every developer and every AI coding agent.

**引用**：10_1 §2.1, 10_1 §13 (Project Memory Philosophy)

---

## 2. Testing Philosophy

### 2.1 Project Testing Principles

> **Principle**: Tests are design assets, not code artifacts. They are generated from design documents, validated by humans, and maintained as living documentation.

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **Testing Mirrors Architecture** | Test structure mirrors the five-layer architecture: Entry / Service / Engine / Repository / Integration. Each layer has its own test scope. |
| 2 | **Single Responsibility Testing** | Each test validates a single responsibility. One assertion per test concept. Tests are small, focused, and fast. |
| 3 | **Test Escalation Principle** | Fast deterministic tests first. Slow evaluation tests last. CI gates on deterministic tests only. |
| 4 | **Mock Mirrors Layer Boundary** | Mocks exist only at layer boundaries. Never mock within a layer. Never mock the current test object. |
| 5 | **Avoid Over-Mocking** | Mock only external dependencies (Database, LLM API, File System). Do not mock internal classes, interfaces, or collaborators that are part of the same layer. |
| 6 | **Prefer Behavioral Verification** | Verify observable behavior (state changes, events published, outcomes) rather than internal method call sequences. |
| 7 | **Deterministic-by-Default** | All unit and integration tests must be deterministic. Non-determinism is the exception, not the rule. |
| 8 | **Stable CI Principle** | CI pipeline relies exclusively on deterministic tests. Evaluation tests are optional gates, never blocking. |
| 9 | **Tests Are Generated from Design** | Test cases derive from design documents (10_1~10_7), not from code inspection. Design precedes test implementation. |
| 10 | **Test Cases Are Design Assets** | Test cases are part of the design documentation. They express expected behavior in executable form. |
| 11 | **AI Generates, Human Reviews** | AI agents generate test scaffolding and initial test cases. Human reviewers validate correctness, completeness, and architectural alignment. |
| 12 | **Test Review Before Coverage Review** | Review test quality (assertion clarity, isolation, determinism) before reviewing test coverage percentage. |
| 13 | **Test Data Is a First-Class Artifact** | Test data (fixtures, scenarios, golden datasets) is version-controlled, reviewed, and treated as design documentation. |
| 14 | **Golden Dataset Principle** | Golden datasets define the expected output for known inputs. They are the ground truth for regression testing. |
| 15 | **Regression Suite Is Living Documentation** | Every bug fix adds a regression test. The regression suite documents the project's learned mistakes. |
| 16 | **Testability Is an Architectural Requirement** | If a component cannot be tested in isolation, its architecture is flawed. Testability drives design decisions. |
| 17 | **Quality Is Designed, Not Inspected** | Quality comes from good architecture, clear contracts, and deterministic design. Testing verifies quality, it does not create it. |
| 18 | **Semantic Equivalence Principle** | Tests validate semantic equivalence (meaning, state, behavior), not literal string matching. Especially critical for LLM-generated content. |
| 19 | **Validate Outcomes, Not Wording** | Verify the outcome (evidence stored, memory captured, entity resolved) rather than exact text output. |

**AI Output Validation Targets**:

When validating AI-generated content, tests must verify:

| Verify | Do Not Verify |
|--------|---------------|
| Evidence stored in repository | Exact wording of generated text |
| Schema compliance of output | Natural language fluency |
| Memory state transitions | Verbatim text matching |
| Entity state (resolved/created/merged) | Token-level similarity |
| Relationship graph integrity | Prompt template exactness |
| Observable behavior (events, side effects) | Implementation details |

---

## 3. Testing Responsibilities by Layer

Each layer has a clearly defined testing scope. Tests must not cross layer boundaries in their assertions.

### 3.1 Entry Layer Tests

**Responsible for**:

| Test Type | Scope |
|-----------|-------|
| Protocol parsing | Request deserialization, header validation, content negotiation |
| DTO transformation | Bidirectional conversion between public DTO and internal request/result |
| Authentication | Credential validation, token verification, identity extraction |
| Authorization | Capability permission checks, role-to-capability mapping |
| Request validation | Three-layer validation: Protocol → Capability → Domain |
| Response shaping | Protocol-specific response format (REST JSON, MCP tool result, CLI output) |
| Capability discovery | GET /capabilities endpoint returns correct catalog |
| Error formatting | Error codes mapped to protocol-specific representations |

**Not responsible for**:

| Excluded | Reason |
|----------|--------|
| Business logic validation | Belongs to Service layer tests |
| Engine algorithm correctness | Belongs to Engine layer tests |
| Database query correctness | Belongs to Repository layer tests |
| LLM output quality | Belongs to Integration / Evaluation tests |

### 3.2 Service Layer Tests

**Responsible for**:

| Test Type | Scope |
|-----------|-------|
| Use case orchestration | End-to-end workflow correctness within a Service |
| Transaction boundaries | Commit/rollback behavior, per-chunk vs whole-batch |
| Service independence | Verify no synchronous cross-Service calls |
| Domain event publishing | Events published after successful operations |
| Error model compliance | MemoryResult / ImportResult usage, exception not used for control flow |
| Recovery policy | ContinueOnError, StopOnFatal behavior |
| Capability routing | Correct Service method invoked for each capability |
| Command / Query separation | Commands return Id, Queries return State |

**Not responsible for**:

| Excluded | Reason |
|----------|--------|
| Protocol-level details | Belongs to Entry layer tests |
| Engine algorithm internals | Belongs to Engine layer tests |
| Database SQL correctness | Belongs to Repository layer tests |

### 3.3 Engine Layer Tests

**Responsible for**:

| Test Type | Scope |
|-----------|-------|
| Domain capability correctness | MemoryEngine, EntityEngine, QueryEngine, ReflectionEngine |
| Stateless behavior | Same input → same output, no hidden state |
| DAG compliance | Engine dependency graph is acyclic |
| Domain knowledge production | Engine returns domain objects, not DTOs |
| Domain invariant enforcement | EntityEngine owns all entity invariants (G-025) |
| Input/output contracts | Engine method signatures and return types |

**Not responsible for**:

| Excluded | Reason |
|----------|--------|
| HTTP/transport details | Belongs to Entry layer tests |
| Persistence mechanics | Belongs to Repository layer tests |
| User-facing formatting | Belongs to Entry layer tests |

### 3.4 Repository Layer Tests

**Responsible for**:

| Test Type | Scope |
|-----------|-------|
| CRUD correctness | Insert, read, update, delete operations |
| Query correctness | Complex queries, joins, aggregations |
| Transaction support | Isolation levels, rollback behavior |
| Persistence boundary | Repository returns Domain Objects, never Projection or DTO |
| Schema compliance | Stored data matches physical design (09) |

**Not responsible for**:

| Excluded | Reason |
|----------|--------|
| Business logic | Repository is persistence only (G-013) |
| Query planning | Belongs to QueryService / QueryEngine |
| Ranking / scoring | Belongs to Engine layer |

### 3.5 Integration Tests

**Responsible for**:

| Test Type | Scope |
|-----------|-------|
| Cross-layer flow | Entry → Service → Engine → Repository → Database |
| External service integration | LLM API, vector store, file system |
| End-to-end scenario | Full user journey from request to response |
| Task Runtime integration | Submit → Execute → Complete / Retry / Dead |
| Domain event flow | Event → Dispatcher → Registry → Factory → New Task |

**Not responsible for**:

| Excluded | Reason |
|----------|--------|
| Unit-level assertions | Too slow for integration scope |
| Protocol-specific details | Belongs to Entry layer tests |

### 3.6 End-to-End Tests

**Responsible for**:

| Test Type | Scope |
|-----------|-------|
| MVP scenario validation | Complete user stories from start to finish |
| Multi-adapter verification | Same capability works across REST / CLI / SDK |
| Performance baseline | Response time, throughput under load |
| Upgrade path validation | Migration from one version to another |

---

## 4. Mock Strategy

### 4.1 Core Mock Principles

> **Mock mirrors layer boundary.** Mocks isolate responsibilities between architectural layers, not within them.

| Rule | Description |
|------|-------------|
| **Mock at boundaries** | Mock external dependencies: Database, LLM API, File System, HTTP endpoints |
| **Never mock within a layer** | If two classes are in the same layer, test them as real collaborators |
| **Never mock the current test object** | A class is never mocked in its own tests |
| **Real objects over mocks** | Prefer real implementations when they are fast and deterministic |

### 4.2 What to Mock

| Dependency | Mock? | Reason |
|------------|-------|--------|
| Database (PostgreSQL / Supabase) | ✅ Yes | External, slow, non-deterministic state |
| LLM API (OpenRouter / local) | ✅ Yes | External, slow, non-deterministic output |
| File System | ✅ Yes | External, state-dependent |
| HTTP endpoints | ✅ Yes | External, network-dependent |
| Vector Store (pgvector) | ✅ Yes | External, slow |
| Task Runtime | ⚠️ Selective | Mock only the scheduler; test Task execution directly |
| Domain Events | ⚠️ Selective | Mock event dispatcher; test event publication |
| Internal Service collaborator | ❌ No | Same layer, real objects preferred |
| Internal Engine collaborator | ❌ No | Same layer, real objects preferred |
| Configuration | ⚠️ Selective | Use test configuration, not mocks |

### 4.3 Prohibited Mocking

| Prohibited | Reason |
|------------|--------|
| **Mock Repository Database** | Use in-memory database or test fixtures instead. Mocking the database hides persistence bugs. |
| **Over Mock** | Mocking every interface makes tests fragile and disconnected from reality. |
| **Mock Current Test Object** | A class should never mock itself. This creates circular dependencies in test logic. |
| **Mock for Convenience** | If mocking feels necessary, the architecture may need refinement (G-016, G-017). |

### 4.4 Mock Alternatives

| Instead of Mocking | Use |
|--------------------|-----|
| Mock Database | In-memory SQLite / Testcontainers / Fixed fixtures |
| Mock LLM | Fixed prompt templates with deterministic output expectations |
| Mock File System | Temporary directory with controlled fixtures |
| Mock HTTP | WireMock / local test server |

---

## 5. Deterministic vs Evaluation Testing

### 5.1 Deterministic Tests

> **Deterministic tests are the CI gate.** Every deterministic test must pass before any evaluation test is considered.

Deterministic tests have:

| Property | Description |
|----------|-------------|
| **Same input → same output** | No randomness, no time-dependence, no external state |
| **Fast execution** | Sub-second per test |
| **Binary result** | Pass / Fail, no ambiguity |
| **CI-blocking** | Required for every merge / PR |

**Examples**:

- Evidence stored with correct schema
- Memory captured with correct L-level
- Entity resolved to correct EntityID
- Relationship graph integrity maintained
- Query returns expected count and continuation token
- Domain event published with correct payload
- Task submitted with correct metadata

### 5.2 Evaluation Tests (LLM Evaluation)

> **Evaluation tests are non-blocking quality signals.** They measure semantic quality, not correctness.

Evaluation tests have:

| Property | Description |
|----------|-------------|
| **Semantic judgment** | Assesses quality of LLM-generated content |
| **Non-deterministic** | May vary across runs or models |
| **Slow execution** | Seconds to minutes per test |
| **Non-blocking** | Optional gate in CI, manual review recommended |

**Examples**:

- Reflection output improves explanatory power
- Summarization captures key facts without distortion
- Entity merge decision is semantically correct
- Query ranking produces relevant results

### 5.3 CI Strategy

```
CI Pipeline
  ├── Stage 1: Deterministic Tests (blocking)
  │     ├── Unit Tests (Engine, Repository)
  │     ├── Service Tests (orchestration, events)
  │     ├── Entry Tests (DTO, validation, auth)
  │     └── Integration Tests (cross-layer, no external deps)
  │
  ├── Stage 2: Evaluation Tests (non-blocking, optional)
  │     ├── LLM quality assessment
  │     ├── Semantic equivalence checks
  │     └── Golden dataset comparison
  │
  └── Stage 3: E2E (manual or scheduled)
        ├── MVP scenario validation
        ├── Multi-adapter verification
        └── Performance baseline
```

---

## 6. Test Data Management

### 6.1 Test Data Categories

| Category | Description | Version Controlled |
|----------|-------------|-------------------|
| **Shared Fixtures** | Reusable base data for common scenarios | ✅ Yes |
| **Scenario Data** | Test-specific data for individual test cases | ✅ Yes |
| **Golden Dataset** | Known input-output pairs for regression | ✅ Yes |
| **Seed Data** | Initial population for integration tests | ✅ Yes |
| **Generated Data** | Programmatically created data (not reviewed) | ❌ No (generated at test time) |

### 6.2 Shared Fixtures

Shared fixtures are the foundation of test data. They represent the minimum viable memory graph for testing.

```
Shared Fixtures
├── EvidenceFixtures
│   ├── valid_evidence.json          # Well-formed evidence with all required fields
│   ├── minimal_evidence.json        # Minimum required fields
│   └── invalid_evidence.json        # Missing required fields
├── MemoryFixtures
│   ├── l0_memory.json               # Raw L0 memory with evidence
│   ├── l1_summary.json              # Summarized L1 memory
│   └── archived_memory.json         # Archived memory with recovery baseline
├── EntityFixtures
│   ├── created_entity.json          # Entity in Created state
│   ├── active_entity.json           # Entity in Active state
│   └── merged_entity.json           # Entity in Merged state
└── RelationshipFixtures
    ├── simple_relationship.json     # One-to-one relationship
    └── complex_graph.json           # Multi-node relationship graph
```

### 6.3 Scenario Data

Scenario data represents complete test scenarios. Each scenario documents a specific user story or edge case.

```
Scenario Data
├── ingestion_scenarios
│   ├── single_evidence_capture.json
│   ├── batch_ingestion_partial_failure.json
│   └── evidence_with_missing_fields.json
├── query_scenarios
│   ├── simple_retrieval.json
│   ├── paginated_search.json
│   └── projection_with_continuation.json
├── reflection_scenarios
│   ├── incremental_propagation.json
│   ├── pyramid_evolution.json
│   └── recovery_baseline_preservation.json
└── entity_scenarios
    ├── entity_resolution.json
    ├── merge_with_reference_migration.json
    └── alias_collision.json
```

### 6.4 Golden Dataset

Golden datasets define the expected output for known inputs. They are the ground truth for regression testing.

| Property | Description |
|----------|-------------|
| **Input** | Known, versioned input data |
| **Expected Output** | Known, versioned expected result |
| **Purpose** | Detect unintended behavioral changes |
| **Maintenance** | Updated only when design changes, not when implementation changes |

**Golden Dataset Structure**:

```
golden_datasets/
├── ingestion/
│   ├── valid_batch.input.json       # Input: batch of valid evidence
│   ├── valid_batch.expected.json    # Expected: 3 memories captured, 1 rejected
│   └── valid_batch.actual.json      # Generated at test time for comparison
├── query/
│   ├── search_by_keyword.input.json
│   ├── search_by_keyword.expected.json
│   └── search_by_keyword.actual.json
└── entity/
    ├── resolve_identity.input.json
    ├── resolve_identity.expected.json
    └── resolve_identity.actual.json
```

### 6.5 Test Data Evolution

> **Test data evolves with design.** When a design document changes, corresponding test data must be updated.

| Design Change | Test Data Action |
|---------------|-----------------|
| New Capability added | Add scenario data for the new capability |
| Schema changed | Update fixtures to match new schema |
| Golden dataset output changed | Review: was this a design change or a bug? |
| New constraint added | Add fixture data that violates the constraint |

---

## 7. Regression Strategy

### 7.1 Regression as Executable Project Memory

> **Regression tests are executable project memory.** They capture the project's learned mistakes in a form that can be automatically verified.

Every bug fix **must** include a regression test that:

1. Reproduces the exact conditions that caused the bug
2. Asserts the corrected behavior
3. Documents the bug in test comments (reference issue / discussion)
4. Is added to the regression suite before the fix is merged

### 7.2 Regression Suite Properties

| Property | Description |
|----------|-------------|
| **Growing** | The regression suite grows with every bug fix. It never shrinks. |
| **Protected** | Regression tests are never modified to pass a broken implementation. |
| **Contract-focused** | Regression tests protect contracts (API, schema, behavior), not implementation details. |
| **Executable documentation** | Reading regression tests tells the story of what went wrong and how it was fixed. |

### 7.3 Regression Test Categories

| Category | Scope | Example |
|----------|-------|---------|
| **API Regression** | Entry layer contract stability | REST endpoint returns correct schema after refactoring |
| **Schema Regression** | Database schema compliance | New migration doesn't break existing data |
| **Behavioral Regression** | Service-level behavior | Memory capture with missing evidence is rejected |
| **Entity Regression** | Entity invariants | Merge doesn't alter L0 memory facts |
| **Query Regression** | Query determinism | Same query on unchanged data produces same results |
| **Reflection Regression** | Memory Pyramid evolution | Reflection doesn't destroy L0 protection |

### 7.4 Regression Protection Principle

> **Regression protects Contract, not Implementation.**

```
Regression Test
  ├── Protects: API contract, schema, observable behavior
  └── Does NOT protect: Internal method names, private field names, implementation details
```

---

## 8. Future Extensibility

### 8.1 Testability Is an Architectural Requirement

> **If a component cannot be tested in isolation, its architecture is flawed.**

Testability drives design decisions:

| Design Question | Testability Check |
|-----------------|-------------------|
| Should this be a Service or an Engine? | Can it be tested without external dependencies? |
| Should this interface be mocked or made real? | Does mocking hide a layer boundary violation? |
| Is this method too large? | Can it be tested with focused assertions? |
| Are dependencies too tight? | Can the component be tested in isolation? |

### 8.2 New Capability Requires New Test Ownership

When adding a new capability:

| Step | Action |
|------|--------|
| 1 | Define test scope in the capability design document |
| 2 | Create shared fixtures for the new capability's data |
| 3 | Write deterministic tests before implementation |
| 4 | Add scenario data for at least one positive and one negative case |
| 5 | Register new capability in golden dataset if applicable |
| 6 | Update regression suite if the capability addresses a known gap |

### 8.3 Testing Standards Are Project-wide Standards

Testing standards apply equally to:

| Audience | Standard |
|----------|----------|
| Human developers | Same test principles, same mock strategy, same deterministic requirement |
| AI coding agents | Same test principles, same mock strategy, same deterministic requirement |
| Code review | Test quality reviewed before test coverage |
| Architecture review | Testability assessed alongside architectural decisions |

### 8.4 Quality Is Designed, Not Inspected

> **Quality comes from good architecture, clear contracts, and deterministic design.**

Testing verifies quality; it does not create it. The design must enable quality:

| Design Element | Quality Contribution |
|----------------|---------------------|
| Clear layer boundaries | Enables focused testing per layer |
| Capability-based interface | Enables deterministic test inputs |
| Domain events (not direct calls) | Enables event-based verification |
| Command/Query separation | Enables clear test expectations |
| Stable Result Contract | Enables golden dataset testing |
| Deterministic Engine design | Enables unit test isolation |

---

## 9. Test Directory Structure

```
tests/
├── fixtures/                    # Shared fixtures (version controlled)
│   ├── evidence/
│   ├── memory/
│   ├── entity/
│   └── relationship/
├── scenarios/                   # Scenario data (version controlled)
│   ├── ingestion/
│   ├── query/
│   ├── reflection/
│   └── entity/
├── golden/                      # Golden datasets (version controlled)
│   ├── ingestion/
│   ├── query/
│   └── entity/
├── unit/                        # Unit tests (per layer)
│   ├── entry/
│   ├── service/
│   ├── engine/
│   └── repository/
├── integration/                 # Integration tests
│   ├── cross_layer/
│   ├── task_runtime/
│   └── domain_events/
├── evaluation/                  # Evaluation tests (non-blocking)
│   ├── llm_quality/
│   └── semantic_equivalence/
└── e2e/                         # End-to-end tests
    ├── mvp_scenarios/
    ├── multi_adapter/
    └── performance/
```

---

## 10. Checklist

### 10.1 P0 — Must Have

| # | Check Item | Status |
|---|------------|--------|
| P0-1 | **Testing Mirrors Architecture** | ✅ Five-layer test structure defined |
| P0-2 | **Deterministic Tests as CI Gate** | ✅ Blocking on deterministic only |
| P0-3 | **Mock at Layer Boundaries** | ✅ No intra-layer mocking |
| P0-4 | **Golden Dataset for Regression** | ✅ Version-controlled golden datasets |
| P0-5 | **Test Data as First-Class Artifact** | ✅ Shared fixtures, scenario data, golden datasets |
| P0-6 | **Semantic Equivalence over Literal Match** | ✅ Validate outcomes, not wording |
| P0-7 | **Testability as Architectural Requirement** | ✅ Testability drives design decisions |
| P0-8 | **Regression Suite Growing** | ✅ Every bug fix adds regression test |

### 10.2 P1 — Recommended

| # | Check Item | Status |
|---|------------|--------|
| P1-1 | **Evaluation Tests Non-Blocking** | ✅ Optional CI gate |
| P1-2 | **Shared Fixtures Library** | ✅ Reusable base data |
| P1-3 | **Test Review Before Coverage** | ✅ Quality over quantity |
| P1-4 | **AI Test Generation Workflow** | ✅ AI generates, human reviews |

### 10.3 P2 — Future

| # | Check Item | Status |
|---|------------|--------|
| P2-1 | **Performance Baseline Tests** | ✅ Throughput, latency targets |
| P2-2 | **Cross-Model Evaluation** | ✅ Test across different LLM providers |
| P2-3 | **Test Data Mutation Framework** | ✅ Automated edge-case generation |

---

## 11. Decision Summary

| # | Decision | Rationale | Reference |
|---|----------|-----------|-----------|
| 1 | **Testing Mirrors Architecture** | Five-layer structure maps to five test categories | 10_8 §3 |
| 2 | **Deterministic-by-Default** | CI must be reliable and fast | 10_8 §5.1 |
| 3 | **Mock at Layer Boundaries** | Mocks isolate responsibilities, not implementations | 10_8 §4 |
| 4 | **No Over-Mocking** | Over-mocking hides architectural flaws | 10_8 §4.3 |
| 5 | **Behavioral Verification** | Verify outcomes, not call sequences | 10_8 §2.1 (P6) |
| 6 | **Semantic Equivalence** | Validate meaning, not exact text | 10_8 §2.1 (P18) |
| 7 | **Golden Dataset Principle** | Ground truth for regression | 10_8 §6.4 |
| 8 | **Regression as Executable Memory** | Tests document learned mistakes | 10_8 §7.1 |
| 9 | **Testability Is Architectural** | Un-testable code means flawed design | 10_8 §8.1 |
| 10 | **Quality Is Designed** | Testing verifies, not creates, quality | 10_8 §8.4 |
| 11 | **AI Generates, Human Reviews** | Leverage AI for scaffolding, human for judgment | 10_8 §2.1 (P11) |
| 12 | **Test Data Evolves with Design** | Design changes require test data updates | 10_8 §6.5 |
| 13 | **Regression Protects Contract** | Not implementation details | 10_8 §7.4 |
| 14 | **Evaluation Tests Non-Blocking** | LLM quality is signal, not gate | 10_8 §5.2 |
| 15 | **New Capability Requires New Test Ownership** | Every capability needs test scaffolding | 10_8 §8.2 |
| 16 | **Test Review Before Coverage** | Quality over quantity | 10_8 §2.1 (P12) |
| 17 | **Roadmap Alignment** | Testing milestones map to 11 Milestone 5 (Testing & Stabilization) | 11 |
| 18 | **CI Testing Pipeline** | 10_8 testing principles implemented in CI strategy per 11 §8 | 11 |

---

## 12. Backport Updates

The following documents require backport updates after 10_8 is finalized:

| Document | Update Required |
|----------|----------------|
| **13_Architecture_Guidelines** | Add G-056~G-065 (Testing Guidelines) |
| **10_1_Implementation_Service_Layer** | Add testing section to Decision Summary |
| **INDEX.md** | Mark 10_8 as completed, update progress |

---

## 13. Relationship with 11_Implementation_Roadmap

| Relationship | Description |
|--------------|-------------|
| Milestone 5 (Testing & Stabilization) | Directly implements 10_8 testing architecture |
| CI Strategy | 10_8 testing principles implemented in CI pipeline |
| Regression Suite | 10_8 §7 regression strategy executed per milestone |
| Golden Datasets | 10_8 §6.4 golden datasets maintained per milestone |

---

## 14. Relationship with Other Documents

| Document | Relationship |
|----------|-------------|
| **10_1** | Defines layered architecture that 10_8 mirrors in test structure |
| **10_2** | MemoryService test scope: capture, correct, archive, restore |
| **10_3** | QueryService test scope: determinism, side-effect free, continuation |
| **10_4** | ReflectionService test scope: memory pyramid evolution, L0 protection |
| **10_5** | EntityService test scope: entityID stability, merge, reference migration |
| **10_6** | TaskRuntime test scope: retry, recovery, idempotency, event chaining |
| **10_7** | API Entry test scope: DTO transformation, validation, auth, capability discovery |
| **08_Implementation_Architecture** | Layer boundaries that 10_8 uses for mock strategy |
| **13_Architecture_Guidelines** | G-015 (Side-Effect Free Query), G-016 (Query Determinism) tested by 10_8 |

---

## Appendix A: Terminology

| Term | Description | Source |
|------|-------------|--------|
| Deterministic Test | Same input → same output, CI-blocking | 10_8 §5.1 |
| Evaluation Test | Semantic quality assessment, non-blocking | 10_8 §5.2 |
| Golden Dataset | Known input-output pair for regression | 10_8 §6.4 |
| Shared Fixture | Reusable base test data | 10_8 §6.2 |
| Scenario Data | Test-specific data for individual cases | 10_8 §6.3 |
| Regression Test | Reproduces and prevents recurrence of a bug | 10_8 §7 |
| Semantic Equivalence | Same meaning, different wording | 10_8 §2.1 (P18) |
| Mock Boundary | Layer boundary where mocking is allowed | 10_8 §4 |
| Test Escalation | Fast deterministic tests first, slow evaluation tests last | 10_8 §2.1 (P3) |

---

## Appendix B: Document Change Record

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-07-01 | Initial version — Testing Philosophy (19 principles), Testing Responsibilities (6 layers), Mock Strategy, Deterministic vs Evaluation, Test Data, Regression Strategy, Future Extensibility | ✅ Confirmed |
| 1.1 | 2026-07-01 | Phase B-9 修订：(1) Decision Summary 补充 17~18（Roadmap Alignment / CI Testing Pipeline） (2) 新增 Relationship with 11_Implementation_Roadmap | ✅ Confirmed |

---

*This document is a Living Testing Specification. It evolves with the project.*

*Subsequent Phase B documents (10_9~10_N) that introduce new capabilities must define their test scope in this document's framework.*
