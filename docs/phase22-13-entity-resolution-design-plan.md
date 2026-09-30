# Phase 22.13 — Entity Resolution Design & Validation Plan

**Date**: 2026-08-14  
**Mode**: READ ONLY — Design and validation plan  
**Status**: Complete

---

## Executive Verdict

```
╔═══════════════════════════════════════════════════════════════════╗
║  FOR CLEAN REBUILD, ENTITY RESOLUTION MUST BECOME A FORMAL      ║
║  CAPABILITY OF THE L0→L1 FORMATION PIPELINE.                      ║
║                                                                    ║
║  RECOMMENDED BOUNDARY: ContextWindow Formation Time               ║
║  RECOMMENDED IMPLEMENTATION: New EntityResolutionService          ║
║  REQUIRED BEFORE REBUILD: YES — hard gate                         ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Core thesis**: The "resolve later" comment in the import adapter is not a postponed feature — it is an unimplemented design contract. Entity resolution must be a first-class step in the Formation pipeline, not a post-hoc reflection of already-formed candidates.

---

## 1. Full Call-Chain Audit

### Current Production Call Chain (ReflectionService path)

```
[CRON]
  ↓
ReflectionService.reflect(workspace_id, scope="daily", limit=50)
  ↓
_acquire_scope()
  → queries candidates WHERE status='candidate' AND workspace_id=X
  ↓
_run_engine_pipeline(scope, candidates, workspace_id)
  → EvidenceEvolutionEngine (LLM: fact extraction)
  → ReflectionEngine (LLM: proposal generation)
  ↓
_save_proposals(proposals, workspace_id)
  → INSERT proposals (candidate_id, entity=varchar, evidence_chain)
  ↓
_auto_approve_pending_proposals(workspace_id)
  → for each proposal: approve_proposal()
    → INSERT memory_nodes (level=1)
    → entity_id = None  ← BUG: always NULL
```

**No Formation, no ContextWindow, no Interpretation in production.**

### EvidencePipelineService Call Chain (API-only, dormant)

```
POST /pipeline/trigger { evidence_id, workspace_id }
  ↓
EvidencePipelineService.process_evidence()
  ↓
_form_context_window(evidence_id, workspace_id)
  → ContextWindowFormulator.formulate(trigger_evidence_id, workspace_id, entity_id=None)
    → _get_trigger_evidence()
    → _expand_short_confirmation()
    → _recall_temporal_context(workspace_id, entity_id=None)
    → _recall_reconstructions(workspace_id, entity_id=None)
    → _apply_budget()
  ↓
_interpret(context_window, evidence_id, workspace_id)
  → UserSemanticInterpreter.interpret(InterpretationContext)
    → role check (user vs assistant)
    → short confirmation expansion
    → direct interpretation
  ↓
_form(interpretation, evidence_id, workspace_id)
  → FormationService.form(interpretation, trigger_evidence_id, workspace_id, entity_id=None)
    → _resolve_entity(trigger_evidence_id, workspace_id)
      → SELECT entity_id FROM evidences WHERE id=evidence_id
      → returns evidence.entity_id (NULL for 71.64% of cases)
    → IF entity_id IS NULL: return Failure
    → CREATE Reconstruction
    → CREATE Candidate (entity_id set)
  ↓
_extract_topics(interpretation, formation, workspace_id)
  → TopicService.extract_topics_from_summary(semantic_summary)
    → keyword extraction + resolve_topic()
  ↓
_evolve(candidate_id, workspace_id, entity_id, topic_ids)
  → IF interpretation.user_owned: EvolutionService.evolve()
    → _detect_historical_relationships()
    → _create_memory_node(candidate)  ← creates L2/L3 directly
```

### Critical Gaps Identified

| Gap | Location | Impact |
|-----|----------|--------|
| **entity_id=None on import** | `chatgpt.py:148` | Root cause of 71.64% failure |
| **No entity resolution service** | Entire pipeline | No mechanism to resolve NULL entity_id |
| **Formation fails on NULL** | `formation_service.py:139-143` | Blocks 71.64% of evidences |
| **Direct L2 creation in pipeline** | `evidence_pipeline_service.py:162-168` | Violates L2/L3 ownership boundary |
| **Evidence.entity_id nullable in DB** | Schema vs ORM mismatch | Design inconsistency |

---

## 2. Entity Resolution Boundary Analysis

### Candidate Locations

| Location | Input | Output | LLM Cost | Context Available | Design Cleanliness |
|----------|-------|--------|----------|-------------------|-------------------|
| **Import time** | Raw evidence content | entity_id | High (per evidence) | None (single evidence) | ❌ Premature |
| **ContextWindow time** | ContextWindow (multiple evidences) | resolved_entities | Medium (batch) | Full conversation context | ✅ Recommended |
| **Interpretation time** | InterpretationContext | entity_ids | Medium (with LLM) | Semantic interpretation | ⚠️ Acceptable |
| **Formation time** | FormationService | entity_id | Low (lookup only) | Interpretation result | ❌ Too late |
| **Independent service** | Any | entities | Variable | Caller provides context | ✅ Flexible |

### Why ContextWindow Time is Optimal

**Evidence from code:**

```python
# formulator.py:90-93 — short confirmation expansion already uses context
if trigger_context.is_user_confirmation and trigger_context.is_short:
    context = await self._expand_short_confirmation(
        context, trigger_context, workspace_id, entity_id
    )
```

The ContextWindowFormulator **already has logic to expand context for ambiguous evidences**. Adding entity resolution at this point is a natural extension:

1. **Context is available**: Multiple related evidences provide semantic context
2. **Timing is correct**: Before interpretation, after context assembly
3. **Cost is efficient**: Batch resolution across context window
4. **Separation of concerns**: Formulator assembles context; resolver annotates it

### Why NOT Other Boundaries

| Boundary | Why Rejected |
|----------|-------------|
| Import time | No context available; single evidence; high LLM cost for 15K evidences; premature binding |
| Interpretation time | Interpretation is about USER INTENT, not entity discovery; mixes concerns |
| Formation time | FormationService already fails on NULL entity_id; resolution must happen BEFORE this |
| Independent service (standalone) | Valid option, but adds complexity; better integrated as part of ContextWindow pipeline |

---

## 3. Multi-Entity Analysis

### Current Data Model Limitations

```sql
-- evidences table
entity_id | uuid | (nullable in DB, required in ORM)

-- candidates table  
entity_id | uuid | NOT NULL (must have exactly one)

-- topic_links table
topic_id | uuid
source_type | varchar ('reconstruction' | 'candidate' | 'entity')
source_id | uuid
```

### Can a Single Evidence Have Multiple Entities?

**Statistical evidence from Phase 22.12 sample (100 evidences):**
- Category C (multiple entities): 15% (15/100)
- Examples: "比较Apple和Google的钱包服务", "亚马逊和淘宝对比"

**Design question**: Should Evidence.entity_id support multiple entities?

**Analysis**:

| Option | Pros | Cons | Recommended? |
|--------|------|------|-------------|
| A. Keep single entity_id, pick primary | Simple, existing schema works | Loses secondary entities | ⚠️ Partial |
| B. Add entity_links junction table | Full multi-entity support | New schema, migration | ✅ Future-proof |
| C. Use topic_links for multi-entity | Already exists, flexible | Indirect, requires topic creation | ⚠️ Workaround |
| D. JSON array in entity_id | No schema change | Breaks FK, indexing, query patterns | ❌ Never |

**Recommendation**: **Option A + C hybrid**:
- Evidence.entity_id = primary entity (required for lineage)
- Secondary entities expressed via topic_links (entity → topics → candidate)
- ContextWindow resolver returns `(primary_entity_id, secondary_entity_ids[])`
- FormationService stores primary in Candidate.entity_id, links secondaries via topics

### Topic_links as Multi-Entity Carrier

```sql
-- topic_links structure
source_type | source_id | topic_id
'entity'    | entity_A  | topic_1
'entity'    | entity_B  | topic_1  ← same topic, different entities
'candidate' | cand_X    | topic_1
```

**Gap identified**: topic_links has no direct entity-to-entity relationship. Multi-entity evidence must be expressed as: primary entity in Evidence.entity_id + additional entities linked via topics.

---

## 4. Entity Resolution Method Analysis

### Existing Capabilities

**EntityService.resolve_entity()** (`entity_service.py:142-205`):
```python
async def resolve_entity(
    self,
    *,
    workspace_id: UUID,
    entity_id: UUID | None = None,
    canonical_name: str | None = None,
    entity_type: str | None = None,
) -> EntityProfile | None:
```
- Resolves by ID or canonical_name
- Does NOT extract from raw text
- Requires caller to provide name or ID

**ReflectionEngine._extract_entity_names()** (`reflection_engine.py:382-388`):
```python
@staticmethod
def _extract_entity_names(facts: list[dict[str, Any]]) -> list[str]:
    entities = set()
    for fact in facts:
        entity = fact.get("entity", "")
        if entity:
            entities.add(entity)
    return sorted(entities)
```
- Extracts from LLM-generated structured facts
- Post-hoc, not pre-resolution
- Returns names, not resolved UUIDs

**TopicService.extract_topics_from_summary()** (`topic_service.py`):
```python
async def extract_topics_from_summary(
    self, *, workspace_id: UUID, semantic_summary: str
) -> list[UUID]:
    topics = self._extract_keywords(semantic_summary)
    resolved_ids = []
    for topic_name in topics:
        topic_id = await self.resolve_topic(workspace_id=workspace_id, name=topic_name)
        if topic_id:
            resolved_ids.append(topic_id)
    return resolved_ids
```
- Keyword-based topic extraction
- Could be extended to entity extraction

### Resolution Methods Comparison

| Method | Accuracy | Cost | Deterministic | Works For |
|--------|----------|------|---------------|-----------|
| Exact keyword match | High | $0 | Yes | Category A (30%) |
| Alias matching | High | $0 | Yes | Category A with aliases |
| Partial/fuzzy match | Medium | $0 | Partial | Category A/B hybrid |
| LLM extraction | High | $$ | No | Category B (40%), C (15%) |
| Rule-based + LLM fallback | High | $ | Partial | All categories |

### Recommended Hybrid Approach

```
Step 1: Exact canonical_name match against existing entities
Step 2: Alias match against existing entity aliases
Step 3: Fuzzy/partial match (Levenshtein, substring)
Step 4: LLM extraction (only if steps 1-3 fail)
Step 5: Create new entity if confidence threshold met
Step 6: Mark as unresolved if all methods fail
```

**Cost optimization**: Steps 1-3 are $0 (database lookups). Step 4 (LLM) only for ~55% of evidences (Categories B+C).

---

## 5. Case-by-Case Resolution Design

### Case A: Clear Single Entity (30%)

**Example**: "预算管理APP" → entity "预算管理" or "budget_management_app"

**Resolution**:
1. Exact match: Search entities WHERE canonical_name ILIKE '%预算管理%'
2. If found: return (entity_id, confidence=1.0, method='exact_match')
3. If not found: create new entity with confidence=0.9

**Action**: Direct resolution, no LLM needed.

### Case B: Needs Context (40%)

**Example**: "这个功能怎么样" (in context of prior discussion about 预算管理APP)

**Resolution**:
1. ContextWindow contains prior evidences about 预算管理APP
2. Extract entities from context window evidences
3. Infer primary entity from context
4. Return (entity_id, confidence=0.7, method='context_inference')

**Action**: Requires ContextWindow access + LLM for complex cases.

### Case C: Multiple Entities (15%)

**Example**: "比较Apple Pay和Google Pay的优缺点"

**Resolution**:
1. Extract all named entities from content
2. Primary: Apple Pay (mentioned first / more detail)
3. Secondary: Google Pay
4. Return (primary_entity_id, [secondary_entity_ids], confidence=0.8, method='multi_entity_extraction')

**Action**: LLM extraction required. Store primary in Evidence.entity_id, secondaries via topic_links.

### Case D: No Clear Entity (10%)

**Example**: "你好", "谢谢", "明白了"

**Resolution**:
1. No entity keywords detected
2. Mark as UNRESOLVED
3. Confidence = 0.0, method = 'no_entity_detected'

**Action**: Evidence enters pipeline but Candidate is created with unresolved flag. Does NOT block pipeline.

### Case E: Cannot Determine (5%)

**Example**: Ambiguous technical query without clear domain

**Resolution**:
1. Attempt best-effort extraction
2. If confidence < 0.5: mark as UNRESOLVED
3. Log warning for manual review

**Action**: Same as Case D — does not block pipeline.

---

## 6. Entity Resolution Contract

### Input

```python
@dataclass
class EntityResolutionInput:
    evidence_id: UUID
    workspace_id: UUID
    context_window: ContextWindow  # Already formed
    existing_entities: list[EntityProfile]  # All entities in workspace
```

### Output

```python
@dataclass
class EntityResolutionResult:
    primary_entity_id: UUID | None
    secondary_entity_ids: list[UUID]
    confidence: float  # 0.0-1.0
    method: str  # 'exact_match' | 'alias_match' | 'fuzzy_match' | 'llm_extraction' | 'context_inference' | 'unresolved'
    rationale: str  # Human-readable explanation
    lineage: dict  # Resolution trace
    
    @property
    def is_resolved(self) -> bool:
        return self.primary_entity_id is not None and self.confidence >= 0.5
    
    @property
    def is_unresolved(self) -> bool:
        return not self.is_resolved
```

### Guarantees

1. **Never returns wrong entity**: If confidence < 0.5, return unresolved, not wrong entity
2. **Never fabricates entity_id**: Unresolved evidences proceed with NULL primary_entity_id
3. **Always records lineage**: method + rationale + confidence for audit
4. **Batch efficient**: Process multiple evidences in single LLM call when possible

---

## 7. Failure Strategy

### Principle: Entity Resolution Failure ≠ Evidence Loss

**Current problem**: FormationService returns `success=False` when entity cannot be resolved, causing the entire evidence to be skipped.

**New design**: Entity resolution failure should NOT block the pipeline.

### Failure Handling Matrix

| Resolution Outcome | Action | Pipeline Status |
|-------------------|--------|----------------|
| Resolved (confidence ≥ 0.8) | Normal flow: Create Candidate with entity_id | ✅ Proceed |
| Resolved (confidence 0.5-0.8) | Create Candidate with entity_id + flag low_confidence | ✅ Proceed with warning |
| Unresolved (confidence < 0.5) | Create Candidate with NULL entity_id + flag unresolved | ✅ Proceed (do NOT block) |
| No entity detected (Case D) | Create Candidate with NULL entity_id + tag 'no_entity' | ✅ Proceed |
| Multi-entity (Case C) | Create Candidate with primary entity_id + link secondaries via topics | ✅ Proceed |

### Modified FormationService Logic

```python
# Current (blocking):
if entity_id is None:
    return FormationResult(success=False, error="Could not resolve entity_id")

# New (non-blocking):
if entity_id is None:
    logger.warning(f"Evidence {trigger_evidence_id} has no entity, creating candidate without entity linkage")
    # Continue with entity_id=None, mark candidate as unresolved
```

---

## 8. Validation Plan: 100-Evidence Test

### Sampling Strategy

```
1. Stratified random sample:
   - 30 from Category A (clear single entity)
   - 40 from Category B (needs context)
   - 15 from Category C (multi-entity)
   - 10 from Category D (no entity)
   - 5 from Category E (ambiguous)

2. Source: evidences WHERE entity_id IS NULL ORDER BY RANDOM() LIMIT 100
```

### Ground Truth Establishment

```
Method 1: Human annotation (gold standard)
  - 3 reviewers independently annotate each evidence
  - Majority vote = ground truth
  - Disputed cases → senior reviewer arbitrates

Method 2: Existing entity_id as proxy
  - For evidences WITH entity_id: use as reference
  - Compare resolution against known entity

Method 3: Cross-validation
  - Run resolution 3 times with different seeds
  - Consistency = reliability indicator
```

### Metrics Calculation

| Metric | Formula | Target |
|--------|---------|--------|
| **Single-entity accuracy** | Resolved correctly / Total single-entity cases | ≥ 90% |
| **Multi-entity recall** | Detected secondary entities / Total secondary entities | ≥ 80% |
| **Unresolved rate** | Unresolved evidences / Total evidences | ≤ 15% |
| **False-positive rate** | Wrong entity assigned / Total resolved | ≤ 5% |
| **Pipeline survival rate** | Evidences that complete pipeline / Total evidences | 100% |

### Test Execution Plan

```
Phase 1: Build test harness
  - Create EntityResolutionService test implementation
  - Load 100 sampled evidences
  - Establish ground truth (manual annotation)

Phase 2: Run resolution
  - Execute resolution on all 100 evidences
  - Record: primary_entity_id, secondary_entity_ids, confidence, method, rationale

Phase 3: Evaluate
  - Compare against ground truth
  - Calculate all metrics
  - Identify failure patterns

Phase 4: Iterate
  - Fix resolution logic for failure cases
  - Re-run until all gates pass
```

---

## 9. Clean Rebuild Pre-Conditions (Gates)

### Gate ER-1: Single-Entity Resolution Accuracy

```
Condition: Single-entity accuracy ≥ 90%
Test: 30 Category A evidences
Pass criteria: ≥ 27/30 correctly resolved
```

### Gate ER-2: Multi-Entity Recall

```
Condition: Multi-entity recall ≥ 80%
Test: 15 Category C evidences
Pass criteria: ≥ 12/15 secondary entities detected
```

### Gate ER-3: False-Positive Rate

```
Condition: False-positive rate ≤ 5%
Test: All 100 evidences
Pass criteria: ≤ 5 wrong entity assignments
```

### Gate ER-4: Pipeline Survival

```
Condition: No evidence lost due to entity resolution failure
Test: All 100 evidences through full pipeline
Pass criteria: 100/100 produce Candidate (with or without entity_id)
```

### Gate ER-5: Lineage Completeness

```
Condition: Every Candidate has complete entity lineage
Test: Check all produced Candidates
Pass criteria:
  - All Candidates have evidence_chain (non-empty)
  - All Candidates with resolved entity have entity_id set
  - All Candidates track resolution method in metadata
```

### Gate ER-6: 100-Evidence Test Pass

```
Condition: All Gates ER-1 through ER-5 pass
Test: Full 100-evidence validation suite
Pass criteria: All gates pass simultaneously
```

---

## 10. Final Architecture Recommendation

### A. Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ENTITY RESOLUTION LAYER (NEW)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  EntityResolutionService                                                │
│  ─────────────────────────────────────                                  │
│  Input:  ContextWindow + workspace_id                                   │
│  Process:                                                              │
│    1. Exact canonical_name match                                        │
│    2. Alias match                                                       │
│    3. Fuzzy/partial match                                               │
│    4. LLM extraction (fallback)                                         │
│  Output: EntityResolutionResult                                         │
│    - primary_entity_id                                                  │
│    - secondary_entity_ids[]                                             │
│    - confidence, method, rationale                                      │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    MODIFIED CONTEXTWINDOW FORMATION                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ContextWindowFormulator.formulate()                                    │
│  ─────────────────────────────────────                                  │
│  After assembling context window:                                       │
│    resolved = await self.entity_resolver.resolve(context, workspace_id) │
│    context.resolved_entities = resolved.primary_entity_id               │
│    context.secondary_entities = resolved.secondary_entity_ids           │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    MODIFIED FORMATIONSERVICE                            │
├─────────────────────────────────────────────────────────────────────────┤
│  FormationService.form()                                                │
│  ─────────────────────────────────────                                  │
│  entity_id = context.resolved_entities (NOT from evidence.entity_id)    │
│  If unresolved: create candidate with entity_id=NULL, flag='unresolved' │
└─────────────────────────────────────────────────────────────────────────┘
```

### B. Data Model Changes

| Change | Table | Column | Type | Required? |
|--------|-------|--------|------|-----------|
| Add resolved_entities | ContextWindow (in-memory) | resolved_entities | list[UUID] | No (runtime only) |
| Add resolution_method | candidates | _meta | jsonb | No (stored in metadata) |
| Add resolution_confidence | candidates | evidence_strength | float | No (reuse existing) |
| **NO schema changes needed** | | | | |

### C. Files to Modify

| File | Change | Lines | Risk |
|------|--------|-------|------|
| `context/context_window.py` | Add `resolved_entities` field | ~5 | Low |
| `context/formulator.py` | Call EntityResolutionService after context assembly | ~20 | Low |
| `service/entity_resolution_service.py` | **NEW FILE** | ~200 | Medium |
| `service/formation_service.py` | Use context.resolved_entities instead of evidence.entity_id | ~10 | Medium |
| `service/evidence_pipeline_service.py` | Remove direct L2 creation | ~5 | Low |

### D. New Service: EntityResolutionService

```python
# backend/src/backend/service/entity_resolution_service.py
class EntityResolutionService(BaseService):
    """Resolves entities from evidence content + context.
    
    Resolution pipeline:
    1. Exact match against existing entities
    2. Alias match
    3. Fuzzy match
    4. LLM extraction (fallback)
    5. Create new entity (if confidence sufficient)
    """
    
    async def resolve(
        self,
        *,
        context_window: ContextWindow,
        workspace_id: UUID,
    ) -> EntityResolutionResult:
        """Resolve entities from context window."""
        # Step 1-3: Rule-based matching (fast, $0)
        # Step 4: LLM extraction (slow, costs money)
        # Step 5: Create entity if needed
        pass
```

### E. EvidencePipelineService Changes

| Change | Description |
|--------|-------------|
| Remove direct L2 creation | Lines 162-168: Comment out `if interpretation.user_owned: await self._evolve(...)` |
| Add entity resolution step | Before `_form()`, call EntityResolutionService |
| Pass resolved entities to Formation | Update `_form()` call signature |

### F. ContextWindow / Interpretation Changes

| Component | Change |
|-----------|--------|
| ContextWindow | Add `resolved_entities: list[UUID]` field |
| EvidenceContext | Already has `entity_id: UUID` (from evidence) |
| InterpretationResult | No change needed (entity resolution is separate concern) |

### G. Clean Rebuild Prerequisite Gates

```
[ ] Gate ER-1: Single-entity accuracy ≥ 90% (30 test evidences)
[ ] Gate ER-2: Multi-entity recall ≥ 80% (15 test evidences)
[ ] Gate ER-3: False-positive rate ≤ 5% (100 test evidences)
[ ] Gate ER-4: Pipeline survival = 100% (no evidence lost)
[ ] Gate ER-5: Lineage completeness verified
[ ] Gate ER-6: All gates pass in 100-evidence validation suite
[ ] Code review completed for all modified files
[ ] Rollback plan tested
[ ] Staging environment validated
```

### H. Estimated Implementation Work

| Task | Estimated Effort | Dependencies |
|------|-----------------|--------------|
| EntityResolutionService implementation | 2-3 days | None |
| ContextWindowFormulator enhancement | 0.5 days | EntityResolutionService |
| FormationService modification | 0.5 days | EntityResolutionService |
| EvidencePipelineService cleanup | 0.5 days | EntityResolutionService |
| 100-evidence validation test | 1 day | All above |
| Code review + integration testing | 1 day | All above |
| **Total** | **5-7 days** | — |

---

## 11. Answer to Core Question

> "为了 Strategy B Clean Rebuild，Entity Resolution 应该成为 L0→L1 Formation Pipeline 的正式能力吗？如果是，它的准确边界和数据契约是什么？"

**Answer: YES.**

**Boundary**: Entity Resolution MUST be a formal step in the Formation pipeline, executed at ContextWindow formation time (after context assembly, before interpretation).

**Data Contract**:
- **Input**: ContextWindow (with evidence_list) + workspace_id
- **Output**: EntityResolutionResult with primary_entity_id, secondary_entity_ids, confidence, method, rationale
- **Guarantee**: Never returns wrong entity (confidence < 0.5 → unresolved, not wrong entity)
- **Pipeline impact**: Unresolved evidences continue through pipeline with NULL entity_id (do NOT block)

**Why this boundary**:
1. ContextWindow has full conversational context (vs. import time: no context)
2. Resolution happens before Interpretation (vs. after: too late for Formation)
3. Separate service maintains clean boundaries (vs. mixing into Formulator/Formation)
4. Hybrid approach (rule-based + LLM fallback) balances cost and accuracy

---

## 12. Summary of Architecture Conflicts Status

| Conflict | Status | Resolution |
|----------|--------|------------|
| FC-001 (EvidencePipelineService entry) | ✅ RESOLVED | Orchestrator pattern |
| FC-002 (L1 entity_id lineage) | ✅ RESOLVED | ContextWindow-time resolution |
| FC-003 (EvolutionService integration) | ✅ RESOLVED | L2/L3 via EvolutionService only |
| FC-004 (Cross-batch aggregation) | ✅ RESOLVED | L1 aggregation, no entity_facts |
| **CONFLICT-002-B** (Entity resolution implementation) | 🔴 OPEN | Requires EntityResolutionService |

---

**Phase 22.13 complete. Awaiting user approval to proceed with EntityResolutionService implementation.**
