# Phase 22.2 L0→L1 Formation Boundary & Rebuild Feasibility Audit

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## Executive Summary

### Core Finding
**L1 MemoryNode creation belongs to ReflectionService, not EvidencePipelineService.**

The current architecture is:
```
EvidencePipelineService (Phase 21):
  Evidence → ContextWindow → Interpretation → Reconstruction + Candidate → [Optional] EvolutionService

ReflectionService (Phase 20):
  Candidates → Facts → Proposals → L1 MemoryNode (via approve_proposal)
```

EvidencePipelineService **does NOT create L1 MemoryNodes**. It creates Candidates and optionally calls EvolutionService (which can create L2/L3).

This is a **design decision**, not an implementation gap.

---

## 1. Historical Evidence → L1 MemoryNode Trace

### Current Production Path
```
File: reflection_service.py:208-380
Function: approve_proposal()

Process:
  1. SELECT proposal WHERE id = :proposal_id
  2. UPDATE proposals SET status = 'approved'
  3. INSERT INTO memory_nodes (level=1, type='Observation')
  4. UPDATE candidates SET status = 'confirmed'
```

### Does EvidencePipelineService create L1?
**Answer: NO**

```python
# evidence_pipeline_service.py:106-195
async def process_evidence(self, evidence_id, workspace_id):
    # Step 1: Form ContextWindow
    context_window = await self._form_context_window(...)
    
    # Step 2: Interpret
    interpretation = await self._interpret(...)
    
    # Step 3: Form (Reconstruction + Candidate)
    formation = await self._form(...)
    
    # Step 4: Extract topics
    topic_ids = await self._extract_topics(...)
    
    # Step 5: Evolution (ONLY if user_owned)
    if interpretation.user_owned:
        await self._evolve(...)  # Creates L2/L3, NOT L1
    
    return PipelineResult(...)
```

**EvidencePipelineService creates:**
- ✅ ContextWindow (in-memory)
- ✅ InterpretationResult (in-memory)
- ✅ Reconstruction (DB)
- ✅ Candidate (DB)
- ✅ Topics (DB)
- ⚠️ L2/L3 MemoryNode (via EvolutionService, conditional)
- ❌ L1 MemoryNode (NEVER created)

---

## 2. Phase 21 EvidencePipelineService Actual Behavior

### Where does it stop?
```
After Formation (Step 3):
  - Reconstruction created
  - Candidate created (status='candidate')
  - Topics linked
  
After Evolution (Step 5, conditional):
  - L2/L3 MemoryNode created (if candidate_type='pattern')
  - Relationships created
```

### Why no L1 creation?
**Design decision in FormationService._create_candidate():**

```python
# formation_service.py:245-284
candidate = Candidate(
    content=interpretation.semantic_content,  # → This BECOMES L1 content
    candidate_type=candidate_type,  # → "pattern" or "belief"
    evidence_chain=[str(eid) for eid in evidence_ids],
    evidence_count=len(evidence_ids),
    evidence_strength=evidence_strength,
    status="candidate",  # ← Pending state
    ...
)
```

The Candidate acts as a **holding structure** for Evidence until ReflectionService processes it.

---

## 3. L1 MemoryNode Semantic Ownership Analysis

### Is L1 part of Formation or Evolution?

**Evidence:**
```python
# Formation: Creates Candidate (structured evidence)
# Reflection: Creates MemoryNode (confirmed observation)

# The semantic boundary:
# - Formation: Evidence → Structured Candidate (potential memory)
# - Reflection: Candidate → Confirmed MemoryNode (actual memory)
```

### Conclusion
**L1 belongs to ReflectionService (Evolution phase), not EvidencePipelineService (Formation phase).**

Rationale:
1. Candidate is a "pending" state awaiting validation
2. L1 MemoryNode is the "confirmed" state after Reflection
3. The transition Candidate → MemoryNode requires:
   - Fact extraction (LLM)
   - Proposal generation
   - Approval logic
   - These are all in ReflectionService

---

## 4. Candidate → L1 Mapping

### Field mapping analysis:

| Candidate field | L1 MemoryNode field | Source |
|-----------------|---------------------|--------|
| `content` | `content` | Direct copy |
| `entity_id` | `entity_id` | Via proposal.evidence_chain |
| `workspace_id` | `workspace_id` | Passed through |
| `evidence_chain` | `evidence_links` | JSON array |
| `evidence_strength` | `confidence` | Direct |
| `id` | - | Not copied (new node ID) |

### Missing mappings:
```python
# ReflectionService.approve_proposal() does NOT set:
- reconstruction_id (lost!)
- parent_node_id (not tracked)
- source_level (defaults to 1)
```

### Evidence from code:
```python
# reflection_service.py:313-330
await conn.execute(text("""
    INSERT INTO memory_nodes (
        id, workspace_id, entity_id, level, node_type, content, summary,
        confidence, importance, signal_strength, status, source, generated_by,
        evidence_links, contradict_evidence, _meta, created_at, updated_at
    ) VALUES (
        :id, :workspace_id, :entity_id, :level, :node_type, :content, :summary,
        :confidence, :importance, :signal_strength, 'active', 'ai_reflect', 'ai_reflect',
        :evidence_links, '[]', '{}', NOW(), NOW()
    )
"""), {
    "content": content,  # From proposal, not from Candidate.content
    "evidence_links": json.dumps(evidence_chain),  # From proposal.evidence_chain
    ...
})
```

**Finding:** L1 content comes from proposal aggregation, NOT directly from Candidate.content. This means:
- If proposal has multiple evidences, content is aggregated
- If proposal has single evidence, content may be truncated

---

## 5. ReflectionService Current Responsibilities

### Split by function:

| Responsibility | Method | Level |
|---------------|--------|-------|
| A. L0→L1 Formation | `_save_candidates()` | N/A (Candidate already exists) |
| B. L1→L2 Evolution | `approve_proposal()` | L1 (with level=1) |
| C. L2→L3 Evolution | `approve_proposal()` | Conditional (if target_level=3) |
| D. Batch Processing | `reflect()` | Orchestration |
| E. Proposal Generation | `_generate_proposals()` | Decision logic |
| F. Fact Extraction | `_extract_facts()` | LLM-based |

### Critical observation:
**ReflectionService does NOT do "Formation" (A). It processes ALREADY FORMED Candidates.**

The actual flow:
```
EvidencePipelineService.form() → Candidate (DB)
       ↓
ReflectionService.reflect() → Proposal (DB)
       ↓
ReflectionService.approve_proposal() → MemoryNode (DB)
```

---

## 6. EvolutionService Current Capabilities

### What it CAN do:
```python
# evolution_service.py:333-372
async def _create_memory_node(self, candidate: Candidate):
    level = 2 if candidate.candidate_type == "pattern" else 3
    node_type = "Pattern" if level == 2 else "Belief"
    
    node = MemoryNode(
        level=level,  # ← L2 or L3
        node_type=node_type,
        content=candidate.content,
        ...
    )
```

### What it DOES do in production:
**NOTHING** — EvidencePipelineService is not called by Cron.

### Evidence:
```python
# evidence_pipeline_service.py:162-168
if interpretation.user_owned:
    await self._evolve(
        candidate_id=formation.candidate_id,
        ...
    )
```

Only triggered by:
1. Direct API call to `/api/v1/pipeline/process`
2. NOT by Cron (Cron calls ReflectionService)

---

## 7. Rebuild Feasibility Analysis

### Dependency graph:

```
Evidence (L0)
  ↓ FK: evidence_chain
Candidate
  ↓ FK: candidate_id
Proposal
  ↓ FK: evidence_links
MemoryNode (L1)
  ↓ FK: evidence_links (candidate IDs)
MemoryNode (L2/L3)

Reconstruction ← links to Candidate
Topics ← linked to Reconstruction
TopicLinks ← links Topics to entities
```

### Deletable tables (if rebuild from Evidence):
| Table | FK dependencies | Rebuildable? |
|-------|-----------------|--------------|
| candidates | evidence_chain → evidences | ✅ Yes |
| reconstructions | entity_id, evidence_refs | ✅ Yes |
| proposals | candidate_id → candidates | ✅ Yes |
| memory_nodes | evidence_links → candidates/evidences | ⚠️ Partial |
| memory_relationships | source/target → memory_nodes | ❌ No (depends on MN) |
| topics | workspace_id | ✅ Yes |
| topic_links | topic_id, entity_id | ⚠️ Partial |

### Critical dependencies:
```sql
-- MemoryNodes reference Candidates in evidence_links
-- If we delete Candidates, we break MemoryNode lineage

-- However:
-- L1 MemoryNodes could be recreated from Evidence directly
-- L2/L3 MemoryNodes would need re-evolution
```

---

## 8. Data Rebuild Boundaries

### Safe to preserve:
```
- evidences (raw input)
- areas (spatial context)
- entities (semantic anchors)
- workspace (tenant isolation)
- user_profiles
```

### Candidates for rebuild:
```
- candidates (from Evidence via Formation)
- reconstructions (from Interpretation)
- proposals (from Candidates via Reflection)
- memory_nodes L1 (from Candidates via Reflection)
- memory_nodes L2+ (from Candidates via Evolution)
- topics (re-extractable)
- topic_links (rebuildable)
```

### Risks:
1. **L2/L3 MemoryNodes**: Would need to re-run EvolutionService for each candidate
2. **MemoryRelationships**: Would need to re-detect historical relationships
3. **Topic associations**: May need re-extraction
4. **Lineage**: Some lineage may be lost if not preserved in Evidence

---

## 9. Rebuild Experiment Design (Not Executed)

### Phase A: Formation-only rebuild
```
For each Evidence:
  1. Run EvidencePipelineService.process_evidence()
  2. Create: ContextWindow → Interpretation → Reconstruction + Candidate
  3. Stop before Evolution
```

### Phase B: Reflection-only rebuild
```
For each Candidate:
  1. Run ReflectionService.reflect()
  2. Create: Facts → Proposals → L1 MemoryNode
  3. Stop before L2 evolution
```

### Phase C: Evolution rebuild
```
For each L1 MemoryNode:
  1. Run EvolutionService.evolve()
  2. Create: L2 Pattern / L3 Belief
  3. Create: Relationships
```

### Validation metrics:
- Evidence count preserved
- Candidate count matches Formation output
- Proposal count matches Reflection output
- MemoryNode count matches Evolution output
- Lineage integrity (evidence → candidate → proposal → memory)

---

## 10. Architecture Verdict

### Q1. Should L1 be created by EvidencePipelineService?
**A: NO**

**Reason:**
- L1 requires fact extraction and proposal approval
- EvidencePipelineService focuses on Formation (structured interpretation)
- L1 is the result of Reflection (evolution), not Formation

### Q2. Should ReflectionService start from L1?
**A: YES (current behavior)**

**Evidence:**
- ReflectionService receives Candidates (already formed)
- Creates Proposals from Candidate facts
- Creates L1 MemoryNodes from approved Proposals

### Q3. Should EvolutionService be the底层 implementation for L1+ evolution?
**A: YES (partial)**

**Evidence:**
- EvolutionService already handles L2/L3 creation
- Should also handle L1 creation for consistency
- Currently only used by EvidencePipelineService (not ReflectionService)

### Q4. Is current database suitable for clean rebuild?
**A: YES (with caveats)**

**Requirements:**
1. Preserve all Evidences (source of truth)
2. Delete Candidates and above
3. Re-run Formation pipeline for each Evidence
4. Re-run Reflection pipeline for each Candidate
5. Re-run Evolution pipeline for each L1

**Risks:**
- Time: ~15,000 evidences × formation cost
- LLM calls: Significant API cost
- Data consistency: Must ensure no evidence is lost

### Q5. What is the minimal safe delete scope?
**A:**
```
Delete:
- candidates (all)
- reconstructions (all)
- proposals (all)
- memory_nodes (all)
- memory_relationships (all)
- topic_links (all)

Keep:
- evidences
- areas
- entities
- topics (maybe, if deterministic)
- workspace
- user_profiles
```

### Q6. Does rebuild require code changes?
**A: YES (recommended)**

**Changes needed:**
1. Add L1 creation to EvidencePipelineService (or keep in ReflectionService)
2. Ensure EvolutionService can create L1 (currently only L2/L3)
3. Add batch processing for efficient rebuild
4. Add validation hooks for lineage checking

---

## 11. Final Recommendations

### Immediate (No changes):
- Accept current architecture as valid
- EvidencePipelineService = Formation (Evidence → Candidate)
- ReflectionService = Evolution (Candidate → Memory)

### Short-term:
- Document the boundary clearly
- Ensure both services have consistent L1 creation logic
- Add validation for cross-service data integrity

### Long-term:
- Consider unified pipeline: Evidence → Candidate → L1 → L2 → L3
- Use EvolutionService consistently for all evolution steps
- Add entity-level fact accumulation for L2/L3 triggers

---

## 12. Explicit "DO NOT MODIFY" Confirmation

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
