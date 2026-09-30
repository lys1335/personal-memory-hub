# Phase 22.8 Clean Rebuild Architecture Design

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Decision

### Current State Assessment

| Metric | Value | Status |
|--------|-------|--------|
| Evidences | 15,662 | ✅ Source of truth |
| Candidates | 21,890 | ⚠️ Mixed quality |
| Proposals | 240 | ✅ Intact lineage |
| L1 MemoryNodes | 25,954 | ❌ 74.2% lack entity_id |
| L2 Patterns | 2 | ⚠️ Insufficient |
| L3 Beliefs | 0 | ❌ Never created |
| Reconstructions | 0 | ❌ Formation layer dormant |

### Architecture Conflict Identified

**Phase 20/21 Frozen Design vs Clean Rebuild Goal:**

| Aspect | Frozen Design | Clean Rebuild Need | Conflict |
|--------|--------------|-------------------|----------|
| L0→L1 Owner | ReflectionService | EvidencePipelineService | **CONFLICT** |
| L1 entity_id | Not enforced | Required | **CONFLICT** |
| Evolution trigger | Manual/API | Cron-integrated | **CONFLICT** |
| Cross-batch aggregation | Not implemented | Required for L2/L3 | **CONFLICT** |

**Verdict**: Clean Rebuild requires architectural changes that conflict with Phase 20/21 frozen boundary. These conflicts must be explicitly approved before implementation.

---

## 1. Final L0→L1 Boundary

### Comparative Analysis

#### Option A: Current Architecture (ReflectionService owns L0→L1)

```
Evidence → [Cron] → ReflectionService
                            ↓
                      Candidate (derived)
                            ↓
                      Proposal
                            ↓
                      L1 MemoryNode
```

**Pros:**
- Existing production pipeline
- Proven stability
- No architectural change

**Cons:**
- L1 lacks entity_id (confirmed bug)
- No Formation layer (Reconstruction empty)
- EvidencePipelineService dormant
- Entity aggregation impossible without fix

---

#### Option B: EvidencePipelineService owns L0→L1

```
Evidence → EvidencePipelineService
                    ↓
              ContextWindow
                    ↓
              Interpretation
                    ↓
              FormationService
                    ↓
              Reconstruction + Candidate
                    ↓
              [Optional: EvolutionService]
                    ↓
              L1 MemoryNode (direct)
```

**Pros:**
- Clean separation: Formation vs Evolution
- Reconstruction layer restored
- Entity resolution at Formation time
- L1 creation with proper entity_id

**Cons:**
- Requires significant code changes
- Breaks Phase 20/21 frozen boundary
- EvolutionService needs enhancement
- Risk of dual pipeline confusion

---

#### Option C: Unified Pipeline (Hybrid)

```
Evidence → EvidencePipelineService (Formation)
                    ↓
              Candidate (with entity_id)
                    ↓
ReflectionService (Evolution coordination)
                    ↓
              L1 → L2 → L3 (via EvolutionService)
```

**Pros:**
- Best of both worlds
- Clear responsibility separation
- Extensible architecture
- Minimal change to existing code

**Cons:**
- Requires integration work
- Need to decide transaction boundaries
- Potential service coordination complexity

---

### **RECOMMENDED: Option C (Unified Pipeline)**

**Rationale:**

1. **EvidencePipelineService** handles Formation (Evidence → Candidate)
   - Resolves entity_id at Formation time
   - Creates Reconstruction (restores dormant layer)
   - Produces well-structured Candidate

2. **ReflectionService** handles L1 Evolution (Candidate → L1)
   - Aggregates facts across candidates
   - Generates Proposals
   - Creates L1 MemoryNodes WITH entity_id

3. **EvolutionService** handles L2+ Evolution (L1 → L2 → L3)
   - Receives entity-level L1 history
   - Applies threshold logic
   - Creates Pattern/Belief MemoryNodes

---

## 2. Final Component Responsibilities

### EvidencePipelineService

| Aspect | Specification |
|--------|--------------|
| **Input** | evidence_id, workspace_id |
| **Output** | candidate_id, reconstruction_id, topic_ids |
| **Persisted** | Candidate, Reconstruction, Topics |
| **Creates MemoryNode** | NO (only if user_owned AND Evolution called) |
| **Calls LLM** | YES (ContextWindow, Interpretation) |
| **Batch** | NO (single evidence processing) |
| **Cross-history** | NO |
| **Transaction owner** | YES |
| **Cron callable** | NO (API-only) |

**Final Duty**: Formation — transform raw Evidence into structured Candidate with proper entity linkage.

---

### ReflectionService

| Aspect | Specification |
|--------|--------------|
| **Input** | workspace_id, optional entity_id, limit |
| **Output** | ReflectionExecutionResult |
| **Persisted** | Proposals, L1 MemoryNodes |
| **Creates MemoryNode** | YES (L1 Observation only) |
| **Calls LLM** | YES (fact extraction, proposal generation) |
| **Batch** | YES (processes multiple candidates) |
| **Cross-history** | NO (currently) |
| **Transaction owner** | YES |
| **Cron callable** | YES |

**Final Duty**: L1 Evolution — aggregate candidates into confirmed Observations.

---

### EvolutionService

| Aspect | Specification |
|--------|--------------|
| **Input** | candidate_id OR entity_id (for aggregation) |
| **Output** | EvolutionResult |
| **Persisted** | L2/L3 MemoryNodes, Relationships |
| **Creates MemoryNode** | YES (L2 Pattern, L3 Belief) |
| **Calls LLM** | YES (pattern detection) |
| **Batch** | Optional (can process entity history) |
| **Cross-history** | YES (queries historical L1 nodes) |
| **Transaction owner** | NO (caller manages) |
| **Cron callable** | YES (when integrated) |

**Final Duty**: Advanced Evolution — create L2/L3 from L1 history.

---

### Candidate

| Aspect | Specification |
|--------|--------------|
| **Role** | Lineage carrier, processing intermediate |
| **Pyramid Level** | NOT A NODE |
| **Lifetime** | Until L1 creation, then archive |
| **Persisted** | YES (for lineage) |
| **Created by** | FormationService (via EvidencePipelineService) |
| **Consumed by** | ReflectionService |
| **Archived after** | 30 days or L1 creation |

**Final Position**: Transient lineage object, NOT a Memory Pyramid level.

---

## 3. Final Memory Pyramid

```
┌─────────────────────────────────────────────────────────────┐
│                     MEMORY PYRAMID                          │
├────────┬──────────────────┬──────────────┬──────────────────┤
│ Level  │ Node Type        │ Input        │ Creation Method  │
├────────┼──────────────────┼──────────────┼──────────────────┤
│ L0     │ Evidence         │ Raw input    │ Import/API       │
│        │                  │              │ (append-only)    │
├────────┼──────────────────┼──────────────┼──────────────────┤
│ L1     │ Observation      │ Candidates   │ ReflectionService│
│        │                  │              │ (batch evolution)│
├────────┼──────────────────┼──────────────┼──────────────────┤
│ L2     │ Pattern          │ L1 history   │ EvolutionService │
│        │                  │ (entity agg) │ (threshold-based)│
├────────┼──────────────────┼──────────────┼──────────────────┤
│ L3     │ Belief           │ L2 history   │ EvolutionService │
│        │                  │ (cross-entity)│ (threshold-based)│
└────────┴──────────────────┴──────────────┴──────────────────┘

NOT PART OF PYRAMID:
- Candidate: Processing intermediate (transient)
- Proposal: Decision object (transient after approval)
- Reconstruction: Formation intermediate (archived)
- Topic: Metadata index (not a memory node)
```

### Immutability Rules

| Level | Append-only | Update allowed | Delete allowed |
|-------|-------------|----------------|----------------|
| L0 Evidence | ✅ Yes | ❌ No | ❌ No (soft delete only) |
| L1 Observation | ✅ Yes | ⚠️ Rare | ❌ No |
| L2 Pattern | ✅ Yes | ❌ No | ❌ No |
| L3 Belief | ✅ Yes | ❌ No | ❌ No |

**Rationale**: Higher levels are abstractions of lower levels. Changing them breaks lineage.

---

## 4. L1 Entity Lineage Model

### Final Decision: Single entity_id + Relationship Support

**Why single entity_id:**
- 100% of current L1 nodes have single-entity content pattern
- Content prefix extraction shows clear entity: fact structure
- Simpler queries and aggregation

**How to handle multi-entity L1 (future):**
- Use `memory_relationships` to link L1 to multiple entities
- Use `topic_links` for topic-based association
- entity_id field remains primary, relationships provide flexibility

### Required Field Changes

| Table | Field | Current | Required | Action |
|-------|-------|---------|----------|--------|
| memory_nodes | entity_id | NULLABLE, often NULL | NOT NULL for L1+ | Fix in code + backfill |
| proposals | entity_id | MISSING | Optional (for traceability) | Add if needed |
| candidates | entity_id | ✅ Present | ✅ Keep | No change |

### Lineage Chain (Future State)

```
Evidence (entity_id)
    ↓
Candidate (entity_id) ← FormationService resolves this
    ↓
Proposal (entity_id from candidate)
    ↓
L1 MemoryNode (entity_id from proposal/candidate) ← FIX REQUIRED
    ↓
L2 Pattern (entity_id from L1 aggregation)
    ↓
L3 Belief (entity_id from L2 aggregation)
```

---

## 5. Candidate Lifecycle

### State Machine

```
                    ┌─────────────┐
                    │   PENDING   │ ← Created by FormationService
                    └──────┬──────┘
                           │
              Proposal generated
                           │
                    ┌──────▼──────┐
                    │  CONFIRMED  │ ← L1 created, archived
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  ARCHIVED   │ ← After 30 days
                    └─────────────┘
                    
                    ┌─────────────┐
                    │  ORPHANED   │ ← Proposal rejected
                    └─────────────┘
```

### Retention Policy

| Status | Retention | Action |
|--------|-----------|--------|
| PENDING | Until proposal generated | Keep for lineage |
| CONFIRMED | 30 days after L1 creation | Archive |
| ORPHANED | 7 days | Delete |
| ARCHIVED | Permanent (read-only) | Keep for audit |

---

## 6. Proposal Lifecycle

### State Machine

```
                    ┌─────────────┐
                    │   PENDING   │ ← Created by ReflectionService
                    └──────┬──────┘
                           │
              Auto-approve or manual review
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │  APPROVED │ │REJECT │ │  REVISED  │
        └─────┬─────┘ └───┬───┘ └─────┬─────┘
              │            │            │
        L1 created    Orphaned     Re-evaluate
```

### Retention Policy

| Status | Retention | Reason |
|--------|-----------|--------|
| PENDING | Until decision | Required for workflow |
| APPROVED | Permanent | Audit trail for L1 |
| REJECTED | 90 days | Dispute resolution |
| REVISED | Until final decision | Workflow state |

---

## 7. Derived Data Classification

### KEEP (Must Preserve)

| Table | Rows | Reason |
|-------|------|--------|
| workspace | 2 | Tenant isolation |
| user_profiles | 0 | User management |
| areas | 3,732 | Spatial context |
| entities | 4,609 | Semantic anchors |
| evidences | 15,662 | Source of truth |

### REBUILD (Can Regenerate)

| Table | Rows | Reason |
|-------|------|--------|
| candidates | 21,890 | Regenerable from Evidence |
| proposals | 240 | Regenerable from Candidates |
| memory_nodes | 25,954 | Regenerable from Candidates |
| reconstructions | 0 | Regenerable from Evidence |

### ARCHIVE (Keep for Audit)

| Table | Rows | Reason |
|-------|------|--------|
| proposals_backup_20260812 | 364 | Historical reference |
| memory_relationships | 0 | Future use |
| topics | 0 | Future use |
| topic_links | 0 | Future use |

### DELETE (Safe to Remove)

| Table | Rows | Reason |
|-------|------|--------|
| archives | - | Empty/stale |
| tags | 0 | Unused |
| tag_links | 0 | Unused |
| relationships | 0 | Unused |
| tasks | - | Transient |
| vector_documents | - | Rebuildable |

---

## 8. Clean Rebuild Plan

### Phase 0: Pre-Rebuild Validation

```
Step 0.1: Freeze Cron (stop new data ingestion)
Step 0.2: Backup all derived tables
Step 0.3: Validate Evidence integrity (all 15,662 evidences valid)
Step 0.4: Verify workspace/user/area/entity consistency
```

### Phase 1: Architecture Fix

```
Step 1.1: Modify EvidencePipelineService
         - Enable Formation layer for Cron
         - Ensure entity_id resolution at Formation time
         
Step 1.2: Modify ReflectionService
         - Fix approve_proposal() to set entity_id from Candidate
         - Add entity_id parameter passing
         
Step 1.3: Modify EvolutionService
         - Add evolve_entity_history(entity_id) method
         - Enable multi-L1 aggregation
```

### Phase 2: Data Cleanup

```
Step 2.1: Rename current tables (backup)
         candidates → candidates_backup_20260814
         proposals → proposals_backup_20260814
         memory_nodes → memory_nodes_backup_20260814
         reconstructions → reconstructions_backup_20260814
         
Step 2.2: Truncate derived tables
         TRUNCATE candidates, proposals, memory_nodes, reconstructions
         
Step 2.3: Verify cleanup (only evidences/entities/areas remain)
```

### Phase 3: Rebuild from Evidence

```
Step 3.1: Batch process Evidences through EvidencePipelineService
         - Process 100 evidences per batch
         - Create Candidates with proper entity_id
         - Log progress for monitoring
         
Step 3.2: Run ReflectionService on new Candidates
         - Generate Proposals
         - Create L1 MemoryNodes with entity_id
         - Validate lineage at each step
         
Step 3.3: Run EvolutionService for L2/L3
         - Aggregate L1 by entity
         - Create L2 Patterns where threshold met
         - Create L3 Beliefs where applicable
```

### Phase 4: Validation

```
Step 4.1: Lineage validation
         - Verify all L1 have entity_id
         - Verify all L1 link to Candidates
         - Verify all Candidates link to Evidences
         
Step 4.2: Data quality check
         - Compare counts with pre-rebuild
         - Validate content quality (sample)
         - Check entity distribution
         
Step 4.3: Regression tests
         - Run Phase 20/21 test suite
         - Verify no functionality loss
```

### Phase 5: Go-Live

```
Step 5.1: Enable Cron with new pipeline
Step 5.2: Monitor for 24 hours
Step 5.3: Archive backup tables
Step 5.4: Document changes
```

---

## 9. Rollback Plan

### Trigger Conditions
- Data corruption detected
- Lineage integrity failure
- Performance degradation > 50%
- Business critical bug discovered

### Rollback Steps
```
Step R1: Stop Cron
Step R2: Restore from backup
        - Rename backup tables to active
        - Drop rebuilt tables
Step R3: Verify restore integrity
Step R4: Resume Cron with original configuration
Step R5: Post-mortem analysis
```

---

## 10. Validation Gates

### Gate 1: Pre-Rebuild
- [ ] Evidence count verified (15,662)
- [ ] Entity count verified (4,609)
- [ ] Backup completed
- [ ] Rollback plan tested

### Gate 2: Post-Cleanup
- [ ] Only base tables remain (workspace, user_profiles, areas, entities, evidences)
- [ ] No orphaned references
- [ ] FK integrity maintained

### Gate 3: Post-Rebuild
- [ ] All L1 have entity_id
- [ ] All L1 link to valid Candidates
- [ ] All Candidates link to valid Evidences
- [ ] Lineage depth = 3 (Evidence → Candidate → L1)

### Gate 4: Post-L2
- [ ] L2 Patterns have entity_id
- [ ] L2 link to multiple L1 nodes
- [ ] L2 content is aggregated summary

### Gate 5: Production
- [ ] Cron running successfully
- [ ] No UniqueViolation errors
- [ ] Memory growth stable
- [ ] Query performance acceptable

---

## 11. Phase 20/21 Frozen Boundary Impact

### Conflicts Identified

| ID | Conflict | Severity | Resolution Required |
|----|----------|----------|---------------------|
| FC-001 | EvidencePipelineService must be activated | HIGH | User approval |
| FC-002 | L1 entity_id enforcement | HIGH | Schema/code change |
| FC-003 | EvolutionService integration | MEDIUM | Code change |
| FC-004 | Cross-batch aggregation logic | MEDIUM | New feature |
| FC-005 | Candidate lifecycle management | LOW | Enhancement |

### Frozen Code Exceptions Required

1. **reflection_service.py:248-250**
   ```python
   # Current (frozen):
   entity_id = None
   
   # Required change:
   candidate = await self._candidate_repo.find_by_id(prop['candidate_id'])
   entity_id = candidate.entity_id if candidate else None
   ```

2. **evidence_pipeline_service.py:Cron integration**
   - Currently API-only
   - Required: Enable for Cron processing

3. **evolution_service.py:Multi-L1 support**
   - Currently single-candidate input
   - Required: Entity-history aggregation

---

## 12. Open Design Questions

### Q1: Should entity_facts table be added?

**Analysis**:
- L1 MemoryNodes already contain entity-specific facts
- Aggregation can query L1 directly by entity_id
- entity_facts would duplicate L1 content

**Recommendation**: NOT NEEDED initially. Add only if:
- L1 content too verbose for L2 input
- Performance issues with direct L1 aggregation
- Need for fact-level confidence tracking

---

### Q2: How to handle 74.2% orphaned L1?

**Options**:
A. Keep as-is (entity_id = NULL) — loses aggregation capability
B. Attempt content-based recovery — risk of misattribution
C. Delete and regenerate — maximum data loss

**Recommendation**: OPTION A (Keep as-is)
- Preserve historical record
- New L1 will have correct entity_id
- Gradual transition as old L1 ages out

---

### Q3: Should old Candidates be preserved?

**Analysis**:
- Old Candidates (pre-rebuild) have mixed quality
- Some have entity_id, some don't
- Lineage may be broken

**Recommendation**: ARCHIVE, not delete
- Rename table: candidates → candidates_pre_rebuild_backup
- Keep for audit/debugging
- Do not use in production

---

### Q4: Transaction boundary for rebuild?

**Options**:
A. Single transaction for all evidence processing
B. Batch transactions (100 evidences each)
C. Individual transactions per evidence

**Recommendation**: OPTION B (Batch transactions)
- Balance between performance and safety
- Allows progress monitoring
- Enables rollback at batch level

---

## 13. Final Verdict

### REBUILD READY: **NO**

### Blocking Issues

| # | Issue | Status | Required Action |
|---|-------|--------|-----------------|
| 1 | Phase 20/21 frozen code conflicts | ❌ BLOCKED | User approval for exceptions |
| 2 | EvidencePipelineService activation | ❌ BLOCKED | Design decision required |
| 3 | Entity_facts necessity | ⚠️ UNRESOLVED | Performance testing needed |
| 4 | Rollback testing | ❌ BLOCKED | Must test before rebuild |

### Prerequisites for Rebuild

```
[ ] User approval for Phase 20/21 code exceptions
[ ] Architecture Conflict resolution (FC-001 to FC-005)
[ ] Rollback plan tested in staging
[ ] Performance baseline established
[ ] Stakeholder communication completed
```

---

## 14. Alternative: Selective Repair (Strategy A)

If Clean Rebuild is blocked, Alternative Strategy A remains viable:

### What Strategy A Does
1. Fix entity_id in ReflectionService (3-line code change)
2. Backfill 6,702 recoverable L1 nodes via SQL
3. Enhance EvolutionService for multi-L1 aggregation
4. Enable L2/L3 creation without full rebuild

### What Strategy A Sacrifices
- 19,250 L1 remain without entity_id
- No Reconstruction layer restoration
- No EvidencePipelineService activation

### When to Choose Strategy A
- Frozen code cannot be modified
- Rebuild risk too high
- Quick win needed for L2/L3 activation

---

## 15. Summary

| Aspect | Clean Rebuild (Strategy B) | Selective Repair (Strategy A) |
|--------|---------------------------|-------------------------------|
| L1 entity_id coverage | 100% | 25.8% |
| Architecture change | Major | Minimal |
| Downtime | Hours | Minutes |
| Risk | High | Low |
| L2/L3 enablement | Full | Partial |
| Frozen boundary impact | Multiple conflicts | None |

**Final Recommendation**: 
- If architecture purity required → Clean Rebuild (after resolving conflicts)
- If production stability priority → Selective Repair (Strategy A)

---

**Adjudication complete. Awaiting user decision on Strategy selection and frozen boundary exceptions.**
