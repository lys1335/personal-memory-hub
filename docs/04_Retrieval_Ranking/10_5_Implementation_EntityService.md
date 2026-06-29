# Personal AI Memory Hub — 10_5 Implementation EntityService

> **版本**: 1.0
> **日期**: 2026-06-28
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
| Create Entity | 创建新 Entity（手动或自动） |
| Resolve Entity | 识别输入是否指向已有 Entity |
| Merge Entity | 合并两个或多个 Entity |
| Rename Entity | 更新 Entity 的 Canonical Name |
| Alias Management | 管理 Entity 的别名体系 |
| Relationship Management | 管理 Entity 间的关系 |
| Entity Profile Update | 更新 Entity 的类型、元数据等属性 |

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
├── Merge Capability
│   ├── mergeEntities()
│   └── getMergeStatus()
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
└── Profile Update Capability
    ├── updateCanonicalName()
    └── updateMetadata()
```

---

## 3. Entity Philosophy

### 3.1 Identity Evolution, Not Mutation

> **Entity identity evolves continuously. EntityID remains stable. Attributes evolve through accumulated Evidence.**

Entity 的身份是持续演化的，不是突变修改的：

| 概念 | 说明 |
|------|------|
| **EntityID** | 稳定不变，是 Identity 的锚点 |
| **Canonical Name** | 通过证据积累持续更新为 Current Best |
| **Alias** | 随证据积累增减 |
| **Metadata** | 随证据积累更新 |
| **Relationships** | 随证据积累演化 |
| **Type** | 随证据积累调整 |

Entity 始终代表 **Current Best Identity**，没有 Candidate 生命周期，没有验证工作流。

### 3.2 Human-like Identity Evolution

> **Entity does not preserve every historical semantic label. Entity preserves current best identity. Historical facts remain inside L0 Memory.**

Entity 不保留每个历史语义标签。Entity 保留当前最佳身份。历史事实在 L0 Memory 中保持不变。

Entity 因此代表：

> **当前对历史经验的语义组织（Current semantic organization of historical experience）。**

### 3.3 Preservation First

> **Identity evolution never deletes historical facts. Entity evolution reorganizes semantic identity. Memory facts remain preserved.**

身份演化从不删除历史事实。Entity 演化重组语义身份。Memory 事实保持不变。

EntityID 是索引（Index），不是历史真相（Historical Truth）。

### 3.4 Memory Fact ≠ Entity Reference

> **Entity Merge updates references. It does NOT modify L0 Facts. Memory remains unchanged. Only Memory's semantic organization changes.**

澄清：

| 概念 | 说明 |
|------|------|
| **Memory Fact** | 原始事实记录，保存在 L0，不可变 |
| **Entity Reference** | 对 Memory Fact 的语义组织索引 |

Reference Migration 是 **Index Maintenance**，不是历史修改。

---

## 4. Capability Boundary

### 4.1 Capability 分组

| Capability 组 | 职责 | 编排的 Engine |
|---------------|------|--------------|
| **Identity Management** | 创建、解析、获取 Entity 档案 | EntityEngine, EvidenceEngine |
| **Merge** | 合并两个或多个 Entity | EntityEngine, RelationshipEngine, EvidenceEngine |
| **Alias** | 管理 Entity 别名体系 | EntityEngine |
| **Relationship** | 管理 Entity 间关系 | EntityEngine, RelationshipEngine |
| **Profile Update** | 更新 Canonical Name、元数据 | EntityEngine |

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

## 7. Entity Merge Strategy

### 7.1 Final Architecture Decision

> **Entity Merge adopts asynchronous Reference Migration. Do NOT introduce runtime Canonical Resolution.**

**理由**：

| 考量 | 说明 |
|------|------|
| Memory Hub 是 Query-first | 查询是高频率操作 |
| Merge 是低频率操作 | 合并很少发生 |
| Query 路径应保持简单 | 不要在每次查询时做 Canonical Resolution |

### 7.2 Merge Workflow

```
Entity Merge (via EntityService)
    ↓
Publish Domain Event (EntityMerged)
    ↓
Task Runtime (异步)
    ↓
Reference Migration
    ↓
Relationship Update
    ↓
Index Rebuild
    ↓
Audit
```

### 7.3 Merge Philosophy

- Entity Merge 更新引用（References），不修改 L0 事实
- Memory 保持不变
- 只有 Memory 的语义组织发生变化
- Reference Migration 是 Index Maintenance，不是历史修改

---

## 8. Lifecycle

### 8.1 Final Lifecycle

```
Created
    ↓
Active
    ↓
Merged
```

### 8.2 已移除的状态

| 移除状态 | 原因 |
|----------|------|
| Candidate | Entity 不是 Candidate，是 Current Best Identity |
| Deprecated | 通过 Merge 处理，不需要独立的 Deprecated 状态 |
| Pending | 无验证工作流 |
| Verified | 语义演化通过证据驱动的属性更新表示，不是生命周期状态 |

### 8.3 设计原则

> **Lifecycle represents objective state transitions. Semantic evolution is represented through evidence-backed attribute updates.**

生命周期表示客观状态转换。语义演化通过证据支持的属性更新来表示。

---

## 9. Domain Events

### 9.1 Event 清单

| 事件 | 触发时机 | 说明 |
|------|----------|------|
| `EntityCreated` | Entity 创建成功 | 新 Entity 持久化后发布 |
| `EntityMerged` | Entity 合并完成 | 合并操作成功后发布 |
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
| EntityService | MemoryEngine | ✅ | Orchestrate | Entity 关联 Memory 维护 | Shared Domain Engine Principle |
| EntityService | QueryEngine | ❌ | Forbidden | QueryEngine 面向读取视图 | Engine 职责隔离 |
| EntityService | MemoryService | ❌ | Forbidden | Service Independence Principle | G-005 |
| EntityService | ReflectionService | ❌ | Forbidden | Service Independence Principle | G-005 |
| EntityService | QueryService | ❌ | Forbidden | Service Independence Principle | G-005 |

### 10.2 与其他 Service 的协作关系

| Service | 协作关系 | 说明 |
|---------|----------|------|
| **MemoryService** | 编排 EntityEngine | 在创建 Memory 时解析 Entity，从不调用 EntityService |
| **ReflectionService** | 可能推断身份演化 | 可能产生 merge 建议，但只有 EntityService 可执行身份修改 |
| **TaskRuntime** | 可能调用 EntityService 能力 | 在异步维护期间调用 EntityService 的能力 |
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
| EntityService → QueryEngine | QueryEngine 面向读取视图 |

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
| P0-6 | **Public API Family** | createEntity()/resolveEntity()/mergeEntities()/addAlias()/addRelationship()/updateCanonicalName() |
| P0-7 | **Service Independence** | 不调用 MemoryService / ReflectionService / QueryService |
| P0-8 | **Shared Domain Engine** | 协调共享 Engine 完成领域变更 |
| P0-9 | **Repository Is Persistence Only** | EntityRepository 不执行 merge/alias/conflict 决策 |
| P0-10 | **EntityID Stability** | EntityID 永不改变 |
| P0-11 | **Evidence-Based Entity** | 每个 Entity 必须有至少一条 L0 Memory 支持 |
| P0-12 | **No Entity Version** | 历史通过 L0 + Evidence Chain + Domain Events 自然存在 |

### 13.2 P1 — 推荐实现

| # | 检查项 | 状态 |
|---|--------|------|
| P1-1 | **Asynchronous Reference Migration** | Merge 后通过 Task Runtime 异步执行 |
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
| 1 | **EntityService 定位** | Identity Management 能力所有者，不是 CRUD | 10_5 §2 |
| 2 | **Identity Evolution, Not Mutation** | EntityID 稳定，属性通过证据演化 | 10_5 §3.1 |
| 3 | **Human-like Identity Evolution** | 保留当前最佳身份，历史在 L0 | 10_5 §3.2 |
| 4 | **Preservation First** | 身份演化不删除历史事实 | 10_5 §3.3 |
| 5 | **Memory Fact ≠ Entity Reference** | Merge 更新引用，不修改 L0 | 10_5 §3.4 |
| 6 | **Five Capability Groups** | Identity / Merge / Alias / Relationship / Profile Update | 10_5 §4 |
| 7 | **Public API Family** | createEntity()/resolveEntity()/mergeEntities()/addAlias()/addRelationship()/updateCanonicalName() | 10_5 §5 |
| 8 | **Domain Invariants in Engine** | EntityEngine 拥有所有领域不变量 | 10_5 §5.3 |
| 9 | **Repository Is Persistence Only** | EntityRepository 不执行 merge/alias 决策 | 10_5 §6 |
| 10 | **Asynchronous Reference Migration** | Merge 后发布事件，Task Runtime 异步执行 | 10_5 §7 |
| 11 | **No Runtime Canonical Resolution** | Query 路径保持简单 | 10_5 §7.1 |
| 12 | **Three-State Lifecycle** | Created → Active → Merged | 10_5 §8 |
| 13 | **Lifecycle = Objective Transitions** | 语义演化通过证据驱动的属性更新 | 10_5 §8.3 |
| 14 | **Domain Events = Completed Facts** | 事件在事务提交后发布 | 10_5 §9.2 |
| 15 | **Task Runtime for Async Maintenance** | Reference Migration / Graph Maintenance / Index Rebuild | 10_5 §9.3 |
| 16 | **EntityService Never Waits** | 后台维护不影响在线事务延迟 | 10_5 §9.3 |
| 17 | **Service Independence** | 不调用其他 Service | 10_5 §10 |
| 18 | **Service May Orchestrate Multiple Engines** | 澄清现有 Service Layer 规则 | 10_5 §10.3 |
| 19 | **Evidence-Based Entity** | 每个 Entity 必须有 L0 Memory 支持 | 10_5 §11.2 |
| 20 | **No Entity Version** | 历史通过 L0 + Evidence + Events 自然存在 | 10_5 §11.4 |
| 21 | **Manual Entity Creation Allowed** | 创建交互本身产生 L0 Memory | 10_5 §11.2 |
| 22 | **Entity Suppression = Potential Only** | MVP 不实现 | 10_5 §12.2 |
| 23 | **Progressive Recall = Potential Only** | MVP 不实现 | 10_5 §12.2 |
| 24 | **ReflectionService 可推断身份演化** | 但只有 EntityService 可执行身份修改 | 10_5 §10.2 |
| 25 | **QueryService 消费 Entity 信息** | 但不拥有 Entity 状态 | 10_5 §10.2 |

---

## 15. Backport Updates

完成 10_5 后，需要同步更新以下文档：

| 文档 | 更新内容 |
|------|----------|
| **03_Entity_MemoryGraph** | 补充 Entity Lifecycle 定义（Created → Active → Merged） |
| **06_Runtime_Architecture** | 补充 EntityEngine 职责与 EntityService 编排关系 |
| **08_Implementation_Architecture** | 补充 EntityRepository 边界（Persistence Only） |
| **10_1_Implementation_Service_Layer** | 补充 EntityService 到 Service 清单，补充 EntityEngine 到 Engine 清单，补充 Service DAG |
| **10_3_Implementation_QueryService** | 补充 QueryService 消费 Entity 信息的角色 |
| **10_6_Implementation_TaskRuntime** | 补充 Task Runtime 与 EntityService Domain Events 的集成 |
| **12_Architecture_Decisions** | 新增 ADR：Entity Merge Strategy |
| **13_Architecture_Guidelines** | 新增 Entity 相关 Guideline |

---

## 16. Version Record

| 版本 | 日期 | 变更 | 状态 |
|------|------|------|------|
| 1.0 | 2026-06-28 | 初始版本，确认 EntityService 全部设计要素 | ✅ 已确认 |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

*本文档继承 Phase B 所有已确立的架构原则（Service Independence、Shared Domain Engine、Command/Query Separation、One Capability One Implementation）。*
