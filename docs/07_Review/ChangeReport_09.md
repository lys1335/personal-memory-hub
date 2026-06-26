# Change Report 09 — Phase B Service Layer Architecture

> **日期**: 2026-06-26
> **阶段**: Phase B — 实现设计
> **触发原因**: Phase A 架构设计完成，进入实现设计阶段
> **生成文档**: 10_1_Implementation_Service_Layer.md
> **影响文档**: 01~09, README.md, INDEX.md

---

## 1. 概述

本次变更是 Project Memory Hub 从 Phase A（架构设计）进入 Phase B（实现设计）的首次变更。

核心变更是将 Phase A 的架构概念转化为**可编码的服务层架构**，定义了五层模型、Engine 重新定义、Repository 边界、API Entry Layer 术语变更、依赖规则和项目记忆哲学。

---

## 2. 变更清单

### 2.1 新增文档

#### 10_1_Implementation_Service_Layer.md

**为什么变更**: Phase A 已完成架构设计，需要一份总纲文档将架构转化为可编码的服务层设计，作为后续 10_2~10_N 的基础。

**变更内容**:
* 五层架构模型（Entry → Service → Engine → Repository → Database）
* Service 分类与职责（6 个 Service：Memory/Ingestion/Reflection/Query/Context/Task）
* Engine 清单与组成（11 个 Engine，MemoryEngine 为 Composite Engine）
* Repository 层定义（按 Domain Aggregate 组织，引入 QueryRepository）
* API Entry Layer 定义（REST/MCP/CLI/SDK/Agent）
* 依赖规则（分层依赖、Service DAG、Engine DAG、无层跳跃）
* MVP 实施顺序（B-1 至 B-7）
* 未来扩展策略
* 项目结构定义（entry/service/engine/repository/shared/）
* Project Memory 哲学（文档=长期记忆，Chat=工作记忆，代码=可执行记忆）

**影响**: 
* 所有后续 10_X 文档必须引用本文档的分层架构和依赖规则
* 01~09 中涉及 Service/Engine/Repository 边界的内容需同步更新
* 代码实现必须遵循本文档定义的依赖规则

**跨文档一致性**: 本文档与 01~09 完全一致，未引入新的架构范式。

---

### 2.2 更新文档

#### 01_MemoryHub_Foundation.md

**为什么变更**: 作为总纲文档，术语表需要覆盖新增的 Phase B 术语。

**变更内容**:
* 附录 A 术语表新增 "Memory Domain Orchestrator" 和 "Project Memory" 两个术语
* 版本号从 1.3 → 1.4

**影响**: 读者可通过总纲术语表快速理解 Phase B 新增概念。

**跨文档一致性**: 术语与 10_1 第 13 章完全一致。

---

#### 02_MemoryEngine_ContextBuilder.md

**为什么变更**: MemoryEngine 在 Phase B 重新定义为 Memory Domain Orchestrator，需要在原文档中明确这一变更。

**变更内容**:
* 新增第 2.3 节 "Memory Domain Orchestrator（Phase B 重新定义）"
* 明确 MemoryEngine 协调的 4 个子 Engine（Archive/Evidence/Relationship/Candidate）
* 明确 MemoryEngine 不直接访问 Repository
* 术语表 Memory Engine 条目补充 Phase B 变更说明
* 版本号从 1.5 → 1.6

**影响**: 
* 消除了 MemoryEngine 是"全能引擎"的歧义
* 明确了 MemoryEngine 通过 Service 层协调数据的约束

**跨文档一致性**: 
* 与 10_1 第 6.3 章 Composite Engine 模式完全一致
* 与 10_1 第 6.5 章 Engine 无 Repository 依赖完全一致
* 与 04 中 ContextBuilder 的说明一致

---

#### 06_Runtime_Architecture.md

**为什么变更**: Engine 的定义在 Phase B 被重新明确为 Domain Capability，需要在原文档中补充。

**变更内容**:
* 第 3.1 章新增 Engine 重新定义说明（无状态/可复用/能力导向/Composite Engine 模式）
* 版本号从 1.0 → 1.1

**影响**: 
* 明确了 Runtime Engine 不是 Agent、不是 Service、不是 Repository
* 为后续 10_2~10_N 的 Engine 实现设计提供了定义基础

**跨文档一致性**: 与 10_1 第 6 章 Engine 定义完全一致。

---

#### 08_Implementation_Architecture.md

**为什么变更**: API Layer 术语变更、Engine 重新定义、Service/Engine/Repository 边界需要在 Implementation Architecture 中体现。

**变更内容**:
* 第 8.1 节新增 "API Entry Layer（Phase B 术语变更）"，解释 API Layer → API Entry Layer 的变更
* 原有 8.2/8.3 节编号顺延为 8.3/8.5
* 第 17 章新增 17.7~17.10 四个 Phase B 原则：
  * 17.7 API Entry Layer
  * 17.8 Engine as Domain Capability
  * 17.9 No Direct Repository Access by Engine
  * 17.10 Project Memory Philosophy
* 版本号从 1.0 → 1.1

**影响**: 
* 明确了 API Entry Layer 的职责边界
* 明确了 Engine 的领域能力定位
* 明确了 Engine 不直接访问 Repository 的约束
* 确立了 Project Memory 哲学

**跨文档一致性**: 
* 与 10_1 第 8 章 API Entry Layer 完全一致
* 与 10_1 第 6 章 Engine 定义完全一致
* 与 10_1 第 9 章依赖规则完全一致

---

#### 09_Database_Physical_Design.md

**为什么变更**: Repository 按 Domain Aggregate 组织的新概念需要在数据库设计文档中体现。

**变更内容**:
* CR-006 → CR-007（编号顺延）
* 新增 CR-008 与 10_1 的一致性检查（Repository 按 Domain Aggregate 组织、QueryRepository、Engine 无 Repository 依赖、ContextService 无独立 Repository）
* 版本号从 1.1 → 1.2

**影响**: 
* 明确了数据库表结构与 Repository 层的映射关系
* 为 QueryRepository 的实现提供了理论基础

**跨文档一致性**: 与 10_1 第 5 章 Repository 定义完全一致。

---

#### 04_Schema_Archive_Reflect.md

**为什么变更**: ContextService 不拥有独立 Repository 是重要的架构约束，需要在 Schema 文档中记录。

**变更内容**:
* 第 15 章新增 Phase B 补充说明：ContextBuilder 是 Domain Engine，ContextService 不拥有独立 Repository
* 版本号从 1.2 → 1.3

**影响**: 
* 消除了 ContextService 是否有独立 Repository 的歧义
* 明确了 ContextBuilder 属于 Engine 层而非 Service 层

**跨文档一致性**: 与 10_1 第 4.4 章 ContextService 特殊性完全一致。

---

#### 05_MemoryLifecycle_ReflectionEngine.md

**为什么变更**: Engine 重新定义为 Domain Capability 需要在生命周期文档中体现。

**变更内容**:
* 第 16 章新增 16.6 "Engine as Domain Capability（Phase B 新增）"
* 版本号从 1.1 → 1.2

**影响**: 
* 明确了 IngestionEngine、ScoringEngine、ReflectionEngine、ActivationEngine 均为 Domain Capability
* 消除了 Engine 可能是 Agent 或服务层的歧义

**跨文档一致性**: 与 10_1 第 6 章 Engine 定义完全一致。

---

#### 03_Entity_MemoryGraph.md

**为什么变更**: Engine 重新定义作为 ADR 记录需要归档。

**变更内容**:
* 附录 A 新增 ADR-012 "Engine 重新定义（Phase B）"
* 版本号从 1.4 → 1.5

**影响**: 
* 将 Engine 重新定义作为架构决策记录归档
* 便于未来追溯设计决策

**跨文档一致性**: 与 10_1 第 6 章 Engine 定义完全一致。

---

#### 07_Boundary_Review.md

**为什么变更**: Engine 重新定义作为 ADR 记录需要归档。

**变更内容**:
* 附录 A 新增 ADR-012 "Engine 重新定义（Phase B）"
* 版本号从 1.0 → 1.1

**影响**: 
* 将 Engine 重新定义作为边界约束的 ADR 记录归档
* 确保边界原则与新的 Engine 定义一致

**跨文档一致性**: 与 10_1 第 6 章 Engine 定义完全一致。

---

#### README.md

**为什么变更**: Phase B 已开始，需要更新项目状态和文档列表。

**变更内容**:
* 文档列表新增 "Implementation Service Layer（Phase B 新增）"
* Phase B 状态从 "Planned" 改为 "Started"
* Phase B 子项标记 10_1 为已完成 ✅
* 版本号从 1.0 → 1.1

**影响**: 读者可清楚了解项目当前处于 Phase B 的 Service Layer 设计阶段。

**跨文档一致性**: 与 INDEX.md 和 10_1 完全一致。

---

#### INDEX.md

**为什么变更**: Phase 5 从 Planned 变为 Completed（10_1），需要更新阅读顺序、当前状态和设计原则。

**变更内容**:
* Phase 4 后新增 Phase 5 - Implementation Design 章节
* 10_1_Implementation_Service_Layer.md 从 Planned 移至 Completed
* Current Progress 从 9/9 更新为 10/10
* 设计原则更新为 Phase B 确认的五大原则（Memory First, Evidence-Based, Capability-Based, Document-Driven, Project Memory）
* 移除了原有的 Planned Documents 和 Phase 6/7 内容（整合进 Phase B  Started 状态）
* Last Updated 从 "2026-06" 更新为 "2026-06-26"

**影响**: 
* 读者可通过 INDEX 快速了解 Phase B 已开始
* 设计原则反映了 Phase B 确认的架构价值观

**跨文档一致性**: 与 README.md 和 10_1 完全一致。

---

## 3. 架构决策影响分析

### 3.1 MemoryEngine 重新定义的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 02 | MemoryEngine 定位为 Memory Domain Orchestrator | 新增第 2.3 节 |
| 06 | Runtime Engine 重新定义为 Domain Capability | 第 3.1 章补充 |
| 08 | Service/Engine/Repository 边界 | 新增 17.8/17.9 |
| 10_1 | 定义 MemoryEngine 协调的子 Engine | 第 6.3 章 Composite Engine |

### 3.2 Engine 重新定义的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 02 | MemoryEngine 不再是全能引擎 | 新增第 2.3 节 |
| 05 | 所有 Runtime Engine 重新定义 | 新增 16.6 |
| 06 | Engine 定义澄清 | 第 3.1 章补充 |
| 08 | Engine 边界约束 | 新增 17.8 |

### 3.3 Repository 按 Domain Aggregate 组织的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 09 | 表结构分组 | CR-008 新增 |
| 10_1 | Repository 定义 | 第 5 章 |

### 3.4 API Entry Layer 术语变更的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 08 | API Layer → API Entry Layer | 新增 8.1 |
| 10_1 | Entry 层定义 | 第 8 章 |

---

## 4. 跨文档一致性验证

### 4.1 术语一致性

| 术语 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10_1 | 一致? |
|------|----|----|----|----|----|----|----|----|----|------|-------|
| MemoryDomain Orchestrator | ✅ | ✅ | — | — | — | — | — | — | — | ✅ | ✅ |
| Engine as Domain Capability | — | — | — | — | ✅ | ✅ | — | ✅ | — | ✅ | ✅ |
| API Entry Layer | — | — | — | — | — | — | — | ✅ | — | ✅ | ✅ |
| ContextService 无 Repository | — | — | — | ✅ | — | — | — | — | — | ✅ | ✅ |
| Repository 按 Domain Aggregate | — | — | — | — | — | — | — | — | ✅ | ✅ | ✅ |
| Project Memory | ✅ | — | — | — | — | — | — | ✅ | — | ✅ | ✅ |
| One Capability One Implementation | — | — | — | — | — | — | — | ✅ | — | ✅ | ✅ |

### 4.2 依赖规则一致性

| 规则 | 08 | 10_1 | 一致? |
|------|----|------|-------|
| 分层依赖（Entry→Service→Engine→Repository→DB） | ✅ | ✅ | ✅ |
| 无层跳跃 | ✅ | ✅ | ✅ |
| Service DAG | ✅ | ✅ | ✅ |
| Engine DAG | ✅ | ✅ | ✅ |
| Engine 无 Repository 依赖 | — | ✅ | ✅ |
| Repository 不互相调用 | ✅ | ✅ | ✅ |
| MemoryEngine 不直接访问 Repository | — | ✅ | ✅ |

### 4.3 版本号一致性

| 文档 | 变更前 | 变更后 | 备注 |
|------|--------|--------|------|
| 01 | 1.3 | 1.4 | 术语表新增 |
| 02 | 1.5 | 1.6 | MemoryEngine 重新定义 |
| 03 | 1.4 | 1.5 | ADR-012 新增 |
| 04 | 1.2 | 1.3 | ContextService 补充 |
| 05 | 1.1 | 1.2 | Engine 原则新增 |
| 06 | 1.0 | 1.1 | Engine 重新定义 |
| 07 | 1.0 | 1.1 | ADR-012 新增 |
| 08 | 1.0 | 1.1 | API Entry Layer + 原则新增 |
| 09 | 1.1 | 1.2 | CR-008 新增 |
| 10_1 | — | 1.0 | 新建 |

---

## 5. 开放问题（Open Questions）

以下问题在本次变更中未做出最终决策，留待后续文档处理：

| # | 问题 | 涉及文档 | 计划处理 |
|---|------|----------|----------|
| OQ-001 | Ingestion Pipeline 的具体 Chunking 策略（按字数/按段落/按语义） | 10_2 | 待定 |
| OQ-002 | Reflection Engine 的 LLM 调用策略（单次 vs 多轮） | 10_4 | 待定 |
| OQ-003 | 向量检索的 embedding 模型选择 | 10_3 | 待定 |
| OQ-004 | MCP Server 的具体 Tool 定义 | 10_8 | 待定 |
| OQ-005 | Database migration 的具体策略（SQL vs ORM） | 10_9 | 待定 |

---

## 6. 变更总结

本次 Phase B 首次变更完成了以下核心目标：

1. **将 Phase A 架构转化为可编码的服务层设计** — 10_1 定义了五层架构、6 个 Service、11 个 Engine、Repository 层、Entry 层
2. **重新定义 MemoryEngine** — 从"全能引擎"变为"Memory Domain Orchestrator"，协调 4 个子 Engine
3. **重新定义 Engine** — 所有 Engine 明确为 Domain Capability，不是 Agent/Service/Repository
4. **确立 Repository 边界** — 仅持久化，按 Domain Aggregate 组织，引入 QueryRepository
5. **确立 API Entry Layer 术语** — 从 API Layer 改为 API Entry Layer，明确职责
6. **确立依赖规则** — 分层依赖、无层跳跃、Service DAG、Engine DAG
7. **确立 Project Memory 哲学** — 文档=长期记忆，Chat=工作记忆，代码=可执行记忆
8. **统一 01~09 的术语和边界** — 所有受影响文档已同步更新

**没有引入任何新的架构范式**。所有变更都是对 Phase A 概念的澄清和细化。

---

*本报告记录了 Phase B 首次变更的全部影响。后续 10_2~10_N 变更将参照本报告的格式。*
