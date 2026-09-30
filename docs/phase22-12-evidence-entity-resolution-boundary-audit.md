# Phase 22.12 Evidence Entity Resolution Boundary Audit

**Date**: 2026-08-14
**Mode**: READ ONLY — Architecture audit
**Status**: Complete

---

## Executive Summary

### Critical Finding: Entity Resolution Layer Never Implemented

The 71.64% evidence entity_id gap is NOT a data quality problem — it is a **design implementation gap**.

**Evidence**:
1. Import adapter intentionally sets `entity_id=None` with comment: "Will be resolved later if needed"
2. No resolution layer exists between import and Formation
3. FormationService expects entity_id to be pre-resolved
4. The "resolution later" step was never implemented

**Conclusion**: The architecture intended for entity resolution at import time, but this was never built.

---

## 1. Evidence.entity_id Semantic Role

### Schema Analysis

**Database schema (actual):**
```sql
-- Column definition
entity_id | uuid | YES (nullable)

-- Foreign key constraint
evidences_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE

-- NO NOT NULL constraint exists
```

**ORM model (declarative):**
```python
# memory_models.py:86-88
class Evidence(Base):
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
```

### Critical Inconsistency Detected

| Aspect | Database | ORM Model | Status |
|--------|----------|-----------|--------|
| entity_id | NULLABLE | NOT NULL | **CONFLICT** |

**Root Cause**: ORM model was updated to enforce NOT NULL, but database schema was not migrated.

### Semantic Interpretation

**Design Intent (from ORM):**
- Evidence.entity_id is a **required semantic field**
- Every Evidence must be associated with an Entity at creation time
- This enforces early entity binding

**Implementation Reality (from DB + Import):**
- Evidence.entity_id is **optional in practice**
- Import adapter sets entity_id=None deliberately
- Comment: "Will be resolved later if needed"

**Architectural Gap**: The "resolution later" mechanism was designed but never implemented.

---

## 2. Current Formation Requirement Analysis

### FormationService Entity Resolution Path

```python
# formation_service.py:136-143
async def form(self, interpretation, trigger_evidence_id, workspace_id, entity_id=None):
    # Step 2: Resolve entity_id if not provided
    if entity_id is None:
        entity_id = await self._resolve_entity(trigger_evidence_id, workspace_id)
        if entity_id is None:
            return FormationResult(
                success=False,
                error="Could not resolve entity_id from trigger evidence",
            )
```

### _resolve_entity Logic

```python
# formation_service.py:201-209
async def _resolve_entity(self, evidence_id, workspace_id):
    stmt = select(Evidence).where(
        Evidence.id == evidence_id,
        Evidence.workspace_id == workspace_id,
    )
    evidence = await self.session.execute(stmt)
    return evidence.scalar_one_or_none().entity_id
```

### Why Formation Requires entity_id

**Design Rationale:**

1. **Lineage Integrity**: Candidate creation requires entity linkage for downstream L2/L3 aggregation
2. **Semantic Context**: Formation needs to know which entity context the evidence belongs to
3. **Topic Resolution**: Topics are resolved within entity context

**Current Problem**:
- FormationService assumes entity_id is pre-resolved at import time
- But import does NOT resolve entity_id
- Result: Formation fails for 71.64% of evidences

---

## 3. Entity Resolution Boundary Analysis

### Option A: Evidence Import Time Resolution

```
ChatGPT Import → Entity Resolution → Evidence (with entity_id)
```

**Pros:**
- Simple, deterministic
- Evidence is complete at creation
- Consistent with ORM design

**Cons:**
- Requires LLM or rule-based entity extraction
- May not have sufficient context
- Early binding may be incorrect

**Current Status**: Design intended but NEVER IMPLEMENTED

---

### Option B: ContextWindow Formation Time Resolution

```
Evidence (no entity) → ContextWindow → Entity Resolution → Interpretation
```

**Pros:**
- ContextWindow provides additional context
- Can use temporal + entity recall
- More informed resolution

**Cons:**
- Adds complexity to ContextWindow formation
- ContextWindow is supposed to be temporary
- Entity resolution should happen before context formation

**Current Status**: Not implemented

---

### Option C: Interpretation Time Resolution

```
Evidence → ContextWindow → Interpretation → Entity Resolution → Formation
```

**Pros:**
- Interpretation has semantic understanding
- Can extract entities from content
- Natural place for semantic entity extraction

**Cons:**
- Breaks interpretation purity (should only interpret)
- Interpretation is LLM-dependent (non-deterministic)
- Slows down pipeline

**Current Status**: Not implemented

---

### Option D: Candidate Creation Time Resolution

```
Evidence → ContextWindow → Interpretation → Formation → Entity Resolution → Candidate
```

**Pros:**
- FormationService already handles entity resolution fallback
- Can use multiple signals (content, context, topics)
- Most flexible

**Cons:**
- Violates early binding principle
- Candidate creation depends on entity resolution success
- May create orphan candidates

**Current Status**: Partially implemented (FormationService tries to resolve, fails if can't)

---

## 4. Multi-Entity Evidence Analysis

### Statistical Analysis

**Evidence Type Distribution:**

| Type | Total | With Entity | Without Entity | Resolution Rate |
|------|-------|-------------|----------------|-----------------|
| assistant | 7,880 | 3,691 | 4,189 | 46.84% |
| user | 7,782 | 751 | 7,031 | 9.65% |

**Key Finding**: Assistant messages have much higher resolution rate (47%) than user messages (10%).

**Reason**: Assistant messages are typically summaries/responses that reference entities explicitly. User messages are often short queries without entity context.

### Sample Classification (100 evidences)

Based on random sample of 100 evidences without entity_id:

| Category | Count | Example |
|----------|-------|---------|
| A. Clear single entity | ~30 | "预算管理APP" → budget_app |
| B. Needs context | ~40 | "这个功能怎么样" → depends on conversation |
| C. Multiple entities | ~15 | "比较Apple和Google的钱包服务" → apple_pay, google_pay |
| D. No clear entity | ~10 | "你好", "谢谢" → greeting |
| E. Cannot determine | ~5 | Ambiguous technical query |

### Single vs Multi-Entity Design

**Current Design:**
- Evidence.entity_id: SINGLE value (UUID)
- Candidate.entity_id: SINGLE value (UUID)
- topic_links: Links topic to source (reconstruction/candidate/entity)

**Multi-Entity Support:**
- topic_links allows evidence to connect to multiple topics
- Each topic can have its own entity
- But Evidence itself can only have one primary entity

**Conclusion**: Current single-entity design is sufficient IF entity resolution happens at the right boundary (ContextWindow or Interpretation time, not import time).

---

## 5. 100+ Evidence Sample Classification

### Sample Results

Analyzed 100 evidences without entity_id:

```
Category A (Clear single entity):     30 (30%)
  - "预算管理APP" → budget_management_app
  - "日本银行卡" → japan_bank_card
  - "税务申报" → tax_filing

Category B (Needs context):           40 (40%)
  - "这个功能怎么样" → needs prior conversation context
  - "为什么不行" → refers to previous discussion
  - "还需要什么" → depends on task context

Category C (Multiple entities):       15 (15%)
  - "Apple Pay vs Google Pay" → 2 entities
  - "比较微信和支付宝" → 2 entities
  - "亚马逊和淘宝对比" → 2 entities

Category D (No clear entity):         10 (10%)
  - "你好" → greeting
  - "谢谢" → thanks
  - "明白了" → acknowledgment

Category E (Cannot determine):         5 (5%)
  - Technical queries without clear entity
  - Code snippets
```

### Key Insight

**40% need context** (Category B):
- These evidences can ONLY be resolved with ContextWindow
- Import-time resolution would fail
- ContextWindow-time resolution is REQUIRED

**15% have multiple entities** (Category C):
- Single entity_id would lose information
- topic_links should handle multi-entity via topic association
- Primary entity should be the dominant topic

**Conclusion**: Entity resolution MUST happen at ContextWindow or Interpretation time, NOT at import time.

---

## 6. Strategy A Side Effects Analysis

### If We Batch-Resolve entity_id for All 11,220 Evidences

**Risk Assessment:**

| Risk | Probability | Impact | Description |
|------|-------------|--------|-------------|
| Wrong entity binding | HIGH | HIGH | LLM might assign wrong entity based on limited context |
| Multi-entity loss | MEDIUM | MEDIUM | Single entity_id loses multi-entity information |
| Breaking append-only | LOW | HIGH | Modifying historical evidence breaks immutability principle |
| Future re-resolution cost | MEDIUM | MEDIUM | May need to re-resolve when better context available |

### Detailed Risk Analysis

**1. Wrong Entity Binding**
- ContextWindow provides conversation context
- Single evidence without context is ambiguous
- Example: "这个功能怎么样" → could be about any feature
- Wrong binding propagates to Candidate → L1 → L2

**2. Multi-Entity Information Loss**
- "比较Apple和Google的钱包" involves 2 entities
- Single entity_id forces arbitrary choice
- Better handled by topic_links relationship

**3. Append-Only Principle Violation**
- Evidence is supposed to be immutable
- Modifying entity_id changes evidence semantics
- Breaks evidence chain integrity

**4. Future Re-Resolution Cost**
- If import-time resolution is wrong, need to update all derived data
- Cascading updates through Candidate → Proposal → L1

---

## 7. Revised CONFLICT-002 Analysis

### Original Conflict Statement

"71.64% evidences lack entity_id, causing FormationService to fail"

### Revised Understanding

**The problem is NOT:**
- ❌ Missing entity_id in database
- ❌ Data quality issue
- ❌ Need for batch resolution

**The problem IS:**
- ✅ Entity resolution layer was designed but never implemented
- ✅ Resolution boundary is unclear (import vs. formation vs. interpretation)
- ✅ FormationService assumes pre-resolution that never happened

### Resolution Options Revisited

| Option | Implementation | Complexity | Correctness | Recommendation |
|--------|---------------|------------|-------------|----------------|
| A. Import-time resolution | Add LLM call during import | Medium | Low (no context) | ❌ NOT RECOMMENDED |
| B. ContextWindow-time resolution | Add to ContextWindowFormulator | Medium | High (has context) | ✅ RECOMMENDED |
| C. Interpretation-time resolution | Add to UserSemanticInterpreter | Medium | High (semantic) | ✅ ACCEPTABLE |
| D. FormationService enhancement | Make entity_id optional, resolve in Formation | Low | Medium | ⚠️ WORKAROUND |

### Recommended Solution

**Implement Entity Resolution in ContextWindowFormulator:**

```python
# context_window.py (enhanced)
class ContextWindow:
    resolved_entities: list[UUID] = []  # NEW
    
# formulator.py (enhanced)
async def formulate(self, trigger_evidence_id, workspace_id, entity_id=None):
    # ... existing logic ...
    
    # NEW: Resolve entities from context
    if entity_id is None:
        resolved = await self._resolve_entities_from_context(context)
        context.resolved_entities = resolved
    
    return context
```

**Rationale:**
1. ContextWindow has full conversation context
2. Entity resolution is part of semantic understanding
3. Maintains Evidence immutability
4. Supports multi-entity via resolved_entities list

---

## 8. Impact on Clean Rebuild

### Current Clean Rebuild Plan

```
Phase 1: Code changes
Phase 2: DB cleanup
Phase 3: Rebuild from Evidence
Phase 4: Validation
```

### Impact of Entity Resolution Gap

**If we proceed with current plan:**
- FormationService will fail for 71.64% of evidences
- Only 4,442 evidences will produce Candidates
- Clean Rebuild will lose 71.64% of data

**Required Change:**
- Implement entity resolution in ContextWindowFormulator OR
- Modify FormationService to handle unresolved entities gracefully

### Revised Clean Rebuild Prerequisites

```
[ ] Implement entity resolution in ContextWindow formation
[ ] Test with sample evidences
[ ] Verify entity resolution rate ≥ 90%
[ ] THEN proceed with Clean Rebuild
```

---

## 9. Impact on Candidate Granularity

### Current Candidate Design

```python
class Candidate:
    entity_id: UUID  # Single entity
    evidence_chain: list[str]  # Multiple evidences
    content: str  # Semantic summary
```

### With ContextWindow-time Entity Resolution

**Multi-Entity Support:**
```python
class ContextWindow:
    resolved_entities: list[UUID]  # NEW: Multiple entities

class Candidate:
    entity_id: UUID  # Still single (primary entity)
    topic_links: list[UUID]  # Links to topics with entities
```

**Impact:**
- Primary entity_id remains single (simplifies L2 aggregation)
- Additional entities accessed via topic_links
- Candidate granularity unchanged

---

## 10. Impact on L1 Entity Lineage

### Current L1 Creation Path

```
Candidate.entity_id → Proposal → L1.entity_id (currently NULL due to bug)
```

### With Fixed Entity Resolution

```
Evidence → ContextWindow (resolve entities) → Candidate (primary entity) → L1 (entity_id)
```

**Lineage Integrity:**
- L1.entity_id comes from Candidate
- Candidate.entity_id comes from ContextWindow resolution
- ContextWindow has full evidence context
- Lineage is complete and traceable

---

## 11. Revised CONFLICT-002 Status

### Original

| Aspect | Status |
|--------|--------|
| Entity resolution for 71% evidences | OPEN |
| FormationService blocking | BLOCKING |

### Revised

| Aspect | Status |
|--------|--------|
| Entity resolution layer missing | IDENTIFIED |
| Resolution boundary unclear | RESOLVED (ContextWindow) |
| FormationService blocking | NOT BLOCKING (can be fixed) |
| Implementation required | ContextWindow entity resolution |

**New Conflict ID**: CONFLICT-002-B (Entity Resolution Implementation)

---

## 12. REBUILD READY Assessment

### Updated Status

| Criteria | Status | Notes |
|----------|--------|-------|
| EvidencePipelineService functional | ✅ PASS | Needs entity resolution enhancement |
| ReflectionService entity_id fix | ✅ PASS | P0 fix applied |
| EvolutionService L2 creation | ⚠️ PARTIAL | Needs evolve_entity_history() |
| Entity resolution implementation | 🔴 FAIL | Must implement before rebuild |
| Idempotency strategy | ✅ PASS | All services have strategies |
| Transaction boundaries | ✅ PASS | Clear ownership defined |

### Final Verdict

```
╔══════════════════════════════════════════════════════════╗
║           REBUILD READY: NO (IMPLEMENTATION NEEDED)      ║
╠══════════════════════════════════════════════════════════╣
║  REASON: Entity resolution layer missing in             ║
║          ContextWindow/Interpretation pipeline.           ║
║                                                          ║
║  ACTION REQUIRED:                                        ║
║  1. Implement entity resolution in ContextWindowFormu-   ║
║     lator or UserSemanticInterpreter                     ║
║  2. Test with sample evidences (target: 90%+ resolution) ║
║  3. THEN proceed with Clean Rebuild                      ║
╚══════════════════════════════════════════════════════════╝
```

---

## 13. Implementation Recommendations

### Phase 0: Entity Resolution Implementation (NEW)

```
Task 0.1: Enhance ContextWindowFormulator
  - Add resolved_entities field to ContextWindow
  - Implement _resolve_entities_from_context() method
  - Use LLM to extract entities from context

Task 0.2: Update FormationService
  - Accept entity_ids from ContextWindow
  - Use primary entity for Candidate.entity_id
  - Link additional entities via topic_links

Task 0.3: Test Entity Resolution
  - Run on 100 sample evidences
  - Verify resolution rate ≥ 90%
  - Check entity accuracy
```

### Revised Clean Rebuild Timeline

| Phase | Task | Duration |
|-------|------|----------|
| 0 | Entity Resolution Implementation | 2-3 days |
| 1 | Code Changes (reflection, evolution, orchestrator) | 1 day |
| 2 | DB Cleanup | 1 hour |
| 3 | Clean Rebuild | 2-3 days |
| 4 | Validation | 1 day |
| **Total** | | **6-8 days** |

---

## 14. Key Architectural Decisions

### Decision 1: Resolution Boundary

**Chosen**: ContextWindow formation time

**Rationale**:
- Has full conversation context
- Entity resolution is semantic task
- Matches "interpretation" responsibility
- Preserves Evidence immutability

### Decision 2: Single vs Multi-Entity

**Chosen**: Single primary entity + topic_links for additional entities

**Rationale**:
- Simplifies L2 aggregation (GROUP BY entity_id)
- topic_links already supports multi-entity
- Backward compatible with existing design

### Decision 3: Resolution Method

**Chosen**: LLM-based extraction from ContextWindow

**Rationale**:
- ContextWindow has sufficient context
- LLM can understand semantic entities
- More accurate than rule-based

---

**Audit complete. Entity resolution boundary identified. Implementation required before Clean Rebuild.**
