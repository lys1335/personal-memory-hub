# Personal AI Memory Hub — Engineering Decision Register

> **Version**: 1.0
> **Date**: 2026-07-01
> **Phase**: Phase B — Engineering Planning
> **Status**: Draft
> **Author**: System Architecture Group

---

## 1. Purpose

This document is the **Engineering Decision Register** for the Personal AI Memory Hub project.

It records **confirmed engineering decisions** together with the project's **current level of understanding**.

### What This Is

* A living register of important engineering decisions made during the architecture and design phases.
* Each entry captures what was decided, the current evidence base, and what is still unknown.
* Decisions are tagged by maturity: **Confirmed** (evidence-based), **Partial** (needs historical discussion), **Pending** (understood but not yet enriched).

### What This Is Not

* A traditional ADR document focused solely on justification and rationale.
* A redesign instrument. This register records decisions; it does not alter the architecture.
* A place to speculate. If evidence is insufficient, the gap is explicitly acknowledged.

### Knowledge Evolution Philosophy

Engineering decisions are **stable**. Understanding of those decisions **evolves**.

Future Memory Hub import and Reflection may enrich:

* Rationale
* Alternatives considered
* Trade-offs
* Evidence coverage

Without changing the original decision unless explicitly reviewed and approved.

Knowledge enrichment improves **explanations**, not **approved decisions**.

### Source of Truth

GitHub remains the project's Single Source of Truth. All decisions recorded here are based on evidence available in approved documentation. Future enrichments still require human review before becoming official documentation.

---

## 2. Decision Record Template

Each decision record uses the following fields. Fields marked `[Partial]` indicate incomplete understanding that may be enriched later.

| Field | Description |
|-------|-------------|
| **Decision ID** | Stable identifier (ENG-XXX). Never depends on section ordering. |
| **Title** | Concise decision subject. |
| **Status** | Final Decision / Confirmed / Partial / Pending. |
| **Decision Version** | d1.0, d1.1, etc. Increments when understanding is enriched. |
| **Decision** | What was decided. |
| **Context** | Why this decision was made (based on available evidence). |
| **Current Understanding** | Full / Partial / Minimal. Indicates completeness of available evidence. |
| **Completeness / Knowledge Maturity** | High / Medium / Low. Reflects confidence in the decision record. |
| **Alternatives Considered** | Known alternatives (if any). `[Partial]` if historical discussion unavailable. |
| **Trade-offs** | Known trade-offs (if any). `[Partial]` if historical discussion unavailable. |
| **Review Trigger** | Condition that should trigger re-review. |
| **Related Principles** | Guideline or principle references. |
| **Related Documents** | Cross-references to other Phase B / Phase A documents. |
| **Tags** | Topic tags for filtering and discovery. |
| **Keywords** | Searchable keywords. |
| **Evidence Coverage** | Which documents provide evidence. |
| **Known Gaps** | What is explicitly unknown or needs future enrichment. |
| **Future Enrichment** | Expected sources of future knowledge (historical discussion, implementation experience, Reflection). |

---

## 3. Engineering Decisions

### ENG-001: Memory Hub = Memory Infrastructure, Not Business Logic

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-001 |
| **Title** | Memory Hub Positioning as Infrastructure |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Memory Hub is a memory infrastructure component, not a business logic system. |
| **Context** | The project must maintain a clear boundary between memory capabilities and business/application logic. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Memory Hub as a general-purpose AI assistant platform. |
| **Trade-offs** | Restricting scope simplifies architecture but requires clear external interfaces for business logic. |
| **Review Trigger** | Any proposal to add business logic directly into Memory Hub. |
| **Related Principles** | G-001, G-002 |
| **Related Documents** | 08 §2.1, 07 §2.1 (P1) |
| **Tags** | architecture, positioning, scope |
| **Keywords** | infrastructure, memory hub, business logic, scope |
| **Evidence Coverage** | 08, 07 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Implementation experience may refine boundary definitions. |

---

### ENG-002: Memory Hub Is Witness, Not Actor

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-002 |
| **Title** | Memory Hub as Witness, Not Actor |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Memory Hub observes, records, organizes, reflects, and retrieves. It does not decide, recommend, plan, or execute. |
| **Context** | Mixing memory capabilities with action capabilities creates trust boundary violations and responsibility confusion. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Memory Hub providing recommendations alongside context. |
| **Trade-offs** | Cleaner separation of concerns vs. potentially more complex orchestration between Agent and Memory Hub. |
| **Review Trigger** | Any feature proposal that blurs the Witness/Actor boundary. |
| **Related Principles** | G-010, G-011 |
| **Related Documents** | 07 §2.9 (P9) |
| **Tags** | boundary, witness, actor, safety |
| **Keywords** | witness, actor, boundary, recommendation, decision |
| **Evidence Coverage** | 07 |
| **Known Gaps** | None. Well-documented with boundary examples. |
| **Future Enrichment** | Implementation may reveal edge cases in boundary enforcement. |

---

### ENG-003: Agent Always Outside Memory Hub

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-003 |
| **Title** | Agent Architecture Boundary |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Agents (Hermes, Open WebUI, Claude, Gemini, etc.) are always external to Memory Hub. They access Memory Hub through a unified interface. |
| **Context** | Keeping agents external ensures replaceability, independence, and security isolation. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Embedding agent logic within Memory Hub. |
| **Trade-offs** | External agents allow free replacement; internal agents create tight coupling. |
| **Review Trigger** | Any proposal to integrate agent logic into Memory Hub. |
| **Related Principles** | G-009 |
| **Related Documents** | 07 §2.3 (P3) |
| **Tags** | agent, boundary, external, unified-interface |
| **Keywords** | agent, external, unified interface, replaceability |
| **Evidence Coverage** | 07 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Multi-agent scenarios may refine interface design. |

---

### ENG-004: Agent Cannot Directly Modify Memory

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-004 |
| **Title** | Agent Write Restriction |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Agents may submit raw data (conversations, observations, documents, summaries), but cannot directly update, delete, or modify memory scores. All state changes must flow through the Ingestion Pipeline. |
| **Context** | Direct agent modification bypasses validation, scoring, and evidence chain integrity. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing agents to directly update memory. |
| **Trade-offs** | Pipeline enforcement adds latency but guarantees data integrity and auditability. |
| **Review Trigger** | Any proposal to grant agents direct memory write access. |
| **Related Principles** | G-012, G-013 |
| **Related Documents** | 07 §2.4 (P4) |
| **Tags** | agent, write-restriction, ingestion-pipeline |
| **Keywords** | agent, write, modify, pipeline, integrity |
| **Evidence Coverage** | 07 |
| **Known Gaps** | None. Well-documented with boundary examples. |
| **Future Enrichment** | Implementation may reveal optimization opportunities within the pipeline. |

---

### ENG-005: Summary Is Observation, Not Long-Term Memory

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-005 |
| **Title** | Summary Treatment as Observation |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Agent-generated summaries are treated as L1 Observations. They must pass through the Ingestion Pipeline and Scoring Engine before becoming long-term memory. |
| **Context** | Summaries are推理产物 (reasoning products) that may lose details or contain errors. Treating them as first-class memory bypasses evidence validation. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Promoting summaries directly to Pattern or Belief level. |
| **Trade-offs** | Pipeline processing adds complexity but ensures evidence chain integrity. |
| **Review Trigger** | Any proposal to promote summaries without pipeline processing. |
| **Related Principles** | G-014 |
| **Related Documents** | 07 §2.5 (P5) |
| **Tags** | summary, observation, evidence-chain |
| **Keywords** | summary, observation, inference, evidence chain |
| **Evidence Coverage** | 07 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | May refine scoring thresholds for summary-derived observations. |

---

### ENG-006: Evidence-Based Memory

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-006 |
| **Title** | Evidence Requirement for All Memory |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | No Evidence = No Memory. Every piece of long-term memory must be traceable to verifiable evidence (conversation, document, observation, or other evidence source). |
| **Context** | Memory without evidence is unverifiable and potentially misleading. Evidence chains enable explainability and falsifiability. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing memory without direct evidence (e.g., derived purely from reflection). |
| **Trade-offs** | Strict evidence requirement limits memory volume but ensures trustworthiness. |
| **Review Trigger** | Any proposal to create memory without evidence chain. |
| **Related Principles** | G-015 |
| **Related Documents** | 07 §2.6 (P6) |
| **Tags** | evidence, traceability, explainability |
| **Keywords** | evidence, traceability, verifiable, chain |
| **Evidence Coverage** | 07 |
| **Known Gaps** | Evidence strength scoring algorithm TBD. |
| **Future Enrichment** | Implementation experience will refine evidence strength calculation. |

---

### ENG-007: No Orphan Memory

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-007 |
| **Title** | No Orphan Memory Rule |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Every memory must have at least one associated evidence. Orphaned memories enter maintenance queue. Broken chains trigger maintenance. |
| **Context** | Orphan memory destroys trust in the entire system. Users cannot verify memories without evidence links. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing orphan memory with special marking. |
| **Trade-offs** | Strict no-orphan rule increases maintenance overhead but preserves system integrity. |
| **Review Trigger** | Any proposal to allow orphan memory creation. |
| **Related Principles** | G-016 |
| **Related Documents** | 07 §2.7 (P7) |
| **Tags** | orphan, evidence, maintenance |
| **Keywords** | orphan, evidence, maintenance, integrity |
| **Evidence Coverage** | 07 |
| **Known Gaps** | Orphan detection algorithm and maintenance queue implementation TBD. |
| **Future Enrichment** | Implementation may refine detection heuristics. |

---

### ENG-008: Reflection Is Memory Maintenance, Not Agent Behavior

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-008 |
| **Title** | Reflection Scope Limitation |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Reflection is limited to memory maintenance: consolidation, merge, entity merge, relationship update, archive decision. It cannot recommend, create goals, create tasks, invoke tools, or make decisions. |
| **Context** | Unrestricted reflection would blur the Witness/Actor boundary and violate the separation between memory and agent responsibilities. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing reflection to generate recommendations. |
| **Trade-offs** | Limited reflection is safer but may require more manual intervention for complex cognitive tasks. |
| **Review Trigger** | Any proposal to expand reflection beyond maintenance. |
| **Related Principles** | G-017, G-018 |
| **Related Documents** | 07 §2.8 (P8) |
| **Tags** | reflection, maintenance, scope-limitation |
| **Keywords** | reflection, maintenance, consolidation, merge |
| **Evidence Coverage** | 07 |
| **Known Gaps** | None. Well-documented with boundary examples. |
| **Future Enrichment** | Implementation may reveal edge cases in reflection scope. |

---

### ENG-009: Entity Admission Criteria

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-009 |
| **Title** | Entity Admission Standards |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | An object becomes an Entity only if it satisfies at least one of: has lifecycle, has state changes, will be referenced in future, will be part of reasoning chains. Otherwise, store as Observation. |
| **Context** | Uncontrolled Entity creation leads to graph explosion, increased inference cost, and maintenance burden. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Automatic Entity creation for all named objects. |
| **Trade-offs** | Strict admission reduces graph complexity but may require Observation-to-Entity upgrades later. |
| **Review Trigger** | Entity count exceeding design expectations. |
| **Related Principles** | G-003 |
| **Related Documents** | 03 ADR-001, 08 §3 |
| **Tags** | entity, admission, graph-complexity |
| **Keywords** | entity, admission, lifecycle, state-change, reasoning |
| **Evidence Coverage** | 03, 08 |
| **Known Gaps** | Automated admission decision algorithm TBD. |
| **Future Enrichment** | Implementation may refine admission heuristics. |

---

### ENG-010: Entity vs Observation Distinction Principle

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-010 |
| **Title** | Entity vs Observation Distinction |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Ask "does this deserve an independent lifecycle?" not "is this important?". Importance is fuzzy; lifecycle worthiness is actionable. |
| **Context** | "Importance" is subjective and leads to Entity proliferation. Lifecycle-based criterion is operational and measurable. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Using importance score as Entity admission criterion. |
| **Trade-offs** | Lifecycle criterion is clearer but may miss high-importance transient facts. |
| **Review Trigger** | Confusion in Entity vs Observation classification during implementation. |
| **Related Principles** | G-003 |
| **Related Documents** | 03 ADR-002 |
| **Tags** | entity, observation, distinction |
| **Keywords** | entity, observation, lifecycle, importance |
| **Evidence Coverage** | 03 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Implementation experience may provide concrete classification examples. |

---

### ENG-011: MemoryNode Unified Hierarchy (L1–L4)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-011 |
| **Title** | Unified MemoryNode Hierarchy |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | All memory content is stored as MemoryNode with a Level attribute. L1=Observation, L2=Pattern, L3=Belief, L4=State. Not separate tables. |
| **Context** | Separate tables for each memory type increase schema complexity and reduce flexibility. A unified model with Level attribute provides natural hierarchy and extensibility. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Separate tables for Observation, Pattern, Belief, State. |
| **Trade-offs** | Unified table simplifies schema but requires Level-based filtering. Separate tables would be more explicit but harder to extend. |
| **Review Trigger** | Performance issues with Level-based filtering at scale. |
| **Related Principles** | G-004, G-005 |
| **Related Documents** | 03 ADR-004, 04 §5.1, 08 §3.1 |
| **Tags** | memory-node, hierarchy, unified-model |
| **Keywords** | memorynode, level, observation, pattern, belief, state |
| **Evidence Coverage** | 03, 04, 08 |
| **Known Gaps** | None. Well-documented across multiple sources. |
| **Future Enrichment** | Level expansion (L5+) may be needed based on implementation experience. |

---

### ENG-012: Reflect Derivation Chain (L1→L2→L3→L4)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-012 |
| **Title** | Reflect Derivation Chain |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Fixed four-layer derivation chain: Observation → Pattern → Belief → State. Each derivation recorded via `derived_from` relationship. No skipping layers. |
| **Context** | A fixed chain provides clear knowledge evolution path and supports Explainable Memory. Skipping layers would break traceability. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing direct Observation → Belief derivation. |
| **Trade-offs** | Fixed chain ensures traceability but may be less flexible for novel cognitive patterns. |
| **Review Trigger** | Evidence that skipping layers improves recall accuracy. |
| **Related Principles** | G-018 |
| **Related Documents** | 03 ADR-010, 04 §14 |
| **Tags** | derivation-chain, explainable-memory, reflection |
| **Keywords** | derivation, chain, observation, pattern, belief, state, explainable |
| **Evidence Coverage** | 03, 04 |
| **Known Gaps** | Derivation algorithms (induction, inference, synthesis) TBD. Confidence propagation TBD. |
| **Future Enrichment** | Implementation will define concrete derivation algorithms. |

---

### ENG-013: Memory Never Deletable (Immutable Memory)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-013 |
| **Title** | Memory Immutability |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Memory is never deleted. Corrections use `correctMemory()` (creates CORRECT/SUPERSEDES relationship). Archival uses `archiveMemory()` (cognitive compression, not data relocation). |
| **Context** | Deleting memory destroys evidence chains and makes future re-analysis impossible. Model upgrades may benefit from re-analyzing historical observations. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing soft-delete or time-based expiration. |
| **Trade-offs** | Immutable memory grows indefinitely; archival compresses but never deletes. |
| **Review Trigger** | Storage costs exceeding practical limits. |
| **Related Principles** | G-019 |
| **Related Documents** | 04 §12.1, 08 §8.3 |
| **Tags** | immutability, correction, archive |
| **Keywords** | immutable, delete, correct, archive, retention |
| **Evidence Coverage** | 04, 08 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Storage optimization strategies may be needed at scale. |

---

### ENG-014: Archive Is Cognitive Compression, Not Cold Storage

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-014 |
| **Title** | Archive Purpose Definition |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Archive is a cognitive compression layer, not data relocation. Original memory permanently retained in memory_nodes. Archive supports Time Travel (traceable to any historical moment). |
| **Context** | Misunderstanding archive as cold storage leads to data loss risk and breaks explainability. Archive summarizes; it does not replace. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Moving old memory to archive (cold storage model). |
| **Trade-offs** | Cognitive compression requires computation but preserves full traceability. |
| **Review Trigger** | Any proposal to treat archive as data relocation. |
| **Related Principles** | G-020 |
| **Related Documents** | 04 §12.1 |
| **Tags** | archive, cognitive-compression, time-travel |
| **Keywords** | archive, compression, time-travel, retention |
| **Evidence Coverage** | 04 |
| **Known Gaps** | Archive content generation algorithm TBD. |
| **Future Enrichment** | Implementation will define archive generation criteria. |

---

### ENG-015: UUIDv7 for All Primary and Foreign Keys

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-015 |
| **Title** | UUIDv7 Key Strategy |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | All table primary keys and foreign keys use UUIDv7. Auto-increment IDs are prohibited. |
| **Context** | UUIDv7 provides time-ordered, distributed-friendly, import-export-safe identifiers compatible with Supabase, SQLite, and future graph databases. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Auto-increment integers, UUIDv4, Snowflake IDs. |
| **Trade-offs** | UUIDv7 is slightly larger than integers but enables multi-Workspace sync and graph migration. |
| **Review Trigger** | Performance profiling showing UUIDv7 is a bottleneck. |
| **Related Principles** | G-006 |
| **Related Documents** | 04 §4.1–4.2 |
| **Tags** | uuidv7, primary-key, distributed |
| **Keywords** | uuid, v7, primary-key, foreign-key, distributed |
| **Evidence Coverage** | 04 |
| **Known Gaps** | None. Well-documented with rationale. |
| **Future Enrichment** | Implementation may reveal indexing optimizations for UUIDv7 ranges. |

---

### ENG-016: Independent vector_documents Table

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-016 |
| **Title** | Vector Storage Separation |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Embeddings stored in independent `vector_documents` table, not in `memory_nodes`. Two-layer separation: full fact library (memory_nodes) + high-value cognitive index (vector_documents). |
| **Context** | Embedding columns are large and degrade query performance. Not all data should be vectorized; value-based分层 (layering) is more efficient. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Storing embeddings inline with memory_nodes. |
| **Trade-offs** | Independent table adds join complexity but preserves query performance and model flexibility. |
| **Review Trigger** | Query performance degradation from join overhead. |
| **Related Principles** | G-007 |
| **Related Documents** | 04 §7.1–7.3, §8 |
| **Tags** | vector, embedding, performance |
| **Keywords** | vector, embedding, performance, independence, layering |
| **Evidence Coverage** | 04 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Vector model selection and index strategy refinement. |

---

### ENG-017: Supabase pgvector for MVP, External Store for V2+

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-017 |
| **Title** | Vector Storage Upgrade Path |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | MVP uses Supabase + pgvector (ivfflat). V2+ upgrade path to hnsw or external vector store (Chroma/Qdrant/Weaviate) via abstraction layer. |
| **Context** | Introducing Chroma as MVP requirement increases initial complexity. pgvector is sufficient for MVP scale (< 1M records). Upgrade path is abstracted to avoid lock-in. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Using Chroma from day one. |
| **Trade-offs** | pgvector is simpler initially but may require migration at scale. |
| **Review Trigger** | Vector search performance exceeding pgvector capabilities. |
| **Related Principles** | G-008 |
| **Related Documents** | 04 §10, 08 §11 |
| **Tags** | vector-storage, supabase, upgrade-path |
| **Keywords** | supabase, pgvector, ivfflat, hnsw, chroma, qdrant, upgrade |
| **Evidence Coverage** | 04, 08 |
| **Known Gaps** | Abstract layer interface design TBD. |
| **Future Enrichment** | Implementation will define the abstraction interface. |

---

### ENG-018: Unified tasks Table (Not Separate Queues)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-018 |
| **Title** | Unified Task Table |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | All queues (Ingestion, Reflection, Activation, Archive) managed through a single `tasks` table. Separate queue tables are prohibited. |
| **Context** | Multiple queue tables increase schema complexity and operational overhead. A unified table with task_type discriminator provides the same functionality with simpler maintenance. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Separate tables for each queue type. |
| **Trade-offs** | Unified table simplifies schema but requires task_type-based routing logic. |
| **Review Trigger** | Queue management complexity exceeding design expectations. |
| **Related Principles** | G-009 |
| **Related Documents** | 04 §14.3, 08 §9 |
| **Tags** | tasks, queue, unified-table |
| **Keywords** | tasks, queue, unified, ingestion, reflection, activation, archive |
| **Evidence Coverage** | 04, 08 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Task priority and scheduling algorithms TBD. |

---

### ENG-019: Candidate Schema Independent of MemoryNode

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-019 |
| **Title** | Candidate Schema Design |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Candidate is an independent table, separate from MemoryNode. It is the working object of Reflection. Promotion (Candidate → MemoryNode) requires full evidence chain verification. |
| **Context** | Mixing Candidate with MemoryNode blurs the distinction between unverified hypothesis and confirmed memory. Independent table enforces the promotion gate. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Using a status field within MemoryNode to represent candidates. |
| **Trade-offs** | Independent table is cleaner but adds a table to the schema. |
| **Review Trigger** | Candidate-MemoryNode boundary confusion during implementation. |
| **Related Principles** | G-020 |
| **Related Documents** | 08 §4 |
| **Tags** | candidate, promotion, reflection |
| **Keywords** | candidate, promotion, memorynode, reflection, evidence |
| **Evidence Coverage** | 08 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Promotion criteria refinement based on implementation experience. |

---

### ENG-020: Ingestion Pipeline Mandatory for All Memory

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-020 |
| **Title** | Ingestion Pipeline Enforcement |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | All memory enters through Ingestion Pipeline: Chunking → Extraction → Entity Linking → Validation → Observation Store. No bypass allowed. `ingested_by` field restricted to `ingestion_pipeline`. |
| **Context** | Bypassing the pipeline breaks evidence chain construction, entity linking, and scoring. The pipeline is the only legal entry point for all memory. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing direct memory creation for trusted sources. |
| **Trade-offs** | Pipeline enforcement adds latency but guarantees data quality and traceability. |
| **Review Trigger** | Any proposal to create memory outside the pipeline. |
| **Related Principles** | G-021 |
| **Related Documents** | 07 §2.4 (P4), 06 §3.2 |
| **Tags** | ingestion, pipeline, mandatory |
| **Keywords** | ingestion, pipeline, chunking, extraction, entity-linking, validation |
| **Evidence Coverage** | 07, 06 |
| **Known Gaps** | Pipeline performance optimization TBD. |
| **Future Enrichment** | Implementation will define pipeline optimization strategies. |

---

### ENG-021: Three-Score Separation (Confidence / Importance / Signal Strength)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-021 |
| **Title** | Three-Score Separation Principle |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Three scoring dimensions are never mixed: confidence (belief certainty), importance (retrieval priority), signal_strength (evidence weight). Each computed independently. |
| **Context** | Mixing scores conflates orthogonal dimensions and corrupts both retrieval and reflection quality. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Single composite score. |
| **Trade-offs** | Three separate scores require more computation but preserve dimensional purity. |
| **Review Trigger** | Score correlation analysis showing dimension mixing. |
| **Related Principles** | G-022 |
| **Related Documents** | 01 §6, 06 §3.2 |
| **Tags** | scoring, three-score, separation |
| **Keywords** | confidence, importance, signal-strength, scoring |
| **Evidence Coverage** | 01, 06 |
| **Known Gaps** | Scoring algorithm implementation TBD. |
| **Future Enrichment** | Implementation will define concrete scoring formulas. |

---

### ENG-022: State = Belief + Current Context (Runtime Only)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-022 |
| **Title** | State Runtime Activation |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | State is not persisted to database. State = Belief + Current Context. State is a runtime activation computed by Activation Engine, cached in State Cache, and consumed by Context Builder. |
| **Context** | Persisting State would conflate runtime context with stored memory. State changes with every query context; storing it would create stale data. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Persisting State as a MemoryNode level. |
| **Trade-offs** | Runtime-only State avoids stale data but requires recomputation on each access. |
| **Review Trigger** | Performance profiling showing State recomputation is a bottleneck. |
| **Related Principles** | G-023 |
| **Related Documents** | 08 §3.3, 06 §3.4 |
| **Tags** | state, runtime, activation |
| **Keywords** | state, belief, context, runtime, activation, cache |
| **Evidence Coverage** | 08, 06 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | State caching strategy refinement. |

---

### ENG-023: Service Independence (No Cross-Service Sync Calls)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-023 |
| **Title** | Service Independence Principle |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Cross-service synchronous calls are prohibited. Services coordinate through Domain Events and Task Runtime, not direct method calls. |
| **Context** | Direct service calls create tight coupling, circular dependencies, and deployment entanglement. Event-driven coordination preserves independence. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing direct service calls for performance-critical paths. |
| **Trade-offs** | Event-driven adds latency but preserves loose coupling and independent deployability. |
| **Review Trigger** | Any proposal for cross-service synchronous call. |
| **Related Principles** | G-024 |
| **Related Documents** | 10_1 §4.4, 10_4 §2.2 |
| **Tags** | service-independence, event-driven |
| **Keywords** | service, independence, event, coupling, orchestration |
| **Evidence Coverage** | 10_1, 10_4 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Event schema design and delivery guarantees TBD. |

---

### ENG-024: Engine as Domain Capability (Not Agent, Not Service)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-024 |
| **Title** | Engine Definition as Domain Capability |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Engine represents a domain capability (Ingestion, Reflection, Activation, Retrieval, Context Building, Scheduler, Entity, Relationship). Engines must be stateless, reusable, and capability-oriented. Composite Engines compose Atomic Engines. |
| **Context** | Previous "MemoryEngine" concept was too broad. Redefining as Domain Capability clarifies responsibilities and enables compositional design. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Keeping MemoryEngine as a monolithic orchestrator. |
| **Trade-offs** | Domain Capability model is more granular but enables better reuse and testing. |
| **Review Trigger** | Engine responsibility boundary disputes during implementation. |
| **Related Principles** | G-025 |
| **Related Documents** | 06 §3.1, 08 §17.8 |
| **Tags** | engine, domain-capability, composition |
| **Keywords** | engine, domain, capability, atomic, composite |
| **Evidence Coverage** | 06, 08 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Engine interface contracts TBD. |

---

### ENG-025: Engine Does Not Directly Access Repository

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-025 |
| **Title** | Engine-Repository Boundary |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Engines do not directly access Repository. Data persistence is handled by Service + Repository layer. Service is the orchestration layer. |
| **Context** | Allowing Engine-Repository direct access breaks the layered architecture and creates coupling between domain logic and data access. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing Engine to access Repository directly for performance. |
| **Trade-offs** | Service-mediated access adds indirection but preserves architectural boundaries. |
| **Review Trigger** | Any proposal for Engine-Repository direct access. |
| **Related Principles** | G-026 |
| **Related Documents** | 08 §17.9 |
| **Tags** | engine, repository, boundary |
| **Keywords** | engine, repository, service, boundary, layering |
| **Evidence Coverage** | 08 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Service-Engine-Repository interface contracts TBD. |

---

### ENG-026: Query-First Architecture

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-026 |
| **Title** | Query-First Design Philosophy |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Memory Hub is a Query-First architecture. Query is high-frequency; Mutation (merge, archive, reflect) is low-frequency. Design optimizes for query performance. |
| **Context** | Memory Hub is primarily read by agents. Write operations are infrequent and can tolerate higher latency. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Balanced read/write optimization. |
| **Trade-offs** | Query-first may slightly slow writes but dramatically improves agent response times. |
| **Review Trigger** | Write-heavy workload patterns emerging. |
| **Related Principles** | G-027 |
| **Related Documents** | 10_3, 10_5 |
| **Tags** | query-first, performance, read-optimized |
| **Keywords** | query, first, read, performance, mutation |
| **Evidence Coverage** | 10_3, 10_5 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Query planner optimization strategies TBD. |

---

### ENG-027: Entity Merge via Asynchronous Reference Migration

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-027 |
| **Title** | Entity Merge Strategy |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Entity Merge uses asynchronous Reference Migration: EntityService merges → publishes EntityMerged event → Task Runtime asynchronously migrates references, updates relationships, rebuilds indexes. |
| **Context** | Merge is low-frequency; Query is high-frequency. Synchronous merge would block queries during migration. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Synchronous entity merge. |
| **Trade-offs** | Async migration introduces brief inconsistency window but keeps query path simple. |
| **Review Trigger** | Merge frequency increasing beyond design expectations. |
| **Related Principles** | G-028 |
| **Related Documents** | 10_5 §7, 12_Architecture_Decisions ADR-006 |
| **Tags** | entity-merge, async, reference-migration |
| **Keywords** | merge, async, reference, migration, event-driven |
| **Evidence Coverage** | 10_5, 12 |
| **Known Gaps** | Reference migration completeness verification TBD. |
| **Future Enrichment** | Implementation will define migration verification criteria. |

---

### ENG-028: EntityID Never Changes

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-028 |
| **Title** | EntityID Stability |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | EntityID is the stable anchor of identity. It never changes. All attribute evolution (Canonical Name, Alias, Metadata, Relationships, Type) occurs through evidence-driven attribute updates. |
| **Context** | Changing EntityID would break all relationships, references, and evidence chains pointing to that Entity. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing EntityID rotation during rename/merge. |
| **Trade-offs** | Static ID preserves all references; rotation would require cascading updates. |
| **Review Trigger** | Any proposal to rotate or change EntityID. |
| **Related Principles** | G-029 |
| **Related Documents** | 10_5 §3.1, 12_Architecture_Decisions ADR-008 |
| **Tags** | entity-id, stability, identity |
| **Keywords** | entity, id, stability, identity, anchor |
| **Evidence Coverage** | 10_5, 12 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Identity resolution algorithms TBD. |

---

### ENG-029: No Entity Version Table

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-029 |
| **Title** | Entity History via Evidence, Not Version Table |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | No separate Entity version table. Entity history is reconstructed from L0 Memory + Evidence Chain + Domain Events + Audit trail. Entity represents Current Best Identity only. |
| **Context** | Version tables duplicate evidence stored elsewhere and create synchronization problems. Evidence-based reconstruction is more reliable. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Maintaining a version table for Entity attributes. |
| **Trade-offs** | No version table simplifies schema but requires evidence-based history reconstruction. |
| **Review Trigger** | History reconstruction proving impractical at scale. |
| **Related Principles** | G-030 |
| **Related Documents** | 10_5 §11.4, 12_Architecture_Decisions ADR-007 |
| **Tags** | entity-history, evidence-based, no-version-table |
| **Keywords** | entity, history, version, evidence, reconstruction |
| **Evidence Coverage** | 10_5, 12 |
| **Known Gaps** | History reconstruction query patterns TBD. |
| **Future Enrichment** | Implementation will define reconstruction query patterns. |

---

### ENG-030: Unified Node/Edge/Memory/Retrieval Models

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-030 |
| **Title** | Unified Model Strategy |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Everything is Entity (unified node model). Everything is Relationship (unified edge model). Everything is MemoryNode (unified memory model). Retrieval is Graph + Vector + Archive + Context Builder synergy. |
| **Context** | Multiple specialized tables for similar concepts increase schema complexity and maintenance burden. Unified models with discriminators provide flexibility. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Separate tables for each entity type, relationship type, and memory type. |
| **Trade-offs** | Unified tables are simpler but require discriminator-based filtering. |
| **Review Trigger** | Discriminator-based filtering proving insufficient for performance. |
| **Related Principles** | G-031 |
| **Related Documents** | 04 §17.1–17.4 |
| **Tags** | unified-model, node, edge, memory |
| **Keywords** | unified, node, edge, memory, retrieval, synergy |
| **Evidence Coverage** | 04 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Discriminator index optimization TBD. |

---

### ENG-031: Three-Layer Tag System (System / AI / User)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-031 |
| **Title** | Tag System Architecture |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Three tag layers: System Tags (auto-generated, technical), AI Tags (auto-maintained, thematic), User Tags (manually created, classification). Tags are metadata, not primary interaction entry. |
| **Context** | A single flat tag system conflates automated and manual tagging, creating maintenance burden. Three layers separate concerns. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Single unified tag system. |
| **Trade-offs** | Three layers add schema complexity but prevent tag system abuse. |
| **Review Trigger** | Tag system misuse or confusion between layers. |
| **Related Principles** | G-032 |
| **Related Documents** | 04 §11 |
| **Tags** | tag-system, metadata, three-layer |
| **Keywords** | tag, system, ai, user, metadata, layering |
| **Evidence Coverage** | 04 |
| **Known Gaps** | Tag extraction algorithm TBD. |
| **Future Enrichment** | Implementation will define tag extraction and maintenance criteria. |

---

### ENG-032: Vector Storage Upgrade Through Abstraction

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-032 |
| **Title** | Vector Storage Abstraction |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | All vector storage upgrades (pgvector ivfflat → hnsw → external store) go through an abstraction layer. Schema does not change; only the retrieval engine implementation changes. |
| **Context** | Direct coupling to a specific vector database creates vendor lock-in and migration risk. Abstraction enables transparent upgrades. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Hard-coding vector database implementation. |
| **Trade-offs** | Abstraction layer adds code complexity but enables transparent upgrades. |
| **Review Trigger** | Need to switch vector database vendors. |
| **Related Principles** | G-033 |
| **Related Documents** | 04 §10.2, 08 §11.3–11.4 |
| **Tags** | abstraction, vector-storage, upgrade |
| **Keywords** | abstraction, vector, upgrade, pgvector, hnsw, external |
| **Evidence Coverage** | 04, 08 |
| **Known Gaps** | Abstraction interface design TBD. |
| **Future Enrichment** | Implementation will define the abstraction contract. |

---

### ENG-033: In-Memory Cache for V1, Redis for V2+

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-033 |
| **Title** | Cache Strategy Evolution |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | V1 uses In-Memory Cache only. Redis is prohibited in V1. V2+ upgrade path from In-Memory to Redis Distributed Cache via abstracted Cache Interface. |
| **Context** | Introducing Redis at MVP increases infrastructure complexity. In-Memory is sufficient for single-instance deployment. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Using Redis from day one. |
| **Trade-offs** | In-Memory cache is simpler but does not support multi-instance deployment. |
| **Review Trigger** | Multi-instance deployment requirement. |
| **Related Principles** | G-034 |
| **Related Documents** | 08 §10 |
| **Tags** | cache, in-memory, redis, evolution |
| **Keywords** | cache, in-memory, redis, distributed, evolution |
| **Evidence Coverage** | 08 |
| **Known Gaps** | Cache invalidation strategy TBD. |
| **Future Enrichment** | Implementation will define cache lifecycle management. |

---

### ENG-034: Shared Domain Engine Concept

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-034 |
| **Title** | Shared Domain Engine |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | One Service can orchestrate multiple Domain Engines. Engines are shared capabilities, not owned by a single Service. |
| **Context** | Tight Engine-to-Service mapping creates duplication. Shared engines enable compositional design. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | One-to-one Service-Engine mapping. |
| **Trade-offs** | Shared engines reduce duplication but require careful responsibility boundaries. |
| **Review Trigger** | Engine responsibility conflicts between Services. |
| **Related Principles** | G-035 |
| **Related Documents** | 10_1 §6.3, 12_Architecture_Decisions ADR-010 |
| **Tags** | domain-engine, shared, orchestration |
| **Keywords** | engine, shared, orchestration, service, composition |
| **Evidence Coverage** | 10_1, 12 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Engine responsibility matrix TBD. |

---

### ENG-035: Memory Hub as Witness Outputs Context, Not Conclusion

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-035 |
| **Title** | Memory Hub Output Discipline |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Memory Hub outputs Context (facts, related memories, confidence scores). Agent outputs Conclusion (decisions, recommendations, plans). |
| **Context** | Memory Hub providing conclusions would blur the Witness/Actor boundary and mislead users about responsibility attribution. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Memory Hub providing contextual recommendations. |
| **Trade-offs** | Strict output discipline preserves clarity but may feel limiting for users expecting AI assistance. |
| **Review Trigger** | User requests for Memory Hub recommendations. |
| **Related Principles** | G-036 |
| **Related Documents** | 07 §2.9 (P9) |
| **Tags** | output-discipline, context, conclusion |
| **Keywords** | output, context, conclusion, witness, actor |
| **Evidence Coverage** | 07 |
| **Known Gaps** | None. Well-documented with boundary examples. |
| **Future Enrichment** | Output format refinement TBD. |

---

### ENG-036: Project as Entity, Not Separate Table

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-036 |
| **Title** | Project Stored as Entity |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Project is stored in the `entities` table as `entity_type = 'Project'`. No separate Project table. |
| **Context** | Project is fundamentally an Entity with lifecycle and state changes. Separate table duplicates functionality already provided by the entities table with entity_type discriminator. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Separate projects table. |
| **Trade-offs** | Unified entities table is simpler but requires entity_type filtering for project-specific queries. |
| **Review Trigger** | Project-specific queries proving too complex with entity_type filtering. |
| **Related Principles** | G-037 |
| **Related Documents** | 08 §2.9, 04 §2.2 |
| **Tags** | project, entity, unified-model |
| **Keywords** | project, entity, unified, table |
| **Evidence Coverage** | 08, 04 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Project-specific query patterns TBD. |

---

### ENG-037: No Direct Repository Access by Engine

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-037 |
| **Title** | Engine-Repository Isolation |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | EngineRepository maintains persistence boundary. It does not perform merge decisions, alias conflict decisions, or relationship validation. Repository returns Domain Objects only — Never Projection, Never DTO. |
| **Context** | Allowing Repository to make domain decisions creates coupling between persistence and business logic. Pure data access preserves clean boundaries. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Allowing Repository to return projections or DTOs directly. |
| **Trade-offs** | Repository returning only Domain Objects adds a mapping layer but preserves clean architecture. |
| **Review Trigger** | Repository leaking domain logic into persistence layer. |
| **Related Principles** | G-038 |
| **Related Documents** | 10_1 §17.11 |
| **Tags** | repository, isolation, domain-object |
| **Keywords** | repository, domain-object, projection, dto, boundary |
| **Evidence Coverage** | 10_1 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Repository interface contracts TBD. |

---

### ENG-038: Reflection Mode Switching (Auto / Manual / Hybrid)

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-038 |
| **Title** | Reflection Mode Configuration |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Default is Auto (automatic Reflection + automatic Promotion). Three modes available: Auto, Manual (manual trigger + manual confirmation), Hybrid (automatic Reflection + manual Promotion confirmation). |
| **Context** | Different users may have different trust levels in automated reflection. Mode switching provides operational flexibility. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Single fixed reflection mode. |
| **Trade-offs** | Mode switching adds configuration complexity but provides user control. |
| **Review Trigger** | User requests for additional reflection modes. |
| **Related Principles** | G-039 |
| **Related Documents** | 08 §13.3 |
| **Tags** | reflection, mode-switching, configuration |
| **Keywords** | reflection, auto, manual, hybrid, mode, configuration |
| **Evidence Coverage** | 08 |
| **Known Gaps** | Mode switching implementation TBD. |
| **Future Enrichment** | Implementation will define mode switching interface. |

---

### ENG-039: Entity Type Extensible Without Schema Migration

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-039 |
| **Title** | Entity Type Extensibility |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Future Entity Types (Agent, Tool, Model, Document, Person) are added by inserting new `entity_type` values. No schema migration required. Existing Entity types can be changed at any time. |
| **Context** | Hard-coding entity types in schema would require migration for every new type. Discriminator-based extensibility supports 5-10 year evolution without schema changes. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Separate table for each entity type. |
| **Trade-offs** | Discriminator-based approach requires type-filtering queries but eliminates migrations. |
| **Review Trigger** | Entity type proliferation causing query complexity. |
| **Related Principles** | G-040 |
| **Related Documents** | 04 §3.3 |
| **Tags** | entity-type, extensibility, migration-free |
| **Keywords** | entity, type, extensible, migration, discriminator |
| **Evidence Coverage** | 04 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Type validation rules TBD. |

---

### ENG-040: Memory Hub Is Not a Decision-Making System

| Field | Content |
|-------|---------|
| **Decision ID** | ENG-040 |
| **Title** | Memory Hub Non-Decision Role |
| **Status** | Final Decision |
| **Decision Version** | d1.0 |
| **Decision** | Memory Hub does not make technical, architectural, product, commercial, or personal decisions. These are Agent responsibilities. |
| **Context** | Allowing Memory Hub to make decisions would violate the Witness principle and create responsibility confusion. |
| **Current Understanding** | Full |
| **Completeness / Knowledge Maturity** | High |
| **Alternatives Considered** | Memory Hub providing decision suggestions. |
| **Trade-offs** | Restricting to observation/record/organize/reflect/retrieve preserves clear responsibility boundaries. |
| **Review Trigger** | Any proposal to add decision-making capability to Memory Hub. |
| **Related Principles** | G-041 |
| **Related Documents** | 07 §3.2 |
| **Tags** | non-decision, boundary, agent-responsibility |
| **Keywords** | decision, non-decision, boundary, agent, responsibility |
| **Evidence Coverage** | 07 |
| **Known Gaps** | None. Well-documented. |
| **Future Enrichment** | Decision boundary refinement TBD. |

---

## 4. Decision Index

| ID | Title | Status | Maturity |
|----|-------|--------|----------|
| ENG-001 | Memory Hub as Infrastructure | Final Decision | High |
| ENG-002 | Memory Hub as Witness, Not Actor | Final Decision | High |
| ENG-003 | Agent Outside Memory Hub | Final Decision | High |
| ENG-004 | Agent Cannot Directly Modify Memory | Final Decision | High |
| ENG-005 | Summary Is Observation | Final Decision | High |
| ENG-006 | Evidence-Based Memory | Final Decision | High |
| ENG-007 | No Orphan Memory | Final Decision | High |
| ENG-008 | Reflection Is Memory Maintenance | Final Decision | High |
| ENG-009 | Entity Admission Criteria | Final Decision | High |
| ENG-010 | Entity vs Observation Distinction | Final Decision | High |
| ENG-011 | MemoryNode Unified Hierarchy | Final Decision | High |
| ENG-012 | Reflect Derivation Chain | Final Decision | High |
| ENG-013 | Memory Immutability | Final Decision | High |
| ENG-014 | Archive as Cognitive Compression | Final Decision | High |
| ENG-015 | UUIDv7 for All Keys | Final Decision | High |
| ENG-016 | Independent Vector Table | Final Decision | High |
| ENG-017 | Supabase pgvector MVP → External V2+ | Final Decision | High |
| ENG-018 | Unified tasks Table | Final Decision | High |
| ENG-019 | Candidate Schema Independent | Final Decision | High |
| ENG-020 | Ingestion Pipeline Mandatory | Final Decision | High |
| ENG-021 | Three-Score Separation | Final Decision | High |
| ENG-022 | State Runtime Activation | Final Decision | High |
| ENG-023 | Service Independence | Final Decision | High |
| ENG-024 | Engine as Domain Capability | Final Decision | High |
| ENG-025 | Engine-Repository Boundary | Final Decision | High |
| ENG-026 | Query-First Architecture | Final Decision | High |
| ENG-027 | Async Reference Migration | Final Decision | High |
| ENG-028 | EntityID Stability | Final Decision | High |
| ENG-029 | No Entity Version Table | Final Decision | High |
| ENG-030 | Unified Model Strategy | Final Decision | High |
| ENG-031 | Three-Layer Tag System | Final Decision | High |
| ENG-032 | Vector Storage Abstraction | Final Decision | High |
| ENG-033 | Cache Evolution Strategy | Final Decision | High |
| ENG-034 | Shared Domain Engine | Final Decision | High |
| ENG-035 | Output Discipline (Context vs Conclusion) | Final Decision | High |
| ENG-036 | Project as Entity | Final Decision | High |
| ENG-037 | Engine-Repository Isolation | Final Decision | High |
| ENG-038 | Reflection Mode Switching | Final Decision | High |
| ENG-039 | Entity Type Extensibility | Final Decision | High |
| ENG-040 | Memory Hub Non-Decision Role | Final Decision | High |

---

## 5. Tag Index

| Tag | Associated Decisions |
|-----|---------------------|
| architecture | ENG-001, ENG-002, ENG-003, ENG-040 |
| boundary | ENG-002, ENG-003, ENG-004, ENG-025, ENG-037 |
| entity | ENG-009, ENG-010, ENG-027, ENG-028, ENG-029, ENG-036, ENG-039 |
| evidence | ENG-006, ENG-007, ENG-029 |
| engine | ENG-024, ENG-025, ENG-034, ENG-037 |
| memory | ENG-011, ENG-012, ENG-013, ENG-014, ENG-020, ENG-022 |
| performance | ENG-016, ENG-017, ENG-026 |
| repository | ENG-025, ENG-037 |
| service | ENG-023, ENG-027, ENG-034 |
| storage | ENG-015, ENG-016, ENG-017, ENG-032, ENG-033 |
| tag | ENG-031 |
| unified-model | ENG-011, ENG-030, ENG-036 |

---

## 6. Document Change Record

| Version | Date | Change Description | Status |
|---------|------|-------------------|--------|
| 1.0 | 2026-07-01 | Initial Engineering Decision Register — 40 decisions extracted from Phase A and Phase B documentation | ✅ Created |

---

## 7. Knowledge Evolution Log

This section tracks understanding enrichment over time.

| Date | Enrichment | Source |
|------|-----------|--------|
| — | Register created. All 40 decisions based on approved Phase A and Phase B documentation. | Current repository state |
| TBD | Post-implementation enrichment: rationale validation, alternatives comparison, trade-off verification. | Future implementation experience |
| TBD | Memory Hub import of historical discussions may enrich decisions with original context. | Future Reflection |
| TBD | Engineering decisions may be refined after MVP implementation reveals practical constraints. | Future human review |

---

## 8. Usage Notes

### For Human Developers

* Use this register as a reference when making implementation decisions.
* If you encounter a situation not covered by existing decisions, document it and propose a new ENG entry.
* Do not modify existing decisions without explicit human approval and version increment.

### For AI Assistants

* Read this register before implementing any feature that touches a registered decision.
* If a proposed implementation conflicts with a registered decision, flag it for human review.
* Do not infer or fabricate rationale for decisions not explicitly documented.
* When enriching understanding, append to the relevant decision record with a new version (d1.1, d1.2, etc.) and update Knowledge Evolution Log.
* Follow the AI Development Workflow (13_AI_Development_Workflow.md) for state transitions, gate system, and responsibility matrix.

### For Future Memory Hub Reflection

* This register itself may become a memory source for the Memory Hub.
* Reflection may identify patterns across decisions that suggest architectural principles.
* Historical discussion import may enrich decisions with original context and rationale.
* Knowledge enrichment must follow the Knowledge Lifecycle in 13 (Reflection → Candidate → Admission → Evolution).

---

## 9. Relationship with 13_AI_Development_Workflow

This register constrains the AI Development Workflow. Key intersections:

| ENG Decision | Workflow Section | Interaction |
|-------------|-----------------|-------------|
| ENG-002 (Witness, Not Actor) | §3 Human/AI Matrix | Defines AI prohibited actions |
| ENG-003 (Agent External) | §9 Stateless Collaboration | Agent boundary preserved |
| ENG-004 (Agent Write Restriction) | §6 Implementation | Agent writes flow through pipeline |
| ENG-006 (Evidence-Based) | §8 Verification | Verification must be evidence-based |
| ENG-008 (Reflection Scope) | §10 Knowledge Lifecycle | Reflection limited to maintenance |
| ENG-023 (Service Independence) | §7 Escalation | Cross-service issues escalated |
| ENG-038 (Reflection Mode) | §10.1 Reflection | Mode selection affects workflow |
| ENG-040 (Non-Decision Role) | §3.3 Prohibited Actions | Memory Hub never makes decisions |

---

*This document is a living Engineering Decision Register. Decisions are stable; understanding evolves. GitHub remains the project's Single Source of Truth.*
