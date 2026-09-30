# Phase 22.14 — Service Boundary & Responsibility Audit

**Date**: 2026-08-14  
**Mode**: READ ONLY — Architecture audit  
**Status**: Complete

---

## Executive Verdict

```
╔═══════════════════════════════════════════════════════════════════╗
║  PMH has 11 Services + 9 Engines. Most are well-scoped.          ║
║  Two issues require attention:                                   ║
║   1. ReflectionService is OVERLOADED (1273 lines, 18 methods)    ║
║   2. EvidencePipelineService._evolve() creates L2 directly       ║
║                                                                      ║
║  NO new services needed for Clean Rebuild.                         ║
║  Entity Resolution → component inside FormationService.             ║
║  Orchestrator → inline in app.py Cron loop.                        ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 1. Complete Service Inventory

### Application Services (service/)

| # | Service | Lines | Responsibility | Caller |
|---|---------|-------|----------------|--------|
| 1 | **BaseService** | — | Abstract base class | All services |
| 2 | **EntityService** | 526 | Entity CRUD, resolution, merging | API endpoints |
| 3 | **EvidencePipelineService** | 294 | Full L0→L2 pipeline orchestration | API `/pipeline/trigger` |
| 4 | **FormationService** | 378 | Interpretation → Reconstruction → Candidate | EvidencePipelineService |
| 5 | **MemoryService** | 1053 | Import, query, archive, vector search | API endpoints |
| 6 | **QueryService** | 586 | Memory queries (text, semantic, graph) | API endpoints |
| 7 | **ReflectionService** | **1273** | L1 evolution (candidate → proposal → L1) | Cron, API |
| 8 | **TopicService** | — | Topic CRUD, extraction, linking | EvidencePipelineService |
| 9 | **TaskService** | 396 | Task management | API endpoints |
| 10 | **EmbeddingService** | — | Vector embeddings | MemoryService |
| 11 | ~~Orchestrator~~ | — | **Not yet implemented** | Design proposal only |

### Evolution Services (evolution/)

| # | Service | Lines | Responsibility | Caller |
|---|---------|-------|----------------|--------|
| 12 | **EvolutionService** | 399 | L2/L3 creation, relationship detection | EvidencePipelineService._evolve() |
| 13 | **EvolutionEngine** | 514 | Topic evolution, status transitions | EvolutionService |

### Domain Engines (engine/)

| # | Engine | Lines | Responsibility | Caller |
|---|--------|-------|----------------|--------|
| 14 | **ReflectionEngine** | 586 | Fact extraction, proposal generation (LLM) | ReflectionService |
| 15 | **EvidenceEvolutionEngine** | 427 | Pattern discovery, evidence aggregation | ReflectionService |
| 16 | **EntityEngine** | 423 | Entity graph operations | EntityService |
| 17 | **MemoryEngine** | 461 | Memory node operations | MemoryService |
| 18 | **ProjectionEngine** | 465 | View projection | QueryService |
| 19 | **RelationshipEngine** | 367 | Relationship CRUD | EvolutionService |
| 20 | **SearchEngine** | 436 | Full-text search | MemoryService |

### Context Layer (context/)

| # | Component | Lines | Responsibility | Caller |
|---|-----------|-------|----------------|--------|
| 21 | **ContextWindowFormulator** | 304 | Context window assembly | EvidencePipelineService |
| 22 | **UserSemanticInterpreter** | 440 | Semantic interpretation | EvidencePipelineService |
| 23 | **ContextWindow** | 198 | Data structure (temporary) | Formulator |
| 24 | **InterpretationResult** | 226 | Data structure (output) | Interpreter |

**Total: 11 Services + 9 Engines + 4 Context components = 24 classes**

---

## 2. Complete Call Graph (Current Production)

```
[Cron: every 10 minutes]
    ↓
app.py: run_cron_task_now(task_id='evolution')
    ↓
ReflectionService.reflect(workspace_id, scope='daily', limit=200)
    ↓
_acquire_scope() → CandidateRepository.find_by_status('candidate')
    ↓
_run_engine_pipeline(scope, candidates, workspace_id)
    ├─ EvidenceEvolutionEngine.evolve() [LLM: fact extraction]
    └─ ReflectionEngine.reflect_pipeline() [LLM: proposal generation]
    ↓
_save_proposals(proposals, workspace_id) → proposals table INSERT
    ↓
_auto_approve_pending_proposals(workspace_id)
    └─ approve_proposal() × N
        ├─ UPDATE proposals SET status='approved'
        └─ INSERT memory_nodes (level=1)  ← entity_id=NULL (BUG)
```

**Formation path (API only, never called by Cron):**

```
POST /pipeline/trigger { evidence_id, workspace_id }
    ↓
EvidencePipelineService.process_evidence()
    ├─ _form_context_window() → ContextWindowFormulator
    ├─ _interpret() → UserSemanticInterpreter
    ├─ _form() → FormationService.form()
    │   ├─ _resolve_entity() → Evidence.entity_id (NULL for 71%)
    │   ├─ _create_reconstruction()
    │   └─ _create_candidate()
    ├─ _extract_topics() → TopicService
    └─ _evolve() → EvolutionService.evolve()  ← DIRECT L2 CREATION
```

---

## 3. ReflectionService Deep Dive

### Method Inventory (18 public/private methods)

| Method | Lines | Responsibility | Should Stay? |
|--------|-------|---------------|-------------|
| `reflect()` | 92-200 | Main entry, orchestrates entire flow | ✅ Keep |
| `reflect_by_entity()` | 195 | Entity-scoped reflection | ✅ Keep |
| `approve_proposal()` | 208-400 | L1 creation (DIRECT SQL) | ✅ Keep |
| `_auto_approve_by_threshold()` | 402 | Auto-approve logic | ✅ Keep |
| `reject_proposal()` | 460 | Proposal rejection | ✅ Keep |
| `reflect_by_time_window()` | 515 | Time-window reflection | ⚠️ Review |
| `reflect_by_scope()` | 540 | Scope-based reflection | ⚠️ Review |
| `consolidate()` | 556 | Memory consolidation | ❌ Out of scope |
| `consolidate_by_entity()` | 577 | Entity-scoped consolidation | ❌ Out of scope |
| `summarize()` | 593 | Memory summarization | ❌ Out of scope |
| `summarize_by_level()` | 632 | Level-based summarization | ❌ Out of scope |
| `evaluate()` | 648 | Memory evaluation | ❌ Out of scope |
| `evaluate_by_entity()` | 689 | Entity-scoped evaluation | ❌ Out of scope |
| `_run_engine_pipeline()` | 705-855 | Engine delegation | ✅ Keep |
| `_save_candidates()` | 858-985 | Candidate persistence | ✅ Keep |
| `_auto_approve_pending_proposals()` | 986-1045 | Auto-approval | ✅ Keep |
| `_save_proposals()` | 1046-1120 | Proposal persistence | ✅ Keep |
| `_acquire_scope()` | 1122-1265 | Candidate acquisition | ✅ Keep |

### Verdict: REFLECTIONSERVICE IS OVERLOADED

**1273 lines, 18 methods, 5 responsibilities:**

| Responsibility | Methods | Status |
|---------------|---------|--------|
| L1 Evolution (core) | reflect(), _run_engine_pipeline(), _save_proposals(), approve_proposal() | ✅ Core |
| Scope management | _acquire_scope(), reflect_by_entity(), reflect_by_time_window(), reflect_by_scope() | ⚠️ Growing |
| Consolidation | consolidate(), consolidate_by_entity() | ❌ Different feature |
| Summarization | summarize(), summarize_by_level() | ❌ Different feature |
| Evaluation | evaluate(), evaluate_by_entity() | ❌ Different feature |

**Recommendation**: The 5 non-core methods (consolidate, summarize, evaluate + their variants) should be removed or moved to a separate service. But this is NOT a blocker for Clean Rebuild.

---

## 4. EvolutionService vs ReflectionService Boundary

### Current Boundary (Correct)

| Aspect | ReflectionService | EvolutionService |
|--------|-------------------|------------------|
| **Input** | Candidates (pending) | Candidate (single, post-formation) |
| **Output** | L1 MemoryNodes | L2 Patterns, L3 Beliefs |
| **LLM** | Yes (fact extraction, proposals) | No (deterministic thresholds) |
| **Transaction** | Owns transaction | Caller-managed |
| **Batch** | Yes (up to 50 candidates) | No (single candidate) |
| **Cross-history** | No | Yes (queries historical L1) |
| **Cron caller** | Yes | Optional |

### Is Merging Necessary?

**Analysis**: NO. The two services have fundamentally different responsibilities:

| Dimension | ReflectionService | EvolutionService |
|-----------|------------------|-----------------|
| Algorithm | LLM-driven (nondeterministic) | Rule-driven (deterministic) |
| Time scope | Current batch | Historical aggregation |
| Output level | L1 (Observation) | L2+ (Pattern/Belief) |
| Confidence | Per-proposal | Per-entity aggregation |

**Verdict**: Keep separate. They solve different problems at different abstraction levels.

---

## 5. EvidencePipelineService: Service or Wrapper?

### Current Responsibilities

| Method | Lines | What it does |
|--------|-------|-------------|
| `process_evidence()` | 106-207 | Main entry, orchestrates full pipeline |
| `_form_context_window()` | 208-218 | Delegates to ContextWindowFormulator |
| `_interpret()` | 221-235 | Delegates to UserSemanticInterpreter |
| `_form()` | 238-248 | Delegates to FormationService |
| `_extract_topics()` | 251-275 | Delegates to TopicService |
| `_evolve()` | 280-290 | Delegates to EvolutionService |

### Verdict: VALID ORCHESTRATOR

EvidencePipelineService is a **thin orchestrator** — it doesn't implement any business logic, only delegates to sub-services. This is the correct pattern.

**However**: The name "PipelineService" is misleading. It's not a pipeline in the data-processing sense; it's an **application service** that coordinates multiple domain services.

**Alternative names**:
- `EvidenceFormationOrchestrator` (accurate but verbose)
- `EvidencePipelineAppService` (clear hierarchy)
- Keep `EvidencePipelineService` (acceptable, widely understood)

**Recommendation**: Keep the name. The "pipeline" metaphor is clear enough in context.

---

## 6. EntityResolution: Service or Component?

### Decision Criteria

| Criterion | Independent Service | Component |
|-----------|--------------------|-----------|
| Called from multiple services | ❌ No (only Formation) | ✅ Yes |
| Independent lifecycle | ❌ No | ✅ Yes |
| Independent transaction | ❌ No | ✅ Yes |
| Independent persistence | ❌ No | ✅ Yes |
| Complex orchestration | ⚠️ Some | ✅ Enough |
| Needs independent provider | ❌ No | ✅ No |
| Needs independent testing | ⚠️ Some | ✅ Unit tests suffice |
| Future pipeline reuse | ❌ Unlikely | ✅ Not needed |

### Verdict: FORMATIONSERVICE COMPONENT

Entity resolution should be a **private method** inside FormationService, NOT a separate service.

**Rationale**:
1. Only called from FormationService
2. No independent lifecycle
3. No independent transaction needed
4. Simple enough to be a method (4 steps: exact match, alias match, fuzzy match, LLM fallback)
5. Adding a new service increases complexity without proportional benefit

**Implementation**:
```python
# formation_service.py (enhanced)
class FormationService(BaseService):
    async def form(self, interpretation, trigger_evidence_id, workspace_id, entity_id=None):
        # Step 1: Try provided entity_id
        if entity_id is None:
            entity_id = await self._resolve_entity(trigger_evidence_id, workspace_id)
        
        # Step 2: If still None, try context-aware resolution
        if entity_id is None:
            entity_id = await self._resolve_entity_from_context(
                trigger_evidence_id, workspace_id
            )
        
        # Step 3: Create Reconstruction + Candidate
        ...
    
    async def _resolve_entity_from_context(
        self, evidence_id: UUID, workspace_id: UUID
    ) -> UUID | None:
        """Resolve entity using ContextWindow (requires DB access)."""
        # 1. Load evidence and related evidences
        # 2. Extract keywords/names
        # 3. Match against existing entities
        # 4. LLM fallback if no match
        pass
```

---

## 7. Orchestrator: Necessary or Redundant?

### Phase 22.10 Proposed Orchestrator

```python
async def _run_full_pipeline(workspace_id, limit=200):
    # Stage 1: Formation
    formation_result = await _run_formation_phase(workspace_id, limit)
    # Stage 2: L1 Evolution
    l1_result = await _run_l1_evolution_phase(workspace_id, limit)
    # Stage 3: L2/L3 Evolution
    l2_result = await _run_l2_evolution_phase(workspace_id)
    return PipelineOrchestrationResult(...)
```

### Verdict: NOT NEEDED AS SEPARATE SERVICE

The orchestration logic is simple (call A, then B, then C). It belongs in **app.py Cron loop**, not a separate service.

**Alternative**: Inline orchestration in Cron:
```python
# app.py (current Cron loop, enhanced)
async def _cron_scheduler_loop():
    while True:
        # Stage 1: Formation (skip if no pending evidences)
        pending_evidences = await _get_pending_evidences(workspace_id)
        if pending_evidences:
            for evidence in pending_evidences[:limit]:
                await evidence_pipeline_service.process_evidence(
                    evidence_id=evidence.id, workspace_id=workspace_id
                )
        
        # Stage 2: L1 Evolution (existing)
        await reflection_service.reflect(workspace_id=workspace_id, limit=50)
        
        # Stage 3: L2/L3 Evolution (new, optional)
        await _run_l2_evolution(workspace_id)
        
        await asyncio.sleep(600)
```

**This is simpler and more transparent than introducing a new Orchestrator service.**

---

## 8. Minimum Necessary Service Set

### Current State (11 Services)

```
EntityService          — Entity domain operations
EvidencePipelineService — Evidence → Candidate orchestration
FormationService       — Interpretation → Candidate formation
MemoryService          — Import, query, archive
QueryService           — Memory queries
ReflectionService      — Candidate → L1 evolution
TopicService           — Topic operations
TaskService            — Task management
EmbeddingService       — Vector embeddings
EvolutionService       — L2/L3 evolution
EvolutionEngine        — Topic status transitions (actually an Engine)
```

### Proposed Cleanup

**Remove (merge into existing):**
- ~~Orchestrator~~ → Inline in app.py
- ~~EntityResolutionService~~ → Method in FormationService

**Keep (all 11 are necessary):**
- All existing services have clear, non-overlapping responsibilities

**Rename for clarity:**
- `EvidencePipelineService` → Keep (pipeline metaphor is clear)
- `ReflectionService` → Keep (reflection = L1 evolution)
- `EvolutionService` → Keep (evolution = L2/L3 abstraction)

### Final Service Count: 11 (unchanged)

---

## 9. Naming Analysis

### Current Names vs. Actual Responsibilities

| Name | Actual Responsibility | Accuracy |
|------|----------------------|----------|
| EvidencePipelineService | Evidence → Candidate orchestration | ✅ Accurate |
| FormationService | Interpretation → Reconstruction → Candidate | ✅ Accurate |
| ReflectionService | Candidate → Proposal → L1 | ⚠️ Partial (also does consolidation/summarize/evaluate) |
| EvolutionService | L2/L3 creation from Candidate | ✅ Accurate |
| EntityService | Entity CRUD + resolution | ✅ Accurate |
| TopicService | Topic CRUD + extraction | ✅ Accurate |
| MemoryService | Import + query + archive + vectors | ⚠️ Too broad (5 responsibilities) |
| QueryService | Memory queries | ✅ Accurate |
| TaskService | Task management | ✅ Accurate |
| EmbeddingService | Vector embeddings | ✅ Accurate |

### Issues Found

1. **ReflectionService** does too much (consolidation, summarization, evaluation are different features)
2. **MemoryService** is a catch-all (import, query, archive, vectors)
3. **No naming conflict** between ReflectionService and EvolutionService (they operate at different levels)

### Recommended Renames

| Current | Recommended | Reason |
|---------|-------------|--------|
| ReflectionService | Keep | Well-understood term |
| MemoryService | Split into ImportService + QueryService | Too broad |
| EvolutionService | Keep | Clear distinction from Reflection |

**Note**: MemoryService split is a future refactor, not required for Clean Rebuild.

---

## 10. Core Questions Answered

### Q1: Should ReflectionService continue to exist?

**YES.** It is the L1 evolution engine. 1273 lines is large but mostly due to 5 extra features (consolidate, summarize, evaluate). Core functionality is well-scoped.

### Q2: Should EvolutionService continue to exist?

**YES.** It handles L2/L3 creation with deterministic threshold logic. Different from ReflectionService's LLM-driven approach.

### Q3: Should they merge?

**NO.** Different algorithms (LLM vs. rule-based), different time scopes (batch vs. historical), different output levels (L1 vs. L2/L3).

### Q4: Should EvidencePipelineService continue to exist?

**YES.** It's a thin orchestrator with clear responsibility. The name is acceptable.

### Q5: Is FormationService sufficient for Evidence → Candidate?

**YES.** FormationService already handles Interpretation → Reconstruction → Candidate. Entity resolution should be added as a method inside it.

### Q6: Does Entity Resolution need an independent Service?

**NO.** It's only called from FormationService. Implement as a private method `_resolve_entity_from_context()`.

### Q7: Does Orchestrator need to exist?

**NO.** Simple sequential calls belong in the Cron loop (app.py), not a separate service.

### Q8: What is the minimum Service set?

**11 services** (same as current). No additions needed. One removal (EntityResolutionService → method).

### Q9: What is each Service's unique responsibility?

| Service | Unique Responsibility |
|---------|----------------------|
| EvidencePipelineService | Coordinate Evidence → Candidate (orchestration) |
| FormationService | Interpretation → Reconstruction → Candidate (with entity resolution) |
| ReflectionService | Candidate → Proposal → L1 (LLM-driven evolution) |
| EvolutionService | L2/L3 creation from historical L1 (rule-based evolution) |
| EntityService | Entity CRUD and resolution (lookup by name/ID) |
| TopicService | Topic extraction and linking |
| MemoryService | Import, archive, vector operations |
| QueryService | Memory queries (text, semantic, graph) |
| TaskService | Task lifecycle management |
| EmbeddingService | Vector embedding generation |
| EvolutionEngine | Topic status transitions |

### Q10: What is the final recommended call chain?

```
[CRON]
    ↓ (inline in app.py)
[Stage 1] EvidencePipelineService.process_evidence()
    ├─ ContextWindowFormulator (assemble context)
    ├─ UserSemanticInterpreter (interpret semantics)
    └─ FormationService.form()
        ├─ _resolve_entity_from_context()  ← NEW: entity resolution
        ├─ _create_reconstruction()
        └─ _create_candidate()
    
[Stage 2] ReflectionService.reflect()
    ├─ _acquire_scope() (find pending candidates)
    ├─ EvidenceEvolutionEngine (fact extraction)
    ├─ ReflectionEngine (proposal generation)
    ├─ _save_proposals()
    └─ _auto_approve_pending_proposals()
        └─ approve_proposal()
            └─ INSERT memory_nodes (level=1, entity_id set)

[Stage 3] EvolutionService.evolve_entity_history()  ← NEW METHOD
    ├─ Query L1 by entity_id
    ├─ Check threshold (≥3 facts, conf≥0.8)
    └─ Create L2 Pattern / L3 Belief
```

---

## 11. Architecture Conflicts Summary

| ID | Issue | Resolution |
|----|-------|------------|
| FC-001 | EvidencePipelineService production entry | ✅ Keep, call from Cron inline |
| FC-002 | L1 entity_id lineage | ✅ Fix in FormationService._resolve_entity_from_context() |
| FC-003 | EvolutionService L2/L3 integration | ✅ Add evolve_entity_history() method |
| FC-004 | Cross-batch aggregation | ✅ L1 aggregation in EvolutionService |
| **NEW-001** | ReflectionService overloaded (1273 lines) | ⚠️ Future refactor (merge consolidate/summarize/evaluate) |
| **NEW-002** | EvidencePipelineService._evolve() creates L2 directly | 🔴 Must fix: remove direct L2 creation |

---

## 12. Files to Change for Clean Rebuild

| File | Change | Lines | Type |
|------|--------|-------|------|
| `service/formation_service.py` | Add `_resolve_entity_from_context()` | +50 | New method |
| `service/formation_service.py` | Modify `form()` to use new resolver | +10 | Modify |
| `service/formation_service.py` | Allow NULL entity_id with warning | +5 | Modify |
| `service/evidence_pipeline_service.py` | Remove direct L2 creation | -5 | Delete |
| `evolution/evolution_service.py` | Add `evolve_entity_history()` | +80 | New method |
| `app.py` | Inline orchestration in Cron loop | +30 | New function |
| `service/reflection_service.py` | Fix entity_id propagation | +3 | Bug fix |

**Total: 7 files, ~183 lines changed. No new services. No new tables.**

---

## 13. Final Recommendation

```
┌────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED ARCHITECTURE                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Cron Loop (app.py)                                            │
│    ├── Stage 1: EvidencePipelineService.process_evidence()     │
│    │     └── FormationService.form()                          │
│    │           └── _resolve_entity_from_context() [NEW]       │
│    ├── Stage 2: ReflectionService.reflect()                   │
│    │     └── approve_proposal() → L1 with entity_id ✅       │
│    └── Stage 3: EvolutionService.evolve_entity_history() [NEW]│
│          └── L2/L3 creation from historical L1                │
│                                                                │
│  NO new services.                                              │
│  NO new tables.                                                │
│  NO Orchestrator service.                                      │
│  Entity Resolution = FormationService method.                  │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Services count: 11 (unchanged)                                │
│  Engines count: 9 (unchanged)                                  │
│  Context components: 4 (unchanged)                             │
│                                                                │
│  Net new code: ~183 lines                                      │
│  Net new files: 0                                              │
│  Net new tables: 0                                             │
└────────────────────────────────────────────────────────────────┘
```

---

**Phase 22.14 complete. Service boundaries audited. No new services needed for Clean Rebuild.**
