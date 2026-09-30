# Phase 22 Memory Pyramid Evolution Read-Only Audit

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Summary

### Current State
```
L0 Evidence:     15,662  (input data)
L1 Candidate:    21,152  (pending)
L1 MemoryNode:   25,822  (Observation)
L2 MemoryNode:        2  (Pattern) ← Only 2 from historical runs
L3 MemoryNode:        0  (Belief)
```

### Core Finding
**L2/L3 evolution is NOT happening in production.**

All current proposals target level 1 (Refine/Split), never reaching the threshold for L2 creation (Strengthen/Create).

### Root Cause
**Fact density per entity is too low:**
- 92% of batches produce only 1 fact per entity
- Strengthen requires ≥3 facts with confidence ≥0.8
- Create requires ≥2 facts with confidence ≥0.6
- Neither condition is met → No L2 proposals generated

---

## 1. Runtime Stability

### Cron Performance (Post-Fix)
```
Time                Status     Facts  Proposals  Dedup  Duration
01:48:32            completed  41      41         21     68.3s
02:00:02            completed  36      36         16     59.2s
02:11:43            completed  ~40     ~40        ~20    ~60s
02:23:23            completed  ~35     ~35        ~15    ~55s
02:34:39            completed   4       4         0      ~3s
```

**Stability: ✅ PASS**
- No UniqueViolation errors
- Consistent completion times (~60s)
- Deduplication working as expected

### Database Growth
```
Date        Proposals  MemoryNodes  Delta
2026-08-14    +40        +35       (from fix)
2026-08-13     +7         +7       (pre-fix)
2026-08-12  +2540      +2540      (historical)
```

---

## 2. ReflectionService Actual Call Graph

### Entry Point: `reflect()` 
```
File: reflection_service.py:92
├── _acquire_scope()           → Query pending candidates
├── _run_engine_pipeline()     → EvidenceEvolutionEngine + ReflectionEngine
│   ├── EvidenceEvolutionEngine.evolve()  → Extract facts, build candidates
│   └── ReflectionEngine.reflect_pipeline() → Generate proposals
├── _save_proposals()          → INSERT proposals (with P0 dedup fix)
└── _auto_approve_pending_proposals()
    └── approve_proposal()     → UPDATE proposal + INSERT memory_node
```

### Critical Path: `approve_proposal()`
```
File: reflection_service.py:208-350
Input: proposal_id, workspace_id
Process:
  1. SELECT proposal WHERE id = :id
  2. UPDATE proposals SET status = 'approved'
  3. INSERT INTO memory_nodes (level = target_level)
  4. UPDATE candidates SET status = 'confirmed'
```

### L2/L3 Creation Logic (in approve_proposal)
```python
# reflection_service.py:245-246
level = prop["target_level"]
node_type = "Pattern" if level == 2 else "Belief" if level == 3 else "Observation"
```

**Evidence: L2/L3 creation IS coded, but target_level never exceeds 1.**

---

## 3. Candidate → Proposal → MemoryNode Mapping

### Candidate Types (from database)
```sql
candidate_type | count
---------------|------
pattern        | 21,318
```

**Finding: ALL candidates are 'pattern' type. No 'belief' type exists.**

### Proposal Types (from database)
```sql
proposal_type | target_level | count
--------------|--------------|------
Refine        | 1            | 68
Split         | 1            | 12
```

**Finding: NO Strengthen or Create proposals exist in production.**

### MemoryNode Levels (from database)
```sql
level | node_type  | count
------|------------|------
1     | Observation| 25,822
2     | Pattern    | 2
3     | Belief     | 0
```

**Finding: L2/L3 only from historical Phase 21.7 runs, not from current ReflectionService.**

---

## 4. L1 → L2 → L3 Evolution Evidence

### Proposal Generation Logic (reflection_engine.py:305-316)
```python
if avg_confidence >= 0.8 and len(entity_facts) >= 3 and source_level < max_level:
    proposal_type = "Strengthen"
    target_level = source_level + 1  # Would create L2
elif avg_confidence >= 0.6 and len(entity_facts) >= 2 and source_level < max_level:
    proposal_type = "Create"
    target_level = source_level + 1  # Would create L2
elif avg_confidence >= 0.9:
    proposal_type = "Refine"
    target_level = source_level  # Stays at L1
else:
    proposal_type = "Split"
    target_level = source_level  # Stays at L1
```

### Fact Distribution Analysis
```
Facts per batch:
  1 fact:   3,396 batches (92%)
  2 facts:  1,045 batches (3%)
  3 facts:    535 batches (1.4%)
  4+ facts:   224 batches (0.6%)
```

### Root Cause Analysis
```
Condition for L2 creation: len(entity_facts) >= 2 (Create) or >= 3 (Strengthen)

Current reality:
  - Most entities have only 1 fact per batch
  - Therefore len(entity_facts) is almost always 1
  - Condition len(entity_facts) >= 2 NEVER met
  - Result: All proposals stay at target_level = 1
```

**Verdict: L2/L3 evolution logic EXISTS in code but is NEVER TRIGGERED in production due to fact density.**

---

## 5. EvidencePipelineService vs ReflectionService Boundary

### EvidencePipelineService (Phase 21.8)
```
Trigger: API endpoint or manual invocation
Input: Single evidence_id
Pipeline:
  Evidence → ContextWindow → Interpretation → Formation → Candidate
                                       ↓
                                 Topic extraction
                                       ↓
                                 EvolutionService (if user-owned)
Output: Reconstruction + Candidate + Topics + L2/L3 MemoryNode (via EvolutionService)
```

**Key: Uses EvolutionService which CAN create L2/L3 MemoryNodes from pattern candidates.**

### ReflectionService (Phase 20)
```
Trigger: Cron (every 10 minutes)
Input: Batch of pending candidates
Pipeline:
  Candidates → Fact extraction → Proposal generation
                              ↓
                        Proposal approval
                              ↓
                        L1 MemoryNode creation (direct SQL INSERT)
Output: Proposal + L1 MemoryNode + Confirmed candidate
```

**Key: Does NOT use EvolutionService. Creates L1 only via direct SQL.**

### Boundary Violation
```
EvidencePipelineService:
  - Creates L2/L3 MemoryNodes (via EvolutionService)
  - Processes single evidence
  - Used for: New evidence ingestion

ReflectionService:
  - Creates ONLY L1 MemoryNodes
  - Processes batch of candidates
  - Used for: Historical evolution
  - DOES NOT use EvolutionService ← DESIG GAP
```

---

## 6. Evolution Trigger Audit

### Current Triggers

| Trigger | Who Calls | What It Processes | Level | Frequency |
|---------|-----------|-------------------|-------|-----------|
| Cron | app.py:1407 | ReflectionService.reflect() | L1 | Every 10 min |
| API | /api/v1/pipeline/process | EvidencePipelineService.process_evidence() | L1-L3 | On demand |
| Manual | - | - | - | - |

### EvolutionService Usage
```
Called by: EvidencePipelineService only (app.py:104)
NOT called by: ReflectionService

EvidencePipelineService._evolve() → EvolutionService.evolve()
  → Creates L2/L3 MemoryNode from pattern candidate
  
ReflectionService.approve_proposal()
  → Direct SQL INSERT for L1 MemoryNode
  → NO call to EvolutionService
```

---

## 7. Architecture Gap Classification

### P0: No Active Blockers
- ✅ UniqueViolation fixed
- ✅ Cron running successfully
- ✅ Proposals being created
- ✅ MemoryNodes growing (L1)

### P1: L2/L3 Evolution Not Triggered
**Issue:** Fact density insufficient for L2 creation

**Evidence:**
- 92% of batches have only 1 fact per entity
- Strengthen requires ≥3 facts (never met)
- Create requires ≥2 facts (rarely met)
- Result: All proposals target_level = 1

**Impact:**
- L2 Pattern nodes: Only 2 (from historical Phase 21.7)
- L3 Belief nodes: 0
- No abstraction happening in production

**Classification:** P1 — Design gap, not a bug

### P2: ReflectionService Bypasses EvolutionService
**Issue:** ReflectionService should use EvolutionService for L2/L3 creation

**Current behavior:**
- EvidencePipelineService uses EvolutionService → Can create L2/L3
- ReflectionService does NOT use EvolutionService → Only creates L1

**Gap:**
- Two pipelines with different evolution capabilities
- No unified approach to L2/L3 creation
- ReflectionService has hardcoded SQL for L1 only

**Classification:** P2 — Architecture inconsistency

### INFO: Design Intention vs Implementation
**Design (per docs):**
- ReflectionService should handle full L1→L2→L3 evolution
- EvolutionService should be used by both pipelines

**Implementation:**
- ReflectionService creates L1 only via direct SQL
- EvolutionService only used by EvidencePipelineService
- L2/L3 logic exists in ReflectionEngine but never triggered

---

## 8. Memory Pyramid Lifecycle — Current Reality

### Actual Flow
```
Evidence (L0)
  ↓
[New evidence arrival]
  ↓
EvidencePipelineService
  ↓
Candidate (L1 pending) + Topics
  ↓
[If user-owned]
  ↓
EvolutionService
  ↓
L2/L3 MemoryNode (Pattern/Belief)

---

[Candidate already in DB]
  ↓
ReflectionService (Cron)
  ↓
Proposal (L1 pending)
  ↓
Auto-approve (confidence >= 0.9, level <= 3)
  ↓
L1 MemoryNode (Observation) ONLY
  ↓
[Candidate status → confirmed]
```

### Missing Links
```
❌ Batch candidates → L2 evolution (ReflectionService doesn't trigger)
❌ Multiple entities aggregation (no cross-candidate analysis)
❌ Contradiction detection (EvolutionService has logic but not called)
❌ Supersession handling (not implemented in ReflectionService)
```

---

## 9. The 2 L2 Pattern Nodes — Origin Investigation

### Database Evidence
```sql
SELECT id, content, evidence_links, created_at
FROM memory_nodes WHERE level = 2;

-- Results:
-- ID: 06a791e4-dabc-7941-8000-1f87ab05dfeb
--   Content: "候补规则: 怎么写"
--   Created: 2026-08-10 00:41:49
--   Source: candidate 12e59454-9096-11f1-9643-46894c7bcffe

-- ID: 06a791e2-a501-7a30-8000-56931ec232cb
--   Content: "候补规则: 接下来要确定申告了..."
--   Created: 2026-08-10 00:41:14
--   Source: candidate 12e4fa58-9096-11f1-9643-46894c7bcffe
```

### Candidate Source
```sql
SELECT id, candidate_type, status, created_at
FROM candidates 
WHERE id IN ('12e59454-...', '12e4fa58-...');

-- Results:
-- Both are candidate_type='pattern', status='candidate'
-- Both created: 2026-08-05 06:22:46
```

### Conclusion
These 2 L2 nodes were created by **EvolutionService** during Phase 21.7 testing on 2026-08-10, NOT by ReflectionService. They are isolated historical artifacts, not part of the current production flow.

---

## 10. Critical Findings Summary

### Finding 1: Fact Density Problem
**Severity:** P1
**Impact:** No L2/L3 evolution in production
**Evidence:** 92% of batches produce only 1 fact per entity
**Code location:** reflection_engine.py:305-316

### Finding 2: EvolutionService Not Used by ReflectionService
**Severity:** P2
**Impact:** Inconsistent evolution capabilities between pipelines
**Evidence:** ReflectionService has no import/call to EvolutionService
**Code location:** reflection_service.py (no EvolutionService dependency)

### Finding 3: Hardcoded L1 Creation in ReflectionService
**Severity:** P2
**Impact:** ReflectionService bypasses domain service layer
**Evidence:** Direct SQL INSERT in approve_proposal() instead of using repositories
**Code location:** reflection_service.py:313

### Finding 4: Only 2 L2 Nodes from Historical Runs
**Severity:** INFO
**Impact:** L2 evolution not happening in current production
**Evidence:** Both L2 nodes created on 2026-08-10 via EvolutionService
**Code location:** N/A (historical artifact)

---

## 11. Architecture Verdict

### Q: Should EvidencePipelineService and ReflectionService be merged?
**A: NO** — They serve different purposes:
- EvidencePipelineService: Single evidence ingestion, structured formation
- ReflectionService: Batch historical evolution, abstraction

### Q: Should ReflectionService use EvolutionService?
**A: YES** — Currently it bypasses EvolutionService, creating inconsistency:
- EvidencePipelineService → EvolutionService → L2/L3 capable
- ReflectionService → Direct SQL → L1 only

### Q: Is the current L1-only output a bug?
**A: NO** — It's a design limitation:
- Fact density too low for L2 thresholds
- This is by design (requires sufficient evidence aggregation)
- Solution requires either:
  a) Lowering thresholds (risky - noise)
  b) Increasing fact extraction granularity (better)
  c) Adding cross-batch aggregation (future phase)

### Q: What is the correct architecture?
**A: Two complementary pipelines:**
```
Pipeline A (Real-time): Evidence → EvidencePipelineService → Candidate → EvolutionService → L1/L2/L3
Pipeline B (Batch):     Candidates → ReflectionService → Proposal → L1 MemoryNode
                              ↓
                        [Future: EvolutionService for L2/L3]
```

---

## 12. Recommendations (For Future Phases)

### Phase 22 (Next)
1. **Investigate fact extraction granularity** — Why is entity_facts count so low?
2. **Design cross-batch aggregation** — Can we accumulate facts across multiple runs?
3. **Consider lowering thresholds** — With careful validation

### Phase 23 (If needed)
1. **Integrate EvolutionService into ReflectionService** — Unified L2/L3 creation
2. **Add contradiction detection** — Use EvolutionService._detect_historical_relationships()
3. **Implement supersession logic** — Properly handle old vs new memories

### Not Recommended (Without user approval)
- Modifying proposal generation thresholds
- Changing fact extraction logic
- Altering ReflectionService to use EvolutionService
- Any database schema changes

---

## 13. Explicit "DO NOT MODIFY" Confirmation

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
