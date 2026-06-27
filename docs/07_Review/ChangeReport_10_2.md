# Change Report 10_2 — Phase B MemoryService Design

> **日期**: 2026-06-27
> **阶段**: Phase B — 实现设计（第二部分）
> **触发原因**: Phase B-2 开始，定义 MemoryService 的工程实现设计
> **生成文档**: 10_2_Implementation_MemoryService.md
> **影响文档**: 10_1_Implementation_Service_Layer.md, INDEX.md, README.md
> **变更说明**: ChangeReport_09.md 已重命名为 ChangeReport_10_1.md

---

## 1. 概述

本次变更是 Phase B 的第二份实现设计文档，聚焦 **MemoryService** 的工程实现。

核心贡献：

1. 确立了 MemoryService 作为 **Domain Service**（非 CRUD Service）的定位
2. 定义了 **Capability-Oriented API** 分组
3. 确立了 **Command / Query Separation** 原则
4. 设计了 **Batch Import** 完整能力（ImportContext、Pipeline、Parser 可扩展）
5. 引入了 **TransactionPolicy** 和 **RecoveryPolicy** 可扩展策略
6. 确立了 **Idempotent Import** 原则
7. 设计了 **Job-Oriented Execution Model**
8. 定义了 **Error Model**（统一返回模型）
9. 引入了 **Domain Events** 解耦机制
10. 建立了 **Service Collaboration Matrix** 统一规范

---

## 2. 变更清单

### 2.1 新增文档

#### 10_2_Implementation_MemoryService.md

**为什么变更**: Phase B-2 需要定义 MemoryService 的工程实现，作为后续 Service 文档的参考基准。

**变更内容**:

| 章节 | 内容 |
|------|------|
| 第 2 章 | MemoryService Responsibility — Domain Service 定位，明确禁止 CRUD 接口 |
| 第 3 章 | Capability-Oriented API — 6 大 Capability 分组（Capture/Import/Merge/Archive/Lifecycle/Restore） |
| 第 3.3 章 | Command Returns Identity, Query Returns State — 读/写分离原则 |
| 第 4 章 | Batch Import Capability — ImportContext、编排流程、Parser 可扩展设计 |
| 第 5 章 | Import Pipeline — 6 步 Pipeline + 状态机 |
| 第 6 章 | Transaction Policy — PerMemory 默认 + TransactionPolicy 可扩展 |
| 第 7 章 | Idempotent Import — Canonical Identity + Evidence 唯一性判定 |
| 第 8 章 | Failure Recovery — ContinueOnError 默认 + RecoveryPolicy 可扩展 + ImportError Collection |
| 第 9 章 | Execution Model — Job-Oriented Design，ImportJob 结构，MemoryService/TaskRuntime 职责分离 |
| 第 10 章 | Public API — 6 大 Capability 的完整方法签名 |
| 第 11 章 | Error Model — MemoryResult 统一返回模型 + 错误码约定 |
| 第 12 章 | Domain Events — 事件清单、事件结构、发布原则 |
| 第 13 章 | Service Collaboration Matrix — Phase B 统一规范 + MemoryService 矩阵 |

**影响**:
* 所有后续 10_x Service 文档必须引用本文档的 Service Collaboration Matrix 规范
* 10_1 必须同步更新以保持一致
* 代码实现必须遵循 Domain Service 原则（非 CRUD）

**跨文档一致性**: 与 10_1 的 Service 分类、Engine 清单、依赖规则完全一致。

---

### 2.2 回溯修改文档

#### 10_1_Implementation_Service_Layer.md

**为什么变更**: 10_2 发现了多个 Service 层统一原则，需要在总纲文档中同步。

**变更内容**:

| 变更 | 说明 |
|------|------|
| Service 清单更新 | MemoryService 职责从"记忆 CRUD"改为"Memory Domain Service（Capture/Import/Merge/Archive/Lifecycle）" |
| 新增 4.2.1 Domain Service 原则 | MemoryService is a Domain Service, not CRUD |
| 新增 4.2.2 Command/Query Separation | Command Returns Identity, Query Returns State |
| 新增 7.4 Service Collaboration Matrix 规范 | 每个 Service 文档必须包含 Matrix |
| Decision Summary 补充 16~22 | Domain Service、C/Q 分离、Matrix、Error Model、Events、Transaction Policy、Recovery Policy |
| 版本号 1.0 → 1.1 | 记录 Phase B-2 修订 |

**影响**: 10_1 从"仅定义分层架构"升级为"定义 Phase B 全部工程原则"。

**跨文档一致性**: 与 10_2 完全一致。

#### INDEX.md

**为什么变更**: 10_2 已生成，需要更新阅读顺序和完成状态。

**变更内容**:

| 变更 | 说明 |
|------|------|
| Phase 5 新增 10_2 | 添加 10_2_Implementation_MemoryService.md 条目 |
| Current Progress 更新 | 10/10 → 11/11 |
| Last Updated 更新 | 2026-06 → 2026-06-27 |

**影响**: 读者可通过 INDEX 了解 Phase B 已进入 MemoryService 设计阶段。

#### README.md

**为什么变更**: Phase B 进度更新。

**变更内容**:

| 变更 | 说明 |
|------|------|
| 文档列表新增 10_2 | Implementation MemoryService（Phase B-2 新增） |
| Phase B 状态更新 | 10_2 标记为 ✅ 完成，后续编号顺延 |

**影响**: 读者可通过 README 了解项目当前进度。

---

### 2.3 文件重命名

#### ChangeReport_09.md → ChangeReport_10_1.md

**为什么变更**: Phase B 采用 `10_X` 编号体系，ChangeReport 也应遵循同一体系。

**变更内容**:

| 变更 | 说明 |
|------|------|
| 文件名 | ChangeReport_09.md → ChangeReport_10_1.md |
| 标题 | Change Report 09 → Change Report 10_1 |
| 元数据 | 新增变更说明字段，记录重命名原因 |

**影响**: 所有后续 ChangeReport 遵循 `ChangeReport_10_X.md` 命名规范。

---

## 3. 新增原则

本次变更确认了以下 **Phase B 工程原则**：

| # | 原则 | 说明 | 影响范围 |
|---|------|------|----------|
| 1 | **Domain Service 原则** | MemoryService is a Domain Service, not CRUD. Public APIs organized by capability | 10_1、10_2 |
| 2 | **Capability-Oriented API** | 禁止 create()/update()/delete()/find() 等 Repository 风格接口 | 10_2 |
| 3 | **Command / Query Separation** | Command Returns Identity, Query Returns State | 10_1、10_2 |
| 4 | **Batch Import 独立 Capability** | Import 不是循环调用 storeMemory()，是独立 Use Case | 10_2 |
| 5 | **ImportContext 属于 Batch** | 不是 Memory 的属性 | 10_2 |
| 6 | **Parser 独立可扩展** | MemoryService 不负责解析不同格式 | 10_2 |
| 7 | **TransactionPolicy 可扩展** | 默认 PerMemory，未来可扩展 PerChunk/WholeBatch | 10_2 |
| 8 | **MemoryService 不负责数据库事务** | 事务由 Repository/Unit of Work 控制 | 10_2 |
| 9 | **Idempotent Import** | 重复导入不生成重复 Memory | 10_2 |
| 10 | **Continue-on-Error 默认** | 单条失败不中断 Batch | 10_2 |
| 11 | **RecoveryPolicy 可扩展** | 默认 ContinueOnError，未来可扩展 StopOnFatal/StopAfterNFailures | 10_2 |
| 12 | **ImportError Collection** | 每条失败记录结构化错误信息 | 10_2 |
| 13 | **Job-Oriented Design** | Import 面向 ImportJob，不是 Thread/HTTP Request | 10_2 |
| 14 | **MemoryService ≠ TaskRuntime** | Job 生命周期管理 vs 真正调度 | 10_2 |
| 15 | **统一 Error Model** | MemoryResult< T > 统一返回模型 | 10_2 |
| 16 | **Domain Events 解耦** | Service 间通过事件通信，不直接通知 | 10_2 |
| 17 | **Service Collaboration Matrix 规范** | 每个 Service 文档必须包含，合并形成完整 Dependency Graph | 10_1、10_2 |

---

## 4. 架构决策影响分析

### 4.1 Domain Service 定位的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 10_1 | Service 清单更新 | MemoryService 职责从 CRUD 改为 Capability |
| 10_2 | 全文档基础 | 所有 API 按 Capability 分组 |
| 02 | MemoryEngine 协调 | 确认 MemoryService 编排 MemoryEngine，不直接操作 Repository |

### 4.2 Batch Import 设计的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 10_1 | Service 职责更新 | 新增 Import Capability |
| 10_2 | 完整 Import Pipeline | ImportContext、Parser 可扩展、TransactionPolicy |
| 09 | 表结构设计 | 确认 Import 相关表（archives、archive_sources） |

### 4.3 Service Collaboration Matrix 的影响

| 受影响文档 | 影响范围 | 处理方式 |
|-----------|----------|----------|
| 10_1 | 新增 7.4 统一规范 | 定义 Matrix 格式和合并规则 |
| 10_2 | MemoryService 矩阵 | 6 行矩阵（含禁止项） |
| 10_3~10_N | 后续所有 Service | 必须包含相同格式的 Matrix |

---

## 5. 跨文档一致性验证

### 5.1 术语一致性

| 术语 | 10_1 | 10_2 | 一致? |
|------|------|------|-------|
| Domain Service | ✅ | ✅ | ✅ |
| Capability-Oriented API | ✅ | ✅ | ✅ |
| Command / Query Separation | ✅ | ✅ | ✅ |
| Batch Import | ✅ | ✅ | ✅ |
| TransactionPolicy | ✅ | ✅ | ✅ |
| RecoveryPolicy | — | ✅ | ✅ |
| ImportContext | — | ✅ | ✅ |
| Service Collaboration Matrix | ✅ | ✅ | ✅ |
| Domain Events | ✅ | ✅ | ✅ |
| MemoryResult | — | ✅ | ✅ |

### 5.2 依赖规则一致性

| 规则 | 10_1 | 10_2 | 一致? |
|------|------|------|-------|
| Service → Engine ✅ | ✅ | ✅ | ✅ |
| Service → Repository ✅ | ✅ | ✅ | ✅ |
| Engine → Repository ❌ | ✅ | ✅ | ✅ |
| Service → Service ❌ | ✅ | ✅ | ✅ |
| MemoryService → QueryService ❌ | ✅ | ✅ | ✅ |
| MemoryService → Repository ❌ | ✅ | ✅ | ✅ |

### 5.3 版本号一致性

| 文档 | 变更前 | 变更后 | 备注 |
|------|--------|--------|------|
| 10_1 | 1.0 | 1.1 | Phase B-2 修订 |
| 10_2 | — | 1.0 | 新建 |
| INDEX | 2026-06-26 | 2026-06-27 | 更新 |
| README | — | — | 更新进度 |

---

## 6. 开放问题（Open Questions）

以下问题在本次变更中未做出最终决策，留待后续文档处理：

| # | 问题 | 涉及文档 | 计划处理 |
|---|------|----------|----------|
| OQ-001 | ImportJob 的实际调度实现（线程池 vs 消息队列） | 10_6 | 待定 |
| OQ-002 | Domain Event 的实际传输机制（内存事件 vs 消息队列） | 10_1 预留 | V2+ |
| OQ-003 | Parser 的具体格式适配接口定义 | 10_3 | 待定 |
| OQ-004 | ImportError 的持久化策略（临时存储 vs 永久记录） | 10_2 | 待定 |
| OQ-005 | TransactionPolicy.PerChunk 的具体 chunk 大小 | 10_2 | V2+ |

---

## 7. 变更总结

本次 Phase B-2 变更完成了以下核心目标：

1. **确立了 MemoryService 的 Domain Service 定位** — 不是 CRUD，是 Capability 编排
2. **设计了完整的 Batch Import 能力** — ImportContext、Pipeline、Parser 可扩展、TransactionPolicy、Idempotent、Failure Recovery
3. **确立了 Command / Query Separation 原则** — Command Returns Identity, Query Returns State
4. **设计了统一 Error Model** — MemoryResult 结构化返回
5. **引入了 Domain Events 解耦机制** — 服务间通过事件通信
6. **建立了 Service Collaboration Matrix 统一规范** — 每个 Service 文档必须包含
7. **更新了 10_1 总纲** — 同步所有新发现的 Phase B 工程原则
8. **重命名 ChangeReport_09 → ChangeReport_10_1** — 统一 Phase B 编号体系

**没有引入任何新的架构范式**。所有变更都是对 10_1 的分化和细化。

---

*本报告记录了 Phase B-2 变更的全部影响。后续 10_3~10_N 变更将参照本报告的格式。*
