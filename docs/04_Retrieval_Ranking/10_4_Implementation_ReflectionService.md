# Personal AI Memory Hub — 10_4 Implementation ReflectionService

> **版本**: 1.0
> **日期**: 2026-06-28
> **阶段**: Phase B — 实现设计（第四部分）
> **状态**: 已确认
> **作者**: 系统架构组

---

## 1. Purpose

本文档定义 **ReflectionService** 的工程实现设计。

ReflectionService 负责维护 Memory Pyramid 的语义质量、证据一致性和持续知识演化。

本文档是 Phase B 所有后续 Service 设计文档的参考基准。

---

## 2. ReflectionService Responsibility

### 2.1 核心定位

> **ReflectionService is responsible for maintaining the semantic quality, evidence consistency, and continuous knowledge evolution of the Memory Pyramid.**

ReflectionService 是 **Memory Domain** 的演化编排服务（Orchestration Service），不是摘要生成器。

它编排 ReflectionEngine、MemoryEngine、EntityEngine、ArchiveEngine 等 Domain Engine，完成记忆领域的知识演化。

### 2.2 明确禁止

ReflectionService **不得**执行以下操作：

| 禁止 | 原因 |
|------|------|
| 直接调用其他 Service | 违反 Service Independence Principle（G-005） |
| 直接操作 Repository | Repository 属于 Engine 职责 |
| 自主创建 L0 Memory | L0 必须源于用户交互或用户预授权 |
| 保存高层 Memory 的历史版本 | 高层 Memory 存储当前最佳知识，不是历史快照 |
| 直接修改业务状态 | 通过 Domain Engine 编排 |
| 绑定具体实现技术 | 如 Cron、MQ、EventBus 等 |

### 2.3 正确定位

ReflectionService 的公开接口按 **Capability** 组织，而非按 **实现动作** 组织。

```
ReflectionService
│
├── Reflect Capability
│   ├── reflect()
│   ├── reflectByEntity()
│   ├── reflectByTimeWindow()
│   └── reflectByScope()
│
├── Consolidate Capability
│   ├── consolidate()
│   └── consolidateByEntity()
│
├── Summarize Capability
│   ├── summarize()
│   └── summarizeByLevel()
│
└── Evaluate Capability
    ├── evaluate()
    └── evaluateByEntity()
```

---

## 3. Reflection Philosophy

### 3.1 Reflection 是演化，不是突变

> **Reflection Is Evolution, Not Mutation Principle**

ReflectionService 的职责是驱动 Memory 的演化（Evolution），而不是直接修改任意 Domain Object。Reflection 产生的是领域决策（Decision）、建议（Proposal）或新的领域结果，由对应 Domain Engine 完成实际领域变更。

意义：
- 避免 ReflectionService 成为"万能修改器"
- 保持 Reflection 流程可审计、可解释、可回放
- 与 Evidence-Based Memory 保持一致：每一次演化都有可追溯的依据

### 3.2 高层 Memory 存储演化解释，而非历史快照

> **Higher-level Memory stores evolving explanations rather than historical snapshots.**

当变化本身具有知识价值时，高层 Memory 应描述演化，而不是保存多个时间快照。

示例：
- **错误**：L2 保存"用户研究 Hermes" → 后来改为"用户研究 Codex"
- **正确**：L2 保存"用户的研究重点已从 Hermes Desktop 逐步转向 Codex，目前主要关注 Codex，Hermes 的研究经历是当前知识体系的重要基础"

### 3.3 Memory Pyramid 抽象基于解释范围（Scope），而非时间

Memory Pyramid 不是按时间组织的，而是按解释范围组织的：

| 层级 | 类型 | 解释范围 | 示例 |
|------|------|----------|------|
| L0 | Historical Facts | 原始事实 | 聊天记录、导入文档 |
| L1 | Topic Knowledge | 单主题内总结 | "Personal Memory Hub 开发日志总结" |
| L2 | Cross-topic Pattern | 跨主题模式 | "用户选择工具时先验证架构再验证成本" |
| L3 | General Principle | 一般原则 | "用户长期决策：优先长期价值，避免重复返工" |

每一层回答不同的问题：

| 层级 | 问题 |
|------|------|
| L0 | 发生了什么？(What Happened?) |
| L1 | 这个主题说明了什么？(What Does This Topic Mean?) |
| L2 | 这些主题体现了什么模式？(What Pattern Does It Reveal?) |
| L3 | 这些模式背后的原则是什么？(What Principle Explains These Patterns?) |

### 3.4 Reflection 目标：提升解释力

> **The objective of Reflection is not to preserve snapshots, but to continuously improve the explanatory power of higher-level memories as evidence accumulates.**

Reflection 每次更新时都会问：**新的 Memory 能否更好地解释全部 Evidence？**
- 如果能 → 更新
- 如果不能 → 保持原状

### 3.5 同层语义唯一

> **Semantic Uniqueness Principle**

在同一抽象层级内，同一语义空间应只有一个当前有效的 Memory 节点。Reflection 首先尝试语义合并/更新，只有在语义唯一性无法维持时才创建新 Memory。

### 3.6 增量传播

> **Incremental Propagation Principle**

Reflection 向上传播是增量式的：

1. 更新当前层
2. 评估是否影响上层
3. 仅当必要时向上传播

不重建整个金字塔。

---

## 4. Capability Taxonomy

### 4.1 四大能力

| Capability | 职责 | 编排的 Engine |
|------------|------|--------------|
| **Reflect** | 对指定范围的 Memory 执行反射分析 | ReflectionEngine, MemoryEngine |
| **Consolidate** | 发现并合并重复、相似或可聚合的 Memory | ReflectionEngine, MemoryEngine, EntityEngine |
| **Summarize** | 生成更高层级的长期记忆 | ReflectionEngine, MemoryEngine |
| **Evaluate** | 重新评估已有 Memory（Importance / Confidence / Freshness / Archive Candidate） | ReflectionEngine, MemoryEngine |

### 4.2 为什么不超过四个 Capability

Capability 应该对应**用户或系统可理解的领域能力**，而不是内部算法。

例如：
- `mergeMemory()` / `updateImportance()` / `archiveMemory()` 是**实现动作**（Implementation Action），不是领域能力
- `reflect()` / `summarize()` / `evaluate()` / `consolidate()` 是**领域能力**

调用方表达的是："我要执行 Reflection"，而不是"我要修改数据库中的某个字段"。

---

## 5. Public API Family

### 5.1 设计原则

遵循 **One Capability, One Public API Family**（G-001）和 **Consumer-Agnostic Interface**（G-003）。

| Capability | Public API Family | 说明 |
|------------|-------------------|------|
| Reflect | `reflect*` | 执行反射分析 |
| Consolidate | `consolidate*` | 整合重复/相似 Memory |
| Summarize | `summarize*` | 生成高层级记忆 |
| Evaluate | `evaluate*` | 重新评估已有 Memory |

### 5.2 返回结果模型

ReflectionService 返回 **ReflectionExecutionResult**，属于执行报告（Execution Report），不是业务数据。

```
ReflectionExecutionResult
├── Status (SUCCESS / FAILED / SUSPENDED)
├── Statistics
│   ├── GeneratedMemoryCount
│   ├── UpdatedMemoryCount
│   ├── ArchivedMemoryCount
│   └── FailedSteps[]
├── Execution Metadata
│   ├── Duration
│   ├── Scope
│   └── Policy
└── Optional JobId
```

**真正的业务数据**（新生成的 Memory、更新的 Entity 等）全部通过 **QueryService** 读取。

> **QueryService is the canonical read interface for all persisted domain state.**

### 5.3 命令返回执行信息

Reflection 本质上是 **Command Capability**，遵循 **Command Returns Identity** 原则：
- **Command** 返回执行信息（ReflectionExecutionResult 或 JobId）
- **真正的数据状态**通过 QueryService 获取

---

## 6. Service → Engine Orchestration

### 6.1 编排关系

ReflectionService 作为 Capability Orchestrator，协调多个共享 Domain Engine：

```
ReflectionService
        │
        ├── ReflectionEngine
        │       ↓
        │   Generated Memory Proposal
        │
        ├── MemoryEngine
        │       ↓
        │   Validate / Lifecycle / Persist
        │
        ├── EntityEngine
        │       ↓
        │   Update Entity / Relation / Graph
        │
        └── ArchiveEngine
                ↓
            Archive Decision Execution
```

### 6.2 共享 Engine 原则

ReflectionService 协调共享 Domain Engine 来演化 Memory。它从不调用其他 Application Service。

| Engine | ReflectionService 可调用 | 原因 |
|--------|------------------------|------|
| ReflectionEngine | ✅ 必须 | Reflection 核心算法 |
| MemoryEngine | ✅ 必须 | 创建新的 Summary Memory、更新 Memory 生命周期 |
| EntityEngine | ✅ 必须 | 更新 Entity、Relation、Graph |
| ArchiveEngine | ✅ 可选 | Reflection 可能产生 Archive Decision |
| QueryEngine | ❌ 不调用 | Query 属于读取能力，Reflection 需要的是原始领域数据，不是 Projection |

### 6.3 Engine 使用规则

> **ReflectionService coordinates Domain Engines only. It does not depend on QueryEngine for domain analysis.**

原因：
- QueryEngine 面向读取视图（Read Model）
- ReflectionEngine 面向领域分析（Domain Model）
- 两者职责保持独立

---

## 7. Reflection Pipeline

### 7.1 Pipeline 抽象阶段

```
Select Scope
    ↓
Collect Candidate Memories
    ↓
Analyze Evidence
    ↓
Generate Reflection
    ↓
Validate Reflection
    ↓
Persist Higher-level Memory
    ↓
Link Evidence Chain
    ↓
Propagate Upward (if necessary)
    ↓
Emit Execution Log
```

### 7.2 Pipeline 关键步骤说明

| 步骤 | 职责 | 产出 |
|------|------|------|
| Select Scope | 确定 Reflection 的范围、目标层级、策略 | ReflectionScope |
| Collect Candidate Memories | 收集候选 Memory（从 Repository） | Candidate Memory Set |
| Analyze Evidence | 分析证据链完整性、证据密度 | Evidence Analysis |
| Generate Reflection | 生成 Candidate Memory | GeneratedMemoryProposal |
| Validate Reflection | 验证证据是否充分、是否已有相同高层 Memory、是否达到生成阈值 | Validation Result |
| Persist Higher-level Memory | 通过 MemoryEngine 持久化 | Persisted Memory |
| Link Evidence Chain | 建立完整的证据链接 | Evidence Chain |
| Propagate Upward | 增量向上传播（仅当本层变化足以影响上层时） | Upward Propagation Result |
| Emit Execution Log | 输出执行报告 | ReflectionExecutionResult |

### 7.3 Semantic Evolution Decision

每次 Reflection 得到一个 Candidate Memory 后，不是立即写入，而是先回答：**这个 Candidate 与 Memory Pyramid 中已有 Memory 的关系是什么？**

| 操作 | 条件 | 行为 |
|------|------|------|
| **Create** | 语义空间中不存在 | 创建新的高层 Memory |
| **Strengthen** | 语义一致，证据增加 | 增加 Evidence、更新 Confidence / Freshness，不创建新节点 |
| **Refine** | 主体相同，描述更准确 | Memory 内容更新，Evidence 增加 |
| **Split** | 原 Memory 过于宽泛 | 分解为多条更精确的 Memory，原 Memory 归档 |

### 7.4 Evidence Completeness Constraint

> **Every synthesized memory must maintain at least one valid evidence path to lower-level memories. A synthesized memory without evidence lineage is invalid.**

注意：
- 强调的是**至少一条有效路径（Path）**，不是必须直接连接 L0
- L3 → L2 → L1 → L0 已经满足

### 7.5 最终产物

Reflection Pipeline 的最终产物是：
- **一条新的 Memory** + **一条完整的 Evidence Chain**

Reflection 的工作直到 Evidence Chain 建立完成才算结束。

---

## 8. Trigger Model

### 8.1 Trigger Type

| 类型 | 说明 | 示例 |
|------|------|------|
| **Event Trigger** | 事件触发 | 新增大量 Memory、导入文档完成、长聊天结束 |
| **Schedule Trigger** | 定时触发 | 每日/每周/每月 Reflection |
| **Manual Trigger** | 人工触发 | 用户主动请求总结 |
| **System Trigger** | 系统触发 | Archive 完成、Entity Merge 完成 |

### 8.2 Trigger 职责边界

> **Trigger 负责决定"什么时候开始"，绝不决定"怎么 Reflection"。**

```
Schedule / Event / Manual / System
    ↓
ReflectionService
    ↓
Reflection Pipeline
```

### 8.3 Target Level

由于 Memory Pyramid 是多层的，Trigger 应携带 **目标层级（Target Level）**：

| Trigger | Target Level |
|---------|-------------|
| Daily Schedule | L1 |
| Weekly Schedule | L2 |
| Monthly Schedule | L3 |

这样 ReflectionService 不仅知道"开始 Reflection"，还知道"这次 Reflection 的目标是构建哪一层 Memory"。

---

## 9. Idempotency & Concurrency

### 9.1 Reflection Idempotency

Reflection 必须满足幂等性：对于**同一输入集合 + 同一 Reflection Policy + 同一目标层级**，无论执行一次还是十次，最终 Memory Pyramid 应保持一致。

### 9.2 Reflection Scope

定义 **Reflection Scope** 作为幂等性锚点：

```
Reflection Scope
├── Memory Range
├── Target Level
├── Reflection Policy
└── Version
```

只有当 Scope 发生变化时，Reflection 才真正产生新的高层 Memory。否则：更新已有 Memory，或直接返回"无需演化"。

### 9.3 Concurrency Control

> **同一 Reflection Scope 同一时刻只能有一个 Active Execution。**

- 锁的粒度是 **Reflection Scope**，不是整个 ReflectionService
- 不同 Entity、不同时间窗口、不同 Target Level 的 Reflection 仍可并行

---

## 10. Failure & Retry

### 10.1 失败模型

Reflection 执行属于一个 Reflection Cycle。如果某一周期失败：

| 失败类型 | 行为 |
|----------|------|
| **Temporary Failure** | 跳过，等待下一次 Reflection |
| **Continuous Failure** | 扩大 Reflection Scope，直到达到 Maximum Reflection Horizon |
| **Permanent Failure** | 超过 Horizon 后触发 Recovery Baseline 建议 |

**Resume 不需要**。下一次 Reflection 重新计算已积累的 Evidence 即可。

### 10.2 Maximum Reflection Horizon

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Daily | 10 天 | 连续失败超过 10 天触发警告 |
| Weekly | 8 周 | 可配置 |
| Monthly | 12 个月 | 可配置 |

> **Maximum Reflection Horizon 应保持可配置，避免硬编码值。**

### 10.3 Recovery Baseline

当超过 Maximum Reflection Horizon 时：

1. ReflectionService 向用户发出 **Recovery Baseline 建议**
2. 用户确认（同意 / 拒绝 / 配置 Recovery Policy）
3. 用户与系统的交互本身成为合法的 L0 证据
4. 后续 Reflection 基于新的 L0 继续演化

### 10.4 Recovery Policy

支持可配置的 Recovery Policy：

| Policy | 行为 |
|--------|------|
| **Always Approve** | 自动执行 Recovery Baseline |
| **Always Ask** | 每次询问用户 |
| **Always Reject** | 拒绝执行 |

> **The system never creates L0 memories autonomously. Any recovery baseline must originate from explicit user interaction, thereby remaining evidence-based.**

无论用户同意还是拒绝，都会产生新的 L0（用户与系统的交互记录），但这**不是 Hub 自主创建的**，而是用户参与的真实交互。

### 10.5 L0 Protection

ReflectionService **必须 NEVER 自主创建 L0 Memory**。Recovery Baseline 必须源于用户交互或用户预授权的用户策略。

### 10.6 Reflection Transaction

Reflection 应逻辑原子：
- 高层 Memory 在 **生成 → 验证 → 持久化 → 证据链接** 全部成功后才视为提交
- 一致性优先于完成率
- 如果证据链建立失败，回滚高层 Memory

---

## 11. Memory Pyramid Consistency

### 11.1 Memory Pyramid 维护者

Reflection 的目标不仅是**生成高层 Memory**，还包括**维护 Memory Pyramid 质量**。

Reflection 的输出不仅是"新增"，还包括：
- 新增（Create）
- 强化（Strengthen）
- 修正（Refine）
- 降低置信度（Weaken）
- 分裂（Split）

### 11.2 层级职责

| 层级 | 保存内容 | 特性 |
|------|----------|------|
| L0 | 历史事实（Historical Facts） | 持续增长，永不修改 |
| L1 | 主题知识（Topic Knowledge） | 当前最佳知识，持续更新 |
| L2 | 跨主题模式（Cross-topic Pattern） | 当前最佳知识，持续更新 |
| L3 | 一般原则（General Principle） | 当前最佳知识，持续更新 |

### 11.3 证据链追溯

任何高层 Memory 都可沿 Evidence Chain 追溯到 L0 原始事实：

```
L3 "用户工作中偏向先建立整体框架，再逐步细化实现。"
  ↓ Supported By
L2 "过去半年有 23 次先讨论架构再进入编码"
  ↓ Supported By
L1 "2026 年 6 月完成 Phase A 后开始 Phase B"
  ↓ Supported By
L0 聊天记录 / Git Commit / 设计文档
```

---

## 12. Service Collaboration Matrix

### 12.1 Service → Service 交互

| Caller | Callee | Allowed | Interaction Pattern | Reason | Architecture Rule |
|--------|--------|---------|---------------------|--------|-------------------|
| ReflectionService | MemoryEngine | ✅ | Orchestrate | 创建/更新高层 Memory | Shared Domain Engine Principle |
| ReflectionService | EntityEngine | ✅ | Orchestrate | 更新 Entity/Relation | Shared Domain Engine Principle |
| ReflectionService | ArchiveEngine | ✅ | Orchestrate | 执行归档决策 | Shared Domain Engine Principle |
| ReflectionService | QueryEngine | ❌ | Forbidden | QueryEngine 面向读取视图 | Engine 职责隔离 |
| ReflectionService | MemoryService | ❌ | Forbidden | Service Independence Principle | G-005 |
| ReflectionService | QueryService | ❌ | Forbidden | Service Independence Principle | G-005 |

### 12.2 Service → Engine 交互

| Caller | Callee | Allowed | Interaction Pattern | Reason | Architecture Rule |
|--------|--------|---------|---------------------|--------|-------------------|
| ReflectionService | ReflectionEngine | ✅ | Orchestrate | Reflection 核心算法 | Domain Engine Principle |
| ReflectionService | MemoryEngine | ✅ | Orchestrate | Memory 生命周期 | Shared Domain Engine Principle |
| ReflectionService | EntityEngine | ✅ | Orchestrate | Entity/Relation 更新 | Shared Domain Engine Principle |
| ReflectionService | ArchiveEngine | ✅ | Orchestrate | 归档决策执行 | Shared Domain Engine Principle |

### 12.3 Forbidden Dependencies

| Forbidden | Reason |
|-----------|--------|
| ReflectionService → MemoryService | Service Independence Principle (G-005) |
| ReflectionService → QueryService | Service Independence Principle (G-005) |
| ReflectionService → QueryEngine | QueryEngine 面向读取视图，Reflection 需要原始领域数据 |
| ReflectionService → 自主创建 L0 | L0 Protection Principle |

---

## 13. Consistency Principles

### 13.1 Consistency First

> **Memory Pyramid Consistency takes precedence over Reflection completion.**

如果持久化成功但证据链建立失败，应回滚高层 Memory。宁可不要这条 Memory，也不能有一条孤儿 Memory。

### 13.2 No Orphan Memory

> **A synthesized memory is not considered committed until its Evidence Chain has been successfully established.**

### 13.3 Propagation Barrier

> **Upward propagation must stop immediately when a lower-level Reflection fails.**

如果 L2 更新失败，L3 不允许继续生成，因为 L2 还不是 Current Best Knowledge。

### 13.4 Retry Policy

> **Retry resumes the interrupted step, not regenerating Candidate Memory.**

重试使用第一次 Reflection 的 Candidate、Scope、Policy，继续执行未完成的工作。

---

## 14. Future Evolution

### 14.1 Planned Evolution

| 方向 | 说明 |
|------|------|
| **Multi-Strategy Reflection** | 不同 Reflection Policy（Daily / Weekly / Project / Personality）可使用不同策略，ReflectionService 不关心实现 |
| **Incremental Reflection Optimization** | 进一步优化增量传播算法，减少不必要的上层 Reflection |

### 14.2 Potential Evolution

| 方向 | 说明 |
|------|------|
| **User Feedback Driven Reflection** | 用户反馈作为新 Evidence 纳入 Reflection 分析 |
| **Knowledge Conflict Resolution** | 当证据相互矛盾时，ReflectionEngine 独立处理冲突 |

### 14.3 ReflectionEngine 演进

> ReflectionEngine 可能在未来版本中演进为更通用的 **Knowledge Evolution Engine**，同时保持向后兼容。

---

## 15. Checklist

### 15.1 P0 — 必须完成

| # | 检查项 | 状态 |
|---|--------|------|
| P0-1 | **Side-Effect Free Query** | ReflectionService 是写编排服务，不涉及查询 |
| P0-2 | **Service → Service 检查** | 无 Service 互调，仅编排 Engine |
| P0-3 | **Engine DAG 清晰** | ReflectionEngine → MemoryEngine → EntityEngine → ArchiveEngine |
| P0-4 | **Service DAG 无循环** | ReflectionService 不依赖其他 Service |
| P0-5 | **Consumer-Agnostic Interface** | Public API 面向能力，不面向调用方 |
| P0-6 | **Stable Result Contract** | ReflectionExecutionResult 统一模型 |
| P0-7 | **Public API Family** | reflect* / consolidate* / summarize* / evaluate* |
| P0-8 | **Semantic Evolution Decision** | Create / Strengthen / Refine / Split |
| P0-9 | **Evidence Completeness Constraint** | 每条高层 Memory 必须有证据链 |
| P0-10 | **L0 Protection** | ReflectionService 绝不自主创建 L0 |
| P0-11 | **Maximum Reflection Horizon** | 可配置，超限触发 Recovery Baseline |
| P0-12 | **Incremental Propagation** | 先更新本层，再决定是否向上传播 |

### 15.2 P1 — 推荐实现

| # | 检查项 | 状态 |
|---|--------|------|
| P1-1 | **Idempotency** | 同一 Scope 不重复生成高层 Memory |
| P1-2 | **Concurrency Control** | 基于 Reflection Scope 的并发控制 |
| P1-3 | **Reflection Execution Log** | 执行日志用于可观测性 |
| P1-4 | **Semantic Similarity Optimization** | 语义相似度优化减少重复 |
| P1-5 | **Confidence Update Strategy** | Confidence 更新策略 |

### 15.3 P2 — 未来演进

| # | 检查项 | 状态 |
|---|--------|------|
| P2-1 | **Multi-Strategy Reflection** | 不同策略支持 |
| P2-2 | **User Feedback Driven** | 用户反馈驱动 |
| P2-3 | **Knowledge Conflict Resolution** | 知识冲突解决 |

### 15.4 ADR Impact Check

| 影响 | 说明 |
|------|------|
| **01_MemoryHub_Foundation** | 补充 Memory Pyramid 抽象层级定义 |
| **04_Schema_Archive_Reflect** | 明确 Reflection 产生的是更高层级的 Memory |
| **05_MemoryLifecycle_ReflectionEngine** | 对齐 Reflection 与 Memory Lifecycle 的关系 |
| **10_2_Implementation_MemoryService** | 新增与 10_4 的交叉引用（Service Independence、Shared Domain Engine） |
| **10_3_Implementation_QueryService** | 补充 QueryService 为所有持久化领域状态的唯一读接口 |
| **13_Architecture_Guidelines** | 新增 G-020~G-022 |

---

## 16. Decision Summary

| # | 决策 | 说明 | 来源 |
|---|------|------|------|
| 1 | **ReflectionService 定位** | 不是摘要生成器，是 Memory Pyramid 演化编排服务 | 10_4 §2 |
| 2 | **Reflection Is Evolution, Not Mutation** | Reflection 产生领域决策，由 Engine 完成实际变更 | 10_4 §3.1 |
| 3 | **Memory Pyramid 抽象基于解释范围（Scope）** | 不是按时间，而是按 What→Meaning→Pattern→Principle | 10_4 §3.3 |
| 4 | **Reflection 目标：提升解释力** | 不是保存快照，而是持续改进高层 Memory 的解释能力 | 10_4 §3.4 |
| 5 | **同层语义唯一** | 同一抽象层级内，同一语义空间只有一个有效 Memory | 10_4 §3.5 |
| 6 | **增量传播** | 先更新本层，再决定是否向上传播 | 10_4 §3.6 |
| 7 | **四大 Capability** | Reflect / Consolidate / Summarize / Evaluate | 10_4 §4 |
| 8 | **Public API Family** | reflect* / consolidate* / summarize* / evaluate* | 10_4 §5 |
| 9 | **ReflectionExecutionResult 是执行报告** | 不是业务数据，业务数据走 QueryService | 10_4 §5.2 |
| 10 | **QueryService 是持久化领域状态的唯一读接口** | 所有 Memory 通过 QueryService 读取 | 10_4 §5.2 |
| 11 | **共享 Engine 编排** | 协调 ReflectionEngine/MemoryEngine/EntityEngine/ArchiveEngine | 10_4 §6 |
| 12 | **不调用 QueryEngine** | Reflection 需要原始领域数据，不是 Projection | 10_4 §6.3 |
| 13 | **Semantic Evolution Decision** | Create / Strengthen / Refine / Split | 10_4 §7.2 |
| 14 | **Evidence Completeness Constraint** | 每条高层 Memory 必须有完整证据链 | 10_4 §7.4 |
| 15 | **Trigger 四类** | Event / Schedule / Manual / System | 10_4 §8 |
| 16 | **Trigger 携带 Target Level** | 决定 Reflection 的目标抽象层级 | 10_4 §8.3 |
| 17 | **幂等性 + Scope 锁** | 同一 Scope 同一时刻仅一个执行 | 10_4 §9 |
| 18 | **Failure 跳过不 Resume** | 等待下一周期重新计算已积累 Evidence | 10_4 §10.1 |
| 19 | **Maximum Reflection Horizon** | 可配置，默认 Daily 10 天 | 10_4 §10.2 |
| 20 | **Recovery Baseline 源于用户交互** | 系统绝不自主创建 L0 | 10_4 §10.3~10.5 |
| 21 | **Recovery Policy** | Always Approve / Always Ask / Always Reject | 10_4 §10.4 |
| 22 | **Reflection Transaction** | 逻辑原子，一致性优先 | 10_4 §10.6 |
| 23 | **Propagation Barrier** | 下层失败，上层立即停止传播 | 10_4 §13.3 |
| 24 | **Retry 不再生成 Candidate** | 使用第一次的 Candidate 继续执行 | 10_4 §13.4 |
| 25 | **ADR Impact Check** | 需回溯更新 01/04/05/10_2/10_3/13 | 10_4 §15.4 |

---

## 17. Backport Updates

完成 10_4 后，需要同步更新以下文档：

| 文档 | 更新内容 |
|------|----------|
| **01_MemoryHub_Foundation** | 补充 Memory Pyramid 抽象层级定义（L0~L3 的解释范围） |
| **04_Schema_Archive_Reflect** | 明确 Reflection 产生的是更高层级的 Memory，不是新对象类型 |
| **05_MemoryLifecycle_ReflectionEngine** | 对齐 Reflection 与 Memory Lifecycle 的关系 |
| **10_2_Implementation_MemoryService** | 新增与 10_4 的交叉引用（Service Independence、Shared Domain Engine、Semantic Uniqueness） |
| **10_3_Implementation_QueryService** | 补充 QueryService 为所有持久化领域状态的唯一读接口 |
| **13_Architecture_Guidelines** | 新增 G-020~G-022 |

---

## 18. Version Record

| 版本 | 日期 | 变更 | 状态 |
|------|------|------|------|
| 1.0 | 2026-06-28 | 初始版本，确认 ReflectionService 全部设计要素 | ✅ 已确认 |
| 1.1 | 2026-06-28 | Phase B-4 修订：(1) Memory Pyramid 抽象层级定义 (2) Evidence Completeness Constraint (3) Recovery Baseline 与 L0 Protection (4) 回溯更新 10_2/10_3/13 | ✅ 已确认 |
