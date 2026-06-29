# Personal AI Memory Hub — Implementation Service Layer 设计文档

> **版本**: 1.0
> **日期**: 2026-06-26
> **阶段**: Phase B — 实现设计（第一部分）
> **状态**: 已确认
> **作者**: 系统架构组

---

## 1. Purpose

本文档将 Phase A（01~09）的架构设计转化为**可编码的服务层架构**。

它定义：

* 代码的分层结构
* Service 的分类与职责
* Repository 的边界
* Engine 的组成与依赖
* Service 之间的协作规则
* API Entry 层的定位
* 依赖规则与约束
* MVP 实施顺序
* 未来扩展原则

本文档是 Phase B 所有后续实现设计文档（10_2~10_N）的**总纲**，后续文档均引用本文档。

---

## 2. Design Principles

### 2.1 文档即项目记忆（Project Memory）

> 项目文档不是代码的说明，而是项目的长期记忆。

本文档承担四个作用：

| 作用 | 说明 |
|------|------|
| Design Record | 记录最终决策与设计理由 |
| Implementation Guide | 为未来编码提供唯一依据 |
| Knowledge Base | 开发者（包括未来的自己）或 AI 可直接读取文档恢复完整上下文 |
| Architecture Contract | 后续代码实现不得随意突破文档中已确定的边界 |

### 2.2 三层记忆哲学

```
Chat 对话（Working Memory — 思考过程）
    ↓ 沉淀为
设计文档（Long-term Memory — 长期记忆）
    ↓ 实现为
代码（Executable Memory — 执行结果）
```

### 2.3 核心工程原则

| 原则 | 说明 |
|------|------|
| Memory First | 记忆是核心，所有设计围绕记忆展开 |
| Evidence-Based Memory | 所有认知升级基于证据，不基于时间（参见 05） |
| Capability-Based Agent | 每个 Engine 封装一个独立能力（Capability） |
| Document-Driven Design | 以文档为权威来源，而非对话历史 |
| One Capability One Implementation | 每个能力只有一个实现，复用优于复制 |

---

## 3. Layered Architecture

### 3.1 五层模型

```
┌─────────────────────────────────────────────┐
│  Entry Layer                               │  ← REST / MCP / CLI / SDK / Agent
├─────────────────────────────────────────────┤
│  Application Service Layer                 │  ← Use Case / Workflow / Transaction
├─────────────────────────────────────────────┤
│  Domain Engine Layer                       │  ← Capability / Stateless / Reusable
├─────────────────────────────────────────────┤
│  Repository Layer                          │  ← CRUD / Query / Persistence
├─────────────────────────────────────────────┤
│  Database (Supabase / PostgreSQL)          │  ← Storage only
└─────────────────────────────────────────────┘
```

### 3.2 各层职责

| 层 | 职责 | 禁止 |
|----|------|------|
| **Entry Layer** | 协议适配、DTO 转换、认证、能力检查 | 业务逻辑、排序、检索、Reflection、SQL |
| **Application Service** | Use Case 编排、事务控制、权限判断、Engine/Repository 协调 | 底层算法、LLM 调用、Prompt 编写 |
| **Domain Engine** | 实现独立能力（Capability）、无状态、可单元测试 | 数据库访问、HTTP 调用、API 依赖 |
| **Repository** | CRUD、Query、事务支持、持久化 | 业务逻辑、排序、Reflection、Prompt、图推理、Context 构建 |
| **Database** | 数据存储 | 业务逻辑、应用层计算 |

### 3.3 调用方向

```
Entry
  ↓
Service
  ↓
Engine + Repository（Service 可同时编排 Engine 和 Repository）
  ↓
Database
```

**唯一允许跨层调用的是：Service → Repository。**

Engine **不直接访问** Repository。
Engine **不直接调用** Service。
Entry **不直接调用** Engine 或 Repository。

### 3.4 架构理由

| 设计 | 理由 |
|------|------|
| Engine 无数据库依赖 | Engine 可独立单元测试，可替换为本地模型/云模型/独立微服务 |
| Service 编排 Engine + Repository | Service 是真正的业务入口，负责协调多个能力 |
| Entry 层纯粹适配 | 新增入口（Telegram/Discord/VSCode）只需新增 Entry，不改其他层 |
| Repository 只做持久化 | 业务逻辑留在 Engine，避免 Repository 变成第二个 Service |

---

## 4. Service Classification

### 4.1 Service 清单

Application Service 层包含以下 Service，每个 Service 负责一个完整 Use Case：

| # | Service | 职责 | 编排的 Engine | 依赖的 Repository |
|---|---------|------|--------------|-------------------|
| 1 | **MemoryService** | Memory Domain Service（Capture/Import/Merge/Archive/Lifecycle），**不是 CRUD Service** | MemoryEngine, ArchiveEngine | EntityRepo, MemoryNodeRepo, RelationshipRepo |
| 2 | **IngestionService** | 证据摄入、Pipeline 编排 | IngestionEngine, ScoringEngine | EvidenceRepo, EntityRepo |
| 3 | **ReflectionService** | Reflection 任务编排 | ReflectionEngine, CandidateEngine | MemoryNodeRepo, CandidateRepo, RelationshipRepo |
| 4 | **QueryService** | 记忆检索、Context 构建 | RetrievalEngine, ContextBuilder | MemoryNodeRepo, VectorDocRepo, RelationshipRepo |
| 5 | **ContextService** | Context 组装与输出 | ContextBuilder, ActivationEngine | （无独立 Repository） |
| 6 | **TaskService** | 任务调度管理 | Scheduler | TaskRepo |

### 4.2 Service 职责原则

Application Service 负责：

* **Use Case** — 完整业务流程
* **Workflow** — 多步骤编排
* **Transaction 协调** — 事务边界协调（不负责数据库事务控制）
* **Repository 协调** — 决定何时读/写 Repository
* **Engine 协调** — 决定何时调用哪个 Engine
* **Domain Event 发布** — 业务完成后发布事件解耦

Service **不负责**：

* 领域算法（由 Engine 实现）
* 数据持久化细节（由 Repository 实现）
* 协议适配（由 Entry 实现）
* 数据库事务控制（由 Repository / Unit of Work 实现）

### 4.2.1 Domain Service 原则（Phase B 新增）

> **MemoryService is a Domain Service, not an Application CRUD Service.**
> **Public APIs are organized around domain capabilities instead of persistence operations.**

Service 不得暴露 `create()` / `update()` / `delete()` / `find()` 等 Repository 风格接口。

### 4.2.2 Command / Query Separation 原则（Phase B 新增）

> **Command Returns Identity, Query Returns State.**

| 操作类型 | 所属 Service | 返回值 |
|----------|-------------|--------|
| Command（写） | MemoryService | `MemoryId` / `JobId` / `Status` / `ImportReport` |
| Query（读） | QueryService | `Memory` / `MemoryView` / `Context` / `Evidence` |

MemoryService **不承担 Query 职责**。所有 Memory 数据读取统一由 QueryService 提供。

### 4.3 ContextService 的特殊性

ContextService **不拥有独立 Repository**。

理由：

* Context 的数据来源于 QueryService 和 ActivationEngine 的输出
* ContextService 是编排层，不是数据层
* 它协调 ContextBuilder Engine 和 ActivationEngine，但不直接读写数据库

### 4.4 Service 数量控制

| 原则 | 说明 |
|------|------|
| 一个 Service = 一个 Use Case Group | 不要为单个 API 端点创建一个 Service |
| 复用优先于复制 | 多个 Use Case 共享逻辑时，提取为 Engine 而非创建新 Service |
| 未来扩展 | 新增 Use Case 时新增 Service，不修改既有 Service |

---

## 5. Repository Layer

### 5.1 Repository 职责

Repository 层只负责：

* **CRUD** — 创建、读取、更新（仅限 archive/correct）、删除（软删除）
* **Query** — 按条件查询，返回原始数据
* **Transaction 支持** — 保证数据一致性

### 5.2 Repository 禁止事项

Repository **不得**：

* 包含业务逻辑
* 调用另一个 Repository
* 调用 Engine
* 调用 Service
* 执行排序、检索评分、Reflection
* 编写 Prompt
* 进行图推理
* 构建 Context

### 5.3 Repository 组织方式

Repository **按 Domain Aggregate 组织，而非按数据库表组织**。

| Repository | 聚合域 | 对应表 |
|------------|--------|--------|
| EntityRepository | Entity 聚合 | entities, areas, workspace |
| MemoryNodeRepository | MemoryNode 聚合 | memory_nodes, memory_evidences |
| EvidenceRepository | Evidence 聚合 | evidences |
| RelationshipRepository | Relationship 聚合 | relationships |
| VectorDocRepository | Vector 聚合 | vector_documents |
| ArchiveRepository | Archive 聚合 | archives, archive_sources |
| TagRepository | Tag 聚合 | tags, tag_links |
| TaskRepository | Task 聚合 | tasks |
| CandidateRepository | Candidate 聚合 | candidates |

### 5.4 QueryRepository

引入 **QueryRepository** 模式，用于复杂查询：

| QueryRepository | 说明 |
|-----------------|------|
| MemoryQueryRepository | 复杂检索查询（多表 JOIN、条件组合） |
| EntityQueryRepository | Entity 图查询（遍历 relationships） |
| VectorQueryRepository | 向量相似度查询 |

**原则**：QueryRepository 仍然是持久化层，不包含业务逻辑。

### 5.5 Repository 边界

| 规则 | 说明 |
|------|------|
| 一个 Repository = 一个 Domain Aggregate | 不是每张表一个 Repository |
| Repository 之间不互相调用 | 跨聚合查询由 Service 编排 |
| Repository 不依赖 Engine | Repository 是纯粹的持久化工具 |

---

## 6. Engine Composition

### 6.1 Engine 定位

Engine 代表**领域能力（Domain Capability）**。

Engine 是：

* **无状态** — 不持有会话状态
* **可复用** — 被多个 Service 调用
* **能力导向** — 每个 Engine 封装一个独立能力
* **可单元测试** — 不依赖数据库、HTTP、API

Engine **不是**：

* Agent
* Service
* Repository
* 业务编排层

### 6.2 Engine 清单

| # | Engine | 所属层 | 职责 | 输入 | 输出 | 被谁调用 |
|---|--------|--------|------|------|------|----------|
| 1 | **MemoryEngine** | Domain | 记忆领域编排器 | MemoryCommand | MemoryResult | MemoryService |
| 2 | **IngestionEngine** | Domain | 证据摄入 Pipeline | Conversation | Observation | IngestionService |
| 3 | **ScoringEngine** | Domain | 三套评分计算 | Observation | confidence/importance/signal_strength | IngestionEngine |
| 4 | **ReflectionEngine** | Domain | 记忆反思（Light + Heavy） | Observation Pool | Pattern + Belief | ReflectionService |
| 5 | **CandidateEngine** | Domain | 候选生成与验证 | Pattern Candidates | Confirmed Pattern | ReflectionService |
| 6 | **ActivationEngine** | Domain | State 动态激活 | Belief + Context | State | ContextService |
| 7 | **RetrievalEngine** | Domain | 多维检索 | Query | Related Memories | QueryService |
| 8 | **ContextBuilder** | Domain | 四层 Context 构建 | Retrieval Results + States | Prompt Context | ContextService |
| 9 | **ArchiveEngine** | Domain | 认知压缩归档 | Memory Batch | Archive Result | MemoryService |
| 10 | **EvidenceEngine** | Domain | 证据链管理与验证 | Memory ID | Evidence Chain | MemoryEngine |
|| 11 | **RelationshipEngine** | Domain | 图关系管理 | Entity IDs | Relationships | MemoryEngine / EntityService |
|| 12 | **EntityEngine** | Domain | 身份管理（Resolution / Merge / Alias / Canonical Name） | Entity Command | Entity Result | EntityService |

### 6.3 Composite Engine 模式

MemoryEngine 是**复合 Engine**，由多个 Atomic Engine 组合而成：

```
MemoryEngine (Composite)
  ├── ArchiveEngine
  ├── EvidenceEngine
  ├── RelationshipEngine
  └── CandidateEngine
```

MemoryEngine **不直接访问 Repository**。它通过 Service 层协调。

### 6.4 Engine 依赖关系

Engine 之间的依赖构成 DAG（有向无环图）：

```
IngestionEngine → ScoringEngine
ReflectionEngine → CandidateEngine
RetrievalEngine → （无 Engine 依赖）
ContextBuilder → RetrievalEngine, ActivationEngine
ActivationEngine → （无 Engine 依赖）
MemoryEngine → ArchiveEngine, EvidenceEngine, RelationshipEngine, CandidateEngine
```

**Engine 之间不允许循环依赖。**

### 6.5 Engine 无 Repository 依赖

| 规则 | 说明 |
|------|------|
| Engine 不直接访问 Repository | Engine 通过 Service 层获取数据 |
| Engine 只处理内存中的对象 | Engine 的输入是 DTO/Value Object，输出是 DTO/Value Object |
| 数据持久化由 Service + Repository 完成 | Service 调用 Engine 处理后，再由 Repository 持久化 |

---

## 7. Cross-Service Collaboration

### 7.1 Service 协作规则

Service 之间**不直接互相调用**。

所有 Service 协作通过 Engine 层完成：

```
Service A
  ↓ 调用
Engine X
  ↓ 输出
Service B（如果需要）
```

**例外**：Service 可以通过 Event/Message 异步通知其他 Service（V2+ 预留）。

### 7.2 典型协作场景

#### 场景 1：记忆摄入

```
IngestionService
  → IngestionEngine（Chunking → Extraction → Entity Linking → Validation）
  → ScoringEngine（计算评分）
  → 写入 Repository
  → 触发 ReflectionService（通过 Event 或 Task）
```

#### 场景 2：记忆检索与 Context 构建

```
QueryService
  → RetrievalEngine（Vector + Graph + Hybrid）
  → 返回检索结果
  → ContextService
     → ActivationEngine（激活 Belief → State）
     → ContextBuilder（Rank → Compress → Assemble）
     → 返回 ContextPackage
```

#### 场景 3：记忆修正

```
MemoryService
  → correctMemory()
  → EvidenceEngine（验证修正证据）
  → 写入新 MemoryNode（保留旧版本）
  → 更新 relationships（CORRECTS 关系）
```

#### 场景 4：Reflection 触发

```
IngestionService（写入新 Observation）
  → 创建 REFLECTION Task（通过 TaskService）
  → ReflectionService 拾取 Task
  → ReflectionEngine（Light Reflect → Pattern → Heavy Reflect → Belief）
  → 写入 MemoryNode
  → 触发 ActivationEngine（State 刷新）
```

### 7.3 Service 与 Engine 的关系矩阵

| Service | Ingestion | Scoring | Reflection | Candidate | Activation | Retrieval | ContextBuilder | Archive | Evidence | Relationship | Memory |
|---------|-----------|---------|------------|-----------|------------|-----------|----------------|---------|----------|--------------|--------|
| IngestionService | ✅ | ✅ | | | | | | | | | |
| MemoryService | | | | | | | | ✅ | ✅ | ✅ | ✅ |
| EntityService | | | | | | | | | ✅ | ✅ | ✅ |
| ReflectionService | | | ✅ | ✅ | ✅ | | | | | | |
| QueryService | | | | | | ✅ | | | | | |
| ContextService | | | | | ✅ | | ✅ | | | | |
| TaskService | | | | | | | | | | | |

### 7.4 Service Collaboration Matrix（Phase B 统一规范）

> **Phase B 规范**：每个 Service 文档必须包含 Service Collaboration Matrix。所有矩阵合并形成完整的 Service Dependency Graph。

| 规范 | 说明 |
|------|------|
| 每个 Service 文档末尾必须包含固定章节 | Service Collaboration Matrix |
| Matrix 必须包含 5 列 | Caller, Callee, Allowed, Interaction Pattern, Reason |
| Allowed 使用三级符号 | ✅ 允许同步调用, ⚠️ 允许但有限制, ❌ 禁止 |
| Interaction Pattern 标注调用方式 | Sync, Async Preferred, Job Dispatch, Event |
| 所有 Matrix 合并后形成 | Complete Service Dependency Graph |
| 用于 | Consistency Review / Architecture Review / Implementation Review / DAG 验证 |

**示例**（MemoryService → QueryService）：

| Caller | Callee | Allowed | Interaction Pattern | Reason |
|--------|--------|---------|---------------------|--------|
| MemoryService | QueryService | ❌ | N/A | 防止 Command → Query 耦合，CQRS 分离 |

---

## 8. API Entry Layer

### 8.1 术语变更

> API Layer 更名为 **API Entry Layer**。

### 8.2 Entry 层职责

| 职责 | 说明 |
|------|------|
| 协议适配 | REST / MCP Tool / CLI / SDK / Agent 的统一适配 |
| DTO 转换 | 外部格式 ↔ 内部 Domain Object |
| 认证 | 身份验证与授权 |
| 能力检查 | 检查目标能力是否可用 |

Entry 层**不包含**：

* 业务逻辑
* 排序
* 检索
* Reflection
* SQL

### 8.3 Entry 适配器清单

| 适配器 | 协议 | 说明 | MVP |
|--------|------|------|-----|
| REST Adapter | HTTP REST | 标准 REST API | ✅ |
| MCP Adapter | MCP Tool | MCP Protocol 工具调用 | V2+ |
| CLI Adapter | 命令行 | 本地 CLI 工具 | V2+ |
| SDK Adapter | SDK | 客户端 SDK | V2+ |
| Agent Adapter | Agent Protocol | Hermes / Claude / Gemini 等 Agent 集成 | V2+ |

### 8.4 Entry 层设计原则

| 原则 | 说明 |
|------|------|
| One Capability, One Implementation | 每个能力只有一个实现，多个 Entry 适配器共享 |
| Multiple Entry Adapters | 同一 Service 可通过多个 Entry 适配器暴露 |
| Entry 不持有状态 | Entry 是纯粹的适配层 |
| 新增入口不改 Service | 新增 Telegram Bot / Discord Bot 只需新增 Entry Adapter |

### 8.5 请求处理流程示例

```
POST /memory/search  (REST Entry)
    ↓
DTO 转换：SearchRequest → QueryCommand
    ↓
Auth 检查
    ↓
QueryService.search(QueryCommand)
    ↓
RetrievalEngine + ContextBuilder
    ↓
返回 ContextPackage
    ↓
DTO 转换：ContextPackage → SearchResponse
    ↓
REST Response
```

---

## 9. Dependency Rules

### 9.1 分层依赖规则

```
Entry → Service → Engine → Repository → Database
```

**禁止跨层调用**：

| 禁止 | 说明 |
|------|------|
| Entry → Engine | Entry 必须通过 Service |
| Entry → Repository | Entry 不直接接触数据层 |
| Engine → Service | Engine 不编排其他能力 |
| Engine → Repository | Engine 不直接访问数据库 |
| Repository → Engine | Repository 是纯粹的数据访问层 |
| Repository → Repository | 跨聚合查询由 Service 编排 |

**唯一例外**：Service → Repository（Service 可直接调用 Repository）。

### 9.2 Service DAG

Service 之间不互相调用，但通过 Engine 形成依赖 DAG：

```
IngestionService → ScoringEngine
ReflectionService → ReflectionEngine, CandidateEngine
MemoryService → MemoryEngine, ArchiveEngine
EntityService → EntityEngine, EvidenceEngine, RelationshipEngine
QueryService → RetrievalEngine
ContextService → ActivationEngine, ContextBuilder
TaskService → Scheduler
```

### 9.3 Engine DAG

Engine 之间的依赖也必须保持 DAG：

```
ScoringEngine → （无依赖）
IngestionEngine → ScoringEngine
ReflectionEngine → （无依赖）
CandidateEngine → ReflectionEngine
ActivationEngine → （无依赖）
RetrievalEngine → （无依赖）
ContextBuilder → RetrievalEngine, ActivationEngine
MemoryEngine → ArchiveEngine, EvidenceEngine, RelationshipEngine, CandidateEngine
EntityEngine → （无依赖）
RelationshipEngine → （无依赖）
```

**Engine 之间不允许循环依赖。**

### 9.4 核心依赖规则总结

| 规则 | 说明 |
|------|------|
| 分层依赖 | 只能调用下一层，不能跨层 |
| 无层跳跃 | Entry 不能跳过 Service 直接调 Engine |
| Service DAG | Service 通过 Engine 形成有向无环依赖 |
| Engine DAG | Engine 之间形成有向无环依赖 |
| Repository 隔离 | Repository 不依赖 Engine 或 Service |
| Engine 无 Repository 依赖 | Engine 只处理内存对象 |
| One Capability One Implementation | 每个能力只有一个 Engine 实现 |
| Capability 复用优于 Service 滥用 | 共享逻辑提取为 Engine，而非在 Service 中复制 |

### 9.5 规则理由

| 规则 | 为什么 |
|------|--------|
| 无层跳跃 | 防止架构退化，保持职责清晰 |
| Engine 无 Repository 依赖 | Engine 可独立测试、可替换、可迁移 |
| One Capability One Implementation | 避免重复实现，确保行为一致 |
| Capability 复用 | 新增需求时组合已有 Engine，而非创建新 Service |

---

## 10. MVP Implementation Order

### 10.1 实施阶段

| 阶段 | 内容 | 对应文档 |
|------|------|----------|
| **Phase B-1** | Entry + Service + Engine 骨架 | 10_1（本文档） |
| **Phase B-2** | MemoryService + MemoryEngine + Ingestion | 10_2 |
| **Phase B-3** | QueryService + RetrievalEngine | 10_3 |
| **Phase B-4** | ReflectionService + ReflectionEngine | 10_4 |
| **Phase B-5** | ContextService + ContextBuilder | 10_5 |
| **Phase B-6** | TaskService + Scheduler | 10_6 |
| **Phase B-7** | API Contract + Integration | 10_7 |

### 10.2 MVP 必须实现的组件

| 序号 | 组件 | 所属层 | 说明 |
|------|------|--------|------|
| 1 | REST Entry | Entry | 基础 REST API |
| 2 | IngestionService | Service | 证据摄入 |
| 3 | MemoryService | Service | 记忆 CRUD |
| 4 | QueryService | Service | 记忆检索 |
| 5 | IngestionEngine | Engine | 证据摄入 Pipeline |
| 6 | ScoringEngine | Engine | 三套评分 |
| 7 | RetrievalEngine | Engine | 多维检索 |
| 8 | ContextBuilder | Engine | 四层 Context |
| 9 | ActivationEngine | Engine | State 激活 |
| 10 | **MemoryEngine** | Engine | 记忆领域编排 |
| 11 | **EntityRepository** | Repository | Entity 持久化 |
| 12 | **EntityEngine** | Engine | 身份管理（Resolution / Merge / Alias） |
| 13 | MemoryNodeRepository | Repository | MemoryNode 持久化 |
| 14 | EvidenceRepository | Repository | Evidence 持久化 |
| 15 | RelationshipRepository | Repository | Relationship 持久化 |

### 10.3 MVP 暂缓（V2+）

| 组件 | 说明 |
|------|------|
| MCP Adapter | 预留接口，MVP 不实现 |
| CLI Adapter | 预留接口，MVP 不实现 |
| SDK Adapter | 预留接口，MVP 不实现 |
| Agent Adapter | 预留接口，MVP 不实现 |
| ArchiveEngine | MVP 仅实现概念，完整归档逻辑 V2+ |
| Event System | 预留 event/ 目录，MVP 不实现 |

---

## 11. Future Extension

### 11.1 Entry 扩展

新增入口（Telegram Bot / Discord / WeChat / VSCode Plugin）：

* 只需在 `entry/` 下新增适配器
* **不修改** Service 层
* **不修改** Engine 层

### 11.2 Engine 扩展

新增能力（Timeline / Summarization / Learning）：

* 在 `engine/` 下新增 Engine
* 通过 MemoryEngine 或其他 Composite Engine 组合
* **不修改**既有 Engine 的内部实现

### 11.3 Repository 扩展

未来可能引入 Neo4j / Milvus / OpenSearch：

* Repository 层负责适配
* Service 和 Engine **不感知**底层存储变更

### 11.4 Capability 扩展原则

> 新增能力优先采用新增 Capability（Engine）的方式扩展，而不是修改既有 Capability。

**示例**：

```
未来新增 Timeline 能力：
  ✅ 新增 TimelineEngine，MemoryEngine 组合它
  ❌ 在 MemoryEngine 中直接添加 timeline() 方法
```

这符合 **Open-Closed Principle**（开闭原则）。

### 11.5 Capability Registry（未来构想）

未来所有 Engine 自动注册到 Capability Registry：

```
CapabilityRegistry
  ├── ArchiveEngine
  ├── RankingEngine
  ├── ReflectionEngine
  ├── TimelineEngine
  └── ...
```

Agent / MCP Server 可动态查询 Memory Hub 有哪些能力，而非硬编码。

---

## 12. Common Module Boundary

### 12.1 项目结构

```
src/
├── entry/              # Entry Adapters（REST / MCP / CLI / SDK / Agent）
├── service/            # Application Services
├── engine/             # Domain Engines
├── repository/         # Repository Layer
├── shared/             # Common Module（仅纯数据和工具）
│   ├── models/         # Shared Models / DTO / Value Object
│   ├── infrastructure/ # Infrastructure Utilities
│   └── utils/          # Pure Algorithms / Helpers
├── config/             # Configuration
└── event/              # Reserved for future event system
```

### 12.2 Common Module 允许内容

`shared/` 仅允许存放：

| 类型 | 说明 |
|------|------|
| Shared Models | 跨层共享的数据模型 |
| DTO | 数据传输对象 |
| Value Object | 不可变值对象 |
| Infrastructure | 基础设施工具（日志、配置加载等） |
| Utility | 纯算法工具函数 |

### 12.3 Common Module 禁止内容

`shared/` **不得**存放：

| 禁止 | 说明 |
|------|------|
| 业务逻辑 | 必须在 Domain Engine 中 |
| 数据访问 | 必须在 Repository 中 |
| 编排逻辑 | 必须在 Service 中 |
| HTTP 处理 | 必须在 Entry 中 |

### 12.4 原则

> 业务逻辑必须保留在 Domain Engine 中。
> Common 只提供工具和数据结构，不提供能力。

---

## 13. Project Memory Philosophy

### 13.1 记忆层级

本项目存在三层记忆：

| 层级 | 载体 | 性质 | 寿命 |
|------|------|------|------|
| Working Memory | Chat 对话 | 思考过程 | 会话级 |
| Long-term Memory | 设计文档 | 长期记忆 | 项目级 |
| Executable Memory | 代码 | 执行结果 | 部署级 |

### 13.2 决策沉淀流程

```
讨论
  ↓ 达成一致
写入设计文档
  ↓ 以文档为准
未来以文档为依据
```

**不采用**：

```
讨论
  ↓ 直接写代码
  ↓ 文档缺失
  ↓ 未来遗忘
```

### 13.3 文档用途

| 用途 | 说明 |
|------|------|
| 给人看 | 恢复设计初衷，理解为什么这样做 |
| 给 AI 看 | AI 编码时读取文档作为知识库，保证不同模型生成一致的代码风格 |

---

## 14. Decision Summary

### 14.1 最终架构决议

| # | 决议 | 影响范围 |
|---|------|----------|
| 1 | **五层架构**：Entry → Service → Engine → Repository → Database | 整个项目结构 |
| 2 | **MemoryEngine 重新定义**：Memory Domain Orchestrator，协调 Archive/Evidence/Relationship/Candidate Engine，不直接访问 Repository | 02、06、08 |
| 3 | **Engine 是领域能力**：无状态、可复用、能力导向，不是 Agent/Service/Repository | 所有 Engine 文档 |
| 4 | **Repository 仅持久化**：CRUD/Query/Transaction，不含业务逻辑，按 Domain Aggregate 组织 | 所有 Repository |
| 5 | **QueryRepository 引入**：复杂查询专用 Repository，仍是持久化层 | Repository 层 |
| 6 | **API Entry Layer**：术语从 API Layer 改为 API Entry Layer，职责为协议适配/DTO/认证/能力检查 | Entry 层 |
| 7 | **ContextService 无 Repository**：ContextService 不拥有独立 Repository | 02、06 |
| 8 | **Service DAG + Engine DAG**：所有依赖必须保持有向无环图 | 所有 Service/Engine |
| 9 | **无层跳跃**：禁止跨层调用，唯一例外 Service → Repository | 所有层 |
| 10 | **One Capability One Implementation**：每个能力只有一个 Engine 实现 | Engine 层 |
| 11 | **Capability 复用优于 Service 滥用**：共享逻辑提取为 Engine | Service 层 |
| 12 | **Common 模块边界**：仅共享模型/DTO/Value Object/Infrastructure/Utility，业务逻辑在 Engine | shared/ |
| 13 | **Project Memory 哲学**：文档 = 长期记忆，Chat = 工作记忆，代码 = 可执行记忆 | 整个项目 |
| 14 | **未来项目结构**：entry/service/engine/repository/shared/infrastructure/config/event | 工程目录 |
| 16 | **Domain Service 原则** | MemoryService is a Domain Service, not CRUD. Public APIs organized by capability | 10_1、10_2 |
| 17 | **Command / Query Separation** | Command Returns Identity, Query Returns State. MemoryService ≠ QueryService | 10_1、10_2 |
| 18 | **Service Collaboration Matrix** | 每个 Service 文档必须包含 Matrix，合并形成完整 Service Dependency Graph | 10_1、10_2 |
| 19 | **Error Model** | 统一 MemoryResult / ImportResult 返回模型，不依赖 Exception 作为控制流程 | 10_2 |
| 20 | **Domain Events** | Service 间通过事件解耦，不直接互相调用 | 10_2 |
| 21 | **Transaction Policy** | 默认 PerMemory，可扩展为 PerChunk / WholeBatch | 10_2 |
| 22 | **Recovery Policy** | 默认 ContinueOnError，可扩展为 StopOnFatal / StopAfterNFailures | 10_2 |
| 23 | **Query Service 定位** | QueryService 是纯读服务，Side-Effect Free，与 MemoryService 严格分离 | 10_3 |
| 24 | **五大 Query Capability** | Retrieval / Search / Browse / Projection / Analytics | 10_3 |
| 25 | **Query Planner** | Query Planning Before Execution，Optimization 为 Planner 内部能力 | 10_3 |
| 26 | **Engines Produce Domain Knowledge** | Engine 返回 Domain Result，Projection 属于 QueryService | 10_3 |
| 27 | **Service Independence Principle** | Service 之间不互相同步调用，通过 Shared Domain Engine 协作 | 10_3 |
| 28 | **Command Return Policy** | Command 后基于当前 Domain Object 构建返回，不得再次 Query | 10_3 |
| 29 | **Consumer-Agnostic Interface** | 面向能力设计，不面向调用方设计 | 10_3 |
| 30 | **Stable Result Contract** | QueryResult 能力无关、协议无关 | 10_3 |
| 31 | **Continuation Semantics** | QueryService 定义 Continuation，Entry 决定协议 | 10_3 |
| 32 | **Streaming 归属** | Streaming 是 Entry Delivery Strategy，不是 Query Capability | 10_3 |
| 33 | **Query Determinism** | 相同条件下语义一致 | 10_3 |
|| 34 | **Architecture Guidelines (13)** | 22 条 Guideline 编号体系（G-001~G-022） | 13 |
|| 35 | **EntityService 定位** | Identity Management 能力所有者，不是 CRUD | 10_5 |
|| 36 | **Asynchronous Reference Migration** | Merge 后发布事件，Task Runtime 异步执行 | 10_5 |
|| 37 | **EntityID Stability** | EntityID 永不改变，属性通过证据演化 | 10_5 |
|| 38 | **No Entity Version** | 历史通过 L0 + Evidence + Events 自然存在 | 10_5 |

### 14.2 对旧文档的回溯更新

以下旧文档需要同步更新（详见 ChangeReport_09）：

| 文档 | 更新内容 |
|------|----------|
| 02 | MemoryEngine 重新定义为 Memory Domain Orchestrator |
| 02 | ContextService 无 Repository 的说明 |
| 06 | Engine 重新定义为 Domain Capability |
| 06 | API Entry Layer 术语变更 |
| 08 | Service/Engine/Repository 边界更新 |
| 08 | 依赖规则补充 |
| 10_1 | Service Layer 总纲 | Service 分类更新（MemoryService 不是 CRUD）、新增 Domain Service 原则、C/Q 分离、Service Collaboration Matrix 规范 |
|| 10_3 | Query Service 定位 + 五大 Query Capability + Query Planner + Service Independence + Consumer-Agnostic + Stable Result Contract |
|| 10_5 | EntityService 定位 + Identity Evolution + Asynchronous Reference Migration + EntityID Stability + No Entity Version |

---

## 15. 与前序文档的关系

| 文档 | 引用关系 |
|------|----------|
| 01 | 记忆类型体系、生命周期、分类体系（本文档将其映射为 Service/Engine 职责） |
| 02 | MemoryEngine 重新定义、Context Builder 四层结构（本文档定义 Engine 层实现） |
| 03 | Entity / MemoryNode / Relationship 模型（本文档定义 Repository 聚合边界） |
| 04 | Schema / Reflect / Archive（本文档定义 Service 如何协调 Reflect 和 Archive） |
| 05 | Lifecycle / Reflection Engine（本文档定义 IngestionService 和 ReflectionService 的编排） |
| 06 | Runtime Architecture（本文档将 Engine 落地为可编码的 Domain Engine） |
| 07 | Boundary Review（本文档遵守 P1-P9 边界约束） |
| 08 | Implementation Architecture（本文档在其基础上细化 Service 层） |
| 09 | Database Physical Design（本文档的 Repository 层映射到 09 的表结构） |

---

## 附录 A：术语对照

| 术语 | 说明 | 出处 |
|------|------|------|
| Application Service | 负责 Use Case 编排的业务入口层 | 本文档 |
| Domain Engine | 封装独立能力的无状态组件 | 本文档 |
| Repository | 纯粹的持久化层 | 本文档 |
| API Entry Layer | 协议适配层，不含业务逻辑 | 本文档 |
| Memory Domain Orchestrator | MemoryEngine 的新定位，协调多个子 Engine | 本文档 |
| Capability Registry | 未来 Engine 自动注册的构想 | 本文档 |
| Project Memory | 文档 = 长期记忆，Chat = 工作记忆，代码 = 可执行记忆 | 本文档 |

---

## 附录 B：文档变更记录

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|----------|------|
| 1.2 | 2026-06-27 | Phase B-3 修订：(1) 新增 QueryService 定位原则 (2) Decision Summary 补充 23~34 (3) 回溯更新表补充 10_3 (4) 新增 13 Architecture Guidelines 引用 | ✅ 已确认 |
| 1.3 | 2026-06-28 | Phase B-5 修订：(1) 新增 EntityEngine（#12）到 Engine 清单 (2) 新增 EntityService 到 Service Collaboration Matrix (3) 新增 EntityService 到 Service DAG / Engine DAG (4) Decision Summary 补充 35~38 (5) 回溯更新表补充 10_5 | ✅ 已确认 |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

*本文档是 Phase B 的总纲文档，后续 10_2~10_N 文档均引用本文档的分层架构和依赖规则。*
