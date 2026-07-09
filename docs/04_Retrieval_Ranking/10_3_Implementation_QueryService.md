# Personal AI Memory Hub — 10_3 Implementation QueryService

> **版本**: 2.0
> **日期**: 2026-07-09
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

QueryService 是唯一业务读入口。

所有读能力（Read Capability）必须经过 QueryService 编排。

Entry Layer、Repository Layer、Engine Layer 不编排业务能力。

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

### 2.3 Query Purity Principle

> **Query Purity: 除基础设施侧效果外，QueryService 不得产生任何业务侧效果。**

**禁止的隐藏命令**：

| 禁止 | 原因 |
|------|------|
| Automatic Reflection | 属于 ReflectionService 职责 |
| Automatic Embedding Generation | 属于 Engine/Task Runtime 职责 |
| Automatic Index Rebuilding | 属于 Task Runtime 职责 |
| Automatic Repairs | 属于 EntityService/Task Runtime 职责 |

所有上述操作必须通过显式 Command 或 Task 执行，而非 Query 的隐式副作用。

### 2.4 Observational Consistency

> **Query results reflect the persisted business state at query time. QueryService must not alter the observed business state during query execution.**

QueryService 必须尊重数据库已经存储的客观事实，职责是观察（Observe）和组织（Orchestrate），而不是影响（Influence）业务状态。

---

## 3. Capability Composition Principle

> **Public Query capabilities may internally compose other Query capabilities.**
> **Composition remains inside QueryService.**
> **Entry Layer, Repository Layer and Engine Layer do not orchestrate business capability composition.**

### 3.1 能力组合规则

| 规则 | 说明 |
|------|------|
| QueryService 内部组合 | Retrieval 可组合 Search + Projection |
| 禁止跨层编排 | Entry 不编排能力，Repository 不编排能力，Engine 不编排能力 |
| 组合结果仍为 Query | 组合后的结果仍然是只读的，不引入写操作 |

### 3.2 示例

```
Search Capability
  ├── retrieveById()        (内部组合 Retrieval)
  ├── searchByKeyword()     (内部组合 Search + Projection)
  └── searchCombined()      (内部组合 Search + Ranking + Projection)
```

---

## 4. Query Capability Taxonomy

### 4.1 五大能力分类

QueryService 向上暴露五种独立但互补的读能力：

| Capability | 职责 | 返回类型 | 典型场景 |
|------------|------|----------|----------|
| **Retrieval** | 基于 Entity/Relationship 的精确查找 | MemoryView / EntityView | "获取实体 X 的所有记忆" |
| **Search** | 全文搜索 / 向量相似度搜索 | Ranked Memory List | "搜索关于 Hermes 的记忆" |
| **Browse** | 按时间线/类别/标签浏览 | Paginated Memory List | "浏览过去一周的记忆" |
| **Projection** | 基于 Domain Result 构建不同 Query View | Summary / Detail / Graph / Timeline | "以摘要形式展示搜索结果" |
| **Analytics** | 统计分析与洞察 | Statistics / Insights | "统计过去一个月新增记忆数" |

### 4.2 能力边界说明

| 能力 | 与其他能力的区别 |
|------|------------------|
| Retrieval vs Search | Retrieval 是精确查找（基于已知 Entity/ID），Search 是模糊匹配（关键词/向量） |
| Search vs Browse | Search 是关键词驱动的，Browse 是范围驱动的（时间/类别/标签） |
| Projection vs Presentation | **Projection 属于 Query Capability，不是 Presentation**。Projection 是 QueryService 内根据 Domain Result 构建不同 Query View。Presentation 属于 Entry 层（DTO 转换、协议适配） |
| Analytics vs Retrieval | Analytics 返回统计值，不返回具体 Memory 列表 |

### 4.3 Projection 归属原则

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

### 4.4 Projection 三层边界

> **Domain Model → Domain View → Entry DTO**

| 层级 | 职责 | 示例 |
|------|------|------|
| **Domain Model** | Engine 返回的最完整领域对象 | MemoryNode, Entity |
| **Domain View** | QueryService 投影后的语义变换结果 | SummaryView, DetailView, GraphView |
| **Entry DTO** | Entry 层协议适配后的传输对象 | REST JSON, MCP Payload, CLI Output |

**投影约束**：

| 约束 | 说明 |
|------|------|
| 仅变换表示 | Projection 只改变数据的表示形式 |
| 不改变语义 | 投影后结果的语义与 Domain Model 一致 |
| 确定性 | 相同的 Domain Result 经过相同的 Projection 产生相同的 Domain View |
| 无状态 | Projection 不修改任何状态 |
| 无副作用 | Projection 不产生任何业务侧效果 |

---

## 5. Public API Design

### 5.1 Capability-Oriented API

QueryService 的公开接口按 Capability 分组，而非按持久化操作分组。

### 5.2 公共原则：One Capability, One Public API Family

> **Public API Family 应统一命名。**

| Capability | API 前缀 | 示例 |
|------------|----------|------|
| Retrieval | `retrieve...` | `retrieveByEntity()`, `retrieveById()` |
| Search | `search...` | `searchByKeyword()`, `searchBySimilarity()` |
| Browse | `browse...` | `browseByTimeRange()`, `browseByCategory()` |
| Projection | `project...` | `projectToSummary()`, `projectToGraph()` |
| Analytics | `analyze...` | `analyzeStatistics()`, `analyzeInsights()` |

**说明**：此原则应作为整个 Service Layer 公共规范，不是 QueryService 独有。

### 5.3 Consumer-Agnostic Interface

> **Consumer-Agnostic Interface. Design for Capabilities, Not Consumers.**

公共接口不假设特定客户端、框架、协议或 Agent 的实现约定。

### 5.4 QueryService Public API

#### 5.4.1 Retrieval Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `retrieveById(QueryCommand)` | QueryCommand | `QueryResult<MemoryView>` | 通过 ID 检索 |
| `retrieveByEntity(QueryCommand)` | QueryCommand | `QueryResult<EntityView>` | 通过实体检索 |
| `retrieveByRelationship(QueryCommand)` | QueryCommand | `QueryResult<RelationshipView>` | 通过关系检索 |

#### 5.4.2 Search Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `searchByKeyword(QueryCommand)` | QueryCommand | `QueryResult<RankedMemoryView>` | 全文搜索 |
| `searchBySimilarity(QueryCommand)` | QueryCommand | `QueryResult<RankedMemoryView>` | 向量相似度搜索 |
| `searchCombined(QueryCommand)` | QueryCommand | `QueryResult<RankedMemoryView>` | 混合搜索（关键词+向量） |

#### 5.4.3 Browse Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `browseByTimeRange(QueryCommand)` | QueryCommand | `QueryResult<PaginatedMemoryView>` | 按时间范围浏览 |
| `browseByCategory(QueryCommand)` | QueryCommand | `QueryResult<PaginatedMemoryView>` | 按类别浏览 |
| `browseByTag(QueryCommand)` | QueryCommand | `QueryResult<PaginatedMemoryView>` | 按标签浏览 |

#### 5.4.4 Projection Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `projectToSummary(QueryResult)` | QueryResult | `QueryResult<SummaryView>` | 摘要投影 |
| `projectToDetail(QueryResult)` | QueryResult | `QueryResult<DetailView>` | 详情投影 |
| `projectToGraph(QueryResult)` | QueryResult | `QueryResult<GraphView>` | 图结构投影 |
| `projectToTimeline(QueryResult)` | QueryResult | `QueryResult<TimelineView>` | 时间线投影 |

#### 5.4.5 Analytics Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `analyzeStatistics(QueryCommand)` | QueryCommand | `QueryResult<StatisticsView>` | 统计分析 |
| `analyzeInsights(QueryCommand)` | QueryCommand | `QueryResult<InsightsView>` | 洞察分析 |

---

## 6. Unified Read Workflow

### 6.1 冻结的统一读工作流

> **以下六步工作流为冻结规范，后续所有读操作必须遵循此顺序。**

```
Validation
    ↓
Planning
    ↓
Repository Coordination
    ↓
Domain Processing
    ↓
Projection
    ↓
Result Assembly
```

### 6.2 各步骤职责

| 步骤 | 职责 | 所属层 |
|------|------|--------|
| **Validation** | 校验查询参数合法性、权限（由 Entry 前置） | Entry / QueryService |
| **Planning** | Query Planner 决定执行策略、路由、能力选择 | QueryService |
| **Repository Coordination** | 根据 Plan 协调一个或多个 Repository 获取数据 | QueryService → Repository |
| **Domain Processing** | 对 Repository 返回的领域数据进行领域级处理（排序、过滤、聚合、分析等） | QueryService → Engine |
| **Projection** | 将 Domain Result 投影为不同 View | QueryService |
| **Result Assembly** | 构建统一 QueryResult 合同 | QueryService |

### 6.3 Domain Processing 定位

> **Domain Processing 是稳定的扩展点。**

* 详细的领域处理逻辑属于 D4 QueryEngine
* QueryService 协调 Engine 完成 Domain Processing
* Domain Processing 不引入临时性的 "Simple Merge" 表述
* Domain Processing 是 QueryService 与 D4 Engine 之间的明确职责边界

### 6.4 移除 "Simple Merge" 表述

> 本文档及后续所有 QueryService 相关文档中，不再使用 "Simple Merge" 作为稳定术语。
> 统一使用 "Domain Processing" 作为 Repository 结果到 Projection 之间的处理阶段。

---

## 7. Read Pipeline Principles

### 7.1 Pipeline 核心原则

| 原则 | 说明 |
|------|------|
| **Single Read Flow** | 所有读操作走同一条 Pipeline，不针对特定查询类型创建独立流程 |
| **Forward-Only** | Pipeline 单向执行，不回退、不循环 |
| **Immutable Intermediate Results** | 每个 Pipeline 阶段的输出是不可变的，下一阶段基于上一阶段的不可变副本 |
| **Stable QueryResult Contract** | Pipeline 终点是统一的 QueryResult 模型 |
| **Stateless Execution** | Pipeline 执行不保留任何跨请求状态 |

### 7.2 Pipeline 差异点

> **Pipeline 的唯一差异存在于以下三个位置：**

| 差异点 | 说明 |
|--------|------|
| Planning | 不同的查询类型有不同的执行计划 |
| Repository Coordination | 不同的计划协调不同的 Repository 组合 |
| Domain Processing | 不同的计划触发不同的领域处理逻辑 |

Pipeline 的其他步骤（Validation、Projection、Result Assembly）对所有查询类型保持一致。

### 7.3 Pipeline 步骤详述

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
│  3. Repository Coordination                             │
│     └─ 根据 Plan 协调一个或多个 Repository               │
├─────────────────────────────────────────────────────────┤
│  4. Domain Processing                                   │
│     └─ 领域级处理（排序、过滤、聚合、分析）              │
├─────────────────────────────────────────────────────────┤
│  5. Projection                                          │
│     └─ 构建不同 Query View（Summary/Detail/Graph/Timeline）│
├─────────────────────────────────────────────────────────┤
│  6. Result Assembly                                     │
│     └─ 构建统一 Query Result Model                      │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Repository Coordination

### 8.1 唯一协调者原则

> **QueryService is the only repository coordinator.**

| 规则 | 说明 |
|------|------|
| QueryService 协调 Repository | 所有 Repository 访问通过 QueryService 发起 |
| Repository 不互调 | Repositories never coordinate each other |
| Repository 不知道彼此 | Repositories never know each other |
| Repository 不组装跨聚合结果 | Repositories never assemble cross-aggregate results |
| Repository 组合由 Planning 决定 | Repository combinations are determined by Query Planning |
| Repository 仅返回领域数据 | Repositories return domain data only |

### 8.2 跨仓库协调示例

```
QueryService.searchCombined()
    ↓
Planning → 决定需要 MemoryQueryRepository + VectorQueryRepository
    ↓
Repository Coordination
    ├── MemoryQueryRepository → 返回 Memory Domain Objects
    └── VectorQueryRepository → 返回 Vector Match Results
    ↓
Domain Processing → QueryService 合并并排序结果
    ↓
Projection → 构建 RankedMemoryView
```

---

## 9. Query Idempotence Principle

> **The same query executed against the same persisted state shall always produce the same business result.**

### 9.1 幂等性约束

| 约束 | 说明 |
|------|------|
| 相同查询 + 相同状态 = 相同结果 | 这是 QueryService 的基本保证 |
| 不要求逐字节一致 | 允许非确定性基础设施行为（如缓存命中率的统计差异） |
| 要求业务语义一致 | 返回的核心业务结果必须一致 |
| 不修改持久化状态 | 幂等的前提是查询不改变任何状态 |

---

## 10. Transaction Strategy

### 10.1 只读事务

> **Read-Only Transaction. Transaction owned by QueryService.**

| 规则 | 说明 |
|------|------|
| 事务由 QueryService 拥有 | QueryService 负责开启、提交、回滚事务 |
| Repository 不拥有事务 | Repositories 是事务中性的，不 begin/commit/rollback |
| 一致的单一业务快照 | 事务确保整个查询看到一致的数据快照 |
| 无长运行读事务 | Read transaction 必须在单次查询执行期间完成 |
| Streaming 是交付策略 | 不是事务策略。Streaming 属于 Entry Delivery |

### 10.2 事务边界

| 原则 | 说明 |
|------|------|
| 一次查询一个事务 | 每个公共查询方法定义一个事务边界 |
| 事务范围覆盖整个 Pipeline | 从 Repository Coordination 到 Result Assembly |
| 事务内一致性 | 同一事务内的所有 Repository 调用看到相同的数据快照 |

---

## 11. Error Mapping

### 11.1 Repository → Service 错误映射

> **Repository errors are translated into Service errors.**

| 层级 | 错误类型 | 说明 |
|------|----------|------|
| Repository | `RepositoryError` | 持久化层异常（连接失败、约束冲突等） |
| QueryService | `ServiceError` → 子类型 | 业务导向异常模型 |
| Entry | `EntrySafeError` | 对外暴露的安全错误码 |

### 11.2 错误映射原则

| 原则 | 说明 |
|------|------|
| 业务导向异常模型 | QueryService 使用面向业务的异常分类 |
| 投影失败属于 QueryService | Projection 失败是 QueryService 的责任，不是 Engine 的 |
| 空搜索结果不是错误 | Empty search results are not errors — 返回空 QueryResult |
| 确定性错误映射 | 相同的 Repository 错误总是映射到相同的 Service 错误 |
| 部分故障恢复属于 D4 | Partial failure recovery belongs to D4 QueryEngine rather than D3 Service |

### 11.3 异常翻译责任

| 层级 | 翻译责任 |
|------|----------|
| Repository | 抛出 RepositoryError |
| QueryService | 翻译 RepositoryError → ServiceError |
| Entry | 翻译 ServiceError → EntrySafeError |

---

## 12. Query Determinism Principle

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

## 13. Language Preservation Principle

> **Record this as an architecture guideline.**

### 13.1 证据

* 始终保留原始语言
* 使用 Workspace 主语言而非强制英语
* 跨语言检索依赖于嵌入（embeddings）而非将存储的记忆翻译成规范语言
* Memory Hub 本身是语言无关的

### 13.2 指导方针

| 原则 | 说明 |
|------|------|
| 不翻译存储内容 | Memory 以原始语言存储和检索 |
| 嵌入是跨语言桥梁 | 多语言嵌入模型处理跨语言语义匹配 |
| QueryService 语言中立 | QueryService 不对语言做任何假设或转换 |

---

## 14. Service Collaboration Matrix

### 14.1 QueryService 协作矩阵

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

### 14.2 矩阵解读

| 符号 | 含义 |
|------|------|
| ✅ | 允许同步调用 |
| ⚠️ | 允许但有限制（需通过抽象/事件/Job） |
| ❌ | 禁止 |

### 14.3 Forbidden Dependencies

| 禁止 | 原因 |
|------|------|
| QueryService → MemoryService | 违反 Service Independence |
| MemoryService → QueryService | 违反 Service Independence |
| QueryService → Repository | 违反 No Layer Skipping |
| Service → Service 同步调用 | 违反 Service Independence |

---

## 15. Verification Strategy

### 15.1 基于架构的验证

> **Verification based on architecture, not implementation.**

### 15.2 验证维度

| 维度 | 验证内容 |
|------|----------|
| **Layer Boundary** | 确认 QueryService 不直接访问 Repository（通过 Engine 或协调层） |
| **Responsibility Boundary** | 确认 QueryService 不包含领域算法（属于 D4 Engine） |
| **Dependency Rules** | 确认单向依赖：QueryService → Engine → Repository |
| **Behavioral Rules** | 确认 QueryService 不产生业务侧效果 |

### 15.3 架构不变量（Architecture Invariants）

| 不变量 | 说明 |
|--------|------|
| I1: 只读性 | QueryService 的任何方法不修改领域状态 |
| I2: 事务所有权 | 所有读事务由 QueryService 管理 |
| I3: 投影归属 | 所有 Projection 在 QueryService 内部完成 |
| I4: 错误映射确定性 | Repository 错误到 Service 错误的映射是确定性的 |
| I5: 幂等性 | 相同查询在相同状态下产生相同结果 |
| I6: 无隐藏命令 | QueryService 不自动触发 Reflection、Embedding、Index Rebuild |

### 15.4 验证独立性原则

> **Verification must remain implementation-independent.**

验证应基于架构契约和不变量，而非具体代码实现细节。这确保了验证在重构、技术栈迁移等场景下仍然有效。

---

## 16. Design Checklist

### 16.1 P0 — 必须满足

| # | 检查项 | 状态 |
|---|--------|------|
| P0-01 | Side-Effect Free Query | ✅ |
| P0-02 | Command / Query Separation | ✅ |
| P0-03 | Service → Service 检查（禁止互调） | ✅ |
| P0-04 | Layer Skipping 检查（不直接访问 Repository） | ✅ |
| P0-05 | Engine DAG 有效 | ✅ |
| P0-06 | Service DAG 有效 | ✅ |
| P0-07 | Query Purity（无隐藏命令） | ✅ |
| P0-08 | 事务所有权在 QueryService | ✅ |

### 16.2 P1 — 强烈建议

| # | 检查项 | 状态 |
|---|--------|------|
| P1-01 | Consumer-Agnostic Interface | ✅ |
| P1-02 | Stable Result Contract | ✅ |
| P1-03 | Public API Family 统一命名 | ✅ |
| P1-04 | Query Planner 存在 | ✅ |
| P1-05 | Shared Domain Engine 原则 | ✅ |
| P1-06 | Continuation Semantics 独立于分页机制 | ✅ |
| P1-07 | Projection 属于 QueryService 而非 Engine | ✅ |
| P1-08 | Repository Coordination 唯一性 | ✅ |
| P1-09 | 投影三层边界清晰 | ✅ |

### 16.3 P2 — 可选增强

| # | 检查项 | 状态 |
|---|--------|------|
| P2-01 | Query Determinism Principle | ✅ |
| P2-02 | Query Consistency（单次执行内一致性） | ✅ |
| P2-03 | Diagnostics 信息可选 | ✅ |
| P2-04 | Query Idempotence | ✅ |
| P2-05 | Language Preservation | ✅ |

### 16.4 ADR Impact Check

| ADR | 影响 | 说明 |
|-----|------|------|
| CQRS | QueryService 是 Query 端 | 与 MemoryService（Command）严格分离 |
| Service Independence | QueryService 不调用其他 Service | 通过 Shared Domain Engine 协作 |
| Consumer-Agnostic Interface | Continuation 独立于协议 | REST/MCP/CLI/SDK 各自适配 |
| One Capability, One Implementation | 每种 Capability 一个实现 | Retrieval/Search/Browse/Projection/Analytics |

---

## 17. Future Evolution

### 17.1 Planned Evolution

| 演进 | 说明 | 阶段 |
|------|------|------|
| Optimizer 独立 | Query Planner 内部 Optimization 演进为独立 Optimizer | V2+ |
| Query Cache | Redis / Memory Cache 集成，Planner 路由 | V2+ |
| Query Metrics | 执行时间、Engine 耗时、Hit Rate 监控 | V2+ |
| Machine Verifiable Matrix | Service Collaboration Matrix 静态分析 | V3+ |

### 17.2 Potential Evolution

| 演进 | 说明 |
|------|------|
| AI Planner | 基于 LLM 的智能查询规划 |
| Cost Estimator | 查询成本预估 |
| Query Federation | 跨源查询（本地 + 外部） |

---

## 18. 与 Phase A 文档的关系

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
| Query Purity | 除基础设施侧效果外无业务侧效果 | 本文档 (v2.0) |
| Domain Processing | Repository 结果到 Projection 之间的处理阶段 | 本文档 (v2.0) |
| Repository Coordination | QueryService 协调一个或多个 Repository | 本文档 (v2.0) |
| Query Idempotence | 相同查询+相同状态=相同业务结果 | 本文档 (v2.0) |
| Language Preservation | 保留原始语言，嵌入是跨语言桥梁 | 本文档 (v2.0) |
| Observational Consistency | 查询不改变被观察的业务状态 | 本文档 (v2.0) |
| Capability Composition | 公共查询能力可在 QueryService 内部组合 | 本文档 (v2.0) |

---

## 附录 B：文档变更记录

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|----------|------|
| 1.1 | 2026-06-27 | Phase B-3 修订：(1) 新增 QueryService 定位原则 (2) Decision Summary 补充 23~34 (3) 回溯更新表补充 10_3 (4) 新增 13 Architecture Guidelines 引用 | ✅ 已确认 |
| 1.2 | 2026-06-28 | Phase B-5 修订：(1) 补充 QueryService 消费 Entity 信息但不拥有 Entity 状态的角色（与 10_5 对齐）(2) Decision Summary 补充 38 | ✅ 已确认 |
| **2.0** | **2026-07-09** | **D3.3 架构讨论集成：(1) 统一读工作流冻结（Validation→Planning→Repository Coordination→Domain Processing→Projection→Result Assembly）(2) 移除 "Simple Merge" 表述，使用 "Domain Processing"(3) Repository 协调原则（唯一协调者、不互调、不组装跨聚合结果）(4) Read Pipeline 原则（Single Flow、Forward-Only、Immutable Intermediate、Stateless）(5) 投影三层边界（Domain Model → Domain View → Entry DTO）(6) Query Purity Principle（禁止隐藏命令）(7) Observational Consistency(8) Query Idempotence Principle(9) Capability Composition Principle(10) Transaction Strategy（只读事务、QueryService 拥有）(11) Error Mapping（Repository→Service→Entry 确定性映射）(12) Language Preservation Principle(13) Verification Strategy（基于架构的验证、不变量）(14) 新增附录术语对照(15) 与 D3.1/D3.2/Repository 原则/分层架构/CQS/Service Orchestrator/Engine 责任边界/Failure Isolation/Export 原则完全一致** | **✅ 已确认** |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

*本文档是 Phase B 的 QueryService 设计文档，后续 10_4~10_N 文档均引用本文档的 Service Collaboration Matrix 规范。*
