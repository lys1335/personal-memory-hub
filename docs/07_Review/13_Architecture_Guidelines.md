# Personal AI Memory Hub — 13 Architecture Guidelines

> **版本**: 1.1  
> **日期**: 2026-06-30  
> **阶段**: Phase B — 工程规范（Living Guideline）  
> **状态**: 已确认  
> **说明**: 本文档是项目的规范中心（Normative Reference），后续 10_x 文档持续更新。当前包含 G-001~G-055。

---

## 1. Public API Design

### G-001: One Capability, One Implementation

> 每个能力只有一个实现，复用优于复制。

| 规则 | 说明 |
|------|------|
| 一个能力 | 如 Retrieval、Search、Archive |
| 一个实现 | 每个能力只实现一次 |
| 复用 | 其他 Service 通过 Shared Domain Engine 复用 |

**引用**：10_1 §2.3, 10_2 §3, 10_3 §3.1

### G-002: One Public API Family

> 同一 Capability 的 Public API 应统一命名前缀。

| Capability | API 前缀 |
|------------|----------|
| Retrieval | `retrieve...` |
| Search | `search...` |
| Browse | `browse...` |
| Projection | `project...` |
| Analytics | `analyze...` |

**引用**：10_3 §4

### G-003: Consumer-Agnostic Interface

> Public interfaces shall remain independent of the assumptions or conventions of any specific client, framework, protocol, or agent implementation.

| 原则 | 说明 |
|------|------|
| 面向能力设计 | 不是面向调用方设计 |
| 协议适配在 Entry | QueryService 定义 Continuation，Entry 决定 Cursor/Page/Streaming |
| 长期稳定 | Public API 尽量不变，内部实现可演进 |

**引用**：10_3 §8, 10_3 §13

### G-004: Stable Public Interface

> Internal complexity should be encapsulated behind stable public interfaces whenever possible.

| 层级 | 稳定性 |
|------|--------|
| Public API | 保守（Conservative）— 长期稳定 |
| Service | 中等 — Use Case 不变 |
| Engine | 开放（Evolvable）— 可持续演进 |
| Repository | 开放 — 随 Schema 演进 |

**引用**：10_3 §3.3

---

## 2. Service Design

### G-005: Service Independence Principle

> Application Services shall not invoke other Application Services synchronously.

| 层级 | 允许 |
|------|------|
| Entry → Service | ✅ |
| Service → Engine | ✅ |
| Service → Service | ❌ |
| Engine → Engine | ✅（保持 DAG） |

**引用**：10_2 §13, 10_3 §7

### G-006: Shared Domain Engine Principle

> Application Services collaborate through shared domain engines rather than direct service invocations whenever feasible.

| 原则 | 说明 |
|------|------|
| 共享 Engine | MemoryEngine、EntityEngine 等 |
| 不共享 Service | Service 之间不互相调用 |
| 通过 Engine 协作 | 需要领域能力时调用 Engine |

**引用**：10_3 §7.2

### G-007: Domain Service 原则

> MemoryService is a Domain Service, not an Application CRUD Service. Public APIs are organized around domain capabilities instead of persistence operations.

| 禁止 | 允许 |
|------|------|
| `create()` / `update()` / `delete()` | `captureMemory()` / `archiveMemory()` |
| `find()` / `get()` | `retrieveById()` / `searchByKeyword()` |
| Repository 风格接口 | Capability 分组接口 |

**引用**：10_2 §2, 10_1 §4.2.1

### G-008: Command / Query Separation

> Command Returns Identity. Query Returns State.

| 操作类型 | 所属 Service | 返回值 |
|----------|-------------|--------|
| Command（写） | MemoryService | `MemoryId` / `JobId` / `Status` |
| Query（读） | QueryService | `Memory` / `MemoryView` / `Context` |

**引用**：10_1 §4.2.2, 10_2 §3.3, 10_3 §2

### G-009: Service Collaboration Matrix

> Every Service specification shall include a Service Collaboration Matrix that explicitly defines allowed dependencies, interaction patterns, and architectural rationale.

| 矩阵列 | 说明 |
|--------|------|
| Caller | 调用方 Service |
| Callee | 被调用方 |
| Allowed | ✅ / ⚠️ / ❌ |
| Interaction Pattern | Sync / Async / Job Dispatch / Event |
| Reason | 架构理由 |

所有 Matrix 合并形成 **Service Dependency Graph**，用于：

* Consistency Review
* Architecture Review
* Implementation Review
* DAG 验证

**引用**：10_1 §7.4, 10_2 §13, 10_3 §11

---

## 3. Engine Design

### G-010: Engine as Domain Capability

> Engine represents Domain Capability. NOT Agent. NOT Service. NOT Repository.

| 属性 | 说明 |
|------|------|
| 无状态 | Stateless |
| 可复用 | Reusable |
| 能力导向 | Capability-based |
| 不访问 Repository | 通过抽象层间接访问 |

**引用**：10_1 §6, 10_2 §6, 10_3 §6

### G-011: Engine Dependency Graph

> Engine 依赖图必须保持 DAG。

| 规则 | 说明 |
|------|------|
| 允许 Engine → Engine | 如 MemoryEngine → EntityEngine |
| 禁止循环 | MemoryEngine → EntityEngine → MemoryEngine |
| Engine 不知道上层 | Engine 不返回 DTO/Transport Model |

**引用**：10_1 §7.2, 10_3 §6.3

### G-012: Engines Produce Domain Knowledge

> Engines shall return domain objects or domain query results rather than transport-layer models.

| 原则 | 说明 |
|------|------|
| Engine 返回 Domain Result | 不包含 REST/JSON/DTO |
| QueryService 负责 Projection | 不同 View（Summary/Detail/Graph）由 QueryService 构建 |
| Entry 负责 DTO 转换 | 协议适配在 Entry 层 |

**引用**：10_3 §6.2

---

## 4. Repository Design

### G-013: Repository Is Persistence Only

> Repository 仅负责持久化。

| 职责 | 禁止 |
|------|------|
| CRUD | 业务逻辑 |
| Query | 调用 Engine |
| Transaction Support | 调用 Service |
| 按 Domain Aggregate 组织 | 互调 |

**引用**：10_1 §5, 10_2 §6.3

### G-014: No Layer Skipping

> 禁止跳过层级直接访问。

| 允许的路径 | 禁止的路径 |
|-----------|-----------|
| Entry → Service → Engine → Repository | Entry → Repository |
| Service → Engine → Repository | Service → Repository |
| Engine → Repository | Engine → Service |

**引用**：10_1 §7.2

---

## 5. Query Design

### G-015: Side-Effect Free Query

> QueryService shall not modify any domain state or persistent data.

| 允许 | 禁止 |
|------|------|
| Read / Search / Filter / Rank | Create / Update / Delete Memory |
| Aggregate / Project / Paginate | Trigger Reflection / Archive |
| Cache Read（基础设施） | Publish Domain Events |

**引用**：10_3 §2.2

### G-016: Query Determinism

> Given the same query conditions and unchanged underlying data, QueryService should produce semantically consistent results.

| 原则 | 说明 |
|------|------|
| 语义一致 | 不是排序完全一致 |
| 数据未变 → 结果一致 | 数据变了 → 结果可变 |
| 允许排序微调 | 只要结果集合一致 |

**引用**：10_3 §10

### G-017: Stable Result Contract

> QueryResult is capability-agnostic and protocol-independent.

| 字段 | 类型 | 说明 |
|------|------|------|
| `result` | DomainResult[] | 领域结果 |
| `metadata` | QueryMetadata | 查询元数据 |
| `continuation` | Continuation | 续传信息 |
| `diagnostics` | Diagnostics (opt) | 诊断信息 |

**引用**：10_3 §9

---

## 6. Review Rules

### G-018: Architecture Review Checklist

每次架构变更应检查：

| 检查项 | 级别 | 参考 Guideline |
|--------|------|----------------|
| Side-Effect Free Query | P0 | G-015 |
| Service → Service 检查 | P0 | G-005 |
| Layer Skipping | P0 | G-014 |
| Engine DAG | P0 | G-011 |
| Service DAG | P0 | G-005 |
| Consumer-Agnostic | P1 | G-003 |
| Stable Result Contract | P1 | G-017 |
| Public API Family | P1 | G-002 |
| Query Planner 存在 | P1 | G-008 |
| Shared Domain Engine | P1 | G-006 |
| Continuation 独立于分页 | P1 | G-003 |
| Projection 归属 QueryService | P1 | G-012 |
| Query Determinism | P2 | G-016 |
| ADR Impact Check | P1 | — |

**引用**：10_3 §12

---

## 7. Evolution Rules

### G-019: Planned vs Potential Evolution

> 区分 Planned Evolution 和 Potential Evolution。不使用 TODO / Future Work / Later。

| 类别 | 说明 | 示例 |
|------|------|------|
| **Planned Evolution** | 已确认的未来演进 | Optimizer 独立、Query Cache |
| **Potential Evolution** | 可能的探索方向 | AI Planner、Cost Estimator |

**引用**：10_3 §13

---

## 3. Reflection & Memory Evolution

### G-020: Memory Pyramid Abstraction by Scope

> Memory Pyramid 层级按解释范围（Scope of Explanation）而非时间抽象。

| 层级 | 解释范围 | 示例 |
|------|----------|------|
| L0 | 历史事实（What Happened?） | 聊天记录、导入文档 |
| L1 | 主题知识（What Does This Topic Mean?） | 单主题总结 |
| L2 | 跨主题模式（What Pattern Does It Reveal?） | 行为模式 |
| L3 | 一般原则（What Principle Explains These Patterns?） | 决策哲学 |

**引用**：10_4 §3.3

### G-021: Higher-level Memory Stores Evolving Explanations

> 高层 Memory 存储当前最佳知识（Current Best Knowledge）。当变化本身具有知识价值时，高层 Memory 应描述演化，而不是保存多个时间快照。

**引用**：10_4 §3.2

### G-022: Reflection Improves Explanatory Power

> Reflection 的目标不是保存快照，而是随着证据不断积累，持续提升高层 Memory 对全部事实的解释能力。Reflection 每次更新时都会问：新的 Memory 能否更好地解释全部 Evidence？

**引用**：10_4 §3.4

### G-023: L0 Protection Principle

> 系统从不自主创建 L0 Memory。任何恢复基线（Recovery Baseline）必须源于用户明确参与的交互或用户预授权，因此始终保持证据基础（Evidence-Based）。

**引用**：10_4 §10.5

### G-024: EntityID Stability

> EntityID 是 Identity 的稳定锚点，永不改变。Entity 的属性（Canonical Name、Alias、Metadata、Relationships、Type）通过积累的证据持续演化。

**引用**：10_5 §3.1

### G-025: Domain Invariants Belong to Engine

> EntityEngine 拥有 ALL 领域不变量（Identity Resolution、Merge Rules、Alias Rules、Relationship Rules、Canonical Name Selection、Entity Consistency）。Service 只执行验证、授权、事务、编排。

**引用**：10_5 §5.3

### G-026: Repository Is Persistence Only

> EntityRepository 保持持久化层边界。不执行 merge 决策、alias 冲突决策、relationship 验证。Repository 仅返回 Domain Objects，Never Projection, Never DTO。

**引用**：10_5 §6

### G-027: Asynchronous Reference Migration

> Entity Merge 采用异步 Reference Migration。Merge 后发布 Domain Event，Task Runtime 异步执行 Reference Migration / Relationship Update / Index Rebuild。Query 路径保持简单。

**引用**：10_5 §7

### G-028: Lifecycle Represents Objective State Transitions

> Entity Lifecycle 表示客观状态转换（Created → Active → Merged）。语义演化通过证据驱动的属性更新表示，不是生命周期状态。

**引用**：10_5 §8.3

### G-029: Domain Events Publish Facts Only

> Domain Events 代表已完成的业务事实，从不执行业务逻辑。异步处理属于 Task Runtime。EntityService 在成功提交后发布事件。

**引用**：10_5 §9.2

### G-030: Services May Orchestrate Multiple Domain Engines

> A Service 可编排多个 Domain Engine。例如 MemoryService 可编排 EntityEngine + MemoryEngine。跨服务同步调用仍然禁止。

**引用**：10_5 §10.3

### G-031: Identity Modification Belongs Exclusively to EntityService

> 只有 EntityService 可执行身份修改（Create / Merge / Rename / Alias / Relationship）。ReflectionService 可推断身份演化，但不可执行。

**引用**：10_5 §10.2

### G-032: Every Entity Must Be L0-Supported

> 每个 Entity 最终必须由至少一条 L0 Memory 支持。手动创建 Entity 是允许的，因为创建交互本身产生 L0 Memory。

**引用**：10_5 §11.2

### G-033: No Entity Version

> 不引入 Entity 版本。Entity 历史已通过 L0 Memory、Evidence Chain、Domain Events、Audit 自然存在。历史重建应始终依赖证据，而非重复的版本表。

**引用**：10_5 §11.4

### G-034: Task Runtime Performs Asynchronous Maintenance

> 后台维护（Reference Migration / Graph Maintenance / Index Rebuild / Cache Refresh / Audit）属于 Task Runtime 职责。EntityService 从不等待后台维护完成。

**引用**：10_5 §9.3

### G-035: No Runtime Canonical Resolution

> Merge 是低频率操作，Query 是高频率操作。不要在每次查询时做 Canonical Resolution。Merge 后通过异步 Reference Migration 更新索引。

**引用**：10_5 §7.1

### G-036: Entity Is Current Best Identity

> Entity 始终代表 Current Best Identity。没有 Candidate 生命周期，没有验证工作流。

**引用**：10_5 §3.1

### G-037: Memory Fact ≠ Entity Reference

> Entity Merge 更新引用，不修改 L0 事实。Reference Migration 是 Index Maintenance，不是历史修改。

**引用**：10_5 §3.4

### G-038: Planned vs Potential Evolution

> 区分 Planned Evolution 和 Potential Evolution。不使用 TODO / Future Work / Later。

**引用**：10_3

---

| 编号 | 名称 | 首次出现 |
|------|------|----------|
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
| G-020 | Memory Pyramid Abstraction by Scope | 10_4 |
| G-021 | Higher-level Memory Stores Evolving Explanations | 10_4 |
| G-022 | Reflection Improves Explanatory Power | 10_4 |
| G-023 | L0 Protection Principle | 10_4 |
| G-024 | EntityID Stability | 10_5 |
| G-025 | Domain Invariants Belong to Engine | 10_5 |
| G-026 | Repository Is Persistence Only (Entity) | 10_5 |
| G-027 | Asynchronous Reference Migration | 10_5 |
| G-028 | Lifecycle Represents Objective State Transitions | 10_5 |
| G-029 | Domain Events Publish Facts Only | 10_5 |
| G-030 | Services May Orchestrate Multiple Domain Engines | 10_5 |
| G-031 | Identity Modification Belongs Exclusively to EntityService | 10_5 |
| G-032 | Every Entity Must Be L0-Supported | 10_5 |
| G-033 | No Entity Version | 10_5 |
| G-034 | Task Runtime Performs Asynchronous Maintenance | 10_5 |
| G-035 | No Runtime Canonical Resolution | 10_5 |
| G-036 | Entity Is Current Best Identity | 10_5 |
| G-037 | Memory Fact ≠ Entity Reference | 10_5 |
| G-038 | Planned vs Potential Evolution | 10_3 |
| G-039 | Task Runtime Is Infrastructure | 10_6 |
| G-040 | Task Runtime Domain Agnostic | 10_6 |
| G-041 | Task Chaining via Events | 10_6 |
| G-042 | Retry vs Re-trigger | 10_6 |
| G-043 | Task Idempotency | 10_6 |
| G-044 | Operational Interface Principle | 10_6 |
| G-045 | Scheduler Is Unified Task Dispatcher | 10_6 |
| G-046 | Recovery Never Re-evaluates | 10_6 |
| G-047 | Maintenance Manager Scope | 10_6 |
| G-048 | Observability Layering | 10_6 |
|| G-049 | Infrastructure Isolation | 10_6 |
|| G-050 | API Entry Layer 职责 | 10_7 |
|| G-051 | Capability Discovery | 10_7 |
|| G-052 | Multi-Adapter Entry | 10_7 |
|| G-053 | Entry Validation Layers | 10_7 |
|| G-054 | DTO Transformation | 10_7 |
|| G-055 | Memory Immutability at Entry | 10_7 |

---

## 附录：Task Runtime Guidelines

### G-039: Task Runtime Is Infrastructure

> Task Runtime 是通用基础设施层，不是业务逻辑。Task Runtime 不理解 Memory、Entity、Reflection 等业务概念。

**引用**：10_6 §2

### G-040: Task Runtime Domain Agnostic

> Task Runtime 操作 exclusively on generic Task abstraction。Payload 属于 Task 实现，Runtime 从不解析 Payload。

**引用**：10_6 §3

### G-041: Task Chaining via Events

> Task 从不直接创建另一个 Task。Task Chaining 通过 Domain Event → Event Dispatcher → Task Registry → Task Factory → New Task 实现。

**引用**：10_6 §4

### G-042: Retry vs Re-trigger

> Retry = 同一 Task 的技术恢复（Runtime 责任）。Re-trigger = 新 Task 的业务决策（Service 责任）。

**引用**：10_6 §5.4

### G-043: Task Idempotency

> Task Runtime 提供 At-Least-Once 执行保证。每个 Task 实现应该是幂等的。

**引用**：10_6 §6

### G-044: Operational Interface Principle

> Task Runtime 仅暴露操作接口（submit/getTask/queryRuntimeStatus/retry）。不暴露业务接口。

**引用**：10_6 §12

### G-045: Scheduler Is Unified Task Dispatcher

> Scheduler 不是 Cron。Scheduler 是统一的 Task 分发协调器，支持 Domain Event / Cron / Startup Recovery / User Async Request 四种触发源。

**引用**：10_6 §7

### G-046: Recovery Never Re-evaluates Business Logic

> Startup Recovery 只恢复执行，不重新评估业务逻辑。依靠 Task 幂等性保证安全。

**引用**：10_6 §9.4

### G-047: Maintenance Manager Scope

> Maintenance Manager 仅负责 Runtime 维护（Task Cleanup / Lock Cleanup / Statistics / Health / Log Retention）。业务维护属于 Service 层。

**引用**：10_6 §10

### G-048: Observability Layering

> Runtime Metadata / Logging / Metrics / Dashboard 是分层独立的。Dashboard 是消费者，不是 Runtime 的一部分。

**引用**：10_6 §13

### G-049: Infrastructure Isolation

> Task Runtime 与业务逻辑完全隔离。基础设施关注执行，Service 关注业务。

**引用**：10_6 §15.1

---

## 附录：API Entry Layer Guidelines

### G-050: API Entry Layer 职责

> API Entry Layer 负责协议适配、DTO 转换、认证、能力检查。Entry 层不包含业务逻辑。业务逻辑属于 Service 层。

**引用**：10_7 §2

### G-051: Capability Discovery

> 外部调用者通过 Capability 交互，不直接面对 Service。Capability 是稳定的，Service 是内部实现细节。

**引用**：10_7 §3

### G-052: Multi-Adapter Entry

> REST / MCP / CLI / SDK / Agent 等多种 Entry 适配器共享同一能力接口。新增适配器不修改 Service 层。

**引用**：10_7 §5

### G-053: Entry Validation Layers

> 请求验证分三层：协议验证（Entry）→ 能力验证（Entry）→ 领域验证（Service）。每一层拒绝不符合其职责范围的请求。

**引用**：10_7 §7

### G-054: DTO Transformation

> Entry 层负责协议特定的 DTO 与内部 Domain Command 之间的转换。内部模型不得泄漏到外部响应。

**引用**：10_7 §8

### G-055: Memory Immutability at Entry

> Entry 层拒绝所有直接修改 Memory 的请求（update/delete）。修正通过 correctMemory() 完成，归档通过 archiveMemory() 完成。

**引用**：10_7 §4, 08 §8.3

*本文档是 Living Guideline，随 Phase B 推进持续更新。*

*后续 10_4~10_N 每完成一个文档，同步更新本文档。*
