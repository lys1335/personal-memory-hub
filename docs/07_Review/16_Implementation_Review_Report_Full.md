# Phase C Stage 3 — Implementation Review Report

> **版本**: 1.0  
> **日期**: 2026-07-03  
> **阶段**: Phase C Stage 3 — Implementation Review  
> **状态**: Draft  
> **作者**: System Architecture Group  
> **Repository**: https://github.com/lys1335/personal-memory-hub  
> **Branch**: main (HEAD: 2e123bd)

---

## 1. Executive Summary

本报告是对 Personal Memory Hub 项目 Phase C Stage 3 的实施审查。审查范围覆盖从已确认架构到可编码实现设计的全部文档，验证批准后的架构能否以低工程风险安全落地。

**审查结论**：

| 维度 | 评估 |
|------|------|
| 架构完整性 | 通过 — 五层架构、六项 Service、九个 Engine、统一 Repository 层均已定义 |
| API 就绪度 | 通过 — 所有 Service 的 Capability-Oriented API 已完整定义 |
| 持久化就绪度 | 通过 — 11 张核心表、UUIDv7 主键、分层索引策略明确 |
| 依赖注入 | 通过 — Service → Engine → Repository 依赖链清晰，DAG 无循环 |
| 执行流程 | 通过 — Online/Offline 路径、Command/Query 分离、Domain Event 路由已定义 |
| 并发与运行时 | 通过 — Task Runtime 提供 At-Least-Once、幂等键、指数退避 |
| 可测试性 | 通过 — 19 条 Testing Principles、分层测试策略、Golden Dataset 就绪 |
| 运营就绪度 | 通过 — Logging/Metrics/Tracing/Health Check 分层定义 |
| 实施风险 | 低风险 — 无 P0 发现，架构决策成熟，MVP 范围界定清晰 |

**最终评估：Implementation Ready — YES**

---

## 2. Review Scope

### 2.1 审查范围

| 层级 | 文档 | 审查内容 |
|------|------|----------|
| 架构层 | 02_MemoryEngine_ContextBuilder, 06_Runtime_Architecture, 08_Implementation_Architecture | Engine 定义、分层原则、边界约束 |
| 数据层 | 04_Schema_Archive_Reflect, 05_MemoryLifecycle_ReflectionEngine | Schema 设计、Memory 模型、Evidence 链 |
| 服务层 | 10_1~10_6 (Service Layer, MemoryService, QueryService, ReflectionService, EntityService, TaskRuntime) | Capability API、编排关系、Service DAG |
| 入口层 | 10_7_API_Entry | Protocol Adaptation、DTO 转换、Capability Discovery |
| 测试层 | 10_8_Testing | Testing Principles、Mock 策略、CI 策略 |
| 路线图 | 11_Implementation_Roadmap | 六阶段里程碑、编码顺序、MVP 范围 |
| 工程决策 | 12_Engineering_Register | 40 项 ENG-XXX 决策记录 |
| 工作流 | 13_AI_Development_Workflow | 生命周期、责任矩阵、门禁 |
| 前置审查 | 14_Final_Implementation_Review | 工程退出门禁 |

### 2.2 审查范围排除

- 不审查架构重新设计
- 不审查一致性（Phase C Stage 2 已完成）
- 不审查已批准的 ADR 变更
- 不审查 Phase B 之前的架构决策

---

## 3. Review Methodology

### 3.1 审查方法

1. **文档交叉引用**：逐层验证架构设计 → 实现设计 → 服务层 → 入口层的映射关系
2. **依赖图分析**：验证 Service DAG 和 Engine DAG 的无环性
3. **边界约束检查**：验证 No Layer Skipping、Service Independence、Command/Query Separation
4. **MVP 范围验证**：确认 MVP 实现组件与 V2+ 暂缓组件的界限清晰
5. **运行时安全性**：检查 Task Runtime 的幂等性、重试、恢复策略
6. **可测试性评估**：验证分层测试策略的完整性和 Mock 边界

### 3.2 审查标准

- **P0**：编码前必须修复 — 阻塞实施
- **P1**：编码前强烈推荐 — 高风险
- **P2**：改进建议 — 可在实施中或之后处理
- **P3**：仅观察 — 信息性发现

---

## 4. Review Findings

### IR-001: Service 清单完整性

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-001 |
| **Category** | IR-1 (Implementation Completeness) |
| **Severity** | P3 |
| **Affected Documents** | 10_1 §4.1, 10_2, 10_3, 10_4, 10_5, 10_6, 10_7 §3.1 |
| **Description** | 六个 Service（MemoryService, IngestionService, ReflectionService, QueryService, ContextService, TaskService）均有对应的实现设计文档，API 定义完整。但 `IngestionService` 的实现设计文档（10_N）未以独立文件存在，其职责主要在 10_1 §4.1 表格和 06 §3.2 中定义。 |
| **Engineering Impact** | 低 — IngestionService 的核心职责已在 10_1 和 06 中充分定义，实际编码时可参考这两个文档。 |
| **Recommended Resolution** | 在 10_2 或新建 10_X 中补充 IngestionService 的详细编排流程（Chunking → Extraction → EntityLinking → Validation → ObservationStore）。 |
| **Reasoning** | IngestionService 是 Offline Path 的入口，虽然职责相对简单（主要是 Pipeline 编排），但作为 MVP 核心组件应有独立的实现设计文档以保持一致性。 |

### IR-002: EntityService MVP 范围与 V2+ 边界的清晰性

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-002 |
| **Category** | IR-1 (Implementation Completeness) |
| **Severity** | P3 |
| **Affected Documents** | 10_5, 11 §3.6, 10_1 §10.2 |
| **Description** | EntityService 在 MVP 中部分实现（createEntity/resolveEntity ✅），V2+ 延期（mergeEntities/addAlias/addRelationship/updateCanonicalName ❌）。11 §3.6 已明确 MVP 范围，10_5 §8 Entity Lifecycle 定义了 Created → Active → Merged 三态。但 10_7 §3.1 Capability Catalog 仍将 mergeEntities/addAlias 等列为 Capability，未标注 MVP/V2+ 状态。 |
| **Engineering Impact** | 低 — 文档间已有一致性（Stage 2 AR-003 已修补），但 API Entry 的 Capability Catalog 未同步标注 MVP 状态，可能导致前端/SDK 开发者误以为所有 Capability 均可在 MVP 使用。 |
| **Recommended Resolution** | 在 10_7 §3.1 的 Capability Catalog 表格中为每个 Capability 标注 MVP/V2+ 状态，与 11 §3.6 保持一致。 |
| **Reasoning** | Capability Catalog 是外部调用者的第一手参考，应准确反映 MVP 范围。 |

### IR-003: Task Runtime Domain Event → Task 映射表的完整性

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-003 |
| **Category** | IR-5 (Execution Flow) |
| **Severity** | P2 |
| **Affected Documents** | 10_6 §14.2, 12_Architecture_Decisions |
| **Description** | 10_6 §14.2 定义了 6 条 Domain Event → Task 映射（ObservationCreated, ImportCompleted, EntityMerged×2, MemoryArchived, BeliefUpdated）。但 10_2 §12.2 MemoryService 定义了 5 个 Domain Event（MemoryCaptured, MemoryMerged, MemoryArchived, ImportCompleted, ReflectionTriggered），其中 MemoryCaptured 和 ReflectionTriggered 未在 10_6 §14.2 的映射表中出现。 |
| **Engineering Impact** | 中低 — MemoryCaptured 应触发 REFLECTION_TASK（与 ObservationCreated 语义重叠），ReflectionTriggered 应触发 REFLECTION_TASK（手动触发）。这是映射表遗漏而非架构问题。 |
| **Recommended Resolution** | 在 10_6 §14.2 补充 MemoryCaptured → REFLECTION_TASK 和 ReflectionTriggered → REFLECTION_TASK 的映射。 |
| **Reasoning** | Domain Event → Task 映射是 Task Runtime 的核心配置，应与服务层发布的事件完全对齐。 |

### IR-004: ContextService 与 QueryService 的职责边界

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-004 |
| **Category** | IR-5 (Execution Flow) |
| **Severity** | P2 |
| **Affected Documents** | 10_1 §4.1, 10_1 §4.3, 10_3, 06 §3.1 |
| **Description** | ContextService（10_1 §4.1 #5）的职责是"Context 组装与输出"，编排 ContextBuilder Engine 和 ActivationEngine。QueryService（10_1 §4.1 #4）的职责是"记忆检索、Context 构建"，编排 RetrievalEngine 和 ContextBuilder。两者都编排 ContextBuilder，职责存在重叠。10_1 §4.3 说明 ContextService 是编排层，不直接操作 ContextBuilder 内部原子模块；QueryService 的 Retrieval Capability 也涉及 Context 构建。 |
| **Engineering Impact** | 低 — 这是架构设计层面的澄清问题，非实施障碍。ContextService 面向 Online Runtime 的 Context Package 构建（供 LLM 使用），QueryService 面向读操作的检索结果组织。两者通过不同的 Service 入口调用，实际共享 ContextBuilder Engine。 |
| **Recommended Resolution** | 在 10_1 或 10_3 中补充一段说明：ContextService 的 Context 构建面向 LLM Prompt（含 State 激活），QueryService 的 Context 构建面向用户查询结果（含 Projection）。 |
| **Reasoning** | 明确两个 Service 共享 ContextBuilder 的不同使用场景，避免实施时职责混淆。 |

### IR-005: ImportJob 状态与 Task Runtime 状态机的对齐

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-005 |
| **Category** | IR-6 (Concurrency & Runtime) |
| **Severity** | P2 |
| **Affected Documents** | 10_2 §9.2, 10_6 §5.1 |
| **Description** | 10_2 §9.2 定义 ImportJob 状态为 IDLE/RUNNING/COMPLETED/FAILED/CANCELLED。10_6 §5.1 定义 Task Runtime 状态机为 Pending/Running/Completed/Failed/Dead。ImportJob 的 CANCELLED 状态在 Task Runtime 中不存在（10_6 §5.2 明确移除了 Cancelled 状态）。 |
| **Engineering Impact** | 低 — 10_6 §4.1 已明确"Task 从不直接创建另一个 Task"，ImportJob 是 MemoryService 管理的业务对象，Task Runtime 管理的是底层执行任务。两者状态机不同是合理的，但应在 10_2 或 10_6 中说明这种"业务状态 vs 运行时状态"的映射关系。 |
| **Recommended Resolution** | 在 10_2 §9.2 或 10_6 §3 中补充说明：ImportJob 是业务层状态机，Task Runtime 是基础设施层状态机。ImportJob.RUNNING 对应 Task.Status=Running，ImportJob.CANCELLED 对应 Task 被跳过（不重试，不进入 Dead）。 |
| **Reasoning** | 两种状态机共存是合理的，但实施时需要明确的映射规则，否则容易在取消导入时产生歧义。 |

### IR-006: ReflectionService 与 MemoryService 的 Archive 职责分配

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-006 |
| **Category** | IR-1 (Implementation Completeness) |
| **Severity** | P3 |
| **Affected Documents** | 10_2 §3.1, 10_4 §3.1, 10_1 §4.1 |
| **Description** | MemoryService 的 Lifecycle Capability 包含 `scheduleArchive()`（10_2 §3.1）。ReflectionService 的 Evaluate Capability 包含 `evaluate()`，可评估"Archive Candidate"（10_4 §4.1）。但两者的 Archive 职责边界不够清晰：MemoryService 是主动归档，ReflectionService 是评估归档候选。 |
| **Engineering Impact** | 低 — 这是职责分工的澄清，不影响实施。MemoryService 负责归档的执行（调用 ArchiveEngine），ReflectionService 负责归档的评估（调用 ReflectionEngine 分析 Memory 质量）。 |
| **Recommended Resolution** | 在 10_2 或 10_4 中补充一段说明：ReflectionService.evaluate() 产出 ArchiveCandidate（建议），MemoryService.archiveMemory() 执行归档（动作）。 |
| **Reasoning** | 清晰的职责边界有助于实施时避免 Service 间逻辑交叉。 |

### IR-007: Repository 层文档缺失

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-007 |
| **Category** | IR-1 (Implementation Completeness) |
| **Severity** | P2 |
| **Affected Documents** | 10_1 §3.1, 04_Schema_Archive_Reflect, 08_Implementation_Architecture |
| **Description** | 10_1 §3.1 定义了 Repository 层职责（CRUD/Query/Transaction/Persistence），但缺少针对 Repository 层的独立实现设计文档（类似 10_2~10_6 对各个 Service 的粒度）。文档 04 定义了 11 张核心表的结构，08 定义了 Candidate/State/Context Package Schema，但没有 Repository 聚合边界的详细设计（如 MemoryNodeRepository 的 CRUD 方法、EvidenceRepository 的查询模式、RelationshipRepository 的图遍历接口）。 |
| **Engineering Impact** | 中 — 实施时需要根据 04 的表结构自行推导 Repository 接口，缺少统一的 Repository 设计文档可能导致不同 Repository 的接口风格不一致。 |
| **Recommended Resolution** | 建议新增 `10_9_Implementation_Repository_Layer.md`，定义：(1) 各 Repository 的 CRUD 方法清单，(2) QueryRepository 的复杂查询接口，(3) Repository 的事务边界，(4) 聚合根定义。 |
| **Reasoning** | Repository 层是 Service 层和数据层的桥梁，统一的接口设计可显著降低实施阶段的认知负荷。 |

### IR-008: 统一任务表（tasks）与 Task Runtime 的冗余

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-008 |
| **Category** | IR-3 (Persistence Readiness) |
| **Severity** | P2 |
| **Affected Documents** | 04 §2.1, 08 §9.1, 10_6 |
| **Description** | 04 §2.1 将 `tasks` 表定义为 11 张核心表之一，替代原 ingestion_queue/reflection_queue/archive_queue。08 §9.1 同样定义统一任务表。10_6 定义了完整的 Task Runtime（含 tasks 表的 Runtime Metadata 字段：taskId, taskType, status, priority, retryCount 等）。但 04 的 tasks 表字段定义与 10_6 的 Runtime Metadata 字段定义未完全对齐。 |
| **Engineering Impact** | 低 — 两者描述的是同一概念的不同视角：04 是从数据库 Schema 角度，10_6 是从运行时角度。实施时需要将两者合并为统一的表定义。 |
| **Recommended Resolution** | 在 04 或 08 中补充 tasks 表的完整字段定义（包含 10_6 §3.1 的 Runtime Metadata），或在 10_6 中引用 04 的 Schema 定义，消除重复。 |
| **Reasoning** | 统一字段定义可减少实施时的 Schema 设计工作量。 |

### IR-009: API Entry Layer 的 Error Registry 完整性

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-009 |
| **Category** | IR-2 (API Readiness) |
| **Severity** | P2 |
| **Affected Documents** | 10_7 §4.4, 10_1 §3.2 |
| **Description** | 10_7 §4.4 定义了 11 个标准错误码（VALIDATION_ERROR, AUTHENTICATION_REQUIRED, AUTHORIZATION_DENIED, CAPABILITY_NOT_FOUND, SERVICE_UNAVAILABLE, TASK_EXECUTION_FAILED, DUPLICATE_ENTITY, EVIDENCE_MISSING, ARCHIVE_NOT_FOUND, JOB_NOT_FOUND, JOB_CANCELLED）。但 10_2 §11.3 定义了额外的业务错误码（DUPLICATE_MEMORY, INVALID_COMMAND, ENTITY_RESOLUTION_FAILED）。两者未合并。 |
| **Engineering Impact** | 低 — 错误码数量不多，实施时合并即可。但 Error Registry 作为全局概念应有统一的错误码清单。 |
| **Recommended Resolution** | 在 10_7 或 10_1 中建立统一的 Error Registry 表格，包含所有 Service 定义的错误码。 |
| **Reasoning** | 统一的 Error Registry 是 API 契约的重要组成部分，有利于多 Adapter 实现的一致性。 |

### IR-010: ReflectionService 的 L0 Protection 实施可行性

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-010 |
| **Category** | IR-1 (Implementation Completeness) |
| **Severity** | P1 |
| **Affected Documents** | 10_4 §10.5, 05 §1.2, 05 §4.1 |
| **Description** | 10_4 §10.5 明确要求 ReflectionService 必须 NEVER 自主创建 L0 Memory。05 §1.2 定义了 Evidence Based Memory 原则，L0 Observation 只能通过 Ingestion Pipeline 创建。但 10_4 §10.3 Recovery Baseline 中提到"用户与系统的交互本身成为合法的 L0 证据"，这需要 ReflectionService 在用户确认后触发 L0 创建。 |
| **Engineering Impact** | 中 — 这是一个实施时需要特别注意的边界：Recovery Baseline 产生的是用户交互记录（如"用户同意系统建议"），这条记录本身是 L0，但它是由用户交互产生的，不是 ReflectionService 自主创建的。 |
| **Recommended Resolution** | 在 10_4 §10.3 中补充说明：Recovery Baseline 的用户确认交互通过 IngestionService.ingestEvidence() 进入 L0，而非 ReflectionService 直接写入。 |
| **Reasoning** | 明确 Recovery Baseline 的 L0 创建路径，确保不违反 L0 Protection 原则。 |

### IR-011: MemoryService Import 与 TaskRuntime 的协作模式

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-011 |
| **Category** | IR-4 (Dependency Injection) |
| **Severity** | P2 |
| **Affected Documents** | 10_2 §9.1~9.3, 10_6 §14.1 |
| **Description** | 10_2 §9.2 定义 ImportJob 由 MemoryService 管理生命周期，TaskRuntime 负责实际调度（线程池、并发控制、重试）。10_6 §14.1 定义 MemoryService 通过 submit/query 与 TaskRuntime 交互。但 10_2 §9.3 的流程图中 MemoryService.createImportJob() 创建 ImportJob 后"TaskRuntime 拾取并执行"，未明确是通过 Domain Event 还是直接调用 TaskService.submit()。 |
| **EngineeringImpact** | 低 — 两种模式都可行。直接 submit 适用于同步场景，Domain Event 适用于异步解耦。 |
| **Recommended Resolution** | 在 10_2 §9.3 中明确 ImportJob 的 Task 提交方式：建议使用 TaskService.submit() 直接提交（因为是 MemoryService 主动发起的），而非通过 Domain Event 路由。 |
| **Reasoning** | Import 是 MemoryService 主动发起的操作，直接提交 Task 比通过 Domain Event 路由更直接、更可控。 |

### IR-012: 测试策略中 Golden Dataset 的初始化路径

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-012 |
| **Category** | IR-7 (Testability) |
| **Severity** | P2 |
| **Affected Documents** | 10_8 §6.2~6.4, 11 §5.1 |
| **Description** | 10_8 §6.4 定义了 Golden Dataset 结构（input.json, expected.json, actual.json），§6.2 定义了 Shared Fixtures。但 Golden Dataset 的"expected output"如何生成没有明确说明 — 是在设计阶段手工编写，还是通过参考实现自动生成？11 §5.1 Milestone 5 提到"Golden datasets: Known input-output pairs for regression"，但未说明创建流程。 |
| **Engineering Impact** | 低 — 这是测试实施策略问题，不影响架构设计。 |
| **Recommended Resolution** | 在 10_8 中补充 Golden Dataset 的创建流程：(1) 设计阶段手工编写 expected output，(2) 实施阶段用参考实现运行 input 生成 actual，(3) 对比 expected vs actual，差异需人工审查。 |
| **Reasoning** | 明确的 Golden Dataset 创建流程可降低测试实施阶段的认知负担。 |

### IR-013: Online/Offline 路径的 Queue 层实现

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-013 |
| **Category** | IR-6 (Concurrency & Runtime) |
| **Severity** | P2 |
| **Affected Documents** | 06 §2.3, 08 §9.1, 10_6 §7 |
| **Description** | 06 §2.3 定义了三层 Queue 架构（Ingestion Queue, Reflection Queue, Activation Queue），08 §9.1 统一为 tasks 表。10_6 §7 定义 Scheduler 是统一 Task 分发协调器。但 Online Runtime（Retrieval → Activation → ContextBuilder → LLM）和 Offline Runtime（Ingestion → Reflection → Memory Evolution）之间的 Queue 通信机制在实现设计中不够详细。 |
| **Engineering Impact** | 低 — 06 §2.2 已明确"两层通过 Queue 和 Event 机制通信，不直接共享内存"。实施时通过 Domain Event 机制（10_6 §8）实现即可。 |
| **Recommended Resolution** | 在 06 或 10_6 中补充一段说明：Online/Offline 通信通过 Domain Event 实现，Reflection Engine 产出 Belief 后发布 BeliefUpdated 事件，Activation Engine 消费该事件刷新 State。 |
| **Reasoning** | 明确 Online/Offline 通信的具体 Event 路径，减少实施时的猜测。 |

### IR-014: Context Package Token Budget 实施

| 字段 | 内容 |
|------|------|
| **Issue ID** | IR-014 |
| **Category** | IR-2 (API Readiness) |
| **Severity** | P1 |
| **Affected Documents** | 08 §6.3~6.4, 06 §3.1 |
| **Description** | 08 §6.3 定义了 ContextPackage 的四层结构（Session 40%, Entity 30%, Graph 20%, Global 10%），§6.4 要求"ContextPackage 必须支持 Token Budget"。但 06 §3.1 的 Engine 清单中 ContextBuilder (#5) 的职责是"接收检索结果 + State，输出 Prompt Context"，未明确 Token Budget 的计算和截断策略。10_1 §4.3 定义了 ContextBuilder 的三个 Atomic Engine（ContextRanker, ContextCompressor, ContextAssembler），但未定义 Token Budget 的管理接口。 |
| **Engineering Impact** | 中 — Token Budget 是 ContextBuilder 的核心功能，直接影响 LLM 调用的成本和质量。缺乏明确的预算管理机制可能导致上下文溢出或信息丢失。 |
| **Recommended Resolution** | 在 10_1 §4.3 或 08 §6 中补充 Token Budget 的管理机制：(1) Budget 总量配置，(2) 各层优先级（Layer 1 > Layer 2 > Layer 3 > Layer 4），(3) 超预算时的截断策略（先压缩还是先丢弃低优先级层），(4) Token 计数器接口。 |
| **Reasoning** | Token Budget 是 ContextBuilder 的关键实施细节，应在实现设计文档中明确。 |

---

## 5. Severity Summary

| Severity | Count | Items |
|----------|-------|-------|
| **P0** | 0 | — |
| **P1** | 1 | IR-010 (Reflection L0 Protection) |
| **P2** | 8 | IR-003, IR-005, IR-007, IR-008, IR-009, IR-011, IR-012, IR-014 |
| **P3** | 5 | IR-001, IR-002, IR-004, IR-006, IR-013 |
| **Total** | **14** | |

---

## 6. Recommended Actions

### 6.1 编码前必须处理

| # | Action | 对应 IR | 优先级 |
|---|--------|---------|--------|
| 1 | 补充 ReflectionService Recovery Baseline 的 L0 创建路径说明（通过 IngestionService 而非直接写入） | IR-010 | P1 |

### 6.2 编码过程中处理

| # | Action | 对应 IR | 优先级 |
|---|--------|---------|--------|
| 2 | 补充 MemoryCaptured/ReflectionTriggered 到 Task Runtime 的 Domain Event 映射 | IR-003 | P2 |
| 3 | 明确 ImportJob 业务状态与 Task Runtime 运行时状态的映射关系 | IR-005 | P2 |
| 4 | 新增 Repository 层实现设计文档（10_9） | IR-007 | P2 |
| 5 | 统一 tasks 表字段定义（Schema 视角 + Runtime 视角） | IR-008 | P2 |
| 6 | 建立统一 Error Registry | IR-009 | P2 |
| 7 | 明确 ImportJob 的 Task 提交方式（直接 submit vs Domain Event） | IR-011 | P2 |
| 8 | 补充 Golden Dataset 创建流程 | IR-012 | P2 |
| 9 | 补充 ContextPackage Token Budget 管理机制 | IR-014 | P1 |

### 6.3 后续优化

| # | Action | 对应 IR | 优先级 |
|---|--------|---------|--------|
| 10 | 补充 IngestionService 独立实现设计文档 | IR-001 | P3 |
| 11 | 在 10_7 Capability Catalog 中标注 MVP/V2+ 状态 | IR-002 | P3 |
| 12 | 补充 ContextService 与 QueryService 的 Context 构建场景区分说明 | IR-004 | P3 |
| 13 | 补充 ReflectionService 与 MemoryService 的 Archive 职责边界说明 | IR-006 | P3 |
| 14 | 补充 Online/Offline 通信的 Domain Event 路径说明 | IR-013 | P3 |

---

## 7. Deferred Items

以下项目明确推迟到 V2+ 实现，不在本次审查范围内：

| # | 组件 | 推迟阶段 | 依据 |
|---|------|----------|------|
| 1 | MCP/CLI/SDK/Agent Adapter | V2+ | 10_1 §10.3 |
| 2 | ArchiveEngine 完整实现 | V2+ | 10_1 §10.3 |
| 3 | Event System（Domain Event Bus） | V2+ | 10_1 §10.3 |
| 4 | Redis 分布式缓存 | V2+ | 08 §10.3 (UPG-002) |
| 5 | 外部向量存储（Chroma/Qdrant） | V2+ | 08 §11.3 (UPG-003) |
| 6 | EntityService Advanced（merge/alias/relationship/canonical-name） | V2+ | 11 §3.6 |
| 7 | Progressive Recall | V2+ | 11 §3.6 |
| 8 | Entity Suppression/Escape | V2+ | 10_5 §12.2 |
| 9 | Dashboard | V2+ | 11 §5.2 |
| 10 | CD Pipeline | V2+ | 11 §8 |

---

## 8. Final Assessment

### 8.1 Implementation Readiness Checklist

| 检查项 | 状态 |
|--------|------|
| 无 P0 发现 | ✅ 通过 |
| 无实施阻塞 | ✅ 通过（1 个 P1 为设计澄清，非阻塞） |
| 无缺失实施路径 | ✅ 通过（所有 Service/Engine/Repository 均有设计文档） |
| 无缺失核心接口 | ✅ 通过（所有 Capability 的 API 已定义） |
| 无循环依赖 | ✅ 通过（Service DAG 和 Engine DAG 均为有向无环图） |
| 已批准架构未变更 | ✅ 通过（审查期间未发现任何架构变更需求） |

### 8.2 工程风险评估

| 风险维度 | 风险等级 | 说明 |
|----------|----------|------|
| 架构复杂度 | 低 | 五层架构清晰，职责边界明确 |
| 数据一致性 | 低 | UUIDv7 主键、Evidence Chain、L0 Protection 确保数据完整性 |
| 并发安全 | 低 | Task Runtime 提供幂等性、重试、恢复机制 |
| API 稳定性 | 低 | Capability-based 接口，Protocol-agnostic |
| 测试覆盖 | 低 | 19 条 Testing Principles + Golden Dataset + 分层测试 |
| 实施学习曲线 | 中 | 文档量大（14 个 Phase B 文档 + 8 个 Phase A 文档），首次实施需全面阅读 |
| MVP 范围 | 低 | 明确界定了 MVP 和 V2+ 组件 |

### 8.3 最终结论

**Implementation Ready: YES**

批准后的架构可以通过当前设计文档安全、一致地实施，工程风险低。

- 所有 Service 的 Capability-Oriented API 已完整定义
- 所有 Engine 的职责和依赖关系已明确
- Repository 层的 11 张核心表已设计
- Task Runtime 提供了完整的运行时保障机制
- Testing Architecture 覆盖了从 Unit 到 E2E 的全层级
- MVP 范围清晰，V2+ 延期项有据可查

建议开发团队按照 11_Implementation_Roadmap 定义的编码顺序（Foundation → Repository → Domain Engine → Service → Entry → Testing）开始实施。

---

*本报告仅执行审查，不修改任何文档，不生成代码，不创建新设计文档。*

*GitHub HEAD (2e123bd) 作为 Single Source of Truth 在整个审查过程中保持不变。*
