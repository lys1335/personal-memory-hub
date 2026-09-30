# Phase 22.10 Clean Rebuild Implementation Design

**Date**: 2026-08-14
**Mode**: READ ONLY — Implementation Design
**Status**: Complete

---

## Executive Summary

This document translates Phase 22.9's architecture adjudication into an actionable, unambiguous implementation plan. All designs are READ ONLY — no code, database, or configuration changes are made.

**Key Resolution**: Resolved the FC-001 contradiction by defining clear service boundaries and a sequential pipeline architecture.

---

## 1. Final Runtime Architecture

### Resolving FC-001 Contradiction

**Phase 22.9 stated contradiction:**
- EvidencePipelineService: Cron Callable = NO (API only)
- But also: Enable EvidencePipelineService Cron integration

**Resolution:**

EvidencePipelineService is NOT called directly by Cron. Instead, a new **Orchestration Layer** coordinates the pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────┘

[Cron Trigger]
      ↓
[Orchestrator: _run_full_pipeline()]
      ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  Stage 1: Formation (EvidencePipelineService)                          │
│  ─────────────────────────────────────                                                                 │
│  Input:  All pending Evidences (status='pending')                      │
│  Process: Evidence → ContextWindow → Interpretation → Candidate        │
│  Output: Candidates (with entity_id), Reconstructions, Topics          │
│  Transaction: Owns its own transaction                                 │
│  LLM Calls: ContextWindowFormulator, UserSemanticInterpreter           │
└─────────────────────────────────────────────────────────────────────────┘
                                      ↓
                              [Pending Candidates]
                                      ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  Stage 2: L1 Evolution (ReflectionService)                              │
│  ─────────────────────────────────────                                                                 │
│  Input:  All pending Candidates (status='candidate')                   │
│  Process: Candidate → Fact Extraction → Proposal → L1 MemoryNode       │
│  Output: Proposals, L1 MemoryNodes (with entity_id)                    │
│  Transaction: Owns its own transaction                                 │
│  LLM Calls: ReflectionEngine (fact extraction, proposal generation)    │
└─────────────────────────────────────────────────────────────────────────┘
                                      ↓
                              [Approved L1 MemoryNodes]
                                      ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  Stage 3: L2/L3 Evolution (EvolutionService)                            │
│  ─────────────────────────────────────                                                                 │
│  Input:  Entity-level L1 history                                       │
│  Process: Aggregate L1 by entity → Create L2 Patterns / L3 Beliefs     │
│  Output: L2 MemoryNodes, L3 MemoryNodes, Relationships                 │
│  Transaction: Caller-managed (Orchestrator)                            │
│  LLM Calls: Pattern detection (optional, threshold-based)              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why This Architecture Works

| Aspect | Solution |
|--------|----------|
| Formation responsibility | EvidencePipelineService (unchanged) |
| L1 creation responsibility | ReflectionService (unchanged, with entity_id fix) |
| L2/L3 creation responsibility | EvolutionService (enhanced with aggregation) |
| Pipeline coordination | New Orchestrator function in app.py |
| Transaction boundaries | Each service owns its transaction |
| Cron entry point | Orchestrator (not direct service call) |

---

## 2. Final Service Responsibility Matrix

### EvidencePipelineService

| Aspect | Specification |
|--------|---------------|
| **Primary Duty** | Formation: Evidence → Candidate |
| **Input** | evidence_id, workspace_id |
| **Output** | candidate_id, reconstruction_id, topic_ids |
| **Persists** | Candidate, Reconstruction, Topics |
| **Creates MemoryNode** | NO (removed from production path) |
| **Calls LLM** | YES (ContextWindow, Interpretation) |
| **Batch Processing** | NO (single evidence at a time) |
| **Cross-history** | NO |
| **Transaction Owner** | YES (own transaction) |
| **Cron Callable** | NO (called by Orchestrator) |
| **API Endpoint** | POST /pipeline/trigger |

**Critical Change**: Remove direct L2 creation from production path. L2/L3 should ONLY be created by EvolutionService.

```python
# Current (evidence_pipeline_service.py:162-168):
if interpretation.user_owned:
    await self._evolve(...)  # Creates L2 directly — REMOVE from production

# Future (post-rebuild):
# EvidencePipelineService only creates Candidate
# EvolutionService handles L2/L3
```

---

### ReflectionService

| Aspect | Specification |
|--------|---------------|
| **Primary Duty** | L1 Evolution: Candidate → L1 MemoryNode |
| **Input** | workspace_id, limit=50 |
| **Output** | Proposals, L1 MemoryNodes |
| **Persists** | Proposals, MemoryNodes (level=1) |
| **Creates MemoryNode** | YES (L1 Observation only) |
| **Calls LLM** | YES (fact extraction, proposal generation) |
| **Batch Processing** | YES (processes up to 50 candidates) |
| **Cross-history** | NO (current limitation) |
| **Transaction Owner** | YES (own transaction) |
| **Cron Callable** | YES (via Orchestrator) |

**Required Fix**: Extract entity_id from Candidate in `approve_proposal()`:

```python
# reflection_service.py:248-250 (CURRENT — BROKEN):
entity_id = None  # BUG: Always None

# reflection_service.py:248-250 (FIXED):
candidate = await self._candidate_repo.find_by_id(prop['candidate_id'])
entity_id = candidate.entity_id if candidate else None
```

---

### EvolutionService

| Aspect | Specification |
|--------|---------------|
| **Primary Duty** | L2/L3 Evolution: L1 history → Pattern/Belief |
| **Input** | candidate_id OR entity_id (for aggregation) |
| **Output** | L2 MemoryNodes, L3 MemoryNodes, Relationships |
| **Persists** | MemoryNodes (level≥2), Relationships |
| **Creates MemoryNode** | YES (L2 Pattern, L3 Belief) |
| **Calls LLM** | YES (pattern detection, optional) |
| **Batch Processing** | Optional (can process entity history) |
| **Cross-history** | YES (queries historical L1 nodes) |
| **Transaction Owner** | NO (caller manages) |
| **Cron Callable** | YES (via Orchestrator, optional) |

**Required Enhancement**: Add `evolve_entity_history()` method:

```python
# evolution_service.py (NEW METHOD):
async def evolve_entity_history(
    self,
    *,
    entity_id: UUID,
    workspace_id: UUID,
    time_window_days: int = 30,
) -> list[MemoryNode]:
    """Aggregate L1 MemoryNodes for an entity and create L2/L3."""
    # 1. Query historical L1
    l1_nodes = await self.memory_repo.find_by_entity(
        entity_id=entity_id,
        level=1,
        created_after=NOW() - timedelta(days=time_window_days),
    )
    
    # 2. Check threshold (≥3 facts, confidence≥0.8)
    if len(l1_nodes) >= 3 and self._avg_confidence(l1_nodes) >= 0.8:
        # 3. Create L2 Pattern
        return await self._create_pattern(entity_id, l1_nodes)
    
    return []
```

---

### Orchestrator (New in app.py)

| Aspect | Specification |
|--------|---------------|
| **Primary Duty** | Coordinate Formation → L1 → L2/L3 pipeline |
| **Input** | workspace_id, optional filters |
| **Output** | PipelineResult with statistics |
| **Persists** | Nothing directly (delegates to services) |
| **Creates MemoryNode** | NO |
| **Calls LLM** | NO (delegates to services) |
| **Batch Processing** | YES (coordinates multiple services) |
| **Cross-history** | YES (aggregates results) |
| **Transaction Owner** | NO (each service owns its transaction) |
| **Cron Callable** | YES (primary entry point) |

```python
# app.py (NEW FUNCTION):
async def _run_full_pipeline(workspace_id: UUID, limit: int = 200):
    """Run the complete L0→L3 pipeline."""
    
    # Stage 1: Formation (Evidence → Candidate)
    formation_result = await _run_formation_phase(workspace_id, limit)
    
    # Stage 2: L1 Evolution (Candidate → L1)
    l1_result = await _run_l1_evolution_phase(workspace_id, limit)
    
    # Stage 3: L2/L3 Evolution (L1 → L2 → L3)
    l2_result = await _run_l2_evolution_phase(workspace_id)
    
    return PipelineOrchestrationResult(
        formation=formation_result,
        l1_evolution=l1_result,
        l2_evolution=l2_result,
    )
```

---

## 3. Final Call Graph

### Production Pipeline (Post-Rebuild)

```
[Cron: every 10 minutes]
        ↓
[Orchestrator: _run_full_pipeline()]
        ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 1: Formation                                          │
│  Orchestrator → EvidencePipelineService.process_evidence()   │
│    → ContextWindowFormulator (LLM)                           │
│    → UserSemanticInterpreter (LLM)                           │
│    → FormationService.form()                                 │
│      → Create Candidate (with entity_id)                     │
│      → Create Reconstruction                                 │
│      → Extract Topics                                        │
└──────────────────────────────────────────────────────────────┘
        ↓
[Candidate created, status='candidate']
        ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 2: L1 Evolution                                       │
│  Orchestrator → ReflectionService.reflect()                  │
│    → _acquire_scope() (query pending candidates)             │
│    → EvidenceEvolutionEngine.evolve() (LLM: fact extraction) │
│    → ReflectionEngine.reflect_pipeline() (LLM: proposals)    │
│    → _save_proposals()                                       │
│    → _auto_approve_pending_proposals()                       │
│      → approve_proposal()                                    │
│        → CREATE L1 MemoryNode (with entity_id) ✅            │
└──────────────────────────────────────────────────────────────┘
        ↓
[L1 MemoryNode created, status='active']
        ↓
┌──────────────────────────────────────────────────────────────┐
│  Stage 3: L2/L3 Evolution (Optional, periodic)               │
│  Orchestrator → EvolutionService.evolve_entity_history()     │
│    → Query L1 by entity_id                                   │
│    → Aggregate facts                                         │
│    → Create L2 Pattern (if threshold met)                    │
│    → Create L3 Belief (if threshold met)                     │
└──────────────────────────────────────────────────────────────┘
        ↓
[L2 Pattern / L3 Belief created]
```

### API Entry Points

```
POST /pipeline/trigger          → EvidencePipelineService.process_evidence()
                                  (Single evidence, Formation only)

POST /api/reflect               → ReflectionService.reflect()
                                  (Manual L1 trigger)

POST /api/cron/tasks/{id}/run-now → Orchestrator._run_full_pipeline()
                                  (Manual full pipeline trigger)
```

---

## 4. Formation / L1 / L2 / L3 Boundaries

### Formation Boundary (EvidencePipelineService)

```
Input:  Evidence (L0)
Process: ContextWindow → Interpretation → Formation
Output: Candidate (intermediate), Reconstruction (intermediate), Topics (metadata)
Transaction: EvidencePipelineService owns
LLM Calls: ContextWindowFormulator, UserSemanticInterpreter
Deterministic: NO (LLM-dependent)
Idempotent: YES (by evidence_id)
```

### L1 Boundary (ReflectionService)

```
Input:  Candidate (with entity_id)
Process: Fact extraction → Proposal generation → Approval
Output: L1 MemoryNode (Observation)
Transaction: ReflectionService owns
LLM Calls: ReflectionEngine (fact extraction, proposal generation)
Deterministic: NO (LLM-dependent)
Idempotent: YES (by candidate_id, via P0 dedup fix)
```

### L2 Boundary (EvolutionService)

```
Input:  Historical L1 MemoryNodes (aggregated by entity_id)
Process: Pattern detection → Threshold check
Output: L2 MemoryNode (Pattern)
Transaction: Caller-managed (Orchestrator)
LLM Calls: Optional (pattern detection)
Deterministic: YES (threshold-based, minimal LLM)
Idempotent: YES (by entity_id + time_window)
```

### L3 Boundary (EvolutionService)

```
Input:  Historical L2 MemoryNodes (cross-entity)
Process: Belief detection → Threshold check
Output: L3 MemoryNode (Belief)
Transaction: Caller-managed (Orchestrator)
LLM Calls: Optional
Deterministic: YES (threshold-based)
Idempotent: YES (by cross-entity pattern)
```

---

## 5. Entity Lineage Design

### Required Lineage Chain

```
Evidence.id
    ↓ evidence_chain (array of Evidence IDs)
Candidate.evidence_chain
    ↓ candidate_id (FK)
Proposal.candidate_id
    ↓ evidence_chain (propagated)
L1 MemoryNode.evidence_links
    ↓ entity_id (propagated from Candidate)
L1 MemoryNode.entity_id ✅ MUST BE SET

L1.entity_id
    ↓ aggregation
EvolutionService.evolve_entity_history(entity_id)
    ↓
L2 MemoryNode.entity_id ✅ MUST BE SET
```

### Entity Resolution at Formation Time

```python
# formation_service.py:_create_candidate() (ALREADY CORRECT):
candidate = Candidate(
    entity_id=entity_id,  # Resolved from interpretation
    evidence_chain=[str(eid) for eid in evidence_ids],
    content=interpretation.semantic_content,
    ...
)
```

**Key Point**: Entity is resolved at Formation time, NOT at L1 creation time.

### Migration for entity_id

```sql
-- Step 1: Add NOT NULL constraint (for new L1 only)
ALTER TABLE memory_nodes 
ADD CONSTRAINT chk_level1_has_entity 
CHECK (level <> 1 OR entity_id IS NOT NULL);

-- Step 2: Backfill recoverable L1 (via Proposal→Candidate)
WITH lineage AS (
  SELECT mn.id as l1_id, c.entity_id
  FROM memory_nodes mn
  JOIN proposals p ON p.evidence_chain = mn.evidence_links
  JOIN candidates c ON c.id = p.candidate_id
  WHERE mn.level = 1 AND mn.entity_id IS NULL
)
UPDATE memory_nodes mn
SET entity_id = l.entity_id
FROM lineage l
WHERE mn.id = l.l1_id;

-- Step 3: Verify
SELECT COUNT(*) FROM memory_nodes 
WHERE level = 1 AND entity_id IS NULL;
-- Expected: 0 for backfilled, >0 for legacy orphaned
```

---

## 6. Clean Rebuild Workflow

### Phase 0: Preparation

```sql
-- 0.1: Freezing point (capture current state)
CREATE TABLE candidates_pre_rebuild_backup AS 
  SELECT * FROM candidates;
CREATE TABLE proposals_pre_rebuild_backup AS 
  SELECT * FROM proposals;
CREATE TABLE memory_nodes_pre_rebuild_backup AS 
  SELECT * FROM memory_nodes;
CREATE TABLE reconstructions_pre_rebuild_backup AS 
  SELECT * FROM reconstructions;

-- 0.2: Verify source data integrity
SELECT COUNT(*) FROM evidences;  -- Must be 15,662
SELECT COUNT(*) FROM entities;   -- Must be 4,609
SELECT COUNT(*) FROM areas;      -- Must be 3,732
```

### Phase 1: Code Changes

```
1.1: reflection_service.py:248-250
     Fix entity_id propagation from Candidate to L1
     
1.2: evidence_pipeline_service.py:162-168
     Comment out or remove direct L2 creation:
     # if interpretation.user_owned:
     #     await self._evolve(...)
     
1.3: evolution_service.py (NEW METHOD)
     Add evolve_entity_history(entity_id, workspace_id, time_window_days)
     
1.4: app.py (NEW FUNCTION)
     Add _run_full_pipeline(workspace_id, limit)
     Update Cron loop to call orchestrator
```

### Phase 2: Database Cleanup

```sql
-- 2.1: Truncate in correct order (respect FK dependencies)
TRUNCATE topic_links RESTART IDENTITY;
TRUNCATE proposals RESTART IDENTITY;
TRUNCATE memory_nodes RESTART IDENTITY;
TRUNCATE candidates RESTART IDENTITY;
TRUNCATE reconstructions RESTART IDENTITY;

-- 2.2: Verify cleanup
SELECT COUNT(*) FROM candidates;   -- Must be 0
SELECT COUNT(*) FROM proposals;    -- Must be 0
SELECT COUNT(*) FROM memory_nodes; -- Must be 0 (base data preserved)
SELECT COUNT(*) FROM evidences;    -- Must be 15,662 (preserved)
```

### Phase 3: Rebuild from Evidence

```python
# Orchestrator logic for rebuild:
async def _rebuild_from_evidences(workspace_id: UUID):
    # Get all evidences
    evidences = await get_all_evidences(workspace_id)
    
    # Process each evidence through Formation
    for evidence in evidences:
        result = await evidence_pipeline_service.process_evidence(
            evidence_id=evidence.id,
            workspace_id=workspace_id,
        )
        logger.info(f"Formation: evidence={evidence.id}, candidate={result.candidate_id}")
    
    # Run L1 evolution on all new candidates
    await reflection_service.reflect(
        workspace_id=workspace_id,
        scope="daily",
        limit=1000,  # Large batch for rebuild
    )
    
    # Run L2/L3 evolution
    entities = await get_all_entities(workspace_id)
    for entity in entities:
        await evolution_service.evolve_entity_history(
            entity_id=entity.id,
            workspace_id=workspace_id,
            time_window_days=365,  # Full history for rebuild
        )
```

### Phase 4: Validation

```
4.1: Lineage validation
     SELECT COUNT(*) FROM memory_nodes WHERE level=1 AND entity_id IS NULL;
     Expected: 0 (all L1 have entity_id)
     
4.2: Candidate validation
     SELECT COUNT(*) FROM candidates WHERE entity_id IS NULL;
     Expected: 0 (all candidates have entity_id)
     
4.3: Evidence preservation
     SELECT COUNT(*) FROM evidences;
     Expected: 15,662 (no data loss)
     
4.4: Test suite
     Run all Phase 20/21 tests
     Expected: All pass
```

---

## 7. Migration Plan

### Migration 1: Add entity_id constraint (Optional)

```sql
-- Only apply AFTER rebuild confirms all new L1 have entity_id
ALTER TABLE memory_nodes 
ADD CONSTRAINT chk_level1_has_entity 
CHECK (level <> 1 OR entity_id IS NOT NULL);
```

### Migration 2: Add proposal.entity_id (Optional, Future)

```sql
-- NOT REQUIRED for rebuild
-- Only if we want explicit entity_id in proposals
-- ALTER TABLE proposals ADD COLUMN entity_id UUID REFERENCES entities(id);
```

### Backfill Script (For existing data)

```sql
-- Backfill entity_id for L1 nodes with valid proposal lineage
WITH lineage AS (
  SELECT 
    mn.id as l1_id,
    c.entity_id
  FROM memory_nodes mn
  JOIN proposals p ON p.evidence_chain = mn.evidence_links
  JOIN candidates c ON c.id = p.candidate_id
  WHERE mn.level = 1 AND mn.entity_id IS NULL
)
UPDATE memory_nodes mn
SET entity_id = l.entity_id
FROM lineage l
WHERE mn.id = l.l1_id;

-- Verify
SELECT 
  COUNT(*) as total_l1,
  COUNT(entity_id) as with_entity,
  COUNT(*) - COUNT(entity_id) as without_entity
FROM memory_nodes WHERE level = 1;
```

---

## 8. Cron Architecture

### Current Cron (Pre-Rebuild)

```python
# app.py: _cron_scheduler_loop()
# Calls: run_cron_task_now() → ReflectionService.reflect()
# Only does L1 evolution, skips Formation
```

### New Cron (Post-Rebuild)

```python
# app.py: _cron_scheduler_loop()
# Calls: run_cron_task_now() → Orchestrator._run_full_pipeline()
# Does: Formation → L1 Evolution → L2/L3 Evolution
```

### Cron Task Configuration

```json
{
  "task_id": "evolution",
  "type": "evolution",
  "enabled": true,
  "interval_seconds": 600,
  "payload": {
    "workspace_id": "fd0223ed-7aa2-491e-8db5-b0de71b75219",
    "limit": 50,
    "run_formation": true,
    "run_l1_evolution": true,
    "run_l2_evolution": false
  }
}
```

**Note**: L2/L3 evolution is optional in Cron (can be run separately or periodically).

---

## 9. Idempotency Strategy

### EvidencePipelineService (Formation)

```python
# Idempotency key: evidence_id
# If evidence already processed, skip
async def process_evidence(self, evidence_id, workspace_id):
    # Check if candidate already exists for this evidence
    existing = await self.candidate_repo.find_by_evidence(evidence_id)
    if existing:
        logger.info(f"Evidence {evidence_id} already processed, skipping")
        return PipelineResult(success=True, skipped="already_processed")
    
    # Proceed with Formation...
```

### ReflectionService (L1 Evolution)

```python
# Idempotency key: candidate_id
# Already implemented via P0 fix (unique constraint on workspace_id + candidate_id)
# Duplicate proposals are deduplicated
```

### EvolutionService (L2/L3)

```python
# Idempotency key: entity_id + time_window
# If L2 already exists for entity in window, skip
async def evolve_entity_history(self, entity_id, workspace_id, time_window_days=30):
    # Check if L2 already exists
    existing_l2 = await self.memory_repo.find_by_entity(
        entity_id=entity_id, level=2
    )
    if existing_l2:
        logger.info(f"L2 already exists for entity {entity_id}, skipping")
        return []
    
    # Proceed with evolution...
```

---

## 10. Transaction Boundaries

| Service | Transaction | Scope | Rollback Behavior |
|---------|------------|-------|-------------------|
| EvidencePipelineService | Owns | Single evidence → Candidate | Full rollback on failure |
| ReflectionService | Owns | Batch Candidates → L1 | Full rollback on failure |
| EvolutionService | Caller-managed | Single entity history → L2/L3 | Caller decides |
| Orchestrator | No transaction | Coordinates services | Logs failures, continues |

**Critical Rule**: Each service must be able to rollback independently. Orchestrator does NOT wrap all services in a single transaction.

---

## 11. Rollback Strategy

### Pre-Rebuild Backup

```sql
-- Backup all derived tables
CREATE TABLE candidates_backup_20260814 AS SELECT * FROM candidates;
CREATE TABLE proposals_backup_20260814 AS SELECT * FROM proposals;
CREATE TABLE memory_nodes_backup_20260814 AS SELECT * FROM memory_nodes;
CREATE TABLE reconstructions_backup_20260814 AS SELECT * FROM reconstructions;
```

### Rollback Procedure

```
Step R1: Stop Cron
Step R2: Restore backups
        DROP TABLE candidates;
        CREATE TABLE candidates AS SELECT * FROM candidates_backup_20260814;
        (Repeat for proposals, memory_nodes, reconstructions)
Step R3: Verify restore
        SELECT COUNT(*) FROM candidates;
        SELECT COUNT(*) FROM memory_nodes;
Step R4: Resume Cron with original configuration
Step R5: Post-mortem analysis
```

---

## 12. Validation Gates

### Gate 1: Pre-Rebuild

```
[ ] Evidence count = 15,662 (verified)
[ ] Entity count = 4,609 (verified)
[ ] Backup completed (all derived tables)
[ ] Rollback procedure tested
[ ] Code changes reviewed and approved
[ ] Staging environment ready
```

### Gate 2: Post-Cleanup

```
[ ] candidates count = 0
[ ] proposals count = 0
[ ] memory_nodes level=1 count = 0
[ ] reconstructions count = 0
[ ] evidences count = 15,662 (preserved)
[ ] entities count = 4,609 (preserved)
```

### Gate 3: Post-Formation

```
[ ] candidates count > 0 (new candidates created)
[ ] All candidates have entity_id (100%)
[ ] All candidates have evidence_chain (non-empty)
[ ] reconstructions count matches candidates (1:1)
[ ] Topics extracted (non-zero)
```

### Gate 4: Post-L1 Evolution

```
[ ] memory_nodes level=1 count > 0
[ ] All L1 have entity_id (100%)
[ ] All L1 have evidence_links (non-empty)
[ ] proposals count matches L1 count
[ ] Lineage: Evidence → Candidate → L1 verified
```

### Gate 5: Post-L2 Evolution

```
[ ] memory_nodes level=2 count > 0 (at least some L2 created)
[ ] All L2 have entity_id
[ ] L2 content is aggregated summary (not single evidence)
[ ] Relationships created (supports/refutes/supersedes)
```

### Gate 6: Production

```
[ ] Cron running successfully (every 10 minutes)
[ ] No UniqueViolation errors
[ ] Memory growth stable
[ ] Query performance < 100ms for entity queries
[ ] Zero data loss (all Evidences preserved)
[ ] All Phase 20/21 tests pass
```

---

## 13. Files Expected to Change

### Phase 20 Frozen Code (Exception Required)

| File | Lines | Change | Exception ID |
|------|-------|--------|--------------|
| reflection_service.py | 248-250 | Extract entity_id from Candidate | EX-001 |
| app.py | Cron loop | Call Orchestrator instead of direct ReflectionService | EX-002 |

### Phase 21 Frozen Code (Exception Required)

| File | Lines | Change | Exception ID |
|------|-------|--------|--------------|
| evidence_pipeline_service.py | 162-168 | Remove/disable direct L2 creation | EX-003 |
| evolution_service.py | New method | Add evolve_entity_history() | EX-004 |

### New Phase 22 Implementation

| File | Change |
|------|--------|
| app.py | Add _run_full_pipeline() orchestrator function |
| app.py | Update _cron_scheduler_loop() to use orchestrator |
| evolution_service.py | Add evolve_entity_history() method |
| reflection_service.py | Fix entity_id propagation |
| evidence_pipeline_service.py | Comment out direct L2 creation |

---

## 14. Files Explicitly Forbidden to Change

| Category | Files | Reason |
|----------|-------|--------|
| Phase 20 Core | evidence_evolution_engine.py | Frozen boundary |
| Phase 20 Core | reflection_engine.py | Frozen boundary |
| Phase 21 Core | formation_service.py | Frozen boundary (except bug fixes) |
| Phase 21 Core | context/*.py | Frozen boundary |
| Schema | migrations/ | No new migrations without approval |
| Tests | tests/ | No test changes without approval |
| Config | .env, config/*.yaml | No config changes |

---

## 15. Remaining Architecture Conflicts

### CONFLICT-001: Direct L2 Creation in EvidencePipelineService

**Current State**: EvidencePipelineService creates L2 directly if `interpretation.user_owned`.

**Conflict**: This bypasses ReflectionService's proposal workflow and creates inconsistent L2 lineage.

**Resolution Required**: 
- [ ] Remove or comment out direct L2 creation in EvidencePipelineService
- [ ] Ensure ALL L2 creation goes through EvolutionService
- [ ] Update documentation to reflect new boundary

**Status**: ⚠️ OPEN — Requires code change

---

### CONFLICT-002: Entity Resolution for Old Evidences

**Current State**: 71.6% of evidences lack entity_id.

**Conflict**: FormationService resolves entity from interpretation, not from evidence. This may work for new evidences but old evidences have no entity context.

**Resolution Required**:
- [ ] Verify FormationService can resolve entity without evidence.entity_id
- [ ] Test with sample old evidences
- [ ] Document fallback behavior

**Status**: ⚠️ OPEN — Requires testing

---

### CONFLICT-003: L2 Threshold for Low-Density Entities

**Current State**: 93.4% of batches have only 1 fact per entity.

**Conflict**: L2 threshold (≥3 facts) will rarely be met, even with cross-batch aggregation.

**Resolution Required**:
- [ ] Determine optimal time window for aggregation (30 days? 90 days?)
- [ ] Consider lowering threshold for specific entity types
- [ ] Document expected L2 creation rate

**Status**: ⚠️ OPEN — Requires tuning

---

## 16. Implementation Ready Assessment

### Checklist

| Criteria | Status | Notes |
|----------|--------|-------|
| Call Graph无矛盾 | ✅ PASS | Orchestrator resolves FC-001 |
| Service Responsibility无矛盾 | ✅ PASS | Clear boundaries defined |
| Entity Lineage明确 | ✅ PASS | Formation-time resolution, propagation to L1 |
| Migration可执行 | ✅ PASS | Backfill script ready, constraints optional |
| Clean Rebuild可回滚 | ✅ PASS | Backup strategy defined |
| Cron入口明确 | ✅ PASS | Orchestrator as single entry point |
| L1/L2/L3边界明确 | ✅ PASS | Each service owns its level |
| 无P0/P1未决问题 | ⚠️ PARTIAL | 3 open conflicts (see above) |

### Final Verdict

```
IMPLEMENTATION READY: YES (with conditions)
```

**Conditions:**
1. User approves 4 frozen boundary exceptions (EX-001 to EX-004)
2. Open conflicts are reviewed and resolved before execution
3. Staging environment testing completed
4. Rollback procedure tested

**Next Step**: User approval to proceed with Implementation Phase.

---

**Implementation Design complete. Awaiting user approval to proceed.**
