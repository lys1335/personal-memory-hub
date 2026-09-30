# Phase 24-E Clean Rebuild Report — Complete

## Summary

Phase 24-E Full Clean Rebuild has been **successfully completed**.

**Completion Time**: 2026-08-15 00:15:03 UTC
**Total Runtime**: 10 hours 2 minutes (36,115 seconds)

---

## Final Data State

| Table | Count |
|-------|-------|
| **evidences** | 15,662 (preserved) |
| **entities** | 4,855+ (preserved) |
| **areas** | 3,732+ (preserved) |
| **candidates** | 2,469 |
| **reconstructions** | 2,469 |
| **topic_links** | 7,256 |
| **topics** | 456 |
| **proposals** | 0 |
| **memory_nodes** | 0 |

---

## Pipeline Statistics (Resume Portion)

| Metric | Value |
|--------|-------|
| **Processed** | 15,446/15,662 evidences |
| **Formation Success** | 2,402 (15.55% rate) |
| **Candidates Created** | 2,402 |
| **Topic Links Created** | 7,256 |
| **Transactions Failures** | 0 |
| **Errors** | 0 |

---

## Key Fixes Applied

### 1. TopicRepository.increment_count() — Added
- Method: `increment_count(topic_id: UUID, count_field: str)`
- Purpose: Increment `reconstruction_count` on topics table
- Location: `backend/src/backend/repository/topic_repository.py`

### 2. TopicService._increment_*_count() — Fixed
- Changed from positional args to keyword args
- Now calls `repo.increment_count(topic_id=topic_id, count_field="reconstruction_count")`
- Location: `backend/src/backend/service/topic_service.py`

### 3. ContextWindow Fix (from earlier phase)
- Added `classify_role_from_evidence_type()` function
- Changed formulator to read `evidence.evidence_type` instead of broken `_meta["role"]`
- Result: AMBIGUOUS rate dropped from ~85% to ~12%

### 4. TopicLink Schema Fix (from earlier phase)
- Removed non-existent `id` column from ORM
- Fixed `source_type` length: String(20) → String(50)
- Fixed workspace_id comparison: UUID vs string

---

## Validation Results

### Lineage Integrity
- ✅ All 2,469 candidates have corresponding reconstructions
- ✅ All reconstructions have proper candidate_id foreign key
- ✅ 7,256 topic_links created with proper composite PK (topic_id, source_type, source_id)

### Topic Count Consistency
- ✅ `increment_count()` method implemented and working
- ✅ Topic counts updated correctly during pipeline execution

### Data Quality
- ✅ 0 orphan records
- ✅ 0 transaction failures
- ✅ Evidence-type distribution preserved: user=7,782, assistant=7,880

---

## Backup Tables (Preserved)

| Backup Table | Record Count |
|--------------|--------------|
| candidates_backup_20260814 | 22,788 |
| proposals_backup_20260814 | 659 |
| memory_nodes_backup_20260814 | 26,296 |

---

## Next Steps

Phase 24-F: TopicLinks Schema Contract Audit (already completed in Phase 24-D)
Phase 25: L1 MemoryNode Formation (ReflectionService)
Phase 26: L2/L3 Evolution (EvolutionService)

---

## Files Modified

1. `backend/src/backend/repository/topic_repository.py`
   - Added `increment_count()` method (~25 lines)

2. `backend/src/backend/service/topic_service.py`
   - Fixed `increment_count()` calls to use keyword args (~3 lines)

3. `scripts/fix_topic_counts.py`
   - Temporary script for backfilling existing topic counts

4. `scripts/phase24_e_resume.py`
   - Resume pipeline script (preserved for future runs)

---

**Status**: ✅ COMPLETE — Phase 24-E Clean Rebuild finished successfully with 0 errors.
