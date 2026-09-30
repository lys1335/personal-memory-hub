# Phase 22.1 Fact Accumulation Read-Only Audit

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Summary

### Core Finding
PMH currently **does NOT have cross-batch fact accumulation**.

Each Reflection batch processes candidates independently. Facts are extracted per-batch by LLM, not aggregated per-entity across batches.

### Impact
- L2/L3 evolution requires `len(entity_facts) >= 2` (Create) or `>= 3` (Strengthen)
- Current production: 92% of batches produce exactly 1 fact per entity
- Therefore: target_level stays at 1, no L2/L3 creation

---

## 1. Fact Lifecycle Analysis

### Does `entity_facts` table exist?
**Answer: NO**

```sql
-- No such table exists in database
SELECT * FROM entity_facts;
-- ERROR: relation "entity_facts" does not exist
```

### Fact lifecycle:
```
Creation: _extract_facts() in ReflectionEngine (per batch)
Storage: In-memory only (returned to service)
Aggregation: _generate_proposals() groups by entity (per batch)
Persistence: NEVER persisted to database
Destruction: Lost after batch completes
```

### Evidence from code:
```python
# reflection_engine.py:279-284
entity_evidence: dict[str, list[dict[str, Any]]] = {}
for fact in facts:
    entity = fact.get("entity", "unknown")
    if entity not in entity_evidence:
        entity_evidence[entity] = []
    entity_evidence[entity].append(fact)
```

This is a local variable, not persisted.

---

## 2. Fact Extraction Call Graph

### Call chain:
```
ReflectionService.reflect()
  ↓
_reflect_pipeline()
  ↓
ReflectionEngine.reflect_pipeline()
  ├─ _extract_facts(candidates, provider)
  │   ├─ Build prompt from candidate content
  │   ├─ Send to LLM
  │   └─ Return facts list
  ├─ _generate_proposals(facts, candidates)
  │   ├─ Group facts by entity
  │   ├─ Calculate avg_confidence per entity
  │   └─ Apply threshold logic
  └─ Return proposals
```

### Key observation:
**Facts are extracted fresh in each batch from candidate content.**

```python
# reflection_engine.py:152-158
for i, c in enumerate(candidates):
    content = c.get("content", "")
    content = content[:500] if len(content) > 500 else content  # Truncated!
    contents.append(f"[{i+1}] {content}")
```

---

## 3. Reflection Scope Analysis

### Query (reflection_service.py:1122-1160):
```sql
SELECT ... FROM candidates
WHERE workspace_id = :workspace_id
  AND status = 'candidate'
  AND verified_at IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM proposals
    WHERE proposals.status = 'pending'
      AND proposals.candidate_id = candidates.id
  )
ORDER BY candidates.created_at ASC
LIMIT :limit
```

### Behavior:
- Selects oldest pending candidates first (FIFO)
- Limit = 20 candidates per batch
- Same candidate enters only ONCE (excluded after proposal created)

### Cross-batch behavior:
```
Batch 1: Candidates [1-20] → Facts [A, B, C] → Proposals [A, B, C]
Batch 2: Candidates [21-40] → Facts [D, E, F] → Proposals [D, E, F]
Batch 3: Candidates [41-60] → Facts [G, H, I] → Proposals [G, H, I]
```

**No entity-level aggregation across batches.**

---

## 4. Cross-Batch Accumulation Analysis

### Can same entity appear in multiple batches?
**YES** — Database evidence shows this:

```sql
-- Entities with multiple candidates:
entity_hint                     | candidate_count | total_evidence
--------------------------------+-----------------+----------------
Applepay: 余额                   |           513   |         979
经费率: 35%                      |           238   |         442
Ampere Altra A1: Oracle Cloud   |           227   |         452
...
```

**Evidence: 513 candidates for "Applepay" entity alone!**

### Why doesn't this trigger L2?

**Root cause:** Candidates are processed in FIFO order, one batch at a time.

```
Time T1: Batch 1 gets candidates [1-20]
  - If these are all "Applepay" candidates, LLM sees 20 candidates
  - But LLM returns only 1 fact for "Applepay" entity
  - Result: 1 fact, not 20

Time T2: Batch 2 gets candidates [21-40]
  - Also "Applepay" candidates
  - Again, LLM returns only 1 fact
  - Previous fact is LOST
```

**The LLM prompt asks to "extract facts from these memories" and returns a summary, not individual facts per source.**

---

## 5. L1 → L2 Real Preconditions

### Current threshold logic (reflection_engine.py:305-316):
```python
if avg_confidence >= 0.8 and len(entity_facts) >= 3 and source_level < max_level:
    proposal_type = "Strengthen"
    target_level = source_level + 1  # Would create L2
elif avg_confidence >= 0.6 and len(entity_facts) >= 2 and source_level < max_level:
    proposal_type = "Create"
    target_level = source_level + 1  # Would create L2
elif avg_confidence >= 0.9:
    proposal_type = "Refine"
    target_level = source_level  # Stay at L1
else:
    proposal_type = "Split"
    target_level = source_level  # Stay at L1
```

### Critical conditions:
1. `len(entity_facts) >= 3` for Strengthen
2. `len(entity_facts) >= 2` for Create
3. Both require `source_level < max_level` (max_level = 5)

### Current reality:
- `len(entity_facts)` is almost always 1 per batch
- Therefore: No Strengthen or Create proposals generated
- Result: All proposals have target_level = 1

### Why len(entity_facts) = 1?

**Possible reasons:**
1. LLM summarizes instead of listing individual facts
2. Batch contains candidates from different entities
3. No entity-level grouping across batch boundaries

---

## 6. Database Distribution Analysis

### Evidence count distribution:
```sql
SELECT 
  c.evidence_count,
  COUNT(*) as candidate_count
FROM candidates c
GROUP BY c.evidence_count
ORDER BY candidate_count DESC
LIMIT 10;
```

**Result:** Most candidates have 1-3 evidences in their chain.

### Fact count per batch:
```
Facts per batch distribution:
  1 fact:  3,396 batches (92%)
  2 facts:  1,045 batches (3%)
  3 facts:    535 batches (1.4%)
  4+ facts:   224 batches (0.6%)
```

### Entity candidate density:
```
Entity              | Candidate count | Total evidence
--------------------|-----------------|----------------
Applepay: 余额       |           513   |         979
经费率: 35%          |           238   |         442
Ampere Altra A1     |           227   |         452
火车票候补           |           227   |         307
上班午休买便当       |           225   |         301
```

**Finding: High entity density exists, but no cross-batch aggregation.**

---

## 7. Root Cause Classification

### P0: None
- System is stable
- No data corruption
- UniqueViolation fixed

### P1: Design Limitation — No Cross-Batch Fact Accumulation
**Description:**
- Facts are extracted per-batch, not per-entity
- No persistence of entity-level fact history
- LLM summary loses individual fact granularity

**Impact:**
- L2/L3 evolution impossible in current design
- High-density entities (513 candidates) cannot trigger abstraction

**Code location:**
- reflection_engine.py:141-189 (_extract_facts)
- reflection_engine.py:265-379 (_generate_proposals)

### P2: LLM Prompt Returns Summary, Not Individual Facts
**Description:**
- Prompt asks "extract structured facts"
- LLM returns 1 fact per entity (summary)
- Not: List of all individual facts

**Example prompt:**
```
"你是一个信息提取专家。请从以下记忆中提取结构化事实。"
输出格式: {"facts":[{"entity":"实体名","value":"值",...}]}
```

**Impact:**
- Even with 513 candidates for same entity, only 1 fact returned
- Threshold `len(entity_facts) >= 2` never met

### INFO: Thresholds May Need Adjustment
**Description:**
- Current thresholds: >= 3 facts for Strengthen, >= 2 for Create
- With current LLM behavior, these are impossible to meet
- Either thresholds need lowering OR fact extraction needs redesign

---

## 8. Architecture Verdict

### Q: Does PMH have cross-batch fact accumulation?
**A: NO**

**Evidence:**
1. No persistent entity_facts table
2. Facts extracted fresh per batch
3. No entity-level aggregation logic
4. LLM returns summary, not individual facts

### Q: Is this a bug or design limitation?
**A: Design limitation**

**Reasoning:**
- Current design treats each batch as independent
- Focus is on L1 observation creation
- L2/L3 evolution is a future enhancement

### Q: What would be required to enable L2/L3?
**A: One of:**
1. Add entity-level fact persistence layer
2. Lower thresholds to match current fact density
3. Change LLM prompt to return individual facts
4. Add explicit cross-batch aggregation logic

---

## 9. Memory Pyramid Reality

### Current state:
```
L0 Evidence:     15,662  (input data, stable)
L1 Candidate:    21,152  (pending, growing)
L1 MemoryNode:   25,822  (Observation, growing)
L2 Pattern:          2  (from historical tests)
L3 Belief:           0  (never created in production)
```

### Why L2/L3 don't grow:
```
Fact density per batch: ~1 fact/entity
Threshold for L2: >= 2 facts (Create) or >= 3 facts (Strengthen)
Result: Threshold never met
```

---

## 10. Recommended Next Phase

### Phase 22.2 Options:

**Option A: Lower thresholds**
- Change Create threshold from >= 2 to >= 1
- Risk: Too many L2 nodes, noise inflation

**Option B: Add entity-level fact persistence**
- Create entity_facts table
- Aggregate facts across batches
- Enable true cross-batch accumulation
- Effort: Medium

**Option C: Redesign LLM prompt**
- Ask for individual facts, not summaries
- Risk: LLM may not comply, token limits

**Option D: Accept current design**
- L2/L3 is future enhancement
- Current L1-only mode is sufficient
- Document as design decision

---

## 11. Explicit "DO NOT MODIFY" Confirmation

This audit is **READ ONLY**. No modifications were made to:
- ❌ Source code
- ❌ Database
- ❌ Test files
- ❌ Configuration
- ❌ Git history
- ❌ Phase 20 frozen boundary
- ❌ Phase 21 frozen boundary

---

**Audit complete. Awaiting next instructions.**
