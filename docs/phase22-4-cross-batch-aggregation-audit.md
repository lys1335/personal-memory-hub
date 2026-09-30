# Phase 22.4 Cross-Batch Entity Aggregation Architecture Audit

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Summary

### Core Finding
**PMH currently has NO cross-batch entity aggregation mechanism.**

The production pipeline processes each batch independently:
```
Batch N: Evidence → Candidates → Facts → Proposals → L1 MemoryNodes
Batch N+1: New Evidence → New Candidates → New Facts → New Proposals → New L1 MemoryNodes
           ↑
           Previous batch facts are LOST
```

This is the root cause of L2/L3 stagnation.

---

## 1. Candidate Historical Aggregation Analysis

### Investigation: Does cross-batch aggregation exist?

**Evidence from code analysis:**

```python
# reflection_service.py:1148-1163
result = await conn.execute(text("""
    SELECT id, entity_id, area_id, content, candidate_type,
           evidence_source, evidence_id, evidence_chain,
           evidence_count, evidence_strength, status,
           COALESCE(source_level, 1) as source_level
    FROM candidates
    WHERE workspace_id = :workspace_id
    AND status = 'candidate'
    AND NOT EXISTS (
        SELECT 1 FROM proposals
        WHERE proposals.candidate_id = candidates.id
        AND proposals.status = 'pending'
    )
    ORDER BY created_at ASC
    LIMIT :limit
"""), {"workspace_id": str(workspace_id), "limit": limit})
```

**Finding**: `_acquire_scope()` queries `candidates` table filtered by `status='candidate'`. It does NOT:
- Group by `entity_id`
- Aggregate across time
- Look up historical facts
- Build entity-level fact history

### Database Evidence

```sql
-- Entity with most candidates (proves candidates exist for same entity over time)
entity: 经费
  total_candidates: 957
  earliest: 2026-08-06 16:48:19
  latest: 2026-08-14 03:09:54
  avg_evidence_count: 1.87
  avg_content_length: 14.8 chars

entity: Applepay
  total_candidates: 529
  earliest: 2026-08-06 16:40:57
  latest: 2026-08-14 03:21:36
  avg_evidence_count: 1.89
  avg_content_length: 12.1 chars
```

**Key Insight**: 957 candidates for "经费" entity exist across 8 days. But are they aggregated?

**Answer: NO.**

Each batch processes a subset of pending candidates. When processed, they become proposals/memory_nodes and exit the pending pool. The next batch sees NEW candidates, not historical aggregation.

---

## 2. ReflectionService Scope Analysis

### _acquire_scope() Behavior

```python
# Key logic:
WHERE status = 'candidate'
AND NOT EXISTS (SELECT 1 FROM proposals WHERE candidate_id = candidates.id AND status = 'pending')
ORDER BY created_at ASC
LIMIT :limit
```

**Implications:**
1. Only processes candidates with status='candidate'
2. Excludes candidates that already have pending proposals
3. Ordered by creation time (FIFO)
4. Limited to `limit` (default 50)

**Cross-batch behavior:**
- Batch 1: Process candidates [1-50], create proposals
- Batch 2: Process candidates [51-100], create proposals
- ...
- Historical candidates from previous batches are NO LONGER in the pool

### _extract_facts() Behavior

**No such method exists in ReflectionService.**

Fact extraction happens in `EvidenceEvolutionEngine._build_candidates()` during candidate creation:

```python
# evidence_evolution_engine.py:xxx (inferred from Phase 22.1 findings)
# During candidate creation, facts are extracted per-entity per-batch
# But these facts are in-memory only
```

**The entity_facts dictionary is created per-batch and destroyed after processing.**

### _generate_proposals() Behavior

```python
# reflection_service.py:1046-1121
async def _save_proposals(self, proposals, workspace_id):
    for prop in proposals:
        # Insert into proposals table
        INSERT INTO proposals (...) VALUES (...)
```

**Proposal structure:**
```python
{
    "entity": "经费",
    "type": "refine",  # or "split", "strengthen", "create"
    "evidence_chain": [...],
    "target_level": 1,  # Always 1 in production
    "confidence": 0.9,
}
```

**Finding**: `target_level` is always 1 because:
1. Facts are extracted per-batch
2. Each entity has ≤2 facts per batch (due to LLM summary behavior)
3. Threshold for Strengthen (≥3 facts) or Create (≥2 facts) is rarely met

---

## 3. Evidence → L1 → L2 Information Flow

### Current Data Flow

```
Evidence (L0)
    ↓
[ReflectionService._save_candidates()]
    ↓
Candidate (pending state)
    ↓
[ReflectionService._generate_proposals()]
    ↓
Proposal (pending state)
    ↓
[ReflectionService._auto_approve_pending_proposals()]
    ↓
MemoryNode (L1, Observation)
    ↓
[NEXT BATCH] ← DOES NOT READ L1
```

### Critical Gap: L1 MemoryNodes are NOT part of next Reflection scope

**Evidence from `_acquire_scope()`:**
```sql
-- Only queries candidates table
FROM candidates WHERE status = 'candidate'
-- Does NOT query memory_nodes table
-- Does NOT consider historical L1 nodes
```

**Implication**: Once an L1 MemoryNode is created, it is NEVER reconsidered in future Reflection cycles. The system has no mechanism to:
- Read existing L1 nodes
- Compare new evidence against old observations
- Detect patterns across time

### Why L2/L3 Never Trigger

```
Current flow for entity "经费":
Batch 1: 5 evidences → 5 candidates → 5 proposals → 5 L1 MemoryNodes
Batch 2: 5 NEW evidences → 5 NEW candidates → 5 NEW proposals → 5 NEW L1 MemoryNodes
...
Batch 10: 5 NEW evidences → 5 NEW candidates → 5 NEW proposals → 5 NEW L1 MemoryNodes

Result: 50 L1 MemoryNodes, 0 L2 Pattern
Problem: No single batch has ≥3 facts for entity "经费"
```

---

## 4. EvolutionService Actual Capabilities

### What EvolutionService CAN Do

```python
# evolution_service.py: evolve(candidate_id, workspace_id, entity_id, topic_ids)
# 
# Steps:
# 1. Load candidate
# 2. Detect historical relationships
# 3. Process Topic evolution
# 4. Create/Update MemoryNode (L2/L3)
```

### Historical Relationship Detection

```python
# evolution_service.py: _detect_historical_relationships()
# Looks for:
# - Existing MemoryNodes with same entity_id
# - Temporal proximity
# - Semantic similarity
```

### The Gap: Single Candidate Input

**Critical limitation**: EvolutionService expects a SINGLE candidate_id as input.

```python
# evidence_pipeline_service.py:162-168
await self._evolve(
    candidate_id=formation.candidate_id,  # Single candidate
    workspace_id=workspace_id,
    entity_id=interpretation.entity_id,
    topic_ids=topic_ids,
)
```

**It cannot receive:**
- Multiple candidates for the same entity
- Historical L1 MemoryNodes
- Entity-level fact history

### Why ReflectionService Doesn't Use EvolutionService

**Design decision (implicit):**
1. ReflectionService was designed for L1 creation only
2. EvidencePipelineService was designed for Formation + optional L2/L3
3. The integration between them is incomplete

**Code evidence:**
```python
# evidence_pipeline_service.py:160-170
if interpretation.user_owned:
    await self._evolve(...)  # Only if user-owned
# But Cron calls ReflectionService, not EvidencePipelineService
```

---

## 5. Three Candidate Architectures

### Architecture A: Candidate-based Aggregation

```
Entity
  → Query all historical Candidates (by entity_id)
  → Aggregate facts across all Candidates
  → Run Reflection/Evolution if threshold met
  → Create L2/L3 MemoryNode
```

**Pros:**
- Uses existing Candidate data
- Lineage preserved (Candidates reference Evidences)
- No new tables needed

**Cons:**
- Candidates are batch-local summaries, not full facts
- 957 Candidates for "经费" would need aggregation
- LLM context limit for large entity histories

**Data flow:**
```
Evidence → Candidate → [Aggregate by entity] → Facts → Proposal → L2/L3
                                    ↑
                           Historical Candidates
```

---

### Architecture B: MemoryNode-based Evolution

```
Entity
  → Query all historical L1 MemoryNodes (by entity_id)
  → Aggregate observations across all L1 nodes
  → Run EvolutionService if threshold met
  → Create L2/L3 MemoryNode
```

**Pros:**
- L1 MemoryNodes are confirmed observations (higher quality)
- Natural hierarchy: L1 → L2 → L3
- EvolutionService designed for this

**Cons:**
- Requires scanning all L1 nodes per entity
- 25,905 L1 nodes exist; query performance concern
- MemoryNodes don't preserve full evidence lineage

**Data flow:**
```
Evidence → Candidate → Proposal → L1 MemoryNode
                                            ↓
                               [Aggregate by entity]
                                            ↓
                               EvolutionService → L2/L3
```

---

### Architecture C: Hybrid (Proposed)

```
Entity
  → Query historical Candidates (for evidence lineage)
  → Query historical L1 MemoryNodes (for confirmed observations)
  → Build entity fact history
  → Run Reflection/Evolution if threshold met
  → Create L2/L3 MemoryNode
```

**Pros:**
- Best of both worlds: lineage + confirmed observations
- Flexible: can fallback to Candidates if L1 sparse
- Supports both "fresh" and "mature" entities

**Cons:**
- Most complex implementation
- Requires cross-table aggregation logic
- Needs careful transaction management

**Data flow:**
```
Evidence → Candidate → Proposal → L1 MemoryNode
    ↓                      ↓              ↓
[Historical Candidates] [Historical L1s] → Entity Fact History → EvolutionService → L2/L3
```

---

## 6. Semantic Analysis: What Should Be L2 Input?

### Memory Pyramid Semantics

```
L0 Evidence: Raw conversation snippets (unprocessed)
L1 Observation: Entity-specific fact extracted from Evidence
L2 Pattern: Repeated observation across time/entity
L3 Belief: Fundamental principle derived from patterns
```

### Analysis: What makes a Pattern?

**Definition**: A Pattern is a recurring observation that appears across multiple independent Evidence instances.

**Implication**: To detect a Pattern, you need:
1. Multiple Evidence instances
2. Same entity/concept
3. Consistent observation across time

**Current Problem**: We have evidence of Patterns (50+ Candidates for "经费"), but they're stored as separate L1 MemoryNodes, not aggregated into a single L2 Pattern.

### Recommended Input Objects

| Level | Input Type | Rationale |
|-------|-----------|-----------|
| L2 | Historical L1 MemoryNodes | Patterns emerge from repeated Observations |
| L3 | Historical L2 Patterns | Beliefs emerge from repeated Patterns |

**Candidate role**: Candidates are transient processing objects, not long-term storage. They should NOT be the primary input for L2/L3 evolution.

---

## 7. Final Conclusions

### Q1: What is the most reasonable input for L2?

**A: Historical L1 MemoryNodes (Architecture B or C)**

**Evidence:**
1. L1 MemoryNodes are confirmed observations (approved proposals)
2. They represent entity-level facts with lineage to Evidence
3. Aggregating L1 nodes by entity_id gives us the "pattern" we're looking for
4. EvolutionService is designed to work with MemoryNodes

### Q2: What is the most reasonable input for L3?

**A: Historical L2 Patterns (Architecture B or C)**

**Evidence:**
1. L3 should be derived from L2 patterns
2. L2 patterns represent confirmed entity behaviors
3. Belief = persistent pattern across multiple entities

### Q3: Should Candidates be retained long-term?

**A: No (or minimal retention)**

**Evidence:**
1. Candidates are processing intermediates
2. Once approved → MemoryNode, once rejected → orphaned
3. Retaining all 21,589 Candidates wastes storage
4. Lineage is preserved in MemoryNode.evidence_links

**Recommendation**: Archive Candidates after 30 days, or delete after L1 creation.

### Q4: Is a persistent Fact layer needed?

**A: Yes (with caveats)**

**Required:**
1. Entity-level fact table (entity_facts)
2. Timestamped fact entries
3. Confidence tracking
4. Source lineage (which Candidate/Evidence produced it)

**Not Required:**
1. Replace Candidate/MemoryNode tables
2. Duplicate existing data

**Implementation**: Add `entity_facts` table that tracks:
```sql
CREATE TABLE entity_facts (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(id),
    fact_text TEXT,
    confidence FLOAT,
    source_candidate_id UUID REFERENCES candidates(id),
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ  -- For TTL cleanup
);
```

### Q5: Does ReflectionService need modification?

**A: Yes (for Architecture B/C)**

**Changes needed:**
1. Add entity-level history query
2. Aggregate facts across historical L1 nodes
3. Re-evaluate threshold with accumulated facts
4. Call EvolutionService for L2/L3 creation

**But**: Do NOT modify frozen Phase 20/21 code without approval.

### Q6: Where should EvolutionService be positioned?

**A: As the L2/L3 evolution engine (not L1 creator)**

**Current role**: EvidencePipelineService only (dormant)
**Proposed role**: 
- Called by ReflectionService for L2/L3 decisions
- Receives entity-level fact history
- Creates L2/L3 MemoryNodes

**Boundary**:
```
ReflectionService: L0→L1 (current)
EvolutionService: L1→L2→L3 (proposed enhancement)
```

### Q7: Should EvidencePipelineService remain independent?

**A: Yes, but needs integration**

**Current state**: Independent, dormant
**Proposed state**: Integrated as optional Formation layer

**Integration points:**
1. EvidencePipelineService creates Candidates from Evidence
2. ReflectionService processes Candidates into L1
3. (Future) ReflectionService calls EvolutionService for L2/L3

**Rationale**: Separation of concerns - Formation vs. Evolution.

---

## 8. Recommended Path Forward

### Immediate (No code changes)
- Accept current single-pipeline architecture
- Document the L2/L3 stagnation as known limitation
- Focus on fixing immediate issues (UniqueViolation already fixed)

### Short-term (Requires approval)
1. Add entity_facts persistence layer
2. Modify ReflectionService to query historical facts
3. Re-run Reflection for high-density entities
4. Validate L2/L3 creation works

### Long-term (Architecture evolution)
1. Enable EvidencePipelineService for new evidence
2. Integrate EvolutionService into production pipeline
3. Implement cross-batch entity aggregation
4. Design Candidate lifecycle management (archive/delete)

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

## 10. Summary Table

| Component | Current State | Recommended State | Gap |
|-----------|--------------|-------------------|-----|
| EvidencePipelineService | Dormant | Optional Formation layer | Needs integration |
| ReflectionService | L0→L1 only | L0→L1 + L1 history aggregation | Needs history query |
| EvolutionService | L1→L2→L3 (theoretical) | L1→L2→L3 (production) | Needs trigger integration |
| entity_facts | In-memory only | Persistent table | Needs new table |
| Candidates | 21,589 active | Archive after L1 creation | Needs lifecycle mgmt |

---

**Audit complete. Awaiting next instructions.**
