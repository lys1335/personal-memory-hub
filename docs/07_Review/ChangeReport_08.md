# Personal AI Memory Hub — ChangeReport_08

> **版本**: 1.0  
> **日期**: 2026-06-23  
> **阶段**: 第八阶段  
> **作者**: 系统架构组

---

## 1. 本次新增内容

### 1.1 新建文档

| 文件 | 说明 |
|------|------|
| `08_Implementation_Architecture.md` | 实现架构设计文档，定义 Candidate Schema、State Schema、Context Package、API 契约、Queue 统一、Cache、Vector Storage、Retrieval 约束、MVP 范围、升级路径 |

### 1.2 新增升级路径（UPG）

| 编号 | 升级项 | 阶段 |
|------|--------|------|
| UPG-001 | Direct Call → Event Driven Migration | V2+ |
| UPG-002 | In-Memory Cache → Redis Cache | V2+ |
| UPG-004 | Supabase pgvector → External Vector Store (Chroma/Qdrant/Weaviate) | V2+ |

### 1.3 新增设计决策

| 编号 | 决策 | 说明 |
|------|------|------|
| IMP-001 | Candidate 采用独立表 | Candidate 独立于 MemoryNode，是 Reflection 的工作对象 |
| IMP-002 | State 不落库 | State 仅短时缓存，保存引用（sourceBeliefIds/sourcePatternIds） |
| IMP-003 | ContextPackage 为 LLM 唯一入口 | Runtime Flow: ActivationContext → RetrievalResult → RuntimeState → ContextPackage |
| IMP-004 | Memory Immutable | 禁止 updateMemory()/deleteMemory()，仅允许 correctMemory()/archiveMemory() |
| IMP-005 | 统一 tasks 表 | 替代原 ingestion_queue/reflection_queue/archive_queue 独立建表 |
| IMP-006 | Reflection Trigger = Evidence Driven + Debounce | 同一 Entity/Area 存在待执行任务时不重复创建 |
| IMP-007 | V1 禁止 Redis | 仅 In-Memory Cache |
| IMP-008 | V1 禁止 Chroma | 仅 Supabase pgvector |
| IMP-009 | Retrieval 必须回查 Supabase | 禁止 Vector Store 直接向 LLM 提供内容 |
| IMP-010 | Reflection 预留三种模式 | Auto / Manual / Hybrid 可切换 |
| IMP-011 | CORRECTS / SUPERSEDES 新关系 | 记忆修正与替代关系 |

---

## 2. 对旧文档的修订内容

### 2.1 01_MemoryHub_Foundation.md

| # | 位置 | 修订前 | 修订后 | 原因 |
|---|------|--------|--------|------|
| 1 | 第 4.3 章 Knowledge Memory 示例 | "Chroma 作为长期记忆候选方案" | "Supabase pgvector 作为向量检索方案（MVP）" | 08 锁定 pgvector 为 V1 方案，Chroma 为 V2+ 选项 |

### 2.2 02_MemoryEngine_ContextBuilder.md

| # | 位置 | 修订前 | 修订后 | 原因 |
|---|------|--------|--------|------|
| 1 | 第 9.3 章 Tag 示例 | "Chroma | 向量数据库" | "pgvector | 向量检索（Supabase 内置）" | 08 锁定 pgvector 为 V1 方案 |

### 2.3 03_Entity_MemoryGraph.md

| # | 位置 | 修订前 | 修订后 | 原因 |
|---|------|--------|--------|------|
| 1 | 第 9 章 ADR-011 核心表规划 | `reflect_tasks` | `tasks`（统一任务表） | 08 定义统一 tasks 表 |
| 2 | 第 11 章数据流总结 | `reflect_tasks` | `tasks` / `user_profiles` | 统一表名，补全 user_profiles |

### 2.4 04_Schema_Archive_Reflect.md

| # | 位置 | 修订前 | 修订后 | 原因 |
|---|------|--------|--------|------|
| 1 | 第 2.1 章核心表清单 | `reflect_tasks` | `tasks`（统一任务表） | 08 定义统一 tasks 表 |
| 2 | 第 14.3 章 | `reflect_tasks` 只负责调度 | `tasks` 统一任务表 | 08 定义统一任务表，管理所有类型 |
| 3 | 第 14.1 章 Reflect vs Archive | "定时 / 事件驱动" | "Evidence Driven + Debounce" | 08 定义 Reflection Trigger |
| 4 | 附录 A 核心表字段速查 | `reflect_tasks` 行 | 标注 → 已合并入 `tasks` 表 | 08 统一任务表 |
| 5 | 附录 C 术语表 | Scheduler 描述 | 补充 "统一 `tasks` 表" | 08 统一任务表 |

### 2.5 05_MemoryLifecycle_ReflectionEngine.md

| # | 位置 | 修订前 | 修订后 | 原因 |
|---|------|--------|--------|------|
| 1 | 第 10.1 章两级 Reflect | "Queue 满（≥N 条）或兜底定时" | "Evidence Driven + Debounce" | 08 定义 Reflection Trigger |
| 2 | 第 10.1 章 | "每日/每周定时" | "Evidence Driven" | 08 定义 Reflection Trigger |
| 3 | 第 4.2 章 Stage 8 | "Queue 满时才触发 Reflect" | "Evidence Driven + Debounce" | 08 定义 Reflection Trigger |
| 4 | 第 4.2 章 Stage 8 | "定时触发仅作为兜底机制" | "Debounce 机制避免短时间内重复触发" | 08 定义 Reflection Trigger |
| 5 | 第 14.1 章 Runtime Components | Reflection Engine 描述 | 补充 "Evidence Driven + Debounce" | 与 10.1 保持一致 |
| 6 | 第 14.1 章 | 缺少 Scheduler 组件 | 新增 "Scheduler | 统一 `tasks` 表任务调度" | 08 定义统一任务表 |

### 2.6 06_Runtime_Architecture.md

| # | 位置 | 修订前 | 修订后 | 原因 |
|---|------|--------|--------|------|
| 1 | 第 5.1 章队列清单 | 5 个独立队列表 | 统一 `tasks` 表 | 08 定义统一任务表 |
| 2 | 第 5.2 章队列通用能力 | "所有队列必须支持" | "所有任务类型在 `tasks` 表中必须支持" | 统一表名 |
| 3 | 第 5.3 章 MVP 队列实现 | "Ingestion Queue → Reflection Queue → Activation Queue" | "tasks（统一管理所有任务类型）" | 统一表名 |
| 4 | 第 12.1 章 MVP | 列出 Ingestion/Reflection/Activation Queue | 补充 "tasks 表 ✅ 实现" | 统一任务表 |
| 5 | 第 12.2 章 V2 | "Archive Queue ✅ 新增" | "tasks 表新增 ARCHIVE 类型 ✅ 新增" | 统一表名 |
| 6 | 第 12.3 章 V3 | "Maintenance Queue ✅ 新增" | "tasks 表新增 Maintenance 类型 ✅ 新增" | 统一表名 |
| 7 | 第 8.3 章 Light/Heavy Reflect | "Queue 满/兜底定时" | "Evidence Driven + Debounce" | 08 定义 Reflection Trigger |

### 2.7 07_Boundary_Review.md

| # | 位置 | 修订前 | 修订后 | 原因 |
|---|------|--------|--------|------|
| 1 | 第 4.1.3 章 | "Candidate Schema 必须包含" | "tasks 表必须包含" | 08 定义统一任务表 |

---

## 3. 新增升级路径（UPG）

| 编号 | 升级项 | 阶段 | 影响范围 | 前提 |
|------|--------|------|----------|------|
| UPG-001 | Direct Call → Event Driven Migration | V2+ | 执行模式 | 当前 Direct Call 通过 Port Interface 隔离 |
| UPG-002 | In-Memory Cache → Redis Cache | V2+ | Runtime Cache | 当前 Cache 接口已抽象 |
| UPG-004 | Supabase pgvector → External Vector Store | V2+ | Vector Storage | vector_documents 表结构已抽象 |

> **注**：UPG-003 与 UPG-004 合并为 UPG-004。

---

## 4. MVP 范围收缩内容

以下功能/组件从 MVP 中移除或简化：

| # | 收缩项 | 原设计 | 修订后 | 原因 |
|---|--------|--------|--------|------|
| 1 | 独立队列表 | ingestion_queue / reflection_queue / archive_queue | 统一 `tasks` 表 | 简化 Schema |
| 2 | Chroma | 候选向量存储 | 仅 Supabase pgvector | 08 锁定 V1 方案 |
| 3 | Redis | 候选缓存 | 仅 In-Memory Cache | 08 锁定 V1 方案 |
| 4 | Cron 任务 | 06 中 V2 配置 Archive Cron | V1 不配置任何 Cron | 08 保留 V1 精简 |
| 5 | Archive Queue | 06 中列为 V2 新增 | 06 中保留但标注 V2 | 08 通过 tasks 表 type 区分 |
| 6 | Maintenance Queue | 06 中列为 V3 新增 | 06 中保留但标注 V3 | 08 通过 tasks 表 type 区分 |
| 7 | Memory Update/Delete | 原 API 可能有直接更新 | 仅允许 correctMemory()/archiveMemory() | 08 Memory Immutable |

---

## 5. Deferred 到 V2/V3 的内容

| # | 延期项 | 阶段 | 说明 |
|---|--------|------|------|
| 1 | Event Driven 升级（UPG-001） | V2+ | 从 Direct Call 升级到 Event Driven |
| 2 | Redis Cache（UPG-002） | V2+ | 从 In-Memory 升级到 Redis 分布式缓存 |
| 3 | 外部向量存储（UPG-004） | V2+ | 从 pgvector 升级到 Chroma/Qdrant/Weaviate |
| 4 | ARCHIVE 任务类型 | V2+ | tasks 表新增 ARCHIVE 类型 |
| 5 | Maintenance 任务类型 | V3+ | tasks 表新增 Maintenance 类型 |

---

## 6. 文档一致性检查结果

### 6.1 检查项

| # | 检查项 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 状态 |
|---|--------|----|----|----|----|----|----|----|----|------|
| 1 | Chroma 为必选 | ❌ 已修正 | ❌ 已修正 | — | — | — | — | — | ❌ 禁止 | ✅ |
| 2 | Redis 为必选 | — | — | — | — | — | — | — | ❌ 禁止 | ✅ |
| 3 | Project 独立建表 | — | — | — | ✅ 已确认 | — | — | — | ✅ 已确认 | ✅ |
| 4 | Agent 直接修改 Memory | — | — | — | — | — | — | ✅ 已约束 | ✅ 已约束 | ✅ |
| 5 | State 持久化 | — | — | — | — | ✅ 已确认 | ✅ 已确认 | — | ✅ 已确认 | ✅ |
| 6 | Memory 可直接 Update/Delete | — | — | — | — | — | — | ✅ 已约束 | ✅ 已约束 | ✅ |
| 7 | Event Driven 为 MVP 必需 | — | — | — | — | — | ✅ 已修正 | — | ✅ Direct Call | ✅ |
| 8 | reflect_tasks → tasks | — | — | ✅ 已修正 | ✅ 已修正 | ✅ 已修正 | ✅ 已修正 | ✅ 已修正 | ✅ 定义 | ✅ |
| 9 | Reflection Trigger | — | — | — | ✅ 已修正 | ✅ 已修正 | ✅ 已修正 | — | ✅ Evidence Driven | ✅ |
| 10 | 统一 tasks 表 | — | — | — | ✅ 已修正 | — | ✅ 已修正 | — | ✅ 定义 | ✅ |
| 11 | pgvector 为 V1 | — | ✅ 已修正 | — | — | — | — | — | ✅ 已锁定 | ✅ |
| 12 | In-Memory Cache 为 V1 | — | — | — | — | — | — | — | ✅ 已锁定 | ✅ |
| 13 | Memory Immutable | — | — | — | — | — | — | ✅ 已约束 | ✅ 已约束 | ✅ |
| 14 | Candidate 独立表 | — | — | — | — | — | — | ✅ 已约束 | ✅ 已定义 | ✅ |
| 15 | State 不落库 | — | — | — | — | ✅ 已确认 | ✅ 已确认 | — | ✅ 已确认 | ✅ |

### 6.2 检查结论

**所有 15 项检查均通过**。

01~07 中与 08 结论不一致的内容已全部修正。

---

## 7. 变更影响评估

### 7.1 对 Candidate Schema 的影响

| 影响 | 说明 |
|------|------|
| Candidate 独立表 | 新增 `candidates` 表，独立于 `memory_nodes` |
| Promotion 流程 | Candidate → Promotion → MemoryNode |
| Evidence 约束 | 每条 Candidate 必须携带证据链 |
| Agent 写入约束 | 仅 `ingestion_pipeline` 可写入 Candidate |

### 7.2 对 State Schema 的影响

| 影响 | 说明 |
|------|------|
| State 不落库 | 无独立 State 表 |
| State Cache | 短时缓存，保存引用（sourceBeliefIds/sourcePatternIds） |
| State 是引用 | 不保存完整内容 |

### 7.3 对 Queue 架构的影响

| 影响 | 说明 |
|------|------|
| 统一 tasks 表 | 替代原 5 个独立队列表 |
| Task Type 区分 | INGESTION / REFLECTION / ACTIVATION / ARCHIVE |
| Evidence Driven | Reflection 触发改为证据驱动 + Debounce |
| 保留 Retry/DLQ | 所有任务类型支持重试和死信队列 |

### 7.4 对 Vector Storage 的影响

| 影响 | 说明 |
|------|------|
| V1 锁定 pgvector | Supabase pgvector 为唯一 V1 向量存储 |
| Chroma 禁用 | 禁止引入 Chroma 作为 MVP 必需组件 |
| 预留升级 | vector_documents 表结构抽象，支持 V2+ 升级 |

### 7.5 对 API 设计的影响

| 影响 | 说明 |
|------|------|
| Memory Immutable | 禁止 updateMemory()/deleteMemory() |
| 新增 correctMemory() | 修正记忆，保留原始版本 |
| 新增 archiveMemory() | 归档记忆，不删除原始数据 |
| 新增 CORRECTS/SUPERSEDES 关系 | 记忆修正与替代关系 |

---

## 8. 文档版本演进

| 文档 | 原版本 | 新版本 | 变更类型 |
|------|--------|--------|----------|
| 01 | 1.3 | 1.4 | 示例修正 |
| 02 | 1.5 | 1.6 | 示例修正 |
| 03 | 1.4 | 1.5 | 表名修正 |
| 04 | 1.2 | 1.3 | 表名 + 触发修正 |
| 05 | 1.1 | 1.2 | 触发 + 组件修正 |
| 06 | 1.0 | 1.1 | 队列 + 触发修正 |
| 07 | 1.0 | 1.1 | 表名修正 |
| 08 | — | 1.0 | 新建 |

---

*本报告仅记录本次变更，不修改任何未列出的文档内容。*
