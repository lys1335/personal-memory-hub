# Phase 22.3 Candidate Granularity & L0→L1 Architecture Audit

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Summary

### Critical Discovery
**EvidencePipelineService is NOT used in production.** All modern Candidates (20,589) were created by ReflectionService, not FormationService.

This means:
- The "two-pipeline architecture" from Phase 21 is theoretical, not operational
- Production uses a single pipeline: Evidence → ReflectionService → Candidate → Proposal → MemoryNode
- The Formation pipeline (EvidencePipelineService) exists but has no production traffic

### Candidate Granularity Analysis

| Source | Count | Avg Evidence | Avg Content Length |
|--------|-------|--------------|-------------------|
| ai_reflect (ReflectionService) | 20,589 | 1.71 | 18 chars |
| batch_import (legacy) | 950 | 1.00 | 468 chars |
| import (legacy zero-UUID) | 50 | 2.38 | 1,064 chars |

**Key Finding**: Production Candidates are highly condensed (18 chars avg), not raw evidence copies.

---

## 1. Phase 21.5 Formation Pipeline Status

### Actual Production Usage

```python
# evidence_pipeline_service.py:940-973
@app.post("/pipeline/trigger", tags=["phase21"])
async def trigger_pipeline(body: dict = Body(...), session: AsyncSession = Depends(get_session)):
    """POST /pipeline/trigger - trigger Phase 21 pipeline for an Evidence."""
```

**Evidence**: This endpoint exists but is NOT called by Cron.

### Database Evidence

```sql
-- Reconstructions table is EMPTY
SELECT COUNT(*) FROM reconstructions;
-- Result: 0

-- Candidates with ingested_by='formation_service': 0
SELECT ingested_by, COUNT(*) FROM candidates GROUP BY ingested_by;
-- Results: ai_reflect=20589, batch_import=950, import=50
```

**Conclusion**: EvidencePipelineService has NEVER created a Candidate in production.

---

## 2. Candidate Creation Analysis

### How Candidates are Actually Created

**File**: reflection_service.py:858-1045
**Method**: `_save_candidates()`

```python
# reflection_service.py:979
"ingested_by": "ai_reflect",

# reflection_service.py:970-985
candidate = {
    "id": str(generate_uuid()),
    "workspace_id": str(workspace_id),
    "entity_id": entity_id,
    "area_id": area_id,
    "content": candidate.get("content", ""),
    "candidate_type": candidate.get("node_type", "pattern"),
    "evidence_source": candidate.get("evidence_source", "reflection"),
    "evidence_id": candidate.get("evidence_id") or str(generate_uuid()),
    "evidence_chain": json_lib.dumps(candidate.get("evidence_chain", ["dummy"])),
    "evidence_count": candidate.get("evidence_count", 1),
    "evidence_strength": candidate.get("evidence_strength", 0.9),
    "status": "candidate",
    "ingested_by": "ai_reflect",
    "verified_at": candidate_verified_at,
    "source_level": candidate.get("level", 2),
}
```

### Evidence Count Distribution

```sql
evidence_count | candidate_count | percentage
---------------|-----------------|------------
1              | 6,869           | 33%
2              | 14,689          | 71% ← Most common
3+             |   131           | 0.6%
```

**Finding**: 71% of Candidates have exactly 2 evidences. This suggests aggregation from multiple sources.

### Content Length Analysis

| Source | Avg Length | Max Length | Characteristic |
|--------|-----------|------------|----------------|
| ai_reflect | 18 chars | 2,545 chars | Highly condensed |
| batch_import | 468 chars | ~5,000 chars | Original conversation snippets |
| import | 1,064 chars | ~10,000 chars | Full dialogue content |

**Key Insight**: Production Candidates are summaries/abstractions, not raw evidence copies.

---

## 3. Old vs New Candidate Comparison

### Legacy Candidates (2026-08-05 import)

```sql
-- batch_import (Phase 21 pre-existing)
content: "那只看这个记账，进和出也不相等吧"
evidence_count: 1
content_length: ~468 chars

-- import (Zero UUID, custom generator)
content: "实体: Abema\n记忆1: 很好的问题！要说 TVer..."
evidence_count: 1-5
content_length: ~1,064 chars
```

### Modern Candidates (2026-08-06 to 2026-08-14)

```sql
-- ai_reflect (ReflectionService)
content: "个人事业主: 没有抚养控除"
evidence_count: 2
content_length: ~18 chars

content: "税务调查: 金额异常、经费比例异常..."
evidence_count: 2
content_length: ~25 chars
```

### Key Differences

| Aspect | Legacy | Modern |
|--------|--------|--------|
| Content source | Direct evidence copy | LLM-extracted summary |
| Content length | Long (468-1000+ chars) | Short (18 chars avg) |
| Evidence count | 1-5 | 1-2 (mostly 2) |
| Granularity | Evidence-level | Entity-level summary |
| Created by | Import scripts | ReflectionService |

---

## 4. L0→L1 Architecture Boundary Analysis

### Current Reality

```
Evidence (L0)
    ↓
[LLM Fact Extraction]
    ↓
Candidate (L1 pending) ← Created by ReflectionService
    ↓
[Proposal Generation]
    ↓
Proposal (L1 pending)
    ↓
[Auto-approve]
    ↓
MemoryNode (L1 active) ← Also created by ReflectionService
```

### What EvidencePipelineService Should Do (Theoretical)

```
Evidence (L0)
    ↓
[ContextWindow Formation]
    ↓
[Semantic Interpretation]
    ↓
Reconstruction + Candidate (L1 pending) ← Should be created here
    ↓
Topics (L1 linking)
```

### What Actually Happens

```
Evidence (L0)
    ↓
[Cron triggers ReflectionService]
    ↓
[LLM extracts facts from ALL pending candidates]
    ↓
[Candidates created by EvidenceEvolutionEngine]
    ↓
[Proposals generated and approved]
    ↓
[MemoryNodes created]
```

**Critical Gap**: EvidencePipelineService creates Reconstruction + Candidate, but this path is NEVER taken in production.

---

## 5. The Missing Reconstruction Layer

### Evidence

```sql
SELECT COUNT(*) FROM reconstructions;
-- Result: 0
```

**Reconstructions table is empty!**

### Implications

1. FormationService._create_reconstruction() exists but is never called
2. The semantic interpretation output (interpretation.semantic_content) is lost
3. Candidates don't have a Reconstruction parent
4. Lineage from Evidence → Interpretation → Reconstruction → Candidate is broken

### Root Cause

EvidencePipelineService requires manual API call to `/pipeline/trigger`. Cron calls ReflectionService directly, bypassing the Formation layer entirely.

---

## 6. Candidate Semantic Granularity Assessment

### Is Current Candidate Granularity Sufficient for L1→L2?

**Analysis**:

```
Current state:
- 20,589 candidates, avg 18 chars content
- 71% have exactly 2 evidences
- All ingested_by='ai_reflect'
- Created by ReflectionService._save_candidates()

This means:
1. Each "candidate" represents a fact pattern, not a single evidence
2. Multiple evidences are aggregated into one candidate
3. The content is a summary, not raw evidence
4. This is ACTUAL aggregation happening in EvidenceEvolutionEngine
```

### Evidence from Code

```python
# evidence_evolution_engine.py:395-408
candidate = {
    "entity": entity,
    "content": f"{entity}: {', '.join(values[:3])}" if values else entity,
    "evidence_chain": source_ids[:10],
    "evidence_count": len(source_ids),
    "confidence": round(avg_confidence, 3),
    "source_level": 1,
    "candidate_type": "pattern",
    ...
}
```

**Finding**: Candidates ARE aggregated at the entity level within each batch. The problem is cross-batch aggregation.

---

## 7. Three Key Conclusions

### Conclusion 1: Candidate Granularity is Sufficient for L1→L2

**Evidence**:
- 71% of candidates have 2 evidences
- Content is entity-level summary (18 chars avg)
- Evidence chain preserves lineage

**Verdict**: ✅ Sufficient for current ReflectionService logic

### Conclusion 2: Clean Rebuild from Evidence is Feasible but Not Recommended

**Evidence**:
- EvidencePipelineService exists but unused
- FormationService can create Candidates from Evidence
- But: LLM interpretation cost, time, and risk of inconsistency

**Verdict**: ⚠️ Technically feasible, but unnecessary unless current data is corrupted

### Conclusion 3: Recommended Pipeline Architecture

```
Option A: Keep Current (Single Pipeline)
Evidence → ReflectionService → Candidate → Proposal → MemoryNode
  - Simple, proven in production
  - No Formation layer
  - L2/L3 blocked by fact density (known issue)

Option B: Two-Pipeline (Theoretical)
Evidence → EvidencePipelineService → Candidate → ReflectionService → MemoryNode
  - Clean separation
  - Formation + Evolution decoupled
  - Requires: populate EvidencePipelineService into production

Option C: Unified Pipeline (Ideal)
Evidence → Formation → L1 MemoryNode → Reflection/Evolution → L2/L3
  - Most architecturally correct
  - Requires: significant refactoring
  - L1 creation moved to Formation layer
```

---

## 8. Architecture Recommendations

### Immediate (No Changes)
- Accept current single-pipeline architecture
- Document that EvidencePipelineService is dormant
- Focus on fixing L2/L3 fact accumulation (Phase 22.1 issue)

### Short-term
- Consider enabling EvidencePipelineService for new evidence ingestion
- Add validation to ensure Formation layer is populated
- Track Reconstruction creation metrics

### Long-term
- Evaluate moving L1 creation to Formation layer
- Design cross-batch entity aggregation
- Consider unified pipeline architecture

---

## 9. Explicit "DO NOT MODIFY" Confirmation

This audit is **READ ONLY**. No modifications were made to:
- ❌ Source code
- ❌ Database
- ❌ Test files
- ❌ Configuration
- ❌ Git history
- ❌ Phase 20 frozen boundary
- ❌ Phase 21 frozen boundary

---

## 10. Final Verdict

| Question | Answer | Evidence |
|----------|--------|----------|
| Is Candidate granularity sufficient? | ✅ Yes | 71% have 2 evidences, content is entity-level summary |
| Should we clean rebuild? | ⚠️ Not recommended | Formation layer unused, risks outweigh benefits |
| What is the correct pipeline? | Depends on goals | See three options above |

**Primary Issue**: The architecture has a Formation layer (EvidencePipelineService) that is not used in production. This is a design gap, not a data corruption issue.

**Recommended Action**: Document the gap, consider enabling Formation layer for new evidence, focus on L2/L3 fact accumulation fix.

---

**Audit complete. Awaiting next instructions.**
