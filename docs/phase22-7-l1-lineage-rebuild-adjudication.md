# Phase 22.7 L1 Lineage / Rebuild Strategy Adjudication

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Verdict

### Core Finding
**The architecture is fundamentally sound but has a critical lineage gap.**

The current production pipeline (Evidence → ReflectionService → Candidate → Proposal → L1 MemoryNode) is operationally valid. However:

1. **L1 entity_id is ALWAYS NULL** — breaks all aggregation
2. **No cross-batch fact accumulation** — L2/L3 threshold never met
3. **EvidencePipelineService is dormant** — Formation layer unused

### Recommended Strategy: **STRATEGY A** (Selective Repair + Enhancement)

---

## 1. Final L0→L1 Boundary

### Architecture Decision

| Component | Responsibility | Status |
|-----------|---------------|--------|
| EvidencePipelineService | Formation: Evidence → Candidate | Dormant (API-only) |
| ReflectionService | Evolution: Candidate → L1 MemoryNode | **Active** (Cron) |
| EvolutionService | Advanced Evolution: L1 → L2 → L3 | **Partially active** (not triggered) |

### Why This Boundary is Correct

**L1 belongs to ReflectionService because:**
1. L1 requires Proposal approval workflow
2. L1 requires fact extraction and threshold checks
3. L1 is the "confirmed Observation" after reflection
4. EvidencePipelineService only creates "pending Candidates"

**EvidencePipelineService remains as:**
- Optional Formation layer for direct API calls
- Future enhancement for single-Evidence processing
- NOT part of Cron pipeline (by design)

### Final Assignment

```
EvidencePipelineService (Formation):
  Evidence → ContextWindow → Interpretation → Candidate
  Status: Dormant, API-available only

ReflectionService (Evolution):
  Candidate → Proposal → L1 MemoryNode
  Status: Active, Cron-driven
  
EvolutionService (Advanced Evolution):
  L1 MemoryNode → L2 Pattern → L3 Belief
  Status: Not integrated into production pipeline
```

---

## 2. Final L1→L2→L3 Boundary

### Current State

| Level | Count | Creation Method |
|-------|-------|-----------------|
| L1 Observation | 25,952 | ReflectionService.approve_proposal() |
| L2 Pattern | 2 | EvolutionService (manual test) |
| L3 Belief | 0 | Never created |

### Why L2/L3 Don't Trigger

**Root Cause**: Fact density per entity per batch is always 1.

```python
# reflection_engine.py:305-310
if avg_confidence >= 0.8 and len(entity_facts) >= 3:
    proposal_type = "Strengthen"  # → L2
elif avg_confidence >= 0.6 and len(entity_facts) >= 2:
    proposal_type = "Create"      # → L2
```

**Problem**: entity_facts is per-batch, not historical. Each batch has 1 fact/entity. Threshold never met.

### Required Changes for L2/L3

1. **Fix entity_id on L1** (enables grouping)
2. **Add cross-batch aggregation** (accumulate facts over time)
3. **Enhance EvolutionService** to receive multi-L1 input

---

## 3. Candidate Final Positioning

### Verdict: **Lineage Carrier (Transient)**

**Not a Pyramid level. Not a long-term memory. A processing intermediate.**

| Aspect | Status |
|--------|--------|
| Role | Evidence lineage holder |
| Lifetime | Until Proposal created |
| Retention | Archive after 30 days or L1 creation |
| Purpose | Enable evidence traceability |

**Code evidence**:
```python
# reflection_service.py:986-1045
# Candidates are created, then proposals are generated from them
# After approval, candidates are marked as 'confirmed'
```

**Recommendation**: Add archival logic to mark Candidates as 'archived' after L1 creation.

---

## 4. L1 Entity Lineage Final Model

### Current Problem

```
Candidate.entity_id (UUID) ✅
    ↓ lost during Proposal creation
Proposal.entity (varchar) ⚠️
    ↓ lost during L1 creation
L1 MemoryNode.entity_id (UUID) ❌ NULL
```

### Root Cause

```python
# reflection_service.py:248-250
# Note: proposals table does not have entity_id column, use None
entity_id = None
```

### Proposed Fix (Minimal)

```python
# In approve_proposal():
candidate = await self._candidate_repo.find_by_id(prop['candidate_id'])
entity_id = candidate.entity_id if candidate else None
```

### Multi-Entity Support

**Analysis**: No L1 currently contains multiple entities.
- 0 L1 nodes have multi-entity content patterns
- Content prefix extraction shows single entity per L1

**Verdict**: Single entity_id is sufficient for current data.

**Future consideration**: If multi-entity L1 needed, use `memory_relationships` or `topic_links`.

---

## 5. Old L1 Recoverability Re-evaluation

### New Analysis (Beyond Phase 22.6)

| Recovery Path | Count | Confidence | Notes |
|--------------|-------|------------|-------|
| A. Proposal → Candidate | 6,702 | 1.0 | Direct lineage |
| B. Content prefix extraction | 8,715 | 0.5 | Heuristic matching |
| C. Evidence entity_id | 0 | N/A | Evidences lack entity_id |
| D. Topic/Relationship | 0 | N/A | Tables empty |
| **Total recoverable** | **6,702** | **1.0** | Direct lineage only |
| **Total heuristic** | **15,417** | **0.5** | Content-based |
| **Total unrecoverable** | **19,250** | **0.0** | No lineage |

### Key Insight

**Phase 22.6 underestimated recoverability.**

- 6,702 L1 (25.8%) have direct lineage via Proposals
- 8,715 L1 (33.6%) have extractable entity prefix in content
- Combined: **59.4% have SOME entity association**
- But only 25.8% are HIGH-confidence recoverable

### Entity Prefix Matching Results

```
Entity           | Count | Match Status
-----------------|-------|-------------
经费率           | 233   | MATCHED
经费             | 187   | MATCHED
废业             | 164   | MATCHED
Applepay         | 153   | MATCHED
税务系统         | 130   | MATCHED
会计年度         | 128   | MATCHED
午休买便当       | 127   | MATCHED
```

**Conclusion**: Content-based recovery is feasible but lower confidence.

---

## 6. Strategy Comparison

### Strategy A: Selective Repair

**Description**: 
- Fix entity_id for recoverable L1 (6,702)
- Accept 19,250 L1 as orphaned
- Enhance EvolutionService for L2/L3
- Keep all existing data

**Pros**:
- Minimal data loss (25.8% lineage restored)
- No LLM re-processing cost
- Preserves all existing Memories
- Non-disruptive

**Cons**:
- 74.2% of L1 remain without entity_id
- Cannot aggregate orphaned L1 for L2

**Cost**:
- LLM cost: $0
- Execution time: < 1 hour (SQL backfill)
- Risk: Low

---

### Strategy B: Clean Rebuild

**Description**:
- Keep all Evidences (15,662)
- Delete Candidates, Proposals, L1, L2, L3
- Re-run Formation pipeline for all Evidences
- Re-run Reflection pipeline for all Candidates

**Pros**:
- 100% lineage restoration
- Clean architecture
- No legacy data issues

**Cons**:
- Massive LLM cost (~15,000 evidence processing)
- Time: Days to weeks
- Risk: Data loss during transition
- Disrupts production

**Cost**:
- LLM cost: ~$500-1000 (estimated)
- Execution time: 3-7 days
- Risk: High

---

### Strategy C: Parallel Validation

**Description**:
- Keep existing L1 as-is
- Create new correct L1 alongside
- Validate both outputs
- Switch after validation

**Pros**:
- Safe validation
- Can compare quality
- No data loss

**Cons**:
- Doubles storage temporarily
- Complex validation logic
- Still needs full rebuild

**Cost**:
- LLM cost: ~$500 (validation sample)
- Execution time: 1-2 weeks
- Risk: Medium

---

## 7. Recommendation: Strategy A

### Why Strategy A Wins

| Criterion | Strategy A | Strategy B | Strategy C |
|-----------|-----------|------------|------------|
| Data loss | 25.8% lineage | 0% | 0% |
| LLM cost | $0 | $500-1000 | $500 |
| Time | < 1 hour | 3-7 days | 1-2 weeks |
| Risk | Low | High | Medium |
| Production impact | Minimal | Disruptive | Moderate |
| Philosophy fit | Conservative | Aggressive | Cautious |

### Rationale

1. **74.2% data loss is acceptable** because:
   - Core Evidence is preserved (source of truth)
   - New L1 will have correct lineage
   - Orphaned L1 are low-value (no aggregation possible anyway)

2. **Clean rebuild is unnecessary** because:
   - Evidence → Candidate pipeline already works
   - Only entity_id linkage is broken
   - Partial repair is sufficient

3. **Strategy C is over-engineered** because:
   - Parallel validation adds complexity
   - Same end result as Strategy B but slower
   - No additional value

---

## 8. Implementation Roadmap

### Phase 1: Fix entity_id (P0 — Immediate)

**Actions**:
1. Modify `reflection_service.py:approve_proposal()` to extract entity_id from Candidate
2. Run SQL backfill for 6,702 recoverable L1 nodes
3. Validate: All new L1 should have entity_id

**Time**: < 1 hour
**Risk**: Low

### Phase 2: Enhance EvolutionService (P1 — Short-term)

**Actions**:
1. Add `evolve_entity_history(entity_id)` method
2. Query all L1 for entity, aggregate facts
3. Create L2 Pattern if threshold met

**Time**: 1-2 days
**Risk**: Medium

### Phase 3: Enable L2/L3 (P2 — Medium-term)

**Actions**:
1. Trigger EvolutionService for high-density entities
2. Monitor L2/L3 creation
3. Adjust thresholds if needed

**Time**: 1 week
**Risk**: Low

---

## 9. Conflicts and Open Questions

### Confirmed Conflicts

1. **Phase 22.3 vs Phase 22.6**: 
   - 22.3 says EvidencePipelineService is "dormant"
   - 22.6 implies it should be activated
   - **Resolution**: Keep dormant, enhance ReflectionService instead

2. **entity_facts necessity**:
   - Phase 22.5 suggests NOT needed yet
   - Phase 22.4 suggests it might help
   - **Resolution**: Skip for now, add only if L2 aggregation fails

### Open Design Questions

1. **Should entity_prefix extraction be automated?**
   - Pros: Recover more L1
   - Cons: Lower confidence, potential misattribution
   - **Recommendation**: Manual review for top 100 entities

2. **Should we archive orphaned L1?**
   - Pros: Clear data model
   - Cons: Loss of historical context
   - **Recommendation**: Mark as `status='orphaned'`, keep for audit

3. **Should EvidencePipelineService be enabled for new evidence?**
   - Pros: Clean Formation layer
   - Cons: Dual pipeline complexity
   - **Recommendation**: Yes, but keep Cron on ReflectionService

---

## 10. Final Answers

| Question | Answer |
|----------|--------|
| 1. EvidencePipelineService final duty? | Optional Formation layer (API-only) |
| 2. ReflectionService final duty? | L0→L1 evolution (Cron-driven) |
| 3. Who creates L1? | ReflectionService |
| 4. Should ReflectionService handle L0→L1? | YES — this is correct |
| 5. Should ReflectionService handle L1→L2→L3? | NO — delegate to EvolutionService |
| 6. EvolutionService position? | L1→L2→L3 advanced evolution |
| 7. Candidate position? | Lineage carrier (transient) |
| 8. L1 must have entity_id? | YES — critical for aggregation |
| 9. Can 25,952 L1 be recovered? | PARTIALLY — 6,702 (25.8%) |
| 10. Is clean rebuild needed? | NO — Strategy A sufficient |
| 11. Is migration needed? | NO — only code fix + SQL backfill |
| 12. Can modify Phase 20/21? | MINIMAL — only approve_proposal() |
| 13. Next phase? | Phase 1: Fix entity_id |

---

## 11. Explicit "DO NOT MODIFY" Confirmation

This adjudication is **READ ONLY**. No modifications were made to:
- ❌ Source code
- ❌ Database
- ❌ Test files
- ❌ Configuration
- ❌ Git history
- ❌ Phase 20 frozen boundary
- ❌ Phase 21 frozen boundary

---

**Adjudication complete. Awaiting user decision on Strategy A implementation.**
