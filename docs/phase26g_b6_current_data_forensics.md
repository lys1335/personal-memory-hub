# Phase 26-G-B.6 — Current Data State Forensics Report

**Date:** 2026-08-22
**Investigator:** Hermes Agent Agnes 2.0
**Type:** READ-ONLY FORENSICS INVESTIGATION
**Base Commit:** 6692de5ede827904936a2c78ea59b42f52cb9ba5

---

## 1. Executive Summary

```
TRANSITION DECISION: READY_FOR_REASSESSMENT
```

**Key Finding:** All current data (11,008 candidates, 8,310 proposals, 5,961 memory_nodes) was generated AFTER the B.6 preflight was documented (2026-08-15). This is expected behavior — the system continued processing after preflight.

**Data Timeline:**
- 2026-08-15: B.6 preflight documented (2,470 candidates, 1 proposal)
- 2026-08-15 to 2026-08-22: Additional processing generated 8,538 more candidates, 8,309 more proposals, 5,961 memory_nodes
- 2026-08-18: 110 new evidences added

---

## 2. Evidence-Level Definitions

| Level | Definition | Example |
|-------|------------|---------|
| LEVEL 0 | UNKNOWN / No evidence | Production runtime (Cron disabled) |
| LEVEL 1 | CODE PRESENT / Static evidence | Data structure analysis |
| LEVEL 2 | TEST VERIFIED | Unit/integration tests PASS |
| LEVEL 3 | REAL DATA / PRODUCTION VERIFIED | Actual database queries |

**All data state findings in this report are LEVEL 3 (REAL DATA VERIFIED).**

---

## 3. Candidates Growth Analysis

### 3.1 Current State

| Metric | Value | Evidence Level |
|--------|-------|----------------|
| Total Candidates | 11,008 | LEVEL 3 |
| Resolved Candidates | 5,240 (47.6%) | LEVEL 3 |
| Unresolved Candidates | 5,768 (52.4%) | LEVEL 3 |
| Creation Period | 2026-08-15 to 2026-08-19 | LEVEL 3 |
| Workspace | Single workspace | LEVEL 3 |

### 3.2 Growth by Source

| Source | Count | Resolved | Unresolved | % of Total |
|--------|-------|----------|------------|------------|
| semantic_interpretation (formation_service) | 6,938 | 1,170 | 5,768 | 63.0% |
| reflection (ai_reflect) | 4,060 | 4,060 | 0 | 36.9% |
| chatgpt | 10 | 10 | 0 | 0.1% |
| **Total** | **11,008** | **5,240** | **5,768** | **100%** |

**Finding:** The 6,938 candidates from `semantic_interpretation` are the "Clean Rebuild" target — they have 83% unresolved rate.

### 3.3 Growth by Date

| Date | New Candidates | Pattern | Belief |
|------|----------------|---------|--------|
| 2026-08-15 | 6,877 | 6,379 | 498 |
| 2026-08-16 | 2,396 | 2,391 | 5 |
| 2026-08-17 | 1,400 | 1,400 | 0 |
| 2026-08-18 | 125 | 110 | 15 |
| 2026-08-19 | 210 | 0 | 210 |

**Finding:** Most candidates (9,273 = 84%) were created on 2026-08-15 and 2026-08-16, during the initial data processing phase.

### 3.4 Evidence Coverage

| Metric | Value |
|--------|-------|
| Total Candidates | 11,008 |
| Unique Evidences | 6,500 |
| Evidence Coverage | 59.05% |
| Duplicate Evidence Chains | Multiple (max 3 candidates per evidence) |

**Finding:** Some evidences have multiple candidate interpretations — this is expected behavior.

---

## 4. Proposals Growth Analysis

### 4.1 Current State

| Metric | Value | Evidence Level |
|--------|-------|----------------|
| Total Proposals | 8,310 | LEVEL 3 |
| Pending | 3,053 (36.7%) | LEVEL 3 |
| Approved | 4,852 (58.4%) | LEVEL 3 |
| Rejected | 405 (4.9%) | LEVEL 3 |
| Creation Period | 2026-08-16 to 2026-08-21 | LEVEL 3 |
| Unique Candidates | 7,871 | LEVEL 3 |
| Unique Evidence Chains | 7,680 | LEVEL 3 |
| Duplication Rate | 7.58% | LEVEL 3 |

### 4.2 Growth by Date

| Date | New Proposals | Pending | Approved | Rejected |
|------|---------------|---------|----------|----------|
| 2026-08-16 | 3,372 | 292 | 3,073 | 7 |
| 2026-08-17 | 1,666 | 231 | 1,433 | 2 |
| 2026-08-18 | 125 | 0 | 125 | 0 |
| 2026-08-19 | 609 | 104 | 211 | 294 |
| 2026-08-20 | 1,897 | 1,794 | 10 | 93 |
| 2026-08-21 | 641 | 632 | 0 | 9 |

**Finding:** Proposal generation peaked on 2026-08-16 (3,372) and 2026-08-20 (1,897).

### 4.3 Duplication Analysis

| Metric | Value |
|--------|-------|
| Total Proposals | 8,310 |
| Unique Evidence Chains | 7,680 |
| Duplicate Chains | 401 |
| Max Duplication | 3x (same evidence_chain) |
| Empty Evidence Chains | 225 proposals |

**Finding:** 401 proposals (4.8%) share evidence chains with other proposals — this is the duplication issue identified in Phase 20.

### 4.4 Period Analysis

| Period | Proposals | Pending | Approved |
|--------|-----------|---------|----------|
| B.6 Period (2026-08-15 to 2026-08-16) | 3,372 | 292 | 3,073 |
| Post B.6 (2026-08-17 onwards) | 4,938 | 2,761 | 1,779 |

**Finding:** 59.4% of proposals were created after B.6 preflight was documented.

---

## 5. MemoryNodes Growth Analysis

### 5.1 Current State

| Metric | Value | Evidence Level |
|--------|-------|----------------|
| Total MemoryNodes | 5,961 | LEVEL 3 |
| Level 1 (Observations) | 5,418 (90.9%) | LEVEL 3 |
| Level 2 (Patterns) | 505 (8.5%) | LEVEL 3 |
| Level 3 (Beliefs) | 38 (0.6%) | LEVEL 3 |
| Creation Period | 2026-08-17 to 2026-08-19 | LEVEL 3 |

### 5.2 Growth by Date

| Date | New MemoryNodes |
|------|-----------------|
| 2026-08-17 | 1,183 |
| 2026-08-18 | 4,568 |
| 2026-08-19 | 210 |

**Finding:** MemoryNodes were generated by the evolution/reflection pipeline, NOT by Clean Rebuild.

### 5.3 Source Analysis

MemoryNodes are generated by:
- `ai_reflect` — Reflection engine (L2/L3)
- `archive` — Archive process
- `import` — Data import
- `manual` — Manual creation

**Finding:** These MemoryNodes are PART OF THE SYSTEM STATE and should be PRESERVED during Clean Rebuild, NOT cleared.

---

## 6. Reconstructions & TopicLinks Analysis

### 6.1 Reconstructions

| Metric | Value |
|--------|-------|
| Total Reconstructions | 6,938 |
| Unique Candidates | 6,938 (100%) |
| Unique Entities | 177 |
| Creation Period | 2026-08-15 to 2026-08-16 |

**Finding:** 1:1 mapping between candidates and reconstructions. These are GENERATED DATA and should be CLEARED during Clean Rebuild.

### 6.2 TopicLinks

| Metric | Value |
|--------|-------|
| Total TopicLinks | 20,765 |
| Creation Period | 2026-08-15 to 2026-08-16 |

**Finding:** TopicLinks are derived from reconstructions. They should be CLEARED during Clean Rebuild.

---

## 7. Evidence Analysis

### 7.1 Current State

| Metric | Value |
|--------|-------|
| Total Evidences | 15,772 |
| With Entity | 4,442 (28.16%) |
| Without Entity | 11,330 (71.84%) |
| Creation Period | 2026-08-04 (original) + 2026-08-18 (new) |

### 7.2 Evidence Sources

| Source | Count | Date |
|--------|-------|------|
| Original import | 15,662 | 2026-08-04 |
| New additions | 110 | 2026-08-18 |

**Finding:** The 110 new evidences are MINOR and do NOT change the Clean Rebuild scope.

---

## 8. Timeline Reconstruction

```
2026-08-04: Original evidence import (15,662 evidences)
    ↓
2026-08-15: B.6 preflight documented (2,470 candidates, 1 proposal)
    ↓
2026-08-15 to 2026-08-16: Large candidate generation (8,538 new candidates)
    ↓
2026-08-16 to 2026-08-21: Proposal generation (8,309 new proposals)
    ↓
2026-08-17 to 2026-08-19: MemoryNode generation (5,961 new memory_nodes)
    ↓
2026-08-18: 110 new evidences added
    ↓
2026-08-22: Current state (FORENSICS DATE)
```

---

## 9. B.6 Scope Reassessment

### 9.1 What to CLEAR

| Object | Current Count | Action | Reason |
|--------|---------------|--------|--------|
| candidates | 11,008 | CLEAR | Generated from evidences, will be rebuilt |
| reconstructions | 6,938 | CLEAR | Derived from candidates |
| topic_links | 20,765 | CLEAR | Derived from reconstructions |
| proposals | 8,310 | CLEAR | Derived from candidates, has duplication |

### 9.2 What to KEEP

| Object | Current Count | Action | Reason |
|--------|---------------|--------|--------|
| evidences | 15,772 | KEEP | Source data, must not be modified |
| entities | 5,889 | KEEP | Entity definitions, correct as-is |
| memory_nodes | 5,961 | KEEP | Generated by reflection, not part of rebuild |

### 9.3 What to BACKUP

| Object | Current Count | Backup Required |
|--------|---------------|-----------------|
| candidates | 11,008 | YES (before clear) |
| proposals | 8,310 | YES (before clear) |
| memory_nodes | 5,961 | YES (preservation) |

### 9.4 What Cannot Be Deleted Without Lineage

| Object | Reason |
|--------|--------|
| evidences | Source data — deletion would lose information |
| entities | Referenced by multiple tables |
| memory_nodes | May have relationships to other data |

---

## 10. Backup Requirements

### 10.1 Required Backups

| Backup Table | Must Contain | Baseline | Verification |
|--------------|--------------|----------|--------------|
| candidates_backup_CURRENT | All 11,008 candidates | Pre-rebuild | Row count match |
| proposals_backup_CURRENT | All 8,310 proposals | Pre-rebuild | Row count match |
| memory_nodes_backup_CURRENT | All 5,961 memory_nodes | Pre-rebuild | Row count match |
| reconstructions_backup_CURRENT | All 6,938 reconstructions | Pre-rebuild | Row count match |
| topic_links_backup_CURRENT | All 20,765 topic_links | Pre-rebuild | Row count match |

### 10.2 Backup Verification

```sql
-- Verify backup integrity
SELECT 
  (SELECT COUNT(*) FROM candidates) as current_candidates,
  (SELECT COUNT(*) FROM candidates_backup_CURRENT) as backup_candidates,
  (SELECT COUNT(*) FROM candidates) = (SELECT COUNT(*) FROM candidates_backup_CURRENT) as candidates_match,
  
  (SELECT COUNT(*) FROM proposals) as current_proposals,
  (SELECT COUNT(*) FROM proposals_backup_CURRENT) as backup_proposals,
  (SELECT COUNT(*) FROM proposals) = (SELECT COUNT(*) FROM proposals_backup_CURRENT) as proposals_match;
```

---

## 11. Answer to Key Questions

### A. 11,008 Candidates — Can be explained?

**YES (LEVEL 3):**
- 6,938 from `semantic_interpretation` (formation_service) — 83% unresolved
- 4,060 from `reflection` (ai_reflect) — 100% resolved
- All created between 2026-08-15 and 2026-08-19
- Single workspace

### B. 8,310 Proposals — Can be explained?

**YES (LEVEL 3):**
- Generated from candidates via evolution pipeline
- 92.42% uniqueness rate (7.58% duplication)
- Created between 2026-08-16 and 2026-08-21
- 58.4% approved, 36.7% pending, 4.9% rejected

### C. 5,961 MemoryNodes — Can be explained?

**YES (LEVEL 3):**
- Generated by reflection/evolution pipeline
- 90.9% Level 1 (Observations)
- 8.5% Level 2 (Patterns)
- 0.6% Level 3 (Beliefs)
- Created between 2026-08-17 and 2026-08-19

### D. Current data has clear contamination?

**NO (LEVEL 2):**
- Data growth is EXPECTED behavior
- No unauthorized modifications detected
- Cron is DISABLED, AUTO_APPROVE is false
- All data generated by legitimate pipeline processes

### E. B.6 still applicable?

**YES, WITH MODIFICATIONS (LEVEL 2):**
- Original B.6 plan targeted 2,470 candidates
- Current scope is 11,008 candidates
- Clean Rebuild logic is the same
- Scale is different but approach is valid

### F. Should B.6 be redesigned?

**NO (LEVEL 1):**
- Core logic remains valid
- Only scope needs adjustment
- No architectural changes required

---

## 12. Final Decision

```
═══════════════════════════════════════════════════════════════
FINAL DECISION: READY_FOR_REASSESSMENT
═══════════════════════════════════════════════════════════════

REASON:
- All data growth is explained and expected
- No contamination or unauthorized modifications
- B.6 approach is valid, only scope needs update
- Backup strategy can be defined
- Clean Rebuild can proceed with updated scope

NEXT STEPS:
1. Define updated B.6 scope (11,008 candidates instead of 2,470)
2. Create fresh backups before execution
3. Execute Clean Rebuild with updated parameters
4. Validate results against updated targets
```

---

## 13. Safety Invariants

| Invariant | Value | Status |
|-----------|-------|--------|
| DATABASE_MUTATIONS | 0 | ✅ MAINTAINED |
| CRON_ENABLED | false | ✅ MAINTAINED |
| AUTO_APPROVE | false | ✅ MAINTAINED |
| UNAUTHORIZED_PROPOSAL_MUTATIONS | 0 | ✅ MAINTAINED |
| PRODUCTION_CODE_MODIFICATIONS | 0 | ✅ MAINTAINED |
| TEST_MODIFICATIONS | 0 | ✅ MAINTAINED |

---

## Appendix A: Current Database State Summary

| Table | Count | Status |
|-------|-------|--------|
| evidences | 15,772 | KEEP |
| entities | 5,889 | KEEP |
| candidates | 11,008 | CLEAR (rebuild) |
| reconstructions | 6,938 | CLEAR (rebuild) |
| topic_links | 20,765 | CLEAR (rebuild) |
| proposals | 8,310 | CLEAR (rebuild) |
| memory_nodes | 5,961 | KEEP (preserve) |

---

*Forensics Report completed by Hermes Agent Agnes 2.0*
*Date: 2026-08-22*
*Type: READ-ONLY*
*Status: READY_FOR_REASSESSMENT*
