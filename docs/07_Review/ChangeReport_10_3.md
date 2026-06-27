# Change Report 10_3 — Phase B QueryService Design

> **日期**: 2026-06-27
> **阶段**: Phase B — 实现设计（第三部分）
> **触发原因**: Phase B-3 开始，定义 QueryService 的工程实现设计
> **生成文档**: 10_3_Implementation_QueryService.md, 13_Architecture_Guidelines.md
> **影响文档**: 10_1, 10_2, INDEX.md, README.md

---

## 1. 概述

本次变更是 Phase B 的第三份实现设计文档，聚焦 **QueryService** 的工程实现。

核心贡献：

1. 确立了 QueryService 作为 **纯读服务**（Side-Effect Free）的定位
2. 定义了 **五大 Query Capability**（Retrieval/Search/Browse/Projection/Analytics）
3. 确立了 **Query Planning Before Execution** 原则，引入 Query Planner
4. 确立了 **Engines Produce Domain Knowledge** 原则
5. 引入 **Service Independence Principle** 和 **Shared Domain Engine Principle**
6. 确立 **Consumer-Agnostic Interface** 原则
7. 设计 **Continuation Semantics**（独立于分页机制）
8. 定义 **Stable Result Contract**（QueryResult 统一模型）
9. 确立 **Streaming 归属**（Entry Delivery Strategy，不是 Query Capability）
10. 确立 **Query Determinism Principle**
11. 建立 **13_Architecture_Guidelines**（19 条编号 Guideline）
12. 建立 **Design Checklist**（P0/P1/P2 结构 + ADR Impact Check）

---

## 2. 变更清单

### 2.1 新增文档

#### 10_3_Implementation_QueryService.md

**为什么变更**: Phase B-3 需要定义 QueryService 的工程实现，作为后续 Service 文档的参考基准。

**变更内容**:

| 章节 | 内容 |
|------|------|
| 第 2 章 | QueryService Responsibility — Side-Effect Free 原则、尊重持久化客观事实 |
| 第 3 章 | Query Capability Taxonomy — 五大能力（Retrieval/Search/Browse/Projection/Analytics）+ 边界说明 + Projection 归属 |
| 第 4 章 | Public API Design — Capability-Oriented API + One Capability One Public API Family 原则 |
| 第 5 章 | Query Pipeline — 5 步 Pipeline + Query Planner（Planning/Optimization/Routing/Strategy） |
| 第 6 章 | Engine Interaction — 可调用多个 Engine + Engines Produce Domain Knowledge + Engine DAG |
| 第 7 章 | MemoryService Interaction — Service Independence + Shared Domain Engine + Command Return Policy |
| 第 8 章 | Continuation Semantics — Consumer-Agnostic + Streaming 归属 Entry |
| 第 9 章 | Result Model — Stable Result Contract（Capability-Agnostic QueryResult） |
| 第 10 章 | Query Determinism Principle — 语义一致性 |
| 第 11 章 | Service Collaboration Matrix — Phase B 统一规范 + QueryService 矩阵 + Forbidden Dependencies |
| 第 12 章 | Design Checklist — P0/P1/P2 结构 + ADR Impact Check |
| 第 13 章 | Future Evolution — Planned vs Potential |

**影响**:
* 所有后续 Service 文档必须引用本文档的 Service Collaboration Matrix 规范
* 10_1 必须同步更新以保持一致
* 代码实现必须遵循 Side-Effect Free 原则

**跨文档一致性**: 与 10_1、10_2 的 Service Independence、Shared Domain Engine 原则完全一致。

#### 13_Architecture_Guidelines.md（V1）

**为什么变更**: 从 Phase B 讨论中沉淀出的公共工程规范需要统一记录，作为 Living Guideline。

**变更内容**:

| Guideline | 内容 | 来源 |
|-----------|------|------|
| G-001 | One Capability, One Implementation | 10_1 |
| G-002 | One Public API Family | 10_3 |
| G-003 | Consumer-Agnostic Interface | 10_3 |
| G-004 | Stable Public Interface | 10_3 |
| G-005 | Service Independence Principle | 10_3 |
| G-006 | Shared Domain Engine Principle | 10_3 |
| G-007 | Domain Service 原则 | 10_2 |
| G-008 | Command / Query Separation | 10_1 |
| G-009 | Service Collaboration Matrix | 10_1 |
| G-010 | Engine as Domain Capability | 10_1 |
| G-011 | Engine Dependency Graph | 10_1 |
| G-012 | Engines Produce Domain Knowledge | 10_3 |
| G-013 | Repository Is Persistence Only | 10_1 |
| G-014 | No Layer Skipping | 10_1 |
| G-015 | Side-Effect Free Query | 10_3 |
| G-016 | Query Determinism | 10_3 |
| G-017 | Stable Result Contract | 10_3 |
| G-018 | Architecture Review Checklist | 10_3 |
| G-019 | Planned vs Potential Evolution | 10_3 |

**影响**:
* 13 成为项目的规范中心（Normative Reference）
* 后续 10_4~10_N 每完成一个文档，同步更新 13
* Review 时可检查 Guideline Coverage

---

### 2.2 回溯修改文档

#### 10_1_Implementation_Service_Layer.md

**为什么变更**: 10_3 发现了多个 Service 层统一原则，需要在总纲文档中同步。

**变更内容**:

| 变更 | 说明 |
|------|------|
| Decision Summary 补充 23~34 | Query Service 定位、五大 Query Capability、Query Planner、Service Independence、Consumer-Agnostic、Stable Result Contract、Continuation、Streaming、Query Determinism、Architecture Guidelines |
| 回溯更新表补充 10_3 | Query Service 定位 + 五大 Query Capability + Query Planner + Service Independence + Consumer-Agnostic + Stable Result Contract |
| 版本号 1.2 | Phase B-3 修订 |

**影响**: 10_1 从"Service Layer 总纲"升级为"Phase B 全部工程原则总纲"。

**跨文档一致性**: 与 10_3 完全一致。

#### 10_2_Implementation_MemoryService.md

**为什么变更**: 与 10_3 交叉引用，确认 Service Independence 和 Shared Domain Engine 原则。

**变更内容**:

| 变更 | 说明 |
|------|------|
| 版本号 1.1 | Phase B-3 修订：新增与 10_3 的交叉引用 |

**影响**: 10_2 确认了与 10_3 的边界。

#### INDEX.md

**为什么变更**: 10_3 和 13 已生成，需要更新阅读顺序和完成状态。

**变更内容**:

| 变更 | 说明 |
|------|------|
| Phase 5 新增 10_3 | 添加 10_3_Implementation_QueryService.md 条目 |
| Phase 5 新增 13 | 添加 13_Architecture_Guidelines.md 条目 |
| Current Progress 更新 | 11/11 → 13/13 |

**影响**: 读者可通过 INDEX 了解 Phase B 已进入 QueryService 设计阶段。

#### README.md

**为什么变更**: Phase B 进度更新。

**变更内容**:

| 变更 | 说明 |
|------|------|
| Phase B 状态更新 | 10_3 和 13 标记为 ✅ 完成，后续编号顺延 |
| 文档列表新增 | Implementation QueryService + Architecture Guidelines |

**影响**: 读者可通过 README 了解项目当前进度。

---

## 3. 新增原则

本次变更确认了以下 **Phase B 工程原则**：

| # | 原则 | 说明 | 影响范围 |
|---|------|------|----------|
| 1 | **Side-Effect Free Query** | QueryService 是纯读服务，不得修改任何领域状态 | 10_3 |
| 2 | **五大 Query Capability** | Retrieval/Search/Browse/Projection/Analytics | 10_3 |
| 3 | **Projection 归属** | Projection 属于 QueryService，不属于 Engine，不属于 Presentation | 10_3 |
| 4 | **One Public API Family** | 同一 Capability 的 Public API 统一命名前缀 | 10_3 |
| 5 | **Query Planning Before Execution** | Query Planner 负责 Planning/Optimization/Routing/Strategy | 10_3 |
| 6 | **Engines Produce Domain Knowledge** | Engine 返回 Domain Result，QueryService 负责 Projection | 10_3 |
| 7 | **Service Independence** | Service 之间不互相同步调用 | 10_3 |
| 8 | **Shared Domain Engine** | Service 通过共享 Engine 协作 | 10_3 |
| 9 | **Command Return Policy** | Command 后基于当前 Domain Object 构建返回，不得再次 Query | 10_3 |
| 10 | **Consumer-Agnostic Interface** | 面向能力设计，不面向调用方设计 | 10_3 |
| 11 | **Continuation Semantics** | QueryService 定义 Continuation，Entry 决定协议 | 10_3 |
| 12 | **Streaming 归属** | Streaming 是 Entry Delivery Strategy，不是 Query Capability | 10_3 |
| 13 | **Stable Result Contract** | QueryResult 能力无关、协议无关 | 10_3 |
| 14 | **Query Determinism** | 相同条件下语义一致 | 10_3 |
| 15 | **Architecture Guidelines (13)** | 19 条编号 Guideline，Living Guideline | 13 |

---

## 4. 架构决策影响分析

### 4.1 Side-Effect Free 定位的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 10_1 | 新增 G-015 Side-Effect Free Query | 10_1 Decision Summary 补充 |
| 10_2 | Service Independence 原则 | 10_2 确认不与 10_3 互调 |
| 10_3 | 全文档基础 | 所有 API 只读 |

### 4.2 Five Query Capability 的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 10_1 | 五大 Capability 命名规范 | 10_1 Decision Summary 补充 |
| 10_3 | 完整 API 设计 | Retrieval/Search/Browse/Projection/Analytics |
| 13 | G-002 One Public API Family | 统一命名前缀 |

### 4.3 Service Independence 的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 10_1 | 新增 G-005/G-006 | 10_1 Decision Summary 补充 |
| 10_2 | 确认不与 QueryService 互调 | 10_2 交叉引用 |
| 10_3 | QueryService 矩阵明确禁止 → MemoryService | 10_3 §7 |

### 4.4 Architecture Guidelines 的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 10_1 | 引用 13 作为 Normative Reference | 10_1 Decision Summary 补充 |
| 10_2 | 引用 13 作为 Normative Reference | 10_2 交叉引用 |
| 10_3 | 引用 13 作为 Normative Reference | 10_3 §12 Design Checklist |

---

## 5. 跨文档一致性验证

### 5.1 术语一致性

| 术语 | 10_1 | 10_2 | 10_3 | 13 | 一致? |
|------|------|------|------|-----|-------|
| Side-Effect Free | ✅ | ✅ | ✅ | ✅ (G-015) | ✅ |
| Service Independence | ✅ | ✅ | ✅ | ✅ (G-005) | ✅ |
| Shared Domain Engine | ✅ | ✅ | ✅ | ✅ (G-006) | ✅ |
| Consumer-Agnostic | ✅ | — | ✅ | ✅ (G-003) | ✅ |
| Stable Result Contract | — | — | ✅ | ✅ (G-017) | ✅ |
| Query Planner | — | — | ✅ | ✅ (G-008) | ✅ |
| Projection | — | — | ✅ | ✅ (G-012) | ✅ |
| One Public API Family | ✅ | — | ✅ | ✅ (G-002) | ✅ |
| Service Collaboration Matrix | ✅ | ✅ | ✅ | ✅ (G-009) | ✅ |
| Command / Query Separation | ✅ | ✅ | ✅ | ✅ (G-008) | ✅ |

### 5.2 依赖规则一致性

| 规则 | 10_1 | 10_2 | 10_3 | 一致? |
|------|------|------|------|-------|
| Service → Engine ✅ | ✅ | ✅ | ✅ | ✅ |
| Service → Service ❌ | ✅ | ✅ | ✅ | ✅ |
| QueryService → MemoryService ❌ | — | — | ✅ | ✅ |
| MemoryService → QueryService ❌ | — | ✅ | — | ✅ |
| Engine → Engine DAG | ✅ | ✅ | ✅ | ✅ |
| No Layer Skipping | ✅ | ✅ | ✅ | ✅ |

### 5.3 版本号一致性

| 文档 | 变更前 | 变更后 | 备注 |
|------|--------|--------|------|
| 10_1 | 1.1 | 1.2 | Phase B-3 修订 |
| 10_2 | 1.0 | 1.1 | Phase B-3 交叉引用 |
| 10_3 | — | 1.0 | 新建 |
| 13 | — | 1.0 | 新建 |
| INDEX | 11/11 | 13/13 | 更新 |
| README | — | — | 更新进度 |

---

## 6. 开放问题（Open Questions）

以下问题在本次变更中未做出最终决策，留待后续文档处理：

| # | 问题 | 涉及文档 | 计划处理 |
|---|------|----------|----------|
| OQ-001 | Query Cache 策略（Redis / Memory Cache） | 10_3 | V2+ |
| OQ-002 | Query Metrics 具体指标定义 | 10_3 | V2+ |
| OQ-003 | Optimizer 独立后的接口定义 | 10_3 | V2+ |
| OQ-004 | Machine Verifiable Matrix 静态分析工具 | 13 | V3+ |
| OQ-005 | AI Planner 的具体实现方式 | 10_3 | V3+ |

---

## 7. 变更总结

本次 Phase B-3 变更完成了以下核心目标：

1. **确立了 QueryService 的 Side-Effect Free 定位** — 纯读服务，尊重持久化客观事实
2. **定义了五大 Query Capability** — Retrieval/Search/Browse/Projection/Analytics
3. **确立了 Query Planning Before Execution** — 引入 Query Planner
4. **确立了 Engines Produce Domain Knowledge** — Engine 返回 Domain Result，Projection 属于 QueryService
5. **确立了 Service Independence + Shared Domain Engine** — Service 不互调，通过 Engine 协作
6. **确立了 Consumer-Agnostic Interface** — 面向能力设计，不面向调用方
7. **设计了 Continuation Semantics** — 独立于分页机制
8. **定义了 Stable Result Contract** — QueryResult 统一模型
9. **确立了 Streaming 归属** — Entry Delivery Strategy
10. **确立了 Query Determinism Principle** — 语义一致性
11. **建立了 13_Architecture_Guidelines V1** — 19 条编号 Guideline
12. **建立了 Design Checklist** — P0/P1/P2 + ADR Impact Check
13. **更新了 10_1 总纲** — 同步所有新发现的 Phase B 工程原则

**没有引入任何新的架构范式**。所有变更都是对 10_1 的分化和细化，与 10_2 保持一致。

---

*本报告记录了 Phase B-3 变更的全部影响。后续 10_4~10_N 变更将参照本报告的格式。*
