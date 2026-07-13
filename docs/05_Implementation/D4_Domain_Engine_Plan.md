# Personal Memory Hub — D4 Domain Engine Plan

> **Version**: 1.0
> **Date**: 2026-07-13
> **Phase**: Phase D — Document-Driven Implementation
> **Stage**: D4 — Domain Engine Layer
> **Substage**: D4 — Planning
> **Status**: ⏳ Planned

---

## 1. Purpose

### 1.1 Objectives

Implement the complete **Domain Engine Layer** for the Personal Memory Hub project. D4 establishes the domain core that encapsulates business algorithms, domain rules, and domain consistency mechanisms.

D4 objectives:

- Implement domain engines as stable facades with private internal composition
- Each Engine owns domain rules, domain algorithms, and domain consistency
- Engines are stateless and return domain results (not protocol results)
- One Domain Capability → One Engine
- Engine boundaries follow domain capability, not CRUD or repository structure
- Services remain the sole business orchestration layer
- Engines do NOT call other Engines

### 1.2 Scope

D4 covers **Domain Engine implementation only**:

- Domain Engine infrastructure (base engine, composition patterns)
- Individual domain engines (defined by D3 Service dependencies)
- Engine internal composition (Components, Policies, Strategies — all private)
- Engine public contract (stable facade interface)
- Engine testing (domain rule verification, invariant testing)
- Engine error handling (domain exceptions, consistency violations)

### 1.3 Out of Scope

D4 explicitly excludes:

- **Service Layer changes** — Services are Frozen (D3 🧊)
- **Repository Layer changes** — Repositories are Frozen (D2 🧊)
- **Entry/API Layer** — No protocol adapters (D5)
- **Infrastructure changes** — No new infrastructure (D1 🧊)
- **Architecture redesign** — No changes to frozen layers
- **Individual Engine documents** — D4 Plan is the single planning document; per-Engine architecture documents are deferred

---

## 2. Layer Position

### 2.1 Architecture Stack

```
Entry (D5)
  ↓
Service (D3 🧊 Frozen)
  ↓
Engine (D4 — Current)
  ↓
Repository (D2 🧊 Frozen)
  ↓
Database
```

### 2.2 Layer Dependencies

| Layer | Depends On | Owned By |
|-------|-----------|----------|
| Entry | Service | D5 |
| **Service** | **Engine, Repository** | **D3 🧊** |
| **Engine** | **Repository** | **D4** |
| Repository | Database | D2 🧊 |

**Constraint**: Engine may only call Repository. Engine must NOT call Service. Engine must NOT call other Engines.

### 2.3 Engine Position

Engine is the **Domain Core**. It sits between Service (orchestration) and Repository (persistence).

- Service calls Engine for domain computation
- Engine calls Repository for data access
- Engine never calls Service
- Engine never calls other Engines

---

## 3. Engine Principles

### 3.1 Core Principles

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **Engine is a Stable Facade** | Internal composition (Components, Policies, Strategies) is private. Service depends only on Engine public contract. |
| 2 | **One Capability → One Engine** | Engine boundaries follow domain capability, not CRUD or repository structure. |
| 3 | **Stateless Engine** | Engine has no mutable state. All state comes from Repository reads. |
| 4 | **Domain Result, Not Protocol Result** | Engine returns domain-level results (DomainResult, DomainError), not HTTP/status codes or DTOs. |
| 5 | **Composition Over Inheritance** | Internal composition uses composition. Inheritance is prohibited for Engine implementation. |
| 6 | **No Cross-Engine Calls** | Engine A must NOT call Engine B. Service is the only orchestrator. |
| 7 | **Domain Consistency, Not Business Consistency** | Engine ensures domain-level invariants. Service ensures business-level consistency. |
| 8 | **Algorithm Isolation** | Domain algorithms are isolated within Engine. Service coordinates, Engine computes. |

### 3.2 Engine vs Service Boundary

| Aspect | Service (D3 🧊) | Engine (D4) |
|--------|-----------------|-------------|
| Role | Business orchestrator | Domain computation |
| Owns | Validation, transaction, workflow, repository coordination | Domain rules, domain algorithms, domain consistency |
| Calls | Repository (directly or via Engine) | Repository only |
| Calls Other | No (Service Independence Principle) | No (Engine Collaboration Rule) |
| Returns | Business Result / Execution Result | Domain Result |
| State | Stateless | Stateless |
| Composition | DI wiring, BaseService | Private Components, Policies, Strategies |

### 3.3 Engine vs Repository Boundary

| Aspect | Repository (D2 🧊) | Engine (D4) |
|--------|-------------------|-------------|
| Role | Persistence abstraction | Domain computation |
| Owns | CRUD, data access, persistence consistency | Domain rules, domain algorithms |
| Calls | Database | Repository |
| Returns | Domain Model entities | Domain Result |
| Logic | None (persistence only) | Full domain logic |

---

## 4. Engine Responsibilities

### 4.1 What Engine Owns

Engine owns:

- **Domain rules** — Business rules that apply to domain data
- **Domain algorithms** — Computational logic (merge resolution, consistency checks, inference)
- **Domain consistency** — Invariants within the domain layer
- **Domain error classification** — Domain-specific error types

### 4.2 What Engine Does NOT Own

Engine does NOT own:

- **Workflow** — Service orchestrates multi-step workflows
- **Validation** — Service owns business validation (G-105)
- **Transaction** — Service owns transaction boundaries (G-106)
- **Persistence** — Repository owns data access
- **DTO** — Service/Entry owns DTO transformation
- **Protocol** — Entry owns serialization/transport
- **Authentication/Authorization** — Entry owns security

---

## 5. Engine Composition

### 5.1 Public Contract

```
Engine (Public Facade)
├── method1(...) → DomainResult
├── method2(...) → DomainResult
└── method3(...) → DomainResult
```

The Engine public contract is stable. Service depends only on this contract.

### 5.2 Internal Composition (Private)

```
Engine (Facade)
├── ComponentA (private)
├── PolicyB (private)
├── StrategyC (private)
├── ComponentD (private)
└── PolicyE (private)
```

Internal composition is **private**. Service never depends on internal Components, Policies, or Strategies.

Internal composition may change without ADR, as long as the public contract remains stable.

### 5.3 Composition Rules

| Rule | Description |
|------|-------------|
| **Private internals** | Components, Policies, Strategies are implementation details |
| **No external visibility** | Internal classes are not exposed in Engine public API |
| **Composition over inheritance** | Use composition. Inheritance prohibited. |
| **Stable facade** | Public contract is the only dependency point for Service |
| **Evolution freedom** | Internal composition may evolve without ADR |

---

## 6. Engine Collaboration Rules

### 6.1 No Cross-Engine Calls

**Engine must NOT call other Engines.**

This is a hard architectural constraint.

```
Correct:
Service
  ↓
  ├→ Engine A
  ├→ Engine B
  └→ Engine C

Incorrect:
Service
  ↓
Engine A
  ↓
Engine B        ← PROHIBITED
  ↓
Engine C        ← PROHIBITED
```

**Rationale**: Prevents God Engine anti-pattern. Preserves clear responsibility boundaries. Service is the only business orchestration layer.

### 6.2 Internal Coordination

Engine may coordinate its own internal Components, but not other Engines.

```
Engine A
├── ComponentA1 (coordinates internally)
├── ComponentA2 (coordinates internally)
└── ComponentA3 (coordinates internally)
```

Internal coordination is private. Service sees Engine A as a single unit.

### 6.3 Service as Sole Orchestrator

Service coordinates between Engines:

```
MemoryService.capture()
  ↓
  ├→ EntityEngine.resolve()      // Domain rule
  ├→ MemoryEngine.store()         // Domain algorithm
  └→ RelationshipEngine.link()    // Domain consistency
```

Service decides:
- Which Engines to call
- In what order
- How to combine results
- Transaction boundaries

Engine decides:
- How to compute domain rules
- How to ensure domain consistency
- What domain algorithm to apply

---

## 7. Transaction & Consistency Boundaries

### 7.1 Transaction Ownership

| Layer | Transaction Responsibility |
|-------|---------------------------|
| **Service** | Business transaction (commit/rollback, multi-Repository coordination) |
| **Engine** | Transaction-agnostic (no transaction awareness) |
| **Repository** | Persistence transaction (per-entity commit) |

**Rule**: Transaction belongs to Service. Engine is transaction-agnostic.

### 7.2 Consistency Ownership

| Layer | Consistency Type |
|-------|-----------------|
| **Service** | Business Consistency (multi-step workflow correctness) |
| **Engine** | Domain Consistency (invariant enforcement, domain rules) |
| **Repository** | Persistence Consistency (data integrity at storage level) |

**Rule**: Each layer owns its consistency scope. No layer crosses its consistency boundary.

### 7.3 Consistency Examples

| Scenario | Service Consistency | Engine Consistency | Repository Consistency |
|----------|-------------------|-------------------|----------------------|
| Memory capture | Validates input, manages transaction | Ensures memory invariants | Persists data correctly |
| Entity merge | Coordinates merge workflow | Resolves identity conflicts | Maintains referential integrity |
| Reflection | Manages proposal lifecycle | Applies domain rules | Stores reflection result |

---

## 8. Testing Strategy

### 8.1 Test Layer Responsibilities

| Test Layer | Verifies | Owned By |
|------------|----------|----------|
| Entry Test | Protocol adaptation, DTO transformation | D5 |
| **Service Test** | **Workflow, transaction, orchestration** | **D3.8** |
| **Engine Test** | **Domain rules, invariants, algorithms** | **D4** |
| Repository Test | Data access, persistence correctness | D2 |
| Integration Test | Cross-layer interaction | D6 |

### 8.2 Engine Testing Principles

Engine testing is **invariant-driven**.

| Principle | Description |
|-----------|-------------|
| **Invariant-First** | Tests verify domain invariants, not implementation details |
| **Black-Box** | Engine tested via public contract only |
| **Stateless Verification** | Same input → same Domain Result (deterministic) |
| **Domain Error Classification** | Errors classified per D3.7 Error Taxonomy |
| **No Cross-Engine Tests** | Engine tests verify Engine in isolation |

### 8.3 Engine Test Categories

| Category | Verifies | Example |
|----------|----------|---------|
| **Domain Rule Tests** | Business rules applied correctly | Merge conflict resolution |
| **Invariant Tests** | Domain invariants preserved | Memory immutability |
| **Algorithm Tests** | Domain algorithms produce correct results | Entity identity resolution |
| **Error Classification Tests** | Errors classified per Taxonomy | DomainIntegrityError for invariant violation |
| **Statelessness Tests** | Engine produces same result for same input | Deterministic verification |
| **Boundary Tests** | Engine-Repository boundary respected | No Service calls from Engine |

### 8.4 Testing Dependencies

```
Engine Test
├── Engine (SUT)
├── Repository Mock (returns Domain Models)
├── Domain Result Assertion
└── Domain Error Assertion
```

Engine tests mock Repository. Engine tests do NOT call other Engines. Engine tests do NOT involve Service.

---

## 9. Documentation Strategy

### 9.1 D4 Plan as Single Document

D4 uses a **single planning document** (`D4_Domain_Engine_Plan.md`).

Individual Engine architecture documents are **deferred** to subsequent sessions.

### 9.2 Future Per-Engine Documents

When individual Engine documents are created, each will follow the pattern:

```
D4.x_<EngineName>.md
├── Purpose
├── Domain Rules
├── Domain Algorithms
├── Public Contract
├── Internal Composition (overview)
├── Domain Error Classification
├── Invariants
├── Test Strategy
└── References
```

These documents are **not created in D4 Plan**. They will be created after D4 Plan is frozen.

### 9.3 Documentation Alignment

D4 documentation aligns with:

- **D3 Service contracts** — Engine public contract must match Service expectations
- **D2 Repository contracts** — Engine uses Repository interfaces (frozen)
- **D3.7 Error Taxonomy** — Engine errors classified per frozen taxonomy
- **D3.8 Testing principles** — Engine tests follow service test architecture
- **D3.9 Documentation standards** — Metadata, cross-references, terminology

---

## 10. Engine Inventory (Planned)

### 10.1 Engine Candidates

Based on D3 Service dependencies, the following Engines are anticipated:

| Engine | Domain Capability | Likely Service Owner | Status |
|--------|------------------|---------------------|--------|
| **Entity Engine** | Entity identity resolution, merge analysis | EntityService | Planned |
| **Memory Engine** | Memory domain rules, consistency checks | MemoryService | Planned |
| **Relationship Engine** | Relationship graph analysis, link validation | EntityService, MemoryService | Planned |
| **Reflection Engine** | Reflection domain algorithms, proposal generation | ReflectionService | Planned |
| **Search Engine** | Search domain algorithms, ranking | QueryService | Planned |
| **Projection Engine** | Projection domain algorithms | QueryService | Planned |

**Note**: This inventory is **provisional**. Final Engine list will be determined during D4 implementation based on D3 Service dependencies.

### 10.2 Engine Naming Convention

Engines follow the naming convention:

```
<DomainCapability>Engine
```

Examples: `EntityEngine`, `MemoryEngine`, `RelationshipEngine`.

### 10.3 Engine Interface Pattern

Each Engine implements a stable facade interface:

```python
class EntityEngine:
    """Domain engine for entity identity and merge analysis."""

    def resolve_identity(self, ...) → DomainResult
    def analyze_merge_conflicts(self, ...) → DomainResult
    def validate_entity_invariants(self, ...) → DomainResult
```

Interface design details will be determined during D4 implementation.

---

## 11. Risks & Mitigations

### 11.1 Engine Over-Scope

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Engine grows to include business logic that belongs to Service | Each Engine traces back to D3 Service dependencies. Domain algorithms stay in Engine. Service coordinates, Engine computes. |
| Impact | Medium | **Severity: Medium** |
| Trigger | Engine method body exceeds 100 lines without Repository calls | Refactor: move orchestration back to Service, keep Engine algorithmic only. |

### 11.2 Cross-Engine Coupling

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Engine A calls Engine B, creating implicit coupling | Enforce Engine Collaboration Rule (G-D4-01). Service is the only orchestrator. |
| Impact | High | **Severity: Low** |
| Trigger | Architecture review detects Engine→Engine call | Block change. Redirect to Service orchestration pattern. |

### 11.3 Transaction Leakage

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Engine becomes aware of transaction boundaries | Enforce Transaction Ownership Rule. Engine is transaction-agnostic. |
| Impact | Medium | **Severity: Low** |
| Trigger | Engine method accepts transaction parameter | Remove from Engine interface. Transaction belongs to Service. |

### 11.4 Public Contract Instability

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Engine public contract changes frequently, breaking Service | Engine facade is stable. Internal composition evolves freely. |
| Impact | High | **Severity: Medium** |
| Trigger | Service needs new Engine capability | Evaluate: is this a domain rule change (Engine) or workflow change (Service)? |

---

## 12. D4 Substages

### D4.1 Engine Base Infrastructure

**Purpose**: Implement shared Engine infrastructure.

**Deliverables**:

- `EngineBase[T]` — Base class for all Engines
- Engine composition pattern (facade + private components)
- Engine DI wiring
- Engine error classification (per D3.7 Taxonomy)

**Dependencies**: D3.1 (Service Base), D3.7 (Error Taxonomy)

### D4.2 Individual Engine Implementation

**Purpose**: Implement domain engines based on D3 Service dependencies.

**Deliverables**:

- Entity Engine
- Memory Engine
- Relationship Engine
- Reflection Engine
- Search Engine
- Projection Engine
- (Additional Engines as determined by D3 Service analysis)

**Dependencies**: D4.1 (Engine Base), D3 Services (interface contracts)

### D4.3 Engine Testing

**Purpose**: Implement Engine test suite.

**Deliverables**:

- Domain rule tests for each Engine
- Invariant tests
- Algorithm tests
- Error classification tests
- Boundary tests (Engine-Repository, Engine-Service)

**Dependencies**: D4.2 (Engine implementations), D3.8 (Test architecture)

### D4.4 Engine Documentation

**Purpose**: Create per-Engine architecture documents.

**Deliverables**:

- D4.x_Entity_Engine.md
- D4.x_Memory_Engine.md
- D4.x_Relationship_Engine.md
- D4.x_Reflection_Engine.md
- D4.x_Search_Engine.md
- D4.x_Projection_Engine.md

**Dependencies**: D4.2 (Engine implementations)

---

## 13. Definition of Done

D4 is complete when **all** of the following criteria are met:

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 1 | All planned Engines implemented | Each Engine has public contract, internal composition, domain tests |
| 2 | No cross-Engine calls | Code review verifies Engine→Engine dependency is zero |
| 3 | Engine is transaction-agnostic | No Engine method accepts/returns transaction objects |
| 4 | Engine is stateless | No mutable instance state in Engine |
| 5 | Engine returns Domain Result | No protocol-specific return types in Engine |
| 6 | Engine tests pass (invariant-driven) | All domain rule tests, invariant tests, algorithm tests pass |
| 7 | Service-Engine boundary verified | Service tests verify Engine is called correctly, Engine tests verify Repository is called correctly |
| 8 | Error classification matches D3.7 Taxonomy | Engine errors classified per frozen taxonomy |
| 9 | No Service Layer changes | D3 services unchanged (frozen) |
| 10 | No Repository Layer changes | D2 repositories unchanged (frozen) |
| 11 | Documentation synchronized | README, INDEX, D4 Plan consistent |
| 12 | Cross-references verified | All G-NNN, ADR-NNN, §X.Y resolve correctly |

---

## 14. Task Dependencies

```
D4.1 Engine Base Infrastructure
       ↓
D4.2 Individual Engine Implementation ←─────────────────┐
       ↓                                               │
D4.3 Engine Testing ←──────────────────────────────────┤
       ↓                                               │
D4.4 Engine Documentation                              ↓
       ↓                                    D3.7 Error Taxonomy
D4 Freeze
```

**Parallel execution opportunities**:

- D4.2 (individual Engines) can proceed in parallel once D4.1 is complete
- D4.3 (Engine tests) can proceed in parallel with D4.2
- D4.4 (Engine docs) can proceed in parallel with D4.2

---

## 15. Implementation Order

The recommended implementation order follows dependency resolution:

| Order | Task | Description | Estimated Effort |
|-------|------|-------------|-----------------|
| 1 | D4.1 | Engine Base Infrastructure | ~3 hours |
| 2 | D4.2a | Entity Engine (highest complexity) | ~6 hours |
| 3 | D4.2b | Memory Engine | ~4 hours |
| 4 | D4.2c | Relationship Engine | ~3 hours |
| 5 | D4.2d | Reflection Engine | ~5 hours |
| 6 | D4.2e | Search Engine | ~4 hours |
| 7 | D4.2f | Projection Engine | ~3 hours |
| 8 | D4.3 | Engine Test Suite | ~6 hours |
| 9 | D4.4 | Engine Documentation | ~2 hours |

**Total estimated effort**: ~36 hours

---

## 16. D4 Phase Exit Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | All Engines implemented | ⏳ |
| 2 | No cross-Engine calls | ⏳ |
| 3 | Engine is transaction-agnostic | ⏳ |
| 4 | Engine is stateless | ⏳ |
| 5 | Engine returns Domain Result | ⏳ |
| 6 | Engine tests pass | ⏳ |
| 7 | Service-Engine boundary verified | ⏳ |
| 8 | Error classification matches D3.7 | ⏳ |
| 9 | No frozen layer changes | ⏳ |
| 10 | Documentation synchronized | ⏳ |
| 11 | Cross-references verified | ⏳ |

---

## 17. D4 Freeze Declaration

Upon D4 completion:

- **Domain Engine Layer**: ✅ Complete
- **Architecture**: 🧊 Frozen
- **Any future Engine Layer changes require ADR**
- **Baseline established for D5 (Entry & API Layer)**

---

## 18. Guidelines for D4

### G-D4-01: Engine Collaboration Rule

> Engine must NOT call other Engines. Service is the sole business orchestration layer.

**引用**: D4 §6

### G-D4-02: Transaction Agnosticism

> Engine is transaction-agnostic. Transaction belongs to Service.

**引用**: D4 §7

### G-D4-03: Stateless Engine

> Engine has no mutable state. All state comes from Repository reads.

**引用**: D4 §3.1

### G-D4-04: Facade Stability

> Engine public contract is stable. Internal composition is private and may evolve without ADR.

**引用**: D4 §5

### G-D4-05: Domain Result Only

> Engine returns domain-level results. No protocol-specific types in Engine.

**引用**: D4 §4.2

---

## 19. Related Documents

| Document | Section | Relevance |
|----------|---------|-----------|
| D3_Service_Layer_Plan.md | §11 Handoff to D4 | D3→D4 handoff assumptions |
| D3.7_Error_Handling_DTO_Models.md | §1–§13 | Error Taxonomy, DTO model |
| D3.8_Service_Test_Suite.md | §3.3 Engine Test | Test layer responsibilities |
| 10_2_Implementation_MemoryService.md | §3.2 Engine dependency | MemoryService→Engine calls |
| 10_3_Implementation_QueryService.md | §3.2 Engine dependency | QueryService→Engine calls |
| 10_4_Implementation_ReflectionService.md | §3.2 Engine dependency | ReflectionService→Engine calls |
| 10_5_Implementation_EntityService.md | §3.2 Engine dependency | EntityService→Engine calls |
| 13_Architecture_Guidelines.md | G-001~G-118 | All applicable guidelines |
| 12_Architecture_Decisions.md | ADR-010 | Shared Domain Engine |

---

## 20. Closing Confirmation

> **Status**: D4 Planned
> **Date**: 2026-07-13
> **Next**: D4.1 Engine Base Infrastructure

---

## 20.1 D4 Prerequisites

D4 may begin only when:

1. **D3 is Frozen** — Service Layer architecture is complete and frozen
2. **D2 is Frozen** — Repository Layer is complete and frozen
3. **D3 Post-Freeze Audit** — Has passed (see D3.9)
4. **Service contracts are stable** — D3 Services define stable interfaces for Engine integration
5. **Repository contracts are stable** — D2 Repositories define stable interfaces for Engine access

---

## 20.2 D4 Assumptions

D4 assumes:

- Services are stable and will not change without ADR
- 5 Services are callable via DI container
- Service exception hierarchy available for Engine error handling
- DTO boundaries enforced (Entry DTO ↔ Domain Model ↔ Repository ORM Model)
- Transaction boundaries managed at Service level
- Repository interfaces are frozen and stable

---

## 20.3 Handoff to D5

D4 completion enables D5 (Entry & API Layer):

- Engine public contracts are stable
- Service-Engine-Repository layering is verified
- Domain error classification is frozen
- Test infrastructure is in place

---

## 20.4 Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-13 | Initial D4 Domain Engine Plan |
