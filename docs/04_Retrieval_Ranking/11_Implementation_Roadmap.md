# Personal AI Memory Hub — Implementation Roadmap

> **Version**: 1.0
> **Date**: 2026-07-01
> **Phase**: Phase B — Engineering Planning
> **Status**: Draft
> **Author**: System Architecture Group

---

## 1. Purpose

This document defines the **complete engineering implementation lifecycle** for the Personal AI Memory Hub.

It is not a calendar-based project plan. It is an **engineering execution contract** that serves both human developers and AI assistants.

This document covers:

- Engineering Milestones (six implementation phases)
- MVP Definition (end-to-end lifecycle, not feature count)
- Coding Order (dependency-driven sequence)
- Repository Strategy (structure, modules, layout)
- Branch Strategy (lightweight workflow)
- Code Review Workflow (four review levels)
- CI Strategy (prioritized over CD)
- Development Milestones (completion criteria)
- Risk Management (AI engineering risks)
- Design → Implementation Transition (gate system)
- State-Driven Workflow (dynamic progression)
- AI-Driven Engineering Principles

**引用**：10_1 §2.1, 10_8 §2.1, 13_Architecture_Guidelines

---

## 2. Engineering Principles

> **Documents are the operational contract between architecture and implementation.**
> **AI follows documented workflows rather than conversation history.**

| Principle | Description |
|-----------|-------------|
| **Human Decides, AI Executes** | Humans define goals, review outcomes, approve merges. AI generates code, runs tests, produces reports. |
| **Documents as Operational Contract** | Design documents (01~10_N) define the immutable specification. Code must conform to documents, not vice versa. |
| **State-Driven Workflow** | Workflow progression is determined dynamically from project state, not a predefined daily checklist. |
| **Implementation is State-Driven** | Each implementation step begins with state assessment, not assumption of readiness. |
| **Roadmap Serves Both Humans and AI** | This document is the single reference for execution order, review criteria, and risk awareness. |

---

## 3. Engineering Milestones

> **These are engineering milestones, not calendar phases.** Duration depends on implementation complexity, not time estimates.

### Milestone 1: Foundation

**Goal**: Establish the project infrastructure and architectural foundation.

| Component | Deliverable | Verification |
|-----------|-------------|-------------|
| Repository structure | `backend/`, `docs/`, `tests/`, `scripts/`, `.github/` | Directory layout matches spec |
| Build system | Python project with dependencies, linting, type checking | `python -m build` succeeds |
| Configuration | Environment config, logging, error handling | Config loads correctly |
| Shared models | DTOs, Value Objects, Enums | Type annotations compile |
| Database setup | PostgreSQL/Supabase connection, migrations | Schema applies cleanly |
| Repository layer | Base repository interface, connection pool | CRUD operations functional |
| Domain Engine skeleton | Engine base class, dependency injection | Engines instantiate correctly |

**Completion Criteria**:

- [ ] Repository structure established
- [ ] Build, lint, type-check pipeline functional
- [ ] Database connection operational
- [ ] Base repository and engine interfaces implemented

### Milestone 2: Core Memory

**Goal**: Implement the Memory lifecycle — capture, store, correct, and retrieve.

| Component | Deliverable | Verification |
|-----------|-------------|-------------|
| Repository layer | Evidence, Memory, Archive repositories | CRUD + complex queries pass |
| Domain Engine | MemoryEngine (Archive/Evidence/Relationship/Candidate) | Stateless, deterministic output |
| Service layer | MemoryService (Capture/Correct/Restore/Archive) | Use case orchestration correct |
| Entry layer | Basic REST endpoint for memory capture | Request → Response pipeline works |
| Validation | Three-layer validation (Protocol → Capability → Domain) | Invalid input rejected at correct layer |

**Completion Criteria**:

- [ ] Memory can be captured end-to-end
- [ ] Memory can be corrected (correctMemory)
- [ ] Memory can be restored from archive
- [ ] Memory can be archived (L0 protection preserved)

### Milestone 3: Query & Reflection

**Goal**: Implement query capabilities and memory evolution through reflection.

| Component | Deliverable | Verification |
|-----------|-------------|-------------|
| Domain Engine | QueryEngine, ReflectionEngine | Deterministic query results, reflection pipeline |
| Service layer | QueryService (Retrieval/Search/Browse/Projection/Analytics) | Side-effect free, consumer-agnostic |
| Service layer | ReflectionService (Reflect/Consolidate/Summarize/Evaluate) | Memory Pyramid evolution correct |
| Entry layer | Query endpoints with continuation, streaming | Pagination, streaming work correctly |
| Validation | Query determinism, reflection completeness | Same query → same results |

**Completion Criteria**:

- [ ] All five Query Capabilities functional
- [ ] Reflection pipeline evolves Memory Pyramid correctly
- [ ] L0 memory protected during reflection
- [ ] Query determinism verified (G-016)

### Milestone 4: Entry & API

**Goal**: Implement full API Entry Layer with multi-adapter support.

| Component | Deliverable | Verification |
|-----------|-------------|-------------|
| Entry layer | REST adapter, MCP adapter, CLI adapter | All adapters share same pipeline |
| RequestContext | Unified request context (RequestId, TraceId, Principal, Capability, ClientType, API Version) | Services depend on RequestContext |
| Capability Registry | Dynamic capability catalog | GET /capabilities returns correct catalog |
| Authorization | Role→Capability mapping, authentication independence | AuthZ independent of AuthN provider |
| Error handling | Error registry, stable error identities | Error codes globally stable |

**Completion Criteria**:

- [ ] REST, MCP, CLI adapters all functional
- [ ] Capability discovery works
- [ ] Entry Independence Principle enforced
- [ ] Unified Request Lifecycle operational

### Milestone 5: Testing & Stabilization

**Goal**: Achieve test coverage and architectural compliance.

| Component | Deliverable | Verification |
|-----------|-------------|-------------|
| Unit tests | Engine, Repository, Service layer tests | Deterministic, fast, CI-blocking |
| Integration tests | Cross-layer flows, domain events | No external dependencies |
| Golden datasets | Known input-output pairs | Regression protection |
| Architecture tests | Layer boundary enforcement, DAG compliance | No violations |
| Evaluation tests | LLM quality assessment | Non-blocking, semantic equivalence |

**Completion Criteria**:

- [ ] All deterministic tests pass (CI gate)
- [ ] Golden datasets stable
- [ ] No architecture violations detected
- [ ] Regression suite covers all known bugs

### Milestone 6: MVP Release

**Goal**: Achieve MVP completion — full Memory lifecycle through supported Entry interfaces.

**MVP Definition**:

MVP is complete when Memory can flow through the entire lifecycle:

```
Entry (REST/MCP/CLI)
  ↓
Service (MemoryService)
  ↓
Engine (MemoryEngine → Archive/Evidence/Relationship/Candidate)
  ↓
Repository (EvidenceRepo, MemoryRepo, ArchiveRepo)
  ↓
Database (PostgreSQL/Supabase)
  ↓
Query (QueryService → Retrieval/Search/Browse/Projection/Analytics)
  ↓
Reflection (ReflectionService → Reflect/Consolidate/Summarize/Evaluate)
  ↓
Return Deterministic Results
```

Through at least one supported Entry interface (REST, MCP, or CLI).

**Deferred Capabilities** (future roadmap items):

| Deferred | Reason |
|----------|--------|
| Progressive Recall | Not required for MVP memory lifecycle |
| Entity Suppression / Escape | Entity layer beyond MVP scope |
| Human-like Memory Behavior | Evaluation metric, not architectural requirement |

**Completion Criteria**:

- [ ] Full lifecycle operational through at least one Entry interface
- [ ] Deterministic query results returned
- [ ] Reflection produces evolved Memory Pyramid
- [ ] All regression tests pass
- [ ] Architecture compliance verified

---

## 4. Coding Order

> **Code generation follows dependency order.** Implementation sequence is driven by architectural dependencies, not document numbering.

```
Foundation (01-09)
  ↓
Repository (09 → Repository Layer)
  ↓
Domain Engine (02, 04, 05 → Engine Layer)
  ↓
Service (10_1~10_6 → Service Layer)
  ↓
Entry (10_7 → API Entry Layer)
  ↓
Testing (10_8 → Testing Architecture)
```

**Rationale**:

| Step | Why First? | Depends On |
|------|-----------|------------|
| Foundation | Establishes project infrastructure | None |
| Repository | Lowest architectural layer, no business logic | Foundation |
| Domain Engine | Stateless, depends on Repository | Repository |
| Service | Orchestrates Engines, depends on Engine | Domain Engine |
| Entry | Adapts protocols, depends on Service | Service |
| Testing | Validates all layers | Everything above |

**Principle**: Each step must be architecturally complete before the next step begins. No parallel implementation across layers.

---

## 5. Repository Strategy

### 5.1 Structure

```
personal-memory-hub/
├── docs/                 # Architecture and design documents
│   ├── 01_Architecture/
│   ├── 03_Data_Model/
│   ├── 04_Memory_System/
│   ├── 07_Review/
│   └── 04_Retrieval_Ranking/
├── backend/              # Core application code
│   ├── src/
│   │   ├── entry/        # Entry Adapters (REST/MCP/CLI)
│   │   ├── service/      # Application Services
│   │   ├── engine/       # Domain Engines
│   │   ├── repository/   # Repository Layer
│   │   ├── shared/       # Common Module (models, DTOs, utilities)
│   │   ├── config/       # Configuration
│   │   └── event/        # Domain Events
│   ├── tests/            # Application tests
│   │   ├── fixtures/     # Shared fixtures
│   │   ├── scenarios/    # Scenario data
│   │   ├── golden/       # Golden datasets
│   │   ├── unit/         # Unit tests
│   │   ├── integration/  # Integration tests
│   │   └── evaluation/   # Evaluation tests
│   ├── scripts/          # Build, deploy, migration scripts
│   └── tools/            # Development tools
├── dashboard/            # Future: Web dashboard (outside MVP)
├── .github/              # CI/CD configuration
└── README.md
```

### 5.2 Module Strategy

> **One Repository, Multiple Modules.**

| Module | Purpose | MVP Scope |
|--------|---------|-----------|
| `backend/` | Core application | ✅ In scope |
| `docs/` | Architecture documents | ✅ In scope |
| `tests/` | Application tests | ✅ In scope |
| `scripts/` | Build, deploy, migration | ✅ In scope |
| `tools/` | Development utilities | ✅ In scope |
| `dashboard/` | Web dashboard | ❌ Outside MVP |

**Dashboard intentionally excluded from MVP.** The MVP focuses on API-level functionality. Dashboard is a Phase C+ enhancement.

---

## 6. Branch Strategy

> **Lightweight workflow.** No Git Flow unless future multi-developer collaboration requires it.

| Branch Pattern | Purpose | Usage |
|---------------|---------|-------|
| `main` | Production-ready code | Protected, CI-required |
| `feature/*` | New capability development | e.g., `feature/memory-capture` |
| `fix/*` | Bug fixes | e.g., `fix/entity-merge` |
| `docs/*` | Documentation updates | e.g., `docs/testing-architecture` |

**Rules**:

- All branches derive from `main`
- All merges require passing CI
- Feature branches are short-lived (< 1 week target)
- No long-running feature branches

---

## 7. Code Review Workflow

> **Four review levels. Passing tests does not automatically approve merge.**

### Level 1: Self Review

| Check | Description |
|-------|-------------|
| Code style | Follows project conventions |
| Unit tests | Written and passing |
| Documentation | Inline comments adequate |
| Architecture alignment | Matches design documents |

### Level 2: Architecture Review

| Check | Description |
|-------|-------------|
| Layer boundaries | No cross-layer violations |
| Dependency rules | DAG compliance verified |
| Capability alignment | Implements declared capability correctly |
| Mock strategy | Mocks only at layer boundaries |
| G-NNN compliance | All applicable guidelines followed |

### Level 3: Testing Review

| Check | Description |
|-------|-------------|
| Test quality | Assertions clear, isolated, deterministic |
| Coverage | All public methods tested |
| Golden datasets | Updated if behavior changed |
| Regression suite | New bugs have regression tests |

### Level 4: Human Approval

| Check | Description |
|-------|-------------|
| Design rationale | Human understands why this approach |
| Risk assessment | Risks identified and mitigated |
| Future extensibility | Does not block future capabilities |
| **Final decision** | Human approves or rejects merge |

**Principle**: Architecture invariants must be preserved. Tests are necessary but not sufficient for approval.

---

## 8. CI Strategy

> **CI over CD. CD is intentionally deferred until production readiness.**

### CI Pipeline

```
CI Pipeline
  ├── Stage 1: Static Analysis
  │     ├── Lint (flake8, ruff, mypy)
  │     └── Type Check (mypy strict mode)
  │
  ├── Stage 2: Unit Tests
  │     ├── Engine Tests (deterministic, fast)
  │     ├── Repository Tests (in-memory DB)
  │     └── Service Tests (real collaborators)
  │
  ├── Stage 3: Integration Tests
  │     ├── Cross-layer flows
  │     ├── Domain event flows
  │     └── Task Runtime flows
  │
  ├── Stage 4: Architecture Tests
  │     ├── Layer boundary enforcement
  │     ├── DAG compliance
  │     └── Guideline G-NNN checks
  │
  ├── Stage 5: Behavioral Tests
  │     ├── Golden dataset comparison
  │     └── Regression suite
  │
  └── Stage 6: Build Verification
        ├── python -m build
        └── pip install . succeeds
```

### CD Pipeline (Deferred)

| Stage | Status | Notes |
|-------|--------|-------|
| Staging deployment | ❌ Deferred | Until production readiness |
| Production deployment | ❌ Deferred | Until MVP stabilized |
| Rollback strategy | ❌ Deferred | Until CD implemented |

---

## 9. Development Milestones

Each milestone completion requires **five dimensions** of verification:

### 9.1 Functional Completion

| Check | Description |
|-------|-------------|
| Feature works | All declared capabilities functional |
| Edge cases handled | Invalid input, missing data, concurrent access |
| Error handling | Graceful degradation, informative errors |

### 9.2 Architecture Compliance

| Check | Description |
|-------|-------------|
| Layer boundaries | No violations detected |
| Dependency rules | DAG maintained |
| Guideline compliance | G-NNN rules followed |

### 9.3 Automated Verification

| Check | Description |
|-------|-------------|
| Tests pass | All deterministic tests green |
| Golden datasets | Output matches expected |
| Regression suite | No regressions |

### 9.4 Documentation Consistency

| Check | Description |
|-------|-------------|
| Design docs updated | If design changed, docs updated |
| Decision recorded | New decisions in Decision Summary |
| Cross-references valid | All references resolve |

### 9.5 Human Approval

| Check | Description |
|-------|-------------|
| Architectural review | Approved by reviewer |
| Testing review | Test quality verified |
| Risk assessment | No unmitigated risks |
| **Final sign-off** | Human approves milestone completion |

---

## 10. Risk Management

> **AI engineering introduces unique risks.** Traditional project risks (budget, timeline) are secondary to architectural integrity and implementation quality.

### 10.1 Architecture Drift

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Code diverges from design documents over time | Architecture tests in CI, periodic review |
| Symptom | New code implements undocumented behavior | G-NNN compliance checks, layer boundary enforcement |
| Impact | System becomes unmaintainable, unpredictable | **Severity: Critical** |

### 10.2 Document Drift

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Design documents become outdated as implementation progresses | Update documents before merging code changes |
| Symptom | Documents describe features that no longer exist | Cross-reference validation, version control |
| Impact | AI agents follow stale instructions, generating incorrect code | **Severity: High** |

### 10.3 AI Hallucination

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | AI generates code based on imagined requirements, not documented specifications | Always read design documents before generating code |
| Symptom | Code implements features not in any document | Self-review against design docs, architecture review |
| Impact | Feature creep, wasted effort, architectural inconsistency | **Severity: High** |

### 10.4 Workflow Deviation

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Implementation skips required steps (e.g., testing, review) | State-driven workflow enforces progression gates |
| Symptom | Code merged without architecture review, tests skipped | Four-level review workflow, CI gates |
| Impact | Technical debt accumulates, quality degrades | **Severity: Medium** |

### 10.5 Over-Automation

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | AI generates too much code too fast, bypassing human judgment | Human Approval level mandatory for all merges |
| Symptom | Large PRs with no human review, minimal test coverage | PR size limits, mandatory human sign-off |
| Impact | Undetected bugs, architectural inconsistencies | **Severity: Medium** |

### 10.6 Risk Summary

| Risk | Severity | Detection | Prevention |
|------|----------|-----------|------------|
| Architecture Drift | Critical | Architecture tests | CI enforcement |
| Document Drift | High | Cross-reference validation | Update-before-merge policy |
| AI Hallucination | High | Architecture review | Read-docs-first mandate |
| Workflow Deviation | Medium | State assessment | Gate system |
| Over-Automation | Medium | Human review | Mandatory approval |

---

## 11. Design → Implementation Transition

> **Four gates must pass before entering Implementation Mode.**

### Gate 1: Architecture Ready

| Check | Description |
|-------|-------------|
| Design documents complete | All referenced Phase A and Phase B documents finalized |
| Guidelines defined | G-NNN rules documented and understood |
| Cross-references valid | All document references resolve |
| No unresolved conflicts | Architecture decisions documented and approved |

### Gate 2: Engineering Ready

| Check | Description |
|-------|-------------|
| Repository structure established | Directory layout matches specification |
| Build pipeline functional | Lint, type-check, test commands work |
| Dependencies resolved | All packages installed and compatible |
| Environment configured | Database, logging, error handling operational |

### Gate 3: AI Ready

| Check | Description |
|-------|-------------|
| Design documents accessible | AI can read and reference all Phase A/B docs |
| Workflow documented | State-driven process documented in this roadmap |
| Review criteria clear | Four review levels defined and understood |
| Risk awareness established | AI understands AI-specific risks and mitigations |

### Gate 4: Human Ready

| Check | Description |
|-------|-------------|
| Human understands architecture | Human can explain the five-layer model |
| Human approves starting | Human explicitly initiates Implementation Mode |
| Review process understood | Human knows when and how to intervene |
| Exit criteria defined | Human knows when to pause, redirect, or stop |

**Transition Rule**: Only when ALL four gates pass does the project enter Implementation Mode. If any gate fails, the blocker must be resolved before proceeding.

---

## 12. State-Driven Workflow

> **Workflow progression is determined dynamically from project state, not a predefined daily checklist.**

### Typical Flow

```
Read GitHub (current state)
  ↓
Assess project state (what's done, what's pending)
  ↓
Generate Status Report (objective assessment)
  ↓
Human decision (approve, redirect, pause)
  ↓
Execution (implement, test, verify)
  ↓
Execution Report (what was done, what changed)
  ↓
Human decision (accept, request changes)
  ↓
Verification (automated + manual)
  ↓
Verification Report (pass/fail, evidence)
  ↓
Human Approval (final sign-off)
  ↓
Commit / Merge (atomic, documented)
```

### State Assessment Criteria

At each workflow step, assess:

| Dimension | Questions |
|-----------|-----------|
| **Architectural state** | Which layers are implemented? Which are not? |
| **Test state** | What is the current test coverage? Any failing tests? |
| **Document state** | Are design docs aligned with code? Any drift? |
| **Risk state** | Any emerging risks? Any architecture violations? |
| **Milestone state** | Which milestone is current? What are completion criteria? |

### Dynamic Progression

The workflow does not follow a fixed schedule. Progression is determined by:

1. **State assessment** reveals current readiness
2. **Status report** communicates findings
3. **Human decision** determines next action
4. **Execution** proceeds based on decision
5. **Verification** confirms outcome
6. **Repeat** — next assessment starts a new cycle

This ensures the project adapts to changing conditions rather than rigidly following a predetermined plan.

---

## 13. AI-Driven Engineering Concepts

### 13.1 Documents as Operational Contract

Design documents are not suggestions. They are the **binding specification** between architecture and implementation.

| Rule | Description |
|------|-------------|
| Code conforms to documents | Implementation must match design, not the reverse |
| Documents updated before code | Design changes precede implementation changes |
| AI reads documents first | AI never generates code without reading relevant design docs |
| Conversation history is ephemeral | Decisions in chat do not override documents |

### 13.2 Human Decides, AI Executes

| Role | Responsibility |
|------|---------------|
| **Human** | Define goals, review outcomes, approve merges, assess risks, make architectural decisions |
| **AI** | Generate code, run tests, produce reports, update documents, verify compliance |

### 13.3 Implementation is State-Driven

The project does not follow a checklist. It follows a **state machine**:

```
State: Design Complete
  → Gate Assessment
  → Gates Pass? → YES → State: Implementation Ready
  → Gates Pass? → NO  → State: Blocked (resolve blockers)

State: Implementation Ready
  → State Assessment
  → Execute Next Milestone
  → State: In Progress

State: In Progress
  → Execution Report
  → Human Decision
  → State: Verification Needed OR State: Redirected

State: Verification Needed
  → Automated Verification
  → Manual Verification
  → State: Verified OR State: Failed

State: Verified
  → Human Approval
  → State: Committed OR State: Rejected

State: Committed
  → Commit + Push
  → State: Design Complete (next milestone)
```

---

## 14. Checklist

### 14.1 P0 — Must Have

| # | Check Item | Status |
|---|------------|--------|
| P0-1 | **Six engineering milestones defined** | ✅ Foundation → Core Memory → Query & Reflection → Entry & API → Testing & Stabilization → MVP Release |
| P0-2 | **MVP defined by lifecycle, not features** | ✅ End-to-end Memory flow through all layers |
| P0-3 | **Coding order follows dependencies** | ✅ Foundation → Repository → Engine → Service → Entry → Testing |
| P0-4 | **Repository strategy documented** | ✅ One Repo, Multiple Modules |
| P0-5 | **Branch strategy lightweight** | ✅ main / feature/* / fix/* / docs/* |
| P0-6 | **Four-level review workflow** | ✅ Self → Architecture → Testing → Human |
| P0-7 | **CI prioritized over CD** | ✅ Six-stage CI, CD deferred |
| P0-8 | **AI engineering risks addressed** | ✅ Architecture drift, document drift, hallucination, workflow deviation, over-automation |
| P0-9 | **Gate system for implementation** | ✅ Architecture / Engineering / AI / Human ready |
| P0-10 | **State-driven workflow** | ✅ Dynamic progression, not checklist-driven |

### 14.2 P1 — Recommended

| # | Check Item | Status |
|---|------------|--------|
| P1-1 | **Golden dataset management** | ✅ Version-controlled, design-aligned |
| P1-2 | **Dashboard excluded from MVP** | ✅ Intentionally deferred |
| P1-3 | **Five milestone completion dimensions** | ✅ Functional, Architecture, Automated, Documentation, Human |

### 14.3 P2 — Future

| # | Check Item | Status |
|---|------------|--------|
| P2-1 | **CD pipeline** | ✅ Deferred until production readiness |
| P2-2 | **Multi-developer branching** | ✅ Git Flow if needed |
| P2-3 | **Progressive Recall** | ✅ Deferred capability |

---

## 15. Decision Summary

| # | Decision | Rationale | Reference |
|---|----------|-----------|-----------|
| 1 | **Six engineering milestones** | Foundation → Core Memory → Query & Reflection → Entry & API → Testing & Stabilization → MVP | 11 §3 |
| 2 | **MVP = end-to-end lifecycle** | Not feature count, but complete Memory flow through all layers | 11 §3.6 |
| 3 | **Deferred: Progressive Recall** | Not required for MVP memory lifecycle | 11 §3.6 |
| 4 | **Deferred: Entity Suppression** | Entity layer beyond MVP scope | 11 §3.6 |
| 5 | **Deferred: Human-like Memory** | Evaluation metric, not architectural requirement | 11 §3.6 |
| 6 | **Coding order = dependency order** | Repository → Engine → Service → Entry, not document numbering | 11 §4 |
| 7 | **One Repository, Multiple Modules** | backend/, docs/, tests/, scripts/, tools/ | 11 §5 |
| 8 | **Dashboard outside MVP** | API-level focus first | 11 §5.2 |
| 9 | **Lightweight branch strategy** | No Git Flow unless multi-developer | 11 §6 |
| 10 | **Four review levels** | Self → Architecture → Testing → Human | 11 §7 |
| 11 | **CI over CD** | CD deferred until production | 11 §8 |
| 12 | **Five milestone dimensions** | Functional, Architecture, Automated, Documentation, Human | 11 §9 |
| 13 | **AI engineering risks** | Architecture drift, document drift, hallucination, workflow deviation, over-automation | 11 §10 |
| 14 | **Four implementation gates** | Architecture / Engineering / AI / Human ready | 11 §11 |
| 15 | **State-driven workflow** | Dynamic progression, not daily checklist | 11 §12 |
| 16 | **Documents as operational contract** | Code conforms to documents, not reverse | 11 §13.1 |
| 17 | **Human decides, AI executes** | Clear role separation | 11 §13.2 |
| 18 | **Tests necessary but not sufficient** | Architecture invariants also required | 11 §7 |
| 19 | **Regression suite is living documentation** | Every bug fix adds regression test | 10_8 §7 |
| 20 | **Testability is architectural requirement** | Un-testable code means flawed design | 10_8 §8.1 |

---

## 16. Backport Updates

The following documents require backport updates after 11 is finalized:

| Document | Update Required |
|----------|----------------|
| **10_1_Implementation_Service_Layer** | Add testing section to Decision Summary (items 44+) |
| **12_Engineering_Register** | Cross-reference to 11 engineering principles (coding order, CI strategy, risk management) |
| **13_AI_Development_Workflow** | Cross-reference to 11 state-driven workflow, gate system, and AI engineering principles |
| **INDEX.md** | Mark 11 as completed, update progress, replace 12_Architecture_Decisions with 12_Engineering_Decisions |
| **README.md** | Update Phase B status, add 10_8, 11, update planned documents |

---

## 17. Relationship with Other Documents

| Document | Relationship |
|----------|-------------|
| **01** | Foundation principles → Milestone 1 (Foundation) |
| **08** | Implementation Architecture → Coding order reflects layer dependencies |
| **09** | Database Physical Design → Repository layer milestone |
| **10_1** | Service Layer → Milestone 2-4 implementation order |
| **10_2** | MemoryService → Milestone 2 (Core Memory) |
| **10_3** | QueryService → Milestone 3 (Query & Reflection) |
| **10_4** | ReflectionService → Milestone 3 (Query & Reflection) |
| **10_5** | EntityService → Deferred (beyond MVP) |
| **10_6** | TaskRuntime → Milestone 3 (Reflection orchestration) |
| **10_7** | API Entry Layer → Milestone 4 (Entry & API) |
| **10_8** | Testing Architecture → Milestone 5 (Testing & Stabilization) |
| **13** | Architecture Guidelines → All milestones enforce G-NNN compliance |

---

## Appendix A: Terminology

| Term | Description | Source |
|------|-------------|--------|
| Engineering Milestone | Implementation phase defined by deliverables, not calendar dates | 11 §3 |
| MVP Lifecycle | Complete Memory flow: Entry → Service → Engine → Repository → Database → Query → Reflection → Return | 11 §3.6 |
| Coding Order | Dependency-driven implementation sequence | 11 §4 |
| State-Driven Workflow | Dynamic progression based on project state assessment | 11 §12 |
| Implementation Gate | Prerequisite check before entering Implementation Mode | 11 §11 |
| AI Engineering Risk | Risk unique to AI-assisted development (hallucination, drift) | 11 §10 |
| Operational Contract | Design documents as binding specification between architecture and implementation | 11 §13.1 |

---

## Appendix B: Document Change Record

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-07-01 | Initial version — Six engineering milestones, MVP lifecycle definition, coding order, repository strategy, branch strategy, four-level review, CI strategy, milestone completion criteria, AI engineering risks, gate system, state-driven workflow, AI-driven engineering concepts | ✅ Confirmed |

---

*This document is a Living Engineering Specification. It evolves with the project.*

*Subsequent Phase C documents (12_Engineering_Decisions, 13_AI_Development_Workflow, 14_Final_Implementation_Review) will refine and extend this roadmap.*
