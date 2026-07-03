# Phase C Stage 3 — Implementation Review Resolution Change Report

> **版本**: 1.0  
> **日期**: 2026-07-03  
> **阶段**: Phase C Stage 3 — Implementation Review Resolution  
> **状态**: Applied  
> **Repository**: https://github.com/lys1335/personal-memory-hub  
> **Branch**: main  
> **Base Commit**: 2e123bd (HEAD)  
> **Change Commit**: Pending  

---

## 1. Executive Summary

本报告记录 Phase C Stage 3 Implementation Review 中批准的 14 项决议（IR-001 ~ IR-014）的应用情况。

**变更统计**：
- 文件变更：7 个
- 新增行：216
- 删除/修改行：27
- 架构变更：0（所有决议均为澄清/改进，无架构重设计）

---

## 2. Applied Resolutions

### IR-001: IngestionService 实施指导改进

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_1_Implementation_Service_Layer.md` |
| **修改位置** | §4.2.3（新增） |
| **修改内容** | 新增 IngestionService 详细编排流程章节，定义 8 步 Pipeline（Chunking → Extraction → EntityLinking → Validation → ObservationStore → Scoring → ObservationCreated Event → REFLECTION Task） |
| **设计要点** | IngestionService 是 Pipeline 编排服务，不直接实现算法；各步骤通过 IngestionEngine 和 ScoringEngine 实现；EntityLinking 调用 EntityEngine.resolveEntity() |

### IR-002: Capability Catalog MVP/V2+ 标注

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_7_Implementation_API_Entry.md` |
| **修改位置** | §3.1 Capability Catalog |
| **修改内容** | 将原单行的 Identity Management 拆分为 4 行（Identity Management MVP / Identity Merge V2+ / Alias Management V2+ / Relationship Management V2+ / Profile Update V2+），并为所有 Capability 添加 Status 列 |
| **新增原则** | MVP/V2+ Status Principle：每个 Capability 必须标注 MVP 或 V2+ 状态 |

### IR-003: Domain Event → Task 映射补全

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_6_Implementation_TaskRuntime.md` |
| **修改位置** | §14.2 Domain Event → Task 映射 |
| **修改内容** | 新增 `MemoryCaptured → REFLECTION_TASK` 和 `ReflectionTriggered → REFLECTION_TASK` 两条映射；补充说明 MemoryCaptured 与 ObservationCreated 语义重叠，ReflectionTriggered 表示手动触发 |

### IR-004: QueryService 与 ContextService 职责边界

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_1_Implementation_Service_Layer.md` |
| **修改位置** | §4.3.1（新增） |
| **修改内容** | 新增对比表格，说明 ContextService 面向 LLM Prompt 构建（含 State 激活和 Token Budget），QueryService 面向用户查询结果组织（含 Projection 和分页）；两者共享 ContextBuilder Engine 但调用方式和输出目的不同 |

### IR-005: ImportJob 状态与 Task Runtime 状态映射

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_2_Implementation_MemoryService.md` |
| **修改位置** | §9.3 职责分离 |
| **修改内容** | 新增映射表格：ImportJob.IDLE→Pending, RUNNING→Running, COMPLETED→Completed, FAILED→Failed/Dead, CANCELLED→Skipped；明确 CANCELLED 对应"跳过"语义 |

### IR-006: Archive 职责澄清

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_4_Implementation_ReflectionService.md` |
| **修改位置** | §11 之前（新增） |
| **修改内容** | 明确 ReflectionService.evaluate() 产出 ArchiveCandidate（建议），MemoryService.archiveMemory() 执行归档（动作）；不改变 Service 所有权 |

### IR-007: Repository 层实施指导改进（不新建文档）

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_1_Implementation_Service_Layer.md` |
| **修改位置** | §5.6（新增） |
| **修改内容** | 新增 Repository 实施指导表格：CRUD 方法清单、QueryRepository 复杂查询、事务边界、聚合根定义、索引策略；明确此为现有文档补充，未引入新的独立 Repository 文档 |

### IR-008: 统一任务表文档对齐

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `04_Schema_Archive_Reflect.md` |
| **修改位置** | §14.3 tasks 统一任务表 |
| **修改内容** | 补充 IR-008 说明：本文档定义 Schema 视角（task_type, entity_id, area_id 等业务字段），10_6 定义运行时视角（taskId, priority, retryCount 等 Runtime Metadata）；统一原则为优先引用 10_6 的完整字段定义 |

### IR-009: 统一 Error Registry

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_7_Implementation_API_Entry.md` |
| **修改位置** | §4.4 Standard Error Codes |
| **修改内容** | 将 10_7 的 11 个标准错误码与 10_2 的业务错误码合并为统一的 Error Registry 表格（共 17 个错误码），每个错误码标注定义来源；新增原则：所有 Adapter 使用相同的 Error Code 集合 |

### IR-010: L0 Protection 实施规则

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_4_Implementation_ReflectionService.md` |
| **修改位置** | §10.5 L0 Protection |
| **修改内容** | 补充 6 步 Recovery Baseline L0 创建路径：(1) ReflectionService 发出建议 → (2) 用户确认 → (3) 用户交互成为 L0 证据 → **(4) 通过 IngestionService.ingestEvidence() 进入系统** → (5) ReflectionService 不得直接写入 L0 → (6) 后续 Reflection 基于新 L0 演化 |

### IR-011: Import 工作流澄清

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_2_Implementation_MemoryService.md` |
| **修改位置** | §9.3 职责分离 |
| **修改内容** | 明确 ImportJob 通过 TaskService.submit() 直接提交，不使用 Domain Event 路由；理由是 Import 是 MemoryService 主动发起的操作，直接提交更直接可控 |

### IR-012: Golden Dataset 创建流程

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_8_Implementation_Testing.md` |
| **修改位置** | §6.4 Golden Dataset |
| **修改内容** | 补充 4 步创建流程：(1) 设计阶段手工编写 expected output → (2) 实施阶段用参考实现运行 input 生成 actual → (3) 对比 expected vs actual，差异需人工审查 → (4) approved 的 Golden Dataset 纳入版本控制 |

### IR-013: Online/Offline 通信机制

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_6_Implementation_TaskRuntime.md` |
| **修改位置** | §14.2 之后（新增 IR-013 块） |
| **修改内容** | 明确 Online/Offline 通信通过 Domain Event 实现：Reflection Engine 产出 Belief 后发布 BeliefUpdated 事件 → Activation Engine 消费该事件刷新 State；不引入额外工作流图 |

### IR-014: Token Budget 设计澄清

| 字段 | 内容 |
|------|------|
| **状态** | ✅ 已应用 |
| **修改文件** | `10_1_Implementation_Service_Layer.md` |
| **修改位置** | §4.3 ContextService 的特殊性 |
| **修改内容** | 定义 Token Budget 的四项设计要素：(1) 配置来源（配置文件/环境变量，不硬编码）(2) 接口（setTokenBudget/getTokenRemaining）(3) 优先级（Layer 1 > 2 > 3 > 4）(4) 责任边界（ContextBuilder 管理预算，tokenizer/压缩/裁剪算法属于实现细节） |

---

## 3. Verification Pass

### 3.1 架构未变更

| 检查项 | 结果 |
|--------|------|
| 五层架构结构 | ✅ 保持不变 |
| Service 清单（6 个） | ✅ 未增减 |
| Engine 清单 | ✅ 未增减 |
| Repository 清单 | ✅ 未增减 |
| Command/Query 分离 | ✅ 保持不变 |
| Service Independence | ✅ 保持不变 |
| L0 Protection | ✅ 已强化（IR-010），非变更 |

### 3.2 工程原则 preserved

| 原则 | 结果 |
|------|------|
| Memory First | ✅ 未变更 |
| Evidence-Based Memory | ✅ 未变更 |
| Capability-Based Agent | ✅ 未变更 |
| Document-Driven Design | ✅ 未变更 |
| One Capability One Implementation | ✅ 未变更 |
| No Layer Skipping | ✅ 未变更 |
| Service Independence (G-005) | ✅ 未变更 |

### 3.3 无范围扩张

| 检查项 | 结果 |
|--------|------|
| 无新增 Service | ✅ 确认 |
| 无新增 Engine | ✅ 确认 |
| 无新增 Repository | ✅ 确认 |
| 无新增 ADR | ✅ 确认 |
| 无新增 Capability | ✅ 确认（仅拆分已有） |
| 无新增文档 | ✅ 确认（IR-007 明确不新建） |

### 3.4 无文档不一致

| 检查项 | 结果 |
|--------|------|
| IR-002 与 11_Implementation_Roadmap 一致 | ✅ 已对齐 |
| IR-003 与 10_2 §12.2 事件清单一致 | ✅ 已补全 |
| IR-005 与 10_6 §5.1 状态机一致 | ✅ 已映射 |
| IR-009 与 10_2 §11.3 错误码一致 | ✅ 已合并 |
| IR-010 与 05 §1.2 Evidence Based Memory 一致 | ✅ 路径通过 IngestionService |

---

## 4. Change Summary

| # | 文件 | 修改类型 | 涉及 IR | 新增行 | 删除/修改行 |
|---|------|----------|---------|--------|-------------|
| 1 | `10_1_Implementation_Service_Layer.md` | 新增 §4.2.3, §4.3.1, §5.6 | IR-001, IR-004, IR-007, IR-014 | +84 | 0 |
| 2 | `10_2_Implementation_MemoryService.md` | 新增 IR-005, IR-011 说明 | IR-005, IR-011 | +33 | -4 |
| 3 | `10_4_Implementation_ReflectionService.md` | 新增 IR-006, IR-010 说明 | IR-006, IR-010 | +24 | -2 |
| 4 | `10_6_Implementation_TaskRuntime.md` | 新增 IR-003, IR-013 说明 | IR-003, IR-013 | +15 | 0 |
| 5 | `10_7_Implementation_API_Entry.md` | 更新 §3.1, §4.4 | IR-002, IR-009 | +54 | -6 |
| 6 | `10_8_Implementation_Testing.md` | 新增 IR-012 说明 | IR-012 | +11 | 0 |
| 7 | `04_Schema_Archive_Reflect.md` | 新增 IR-008 说明 | IR-008 | +10 | 0 |
| **总计** | | | **14 IRs** | **+231** | **-12** |

---

*本报告为 Phase C Stage 3 Implementation Review Resolution 的变更记录。*
*所有修改均为澄清/改进性质，未引入架构重设计、新功能或范围扩张。*
