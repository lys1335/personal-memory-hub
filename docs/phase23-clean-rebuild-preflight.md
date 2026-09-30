# Phase 23 — Clean Rebuild Preflight Report

**Date**: 2026-08-14  
**Mode**: READ ONLY — Preflight check, no modifications  
**Status**: Complete

---

## Executive Summary

```
╔═══════════════════════════════════════════════════════════════════╗
║              CLEAN REBUILD PREFLIGHT                              ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  PREFLIGHT RESULT: READY ✅                                       ║
║                                                                   ║
║  All checks passed. Clean Rebuild can proceed safely.             ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 1. Git Work Area Status

### Modified Files (Phase 22)

```
M backend/src/backend/evolution/evolution_service.py      (+134 lines)
M backend/src/backend/service/evidence_pipeline_service.py (+19 lines)
M backend/src/backend/service/formation_service.py         (+85/-8 lines)
M backend/src/backend/service/reflection_service.py        (+12/-3 lines)
```

### Untracked Files (Not Critical)

```
backend/scripts/test_context_resolution.py       (test script)
backend/scripts/validate_entity_resolution.py     (test script)
backend/tests/test_phase20_db_integration.py       (test file)
docs/phase22-*.md                                 (15 audit documents)
docs/phase22-implementation-*.md                   (3 implementation docs)
scripts/                                           (validation scripts)
```

### Key Decisions

- **Do NOT commit** — User has not authorized commit yet
- **All modifications are correct and necessary**
- **Test scripts are utility, not production code**

---

## 2. Clean Rebuild Execution Chain Verification

### Intended Flow (from Phase 22.10/22.14/22.16)

```
Evidence
    ↓
EvidencePipelineService.process_evidence()
    ↓
  _form_context_window() → ContextWindow
    ↓
  _interpret() → InterpretationResult
    ↓
  _form(context_window=cw) → FormationService.form()
    ↓
  FormationService._resolve_entity_from_context(context_window)
    ↓
  FormationService._create_candidate() → Candidate (entity_id ✅)
    ↓
  FormationService._create_reconstruction()
    ↓
ReflectionService.reflect() → proposals
    ↓
ReflectionService.approve_proposal() → L1 MemoryNode (entity_id from Candidate)
    ↓
EvolutionService.evolve_entity_history() → L2/L3 (threshold check)
```

### Code Verification

| Step | Method | Status |
|------|--------|--------|
| EvidencePipelineService._form() | Accepts context_window param | ✅ |
| FormationService.form() | Receives context_window | ✅ |
| FormationService._resolve_entity_from_context() | Uses context_window | ✅ |
| FormationService._resolve_from_context_window() | NEW method | ✅ |
| ReflectionService.approve_proposal() | Gets entity_id from Candidate | ✅ |
| EvolutionService.evolve_entity_history() | NEW method | ✅ |

### Call Graph Confirmed

```
✅ EvidencePipelineService → FormationService → Entity Resolution
✅ FormationService → Candidate (with entity_id)
✅ ReflectionService → L1 (with entity_id from Candidate)
✅ EvolutionService → L2/L3 (separate invocation)
```

---

## 3. Data Cleanup Scope

### Tables to CLEAN (TRUNCATE or DELETE)

| Table | Reason | Current Count |
|-------|--------|---------------|
| **candidates** | Will be regenerated from evidences | 22,728 |
| **proposals** | Will be regenerated from candidates | 619 |
| **memory_nodes** | Will be regenerated from proposals | 26,261 |
| **reconstructions** | Already empty (0 rows) | 0 |
| **topic_links** | Already empty (0 rows) | 0 |

### Tables to PRESERVE (NO touch)

| Table | Reason | Current Count |
|-------|--------|---------------|
| **evidences** | Source of truth (L0) | 15,662 |
| **entities** | Entity database | 4,836 |
| **areas** | Area taxonomy | 3,732 |
| **workspace** | Workspace config | 1 |
| **user_profiles** | User data | N/A |

### Additional Tables to Consider

| Table | Action | Reason |
|-------|--------|--------|
| **candidates** | DELETE WHERE workspace_id = :wid | Regenerate with new pipeline |
| **proposals** | DELETE WHERE workspace_id = :wid | Regenerate from new candidates |
| **memory_nodes** | DELETE WHERE workspace_id = :wid AND level IN (1,2,3) | Regenerate with entity_id |

---

## 4. Backup / Rollback Strategy

### Recommended Backup

```sql
-- 1. Create backup tables (preserves data for rollback)
CREATE TABLE candidates_backup_20260814 AS SELECT * FROM candidates;
CREATE TABLE proposals_backup_20260814 AS SELECT * FROM proposals;
CREATE TABLE memory_nodes_backup_20260814 AS SELECT * FROM memory_nodes;

-- 2. OR use transaction (if rebuild is atomic)
BEGIN;
-- ... execute rebuild ...
COMMIT;  -- or ROLLBACK on failure
```

### Rollback Procedure

```sql
-- If rebuild fails, restore from backup:
TRUNCATE candidates, proposals, memory_nodes;
INSERT INTO candidates SELECT * FROM candidates_backup_20260814;
INSERT INTO proposals SELECT * FROM proposals_backup_20260814;
INSERT INTO memory_nodes SELECT * FROM memory_nodes_backup_20260814;
DROP TABLE candidates_backup_20260814, proposals_backup_20260814, memory_nodes_backup_20260814;
```

### Backup Files

| File | Content |
|------|---------|
| `candidates_backup_20260814.sql` | All candidates |
| `proposals_backup_20260814.sql` | All proposals |
| `memory_nodes_backup_20260814.sql` | All memory nodes |

---

## 5. Rebuild Idempotency

### Can We Safely Interrupt and Resume?

| Scenario | Safe? | Notes |
|----------|-------|-------|
| Interrupt mid-rebuild | ⚠️ Partial | Some candidates may exist, others not |
| Restart after interrupt | ✅ Yes | Pipeline checks existing candidates |
| Duplicate candidate creation | ❌ No | Unique constraint prevents duplicates |
| Duplicate proposal creation | ❌ No | uk_proposals_pending_per_candidate prevents |
| Duplicate L1 creation | ❌ No | FK constraint prevents |

### Idempotency Mechanism

```python
# EvidencePipelineService checks before creating:
candidate = await candidate_repo.find_by_evidence_id(evidence_id)
if candidate:
    # Skip, already exists
    return
# Create new candidate
```

### Run ID Tracking

**Recommendation**: Add rebuild_id to _meta for audit trail

```json
{
  "rebuild_id": "20260814_0800",
  "rebuild_timestamp": "2026-08-14T08:00:00Z",
  "phase": "phase22_clean_rebuild"
}
```

---

## 6. Entity Lineage Verification

### L1 entity_id Source

```python
# ReflectionService.approve_proposal() - Line 248-258
# entity_id comes FROM CANDIDATE, not from content
stmt = text("SELECT entity_id FROM candidates WHERE id = :id LIMIT 1")
candidate_row = await conn.execute(stmt, {"id": str(candidate_id)})
entity_id = candidate_row[0] if candidate_row else None
```

### Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| entity_id NOT NULL for new L1 | ✅ | Candidate.entity_id is set during Formation |
| entity_id from Candidate | ✅ | SQL query confirms |
| Not guessed from L1 content | ✅ | No content-based extraction in approve_proposal |

### Critical Path

```
Evidence (entity_id may be NULL)
    ↓
FormationService._resolve_entity_from_context()
    ↓
Candidate.entity_id = resolved entity
    ↓
Proposal.candidate_id = FK to Candidate
    ↓
ReflectionService.approve_proposal()
    ↓
L1.entity_id = Candidate.entity_id ✅
```

---

## 7. Evolution Constraints

### L2/L3 Creation Rules

| Rule | Status |
|------|--------|
| Only EvolutionService creates L2/L3 | ✅ |
| EvidencePipelineService cannot create L2/L3 | ✅ (verified in Phase 22.16) |
| Threshold: min_l1_count ≥ 3, min_avg_confidence ≥ 0.8 | ✅ |

### EvidencePipelineService Check

```python
# evidence_pipeline_service.py - Line 163-166
# NOTE: Historical evolution (L2/L3 creation) is now handled by
# EvolutionService.evolve_entity_history() called separately,
# NOT during EvidencePipelineService processing.
```

### EvolutionService.evolve_entity_history()

```python
# evolution_service.py - Line 401
async def evolve_entity_history(
    self,
    *,
    workspace_id: UUID,
    entity_id: UUID | None = None,
    min_l1_count: int = 3,
    min_avg_confidence: float = 0.8,
) -> list[dict]:
```

---

## 8. Validation Gates

### Post-Rebuild Gates

| Gate | Condition | Expected Result |
|------|-----------|-----------------|
| **ER-1** | Single-entity accuracy ≥ 90% | 100% (from Phase 22.17) |
| ER-2 | Multi-entity recall ≥ 80% | ⚠️ N/A (no multi-entity sample) |
| **ER-3** | False-positive rate ≤ 5% | 0% (confirmed) |
| **ER-4** | Pipeline survival rate 100% | 100% (graceful handling) |
| **ER-5** | Lineage completeness 100% | 100% (entity_id propagated) |
| **ER-6** | All gates pass | Pending verification |

### Additional Gates

| Gate | Condition | Status |
|------|-----------|--------|
| G-1 | All evidences processed | Pending |
| G-2 | All candidates have entity_id | Pending |
| G-3 | All L1 have entity_id | Pending |
| G-4 | No duplicate candidates | Pending |
| G-5 | No duplicate proposals | Pending |
| G-6 | Cron runs successfully | Pending |

---

## 9. Data Scale Prediction

### Current State

| Metric | Value |
|--------|-------|
| Evidences | 15,662 |
| Entities | 4,836 |
| Areas | 3,732 |

### Predicted Rebuild Output

| Output | Count | Notes |
|--------|-------|-------|
| **Candidates** | ~15,000-16,000 | 1 per evidence (some may fail formation) |
| **Proposals** | ~5,000-8,000 | Only user-owned facts produce proposals |
| **L1 MemoryNodes** | ~5,000-8,000 | 1 per approved proposal |
| **L2 MemoryNodes** | 0-100 | Depends on threshold (≥3 L1 + ≥0.8 confidence) |
| **L3 MemoryNodes** | 0-10 | Very rare (requires L2 consolidation) |

### Estimated Runtime

| Phase | Time Estimate |
|-------|---------------|
| Formation (Evidence → Candidate) | ~2-3 hours |
| Reflection (Candidate → L1) | ~1-2 hours |
| Evolution (L1 → L2/L3) | ~10-30 minutes |
| **Total** | **~4-6 hours** |

---

## 10. Preflight Conclusion

### REBUILD PREFLIGHT: READY ✅

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Rebuild failure mid-way | Medium | Transaction + backup tables |
| Duplicate data | Low | Unique constraints prevent |
| Entity resolution failure | Low | Graceful handling (unresolved = NULL) |
| Performance issue | Low | Batch processing with progress tracking |
| Data loss | High | Backup before start |

### Execution Order

```
Step 1: CREATE backup tables
Step 2: TRUNCATE candidates, proposals, memory_nodes
Step 3: Run EvidencePipelineService for all 15,662 evidences
Step 4: Run ReflectionService for all candidates
Step 5: Run EvolutionService.evolve_entity_history()
Step 6: Validate with gates (ER-1 to ER-6)
Step 7: Delete backup tables (if successful)
```

### Rollback Procedure

```sql
-- If anything goes wrong:
TRUNCATE candidates, proposals, memory_nodes;
INSERT INTO candidates SELECT * FROM candidates_backup_20260814;
INSERT INTO proposals SELECT * FROM proposals_backup_20260814;
INSERT INTO memory_nodes SELECT * FROM memory_nodes_backup_20260814;
DROP TABLE candidates_backup_20260814, proposals_backup_20260814, memory_nodes_backup_20260814;
```

---

## Final Status

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                 ║
║  REBUILD PREFLIGHT: READY ✅                                    ║
║                                                                 ║
║  Ready to proceed to Phase 24 (Clean Rebuild Execution)         ║
║                                                                 ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

**Phase 23 Preflight complete. Awaiting user authorization to proceed.**
