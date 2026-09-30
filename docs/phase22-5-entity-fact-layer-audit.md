# Phase 22.5 Entity Fact Layer Architecture Design Audit

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Summary

### Critical Finding: entity_id Loss in L1 MemoryNode Creation

**The root cause of L2/L3 stagnation is NOT just missing fact accumulation — it's that L1 MemoryNodes are created WITHOUT entity_id linkage.**

This means:
1. L1 MemoryNodes cannot be queried by entity for aggregation
2. Cross-batch entity analysis is impossible
3. The entity-based aggregation architecture proposed in Phase 22.4 is fundamentally broken at the data level

---

## 1. Candidate Long-term Responsibilities

### Current Candidate Fields (21 columns)

| Field | Purpose | Long-term Value |
|-------|---------|-----------------|
| id | Primary key | Unique identifier |
| workspace_id | Tenant isolation | Required for queries |
| **entity_id** | **Entity linkage** | **CRITICAL — missing in L1** |
| area_id | Spatial context | Optional |
| content | Entity-level summary | Information载体 |
| candidate_type | pattern/belief | Metadata |
| evidence_chain | Evidence lineage | CRITICAL for provenance |
| evidence_count | Evidence count | Aggregation metric |
| evidence_strength | Confidence metric | Quality indicator |
| status | candidate/confirmed/orphaned | Lifecycle state |
| ingested_by | Source tracking | Audit trail |
| created_at | Creation timestamp | Time-based filtering |

### Candidate Responsibilities Assessment

| Responsibility | Required? | Evidence |
|---------------|-----------|----------|
| Evidence lineage | ✅ Yes | `evidence_chain` field preserves this |
| L1 formation provenance | ✅ Yes | `ingested_by`, `created_at` |
| Proposal input | ✅ Yes | FK in proposals table |
| Deduplication | ⚠️ Partial | Unique constraint on candidate_id + workspace_id |
| Evolution input | ✅ Yes | Used by EvolutionService |
| Historical audit | ✅ Yes | All fields support audit |

**Conclusion**: Candidates ARE necessary long-term objects for lineage and audit purposes. They should NOT be deleted after L1 creation.

---

## 2. MemoryNode Sufficiency Analysis

### Current L1 MemoryNode Fields (21 columns)

| Field | Present? | Value for L2 Input |
|-------|----------|-------------------|
| id | ✅ | Unique identifier |
| workspace_id | ✅ | Required for queries |
| **entity_id** | ❌ **NULL** | **CRITICAL GAP** |
| parent_node_id | ⚠️ NULL | Not set during creation |
| level | ✅ | Always 1 |
| node_type | ✅ | Always "Observation" |
| content | ✅ | Entity summary text |
| evidence_links | ✅ | JSON array of IDs |
| confidence | ✅ | Numeric quality metric |
| created_at | ✅ | Timestamp |

### The entity_id Gap

**Evidence from code:**
```python
# reflection_service.py:248-250
# Get entity_id from proposal (set during candidate creation)
# Note: proposals table does not have entity_id column, use None
entity_id = None
```

**Root Cause:**
1. Candidates have `entity_id` (UUID)
2. Proposals have `entity` (varchar) — TEXT, not UUID FK
3. L1 MemoryNode creation uses `entity_id = None`

**Impact:**
```sql
-- All 25,903 L1 MemoryNodes have NULL entity_id
SELECT COUNT(*) FROM memory_nodes WHERE level = 1 AND entity_id IS NULL;
-- Result: 25,903

-- No L1 can be queried by entity for aggregation
SELECT entity_id, COUNT(*) FROM memory_nodes WHERE level = 1 GROUP BY entity_id;
-- Result: Only NULL group
```

---

## 3. entity_facts Necessity Analysis

### Option Comparison

#### A. Candidate → L1 → Historical Aggregation

```
Flow:
Candidate → Proposal → L1 MemoryNode
                   ↓
            [No entity_id linkage]
                   ↓
            Cannot aggregate by entity
```

**Verdict**: ❌ BROKEN — entity_id is lost

#### B. Candidate → entity_facts → L1 → L2

```
Flow:
Candidate → entity_facts (persistent)
                ↓
         L1 MemoryNode (with entity_id)
                ↓
         L2 Pattern (from entity_facts aggregation)
```

**Verdict**: ⚠️ REDUNDANT — entity_facts duplicates L1 content

#### C. Candidate → entity_facts → L2 (L1 as display layer)

```
Flow:
Candidate → entity_facts (persistent facts)
                ↓
         L2 Pattern (direct from facts)
                ↓
         L1 MemoryNode (for display only)
```

**Verdict**: ❌ SEMANTICALLY WRONG — L1 should be Observation, not display layer

#### D. Candidate → L1 → entity_facts (derived index)

```
Flow:
Candidate → Proposal → L1 MemoryNode (with entity_id)
                              ↓
                    entity_facts (derived index)
                              ↓
                    L2 Pattern (from entity_facts)
```

**Verdict**: ✅ MINIMAL OVERHEAD — only adds aggregation index

---

### Detailed Comparison

| Aspect | A (Current) | B | C | D (Recommended) |
|--------|-------------|---|---|-----------------|
| entity_id linkage | ❌ NULL | ✅ Yes | ✅ Yes | ✅ Yes |
| Lineage preserved | ✅ | ✅ | ⚠️ Partial | ✅ |
| Data duplication | None | High | Medium | Low |
| Query performance | Poor | Good | Good | Good |
| LLM context cost | High | Medium | Low | Low |
| Implementation complexity | None | High | Medium | Low |
| Fits Memory Pyramid | ❌ Broken | ⚠️ Odd | ❌ Wrong | ✅ Correct |

---

## 4. Existing Relationship Analysis

### memory_relationships Table

```sql
-- Schema
id              UUID PK
workspace_id    UUID NOT NULL
source_node_id  UUID NOT NULL
target_node_id  UUID NOT NULL
relationship_type VARCHAR NOT NULL
contribution_weight DOUBLE PRECISION
_meta           JSONB
created_at      TIMESTAMPTZ
```

### Current Usage

```sql
SELECT relationship_type, COUNT(*) 
FROM memory_relationships 
GROUP BY relationship_type;
-- Result: 0 rows
```

**Finding**: Relationships table exists but is NEVER used in production.

### Could Relationships Solve the Problem?

**Hypothetical**: If relationships were populated:
```
L1_A [entity="经费"] --supports--> L2_Pattern [entity="经费"]
L1_B [entity="经费"] --supports--> L2_Pattern [entity="经费"]
```

**Problem**: Still need entity_id on L1 nodes to query relationships by entity.

**Verdict**: Relationships are complementary, not a solution to the entity_id gap.

---

## 5. Minimal Necessary Architecture

### Root Cause Analysis

The problem is NOT:
- Missing cross-batch aggregation logic
- Missing entity_facts table
- Missing EvolutionService integration

The problem IS:
- **L1 MemoryNodes are created without entity_id**
- This makes ALL downstream aggregation impossible

### Minimal Fix: Add entity_id to L1 Creation

**Required changes:**
1. Add `entity_id` column to proposals table (or extract from evidence_chain)
2. Update `approve_proposal()` to set entity_id on L1 MemoryNode
3. Backfill existing L1 MemoryNodes with entity_id from evidence_chain

**Code change location:**
```python
# reflection_service.py:250
entity_id = None  # ← CHANGE THIS
# Extract from proposal evidence_chain → look up candidate → get entity_id
```

### Optional Enhancement: entity_facts Table

**When needed:**
- If L1 content is too verbose for L2 input
- If we want to track fact-level confidence over time
- If we want to deduplicate across L1 nodes

**Table structure:**
```sql
CREATE TABLE entity_facts (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(id),
    fact_text TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    source_l1_id UUID REFERENCES memory_nodes(id),
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ  -- For TTL cleanup
);
```

**Verdict**: NOT REQUIRED immediately. Fix entity_id first.

---

## 6. Memory Pyramid Responsibility Mapping

### Clear Assignment

| Object | Pyramid Level | Rationale |
|--------|--------------|-----------|
| **Evidence** | L0 | Raw input, unprocessed |
| **Candidate** | **NOT A NODE** | Processing intermediate, transient |
| **Reconstruction** | **NOT A NODE** | Formation intermediate, dormant |
| **Proposal** | **NOT A NODE** | Decision intermediate, transient |
| **MemoryNode (L1)** | L1 Observation | Confirmed entity-specific fact |
| **MemoryNode (L2)** | L2 Pattern | Aggregated observation across time |
| **MemoryNode (L3)** | L3 Belief | Fundamental principle from patterns |
| **entity_facts** | **NOT A NODE** | Aggregation index, not a memory node |
| **Topic** | **NOT A NODE** | Metadata/index layer |

### Clarification

**Candidates are NOT part of the Memory Pyramid.** They are processing intermediates that:
- Hold pending Evidence interpretations
- Feed into Proposal generation
- Should be archived/deleted after L1 creation

**The Pyramid is:**
```
L0: Evidence (raw)
    ↓
L1: MemoryNode (Observation)
    ↓
L2: MemoryNode (Pattern)
    ↓
L3: MemoryNode (Belief)
```

---

## 7. Final Architecture Recommendations

### Q1. Should we add entity_facts?

**A: NOT YET.**

First fix the entity_id gap in L1 MemoryNodes. After that, evaluate if entity_facts is needed.

**Rationale:**
- entity_facts would duplicate L1 content
- L1 nodes ALREADY contain entity-specific facts
- Add entity_facts only if L1 content is insufficient for L2 input

### Q2. What should entity_facts store?

**If added, it should store:**
```
- entity_id (FK to entities)
- fact_text (summarized observation)
- confidence (aggregate from L1 nodes)
- source_l1_id (FK to memory_nodes)
- created_at / expires_at (TTL)
```

**NOT:**
- Duplicate of L1 content
- Raw Evidence content
- Full Candidate history

### Q3. Relationship with Candidate

**entity_facts should NOT reference Candidate directly.**

Rationale:
- Candidates are transient processing objects
- entity_facts should derive from L1 MemoryNodes (confirmed observations)
- Lineage: Candidate → L1 → entity_facts (indirect)

### Q4. Relationship with L1 MemoryNode

**entity_facts is a DERIVED INDEX from L1 MemoryNodes.**

```
L1 MemoryNode (authoritative)
    ↓ derives
entity_facts (aggregation index)
```

**Operations:**
- INSERT: When L1 is created, optionally create entity_fact entry
- UPDATE: When L1 is updated, recalculate entity_fact
- DELETE: When L1 is deleted, remove entity_fact entry

### Q5. What should L2 read from?

**PRIMARY: Historical L1 MemoryNodes (by entity_id)**

```sql
SELECT * FROM memory_nodes 
WHERE entity_id = :entity_id 
AND level = 1
ORDER BY created_at DESC;
```

**OPTIONAL: entity_facts (if added)**

```sql
SELECT * FROM entity_facts 
WHERE entity_id = :entity_id
ORDER BY created_at DESC;
```

### Q6. What should L3 read from?

**Historical L2 MemoryNodes (by entity_id or related entities)**

```sql
SELECT * FROM memory_nodes 
WHERE entity_id = :entity_id 
AND level = 2
ORDER BY created_at DESC;
```

### Q7. ReflectionService responsibility?

**Current:**
- Acquire scope (candidates)
- Generate proposals
- Approve proposals → Create L1

**Should add:**
- Set entity_id on L1 MemoryNodes (FIX)
- Optional: Call EvolutionService for L2/L3 (future)

### Q8. EvolutionService responsibility?

**Current:**
- Single candidate evolution (L1→L2→L3)
- Historical relationship detection

**Should be:**
- L2/L3 evolution engine
- Receive entity-level fact history
- Create Pattern/Belief MemoryNodes

### Q9. EvidencePipelineService responsibility?

**Current:**
- Dormant (never used in production)

**Should be:**
- Optional Formation layer
- Evidence → ContextWindow → Interpretation → Reconstruction + Candidate
- Triggered by API, not Cron

### Q10. Should Candidates be retained?

**A: ARCHIVE, not delete.**

**Rationale:**
- Preserve lineage for audit
- Allow re-processing if needed
- Archive after 30 days or L1 creation

**Implementation:**
```sql
-- Soft delete via status change
UPDATE candidates SET status = 'archived' WHERE created_at < NOW() - INTERVAL '30 days';
```

### Q11. Is clean rebuild needed?

**A: NO — but backfill is required.**

**Actions:**
1. Fix code: Add entity_id to L1 creation
2. Backfill: Set entity_id on existing 25,903 L1 nodes
3. Validate: Ensure entity_id propagation works
4. Test: Run ReflectionService on historical data

**DO NOT:**
- Delete all Candidates
- Delete all Proposals
- Delete all MemoryNodes
- Re-import Evidences

---

## 8. Implementation Priority

### P0: Fix entity_id Gap (CRITICAL)

**Files to modify:**
1. `reflection_service.py`: approve_proposal() — extract entity_id from evidence_chain
2. `proposal_repository.py`: Add entity lookup helper

**Migration:**
```sql
-- Backfill entity_id for existing L1 MemoryNodes
WITH candidate_entities AS (
    SELECT c.id as candidate_id, c.entity_id
    FROM candidates c
    WHERE c.entity_id IS NOT NULL
)
UPDATE memory_nodes mn
SET entity_id = ce.entity_id
FROM proposals p
JOIN candidate_entities ce ON ce.candidate_id = p.candidate_id
WHERE mn.evidence_links::text LIKE '%' || p.id::text || '%'
AND mn.entity_id IS NULL;
```

### P1: Enable entity_facts (Optional)

**Only if L1 content insufficient for L2:**
1. Create entity_facts table
2. Add trigger on L1 insert/update
3. Update EvolutionService to query entity_facts

### P2: Integrate EvolutionService (Future)

**When ready:**
1. Modify ReflectionService to call EvolutionService
2. Pass entity-level history
3. Enable L2/L3 creation

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

## 10. Summary

| Finding | Impact | Priority |
|---------|--------|----------|
| L1 MemoryNodes lack entity_id | CRITICAL — breaks all aggregation | P0 |
| Candidates have entity_id | Good — lineage preserved | ✅ |
| Proposals have entity (varchar) | Acceptable — can derive UUID | Medium |
| Relationships table empty | Low — can be populated later | P2 |
| entity_facts table not needed yet | Medium — evaluate after P0 | P1 |

**Bottom Line**: Fix entity_id first. Everything else depends on this.

---

**Audit complete. Awaiting next instructions.**
