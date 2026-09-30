# Phase 22.9 Architecture Conflict Adjudication

**Date**: 2026-08-14
**Mode**: READ ONLY — Design Finalization
**Status**: Complete

---

## Executive Verdict

### User Principles Applied

1. ✅ Strategy B (Clean Rebuild) — user preference
2. ✅ Long-term project perspective
3. ✅ Local LLM — cost not primary constraint
4. ✅ Accept longer execution time
5. ✅ Reject preserving architecturally incorrect L1
6. ✅ Do NOT force EvidencePipelineService to replace ReflectionService
7. ✅ Maintain clear Formation/Evolution boundary

### Final Decision

```
REBUILD APPROVED: YES
REBUILD ARCHITECTURE: APPROVED
FROZEN BOUNDARY EXCEPTIONS: GRANTED (4 conflicts resolved)
```

---

## FC-001 Decision: EvidencePipelineService Production Entry

### Verdict: **MANDATORY — Must Enter Production Main Chain**

### Rationale

**Semantic Analysis:**

| Concept | Definition | Owner |
|---------|-----------|--------|
| Formation | Transform raw input into structured intermediate | EvidencePipelineService |
| Evolution | Transform intermediates into confirmed memories | ReflectionService + EvolutionService |

**EvidencePipelineService already implements Formation:**
- ContextWindow formation (LLM)
- Semantic interpretation (LLM)
- Reconstruction + Candidate creation
- Entity resolution at Formation time

**Current Problem:**
- Formation layer is dormant (0 Reconstructions in DB)
- ReflectionService bypasses Formation
- Entity resolution happens too late (lost in Proposal→L1 transition)

### Final Decision

```
EvidencePipelineService MUST be the L0→Candidate entry point.

Not because "it already exists" — but because:
1. Formation is semantically distinct from Evolution
2. Entity resolution must happen at Formation time
3. Reconstruction layer provides semantic context
4. Phase 21 design was correct; implementation was incomplete
```

### Integration Model

**Option Chosen: Sequential Pipeline (Not Parallel)**

```
[Cron Trigger]
      ↓
EvidencePipelineService (Formation)
  - Process ALL pending Evidences
  - Create Candidates with entity_id
  - Create Reconstructions
  - Extract Topics
      ↓
[Queue: Pending Candidates]
      ↓
ReflectionService (L1 Evolution)
  - Batch process Candidates
  - Generate Proposals
  - Create L1 MemoryNodes
      ↓
[Queue: Pending Proposals]
      ↓
EvolutionService (L2/L3 Evolution)
  - Aggregate L1 by entity
  - Create L2 Patterns
  - Create L3 Beliefs
```

**Transaction Boundaries:**
- EvidencePipelineService: Owns transaction (Evidence → Candidate)
- ReflectionService: Owns transaction (Candidate → L1)
- EvolutionService: Does NOT own transaction (caller manages)

---

## FC-002 Decision: L1 Entity Lineage

### Verdict: **MANDATORY — All L1 MUST Have entity_id**

### Rationale

**Data Integrity Analysis:**

```sql
-- Current state (BROKEN)
SELECT COUNT(*) FROM memory_nodes WHERE level = 1 AND entity_id IS NULL;
-- Result: 25,954 (100% broken)

-- Required state (FIXED)
SELECT COUNT(*) FROM memory_nodes WHERE level = 1 AND entity_id IS NULL;
-- Expected: 0
```

**Why entity_id is Non-Negotiable:**

1. **Aggregation requires it**: L2/L3 aggregation groups by entity_id
2. **Lineage requires it**: Evidence → L1 traceability
3. **Query requires it**: "Show all observations about 经费"
4. **Semantics require it**: L1 = Observation ABOUT an entity

### Multi-Entity L1 Handling

**Question**: Can a single L1 reference multiple entities?

**Analysis**:
- Current data: 0 L1 nodes have multi-entity content patterns
- Content structure: "Entity: fact" format (single entity)
- Memory Pyramid semantics: L1 = single Observation

**Decision**: 
```
L1 entity_id: SINGLE (NOT NULLABLE for level=1)

If multi-entity L1 needed in future:
- Use memory_relationships (source_node_id → target_entity_id)
- Use topic_links (link L1 to multiple topics)
- Do NOT use JSON array for entity_id (breaks FK, indexing)
```

### Lineage Rule (Frozen)

```
Rule L1-LINEAGE-001:
  Every L1 MemoryNode MUST have non-NULL entity_id.
  
Rule L1-LINEAGE-002:
  entity_id MUST come from Candidate (not extracted from content).
  
Rule L1-LINEAGE-003:
  If Candidate has NULL entity_id, L1 creation MUST fail.
```

---

## FC-003 Decision: EvolutionService Production Integration

### Verdict: **MANDATORY — Must Handle L2/L3 Creation**

### Current Problem

```python
# evidence_pipeline_service.py:162-168
if interpretation.user_owned:
    await self._evolve(...)  # Only for user-owned, single candidate
```

**Issues:**
1. Only triggered for user-owned interpretations
2. Only processes single candidate
3. Not integrated into Cron pipeline
4. L2/L3 creation is manual/test-only

### Final Responsibility Assignment

| Service | L1 Creation | L2 Creation | L3 Creation |
|---------|-------------|-------------|-------------|
| ReflectionService | ✅ Yes | ❌ No | ❌ No |
| EvolutionService | ❌ No | ✅ Yes | ✅ Yes |
| EvidencePipelineService | ❌ No | ⚠️ Optional | ⚠️ Optional |

**Rationale:**
- ReflectionService focuses on L1 (Observation formation)
- EvolutionService focuses on L2/L3 (Pattern/Belief abstraction)
- Clear separation of concerns

### Integration Model

**Option Chosen: ReflectionService Calls EvolutionService**

```python
# reflection_service.py (future)
async def approve_proposal(self, ..., proposal_id):
    # ... existing L1 creation logic ...
    
    # NEW: Check if L2/L3 evolution needed
    if prop['target_level'] >= 2:
        await self._evolution_service.evolve(
            candidate_id=prop['candidate_id'],
            workspace_id=workspace_id,
            entity_id=entity_id,
        )
```

**Alternative: Cron Direct Call (Also Valid)**

```python
# Cron loop (future)
for entity_id in high_density_entities:
    await evolution_service.evolve_entity_history(
        entity_id=entity_id,
        workspace_id=workspace_id,
    )
```

**Decision**: Support BOTH models:
1. ReflectionService calls EvolutionService for immediate L2/L3
2. Cron can also call EvolutionService for batch L2/L3 processing

---

## FC-004 Decision: Cross-Batch Aggregation

### Verdict: **IMPLEMENT — Using L1 Aggregation (No entity_facts)**

### Why NOT entity_facts

| Aspect | entity_facts Table | Direct L1 Aggregation |
|--------|-------------------|----------------------|
| Data duplication | High (copies L1 content) | None |
| Maintenance | Triggers needed | None |
| Query complexity | Simple | Moderate |
| Lineage clarity | Indirect (via source_l1_id) | Direct (L1 is source) |
| Memory Pyramid alignment | Adds new layer | Uses existing layers |

**Decision**: Do NOT add entity_facts table. Use direct L1 aggregation.

### Aggregation Model

```python
# EvolutionService (new method)
async def evolve_entity_history(
    self,
    *,
    entity_id: UUID,
    workspace_id: UUID,
    time_window: timedelta = timedelta(days=30),
) -> EvolutionResult:
    """Aggregate L1 MemoryNodes for an entity and create L2/L3."""
    
    # Step 1: Query historical L1 for entity
    l1_nodes = await self.memory_repo.find_by_entity(
        entity_id=entity_id,
        level=1,
        created_after=NOW() - time_window,
        limit=100,  # Context window limit
    )
    
    # Step 2: Aggregate facts
    facts = await self._aggregate_l1_facts(l1_nodes)
    
    # Step 3: Check threshold
    if len(facts) >= 3 and avg_confidence >= 0.8:
        # Create L2 Pattern
        l2_node = await self._create_pattern(entity_id, facts)
        return EvolutionResult(success=True, l2_node=l2_node)
    
    return EvolutionResult(success=False, rationale="threshold_not_met")
```

### Historical Window Design

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| time_window | 30 days | Balance recency vs. history |
| max_l1_nodes | 100 | LLM context limit |
| min_facts_for_l2 | 3 | Threshold from ReflectionEngine |
| min_confidence_for_l2 | 0.8 | Confidence requirement |

### Grouping Dimensions

```
Primary: entity_id (required)
Secondary: topic_ids (optional, via topic_links)
Tertiary: area_id (optional, spatial context)
```

---

## Final Production Pipeline

### Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────┘

[Phase 1: Formation]
                    │
                    ▼
  ┌───────────────────────────────────────┐
  │     EvidencePipelineService           │
  │   (Transaction Owner: Self)           │
  ├───────────────────────────────────────┤
  │ Input:  evidence_id, workspace_id     │
  │ LLM:    ContextWindow, Interpretation │
  │ Output: Candidate (with entity_id)    │
  │         Reconstruction                │
  │         Topics                        │
  └───────────────────────────────────────┘
                    │
                    ▼
            [Pending Candidates]
                    │
                    │ Cron triggers
                    ▼
  ┌───────────────────────────────────────┐
  │     ReflectionService                 │
  │   (Transaction Owner: Self)           │
  ├───────────────────────────────────────┤
  │ Input:  workspace_id, limit=50        │
  │ LLM:    Fact extraction, Proposal gen │
  │ Output: Proposals                     │
  │         L1 MemoryNodes (with entity_id)│
  └───────────────────────────────────────┘
                    │
                    ▼
            [Pending Proposals]
                    │
                    │ Auto-approve
                    ▼
  ┌───────────────────────────────────────┐
  │     EvolutionService                  │
  │   (Transaction Owner: Caller)         │
  ├───────────────────────────────────────┤
  │ Input:  candidate_id OR entity_id     │
  │ LLM:    Pattern detection             │
  │ Output: L2 Patterns                   │
  │         L3 Beliefs                    │
  │         Relationships                 │
  └───────────────────────────────────────┘
                    │
                    ▼
            [Confirmed Memories]
```

### Service Responsibility Matrix

| Service | Formation | L1 Creation | L2 Creation | L3 Creation | LLM Calls | Batch | Cron Callable |
|---------|-----------|-------------|-------------|-------------|-----------|-------|---------------|
| EvidencePipelineService | ✅ Primary | ❌ | ❌ | ❌ | ContextWindow, Interpretation | NO | NO (API only) |
| ReflectionService | ❌ | ✅ Primary | ❌ | ❌ | Fact extraction, Proposals | YES | YES |
| EvolutionService | ❌ | ❌ | ✅ Primary | ✅ Primary | Pattern detection | Optional | YES (optional) |

---

## Memory Pyramid Creation Ownership

| Level | Node Type | Created By | Input | Threshold |
|-------|-----------|------------|-------|-----------|
| L0 | Evidence | Import/API | Raw conversation | N/A |
| L1 | Observation | ReflectionService | Candidates | Proposal approved |
| L2 | Pattern | EvolutionService | Historical L1 (entity-aggregated) | ≥3 facts, conf≥0.8 |
| L3 | Belief | EvolutionService | Historical L2 (cross-entity) | ≥2 patterns, conf≥0.7 |

### Immutability Rules (Reinforced)

| Level | Append-only | Update allowed | Delete allowed | Rationale |
|-------|-------------|----------------|----------------|-----------|
| L0 | ✅ | ❌ | ❌ (soft) | Source of truth |
| L1 | ✅ | ⚠️ Rare | ❌ | Confirmed observation |
| L2 | ✅ | ❌ | ❌ | Aggregated pattern |
| L3 | ✅ | ❌ | ❌ | Fundamental belief |

---

## L1 Entity Lineage Rules (Final)

### Rule Set

```
RULE-L1-001: Every L1 MUST have non-NULL entity_id
RULE-L1-002: entity_id MUST come from Candidate (propagation, not extraction)
RULE-L1-003: If Candidate.entity_id IS NULL, L1 creation MUST fail
RULE-L1-004: L1.entity_id MUST match exactly one Entity.canonical_name
RULE-L1-005: Multi-entity L1 uses memory_relationships (not JSON array)
RULE-L1-006: evidence_links MUST preserve full lineage to Evidences
RULE-L1-007: proposal_id is NOT stored in L1 (transient object)
```

### Lineage Chain (Required)

```
Evidence.id
    ↓ evidence_chain
Candidate.evidence_chain (array of Evidence IDs)
    ↓ candidate_id FK
Proposal.candidate_id
    ↓ evidence_chain propagation
L1.evidence_links (array of Candidate IDs)
    ↓ entity_id propagation
L1.entity_id ← MUST BE SET
```

---

## Cross-Batch Aggregation Model (Final)

### Design: L1-Based Aggregation (No entity_facts)

```python
# EvolutionService.new_method()
async def evolve_entity_history(
    self,
    *,
    entity_id: UUID,
    workspace_id: UUID,
    time_window_days: int = 30,
) -> list[MemoryNode]:
    """
    Aggregate L1 MemoryNodes for an entity and create L2/L3.
    
    Returns:
        List of newly created L2/L3 MemoryNodes
    """
    # 1. Query historical L1
    l1_nodes = await self._query_l1_history(
        entity_id=entity_id,
        workspace_id=workspace_id,
        created_after=NOW() - timedelta(days=time_window_days),
    )
    
    # 2. Extract facts from L1 content
    facts = await self._extract_facts_from_l1(l1_nodes)
    
    # 3. Check thresholds
    if len(facts) >= 3 and self._avg_confidence(facts) >= 0.8:
        # 4. Create L2 Pattern
        return await self._create_pattern(entity_id, facts)
    
    return []
```

### Why This Works

1. **L1 already contains entity-specific facts**
2. **No data duplication** (entity_facts would copy L1 content)
3. **Lineage preserved** (L2 references L1 IDs)
4. **Query-able** (WHERE entity_id = X)
5. **Time-windowed** (configurable history depth)

---

## Candidate Lifecycle (Final)

### State Machine

```
                    ┌─────────────┐
                    │  PENDING    │ ← FormationService creates
                    │ (entity_id) │   with proper entity linkage
                    └──────┬──────┘
                           │
              Proposal generated
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │ CONFIRMED │ │ORPHANED│ │ ARCHIVED  │
        │ (L1 created)│ (rejected)│(after 30d)│
        └─────┬─────┘ └───┬───┘ └─────┬─────┘
              │            │            │
         Keep 30d     Delete 7d    Permanent
         for audit    orphaned     (read-only)
```

### Retention Policy

| Status | Duration | Action |
|--------|----------|--------|
| PENDING | Until proposal | Keep for workflow |
| CONFIRMED | 30 days post-L1 | Archive |
| ORPHANED | 7 days | Delete |
| ARCHIVED | Permanent | Read-only audit |

---

## Proposal Lifecycle (Final)

### State Machine

```
                    ┌─────────────┐
                    │   PENDING   │ ← ReflectionService creates
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │  APPROVED │ │REJECT │ │  REVISED  │
        └─────┬─────┘ └───┬───┘ └─────┬─────┘
              │            │            │
         Create L1     Mark orphan  Re-evaluate
         keep 90d     candidate
```

### Retention Policy

| Status | Duration | Reason |
|--------|----------|--------|
| PENDING | Until decision | Workflow state |
| APPROVED | Permanent | Audit trail |
| REJECTED | 90 days | Dispute resolution |
| REVISED | Until final | Workflow state |

---

## Phase 20/21 Frozen Boundary Exceptions

### Exception List (Requires User Approval)

| ID | File | Line(s) | Change | Justification |
|----|------|---------|--------|---------------|
| EX-001 | reflection_service.py | 248-250 | Extract entity_id from Candidate | Fix critical bug (L1 NULL entity_id) |
| EX-002 | evidence_pipeline_service.py | Cron integration | Enable Formation in production | Restore dormant Formation layer |
| EX-003 | evolution_service.py | New method | Add evolve_entity_history() | Enable L2/L3 aggregation |
| EX-004 | app.py | Cron loop | Integrate EvidencePipelineService | Complete pipeline |

### Changes That Do NOT Require Exception

| ID | File | Change | Reason |
|----|------|--------|--------|
| NC-001 | migration | Add entity_id NOT NULL constraint | Bug fix, not design change |
| NC-002 | tests | Update for new behavior | Test maintenance |
| NC-003 | docs | Document new pipeline | Documentation |

---

## Clean Rebuild Approval

### Status: **APPROVED** ✅

### Conditions

```
[✓] FC-001 Resolved: EvidencePipelineService enters production
[✓] FC-002 Resolved: L1 entity_id mandatory
[✓] FC-003 Resolved: EvolutionService handles L2/L3
[✓] FC-004 Resolved: L1-based aggregation (no entity_facts)
[✓] User principles aligned with Strategy B
[✓] Long-term project justification accepted
```

### Prerequisites (Must Complete Before Rebuild)

```
[ ] Code changes approved by user
[ ] Rollback plan tested in staging
[ ] Performance baseline established
[ ] Stakeholder notification sent
[ ] Backup strategy finalized
```

---

## Required Implementation Changes

### Phase 1: Code Fixes (Estimated: 1 day)

| Task | File | Description |
|------|------|-------------|
| 1.1 | reflection_service.py | Fix entity_id propagation (3 lines) |
| 1.2 | evidence_pipeline_service.py | Enable Cron integration |
| 1.3 | evolution_service.py | Add evolve_entity_history() method |
| 1.4 | app.py | Update Cron loop |

### Phase 2: Migration (Estimated: 1 hour)

| Task | Description |
|------|-------------|
| 2.1 | Add NOT NULL constraint to memory_nodes.entity_id (level=1) |
| 2.2 | Backfill existing L1 with entity_id (from Proposal→Candidate) |
| 2.3 | Validate no NULL entity_id remains |

### Phase 3: Clean Rebuild (Estimated: 2-3 days)

| Task | Description |
|------|-------------|
| 3.1 | Freeze Cron, backup derived tables |
| 3.2 | Truncate candidates, proposals, memory_nodes |
| 3.3 | Re-process all Evidences through EvidencePipelineService |
| 3.4 | Run ReflectionService on new Candidates |
| 3.5 | Run EvolutionService for L2/L3 |
| 3.6 | Validate lineage and data quality |

### Phase 4: Validation (Estimated: 1 day)

| Task | Description |
|------|-------------|
| 4.1 | Run Phase 20/21 test suite |
| 4.2 | Verify all L1 have entity_id |
| 4.3 | Check L2/L3 creation rates |
| 4.4 | Performance benchmarking |

---

## Required Validation Gates

### Gate 1: Pre-Rebuild

```
[ ] Evidence count = 15,662 (verified)
[ ] Entity count = 4,609 (verified)
[ ] Backup completed (all derived tables)
[ ] Rollback plan tested
[ ] Code changes reviewed and approved
```

### Gate 2: Post-Cleanup

```
[ ] Only base tables remain (workspace, user_profiles, areas, entities, evidences)
[ ] No orphaned FK references
[ ] Database integrity check passed
```

### Gate 3: Post-Formation

```
[ ] Candidates created with entity_id (100%)
[ ] Reconstructions created (match Candidate count)
[ ] Topics extracted (non-zero)
[ ] Lineage: Evidence → Candidate verified
```

### Gate 4: Post-Evolution (L1)

```
[ ] L1 MemoryNodes created (match Proposal count)
[ ] All L1 have entity_id (100%)
[ ] All L1 have evidence_links
[ ] Lineage: Candidate → L1 verified
```

### Gate 5: Post-Advanced Evolution (L2/L3)

```
[ ] L2 Patterns created (count > 0)
[ ] L3 Beliefs created (count >= 0)
[ ] L2 entity_id set correctly
[ ] Relationships created
[ ] Threshold logic working (≥3 facts → L2)
```

### Gate 6: Production

```
[ ] Cron running successfully
[ ] No UniqueViolation errors
[ ] Memory growth stable
[ ] Query performance acceptable (<100ms for entity query)
[ ] Zero data loss (all Evidences preserved)
```

---

## Open Design Questions (For Future Resolution)

### Q1: Should entity_facts be added later?
**Status**: Not needed now. Re-evaluate if L2 creation performance degrades.

### Q2: How to handle multi-entity L1 in future?
**Status**: Use memory_relationships. Do NOT change entity_id to JSON array.

### Q3: What is the optimal time window for L2 aggregation?
**Status**: Default 30 days. Tunable via configuration.

### Q4: Should EvolutionService run synchronously or asynchronously?
**Status**: Synchronous for immediate L2 creation, asynchronous for batch L3 creation.

---

## Summary

| Aspect | Decision |
|--------|----------|
| REBUILD APPROVED | ✅ YES |
| FC-001 | ✅ EvidencePipelineService → Production |
| FC-002 | ✅ L1 entity_id mandatory |
| FC-003 | ✅ EvolutionService → L2/L3 owner |
| FC-004 | ✅ L1 aggregation (no entity_facts) |
| Strategy | ✅ B (Clean Rebuild) |
| Frozen Exceptions | ✅ 4 granted |
| Next Phase | Implementation |

---

**Adjudication complete. Awaiting user approval to proceed with Implementation Phase.**
