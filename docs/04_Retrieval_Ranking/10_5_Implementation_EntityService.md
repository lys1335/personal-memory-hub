# Personal AI Memory Hub — 10_5 Implementation EntityService

> **版本**: 2.0
> **日期**: 2026-07-11
> **阶段**: Phase B — 实现设计（第五部分）
> **状态**: 已确认
> **作者**: 系统架构组

---

## 1. Purpose

本文档定义 **EntityService** 的工程实现设计。

EntityService 负责 Memory Hub 的身份管理（Identity Management），维护 Memory Pyramid 中所有高层 Memory 所引用的 Entity 实体的当前最佳身份。

本文档是 Phase B 所有后续 Service 设计文档的参考基准。

---

## 2. EntityService Responsibility

### 2.1 核心定位

> **EntityService 是 Identity Management 的能力所有者（Public Capability Owner）。**

EntityService 负责：

| 职责 | 说明 |
|------|------|
| **Create Entity** | 创建新 Entity（手动或自动） |
| **Resolve Entity** | 识别输入是否指向已有 Entity |
| **Get Entity Profile** | 获取 Entity 当前最佳身份档案 |
| **Identity Consolidation** | 合并两个或多个 Entity 的身份（见 §7 重定义） |
| **Metadata Update** | 更新 Entity 的 Canonical Name、Alias 等元数据（原 Rename） |
| **Alias Management** | 管理 Entity 的别名体系 |
| **Relationship Management** | 管理 Entity 间的关系 |
| **Entity Profile Update** | 更新 Entity 的类型、元数据等属性 |

EntityService **不负责**：

| 禁止 | 原因 |
|------|------|
| Memory 管理 | 属于 MemoryService |
| Reflection 生成 | 属于 ReflectionService |
| Query Projection | 属于 QueryService |
| 历史版本快照 | Entity 历史通过 L0 Memory + Evidence Chain + Domain Events 自然存在 |

### 2.2 明确禁止

EntityService **不得**执行以下操作：

| 禁止 | 原因 |
|------|------|
| 直接调用其他 Service | 违反 Service Independence Principle（G-005） |
| 直接操作 Repository | Repository 属于 Engine 职责 |
| 执行 merge 决策 | Merge 决策属于 EntityEngine 的 Domain Invariant |
| 执行 alias conflict 决策 | Alias 冲突检测属于 EntityEngine |
| 选择 Canonical Name | Canonical Name 选择属于 EntityEngine 的领域不变量 |
| 绑定具体实现技术 | 如 Cron、MQ、EventBus 等 |
| 自主创建 L0 Memory | L0 必须源于用户交互或用户预授权 |
| **Delete Entity** | Entity 一旦创建永久存在，不可删除、销毁或恢复 |
| **Rewrite Memory References** | Memory 引用不可变，Merge 不重写历史 Memory 引用 |

### 2.3 正确定位

EntityService 的公开接口按 **Capability** 组织，而非按 **持久化操作** 组织。

```
EntityService
│
├── Identity Management Capability
│   ├── createEntity()
│   ├── resolveEntity()
│   └── getEntityProfile()
│
├── Identity Consolidation Capability (原 Merge)
│   ├── consolidateIdentities()
│   └── getConsolidationStatus()
│
├── Alias Capability
│   ├── addAlias()
│   ├── removeAlias()
│   └── getAliases()
│
├── Relationship Capability
│   ├── addRelationship()
│   ├── removeRelationship()
│   └── getRelationships()
│
└── Metadata Update Capability (原 Profile Update)
    ├── updateCanonicalName()
    └── updateMetadata()
```

---

## 3. Entity Evolution Philosophy

### 3.1 Identity Evolution, Not Lifecycle

> **Entity is a persistent identity model, not a lifecycle object.** Entity permanently exists after creation. No delete. No destroy. No restore.

Entity 的身份是持续演化的，不是生命周期管理的：

| 概念 | 说明 |
|------|------|
| **EntityID** | 稳定不变，是 Identity 的锚点 |
| **Canonical Name** | 通过证据积累持续更新为 Current Best |
| **Alias** | 随证据积累增减 |
| **Metadata** | 随证据积累更新 |
| **Relationships** | 随证据积累演化 |
| **Type** | 随证据积累调整 |

Entity 始终代表 **Current Best Identity**，没有 Candidate 生命周期，没有验证工作流。

**Entity 永久存在**：Entity 一旦创建即永久存在。不存在删除、销毁或恢复操作。

### 3.2 Entity Is a Persistent Identity Model

> **Entity is a persistent identity model rather than a lifecycle object.**

Entity 代表：

> **当前对历史经验的语义组织（Current semantic organization of historical experience）。**

### 3.3 Preservation First

> **Identity evolution never deletes historical facts. Entity evolution reorganizes semantic identity. Memory facts remain preserved.**

身份演化从不删除历史事实。Entity 演化重组语义身份。Memory 事实保持不变。

EntityID 是索引（Index），不是历史真相（Historical Truth）。

### 3.4 Memory References Are Immutable

> **Memory always keeps its original Entity reference. Entity Merge never rewrites historical Memory references.**

澄清：

| 概念 | 说明 |
|------|------|
| **Memory Fact** | 原始事实记录，保存在 L0，不可变 |
| **Entity Reference** | 对 Memory Fact 的语义组织索引 |

Memory 引用是不可变的。Entity Merge 不重写历史 Memory 引用。

### 3.5 QueryService Performs Alias / Canonical / Merge-Graph Resolution

> **QueryService performs Alias Resolution, Canonical Resolution, and Merge Graph Expansion.**

QueryService 的职责：

- **Alias Resolution**：将别名解析为当前 Canonical EntityID
- **Canonical Resolution**：将 Canonical Name 解析为 EntityID
- **Merge Graph Expansion**：在查询时展开合并图，将已合并 Entity 的相关 Memory 纳入结果

Memory 本身保持不变。

### 3.6 Relationship Belongs to Identity Graph

> **Relationship belongs to the current Identity Graph. Relationship may evolve together with Entity. Memory references never evolve.**

- Relationship 属于当前 Identity Graph
- Relationship 可能与 Entity 一起演化
- Memory 引用永远不变

---

## 4. Capability Boundary

### 4.1 Capability 分组

|| Capability 组 | 职责 | 编排的 Engine |
||---------------|------|--------------|
|| **Identity Management** | 创建、解析、获取 Entity 档案 | EntityEngine, EvidenceEngine |
|| **Identity Consolidation** | 合并两个或多个 Entity 的身份 | EntityEngine, RelationshipEngine, EvidenceEngine |
|| **Alias** | 管理 Entity 别名体系 | EntityEngine |
|| **Relationship** | 管理 Entity 间关系 | EntityEngine, RelationshipEngine |
|| **Metadata Update** | 更新 Canonical Name、元数据 | EntityEngine |

> **Note**: "Merge" 重新定义为 **Identity Consolidation**——它是身份层面的合并，不代表真实世界的演化。
> "Rename" 重新定义为 **Metadata Update**——只更新元数据。

### 4.2 Capability-Oriented API

EntityService 是 Entity Management 的公共能力所有者（Public Capability Owner）。

**One Capability, One Implementation.**

其他 Service 从不同步调用 EntityService。

相反：

- Service 编排多个 Domain Engine
- 例如：MemoryService → EntityEngine.Resolve() → MemoryEngine.Create()

**无 Service-to-Service 调用。**

---

## 5. Service → Engine Orchestration

### 5.1 编排关系

EntityService 作为 Identity Management 的能力所有者，协调共享 Domain Engine：

```
EntityService
        │
        ├── EntityEngine
        │       ↓
        │   Identity Resolution / Merge / Alias / Canonical Name
        │
        ├── EvidenceEngine
        │       ↓
        │   Evidence Chain Validation
        │
        └── RelationshipEngine
                ↓
            Relationship Update
```

### 5.2 共享 Engine 原则

EntityService 协调共享 Domain Engine 来管理 Entity Identity。它从不调用其他 Application Service。

| Engine | EntityService 可调用 | 原因 |
|--------|---------------------|------|
| EntityEngine | ✅ 必须 | Entity Identity 核心算法 |
| EvidenceEngine | ✅ 必须 | 证据链验证 |
| RelationshipEngine | ✅ 必须 | 关系更新 |
| MemoryEngine | ✅ 可选 | Entity 关联 Memory 的维护 |
| QueryEngine | ❌ 不调用 | Query 属于读取能力 |
| TaskService | ⚠️ 通过 Event | 异步维护通过 Domain Event → Task Registry 路由（G-024） |

### 5.3 领域不变量归属

> **EntityService performs validation, authorization, transaction, and orchestration. EntityEngine owns ALL domain invariants.**

EntityEngine 拥有的领域不变量：

| 不变量 | 说明 |
|--------|------|
| Identity Resolution | 识别输入是否指向已有 Entity |
| Merge Rules | 合并规则：何时合并、如何合并 |
| Alias Rules | 别名冲突检测与处理 |
| Relationship Rules | 关系有效性约束 |
| Canonical Name Selection | 当前最佳名称选择 |
| Entity Consistency | Entity 整体一致性 |

**永远不要把领域不变量移到 Service 中。**

---

## 6. Repository Boundary

### 6.1 EntityRepository

EntityRepository 保持 **Persistence Only**。

Repository **不得**执行：

| 禁止 | 原因 |
|------|------|
| Merge Decision | 合并决策属于 EntityEngine |
| Alias Conflict Decision | 别名冲突属于 EntityEngine |
| Relationship Validation | 关系验证属于 EntityEngine |

Repository 仅返回 **Domain Objects**。

**Never Projection. Never DTO.**

### 6.2 EntityQueryRepository

EntityQueryRepository 负责 Entity 图查询（遍历 relationships），但仍属于持久化层，不包含业务逻辑。

---

## 7. Identity Consolidation (原 Entity Merge)

### 7.1 Redefinition of Merge

> **Merge is redefined as Identity Consolidation. Merge does NOT represent real-world evolution. Rename is Metadata Update.**

Identity Consolidation 是身份层面的合并，不代表真实世界的演化。

### 7.2 Metadata Definition

> **Metadata includes Canonical Name, Alias List, and other metadata attributes.**

| 元数据项 | 说明 |
|----------|------|
| **Canonical Name** | 当前最佳名称 |
| **Alias List** | 所有别名列表 |
| **Other Metadata** | 类型、区域、父级等属性 |

**Rename 仅是 Metadata Update**，不改变 Entity 身份。

### 7.3 Final Architecture Decision

> **Entity Consolidation adopts asynchronous Reference Graph Update. Do NOT introduce runtime Canonical Resolution.**

**理由**：

| 考量 | 说明 |
|------|------|
| Memory Hub 是 Query-first | 查询是高频率操作 |
| Consolidation 是低频率操作 | 合并很少发生 |
| Query 路径应保持简单 | 不要在每次查询时做 Canonical Resolution |

### 7.4 Consolidation Workflow

```
Identity Consolidation (via EntityService)
    ↓
Publish Domain Event (IdentitiesConsolidated)
    ↓
Task Runtime (异步)
    ↓
Reference Graph Update (不修改 Memory)
    ↓
Relationship Update
    ↓
Index Rebuild
    ↓
Audit
```

### 7.5 Consolidation Philosophy

- Identity Consolidation 更新引用图（References），不修改 L0 事实
- Memory 引用不可变，永远不重写
- 只有 Memory 的语义组织发生变化
- Reference Graph Update 是 Index Maintenance，不是历史修改

---

## 8. Entity Permanence (原 Lifecycle)

### 8.1 Permanent Existence

> **Entity is never deleted. No Delete. No Destroy. No Restore. Entity permanently exists after creation.**

Entity 一旦创建即永久存在。不存在删除、销毁或恢复操作。

### 8.2 Removed States

|| 移除状态 | 原因 |
||----------|------|
|| Candidate | Entity 不是 Candidate，是 Current Best Identity |
|| Deprecated | 通过 Consolidation 处理，不需要独立的 Deprecated 状态 |
|| Pending | 无验证工作流 |
|| Verified | 语义演化通过证据驱动的属性更新表示，不是生命周期状态 |
|| Deleted / Archived / Restored | Entity 永久存在，无需删除/归档/恢复 |

### 8.3 Design Principle

> **Entity permanence replaces lifecycle. There is no delete, destroy, or restore. Entity permanently exists after creation.**

实体永久存在原则取代了生命周期概念。

---

## 9. Domain Events

### 9.1 Event 清单

| 事件 | 触发时机 | 说明 |
|------|----------|------|
| `EntityCreated` | Entity 创建成功 | 新 Entity 持久化后发布 |
|| `IdentitiesConsolidated` | Identity Consolidation 完成 | 合并操作成功后发布 |
| `EntityAliasAdded` | 别名添加成功 | 新别名加入后发布 |
| `EntityAliasRemoved` | 别名移除成功 | 别名移除后发布 |
| `EntityRelationshipAdded` | 关系添加成功 | 新关系建立后发布 |
| `EntityRelationshipRemoved` | 关系移除成功 | 关系断开后发布 |
| `EntityProfileUpdated` | 档案更新成功 | Canonical Name / Metadata 更新后发布 |

### 9.2 Domain Events 原则

| 原则 | 说明 |
|------|------|
| **Events 代表已完成的业务事实** | 事件在事务提交后发布 |
| **事件从不执行业务逻辑** | 异步处理属于 Task Runtime |
| **EntityService 在成功提交后发布事件** | 保证事件与持久化状态一致 |

**参考**：10_6 §4 (Task Chaining via Events), §6 (Idempotency), §5.4 (Recovery)。Entity Merge 后发布的 Domain Event 遵循 10_6 定义的 Task Chaining 和幂等性规范。

### 9.3 与 Task Runtime 的集成

```
EntityService
    ↓ 提交事务
    ↓ 发布 Domain Event
    ↓
Task Runtime
    ↓
Maintenance Tasks
    ├── Reference Migration
    ├── Relationship Maintenance
    ├── Graph Maintenance
    ├── Index Rebuild
    ├── Cache Refresh
    └── Audit
```

> **EntityService 从不等待后台维护完成。**
>
> **后台维护不得影响在线事务延迟。**

---

## 10. Service Collaboration

### 10.1 Service → Service 交互

| Caller | Callee | Allowed | Interaction Pattern | Reason | Architecture Rule |
|--------|--------|---------|---------------------|--------|-------------------|
| EntityService | EntityEngine | ✅ | Orchestrate | Entity Identity 核心算法 | Shared Domain Engine Principle |
| EntityService | EvidenceEngine | ✅ | Orchestrate | 证据链验证 | Shared Domain Engine Principle |
| EntityService | RelationshipEngine | ✅ | Orchestrate | 关系更新 | Shared Domain Engine Principle |
| EntityService | MemoryEngine | ✅ | Orchestrate | Entity 关联 Memory 的维护 | Shared Domain Engine Principle |
| EntityService | QueryEngine | ❌ | Forbidden | QueryEngine 面向读取视图 | Engine 职责隔离 |
| EntityService | MemoryService | ❌ | Forbidden | Service Independence Principle | G-005 |
| EntityService | ReflectionService | ❌ | Forbidden | Service Independence Principle | G-005 |
| EntityService | QueryService | ❌ | Forbidden | Service Independence Principle | G-005 |
| EntityService | TaskService | ⚠️ | Event → Task Registry | 通过 Domain Event 触发异步维护，不直接调用 | G-024 |

### 10.2 与其他 Service 的协作关系

| Service | 协作关系 | 说明 |
|---------|----------|------|
| **MemoryService** | 编排 EntityEngine | 在创建 Memory 时解析 Entity，从不调用 EntityService |
| **Identity Consolidation** | 可能推断身份合并 | 可能产生 consolidation 建议，但只有 EntityService 可执行身份修改 |
| **TaskService** | 可能调用 EntityService 能力 | 在异步维护期间调用 EntityService 的能力 |
| **QueryService** | 消费 Entity 信息 | 从不拥有 Entity 状态 |

### 10.3 Service 编排澄清

> **A Service may orchestrate multiple Domain Engines.**

示例：

```
MemoryService
    ↓
EntityEngine
+
MemoryEngine
```

跨服务同步调用仍然禁止。这是对现有 Service Layer 规则的澄清，不是新架构。

### 10.4 Forbidden Dependencies

| Forbidden | Reason |
|-----------|--------|
| EntityService → MemoryService | Service Independence Principle (G-005) |
| EntityService → ReflectionService | Service Independence Principle (G-005) |
| EntityService → QueryService | Service Independence Principle (G-005) |
| EntityService | QueryEngine | QueryEngine 面向读取视图 |
| EntityService | TaskService | Task 提交通过 Domain Event 路由（G-024） |

---

## 11. Consistency Principles

### 11.1 EntityID Stability

> **EntityID remains stable. Attributes evolve through accumulated Evidence.**

EntityID 是 Identity 的锚点，永不改变。属性（Canonical Name、Alias、Metadata、Relationships、Type）通过积累的证据演化。

### 11.2 Evidence-Based Entity

> **Every Entity must ultimately be supported by at least one L0 Memory.**

手动创建 Entity 是允许的。创建交互本身产生 L0 Memory，因此每个 Entity 最终都得到至少一条 L0 Memory 的支持。这保持了 Evidence-Based Memory 原则。

### 11.3 Current Best Identity

> **Entity is always Current Best Identity. No Candidate lifecycle. No verification workflow.**

Entity 始终是当前最佳身份。没有 Candidate 生命周期，没有验证工作流。

### 11.4 No Entity Version

> **Do NOT introduce Entity Version.**

不引入 Entity 版本。理由：

| 理由 | 说明 |
|------|------|
| L0 Memory 已存在历史 | 历史事实保存在 L0 Memory 中 |
| Evidence Chain 已存在 | 证据链提供追溯能力 |
| Domain Events 已存在 | 领域事件记录所有变更 |
| Audit 已存在 | 审计日志记录操作轨迹 |
| Entity 仅代表 Current Best | 历史重建应始终依赖证据，而非重复的版本表 |

### 11.5 Entity Transactions Are Limited Scope

> **Entity transactions only modify Entity, Metadata, and Relationship Graph. Never Observation, Memory, or Evidence.**

Entity 事务的修改范围：

| 可修改 | 禁止修改 |
|--------|----------|
| Entity | Observation |
| Metadata | Memory |
| Relationship Graph | Evidence |

### 11.6 Proposal and Task Are Independent

> **Proposal = Business Recommendation. Task = Execution Scheduling. Proposal may execute immediately, through Task, or other future workflows. Manual review is optional, not the default architecture.**

Proposal 和 Task 是独立概念：
- **Proposal** = 业务建议（如 Reflection 产生的 Entity Evolution Proposal）
- **Task** = 执行调度（TaskService 负责）
- Proposal 可以立即执行、通过 Task 执行、或通过其他未来工作流执行
- 人工审查是可选的，不是默认架构

---

## 12. Future Evolution

### 12.1 Planned Evolution

| 方向 | 说明 |
|------|------|
| **Manual Entity Creation Support** | 用户手动创建 Entity 的完整流程 |
| **Entity Relationship Graph Visualization** | Entity 关系的可视化展示 |

### 12.2 Potential Evolution

| 方向 | 说明 |
|------|------|
| **Entity Suppression / Entity Escape** | 用户可能希望移除情感相关的身份标识。系统不应物理删除历史事实。未来架构可能支持：特定身份在正常检索中逐渐消失，但底层生活经验仍被保留。历史事实可通过显式召回恢复。 |
| **Progressive Recall** | 正常检索应优先匹配用户当前语义上下文的抽象层级。显式召回请求可逐步恢复更具体的历史身份。例如：Life Experience → Relationship → Former Partner → Specific Person。 |

> **以上为 Future Architecture Exploration，MVP 不实现，不指定具体实现方式。**

---

## 13. Checklist

### 13.1 P0 — 必须完成

| # | 检查项 | 状态 |
|---|--------|------|
| P0-1 | **Side-Effect Free Query** | EntityService 是写编排服务，不涉及查询 |
| P0-2 | **Service → Service 检查** | 无 Service 互调，仅编排 Engine |
| P0-3 | **Engine DAG 清晰** | EntityEngine + EvidenceEngine + RelationshipEngine |
| P0-4 | **Service DAG 无循环** | EntityService 不依赖其他 Service |
| P0-5 | **Consumer-Agnostic Interface** | Public API 面向能力，不面向调用方 |
|| P0-6 | **Public API Family** | createEntity()/resolveEntity()/consolidateIdentities()/addAlias()/addRelationship()/updateCanonicalName() |
|| P0-7 | **Service Independence** | 不调用 MemoryService / ReflectionService / QueryService |
|| P0-8 | **Shared Domain Engine** | 协调共享 Engine 完成领域变更 |
|| P0-9 | **Repository Is Persistence Only** | EntityRepository 不执行 consolidation/alias/conflict 决策 |
|| P0-10 | **EntityID Stability** | EntityID 永不改变 |
|| P0-11 | **Evidence-Based Entity** | 每个 Entity 必须有至少一条 L0 Memory 支持 |
|| P0-12 | **No Entity Version** | 历史通过 L0 + Evidence Chain + Domain Events 自然存在 |
|| P0-13 | **Entity Permanence** | Entity 永久存在，不可删除/销毁/恢复 |
|| P0-14 | **Memory Reference Immutability** | Memory 引用不可变，Consolidation 不重写历史引用 |
|| P0-15 | **Identity Consolidation Redefined** | Merge 重定义为 Identity Consolidation，不代表真实世界演化 |
|| P0-16 | **Metadata Update** | Rename 重定义为 Metadata Update |
|| P0-17 | **QueryService Resolution** | QueryService 执行 Alias/Canonical/Merge-Graph 解析 |
|| P0-18 | **Relationship Evolution** | Relationship 属于 Identity Graph，可与 Entity 一起演化 |
|| P0-19 | **Reflection Proposal Only** | ReflectionService 仅产生 Entity Evolution Proposals，不直接修改 Entity |
|| P0-20 | **Proposal-Task Separation** | Proposal 和 Task 是独立概念 |
|| P0-21 | **Transaction Scope** | Entity 事务仅修改 Entity/Metadata/Relationship，不碰 Observation/Memory/Evidence |
|| P0-22 | **Verification Scope** | 验证包含 Identity Persistence、Identity Evolution、Memory Reference Stability、Query Transparency、Identity Graph Integrity、Transaction Atomicity、Capability Boundary |

### 13.2 P1 — 推荐实现

| # | 检查项 | 状态 |
|---|--------|------|
|| P1-1 | **Asynchronous Reference Graph Update** | Consolidation 后通过 Task Runtime 异步执行 |
| P1-2 | **Domain Events for All Changes** | 所有变更发布领域事件 |
| P1-3 | **Entity Audit Trail** | 审计轨迹记录所有身份变更 |

### 13.3 P2 — 未来演进

| # | 检查项 | 状态 |
|---|--------|------|
| P2-1 | **Entity Suppression / Escape** | 用户可隐藏特定身份 |
| P2-2 | **Progressive Recall** | 逐步恢复历史身份 |

---

## 14. Decision Summary

| # | 决策 | 说明 | 来源 |
|---|------|------|------|
|| 1 | **EntityService 定位** | Identity Management 能力所有者，不是 CRUD | 10_5 §2 |
|| 2 | **Entity Evolution, Not Lifecycle** | Entity 是持久身份模型，不是生命周期对象 | 10_5 §3.1 |
|| 3 | **Entity Permanence** | Entity 永久存在，不可删除/销毁/恢复 | 10_5 §8.1 |
|| 4 | **Preservation First** | 身份演化不删除历史事实 | 10_5 §3.3 |
|| 5 | **Memory Reference Immutability** | Memory 引用不可变，Consolidation 不重写历史引用 | 10_5 §3.4 |
|| 6 | **Identity Consolidation Redefined** | Merge 重定义为 Identity Consolidation，不代表真实世界演化 | 10_5 §7.1 |
|| 7 | **Metadata Update** | Rename 重定义为 Metadata Update | 10_5 §7.2 |
|| 8 | **Six Capability Groups** | Identity / Consolidation / Alias / Relationship / Metadata Update | 10_5 §2.3 |
|| 9 | **Public API Family** | createEntity()/resolveEntity()/consolidateIdentities()/addAlias()/addRelationship()/updateCanonicalName() | 10_5 §2.3 |
|| 10 | **Domain Invariants in Engine** | EntityEngine 拥有所有领域不变量 | 10_5 §5.3 |
|| 11 | **Repository Is Persistence Only** | EntityRepository 不执行 consolidation/alias 决策 | 10_5 §6 |
|| 12 | **Asynchronous Reference Graph Update** | Consolidation 后发布事件，Task Runtime 异步执行 | 10_5 §7.4 |
|| 13 | **No Runtime Canonical Resolution** | Query 路径保持简单 | 10_5 §7.3 |
|| 14 | **Entity Permanence Principle** | Entity 永久存在，无删除/销毁/恢复 | 10_5 §8.1 |
|| 15 | **QueryService Resolution** | QueryService 执行 Alias/Canonical/Merge-Graph 解析 | 10_5 §3.5 |
|| 16 | **Relationship Evolution** | Relationship 属于 Identity Graph，可与 Entity 一起演化 | 10_5 §3.6 |
|| 17 | **Domain Events = Completed Facts** | 事件在事务提交后发布 | 10_5 §9.2 |
|| 18 | **Task Runtime for Async Maintenance** | Reference Graph Update / Graph Maintenance / Index Rebuild | 10_5 §9.3 |
|| 19 | **EntityService Never Waits** | 后台维护不影响在线事务延迟 | 10_5 §9.3 |
|| 20 | **Service Independence** | 不调用其他 Service | 10_5 §10 |
|| 21 | **Service May Orchestrate Multiple Engines** | 澄清现有 Service Layer 规则 | 10_5 §10.3 |
|| 22 | **Evidence-Based Entity** | 每个 Entity 必须有 L0 Memory 支持 | 10_5 §11.2 |
|| 23 | **No Entity Version** | 历史通过 L0 + Evidence + Events 自然存在 | 10_5 §11.4 |
|| 24 | **Manual Entity Creation Allowed** | 创建交互本身产生 L0 Memory | 10_5 §11.2 |
|| 25 | **Entity Transaction Scope** | 仅修改 Entity/Metadata/Relationship，不碰 Observation/Memory/Evidence | 10_5 §11.5 |
|| 26 | **Proposal-Task Separation** | Proposal 是业务建议，Task 是执行调度 | 10_5 §11.6 |
|| 27 | **Reflection Proposal Only** | ReflectionService 仅产生 Entity Evolution Proposals | 10_5 §11.6 |
|| 28 | **Entity Suppression = Potential Only** | MVP 不实现 | 10_5 §12.2 |
|| 29 | **Progressive Recall = Potential Only** | MVP 不实现 | 10_5 §12.2 |
|| 30 | **Identity Consolidation suggestion** | 可能被 Reflection 推断，但只有 EntityService 可执行 | 10_5 §10.2 |
|| 31 | **QueryService consumes Entity info** | 但不拥有 Entity 状态 | 10_5 §10.2 |

---

## 15. Backport Updates

完成 10_5 后，需要同步更新以下文档：

| 文档 | 更新内容 |
|------|----------|
| **03_Entity_MemoryGraph** | 补充 Entity Permanence 定义（无 Delete/Destroy/Restore） |
| **06_Runtime_Architecture** | 补充 EntityEngine 职责与 EntityService 编排关系 |
| **08_Implementation_Architecture** | 补充 EntityRepository 边界（Persistence Only） |
| **10_1_Implementation_Service_Layer** | 补充 EntityService 到 Service 清单，补充 EntityEngine 到 Engine 清单，补充 Service DAG |
| **10_3_Implementation_QueryService** | 补充 QueryService 消费 Entity 信息的角色 |
| **10_6_Implementation_TaskService** | 补充 Task Runtime 与 EntityService Domain Events 的集成 |
| **12_Architecture_Decisions** | 新增 ADR：Entity Merge Strategy |
| **13_Architecture_Guidelines** | 新增 Entity 相关 Guideline |

---

## 16. Version Record

| 版本 | 日期 | 变更 | 状态 |
|------|------|------|------|
| 2.0 | 2026-07-11 | D3.5 最终决策集成：(1) Entity Lifecycle → Entity Evolution (2) No Delete (3) Merge → Identity Consolidation (4) Rename → Metadata Update (5) Memory refs immutable (6) QueryService resolution (7) Relationship evolution (8) Reflection proposal only (9) Proposal-Task separation (10) Transaction scope (11) Verification scope (12) 8 new principles + Error Taxonomy | ✅ 已确认 |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

*本文档继承 Phase B 所有已确立的架构原则（Service Independence、Shared Domain Engine、Command/Query Separation、One Capability One Implementation）。*
