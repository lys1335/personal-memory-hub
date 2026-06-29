# Personal AI Memory Hub — 10_2 Implementation MemoryService

> **版本**: 1.0
> **日期**: 2026-06-27
> **阶段**: Phase B — 实现设计（第二部分）
> **状态**: 已确认
> **作者**: 系统架构组

---

## 1. Purpose

本文档定义 **MemoryService** 的工程实现设计。

MemoryService 负责 Memory Domain 的所有写操作编排，包括：

* 单条记忆捕获（Capture）
* 批量导入（Batch Import）
* 记忆修正（Merge / Correct）
* 归档（Archive）
* 生命周期管理（Lifecycle）
* Reflection 触发（Reflection Trigger）

本文档是 Phase B 所有后续 Service 设计文档的参考基准。

---

## 2. MemoryService Responsibility

### 2.1 核心定位

> **MemoryService is a Domain Service, not an Application CRUD Service.**
> **It orchestrates Memory Domain capabilities.**
> **Its public API is organized around domain capabilities rather than persistence operations.**

MemoryService 表示 **Memory Domain**，不是 Memory CRUD。

它编排 MemoryEngine、ArchiveEngine、EvidenceEngine、RelationshipEngine 等 Domain Engine，完成记忆领域的业务逻辑。

### 2.2 明确禁止

MemoryService **不得**暴露以下接口：

| 禁止 | 原因 |
|------|------|
| `create()` | Repository 风格，不是领域能力 |
| `update()` | Memory 不可变，修正是通过 EvidenceEngine 创建新版本 |
| `delete()` | Memory 不可删除，只有 Archive |
| `find()` / `get()` | Query 职责，属于 QueryService |
| `list()` | Query 职责 |

### 2.3 正确定位

MemoryService 的公开接口按 **Capability** 组织，而非按 **持久化操作** 组织。

```
MemoryService
│
├── Capture Capability
│   ├── captureMemory()
│   └── captureConversation()
│
├── Import Capability
│   ├── importMemories()
│   ├── createImportJob()
│   ├── getImportStatus()
│   ├── cancelImport()
│   └── retryImport()
│
├── Merge Capability
│   └── mergeMemories()
│
├── Archive Capability
│   └── archiveMemory()
│
├── Lifecycle Capability
│   ├── triggerReflection()
│   ├── scheduleArchive()
│   └── reprocessMemory()
│
└── Restore Capability
    └── restoreArchivedMemory()
```

---

## 3. Capability-Oriented API

### 3.1 Capability 分组

| Capability 组 | 职责 | 编排的 Engine |
|---------------|------|--------------|
| **Capture** | 新增记忆（单条 / 会话） | MemoryEngine, EvidenceEngine |
| **Import** | 批量导入（带 Parser 适配） | MemoryEngine, ArchiveEngine |
| **Merge** | 记忆合并与修正 | MemoryEngine, EvidenceEngine, RelationshipEngine |
| **Archive** | 认知压缩归档 | ArchiveEngine |
| **Lifecycle** | 生命周期管理（Reflection 触发、重新处理） | MemoryEngine, ReflectionEngine（通过 ReflectionService） |
| **Restore** | 从归档恢复 | ArchiveEngine, MemoryEngine |

### 3.2 读/写分离原则

| Service | 职责 | 原则 |
|---------|------|------|
| **MemoryService** | 写操作（Command） | Command Returns Identity |
| **QueryService** | 读操作（Query） | Query Returns State |

MemoryService **不承担 Query 职责**。所有 Memory 数据读取统一由 QueryService 提供。

### 3.3 Command Returns Identity, Query Returns State

| 操作类型 | 返回值 | 说明 |
|----------|--------|------|
| **Command**（MemoryService） | `MemoryId` / `JobId` / `Status` / `ImportReport` | 不返回完整 Memory Entity |
| **Query**（QueryService） | `Memory` / `MemoryView` / `Context` / `Evidence` / `Entity` | 返回完整状态 |

**理由**：

* 写入后立即查询可能导致不一致（异步处理未完成）
* 统一读取路径，避免边界模糊
* 未来 MemoryEngine 增加异步处理（AI 补全、Entity 提取、Embedding）时无需调整架构

---

## 4. Batch Import Capability

### 4.1 Import 是独立 Capability

Batch Import **不是**对 `captureMemory()` 的循环调用。

历史聊天导入通常包含：

```
Chat A
 ├─ message1
 ├─ message2
 ├─ message3

Chat B
 ├─ message1
 ├─ message2
```

导入时需要保留：

* 时间顺序
* 来源（Source）
* 会话（Conversation）
* 引用关系
* Evidence

这些属于 **整个批次（Batch）** 的上下文，不是单条 Memory 能表达的。

### 4.2 ImportContext

Import 期间维护 ImportContext，属于 Batch 级别，不属于 Memory 级别：

| 字段 | 类型 | 说明 |
|------|------|------|
| `batchId` | UUID | 批次唯一标识 |
| `source` | String | 导入来源（ChatGPT / Claude / Markdown / Obsidian 等） |
| `conversationId` | String | 来源会话标识 |
| `importTime` | Instant | 导入时间 |
| `totalCount` | int | 总条目数 |
| `processedCount` | int | 已处理数 |
| `successCount` | int | 成功数 |
| `failedCount` | int | 失败数 |
| `duplicateCount` | int | 重复数 |
| `skippedCount` | int | 跳过数 |
| `currentIndex` | int | 当前处理索引 |

### 4.3 Import 编排流程

```
MemoryService.importMemories()
    ↓
Validate Import（校验文件格式、Source 合法性）
    ↓
Build Import Context（创建 ImportContext）
    ↓
Parse Batch（调用 Parser 解析为 MemoryCandidates）
    ↓
Process Memory（逐条调用 MemoryEngine.captureMemory()）
    ↓
Collect Result（收集成功/重复/跳过/失败结果）
    ↓
Generate Import Report（生成 ImportReport）
    ↓
Publish Domain Event（ImportCompleted）
```

**注意**：MemoryService 负责 Orchestration，真正的单条 Memory 创建仍交由 MemoryEngine 完成，不绕过 Engine，也不直接操作 Repository。

### 4.4 Parser 可扩展设计

MemoryService **不负责解析不同格式**。Parser 独立于 MemoryService。

支持的 Parser 来源（未来可扩展）：

| Parser | 来源 | 说明 |
|--------|------|------|
| ChatGPT Parser | ChatGPT 导出 | JSON / Markdown |
| Claude Parser | Claude 导出 | JSON |
| Gemini Parser | Gemini 导出 | JSON |
| Markdown Parser | Markdown 文件 | 通用 Markdown |
| Obsidian Parser | Obsidian Vault | Markdown + YAML Frontmatter |
| Notion Parser | Notion 导出 | HTML / Markdown |
| LINE Parser | LINE 聊天导出 | JSON |
| Telegram Parser | Telegram 导出 | JSON |
| WeChat Parser | 微信聊天导出 | 自定义格式 |

**扩展原则**：新增 Parser 只需在 `parser/` 目录下新增实现，不修改 MemoryService。

---

## 5. Import Pipeline

### 5.1 Pipeline 步骤

```
┌─────────────────────────────────────────────────────────┐
│                   Import Pipeline                       │
├─────────────────────────────────────────────────────────┤
│  1. Validate Import                                     │
│     └─ 校验文件格式、Source 合法性、Batch 大小上限       │
├─────────────────────────────────────────────────────────┤
│  2. Build Import Context                                │
│     └─ 创建 ImportContext，初始化统计计数器              │
├─────────────────────────────────────────────────────────┤
│  3. Parse Batch                                         │
│     └─ 调用 Parser → MemoryCandidate[]                  │
├─────────────────────────────────────────────────────────┤
│  4. Process Memory                                      │
│     └─ 逐条调用 MemoryEngine.captureMemory()            │
│     └─ 按 ImportContext 跟踪状态                         │
├─────────────────────────────────────────────────────────┤
│  5. Collect Result                                      │
│     └─ 汇总 Success / Duplicate / Skipped / Failed      │
├─────────────────────────────────────────────────────────┤
│  6. Generate Import Report                              │
│     └─ 生成 ImportReport（含 Error Summary）             │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Pipeline 状态机

```
IDLE
  ↓ startImport()
VALIDATING
  ↓ validate()
BUILDING_CONTEXT
  ↓ buildContext()
PARSING
  ↓ parse()
PROCESSING
  ├→ success → Increment successCount
  ├→ duplicate → Increment duplicateCount
  ├→ skipped → Increment skippedCount
  ├→ failed → Increment failedCount, record ImportError
  └→ recoverPolicy? → Continue / Stop
  ↓ all processed
FINISHING
  ↓ generateReport()
COMPLETED
```

---

## 6. Transaction Policy

### 6.1 默认策略：PerMemory Transaction

```
Import Batch
      │
      ▼
Memory 1 → Transaction → Commit
Memory 2 → Transaction → Commit
Memory 3 → Transaction → Commit
...
Memory N → Transaction → Commit
```

**理由**：

| 优势 | 说明 |
|------|------|
| 单条失败不影响其他 | 一条失败不会回滚整个批次 |
| 已完成数据无需重导 | 成功的 Memory 已持久化 |
| 天然支持断点恢复 | 可从失败位置继续 |
| 支持超大规模导入 | 无长事务锁表风险 |

### 6.2 TransactionPolicy 可扩展设计

| 策略 | 说明 | 适用场景 | 状态 |
|------|------|----------|------|
| **PerMemory** | 每条 Memory 独立事务 | 默认，绝大多数场景 | MVP ✅ |
| **PerChunk** | 每 N 条一个事务 | 未来性能优化 | V2+ |
| **WholeBatch** | 整个批次一个事务 | 特殊场景（如数据迁移） | V2+ |

**MVP 默认采用 PerMemory**。未来如有性能需求，可增加 PerChunk（例如每 100 条一个事务），而无需修改 MemoryService 的整体流程。

### 6.3 事务控制边界

MemoryService **不负责数据库事务控制**。

事务边界由更底层控制（Repository 或 Unit of Work），MemoryService 只负责 Batch 生命周期管理。

```
MemoryService
  → 编排 Import Pipeline
  → 调用 MemoryEngine.captureMemory()
  → MemoryEngine 协调 Repository
  → Repository 控制事务边界
```

---

## 7. Idempotent Import

### 7.1 幂等原则

Import 必须支持幂等。

重复导入同一历史聊天：

* **不能**生成重复 Memory
* **不能**因为重复导入而污染统计

### 7.2 唯一性判定

Memory 唯一性由以下因素决定，**不是 Import Batch**：

| 判定依据 | 说明 |
|----------|------|
| Canonical Identity | Entity 级别的规范化标识 |
| Evidence | 原始证据的唯一性 |
| Content Hash | 内容指纹（防近似重复） |
| Time Range | 导入时间范围（防跨批次重复） |

### 7.3 幂等处理流程

```
Parse Batch → MemoryCandidate
    ↓
Duplicate Check（通过 MemoryEngine 验证）
    ↓
    ├→ 重复 → 标记为 DUPLICATE，不创建 MemoryNode
    └→ 新内容 → 调用 MemoryEngine.captureMemory()
```

Import Report 中会明确区分：

```
Success: 998
Duplicate: 2
Skipped: 0
Failed: 0
```

---

## 8. Failure Recovery

### 8.1 默认策略：Continue-on-Error

```
Memory1   ✓
Memory2   ✓
Memory3   ✗  ← 失败，但继续
Memory4   ✓
Memory5   ✓
...
Import Finish
```

**理由**：

| 理由 | 说明 |
|------|------|
| 导入属于离线批处理 | 不是银行转账，目标是最多导入成功 |
| 失败通常是局部数据问题 | 一条 JSON 字段缺失不应影响其余 |
| 与幂等设计天然契合 | 修复后重新导入，失败条可成功 |

### 8.2 RecoveryPolicy 可扩展设计

| 策略 | 说明 | 适用场景 | 状态 |
|------|------|----------|------|
| **ContinueOnError** | 默认，单条失败不中断 Batch | 绝大多数导入场景 | MVP ✅ |
| **StopOnFatal** | 遇到致命错误立即终止 | 数据库不可用、Schema 不兼容 | V2+ |
| **StopAfterNFailures** | 连续失败 N 条后终止 | Parser 与数据格式完全不匹配 | V2+ |

### 8.3 ImportError Collection

每条失败的 Memory 都应记录 ImportError：

| 字段 | 类型 | 说明 |
|------|------|------|
| `memoryIndex` | int | 批次中的序号 |
| `sourceId` | String | 来源 ID（如 message_id） |
| `errorCode` | String | 错误码（如 `MISSING_TIMESTAMP`） |
| `errorMessage` | String | 人类可读的错误描述 |
| `stage` | String | 失败阶段（PARSER / VALIDATION / ENGINE / PERSISTENCE） |
| `exception` | String (optional) | 异常信息（调试用） |

### 8.4 Import Report

最终 Import Report 包含：

```
ImportReport
├── batchId
├── source
├── startTime
├── endTime
├── statistics
│   ├── totalCount
│   ├── successCount
│   ├── duplicateCount
│   ├── skippedCount
│   └── failedCount
├── errorSummary          ← 仅摘要，不含全部堆栈
│   ├── Memory #381: Missing Timestamp
│   └── Memory #728: Invalid Entity Reference
└── recoveryPolicyUsed
```

**原则**：无需返回全部堆栈信息，只需提供可定位问题的摘要。

---

## 9. Execution Model

### 9.1 Job-Oriented Design

Import 使用 **Job-Oriented Design**。

MemoryService 面向 **ImportJob**，不是 Thread，不是 HTTP Request。

### 9.2 ImportJob

| 字段 | 类型 | 说明 |
|------|------|------|
| `jobId` | UUID | 作业唯一标识 |
| `batchId` | UUID | 关联的批次 ID |
| `source` | String | 导入来源 |
| `status` | String | IDLE / RUNNING / COMPLETED / FAILED / CANCELLED |
| `progress` | int | 0-100 百分比 |
| `statistics` | ImportStatistics | 实时统计 |
| `report` | ImportReport (optional) | 完成后生成 |
| `startedAt` | Instant | 开始时间 |
| `finishedAt` | Instant | 结束时间 |

### 9.3 职责分离

| 组件 | 职责 |
|------|------|
| **MemoryService** | 负责 Job 生命周期管理（创建、查询、取消、重试） |
| **TaskRuntime** | 负责真正调度（线程池、并发控制、重试机制） |

MemoryService **不耦合** TaskRuntime 的具体实现。

```
MemoryService.createImportJob(source, file)
    ↓
创建 ImportJob（状态 = IDLE）
    ↓
返回 JobId
    ↓
TaskRuntime 拾取并执行
    ↓
MemoryService 监听状态变更
```

---

## 10. MemoryService Public API

### 10.1 Capture Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `captureMemory(CaptureCommand)` | CaptureCommand | `MemoryResult<MemoryId>` | 捕获单条记忆 |
| `captureConversation(CaptureCommand[])` | CaptureCommand[] | `MemoryResult<List<MemoryId>>` | 捕获会话级记忆 |

### 10.2 Import Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `createImportJob(ImportCommand)` | ImportCommand | `MemoryResult<JobId>` | 创建导入作业 |
| `getImportStatus(JobId)` | JobId | `ImportJobStatus` | 查询导入状态 |
| `cancelImport(JobId)` | JobId | `MemoryResult<Void>` | 取消导入作业 |
| `retryImport(JobId)` | JobId | `MemoryResult<JobId>` | 重试导入作业 |

### 10.3 Merge Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `mergeMemories(MergeCommand)` | MergeCommand | `MemoryResult<MemoryId>` | 合并多条记忆 |

### 10.4 Archive Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `archiveMemory(ArchiveCommand)` | ArchiveCommand | `MemoryResult<Void>` | 归档记忆 |

### 10.5 Lifecycle Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `triggerReflection(MemoryId)` | MemoryId | `MemoryResult<Void>` | 触发 Reflection |
| `scheduleArchive(MemoryId)` | MemoryId | `MemoryResult<Void>` | 计划归档 |
| `reprocessMemory(MemoryId)` | MemoryId | `MemoryResult<Void>` | 重新处理 |

### 10.6 Restore Capability

| 方法 | 输入 | 返回 | 说明 |
|------|------|------|------|
| `restoreArchivedMemory(ArchiveId)` | ArchiveId | `MemoryResult<MemoryId>` | 从归档恢复 |

---

## 11. Error Model

### 11.1 统一返回模型

不要依赖 Exception 作为正常控制流程。

统一使用结构化返回模型：

```
MemoryResult<T>
├── status: SUCCESS | PARTIAL_SUCCESS | FAILED
├── errorCode: String (optional)
├── message: String (optional)
└── payload: T (optional)
```

### 11.2 具体返回类型

| 返回类型 | 用途 |
|----------|------|
| `MemoryResult<MemoryId>` | Capture、Merge、Restore 操作 |
| `MemoryResult<JobId>` | Import 作业创建 |
| `MemoryResult<Void>` | Archive、Lifecycle 操作 |
| `MemoryResult<ImportReport>` | Import 完成后的最终报告 |

### 11.3 错误码约定

| 错误码 | 说明 |
|--------|------|
| `DUPLICATE_MEMORY` | 记忆已存在（幂等检测） |
| `INVALID_COMMAND` | 命令参数无效 |
| `ENTITY_RESOLUTION_FAILED` | Entity 解析失败 |
| `EVIDENCE_MISSING` | 缺少必要证据 |
| `ARCHIVE_NOT_FOUND` | 归档不存在 |
| `JOB_NOT_FOUND` | Job 不存在 |
| `JOB_CANCELLED` | Job 已被取消 |
| `PARSER_UNAVAILABLE` | Parser 不可用 |
| `IMPORT_LIMIT_EXCEEDED` | 导入批次超出大小限制 |

---

## 12. Domain Events

### 12.1 事件驱动解耦

MemoryService 完成业务后 **发布 Domain Event**，不直接通知其它 Service。

### 12.2 事件清单

| 事件 | 触发时机 | 订阅者 |
|------|----------|--------|
| `MemoryCaptured` | 单条记忆捕获完成 | ReflectionService, Analytics |
| `MemoryMerged` | 记忆合并完成 | Analytics, Notification |
| `MemoryArchived` | 记忆归档完成 | Analytics, Notification |
| `ImportCompleted` | 批量导入完成 | Analytics, Notification, TaskRuntime |
| `ReflectionTriggered` | Reflection 触发 | ReflectionService |

### 12.3 事件结构

```
DomainEvent
├── eventType: String
├── eventId: UUID
├── timestamp: Instant
├── aggregateId: String (MemoryId / JobId)
├── aggregateType: String (MEMORY / IMPORT_JOB)
└── payload: Map<String, Object>
```

### 12.4 事件发布原则

| 原则 | 说明 |
|------|------|
| 异步发布 | 事件发布不阻塞主流程 |
| 最终一致性 | 订阅者不保证立即收到 |
| 幂等消费 | 事件可重复消费 |
| 预留 event/ 目录 | MVP 不实现事件总线，预留接口 |

---

## 13. Service Collaboration Matrix

### 13.1 MemoryService 协作矩阵

> **Phase B 规范**：每个 Service 文档必须包含此矩阵。所有矩阵合并形成完整的 Service Dependency Graph。

| Caller | Callee | Allowed | Interaction Pattern | Reason |
|--------|--------|---------|---------------------|--------|
| MemoryService | MemoryEngine | ✅ | Sync | Memory Domain Orchestration |
| MemoryService | ArchiveEngine | ✅ | Sync | Archive Capability 执行 |
| MemoryService | EvidenceEngine | ✅ | Sync | Capture/Merge 时验证证据链 |
| MemoryService | RelationshipEngine | ✅ | Sync | Capture/Merge 时管理关系 |
| MemoryService | IngestionService | ⚠️ | Event Only | 避免直接耦合，通过事件通知 |
| MemoryService | ReflectionService | ⚠️ | Event / Job Dispatch | 触发 Reflection，不直接调用 |
| MemoryService | QueryService | ❌ | N/A | 防止 Command → Query 耦合，CQRS 分离 |
| MemoryService | ContextService | ❌ | N/A | Context 构建属于 Query 侧 |
| MemoryService | TaskRuntime | ⚠️ | Job Dispatch | Import Job 调度，不耦合实现 |
| MemoryService | Repository | ❌ | N/A | 无层跳跃，通过 Engine 间接访问 |

### 13.2 矩阵解读

| 符号 | 含义 |
|------|------|
| ✅ | 允许同步调用 |
| ⚠️ | 允许但有限制（需通过抽象/事件/Job） |
| ❌ | 禁止 |

### 13.3 未来扩展

所有 10_x 文档的 Service Collaboration Matrix 合并后形成：

```
Complete Service Dependency Graph
├── MemoryService Matrix
├── QueryService Matrix
├── ReflectionService Matrix
├── IngestionService Matrix
├── ContextService Matrix
└── TaskService Matrix
```

用于：

* Consistency Review
* Architecture Review
* Implementation Review
* DAG 验证（无循环依赖）

---

## 14. 与 Phase A 文档的关系

| 文档 | 引用关系 |
|------|----------|
| 01 | 记忆类型体系、生命周期、分类体系（MemoryService 的 Capability 分组基于此） |
| 02 | MemoryEngine 重新定义为 Memory Domain Orchestrator（MemoryService 编排 MemoryEngine） |
| 03 | Entity / MemoryNode / Relationship 模型（MemoryService 操作的领域对象） |
| 04 | Schema / Reflect / Archive（MemoryService 的 Archive Capability 基于此） |
| 05 | Lifecycle / Reflection Engine（MemoryService 的 Lifecycle Capability 触发 Reflection） |
| 06 | Runtime Architecture（MemoryService 是 Runtime 的一部分） |
| 07 | Boundary Review（MemoryService 遵守 P1-P9 边界约束） |
| 08 | Implementation Architecture（MemoryService 是 08 定义的 Service 之一） |
| 09 | Database Physical Design（MemoryService 通过 Repository 间接操作 09 的表结构） |
| 10_1 | Implementation Service Layer（本文档引用 10_1 的分层架构、Service 分类、依赖规则） |

---

## 附录 A：术语对照

| 术语 | 说明 | 出处 |
|------|------|------|
| MemoryService | Memory Domain Service，编排记忆领域能力 | 本文档 |
| ImportContext | Batch Import 上下文，属于批次级别 | 本文档 |
| ImportReport | 导入完成后生成的报告 | 本文档 |
| ImportJob | Job-Oriented Design 的作业对象 | 本文档 |
| TransactionPolicy | 事务策略的可扩展设计 | 本文档 |
| RecoveryPolicy | 失败恢复策略的可扩展设计 | 本文档 |
| DomainEvent | 服务间解耦的事件机制 | 本文档 |
| Service Collaboration Matrix | Phase B 统一规范，描述 Service 间调用关系 | 本文档 |

---

## 附录 B：文档变更记录

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|----------|------|
| 1.0 | 2026-06-27 | 初始版本，确认 MemoryService 全部设计要素 | ✅ 已确认 |
| 1.2 | 2026-06-27 | Phase B-3 修订：(1) 新增与 10_4 的交叉引用（Service Independence、Shared Domain Engine、Semantic Uniqueness、L0 Protection）(2) Decision Summary 补充 16~20 (3) 回溯更新表补充 10_4 | ✅ 已确认 |
| 1.3 | 2026-06-28 | Phase B-5 修订：(1) 补充 MemoryService 编排 EntityEngine 的角色（与 10_5 对齐）(2) Decision Summary 补充 21 | ✅ 已确认 |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

*本文档是 Phase B 的 MemoryService 设计文档，后续 10_3~10_N 文档均引用本文档的 Service Collaboration Matrix 规范。*
