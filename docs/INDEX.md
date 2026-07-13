# Personal Memory Hub - Documentation Index

## Project Overview

Personal Memory Hub is a long-term memory system designed for personal AI assistants.

Core goals:

* Persistent memory across models and sessions
* Evidence-based memory management
* Structured entity and relationship graph
* Capability-based agent architecture
* Local-first deployment with optional cloud integration
* Human-reviewable memory lifecycle

---

# Reading Order

## Phase 1 - Foundation

### 01_MemoryHub_Foundation.md

Project vision, goals, principles, scope, and overall architecture direction.

---

## Phase 2 - Core Architecture

### 02_MemoryEngine_ContextBuilder.md

Memory Engine and Context Builder architecture.

### 06_Runtime_Architecture.md

Runtime architecture and execution flow.

### 07_Boundary_Review.md

System boundary definition and responsibility separation.

### 08_Implementation_Architecture.md

Implementation-oriented architecture design.

---

## Phase 3 - Data Model

### 03_Entity_MemoryGraph.md

Entity model, memory graph, and relationship structure.

### 09_Database_Physical_Design.md

Physical database schema and storage design.

---

## Phase 4 - Memory System

### 04_Schema_Archive_Reflect.md

Schema design, archive strategy, and reflection concepts.

### 05_MemoryLifecycle_ReflectionEngine.md

Memory lifecycle and reflection engine design.

---

## Phase 5 - Implementation Design

### 10_1_Implementation_Service_Layer.md

Implementation Service Layer — layered architecture, service classification, engine composition, repository layer, dependency rules, MVP order, project memory philosophy.

### 10_3_Implementation_QueryService.md

QueryService — Domain Service design, five Query Capabilities (Retrieval/Search/Browse/Projection/Analytics), Unified Read Workflow (Validation→Planning→Repository Coordination→Domain Processing→Projection→Result Assembly), Read Pipeline Principles, Repository Coordination rules, Projection Three-Level Boundary, Query Purity, Capability Composition, Transaction Strategy, Error Mapping, Language Preservation, Query Idempotence, Observational Consistency, Consumer-Agnostic Interface, Stable Result Contract, Verification Strategy.

### 10_4_Implementation_ReflectionService.md

ReflectionService — Memory Pyramid evolution orchestration, four Capabilities (Reflect/Consolidate/Summarize/Evaluate), Reflection Pipeline with Semantic Evolution Decision, Evidence Completeness Constraint, Memory Pyramid theory (Scope-based abstraction, not time-based), Maximum Reflection Horizon, Recovery Baseline with L0 Protection, Incremental Propagation.

### 10_5_Implementation_EntityService.md

EntityService — Identity Management capability owner, six Capability groups (Identity Management/Identity Consolidation/Alias/Relationship/Metadata Update), EntityID stability, Asynchronous Reference Graph Update, Entity Permanence (no delete/destroy/restore), Domain Events, Evidence-based Entity (L0 support required), No Entity Version, Memory Reference Immutability, QueryService Resolution (Alias/Canonical/Merge-Graph), Relationship Evolution.

### 10_6_Implementation_TaskRuntime.md

Task Runtime + TaskService — Generic task execution infrastructure with TaskService execution orchestration layer. TaskService owns execution lifecycle/scheduling/retry/context/history, never business decisions. Execution Scope concept (immutable during execution). Scheduling determines when, not what. Periodic creates new Tasks. Retry preserves Execution Scope. Incremental Processing Principle. MemoryService/EntityService coordination (execution-agnostic). One Task = One Transaction. Failure Isolation. Completed Task Immutability.

### 13_Architecture_Guidelines.md

Living Guideline — 118 numbered guidelines (G-001~G-118) covering Foundation, Service Design, Engine Design, Repository Design, Query Design, Entity Design, Error/Validation, Testing, Evolution, and Documentation Governance (G-113~G-118).

### 10_8_Implementation_Testing.md

Testing Implementation Design — 19 Testing Principles, Testing Responsibilities per Layer (Entry/Service/Engine/Repository/Integration/E2E), Mock Strategy, Deterministic vs Evaluation Testing, Test Data Management, Regression Strategy, Future Extensibility.

### 11_Implementation_Roadmap.md

Implementation Roadmap — Six engineering milestones (Foundation/Core Memory/Query&Reflection/Entry&API/Testing&MVP), MVP lifecycle definition, coding order (dependency-driven), repository strategy, branch strategy, four-level review workflow, CI strategy, milestone completion criteria, AI engineering risks, implementation gate system, state-driven workflow, AI-driven engineering principles.

### 12_Engineering_Register.md

Engineering Decision Register — Living register of 40 confirmed engineering decisions (ENG-001~ENG-040) extracted from all Phase A and Phase B documentation. Each decision includes stable ID, current understanding assessment, knowledge maturity, alternatives considered, trade-offs, review triggers, evidence coverage, known gaps, and future enrichment plan. Tag index and usage notes for humans and AI.

### 13_AI_Development_Workflow.md

AI Development Workflow — Project lifecycle state machine (seven states), Human/AI responsibility matrix, Discussion→Decision→Design transition, gate system (Architecture/Engineering/AI/Human), implementation readiness criteria, engineering escalation procedures, verification framework (evidence-based, four-level), GitHub as Project State, stateless AI collaboration, knowledge lifecycle (Reflection→Candidate→Admission→Evolution), knowledge evolution preference (refinement over proliferation), future multi-workflow architecture extension point.

---

# Current Status

## Completed

* 01_MemoryHub_Foundation
* 02_MemoryEngine_ContextBuilder
* 03_Entity_MemoryGraph
* 04_Schema_Archive_Reflect
* 05_MemoryLifecycle_ReflectionEngine
* 06_Runtime_Architecture
* 07_Boundary_Review
* 08_Implementation_Architecture
* 09_Database_Physical_Design
* 10_1_Implementation_Service_Layer（Phase B 开始）
* 10_2_Implementation_MemoryService（Phase B-2）
* 10_3_Implementation_QueryService（Phase B-3）
* 10_4_Implementation_ReflectionService（Phase B-4）
* 10_5_Implementation_EntityService（Phase B-5）
* 10_6_Implementation_TaskRuntime（Phase B-6）
* 10_7_Implementation_API_Entry（Phase B-7）
* 10_8_Implementation_Testing（Phase B-8）
* 11_Implementation_Roadmap（Phase B-9）
* 12_Engineering_Register（Phase B-10）
* 13_AI_Development_Workflow（Phase B-11）
* 13_Architecture_Guidelines（Phase B Living Guideline）
* 14_Final_Implementation_Review（Phase B-12）
* D3.7_Error_Handling_DTO_Models（D3.7 — 已完成 2026-07-12）
* D3.8_Service_Test_Suite（D3.8 — 已完成 2026-07-13）
* D3.9_Documentation_Updates（D3.9 — 已完成 2026-07-13）

Current Progress: 25 / 25 completed
Phase D: D1 ✅ · D2 ✅ · D3 ✅ 🧊 Frozen
---

# Phase D — Implementation

## 05_Implementation/

### README.md

Implementation phase overview — milestones, coding order, review workflow, CI strategy.

### D1_Infrastructure_Foundation_Plan.md

D1 planning document — purpose, deliverables, work breakdown, definition of done, risks, handoff to D2.

### D2_Repository_Layer_Plan.md

D2 planning document — Repository Layer architecture, frozen design, verification guide.

### D3_Service_Layer_Plan.md

D3 planning document — Service Layer architecture, D3.1–D3.9 substages, definition of done, risks, handoff to D4. 🧊 Frozen.

### D3.7_Error_Handling_DTO_Models.md

D3.7 — DTO design, error model, exception mapping, validation strategy, versioning, serialization boundaries, verification checklist.

### D3.8_Service_Test_Suite.md

D3.8 — Service test architecture: contract testing, command/query testing, result verification, error contract testing, validation testing, exception mapping testing, boundary testing, determinism testing, compatibility testing, test taxonomy, verification strategy, documentation synchronization.

### D3.9_Documentation_Updates.md

D3.9 — Documentation governance: cross-reference verification, terminology consistency, document structure, guideline/ADR validation, README/INDEX/Roadmap synchronization, phase exit criteria, D3 freeze, architecture glossary, style guide, architecture registry.

## 06_Guides/

### D1_Verification_Guide.md

Complete human verification guide for D1 Infrastructure Foundation. Allows any developer to independently verify D1 implementation from a fresh clone.

### zh-CN/D1_Verification_Guide.md

简体中文本地化版本。适用于中文开发团队的日常工程使用。技术内容、命令、文件路径与英文版完全一致。

---

# Planned Documents
* D4 — Domain Engine documents (planned)
* D5 — Entry & API documents (planned)
* D6 — Testing & Stabilization documents (planned)

---

# Design Principles

## Architecture Principles

- Memory First
- Evidence-Based Memory
- Capability-Based Agent
- Structured Before LLM
- Long-Term Evolvability

## Development Principles

- Document-Driven Design
- Project Memory Philosophy
- Human Review First
- User-Controlled Architecture

---

# Glossary (Selected Terms)

## Evidence vs Observation

> **Evidence**: 原始输入数据，包括聊天记录、导入文档、用户输入等。Evidence 是不可变的原始事实。
>
> **Observation**: 从 Evidence 中提取的结构化信息。Observation 是 IngestionEngine 的产出物，作为 Memory 构建的基础。
>
> **关系**: Evidence → Observation → Memory。Evidence 是原始输入，Observation 是经过处理的中间产物。
>
> **引用**：02 §5.1, 05 §2.1, 10_2 §2

---

Last Updated: 2026-07-04
