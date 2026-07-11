# Personal AI Memory Hub — Architecture Decision Records

> **版本**: 1.0
> **日期**: 2026-06-28
> **阶段**: Phase B
> **状态**: 已确认
> **作者**: 系统架构组

---

## ADR Catalog

| ADR | 主题 | 决策 | 来源 |
|-----|------|------|------|
| ADR-001 | Entity 准入标准 | Entity = Observations + Beliefs + Current State → MemoryNode (L1-L4) + Relationship | 03 |
| ADR-002 | Entity 数量控制 | 基于证据密度的自动判定，不是人工设定上限 | 03 |
| ADR-003 | Reflection 可解释 | Reflection 产生更高层级 Memory，不是新对象类型 | 04 |
| ADR-004 | Memory 不可变 | Memory 不可删除，只有 Archive | 05 |
| ADR-005 | Query-First Architecture | Query 是高频率操作，Merge 是低频率操作 | 10_5 |
| ADR-006 | Entity Merge Strategy | 采用异步 Reference Migration，不做运行时 Canonical Resolution | 10_5 |
| ADR-007 | No Entity Version | Entity 历史通过 L0 + Evidence Chain + Domain Events 自然存在 | 10_5 |
| ADR-008 | EntityID Stability | EntityID 是 Identity 的稳定锚点，永不改变 | 10_5 |
| ADR-009 | Service Independence | 跨服务同步调用禁止 | 10_3 |
|| ADR-010 | Shared Domain Engine | 一个 Service 可编排多个 Domain Engine | 10_5 |
|| ADR-011 | Entity Permanence | Entity 永久存在，不可删除/销毁/恢复 | 10_5 |
|| ADR-012 | Identity Consolidation | Merge 重定义为 Identity Consolidation，不代表真实世界演化 | 10_5 |
|| ADR-013 | Metadata Update | Rename 重定义为 Metadata Update，只更新元数据 | 10_5 |
|| ADR-014 | Memory Reference Immutability | Memory 引用不可变，Consolidation 不重写历史引用 | 10_5 |
|| ADR-015 | QueryService Resolution | QueryService 执行 Alias/Canonical/Merge-Graph 解析 | 10_5 |
|| ADR-016 | Reflection Proposal Only | ReflectionService 仅产生 Entity Evolution Proposals，不直接修改 Entity | 10_4 |
|| ADR-017 | Proposal-Task Separation | Proposal 和 Task 是独立概念 | 10_4 |
|| ADR-018 | Entity Transaction Scope | Entity 事务仅修改 Entity/Metadata/Relationship，不碰 Observation/Memory/Evidence | 10_5 |

---

## ADR-006: Entity Merge Strategy

**日期**: 2026-06-28
**状态**: Final Decision
**主题**: Entity Merge 采用异步 Reference Migration

### Context

Memory Hub 是 Query-first 架构。Query 是高频率操作，Entity Merge 是低频率操作。

### Decision

Entity Merge 采用异步 Reference Migration 架构：

1. EntityService 执行合并操作
2. 合并成功后发布 `EntityMerged` Domain Event
3. Task Runtime 异步执行：
   - Reference Migration
   - Relationship Update
   - Index Rebuild
   - Audit

### Consequences

| 正面 | 负面 |
|------|------|
| Query 路径保持简单 | Merge 结果有短暂延迟 |
| 在线事务不受后台维护影响 | 需要 Task Runtime 基础设施 |
| 低频率操作不阻塞高频率操作 | 最终一致性，非强一致性 |

### References

* 10_5 §7
* 10_5 §9.3
* G-027, G-034, G-035

---

## ADR-007: No Entity Version

**日期**: 2026-06-28
**状态**: Final Decision
**主题**: 不引入 Entity 版本

### Context

Entity 的历史信息是否需要独立的版本表？

### Decision

不引入 Entity 版本。理由：

| 机制 | 覆盖内容 |
|------|----------|
| L0 Memory | 原始观察记录 |
| Evidence Chain | 证据追溯链 |
| Domain Events | 所有变更事件 |
| Audit | 操作轨迹 |

Entity 仅代表 Current Best Identity。历史重建应始终依赖证据，而非重复的版本表。

### References

* 10_5 §11.4
* G-033

---

## ADR-008: EntityID Stability

**日期**: 2026-06-28
**状态**: Final Decision
**主题**: EntityID 永不改变

### Context

Entity 的属性（Canonical Name、Alias、Metadata、Relationships、Type）会随证据积累而演化。EntityID 是否也应该随之变化？

### Decision

EntityID 是 Identity 的稳定锚点，永不改变。所有演化通过证据驱动的 Attribute 更新完成。

### References

* 10_5 §3.1
* G-024

---

## ADR-011: Entity Permanence

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: Entity 永久存在，不可删除/销毁/恢复

### Context

Entity 是否有删除、销毁或恢复的生命周期状态？

### Decision

Entity 一旦创建即永久存在。不存在删除、销毁或恢复操作。理由：

| 考量 | 说明 |
|------|------|
| Entity 是 Identity 锚点 | EntityID 是稳定的语义标识 |
| Memory 事实不可变 | Memory 保留原始 Entity 引用 |
| 历史重建依赖证据 | L0 Memory + Evidence Chain 提供历史 |
| Identity Evolution 重组语义 | 不是删除历史，而是更新当前最佳身份 |

### Consequences

|| 正面 | 负面 ||
||------|------||
|| 简化架构，无删除/恢复逻辑 | 需要处理"过时"实体的查询策略 ||
|| Memory 引用始终有效 | 存储持续增长（但 Entity 数量相对有限） ||

### References

* 10_5 §8.1
* G-028

---

## ADR-012: Identity Consolidation

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: Merge 重定义为 Identity Consolidation

### Context

"Merge" 是否代表真实世界的演化？

### Decision

Merge 重定义为 **Identity Consolidation**。它是身份层面的合并，不代表真实世界的演化。

### Consequences

- Identity Consolidation 更新引用图，不修改 L0 事实
- Memory 引用不可变，永远不重写
- 只有 Memory 的语义组织发生变化

### References

* 10_5 §7.1

---

## ADR-013: Metadata Update

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: Rename 重定义为 Metadata Update

### Context

"Rename" 是否改变 Entity 身份？

### Decision

Rename 重定义为 **Metadata Update**。只更新元数据（Canonical Name、Alias 列表等），不改变 Entity 身份。

### References

* 10_5 §7.2

---

## ADR-014: Memory Reference Immutability

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: Memory 引用不可变

### Context

Entity Consolidation 是否应该重写历史 Memory 的 Entity 引用？

### Decision

Memory 引用是不可变的。Entity Consolidation 不重写历史 Memory 引用。

| 概念 | 说明 |
|------|------|
| **Memory Fact** | 原始事实记录，保存在 L0，不可变 |
| **Entity Reference** | 对 Memory Fact 的语义组织索引 |

Reference Graph Update 是 Index Maintenance，不是历史修改。

### Consequences

|| 正面 | 负面 ||
||------|------||
|| 历史引用始终一致 | Consolidation 后需要通过 Merge Graph Expansion 在查询时整合 ||
|| Memory 事实不可篡改 | 查询复杂度增加（需要展开合并图） ||

### References

* 10_5 §3.4
* G-037

---

## ADR-015: QueryService Resolution

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: QueryService 执行 Alias/Canonical/Merge-Graph 解析

### Context

Alias Resolution、Canonical Resolution 和 Merge Graph Expansion 应该在 Service 层还是 Query 层？

### Decision

QueryService 负责：

- **Alias Resolution**：将别名解析为当前 Canonical EntityID
- **Canonical Resolution**：将 Canonical Name 解析为 EntityID
- **Merge Graph Expansion**：在查询时展开合并图，将已合并 Entity 的相关 Memory 纳入结果

### References

* 10_5 §3.5

---

## ADR-016: Reflection Proposal Only

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: ReflectionService 仅产生 Entity Evolution Proposals

### Context

ReflectionService 是否可以直接修改 Entity？

### Decision

ReflectionService 仅产生 **Entity Evolution Proposals**。Reflection 不直接修改 Entity。

- Proposal = 业务建议
- 只有 EntityService 可执行身份修改
- Proposal 可以立即执行、通过 Task 执行、或通过其他未来工作流执行

### References

* 10_4 §14.6
* 10_5 §11.6

---

## ADR-017: Proposal-Task Separation

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: Proposal 和 Task 是独立概念

### Context

Proposal 执行是否必须经过 Task？

### Decision

Proposal 和 Task 是独立概念：

| 概念 | 说明 |
|------|------|
| **Proposal** | 业务建议（如 Reflection 产生的 Entity Evolution Proposal） |
| **Task** | 执行调度（TaskService 负责） |

Proposal 可以：
- 立即执行
- 通过 Task 执行
- 通过其他未来工作流执行

人工审查是可选的，不是默认架构。

### References

* 10_4 §14.6
* 10_5 §11.6

---

## ADR-018: Entity Transaction Scope

**日期**: 2026-07-11
**状态**: Final Decision
**主题**: Entity 事务仅修改 Entity/Metadata/Relationship

### Context

Entity 事务是否可以修改 Observation、Memory 或 Evidence？

### Decision

Entity 事务的修改范围严格限定：

| 可修改 | 禁止修改 |
|--------|----------|
| Entity | Observation |
| Metadata | Memory |
| Relationship Graph | Evidence |

### References

* 10_5 §11.5

---

---

*本文档是 Phase B 的 ADR 集合。每个 ADR 都链接到具体的实现文档。*
