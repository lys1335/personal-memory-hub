# Personal Memory Hub — Architecture Update: Evidence Evolution Split

> **Version**: 1.0
> **Date**: 2026-08-05
> **Type**: Architecture Refactoring
> **Status**: 📝 Draft
> **Author**: System Architecture Group

---

## 1. Executive Summary

This document records the architectural decision to split Evidence Evolution capabilities from ReflectionEngine into a new EvidenceEvolutionEngine.

**Decision**: Split EvidenceEvolution from ReflectionEngine
**Rationale**: Separation of Information Extraction from Reasoning
**Impact**: Low (backward compatible)
**Timeline**: Phase D4 implementation

---

## 2. Current Architecture (V1.0)

### 2.1 ReflectionEngine Responsibilities

ReflectionEngine currently owns:

1. **Information Extraction** (FactExtractorComponent)
   - Entity extraction from evidence
   - Pattern discovery
   - Evidence aggregation
   - Confidence estimation

2. **Reasoning** (ProjectionUpdaterComponent)
   - Proposal generation
   - Create/Refine/Split decisions
   - Level evolution decisions

3. **Validation** (ReflectionValidator)
   - Evidence chain validation
   - Semantic coherence checks
   - Domain invariant enforcement

### 2.2 Problem Statement

**Issue 1**: Mixed Responsibilities
- EvidenceEvolution (extraction) and Reflection (reasoning) are混 in single engine
- Boundary between "what is" and "what should be" is blurred

**Issue 2**: Testing Complexity
- Extraction logic interleaved with reasoning logic
- Hard to test each capability independently

**Issue 3**: Evolution Blocking
- L2→L3 evolution blocked because L2 nodes lack entity_id
- EvidenceEvolution should handle L2+ candidate creation

**Issue 4**: source_level Disconnection
- LLM extraction doesn't output source_level
- source_level defaults to 1 for all proposals
- Multi-level evolution not working

---

## 3. Target Architecture (V1.1)

### 3.1 New Engine Division

```
┌─────────────────────────────────────────────────────────────┐
│                    ReflectionService                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ EvidenceEvolutionEngine                              │   │
│  │                                                      │   │
│  │ Capability: Information Extraction                   │   │
│  │                                                      │   │
│  │ Input:  Evidence / MemoryNode (any level)            │   │
│  │ Output: Candidate                                    │   │
│  │                                                      │   │
│  │ Methods:                                             │   │
│  │ - evolve()                                           │   │
│  │ - extract_entities()                                 │   │
│  │ - discover_patterns()                                │   │
│  │ - aggregate_evidence()                               │   │
│  │ - estimate_confidence()                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ReflectionEngine                                     │   │
│  │                                                      │   │
│  │ Capability: Reasoning                                │   │
│  │                                                      │   │
│  │ Input:  Candidate                                    │   │
│  │ Output: Proposal                                     │   │
│  │                                                      │   │
│  │ Methods:                                             │   │
│  │ - reflect_pipeline()                                 │   │
│  │ - generate_proposals()                               │   │
│  │ - validate_proposals()                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Approval (Service method)                            │   │
│  │                                                      │   │
│  │ Capability: Memory Commit                            │   │
│  │                                                      │   │
│  │ Input:  Proposal                                     │   │
│  │ Output: MemoryNode                                   │   │
│  │                                                      │
│  │ Methods:                                             │
│  │ - approve_proposal()                                 │
│  │ - reject_proposal()                                  │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Pipeline Flow

```
Evidence (L1)
    ↓
EvidenceEvolutionEngine.evolve()
    ↓
Candidate (source_level=1)
    ↓
ReflectionEngine.reflect_pipeline()
    ↓
Proposal (target_level=2)
    ↓
Approval
    ↓
MemoryNode (L2 Pattern)
    ↓
EvidenceEvolutionEngine.evolve()  ← L2 as input
    ↓
Candidate (source_level=2)
    ↓
ReflectionEngine.reflect_pipeline()
    ↓
Proposal (target_level=3)
    ↓
Approval
    ↓
MemoryNode (L3 Belief)
```

---

## 4. Component Details

### 4.1 EvidenceEvolutionEngine

**File**: `backend/src/backend/engine/evidence_evolution_engine.py`

**Responsibilities**:
- Entity extraction from evidence
- Pattern discovery across evidence
- Evidence aggregation
- Evidence chain construction
- Confidence estimation

**LLM Usage**: Yes (for extraction)
**Database Access**: No (Repository only)

**Public Methods**:
```python
async def evolve(self, *, evidence, provider) -> EvolutionResult
async def extract_entities(self, content: str) -> list[dict]
async def discover_patterns(self, evidence_list: list[dict]) -> list[dict]
async def aggregate_evidence(self, evidence_list: list[dict]) -> dict
async def estimate_confidence(self, evidence_list: list[dict]) -> float
```

### 4.2 ReflectionEngine (Updated)

**File**: `backend/src/backend/engine/reflection_engine.py`

**Responsibilities**:
- Candidate evaluation
- Proposal generation
- Reasoning decisions (Create/Refine/Split/Reject)
- Validation

**LLM Usage**: No (rule-based)
**Database Access**: No (Repository only)

**Public Methods**:
```python
async def reflect_pipeline(self, *, scope, candidates, provider) -> dict
def generate_proposals(self, candidates, interest_trends) -> list[dict]
def validate_proposals(self, proposals) -> DomainResult
```

### 4.3 Approval (Service Method)

**File**: `backend/src/backend/service/reflection_service.py`

**Responsibilities**:
- Proposal approval
- MemoryNode creation
- Relationship creation

**LLM Usage**: No
**Database Access**: Yes (direct SQL)

**Public Methods**:
```python
async def approve_proposal(self, *, workspace_id, proposal_id) -> ReflectionExecutionResult
async def reject_proposal(self, *, workspace_id, proposal_id, reason) -> ReflectionExecutionResult
```

---

## 5. Data Model Impact

### 5.1 No Schema Changes

All existing tables remain unchanged:
- `candidates` — Already has `source_level` field
- `proposals` — Already has `source_level`, `target_level`
- `memory_nodes` — Already has `level` field

### 5.2 Candidate Definition Update

**Before**:
- Candidate = Reflection working object
- Created manually via scripts

**After**:
- Candidate = Evidence Evolution output
- Created automatically by EvidenceEvolutionEngine
- source_level indicates evolution origin

### 5.3 Proposal Definition Update

**Before**:
- Proposal = Reflection output
- source_level not consistently propagated

**After**:
- Proposal = Reasoning output
- source_level correctly propagated from Candidate
- target_level = source_level + 1 (for Create/Strengthen)

---

## 6. Implementation Plan

### 6.1 Phase 1: Create EvidenceEvolutionEngine

**Tasks**:
1. Create `backend/src/backend/engine/evidence_evolution_engine.py`
2. Move extraction logic from ReflectionEngine
3. Add proper input/output types
4. Write unit tests

**Estimated Effort**: 2-3 days

### 6.2 Phase 2: Update ReflectionEngine

**Tasks**:
1. Remove `_extract_facts()` method
2. Update `reflect_pipeline()` signature
3. Update `_generate_proposals()` to use Candidate input
4. Update tests

**Estimated Effort**: 1-2 days

### 6.3 Phase 3: Update ReflectionService

**Tasks**:
1. Add `_run_evolution_pipeline()` method
2. Update `reflect()` to call EvidenceEvolutionEngine first
3. Add `_save_candidates()` method
4. Update dependency injection

**Estimated Effort**: 1 day

### 6.4 Phase 4: Deprecate Manual Scripts

**Tasks**:
1. Mark `create_candidates_batch.py` as deprecated
2. Update cron tasks to use automatic evolution
3. Document migration path

**Estimated Effort**: 0.5 days

### 6.5 Phase 5: Testing

**Tasks**:
1. End-to-end pipeline testing
2. Multi-level evolution testing (L1→L2→L3)
3. Performance testing
4. Regression testing

**Estimated Effort**: 2-3 days

---

## 7. Risk Assessment

### 7.1 Low Risk Items

- No database schema changes
- No API contract changes
- Backward compatible data model
- Existing proposals unaffected

### 7.2 Medium Risk Items

- LLM prompt changes may affect extraction quality
- Need to validate source_level propagation
- Multi-level evolution needs testing

### 7.3 Mitigation

- Keep existing ReflectionEngine as fallback
- Add comprehensive logging
- gradual rollout with feature flags

---

## 8. Success Criteria

### 8.1 Functional Criteria

- [ ] EvidenceEvolutionEngine creates Candidates from Evidence
- [ ] source_level correctly propagated through pipeline
- [ ] L2→L3 evolution works automatically
- [ ] Manual scripts no longer required

### 8.2 Non-Functional Criteria

- [ ] Pipeline latency unchanged
- [ ] Test coverage maintained
- [ ] Documentation updated

---

## 9. Related Decisions

- ADR-XXX: Evidence Evolution Split (to be created)
- D4.2g: EvidenceEvolutionEngine Architecture
- D4.2d: ReflectionEngine Architecture (updated)

---

## 10. Revision History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-08-05 | Initial draft | 📝 Draft |
