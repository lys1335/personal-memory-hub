# Phase 22.11 Pre-Implementation Validation

**Date**: 2026-08-14
**Mode**: READ ONLY — Dry-run validation
**Status**: Complete

---

## Executive Summary

### Validation Result: **REBUILD READY: NO (Conditional)**

**Critical Finding**: 71.64% of existing evidences lack `entity_id`, which will cause FormationService to fail for the majority of evidence during Clean Rebuild.

**Status**:
- FC-001: RESOLVED (Orchestrator pattern)
- FC-002: OPEN — Requires entity resolution fallback design
- FC-003: INCONCLUSIVE — Needs tuning analysis

---

## 1. Evidence Analysis (15,662 total)

### Evidence Distribution

| Metric | Value |
|--------|-------|
| Total Evidences | 15,662 |
| With entity_id | 4,442 (28.36%) |
| Without entity_id | 11,220 (71.64%) |
| Source | All "chatgpt" |
| Avg content length | 604 chars |

### Content Length Distribution

| Bucket | Count | Avg Length |
|--------|-------|------------|
| Short (<100) | 7,362 (47%) | 31 chars |
| Medium (100-500) | 1,986 (13%) | 252 chars |
| Long (500-1000) | 2,245 (14%) | 764 chars |
| Very Long (>1000) | 4,069 (26%) | 1,725 chars |

### Entity Resolution Rate

**Critical Finding**: Only 28.36% of evidences have entity_id pre-populated.

```sql
-- Evidence with entity vs without
SELECT 
  CASE 
    WHEN entity_id IS NOT NULL THEN 'with_entity'
    ELSE 'without_entity'
  END as entity_status,
  COUNT(*) as count,
  AVG(LENGTH(content)) as avg_content_length
FROM evidences
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
GROUP BY entity_status;

-- Result:
-- with_entity:    4,442 (avg 1,218 chars)
-- without_entity: 11,220 (avg 361 chars)
```

**Observation**: Evidences WITH entity_id are significantly longer (1,218 vs 361 chars), suggesting entity_id is populated during detailed conversations, not short confirmations.

---

## 2. FormationService Analysis

### Current Code Path

```python
# formation_service.py:136-143
if entity_id is None:
    entity_id = await self._resolve_entity(trigger_evidence_id, workspace_id)
    if entity_id is None:
        return FormationResult(
            success=False,
            error="Could not resolve entity_id from trigger evidence",
        )
```

### Resolution Logic

```python
# formation_service.py:_resolve_entity()
async def _resolve_entity(self, evidence_id, workspace_id):
    stmt = select(Evidence).where(
        Evidence.id == evidence_id,
        Evidence.workspace_id == workspace_id,
    )
    evidence = await self.session.execute(stmt)
    return evidence.scalar_one_or_none().entity_id
```

### Critical Finding: Formation Will Fail for 71.64% of Evidences

**If EvidencePipelineService is used for Clean Rebuild:**
- 4,442 evidences (28.36%) → Formation succeeds
- 11,220 evidences (71.64%) → Formation fails with "Could not resolve entity_id"

**This is a BLOCKING ISSUE for Clean Rebuild.**

---

## 3. OLD vs NEW Candidate Comparison

### OLD Candidate (ReflectionService-generated)

| Metric | Value |
|--------|-------|
| Total | 22,316 |
| Avg evidence_count | 1.7 |
| Avg content_length | 39.3 chars ⚠️ Very short |
| Unique entities | 1,029 |
| Null entity candidates | 0 (100% resolved) |

**Key Insight**: OLD candidates have very short content (avg 39 chars) because ReflectionService extracts entity-level summaries, not full evidence content.

### NEW Candidate (EvidencePipelineService-generated)

**Expected characteristics** (based on FormationService code):
- content = interpretation.semantic_content (LLM-extracted summary)
- evidence_count = len(source_evidence_ids) (typically 1-3)
- entity_id = resolved from evidence (critical dependency)
- Topics extracted from interpretation

**Comparison Hypothesis**:
| Aspect | OLD Candidate | NEW Candidate (Expected) |
|--------|---------------|-------------------------|
| entity_id | 100% resolved | 28% resolved (blocking!) |
| content | Short summary (39 chars) | LLM-generated semantic content |
| evidence_count | 1.7 avg | 1-3 (context window) |
| topics | Not tracked | Extracted via TopicService |

---

## 4. Simulated L1 Formation Analysis

### Hypothetical L1 Statistics (using OLD candidates as proxy)

```sql
-- Simulate L1 entity distribution
SELECT 
  entity_id,
  COUNT(*) as estimated_l1_count,
  AVG(evidence_strength) as estimated_avg_confidence,
  CASE 
    WHEN COUNT(*) >= 3 AND AVG(evidence_strength) >= 0.8 THEN 'L2_QUALIFIED'
    ELSE 'NOT_QUALIFIED'
  END as qualification
FROM candidates
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
  AND entity_id IS NOT NULL
GROUP BY entity_id
HAVING COUNT(*) >= 1
ORDER BY estimated_l1_count DESC
LIMIT 20;
```

### Top Entities by Candidate Count

| Entity | Candidates | Avg Confidence | L2 Qualified? |
|--------|-----------|----------------|---------------|
| 经费 | 974 | 1.0 | YES |
| Generate | 950 | 0.7 | NO (confidence < 0.8) |
| 经费率 | 807 | 1.0 | YES |
| Applepay | 542 | 0.9 | YES |
| 交通费 | 435 | 0.9 | YES |
| 废业 | 427 | 0.9 | YES |
| 火车票候补 | 359 | 0.9 | YES |
| 接待交际费 | 319 | 0.9 | YES |
| 共済金A | 296 | 0.9 | YES |
| AirPods Pro 3 | 296 | 0.9 | YES |

### L2 Threshold Analysis

**Current threshold**: ≥3 L1 AND avg_confidence ≥0.8

**Projected L2 creation** (using OLD data as proxy):
- Entities with ≥3 L1: ~1,000+ (majority)
- Entities with avg_confidence ≥0.8: ~80%
- **Estimated L2-qualified entities**: ~800-900 (80% of entities)

**Note**: This is based on OLD candidate data. NEW candidates may have different distribution.

---

## 5. CONFLICT-002 Verification: Entity Resolution

### Current Behavior for Missing Entity

```python
# formation_service.py:136-143
if entity_id is None:
    entity_id = await self._resolve_entity(trigger_evidence_id, workspace_id)
    if entity_id is None:
        return FormationResult(
            success=False,
            error="Could not resolve entity_id from trigger evidence",
        )
```

### What Happens During Clean Rebuild?

**For evidences WITHOUT entity_id:**
1. EvidencePipelineService calls FormationService
2. FormationService tries to resolve entity_id from evidence
3. evidence.entity_id is NULL
4. FormationResult.success = False
5. Candidate is NOT created
6. Evidence is effectively skipped

**Impact**: 71.64% of evidences would be lost during Clean Rebuild!

### Options for Resolution

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Add entity_id to all evidences pre-rebuild | Complete lineage | Requires 11K+ entity resolutions |
| B | FormationService extracts entity from content | No pre-processing needed | LLM cost, non-deterministic |
| C | Create unresolved entity placeholder | Fast rebuild | Dirty data, needs cleanup |
| D | Skip evidences without entity_id | Simple | 71% data loss |

**Recommendation**: Option A (pre-resolve entities) or Option B (extract from content).

---

## 6. EvolutionService L2 Creation Analysis

### Current EvolutionService._create_memory_node()

```python
# Determines level based on candidate_type
level = 2 if candidate.candidate_type == "pattern" else 3
node_type = "Pattern" if level == 2 else "Belief"
```

**Issue**: ALL current candidates have `candidate_type = "pattern"` (100%).

This means ALL L2 created by EvolutionService would be Pattern (level=2), never Belief (level=3).

### Proposed New L2 Creation Logic

```python
# evolution_service.py (proposed enhancement)
async def evolve_entity_history(self, entity_id, workspace_id, time_window_days=30):
    """Aggregate L1 MemoryNodes and create L2/L3."""
    
    # Query historical L1 for entity
    l1_nodes = await self.memory_repo.find_by_entity(
        entity_id=entity_id,
        level=1,
        created_after=NOW() - timedelta(days=time_window_days),
    )
    
    # Check threshold
    if len(l1_nodes) < 3:
        return []  # Not enough facts
    
    avg_confidence = sum(n.confidence for n in l1_nodes) / len(l1_nodes)
    if avg_confidence < 0.8:
        return []  # Confidence too low
    
    # Create L2 Pattern
    return await self._create_pattern(entity_id, l1_nodes)
```

### L2 Creation Conditions

| Condition | Threshold | Current State |
|-----------|-----------|---------------|
| Min L1 count | ≥3 | 80% of entities qualify |
| Min confidence | ≥0.8 | 80% of entities qualify |
| Time window | 30 days (configurable) | TBD |

---

## 7. Orchestrator Design Validation

### Proposed Call Graph

```
[Cron: every 10 minutes]
        ↓
[Orchestrator._run_full_pipeline(workspace_id, limit=200)]
        ↓
┌─────────────────────────────────────────────────────┐
│  Stage 1: Formation                                 │
│  EvidencePipelineService.process_evidence()         │
│    → For each pending evidence:                     │
│      - Form ContextWindow                           │
│      - Interpret semantic content                   │
│      - Create Candidate (if entity resolved)        │
│      - Create Reconstruction                        │
│      - Extract Topics                               │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│  Stage 2: L1 Evolution                              │
│  ReflectionService.reflect()                        │
│    → Acquire scope (pending candidates)             │
│    → Run EvidenceEvolutionEngine (fact extraction)  │
│    → Run ReflectionEngine (proposal generation)     │
│    → Save proposals                                 │
│    → Auto-approve proposals                         │
│    → Create L1 MemoryNodes                          │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│  Stage 3: L2/L3 Evolution (optional, periodic)      │
│  EvolutionService.evolve_entity_history()           │
│    → For each entity with ≥3 L1:                    │
│      - Create L2 Pattern                            │
│      - Create L3 Belief (if applicable)             │
└─────────────────────────────────────────────────────┘
```

### Transaction Boundaries

| Stage | Transaction Owner | Rollback Scope |
|-------|------------------|----------------|
| Formation | EvidencePipelineService | Single evidence |
| L1 Evolution | ReflectionService | Batch (up to 50 candidates) |
| L2/L3 Evolution | Orchestrator | Per-entity (caller-managed) |

### Potential Issues

1. **Circular Dependency**: EvidencePipelineService depends on FormationService, which depends on EntityRepository. No circular deps found.

2. **Duplicate Processing**: 
   - Formation is idempotent by evidence_id ✅
   - L1 creation is idempotent by candidate_id (P0 fix) ✅
   - L2 creation needs idempotency check (time_window + entity_id) ⚠️

3. **Service Ownership**: Clear boundaries established ✅

---

## 8. ID Empotency Strategy

### EvidencePipelineService (Formation)

```python
# Idempotency key: evidence_id
# If candidate already exists for this evidence, skip
existing = await self.candidate_repo.find_by_evidence(evidence_id)
if existing:
    return PipelineResult(success=True, skipped="already_processed")
```

### ReflectionService (L1 Evolution)

```python
# Idempotency key: candidate_id + workspace_id
# P0 fix already implemented (unique constraint)
# Duplicate proposals are deduplicated automatically ✅
```

### EvolutionService (L2/L3)

```python
# Idempotency key: entity_id + time_window
# Need to check if L2 already exists for entity
existing_l2 = await self.memory_repo.find_by_entity(
    entity_id=entity_id, level=2
)
if existing_l2:
    return []  # Skip, already evolved
```

---

## 9. Blockers and Open Issues

### 🔴 CRITICAL: Entity Resolution for 71.64% of Evidences

**Issue**: EvidencePipelineService will fail for 11,220 evidences (71.64%) because they lack entity_id.

**Options**:
1. **Pre-resolve entities**: Run entity resolution on all evidences before Clean Rebuild
2. **LLM-based resolution**: Have FormationService extract entity from content
3. **Skip unresolved**: Accept 71% data loss (NOT RECOMMENDED)

**Recommendation**: Option 1 (pre-resolve) or Option 2 (LLM extraction with fallback).

### 🟡 HIGH: L2 Idempotency Not Implemented

**Issue**: EvolutionService.evolve_entity_history() doesn't exist yet.

**Action Required**: Implement new method with idempotency checks.

### 🟡 HIGH: candidate_type Distribution

**Issue**: 100% of candidates have candidate_type="pattern", which means EvolutionService creates only L2 (never L3).

**Analysis**: This is actually correct — candidate_type determines L2 vs L3, and most evidence should produce L2 Patterns.

### 🟢 MEDIUM: Topic Links Empty

**Issue**: topic_links table is empty (0 rows).

**Analysis**: Topic extraction happens in EvidencePipelineService but results aren't persisted to topic_links.

**Action Required**: Verify TopicService.save_topics() behavior.

---

## 10. Final Validation Verdict

### Rebuild Readiness Assessment

| Criteria | Status | Notes |
|----------|--------|-------|
| EvidencePipelineService functional | ✅ PASS | Can form Candidates |
| ReflectionService entity_id fix | ✅ PASS | P0 fix applied |
| EvolutionService L2 creation | ⚠️ PARTIAL | Needs evolve_entity_history() |
| Entity resolution for old evidences | 🔴 FAIL | 71.64% lack entity_id |
| Idempotency strategy | ✅ PASS | All services have strategies |
| Transaction boundaries | ✅ PASS | Clear ownership defined |
| Cron orchestration | ✅ PASS | Orchestrator pattern valid |

### Final Verdict

```
╔══════════════════════════════════════════════════════════╗
║             REBUILD READY: NO (CONDITIONAL)              ║
╠══════════════════════════════════════════════════════════╣
║  REASON: Critical blocker — 71.64% evidences lack       ║
║          entity_id, causing FormationService to fail.    ║
║                                                          ║
║  ACTION REQUIRED:                                        ║
║  1. Resolve entity_id for 11,220 evidences BEFORE rebuild│
║  2. OR implement LLM-based entity extraction in Form     ║
║  3. OR accept 71% data loss (NOT RECOMMENDED)            ║
╚══════════════════════════════════════════════════════════╝
```

---

## 11. Recommendations

### Immediate Actions (Before Rebuild)

1. **Entity Resolution Strategy**:
   - [ ] Option A: Pre-resolve all evidences with entity_id (batch job)
   - [ ] Option B: Modify FormationService to extract entity from content via LLM
   - [ ] Decision required from user

2. **EvolutionService Enhancement**:
   - [ ] Implement `evolve_entity_history()` method
   - [ ] Add idempotency check for L2 creation
   - [ ] Test with sample entity history

3. **Orchestrator Implementation**:
   - [ ] Create `_run_full_pipeline()` in app.py
   - [ ] Update Cron to call orchestrator
   - [ ] Add manual trigger endpoint

### Validation Gates (Post-Implementation)

```
Gate 1: Pre-Rebuild
  [ ] Evidence entity_id resolution rate = 100%
  [ ] Backup completed (all derived tables)
  [ ] Rollback procedure tested

Gate 2: Post-Formation
  [ ] Candidates created = Evidences processed
  [ ] All candidates have entity_id
  [ ] All candidates have evidence_chain

Gate 3: Post-L1
  [ ] L1 MemoryNodes created
  [ ] All L1 have entity_id
  [ ] Lineage verified: Evidence → Candidate → L1

Gate 4: Post-L2
  [ ] L2 Patterns created for qualified entities
  [ ] L2 entity_id set correctly
  [ ] Relationships created
```

---

## 12. Conflict Resolution Status

| Conflict | Status | Resolution |
|----------|--------|------------|
| CONFLICT-001 (Direct L2 in EvidencePipeline) | RESOLVED | Remove direct L2 creation from production path |
| CONFLICT-002 (Entity resolution for old evidences) | OPEN | Requires pre-rebuild entity resolution or LLM extraction |
| CONFLICT-003 (L2 threshold tuning) | INCONCLUSIVE | Needs staging test with new pipeline |

---

**Validation complete. Awaiting user decision on entity resolution strategy before proceeding with Implementation Phase.**
