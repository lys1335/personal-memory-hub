# Personal Memory Hub — Terminology Freeze

> **Version**: 1.0
> **Date**: 2026-08-05
> **Status**: 🧊 Frozen
> **Type**: Architecture Documentation

---

## 1. Purpose

This document establishes the single source of truth for all terminology used in Personal Memory Hub architecture documents.

**Rule**: Once frozen, all documents must use these exact terms. No synonyms allowed within the same context.

---

## 2. Core Pipeline Terms

| Term | Definition | Usage |
|------|-----------|-------|
| **Evidence** | Raw input data (conversation messages, imported documents, user input). Immutable. | Source for EvidenceEvolution Engine |
| **Observation** | Structured information extracted from Evidence by IngestionEngine. Equivalent to L1 MemoryNode. | Stored in memory_nodes (level=1) |
| **Candidate** | Reflection Working Object. Output of EvidenceEvolution Engine. Not Memory. Not Proposal. | Stored in candidates table |
| **Proposal** | Recommendation from Reflection Engine. Must go through Approval. | Stored in proposals table |
| **Approval** | Service method that converts Proposal to MemoryNode. | Service layer, not Engine |
| **MemoryNode** | Persistent knowledge at any level (L1-Ln). | Stored in memory_nodes table |

---

## 3. Engine Terms

| Term | Definition | Replaces |
|------|-----------|----------|
| **EvidenceEvolution Engine** | Information Extraction engine. Takes Evidence, outputs Candidate. | Light Reflect |
| **Reflection Engine** | Reasoning engine. Takes Candidate, outputs Proposal. | Heavy Reflect (in part) |
| **Approval** | Service method. Takes Proposal, outputs MemoryNode. | Direct Persistence |
| **Ingestion Engine** | Takes Conversation, outputs Observation. | — |
| **Activation Engine** | Takes Belief + Context, outputs State. | — |
| **Retrieval Engine** | Takes Query, outputs Related Memories. | — |
| **Context Builder** | Takes Retrieval Results + States, outputs Prompt Context. | — |
| **Scheduler** | Event + Cron driven task scheduler. | — |
| **EntityEngine** | Entity identity management. | — |
| **RelationshipEngine** | Relationship graph management. | — |
| **TaskRuntime** | Generic task execution infrastructure. | — |

---

## 4. Memory Level Terms

| Level | Old Term | New Term | Definition |
|-------|----------|----------|------------|
| L1 | Observation | Observation | Raw fact, immutable, never deleted |
| L2 | Pattern | Pattern | Abstraction over L1 Observations |
| L3 | Belief | Belief | Inference from L2 Patterns |
| L4 | State | State | Runtime activation of Belief |
| Ln | — | Abstract | Future levels remain abstract |

**Rule**: Memory Node levels (L1, L2, L3, L4) are DIFFERENT from source_level in Candidate/Proposal.

---

## 5. Source_level vs Level

| Field | Table | Meaning |
|-------|-------|---------|
| `source_level` | candidates, proposals | Which level the input came from (1=Evidence, 2=Pattern, 3=Belief) |
| `level` | memory_nodes | The level of the memory itself (1=Observation, 2=Pattern, 3=Belief) |
| `target_level` | proposals | The level the proposal wants to create |

**Example**:
- L1 Evidence → source_level=1 → Proposal target_level=2 → MemoryNode level=2 (Pattern)
- L2 Pattern → source_level=2 → Proposal target_level=3 → MemoryNode level=3 (Belief)

---

## 6. Fact Term

| Term | Definition | Persistence |
|------|-----------|-------------|
| **Fact** | Internal DTO of EvidenceEvolution Engine. Represents extracted information. | NOT persisted |

**Rule**: Facts are transient. They exist only during one EvidenceEvolution Engine call. No facts table exists.

---

## 7. Old → New Term Mapping

### 7.1 Pipeline Terms

| Old Term | New Term |
|----------|----------|
| Light Reflect | EvidenceEvolution Engine |
| Heavy Reflect | Reflection Engine (Stage 2 only) |
| Candidate Discovery | Entity Extraction + Pattern Discovery |
| Evidence Verification | Proposal Validation |
| Pattern Proposal | Proposal |
| Pattern (L2) | MemoryNode (level=2) |
| Belief (L3) | MemoryNode (level=3) |

### 7.2 Observation vs Evidence

| Old Usage | New Usage |
|-----------|-----------|
| Evidence = Observation | Evidence = Raw input, Observation = L1 MemoryNode |
| "Evidence created" | "Observation created" |

### 7.3 Entity Terms

| Old Term | New Term |
|----------|----------|
| Memory Domain Orchestrator | MemoryEngine (still exists, different context) |
| CandidateEngine | EvidenceEvolution Engine |

---

## 8. Term Consistency Rules

### Rule 1: One Term per Concept
- "Evidence" = raw input, never used for Observation
- "Observation" = L1 MemoryNode, never used for raw input
- "Candidate" = Reflection Working Object, never used for Memory
- "Proposal" = Recommendation, never used for Memory

### Rule 2: No Synonyms in Same Context
- Do not write "Evidence/Observation" — pick one
- Do not write "Candidate/Reflection Candidate" — use "Candidate"
- Do not write "Evidence Candidate/Reflection Candidate" — use "Evolution Candidate" or just "Candidate"

### Rule 3: Pipeline Order
```
Evidence → EvidenceEvolution Engine → Candidate → Reflection Engine → Proposal → Approval → MemoryNode
```

**Forbidden patterns**:
- ~~Evidence → Reflection → Proposal~~ (missing EvidenceEvolution)
- ~~Observation → Pattern → Belief~~ (skipping Candidate/Proposal)
- ~~Light Reflect → Heavy Reflect~~ (use new engine names)

---

## 9. Cross-Reference Map

| New Term | Defined In | Referenced In |
|----------|-----------|---------------|
| EvidenceEvolution Engine | D4.2g | 06, 05, ADR-EvidenceEvolution-Split |
| Reflection Engine | D4.2d_v1.1 | 06, 05, 10_4 |
| Candidate | 06, 05 | All Architecture docs |
| Proposal | 06, 05 | 10_4, ADR-EvidenceEvolution-Split |
| Approval | 06, 05 | 10_4 |
| Fact | D4.2g | Architecture docs (as non-persistent) |

---

## 10. Revision History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-08-05 | Initial freeze | 🧊 Frozen |
