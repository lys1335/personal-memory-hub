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

QueryService — Domain Service design, five Query Capabilities (Retrieval/Search/Browse/Projection/Analytics), Query Pipeline with Planner, Engine interaction, Service Independence, Consumer-Agnostic Interface, Stable Result Contract.

### 10_4_Implementation_ReflectionService.md

ReflectionService — Memory Pyramid evolution orchestration, four Capabilities (Reflect/Consolidate/Summarize/Evaluate), Reflection Pipeline with Semantic Evolution Decision, Evidence Completeness Constraint, Memory Pyramid theory (Scope-based abstraction, not time-based), Maximum Reflection Horizon, Recovery Baseline with L0 Protection, Incremental Propagation.

### 10_5_Implementation_EntityService.md

EntityService — Identity Management capability owner, five Capability groups (Identity/Merge/Alias/Relationship/Profile Update), EntityID stability, Asynchronous Reference Migration, three-state lifecycle (Created→Active→Merged), Domain Events, Evidence-based Entity (L0 support required), No Entity Version.

### 10_6_Implementation_TaskRuntime.md

Task Runtime — Generic task execution infrastructure, domain-agnostic task model, event-driven task chaining, minimal lifecycle (Pending→Running→Completed/Failed→Retry→Dead), at-least-once execution with idempotency, unified scheduler (not Cron), startup recovery, maintenance manager, layered observability.

### 13_Architecture_Guidelines.md

Living Guideline — 65 numbered guidelines (G-001~G-065) covering Public API, Service Design, Engine Design, Repository Design, Query Design, Reflection & Memory Evolution, Entity Identity, Task Runtime, API Entry Layer, Testing, Review Rules, Evolution Rules.

### 10_8_Implementation_Testing.md

Testing Implementation Design — 19 Testing Principles, Testing Responsibilities per Layer (Entry/Service/Engine/Repository/Integration/E2E), Mock Strategy, Deterministic vs Evaluation Testing, Test Data Management, Regression Strategy, Future Extensibility.

### 11_Implementation_Roadmap.md

Implementation Roadmap — Six engineering milestones (Foundation/Core Memory/Query&Reflection/Entry&API/Testing&MVP), MVP lifecycle definition, coding order (dependency-driven), repository strategy, branch strategy, four-level review workflow, CI strategy, milestone completion criteria, AI engineering risks, implementation gate system, state-driven workflow, AI-driven engineering principles.

### 12_Engineering_Register.md

Engineering Decision Register — Living register of 40 confirmed engineering decisions (ENG-001~ENG-040) extracted from all Phase A and Phase B documentation. Each decision includes stable ID, current understanding assessment, knowledge maturity, alternatives considered, trade-offs, review triggers, evidence coverage, known gaps, and future enrichment plan. Tag index and usage notes for humans and AI.

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
* 13_Architecture_Guidelines（Phase B Living Guideline）

Current Progress: 20 / 20 completed
---

# Planned Documents
* 13_AI_Development_Workflow.md
* 14_Final_Implementation_Review.md

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

Last Updated: 2026-07-01
