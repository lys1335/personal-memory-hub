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
| ADR-010 | Shared Domain Engine | 一个 Service 可编排多个 Domain Engine | 10_5 |

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

---

*本文档是 Phase B 的 ADR 集合。每个 ADR 都链接到具体的实现文档。*
