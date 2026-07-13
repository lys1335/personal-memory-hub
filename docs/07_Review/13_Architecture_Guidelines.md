|# Personal AI Memory Hub — 13 Architecture Guidelines

> **版本**: 1.5  
> **日期**: 2026-07-10  
> **阶段**: Phase B — 工程规范（Living Guideline）  
> **状态**: 已确认  
> **说明**: 本文档是项目的规范中心（Normative Reference），后续 10_x 文档持续更新。当前包含 G-001~G-064 + G-065~G-112 + G-113~G-118 (Documentation Governance) + Error Taxonomy V1。

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

---

## 9. Reflection & Task Architecture

### G-038: Service Independence Principle

> Services are peer-layer business orchestrators. Services shall not invoke other Services.

ReflectionService 不调用 MemoryService、QueryService、EntityService、TaskService。
共享功能通过共享 Repository 契约、共享 Aggregate 模型、共享 Domain 不变量实现。

**引用**：10_4 §14.1

### G-039: Capability Completeness Principle

> Each Service owns the complete lifecycle required to fulfill its business capability, including persistence required to complete that capability.

MemoryService 不是通用的 Memory 写入网关。Reflection 生成的 Memory 持久化属于 Reflection 能力。

**引用**：10_4 §14.2

### G-040: Shared Aggregate Principle

> Multiple Services may coordinate the same Aggregate while maintaining identical domain invariants and Repository contracts.

MemoryService 与 ReflectionService 共享 Memory Aggregate，但各自拥有不同的工作流所有权。

**引用**：10_4 §14.3

### G-041: Deferred Execution Principle

> Task represents deferred execution rather than deferred business logic.

TaskService 拥有任务生命周期。Task Runtime 拥有执行调度。Reflection 工作流保持在 ReflectionService 内部。

**引用**：10_4 §14.4

### G-042: Execution Context Transparency Principle

> Immediate execution and background execution shall produce identical business behavior.

后台执行只改变执行上下文，不改变工作流、验证、领域规则、错误映射。

**引用**：10_4 §14.5

### G-043: Enhancement Isolation Principle

> Enhancement capabilities fail independently and shall never invalidate committed business results.

Reflection 失败保持局部。重试必须是安全的。每个增强能力独立失败。

**引用**：10_4 §14.7

---

## EntityService D3.5 Guidelines

### G-044: Entity Permanence Principle

> **Entity is never deleted. No Delete. No Destroy. No Restore. Entity permanently exists after creation.**

Entity 一旦创建即永久存在。不存在删除、销毁或恢复操作。

**引用**：10_5 §8.1

### G-045: Identity Consolidation Principle

> **Merge is redefined as Identity Consolidation. Merge does NOT represent real-world evolution. Rename is Metadata Update.**

Identity Consolidation 是身份层面的合并，不代表真实世界的演化。Rename 只是 Metadata Update。

**引用**：10_5 §7.1

### G-046: Metadata Update Principle

> **Metadata includes Canonical Name, Alias List, and other metadata. Rename only changes Metadata.**

元数据包括 Canonical Name、Alias List 和其他元数据。Rename 只更改元数据，不改变 Entity 身份。

**引用**：10_5 §7.2

### G-047: Memory Reference Immutability Principle

> **Memory references are immutable. Memory always keeps its original Entity reference. Entity Merge never rewrites historical Memory references.**

Memory 引用不可变。Memory 始终保持其原始 Entity 引用。Entity Merge 从不重写历史 Memory 引用。

**引用**：10_5 §3.4

### G-048: QueryService Resolution Principle

> **QueryService performs Alias Resolution, Canonical Resolution, and Merge Graph Expansion. Memory remains unchanged.**

QueryService 执行 Alias Resolution、Canonical Resolution 和 Merge Graph Expansion。Memory 保持不变。

**引用**：10_5 §3.5

### G-049: Relationship Evolution Principle

> **Relationship belongs to the current Identity Graph. Relationship may evolve together with Entity. Memory references never evolve.**

Relationship 属于当前 Identity Graph。Relationship 可能与 Entity 一起演化。Memory 引用永不演化。

**引用**：10_5 §3.6

### G-050: Reflection Proposal Principle

> **ReflectionService only produces Entity Evolution Proposals. Reflection never mutates Entity directly.**

ReflectionService 仅产生 Entity Evolution Proposals。Reflection 从不直接修改 Entity。

**引用**：10_4 §14.6

### G-051: Proposal–Task Separation Principle

> **Proposal and Task are independent concepts. Proposal = Business Recommendation. Task = Execution Scheduling.**

Proposal 和 Task 是独立概念。Proposal = 业务建议。Task = 执行调度。

**引用**：10_4 §14.6, 10_5 §11.6

### G-052: Entity Transaction Scope Principle

> **Entity transactions only modify Entity, Metadata, and Relationship Graph. Never Observation, Memory, or Evidence.**

Entity 事务仅修改 Entity、Metadata 和 Relationship Graph。绝不修改 Observation、Memory 或 Evidence。

**引用**：10_5 §11.5

---

## TaskService D3.6 Guidelines


### G-053: Execution Scope Immutability Principle

> **Execution Scope is immutable during execution. Retry must preserve Execution Scope. Immediate and delayed execution use identical Execution Scope. Execution timing may change. Execution Scope never changes.**

**引用**：10_6 §2.4

### G-054: Scheduling Determines When, Not What

> **Scheduling determines when execution occurs. Scheduling never determines what execution occurs. Scheduler never owns business logic, never evaluates memory/entities/proposals.**

**引用**：10_6 §7.2

### G-055: Periodic Creates New Tasks

> **Periodic execution should create new Tasks rather than endlessly recycling the same Task.**

**引用**：10_6 §7.4

### G-056: Retry Preserves Scope

> **Retry retries execution, never retries business decision. Retry preserves Execution Context, Execution Scope, and Business Intent. Only changes Attempt Number, Retry Metadata, and Retry Schedule.**

**引用**：10_6 §9.1

### G-057: Business Services Ensure Semantic Idempotency

> **TaskService never guarantees business idempotency. Business Services remain responsible for semantic idempotency.**

**引用**：10_6 §9.1

### G-058: Incremental Processing

> **Each immutable Observation should enter processing pipeline only once. Summary processes only newly produced Observations. Existing Memory evolves through Reflection.**

**引用**：10_6 §15.4

### G-059: MemoryService Execution-Agnostic

> **MemoryService owns memory semantics, not execution semantics. MemoryService does not create Tasks. Summary belongs to MemoryService. TaskService only executes Summary capability.**

**引用**：10_6 §14.2

### G-060: EntityService Execution-Agnostic

> **EntityService owns identity semantics, not execution semantics. Entity Merge affects future processing only. Completed execution is never modified. Entity evolution creates new Tasks through Trigger Evaluation.**

**引用**：10_6 §14.3

### G-061: One Task One Transaction

> **One Task corresponds to one business capability. One Task corresponds to one business transaction. No cross-service transaction. Business transaction and Task state transaction remain independent.**

**引用**：10_6 §15.2

### G-062: Failure Isolation

> **Execution failure never invalidates committed business state. Business Failure → Terminal. Execution Failure → Retry. Enhancement Failure → Independent retry.**

**引用**：10_6 §15.3

### G-063: Completed Task Immutability

> **Completed Tasks are immutable execution history. Completed Tasks are never reopened. Completed Tasks never return to Pending/Running/Retry Waiting. Business evolution always creates a new Task.**

**引用**：10_6 §15.4

### G-064: Error Mapping Reuses Taxonomy

> **Business Services define business errors. TaskService classifies execution results. Reuse existing Error Taxonomy. Retry decision based on error category. Preserve original business error for auditability.**

**引用**：10_6 §15.5
---

| 编号 | 名称 | 首次出现 |
|------|------|----------|
| G-001 | One Capability, One Implementation | 13 §1 |
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
| G-044 | Entity Permanence Principle | 10_5 |
| G-045 | Identity Consolidation Principle | 10_5 |
| G-046 | Metadata Update Principle | 10_5 |
| G-047 | Memory Reference Immutability Principle | 10_5 |
| G-048 | QueryService Resolution Principle | 10_5 |
| G-049 | Relationship Evolution Principle | 10_5 |
| G-050 | Reflection Proposal Principle | 10_4 |
| G-051 | Proposal–Task Separation Principle | 10_4 |
| G-052 | Entity Transaction Scope Principle | 10_5 |
| G-053 | Execution Scope Immutability Principle | 10_6 |
| G-054 | Scheduling Determines When, Not What | 10_6 |
| G-055 | Periodic Creates New Tasks | 10_6 |
| G-056 | Retry Preserves Scope | 10_6 |
| G-057 | Business Services Ensure Semantic Idempotency | 10_6 |
| G-058 | Incremental Processing | 10_6 |
| G-059 | MemoryService Execution-Agnostic | 10_6 |
| G-060 | EntityService Execution-Agnostic | 10_6 |
| G-061 | One Task One Transaction | 10_6 |
| G-062 | Failure Isolation | 10_6 |
| G-063 | Completed Task Immutability | 10_6 |
| G-064 | Error Mapping Reuses Taxonomy | 10_6 |
| G-038 | Service Independence Principle | 13 |
| G-039 | Capability Completeness Principle | 13 |
| G-040 | Shared Aggregate Principle | 13 |
| G-041 | Deferred Execution Principle | 13 |
| G-042 | Execution Context Transparency Principle | 13 |
| G-043 | Enhancement Isolation Principle | 13 |
| G-054 | Task Runtime Is Infrastructure | 10_6 |
| G-055 | Task Runtime Domain Agnostic | 10_6 |
| G-056 | Task Chaining via Events | 10_6 |
| G-057 | Retry vs Re-trigger | 10_6 |
| G-058 | Task Idempotency | 10_6 |
| G-059 | Operational Interface Principle | 10_6 |
| G-060 | Scheduler Is Unified Task Dispatcher | 10_6 |
| G-061 | Recovery Never Re-evaluates | 10_6 |
| G-062 | Maintenance Manager Scope | 10_6 |
| G-063 | Observability Layering | 10_6 |
| G-064 | Infrastructure Isolation | 10_6 |
| G-065 | API Entry Layer 职责 | 10_7 |
| G-066 | Capability Discovery | 10_7 |
| G-067 | Multi-Adapter Entry | 10_7 |
| G-068 | Entry Validation Layers | 10_7 |
| G-069 | DTO Transformation | 10_7 |
| G-070 | Memory Immutability at Entry | 10_7 |
| G-071 | Testing Mirrors Architecture | 10_8 |
| G-072 | Mock Mirrors Layer Boundary | 10_8 |
| G-073 | Deterministic-by-Default | 10_8 |
| G-074 | Semantic Equivalence Principle | 10_8 |
| G-075 | Regression as Executable Memory | 10_8 |
| G-076 | Golden Dataset Principle | 10_8 |
| G-077 | Testability Is an Architectural Requirement | 10_8 |
| G-078 | Quality Is Designed, Not Inspected | 10_8 |
| G-079 | Tests Generated from Design | 10_8 |
| G-080 | Test Data Is a First-Class Artifact | 10_8 |
| G-081 | DTO Is a Service Contract | D3.7 |
| G-082 | DTO Contains Data Only | D3.7 |
| G-083 | All DTOs Are Immutable | D3.7 |
| G-084 | One Capability Owns One Primary Contract | D3.7 |
| G-085 | Command/Query Naming Convention | D3.7 |
| G-086 | Query Purity Principle | 10_3 |
| G-087 | Capability Composition Principle | 10_3 |
| G-088 | Query Idempotence Principle | 10_3 |
| G-089 | Language Preservation Principle | 10_3 |
| G-090 | Observational Consistency | 10_3 |
| G-091 | Repository Coordination Uniqueness | 10_3 |
| G-092 | Read Pipeline Principles | 10_3 |
| G-093 | Projection Three-Level Boundary | 10_3 |
| G-094 | Transaction Strategy | 10_3 |
| G-095 | Deterministic Error Mapping | 10_3 |
| G-096 | Dual Result Principle | D3.7 |
| G-097 | Error Is Part of Service Contract | D3.7 |
| G-098 | Exceptions Never Cross Service Boundary | D3.7 |
| G-099 | Service Owns Exception Mapping | D3.7 |
| G-100 | Validation Layer Ownership | D3.7 |
| G-101 | Business Validation Completes Before Transaction | D3.7 |
| G-102 | Capability-Owned DTOs | D3.7 |
| G-103 | Shared Objects Are Capability-Neutral | D3.7 |
| G-104 | Backward-Compatible Evolution | D3.7 |
| G-105 | Breaking Changes Require ADR | D3.7 |
| G-106 | Serialization Belongs to Entry Layer | D3.7 |
| G-107 | Protocol Version ≠ Service Contract Version | D3.7 |

---

## 附录：API Entry Layer Guidelines

### G-065: API Entry Layer 职责

> API Entry Layer 负责协议适配、DTO 转换、认证、能力检查。Entry 层不包含业务逻辑。业务逻辑属于 Service 层。

**引用**：10_7 §2

### G-066: Capability Discovery

> 外部调用者通过 Capability 交互，不直接面对 Service。Capability 是稳定的，Service 是内部实现细节。

**引用**：10_7 §3

### G-067: Multi-Adapter Entry

> REST / MCP / CLI / SDK / Agent 等多种 Entry 适配器共享同一能力接口。新增适配器不修改 Service 层。

**引用**：10_7 §5

### G-068: Entry Validation Layers

> 请求验证分三层：协议验证（Entry）→ 能力验证（Entry）→ 领域验证（Service）。每一层拒绝不符合其职责范围的请求。

**引用**：10_7 §7

### G-069: DTO Transformation

> Entry 层负责协议特定的 DTO 与内部 Domain Command 之间的转换。内部模型不得泄漏到外部响应。

**引用**：10_7 §8

### G-070: Memory Immutability at Entry

> Entry 层拒绝所有直接修改 Memory 的请求（update/delete）。修正通过 correctMemory() 完成，归档通过 archiveMemory() 完成。

**引用**：10_7 §4, 08 §8.3

---

## 7. DTO & Service Contract Guidelines

### G-081: DTO Is a Service Contract

> DTO is a Service Contract, not a Domain Object. DTO contains data only — no business logic, no workflow, no persistence logic, no validation logic, no infrastructure references.

**引用**：D3.7 §2

### G-082: DTO Contains Data Only

> DTOs are independent from Repository, Engine, Database, ORM, and Transport Protocol. DTO lifecycle exists only at the Service Boundary.

**引用**：D3.7 §2

### G-083: All DTOs Are Immutable

> All DTO fields are final/readonly. No setters. DTOs contain serializable data fields only.

**引用**：D3.7 §2.2

### G-084: One Capability Owns One Primary Contract

> Each Capability defines and owns its own DTOs. Business DTOs are never shared across Services.

**引用**：D3.7 §2.1, §11.1

### G-085: Command/Query Naming Convention

> Commands follow `XXXCommand`, Queries follow `XXXQuery`, Results follow `XXXResult` naming convention.

**引用**：D3.7 §3.3

---

## 8. QueryService Guidelines

### G-086: Query Purity Principle

> QueryService shall not produce any business side effects other than allowed infrastructure behaviors.

**禁止的隐藏命令**：

| 禁止 | 原因 |
|------|------|
| Automatic Reflection | 属于 ReflectionService |
| Automatic Embedding Generation | 属于 Engine/Task Runtime |
| Automatic Index Rebuilding | 属于 Task Runtime |
| Automatic Repairs | 属于 EntityService/Task Runtime |

所有上述操作必须通过显式 Command 或 Task 执行。

**引用**：10_3 §2.3

### G-087: Capability Composition Principle

> Public Query capabilities may internally compose other Query capabilities. Composition remains inside QueryService.

| 规则 | 说明 |
|------|------|
| QueryService 内部组合 | Retrieval 可组合 Search + Projection |
| 禁止跨层编排 | Entry/Repository/Engine 不编排能力组合 |
| 组合结果仍为 Query | 不引入写操作 |

**引用**：10_3 §3

### G-088: Query Idempotence Principle

> The same query executed against the same persisted state shall always produce the same business result.

| 约束 | 说明 |
|------|------|
| 相同查询 + 相同状态 = 相同结果 | 基本保证 |
| 不要求逐字节一致 | 允许非确定性基础设施行为 |
| 要求业务语义一致 | 核心业务结果必须一致 |
| 不修改持久化状态 | 幂等的前提 |

**引用**：10_3 §9

### G-089: Language Preservation Principle

> Preserve original language. Cross-language retrieval relies on embeddings rather than translating stored memory into a canonical language.

| 原则 | 说明 |
|------|------|
| 不翻译存储内容 | Memory 以原始语言存储和检索 |
| 嵌入是跨语言桥梁 | 多语言嵌入模型处理语义匹配 |
| QueryService 语言中立 | 不对语言做任何假设或转换 |

**引用**：10_3 §12

### G-090: Observational Consistency

> Query results reflect the persisted business state at query time. QueryService must not alter the observed business state during query execution.

QueryService 的职责是观察（Observe）和组织（Orchestrate），而不是影响（Influence）业务状态。

**引用**：10_3 §2.4

### G-091: Repository Coordination Uniqueness

> QueryService is the only repository coordinator.

| 规则 | 说明 |
|------|------|
| Repository 不互调 | Repositories never coordinate each other |
| Repository 不知道彼此 | Repositories never know each other |
| Repository 不组装跨聚合结果 | Repositories never assemble cross-aggregate results |
| Repository 组合由 Planning 决定 | Query Planning determines combinations |

**引用**：10_3 §7

### G-092: Read Pipeline Principles

> All read operations follow a single, forward-only pipeline with immutable intermediate results.

| 原则 | 说明 |
|------|------|
| Single Read Flow | 所有读操作走同一条 Pipeline |
| Forward-Only | Pipeline 单向执行，不回退、不循环 |
| Immutable Intermediate Results | 每个阶段输出不可变 |
| Stateless Execution | Pipeline 不保留跨请求状态 |
| 差异仅在三处 | Planning、Repository Coordination、Domain Processing |

**引用**：10_3 §6

### G-093: Projection Three-Level Boundary

> Domain Model → Domain View → Entry DTO

| 层级 | 职责 |
|------|------|
| Domain Model | Engine 返回的最完整领域对象 |
| Domain View | QueryService 投影后的语义变换结果 |
| Entry DTO | Entry 层协议适配后的传输对象 |

**投影约束**：仅变换表示、不改变语义、确定性、无状态、无副作用。

**引用**：10_3 §4.4

### G-094: Transaction Strategy

> Read-Only Transaction. Transaction owned by QueryService.

| 规则 | 说明 |
|------|------|
| 事务由 QueryService 拥有 | QueryService 负责 begin/commit/rollback |
| Repository 不拥有事务 | Repositories 是事务中性的 |
| 一致的单一业务快照 | 事务确保整个查询看到一致的数据 |
| 无长运行读事务 | 事务在单次查询执行期间完成 |
| Streaming 是交付策略 | 不是事务策略 |

**引用**：10_3 §10

### G-095: Deterministic Error Mapping

> Repository errors are deterministically translated into Service errors. Empty search results are not errors.

| 层级 | 错误类型 |
|------|----------|
| Repository | `RepositoryError` |
| QueryService | `ServiceError` (业务导向) |
| Entry | `EntrySafeError` |

部分故障恢复属于 D4 QueryEngine，不属于 D3 Service。

**引用**：10_3 §11

### G-096: Dual Result Principle

> Business Result represents Domain Outcome. Execution Result represents Runtime Outcome. Business Success ≠ Execution Success. TaskService returns Execution Result. Domain Services return Business Result. Execution information must never pollute Business Contracts.

**引用**：D3.7 §7

### G-097: Error Is Part of Service Contract

> Error represents failure to produce Business Result. Error is transport-independent, language-independent, and expresses stable business semantics. Error is immutable and may include business context. Error never contains recovery logic.

**引用**：D3.7 §8

### G-098: Exceptions Never Cross Service Boundary

> Service boundary converts exceptions to Errors. Service owns exception mapping. Mapping is semantic rather than implementation-based. Infrastructure details are hidden. Unknown exceptions always map to a known Business Error.

**引用**：D3.7 §9

### G-099: Service Owns Exception Mapping

> Exception categories map to frozen Error categories. Internal diagnostic chains may be preserved for logging. Mapping is deterministic. Protocol mapping occurs only in Entry Layer.

**引用**：D3.7 §9

### G-100: Validation Layer Ownership

> Protocol Validation (Entry) → Business Validation (Service) → Persistence Validation (Repository) → Infrastructure Validation (Infrastructure). Each layer validates within its responsibility scope.

**引用**：D3.7 §10.2

### G-101: Business Validation Completes Before Transaction

> Service owns Business Validation. Validation occurs before Business Execution. Validation produces Validation Error. Validation is deterministic, side-effect free, capability-oriented, and transport-independent.

**引用**：D3.7 §10.1

### G-102: Capability-Owned DTOs

> Capability owns its own DTO. Business DTOs are never shared across Services. Only stable Shared Value Objects may be shared. Reuse semantic components rather than complete DTOs.

**引用**：D3.7 §11

### G-103: Shared Objects Are Capability-Neutral

> Shared contracts belong to an independent Shared Contract layer. Shared contracts evolve independently. Shared DTOs must remain capability-neutral. Business DTOs must never become shared contracts.

**引用**：D3.7 §11

### G-104: Backward-Compatible Evolution

> Service Contracts are stable public contracts. Prefer backward-compatible evolution. Capability contracts evolve independently. Infrastructure changes never affect Service Contracts.

**引用**：D3.7 §12

### G-105: Breaking Changes Require ADR

> Semantic stability is more important than structural stability. Error Codes remain stable. Versioning follows Business Capability evolution. Deprecation precedes removal.

**引用**：D3.7 §12

### G-106: Serialization Belongs to Entry Layer

> DTO is the serialization boundary. Serialization is protocol-specific. DTO must remain serialization-friendly. Serialization never changes business semantics. Domain Objects never cross serialization boundaries.

**引用**：D3.7 §13

### G-107: Protocol Version ≠ Service Contract Version

> Protocol changes (HTTP/1.1 → HTTP/2, JSON → MessagePack) do not affect Service Contract Version. Service Contract changes require ADR. Infrastructure changes never affect Service Contracts.

**引用**：D3.7 §13.3

---

## 附录：Service Contract Guidelines

### G-108: Shared Objects Are Capability-Neutral

> Shared contracts belong to an independent Shared Contract layer. Shared contracts evolve independently. Shared DTOs must remain capability-neutral. Business DTOs must never become shared contracts.

**引用**：D3.7 §11

### G-109: Backward-Compatible Evolution

> Service Contracts are stable public contracts. Prefer backward-compatible evolution. Capability contracts evolve independently. Infrastructure changes never affect Service Contracts.

**引用**：D3.7 §12

### G-110: Breaking Changes Require ADR

> Semantic stability is more important than structural stability. Error Codes remain stable. Versioning follows Business Capability evolution. Deprecation precedes removal.

**引用**：D3.7 §12

### G-111: Serialization Belongs to Entry Layer

> DTO is the serialization boundary. Serialization is protocol-specific. DTO must remain serialization-friendly. Serialization never changes business semantics. Domain Objects never cross serialization boundaries.

**引用**：D3.7 §13

### G-112: Protocol Version ≠ Service Contract Version

> Protocol changes (HTTP/1.1 → HTTP/2, JSON → MessagePack) do not affect Service Contract Version. Service Contract changes require ADR. Infrastructure changes never affect Service Contracts.

**引用**：D3.7 §13.3

---

## 附录：Testing Guidelines

### G-071: Testing Mirrors Architecture

> 测试结构镜像五层架构：Entry / Service / Engine / Repository / Integration。每层有明确的测试范围和边界。

**引用**：10_8 §3

### G-072: Mock Mirrors Layer Boundary

> Mock 仅存在于层边界。禁止在同层内 Mock。禁止 Mock 当前测试对象自身。优先使用真实对象而非 Mock。

**引用**：10_8 §4

### G-073: Deterministic-by-Default

> 所有单元测试和集成测试必须是确定性的。CI 门仅依赖确定性测试。LLM 评估测试为非阻塞信号。

**引用**：10_8 §5

### G-074: Semantic Equivalence Principle

> 测试验证语义等价（含义、状态、行为），而非字面字符串匹配。特别是 LLM 生成内容的验证。

**引用**：10_8 §2.1 (P18)

### G-075: Regression as Executable Memory

> 回归测试是可执行的项目记忆。每个 Bug Fix 必须新增回归测试。回归保护 Contract，不保护实现细节。

**引用**：10_8 §7

### G-076: Golden Dataset Principle

> Golden Dataset 定义已知输入的期望输出，是回归测试的真相标准。Golden Dataset 随设计变更而更新，不随实现变更而更新。

**引用**：10_8 §6.4

### G-077: Testability Is an Architectural Requirement

> 如果一个组件无法在隔离状态下测试，其架构是有缺陷的。可测试性驱动设计决策。

**引用**：10_8 §8.1

### G-078: Quality Is Designed, Not Inspected

> 质量来自良好的架构、清晰的契约和确定性设计。测试验证质量，不创造质量。

**引用**：10_8 §8.4

### G-079: Tests Generated from Design

> 测试用例从设计文档生成，而非从代码审查生成。测试用例是设计资产，不是代码附属品。

**引用**：10_8 §2.1 (P9, P10)

### G-080: Test Data Is a First-Class Artifact

> 测试数据（Fixtures、Scenarios、Golden Datasets）是版本控制的一等公民，与源代码同等审查标准。

**引用**：10_8 §6

---

| 编号 | 名称 | 首次出现 |
|------|------|----------|
| G-071 | Testing Mirrors Architecture | 10_8 |
| G-072 | Mock Mirrors Layer Boundary | 10_8 |
| G-073 | Deterministic-by-Default | 10_8 |
| G-074 | Semantic Equivalence Principle | 10_8 |
| G-075 | Regression as Executable Memory | 10_8 |
| G-076 | Golden Dataset Principle | 10_8 |
| G-077 | Testability Is an Architectural Requirement | 10_8 |
| G-078 | Quality Is Designed, Not Inspected | 10_8 |
| G-079 | Tests Generated from Design | 10_8 |
| G-080 | Test Data Is a First-Class Artifact | 10_8 |
| G-081 | DTO Is a Service Contract | D3.7 |
| G-082 | DTO Contains Data Only | D3.7 |
| G-083 | All DTOs Are Immutable | D3.7 |
| G-084 | One Capability Owns One Primary Contract | D3.7 |
| G-085 | Command/Query Naming Convention | D3.7 |
| G-086 | Knowledge Evolution Principle | 12 |
| G-087 | Stateless AI Collaboration | 13_AI_Development_Workflow |
| G-088 | Evidence-Based Verification | 13_AI_Development_Workflow |
| G-089 | GitHub as Project State | 13_AI_Development_Workflow |
| G-090 | Knowledge Refinement Over Proliferation | 13_AI_Development_Workflow |
| G-091 | Query Purity Principle | 10_3 |
| G-092 | Capability Composition Principle | 10_3 |
| G-093 | Query Idempotence Principle | 10_3 |
| G-094 | Language Preservation Principle | 10_3 |
| G-095 | Observational Consistency | 10_3 |
| G-096 | Repository Coordination Uniqueness | 10_3 |
| G-097 | Read Pipeline Principles | 10_3 |
| G-098 | Projection Three-Level Boundary | 10_3 |
| G-099 | Transaction Strategy | 10_3 |
| G-100 | Validation Layer Ownership | D3.7 |
| G-101 | Business Validation Completes Before Transaction | D3.7 |
| G-102 | Capability-Owned DTOs | D3.7 |
| G-103 | Shared Objects Are Capability-Neutral | D3.7 |
| G-104 | Backward-Compatible Evolution | D3.7 |
| G-105 | Breaking Changes Require ADR | D3.7 |
| G-106 | Serialization Belongs to Entry Layer | D3.7 |
| G-107 | Protocol Version ≠ Service Contract Version | D3.7 |
| G-113 | GitHub is Single Source of Truth | D3.9 |
| G-114 | Documentation Never Changes Architecture | D3.9 |
| G-115 | Synchronize Before Enhancement | D3.9 |
| G-116 | Traceability First | D3.9 |
| G-117 | Consistency Over Completeness | D3.9 |
| G-118 | Frozen Documents Protected | D3.9 |

---

## Documentation Governance Guidelines

### G-113: GitHub is Single Source of Truth

> GitHub HEAD is the authoritative representation of project state. All documentation must reflect what is on GitHub, not conversation history, AI memory, or informal notes.

**引用**：D3.9 §2.1

### G-114: Documentation Never Changes Architecture

> Documentation updates are governance, not design. They synchronize text, fix references, unify terminology. They never modify architecture.

**引用**：D3.9 §2.2

### G-115: Synchronize Before Enhancement

> Synchronize existing documentation before adding new content. A consistent baseline is more valuable than an extensive but inconsistent one.

**引用**：D3.9 §2.3

### G-116: Traceability First

> Every document must be traceable. Readers must follow a chain from any statement back to its source. All references (§X.Y, G-NNN, ADR-NNN) must resolve.

**引用**：D3.9 §2.4

### G-117: Consistency Over Completeness

> A consistent incomplete document is better than an inconsistent complete one. Fix contradictions before adding new content.

**引用**：D3.9 §2.5

### G-118: Frozen Documents Protected

> Once a document is marked Frozen, no content changes are allowed without an ADR. Governance-only updates (typos, references, terminology) are permitted.

**引用**：D3.9 §2.6

---

## G-082: Stateless AI Collaboration

> AI collaboration is stateless — each session operates from the current Project State (GitHub HEAD), not from conversation history. Conversation context is ephemeral; documents and repository are persistent.

**引用**：13 §9

## G-083: Evidence-Based Verification

> Every verification claim must reference specific evidence (test output, document section, or approved decision). Claims without evidence are not accepted.

**引用**：13 §8.3

## G-084: GitHub as Project State

> GitHub HEAD is the authoritative representation of current Project State. Project State is an engineering abstraction; it is not the entirety of Project Memory.

**引用**：13 §9.2

## G-085: Knowledge Refinement Over Proliferation

> Knowledge should evolve primarily by refining existing knowledge instead of continuously creating new knowledge. Proliferation (creating new entries) is the least preferred evolution type.

**引用**：13 §10.4

*本文档是 Living Guideline，随 Phase B 推进持续更新。*

*后续 10_9~10_N 每完成一个文档，同步更新本文档。*

---

## 附录：Service Error Taxonomy V1

> **Final Specification**
> 
> 此分类法已在 D3.7 中冻结。
> 后续文档应扩展此分类法，而不是重新定义它。

### 分类法概览

| 编号 | 错误类型 | 适用范围 | 暴露给 Entry |
|------|----------|----------|-------------|
| E-01 | Validation Error | 所有 Service | ✅ |
| E-02 | Conflict Error | 所有 Service | ✅ |
| E-03 | Capability Error | 所有 Service | ✅ |
| E-04 | Persistence Error | 所有 Service | ⚠️ (映射后) |
| E-05 | Background Error | Task Runtime | ⚠️ (映射后) |
| E-06 | Policy Error | 所有 Service | ✅ |
| E-07 | Infrastructure Error | 内部 | ❌ |

### 详细说明

#### E-01: Validation Error

| 属性 | 说明 |
|------|------|
| 触发条件 | 输入参数不符合业务规则 |
| 示例 | 无效的 Memory Level、超出范围的 Confidence |
| 重试策略 | 不重试（客户端修复） |
| 事务影响 | 不启动事务 |

#### E-02: Conflict Error

| 属性 | 说明 |
|------|------|
| 触发条件 | 资源状态冲突（乐观锁、唯一约束） |
| 示例 | Memory 已被其他事务修改、Entity 重复 |
| 重试策略 | 可重试（带退避） |
| 事务影响 | 回滚当前事务 |

#### E-03: Capability Error

| 属性 | 说明 |
|------|------|
| 触发条件 | 业务操作无法完成 |
| 示例 | Reflection 无法生成 Memory（证据不足）、Archive 目标不存在 |
| 重试策略 | 根据具体场景决定 |
| 事务影响 | 回滚当前事务 |

#### E-04: Persistence Error

| 属性 | 说明 |
|------|------|
| 触发条件 | 数据库操作失败 |
| 示例 | 连接丢失、死锁、约束违反 |
| 重试策略 | 可重试（带退避） |
| 事务影响 | 回滚当前事务 |

#### E-05: Background Error

| 属性 | 说明 |
|------|------|
| 触发条件 | 后台任务执行失败 |
| 示例 | Reflection 后台执行超时、Embedding 生成失败 |
| 重试策略 | Task Runtime 重试机制 |
| 事务影响 | 不影响前台事务 |

#### E-06: Policy Error

| 属性 | 说明 |
|------|------|
| 触发条件 | 违反业务策略或权限 |
| 示例 | 无权访问 Workspace、Reflection 策略限制 |
| 重试策略 | 不重试 |
| 事务影响 | 不启动事务 |

#### E-07: Infrastructure Error (Internal Only)

| 属性 | 说明 |
|------|------|
| 触发条件 | 基础设施层故障 |
| 示例 | 网络中断、磁盘满、OOM |
| 重试策略 | 基础设施层处理 |
| 事务影响 | 由基础设施层决定 |

> **注意**：Infrastructure Error 永远不直接暴露给 Entry 层。Entry 层只看到映射后的 EntrySafeError。

### 错误映射规则

```
Repository Exception
    ↓ (Repository Error → Persistence Error E-04)
Service Exception
    ↓ (Persistence Error → Capability Error E-03 / Conflict Error E-02)
Entry Safe Error
    ↓ (Capability/Conflict Error → HTTP 4xx / 5xx)
Protocol Response
```

**原则**：
- 每层只翻译一次
- 保留根因（Exception Chaining）
- 确定性映射（相同输入 → 相同输出）
- Infrastructure Error 不跨越 Service 边界

### 与现有 Guideline 的关系

| 现有 Guideline | 关系 |
|---------------|------|
| G-080 (Deterministic Error Mapping) | 提供具体的错误分类法 |
| G-008 (Command/Query Separation) | 错误类型按 Command/Query 分类 |
| G-049 (Infrastructure Isolation) | Infrastructure Error 隔离在基础设施层 |
