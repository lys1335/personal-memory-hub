# Change Report 10_5 — Phase B EntityService Design

> **日期**: 2026-06-28
> **阶段**: Phase B — 实现设计（第五部分）
> **触发原因**: Phase B-5 开始，定义 EntityService 的工程实现设计
> **生成文档**: 10_5_Implementation_EntityService.md

---

## 1. 变更概述

本次变更完成 Phase B-5 EntityService 的设计，定义了 Memory Hub 的身份管理服务。

核心设计决策：

1. EntityService 是 Identity Management 的能力所有者
2. 五个 Capability 组：Identity / Merge / Alias / Relationship / Profile Update
3. EntityID 稳定不变，属性通过证据演化
4. 异步 Reference Migration（非运行时 Canonical Resolution）
5. 三态生命周期：Created → Active → Merged
6. Domain Events 发布已完成业务事实
7. Task Runtime 执行异步维护
8. 每个 Entity 必须有 L0 Memory 支持
9. 不引入 Entity 版本
10. Entity 始终是 Current Best Identity

---

## 2. 生成文档

### 2.1 10_5_Implementation_EntityService.md

| 章节 | 内容 |
|------|------|
| §1 Purpose | EntityService 定位声明 |
| §2 Responsibility | 核心定位、明确禁止、正确定位 |
| §3 Entity Philosophy | Identity Evolution、Human-like Evolution、Preservation First、Memory Fact ≠ Entity Reference |
| §4 Capability Boundary | 五大 Capability 组、One Capability One Implementation |
| §5 Service → Engine Orchestration | 编排关系图、共享 Engine 原则、领域不变量归属 |
| §6 Repository Boundary | EntityRepository Persistence Only |
| §7 Entity Merge Strategy | Asynchronous Reference Migration、Query-first 理由 |
| §8 Lifecycle | Created → Active → Merged、移除状态说明 |
| §9 Domain Events | 7 个事件清单、Events = Completed Facts、Task Runtime 集成 |
| §10 Service Collaboration | 完整交互矩阵、Forbidden Dependencies |
| §11 Consistency Principles | EntityID Stability、Evidence-Based Entity、Current Best Identity、No Entity Version |
| §12 Future Evolution | Planned + Potential（Suppression/Escape、Progressive Recall） |
| §13 Checklist | P0/P1/P2 检查项 |
| §14 Decision Summary | 25 项决策汇总 |

### 2.2 12_Architecture_Decisions.md（新建）

新增 ADR-005~010，其中 ADR-006/007/008 详细记录了 Entity Merge Strategy、No Entity Version、EntityID Stability。

---

## 3. 回溯更新

| 文档 | 更新内容 |
|------|----------|
| **03_Entity_MemoryGraph** | 补充 Entity Lifecycle 定义（Created → Active → Merged） |
| **06_Runtime_Architecture** | 补充 EntityEngine / RelationshipEngine 到 Engine 清单（#7/#8） |
| **08_Implementation_Architecture** | 新增 17.11 EntityRepository Persistence Only |
| **10_1_Implementation_Service_Layer** | 新增 EntityEngine（#12）到 Engine 清单；新增 EntityService 到 Service Collaboration Matrix；新增 EntityService 到 Service DAG / Engine DAG；Decision Summary 补充 35~38；版本 1.2→1.3 |
| **10_2_Implementation_MemoryService** | 版本 1.2→1.3，补充编排 EntityEngine 的角色 |
| **10_3_Implementation_QueryService** | 版本 1.1→1.2，补充消费 Entity 信息但不拥有 Entity 状态 |
| **10_4_Implementation_ReflectionService** | 补充与 EntityService 的协作关系（ReflectionService 可推断身份演化，但只有 EntityService 可执行身份修改） |
| **13_Architecture_Guidelines** | 新增 G-024~G-038（共 15 条），总数 22→38 |
| **README.md** | 补充 EntityService（10_5）到 Phase B 进度列表 |
| **INDEX.md** | 补充 10_5 条目，进度 14/14→15/15 |

---

## 4. 架构影响分析

### 4.1 新增组件

| 组件 | 类型 | 说明 |
|------|------|------|
| EntityService | Domain Service | Identity Management 能力所有者 |
| EntityEngine | Domain Engine | 身份管理核心算法 |
| EntityQueryRepository | Repository | Entity 图查询 |

### 4.2 变更组件

| 组件 | 变更 | 说明 |
|------|------|------|
| MemoryService | 新增编排 EntityEngine | 在创建 Memory 时解析 Entity |
| ReflectionService | 新增推断身份演化 | 可产生 merge 建议，但不可执行 |
| QueryService | 新增消费 Entity 信息 | 不拥有 Entity 状态 |
| TaskRuntime | 新增异步维护 | Reference Migration / Graph Maintenance |

### 4.3 不变组件

| 组件 | 说明 |
|------|------|
| Service Independence Principle（G-005） | 保持不变 |
| Shared Domain Engine Principle（G-006） | 保持不变 |
| Command/Query Separation（G-008） | 保持不变 |
| 数据库 Schema | EntityService 不引入新表 |

---

## 5. 向后兼容性

| 变更 | 是否向后兼容 | 说明 |
|------|-------------|------|
| 03 补充 Entity Lifecycle | ✅ | 新增不修改已有 |
| 06 补充 Engine 清单 | ✅ | 新增不修改已有 |
| 08 新增 17.11 约束 | ✅ | 仅补充说明 |
| 10_1 补充 EntityService + EntityEngine | ✅ | 新增不修改已有 |
| 10_2 版本更新 | ✅ | 仅补充交叉引用 |
| 10_3 版本更新 | ✅ | 仅补充交叉引用 |
| 10_4 补充协作关系 | ✅ | 仅补充交叉引用 |
| 12 新增 ADR | ✅ | 新建文件 |
| 13 新增 15 条 Guideline | ✅ | 新增不修改已有 |
| README/INDEX 更新 | ✅ | 进度更新 |

---

## 6. ADR Impact

### 6.1 新增 ADR

| ADR | 主题 | 关键决策 |
|-----|------|----------|
| ADR-005 | Query-First Architecture | Query 是高频率操作，Merge 是低频率操作 |
| ADR-006 | Entity Merge Strategy | 采用异步 Reference Migration，不做运行时 Canonical Resolution |
| ADR-007 | No Entity Version | Entity 历史通过 L0 + Evidence Chain + Domain Events 自然存在 |
| ADR-008 | EntityID Stability | EntityID 是 Identity 的稳定锚点，永不改变 |
| ADR-009 | Service Independence | 跨服务同步调用禁止 |
| ADR-010 | Shared Domain Engine | 一个 Service 可编排多个 Domain Engine |

---

*本报告仅记录 Phase B-5 的变更，不涉及其他阶段的架构修改。*
