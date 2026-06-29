# Personal AI Memory Hub — 10_3 Implementation QueryService

> **版本**: 1.0
> **日期**: 2026-06-27
> **阶段**: Phase B — 实现设计（第三部分）
> **状态**: 已确认
> **作者**: 系统架构组

---

## 1. Purpose

本文档定义 **QueryService** 的工程实现设计。

QueryService 负责所有读操作编排，包括：

* 检索（Retrieval）
* 搜索（Search）
* 浏览（Browse）
* 投影（Projection）
* 分析（Analytics）

本文档是 Phase B 所有后续 Service 设计文档的参考基准。

---

## 2. QueryService Responsibility

### 2.1 核心定位

> **QueryService is the application-level read orchestration service.**
> **It orchestrates read capabilities across all domain engines.**

QueryService 表示 **Query Domain**，负责所有读能力的编排。

### 2.2 Side-Effect Free 原则

> **QueryService Shall Be Side-Effect Free**

QueryService 是纯读服务。

它不得修改任何领域状态或持久化数据。

QueryService 始终尊重当前持久化状态作为单一事实来源。

**职责**：

| 允许 | 说明 |
|------|------|
| Read | 读取持久化数据 |
| Search | 全文搜索 |
| Filter | 过滤 |
| Rank | 排序 |
| Aggregate | 聚合 |
| Project | 投影（构建不同 Query View） |
| Paginate | 分页管理 |
| Compose | 组合查询结果 |
| Return Query Result | 返回统一 Query Result Model |

**禁止行为**：

| 禁止 | 原因 |
|------|------|
| Create Memory | Command 职责，属于 MemoryService |
| Update Memory | Memory 不可变 |
| Delete Memory | 只有 Archive |
| Update Entity | 属于 EntityService |
| Trigger Reflection | 属于 ReflectionService |
| Trigger Archive | 属于 MemoryService |
| Publish Domain Events | 只有 Command Service 发布 |
| Persist any business data | 违反 Side-Effect Free |
| Execute Repository write operations | Repository 仅 Persistence |

**允许的 Infrastructure 行为**（不违反 Side-Effect Free）：

| 允许 | 说明 |
|------|------|
| Cache Read | 缓存读取（不改变业务数据） |
| Cache Hit Statistics | 缓存命中统计 |
| Query Metrics | 查询指标（Diagnostics） |
| Performance Tracing | 性能追踪 |
| Access Logging | 访问日志 |

### 2.3 尊重持久化客观事实

> **Query results reflect the persisted business state at query time. QueryService must not alter the observed business state during query execution.**

QueryService 必须尊重数据库已经存储的客观事实，职责是观察（Observe）和组织（Orchestrate），而不是影响（Influence）业务状态。

---

## 3. Query Capability Taxonomy

### 3.1 五大能力分类

QueryService 向上暴露五种独立但互补的读能力：

| Capability | 职责 | 返回类型 | 典型场景 |
|------------|------|----------|----------|
| **Retrieval** | 基于 Entity/Relationship 的精确查找 | MemoryView / EntityView | "获取实体 X 的所有记忆" |
| **Search** | 全文搜索 / 向量相似度搜索 | Ranked Memory List | "搜索关于 Hermes 的记忆" |
| **Browse** | 按时间线/类别/标签浏览 | Paginated Memory List | "浏览过去一周的记忆" |
| **Projection** | 基于 Domain Result 构建不同 Query View | Summary / Detail / Graph / Timeline | "以摘要形式展示搜索结果" |
| **Analytics** | 统计分析与洞察 | Statistics / Insights | "统计过去一个月新增记忆数" |

### 3.2 能力边界说明

| 能力 | 与其他能力的区别 |
|------|------------------|
| Retrieval vs Search | Retrieval 是精确查找（基于已知 Entity/ID），Search 是模糊匹配（关键词/向量） |
| Search vs Browse | Search 是关键词驱动的，Browse 是范围驱动的（时间/类别/标签） |
| Projection vs Presentation | **Projection 属于 Query Capability，不是 Presentation**。Projection 是 QueryService 内根据 Domain Result 构建不同 Query View。Presentation 属于 Entry 层（DTO 转换、协议适配） |
| Analytics vs Retrieval | Analytics 返回统计值，不返回具体 Memory 列表 |

### 3.3 Projection 归属原则

> **Projection 属于 QueryService，不属于 Engine，不属于 Presentation。**

```
Engine → 返回最完整、最准确的 Domain Result
    ↓
QueryService.Projection → 根据需求构建不同 View
    ├→ Summary View
    ├→ Detail View
    ├→ Graph View
    └→ Timeline View
    ↓
Entry → DTO 转换、协议适配
```

**理由**：

* 同一个 Memory，不同 View 只是呈现方式不同
* 如果放 Engine，以后会出现 SummaryEngine / DetailEngine / GraphEngine，职责膨胀
* Projection 是 QueryService 的 Result Processing 环节

---

## 4. Public API Design

### 4.1 Capability-Oriented API

QueryService 的公开接口按 Capability 分组，而非按持久化操作分组。

### 4.2 公共原则：One Capability, One Public API Family

> **Public API Family 应统一命名。**

| Capability | API 前缀 | 示例 |
|------------|----------|------|
| Retrieval | `retrieve...` | `retrieveByEntity()`, `retrieveById()` |
| Search | `search...` | `searchByKeyword()`, `searchBySimilarity()` |
| Browse | `browse...` | `browseByTimeRange()`, `browseByCategory()` |
| Projection | `project...` | `projectToSummary()`, `projectToGraph()` |
| Analytics | `analyze...` | `analyzeStatistics()`, `analyzeInsights()` |

**说明**：此原则应作为整个 Service Layer 公共规范，不是 QueryService 独有。

### 4.3 QueryService Public API

#### 4.3.1 Retrieval Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `retrieveById(QueryCommand)` | QueryCommand | `QueryResult<MemoryView>` | 通过 ID 检索 |
| `retrieveByEntity(QueryCommand)` | QueryCommand | `QueryResult<EntityView>` | 通过实体检索 |
| `retrieveByRelationship(QueryCommand)` | QueryCommand | `QueryResult<RelationshipView>` | 通过关系检索 |

#### 4.3.2 Search Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `searchByKeyword(QueryCommand)` | QueryCommand | `QueryResult<RankedMemoryView>` | 全文搜索 |
| `searchBySimilarity(QueryCommand)` | QueryCommand | `QueryResult<RankedMemoryView>` | 向量相似度搜索 |
| `searchCombined(QueryCommand)` | QueryCommand | `QueryResult<RankedMemoryView>` | 混合搜索（关键词+向量） |

#### 4.3.3 Browse Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `browseByTimeRange(QueryCommand)` | QueryCommand | `QueryResult<PaginatedMemoryView>` | 按时间范围浏览 |
| `browseByCategory(QueryCommand)` | QueryCommand | `QueryResult<PaginatedMemoryView>` | 按类别浏览 |
| `browseByTag(QueryCommand)` | QueryCommand | `QueryResult<PaginatedMemoryView>` | 按标签浏览 |

#### 4.3.4 Projection Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `projectToSummary(QueryResult)` | QueryResult | `QueryResult<SummaryView>` | 摘要投影 |
| `projectToDetail(QueryResult)` | QueryResult | `QueryResult<DetailView>` | 详情投影 |
| `projectToGraph(QueryResult)` | QueryResult | `QueryResult<GraphView>` | 图结构投影 |
| `projectToTimeline(QueryResult)` | QueryResult | `QueryResult<TimelineView>` | 时间线投影 |

#### 4.3.5 Analytics Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `analyzeStatistics(QueryCommand)` | QueryCommand | `QueryResult<StatisticsView>` | 统计分析 |
| `analyzeInsights(QueryCommand)` | QueryCommand | `QueryResult<InsightsView>` | 洞察分析 |

---

## 5. Query Pipeline

### 5.1 Pipeline 步骤

```
┌─────────────────────────────────────────────────────────┐
│                   Query Pipeline                        │
├─────────────────────────────────────────────────────────┤
│  1. Validation                                          │
│     └─ 校验查询参数合法性、权限（由 Entry 前置）          │
├─────────────────────────────────────────────────────────┤
│  2. Planning                                            │
│     └─ Query Planner 决定执行策略                        │
├─────────────────────────────────────────────────────────┤
│  3. Execution                                           │
│     └─ 调用相应 Engine 获取 Domain Result               │
├─────────────────────────────────────────────────────────┤
│  4. Result Processing                                   │
│     └─ 排序、过滤、Projection、Continuation 管理         │
├─────────────────────────────────────────────────────────┤
│  5. Response                                            │
│     └─ 构建统一 Query Result Model                      │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Query Planner

> **Query Planning Before Execution.**

Query Planner 是 Query Pipeline 的关键组件。

**职责**：

| 职责 | 说明 |
|------|------|
| **Planning** | 根据查询意图制定执行计划 |
| **Optimization** | 内部优化能力（不是独立 Service） |
| **Routing** | 决定调用哪个 Engine |
| **Execution Strategy Selection** | 选择最优执行策略 |

**Optimization 定位**：

* Optimization 是 Planner 的内部能力
* 不是独立 Service
* 不是独立 Capability
* Future Evolution 可演进为 Optimizer
* 当前保持 Query Planner 单组件

### 5.3 Pipeline 状态机

```
IDLE
  ↓ executeQuery()
VALIDATING
  ↓ validate()
PLANNING
  ├→ Planner.plan()
  ├→ Routing decision
  └→ Strategy selection
EXECUTING
  ├→ Engine 调用
  └→ Domain Result 收集
PROCESSING
  ├→ Sort / Filter / Aggregate
  ├→ Projection
  └→ Continuation 管理
RESPONDING
  └→ 构建 Query Result Model
```

---

## 6. Engine Interaction

### 6.1 可调用 Engine

QueryService 可调用多个 Engine 完成查询：

| Engine | 职责 |
|--------|------|
| **MemoryEngine** | 记忆检索、上下文构建 |
| **EntityEngine** | 实体信息获取 |
| **SearchEngine** | 全文搜索 |
| **TimelineEngine** | 时间线查询 |
| **RankingEngine** | 排序优化 |

### 6.2 引擎交互原则

> **Engines produce domain knowledge. QueryService shapes query results.**

| 原则 | 说明 |
|------|------|
| Engine 返回 Domain Result | 不返回 DTO、不返回 Transport Model |
| QueryService 负责 Projection | 不同 View（Summary/Detail/Graph）由 QueryService 构建 |
| Engine 不知道 QueryService | 单向依赖：QueryService → Engine |
| Engine 不知道 Entry | Engine 不涉及 REST/MCP/CLI/SDK |

### 6.3 Engine 组合规则

| 规则 | 说明 |
|------|------|
| 允许 Engine → Engine | 保持 DAG，如 MemoryEngine → EntityEngine → RankingEngine |
| 禁止循环 | MemoryEngine → EntityEngine → MemoryEngine 不允许 |
| Engine 不访问 Repository | 通过 Repository 的抽象层访问 |

---

## 7. MemoryService Interaction

### 7.1 Service Independence Principle

> **Application Services shall not invoke other Application Services synchronously.**

| 调用 | 允许 | 原因 |
|------|------|------|
| QueryService → MemoryService | ❌ | 违反 Service Independence |
| MemoryService → QueryService | ❌ | 违反 Service Independence |
| QueryService → MemoryEngine | ✅ | Shared Domain Engine |
| MemoryService → MemoryEngine | ✅ | Shared Domain Engine |

### 7.2 Shared Domain Engine Principle

> **Application Services collaborate through shared domain engines rather than direct service invocations whenever feasible.**

| 原则 | 说明 |
|------|------|
| 共享 Engine | Service 应共享 Engine（如 MemoryEngine） |
| 不共享 Service | Service 之间不互相调用 |
| 通过 Engine 协作 | 需要领域能力时调用 Engine，不调用另一个 Service |

### 7.3 Command Return Policy

> **Command Returns Identity. 当 Command 成功后需要返回更多信息时，基于当前 Domain Object 构建返回，不得再次 Query。**

| 方案 | 说明 |
|------|------|
| **方案 A（推荐）** | 基于当前 Domain Object 构建返回 |
| **禁止** | Command 后调用 QueryService 重新读取 |

**示例**：

```
createMemory()
    ↓
Memory Aggregate
    ↓
Persist
    ↓
返回：MemoryId + 必要的返回字段（来自当前 Domain Object）
```

而不是：

```
Persist
    ↓
QueryService.retrieveById(...)  ← 禁止
    ↓
返回 Memory
```

### 7.4 Service Interaction Rule

Review 检查项：

* 是否存在 Service → Service 同步调用？
* 是否可以改为 Shared Engine？
* 是否新增了 Service DAG 边？
* 是否违反 CQRS？

如果答案是"为了获取数据所以调用另一个 Service"，Review 应首先考虑：能否改为共享 Engine？

---

## 8. Continuation Semantics

### 8.1 核心原则

> **Consumer-Agnostic Interface. Design for Capabilities, Not Consumers.**
> **Pagination 为应用层能力。Persistence 不暴露分页机制。**

| 层面 | 职责 |
|------|------|
| **QueryService** | 定义 Continuation Semantics（还有下一批） |
| **Entry Adapter** | 决定 Cursor / Page / Offset / Iterator / Streaming |

### 8.2 Continuation 设计

QueryService 不暴露具体的分页机制：

* 不固定 Cursor
* 不固定 Offset
* 不固定 Page

QueryService 定义 **Continuation Semantics**：

```
Continuation
├── hasMore: Boolean
└── continuationToken: String (opaque)
```

Entry Adapter 负责将 Continuation 映射为协议特定的形式：

| Entry | 映射方式 |
|-------|----------|
| REST | `?cursor=<token>` 或 `?page=2` |
| MCP | `{ "continuation": "<token>" }` |
| SDK | `iterator.next()` |
| CLI | `--page 2` |
| Agent | Stream continuation |

### 8.3 Streaming

> **Streaming 不是 Query Capability。Streaming 属于 Entry Delivery Strategy。**

```
Query 执行一次
    ↓
Result Ready
    ↓
Entry Delivery Strategy
    ├→ REST Response
    ├→ MCP Stream
    ├→ CLI Console
    ├→ SDK Iterator
    └→ Agent Stream
```

Query 只执行一次，Delivery 可以有多种形式。

---

## 9. Result Model

### 9.1 统一 Query Result Contract

> **Stable Result Contract.**

QueryResult 是能力无关的（Capability-Agnostic）统一模型：

```
QueryResult
├── result: DomainResult[]      ← 领域结果
├── metadata: QueryMetadata     ← 查询元数据
├── continuation: Continuation  ← 续传信息
└── diagnostics: Diagnostics (optional)  ← 诊断信息
```

### 9.2 各字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `result` | DomainResult[] | 领域结果（非 DTO、非 JSON 设计） |
| `metadata` | QueryMetadata | 查询时间、Engine 耗时、搜索策略等 |
| `continuation` | Continuation | 是否有下一批（hasMore + continuationToken） |
| `diagnostics` | Diagnostics (optional) | 执行时间、Planner 决策等（调试用） |

### 9.3 设计约束

| 约束 | 说明 |
|------|------|
| 不要协议绑定 | 不绑定 REST / JSON / GraphQL |
| 不要 DTO 设计 | 不是特定协议的 Data Transfer Object |
| Stable | 接口长期稳定，内部可演进 |

---

## 10. Query Determinism Principle

> **Given the same query conditions and unchanged underlying data, QueryService should produce semantically consistent results.**

QueryService 应保证语义一致性。

* 不是要求排序百分之百一致
* 而是：给定相同查询条件且底层数据未变化，应返回语义一致的结果
* 例如：今天查询 "Hermes" 返回 5 条，明天不应返回 3 条（除非数据变了）
* 如果排序策略允许，顺序可以不同，但结果集合应一致

**Query Consistency（推荐补充）**：

> A query shall observe a consistent view of data within a single execution whenever practical.

一次 Query 的执行过程中，应尽可能基于同一个一致性视图。

---

## 11. Service Collaboration Matrix

### 11.1 QueryService 协作矩阵

> **Phase B 规范**：每个 Service 文档必须包含此矩阵。所有矩阵合并形成完整的 Service Dependency Graph。

| Caller | Callee | Allowed | Interaction Pattern | Reason | Architecture Rule |
|--------|--------|---------|---------------------|--------|-------------------|
| QueryService | MemoryEngine | ✅ | Sync | Shared Domain Engine | Service Independence |
| QueryService | EntityEngine | ✅ | Sync | Shared Domain Engine | Service Independence |
| QueryService | SearchEngine | ✅ | Sync | Shared Domain Engine | Service Independence |
| QueryService | TimelineEngine | ✅ | Sync | Shared Domain Engine | Service Independence |
| QueryService | RankingEngine | ✅ | Sync | Shared Domain Engine | Service Independence |
| QueryService | MemoryService | ❌ | N/A | Prevent Service→Service coupling | Service Independence |
| QueryService | ReflectionService | ❌ | N/A | Prevent Service→Service coupling | Service Independence |
| QueryService | ContextService | ⚠️ | Event Only | Context 构建可能触发，但不直接调用 | Service Independence |
| QueryService | TaskRuntime | ⚠️ | Job Dispatch | 异步查询任务 | Service Independence |
| QueryService | Repository | ❌ | N/A | No Layer Skipping | No Layer Skipping |

### 11.2 矩阵解读

| 符号 | 含义 |
|------|------|
| ✅ | 允许同步调用 |
| ⚠️ | 允许但有限制（需通过抽象/事件/Job） |
| ❌ | 禁止 |

### 11.3 Forbidden Dependencies

| 禁止 | 原因 |
|------|------|
| QueryService → MemoryService | 违反 Service Independence |
| MemoryService → QueryService | 违反 Service Independence |
| QueryService → Repository | 违反 No Layer Skipping |
| Service → Service 同步调用 | 违反 Service Independence |

---

## 12. Design Checklist

### 12.1 P0 — 必须满足

| # | 检查项 | 状态 |
|---|--------|------|
| P0-01 | Side-Effect Free Query | ✅ |
| P0-02 | Command / Query Separation | ✅ |
| P0-03 | Service → Service 检查（禁止互调） | ✅ |
| P0-04 | Layer Skipping 检查（不直接访问 Repository） | ✅ |
| P0-05 | Engine DAG 有效 | ✅ |
| P0-06 | Service DAG 有效 | ✅ |

### 12.2 P1 — 强烈建议

| # | 检查项 | 状态 |
|---|--------|------|
| P1-01 | Consumer-Agnostic Interface | ✅ |
| P1-02 | Stable Result Contract | ✅ |
| P1-03 | Public API Family 统一命名 | ✅ |
| P1-04 | Query Planner 存在 | ✅ |
| P1-05 | Shared Domain Engine 原则 | ✅ |
| P1-06 | Continuation Semantics 独立于分页机制 | ✅ |
| P1-07 | Projection 属于 QueryService 而非 Engine | ✅ |

### 12.3 P2 — 可选增强

| # | 检查项 | 状态 |
|---|--------|------|
| P2-01 | Query Determinism Principle | ✅ |
| P2-02 | Query Consistency（单次执行内一致性） | ✅ |
| P2-03 | Diagnostics 信息可选 | ✅ |

### 12.4 ADR Impact Check

| ADR | 影响 | 说明 |
|-----|------|------|
| CQRS | QueryService 是 Query 端 | 与 MemoryService（Command）严格分离 |
| Service Independence | QueryService 不调用其他 Service | 通过 Shared Domain Engine 协作 |
| Consumer-Agnostic Interface | Continuation 独立于协议 | REST/MCP/CLI/SDK 各自适配 |
| One Capability, One Implementation | 每种 Capability 一个实现 | Retrieval/Search/Browse/Projection/Analytics |

---

## 13. Future Evolution

### 13.1 Planned Evolution

| 演进 | 说明 | 阶段 |
|------|------|------|
| Optimizer 独立 | Query Planner 内部 Optimization 演进为独立 Optimizer | V2+ |
| Query Cache | Redis / Memory Cache 集成，Planner 路由 | V2+ |
| Query Metrics | 执行时间、Engine 耗时、Hit Rate 监控 | V2+ |
| Machine Verifiable Matrix | Service Collaboration Matrix 静态分析 | V3+ |

### 13.2 Potential Evolution

| 演进 | 说明 |
|------|------|
| AI Planner | 基于 LLM 的智能查询规划 |
| Cost Estimator | 查询成本预估 |
| Query Federation | 跨源查询（本地 + 外部） |

---

## 14. 与 Phase A 文档的关系

| 文档 | 引用关系 |
|------|----------|
| 01 | 记忆类型体系（QueryService 的 Projection 基于此） |
| 02 | MemoryEngine / ContextBuilder（QueryService 调用 MemoryEngine） |
| 03 | Entity / MemoryNode 模型（QueryService 的检索对象） |
| 04 | Schema / Reflect（QueryService 可查询 Archive 状态） |
| 05 | Lifecycle（QueryService 可查询记忆生命周期状态） |
| 06 | Runtime Architecture（QueryService 是 Runtime 的一部分） |
| 07 | Boundary Review（QueryService 遵守 P1-P9 边界约束） |
| 08 | Implementation Architecture（QueryService 是 08 定义的 Service 之一） |
| 09 | Database Physical Design（QueryService 通过 Repository 间接操作 09 的表结构） |
| 10_1 | Implementation Service Layer（本文档引用 10_1 的分层架构、Service 分类、依赖规则） |
| 10_2 | Implementation MemoryService（Service Independence、Shared Domain Engine 原则） |

---

## 附录 A：术语对照

| 术语 | 说明 | 出处 |
|------|------|------|
| QueryService | Query Domain Service，编排查询领域能力 | 本文档 |
| Query Planner | 查询执行计划的制定者 | 本文档 |
| Continuation | 续传语义，独立于分页机制 | 本文档 |
| Projection | QueryService 内构建不同 Query View | 本文档 |
| Service Independence | Service 之间不互相同步调用 | 本文档 |
| Shared Domain Engine | Service 通过共享 Engine 协作 | 本文档 |
| Consumer-Agnostic Interface | 公共接口不依赖特定调用方 | 本文档 |
| Stable Result Contract | 统一的 Query Result 模型 | 本文档 |
| Query Determinism | 相同条件下语义一致 | 本文档 |

---

## 附录 B：文档变更记录

| 版本 | 日期 | 变更说明 | 状态 |
| 1.1 | 2026-06-27 | Phase B-3 修订：(1) 新增 QueryService 定位原则 (2) Decision Summary 补充 23~34 (3) 回溯更新表补充 10_3 (4) 新增 13 Architecture Guidelines 引用 | ✅ 已确认 |
| 1.2 | 2026-06-28 | Phase B-5 修订：(1) 补充 QueryService 消费 Entity 信息但不拥有 Entity 状态的角色（与 10_5 对齐）(2) Decision Summary 补充 38 | ✅ 已确认 |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

*本文档是 Phase B 的 QueryService 设计文档，后续 10_4~10_N 文档均引用本文档的 Service Collaboration Matrix 规范。*
