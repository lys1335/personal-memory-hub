# ChangeReport_06

> **日期**: 2026-06-20  
> **触发文档**: `06_Runtime_Architecture.md`  
> **被 Review 文档**: `01`、`02`、`03`、`04`、`05`  
> **Review 范围**: 术语统一、命名统一、Lifecycle 统一、State 定义统一、Evidence Based Memory 统一、Reflection 流程统一、Runtime 引用统一、Project Entity 定义统一

---

## 1. 新增内容（06 文档）

| 新增项 | 章节 | 说明 |
|--------|------|------|
| Runtime 分层架构 | 第 2 章 | Online Runtime / Offline Runtime 两层模型，严格分离 |
| 6 个核心 Engine 定义 | 第 3 章 | Ingestion/Reflection/Activation/Retrieval/Context Builder/Scheduler |
| Sync / Async Boundary | 第 4 章 | 影响当前回答的流程必须同步，不影响当前回答的流程必须异步 |
| Queue Architecture | 第 5 章 | Ingestion/Reflection/Activation（MVP）+ Archive（V2）+ Maintenance（V3） |
| Scheduler Architecture | 第 6 章 | 事件驱动 + Cron 驱动混合架构，V1 保留 Cron 能力但不配置任务 |
| LLM vs Rule Boundary | 第 7 章 | Rule 负责正确性，LLM 负责洞察力，禁止 LLM 直接控制系统状态 |
| Reflection Flow 完整流程图 | 第 8 章 | Observation → Candidate → Pattern → Belief，禁止 Observation → Belief 直接跳跃 |
| Activation Flow 完整流程图 | 第 9 章 | State = Belief + Current Context，Activation ≠ Ranking |
| Conversation Window Manager | 第 9.4 章 | 维护 Recent Message Window / Area Focus Score / Entity Focus Score |
| Multi Active Areas 原则 | 第 9.3 章 | 允许同时激活多个 Area 下的 Belief |
| Context Builder 内部模块 | 第 10 章 | Context Ranker / Context Compressor / Context Assembler |
| Runtime Sequence 时序图 | 第 11 章 | Online / Offline 完整流程的 Mermaid sequence diagram |
| 版本路线图 | 第 12 章 | MVP / V2 / V3 各阶段组件清单 |
| Engine 接口概要 | 附录 A | 6 个 Engine 的输入/输出定义 |

---

## 2. 更新内容（06 文档自身）

| 更新项 | 章节 | 说明 |
|--------|------|------|
| 6 个 Engine 职责定义 | 第 3 章 | 每个 Engine 的输入/输出/内部阶段/约束完整定义 |
| Light Reflect 触发条件 | 第 8.3 章 | 确认 Queue 满或兜底定时，与 05 一致 |
| Heavy Reflect 触发条件 | 第 8.3 章 | 每日/每周定时，与 05 一致 |
| State 非持久化声明 | 第 9.1 章 | 明确 State 是运行时激活结果，不写入数据库 |
| Context 优先级 | 第 10.2 章 | State > Belief > Pattern > Observation |
| Token Budget 要求 | 第 10.4 章 | Context Builder 必须支持 |
| Context Source Trace 要求 | 第 10.4 章 | 每条 Context 必须可追溯来源 |

---

## 3. 回溯修改内容（01-05）

### 01_MemoryHub_Foundation.md

| # | 修改内容 | 原因 |
|---|----------|------|
| 1 | 附录 A 术语表补充 6 个 Engine 术语 | 术语统一 |
| 2 | 版本号 1.2 → 1.3 | 变更记录 |

### 02_MemoryEngine_ContextBuilder.md

| # | 修改内容 | 原因 |
|---|----------|------|
| 1 | 第 3.1 节轻实时模式：补充走 Ingestion Pipeline 的说明 | 06 明确所有输入必须经过 Ingestion Engine 的完整 Pipeline |
| 2 | 第 12 章数据流总结：更新为 Online Path 流程 | 06 定义了 User Query → Retrieval → Activation → Context Builder → LLM |
| 3 | 附录 A 术语表：补充 6 个 Engine 术语 | 术语统一 |
| 4 | 版本号 1.4 → 1.5 | 变更记录 |

### 03_Entity_MemoryGraph.md

| # | 修改内容 | 原因 |
|---|----------|------|
| 1 | ADR-010 补充 05 Reflection Workflow 引用 | 05 给出了完整的 8 Phase Reflection Workflow |
| 2 | 附录 B 术语表：补充 6 个 Engine 术语 | 术语统一 |
| 3 | 版本号 1.3 → 1.4 | 变更记录 |

### 04_Schema_Archive_Reflect.md

| # | 修改内容 | 原因 |
|---|----------|------|
| 1 | 第 15.5 章新增：Context Builder 内部模块说明 | 06 第 10.3 章定义了 Ranker/Compressor/Assembler |
| 2 | 附录 C 新增：术语表（6 个 Engine） | 术语统一 |
| 3 | 版本号 1.1 → 1.2 | 变更记录 |

### 05_MemoryLifecycle_ReflectionEngine.md

| # | 修改内容 | 原因 |
|---|----------|------|
| 1 | 第 14.1 章 Runtime Components：补充 Retrieval Engine | 05 原列表遗漏了 Retrieval Engine |
| 2 | 第 14.6 章组件交互图：补充 Retrieval Engine → Context Builder 连线 | 与 06 架构一致 |
| 3 | 版本号 1.0 → 1.1 | 变更记录 |

---

## 4. 对 01-05 产生影响的位置

### 4.1 术语统一

| 术语 | 01 之前 | 06 之后 |
|------|---------|---------|
| 输入处理组件 | "分类器" | "Ingestion Engine" |
| 认知分析组件 | "derive 引擎" | "Reflection Engine" |
| 状态生成组件 | "Current State"（未明确） | "Activation Engine" |
| 检索组件 | "Recall" | "Retrieval Engine" |
| 上下文构建 | "Context Builder" | "Context Builder（含 Ranker/Compressor/Assembler）" |
| 任务调度 | 未提及 | "Scheduler" |

### 4.2 命名统一

| 概念 | 02 之前 | 06 之后 |
|------|---------|---------|
| 轻实时模式 | "立即进入记忆系统" | "立即进入 Ingestion Pipeline" |
| 数据流 | "识别 Area → 识别 Project → Recall" | "Retrieval → Activation → Context Builder → LLM" |

### 4.3 Lifecycle 统一

| 层级 | 01 之前 | 06 之后 |
|------|---------|---------|
| Daily | 30~90 天 | 保留（短期缓存，不影响 Evidence Based 原则） |
| Topic Window | 约 1 年 | 保留（可重建，非关键数据） |
| Monthly Archive | 永久 | 保留（04 第 12 章定义） |
| Observation | 未明确 | 永不删除（05 第 1.3 章） |
| Pattern | 未明确 | 永久保存（05 第 1.3 章） |
| Belief | 未明确 | 永久保存并允许动态修正（05 第 1.3 章） |
| State | 未明确 | 运行时激活，不持久化（06 第 9.1 章） |

### 4.4 State 定义统一

| 文档 | 之前描述 | 06 之后 |
|------|---------|---------|
| 01 | 未涉及 | 未涉及（宏观视角） |
| 02 | "Current State = f(Observations, Beliefs)" | "State = Belief + Current Context（运行时激活，非持久化实体）" |
| 03 | "实体的当前状态结论" | "实体的当前状态结论（运行时激活，非持久化实体，参见 05 第 12 章）" |
| 04 | 未涉及 | 未涉及 |
| 05 | 已明确"运行时激活" | 已明确 |
| 06 | — | "State 不是持久化实体，是 Belief 在当前上下文中的运行时激活结果" |

### 4.5 Evidence Based Memory 统一

| 文档 | 之前 | 06 之后 |
|------|------|---------|
| 05 | 已明确废弃 Time Based | 已明确 |
| 04 | Memory Verification（基于证据而非时间） | 已修正 |
| 02 | 未涉及 | 未涉及（02 是 API 层，不涉及证据模型） |

### 4.6 Reflection 流程统一

| 文档 | 之前 | 06 之后 |
|------|------|---------|
| 05 | 8 Phase Workflow | 已明确 |
| 04 | Light Reflect "每次 Conversation 后" | 修正为"Queue 满触发" |
| 06 | 完整 Reflection Flow 图 | Observation → Candidate → Pattern → Belief，禁止跳跃 |

### 4.7 Runtime 引用统一

| 文档 | 之前 | 06 之后 |
|------|------|---------|
| 02 | "Memory Engine"（未细分） | 6 个 Engine 各司其职 |
| 04 | "reflect()" API | 明确 Reflection Engine 的职责 |
| 05 | "Runtime Components"（5 个） | 扩展为 6 个（补充 Retrieval Engine） |

### 4.8 Project Entity 定义统一

| 文档 | 之前 | 06 之后 |
|------|------|---------|
| 03 | Project 作为 Entity Type | 保留 |
| 04 | Project 不再单独建表 | 保留 |
| 02 | "识别 Project" | 修正为"识别 Entity"（Project 也是 Entity） |
| 06 | 不涉及 | 不涉及 |

---

## 5. 后续待设计项

以下项目需在下一阶段 Implementation Architecture 中设计：

### 5.1 待设计 Schema

| 项目 | 优先级 | 说明 | 依赖 |
|------|--------|------|------|
| Candidate Schema | P1 | Candidate Pattern 的正式数据结构 | 06 第 8.2 章 |
| State Schema | P1 | State 运行时激活的数据结构（虽不持久化，但需定义输入/输出） | 06 第 9 章 |
| Context Package Schema | P1 | Context Builder 输出的 Context 包结构 | 06 第 10 章 |

### 5.2 待设计 Engine 接口

| Engine | 需设计内容 | 优先级 |
|--------|-----------|--------|
| Ingestion Engine | `ingest(conversation: Conversation) → Observation[]` | P1 |
| Reflection Engine | `reflect(observation_pool: Observation[]) → (Pattern[], Belief[])` | P1 |
| Activation Engine | `activate(query: Query, beliefs: Belief[]) → State[]` | P1 |
| Retrieval Engine | `retrieve(query: Query) → MemoryResult[]` | P1 |
| Context Builder | `build(retrieval: MemoryResult[], states: State[]) → PromptContext` | P1 |
| Scheduler | `schedule(event: Event) → EngineMethodCall` | P2 |

### 5.3 待设计 Queue 实现

| Queue | MVP | V2 | V3 |
|-------|-----|----|----|
| Ingestion Queue | ✅ 需设计 | — | — |
| Reflection Queue | ✅ 需设计 | — | — |
| Activation Queue | ✅ 需设计 | — | — |
| Archive Queue | — | ✅ 需设计 | — |
| Maintenance Queue | — | — | ✅ 需设计 |

### 5.4 待设计 LLM Propose → Rule Verify → Commit 协议

| 需设计内容 | 说明 |
|-----------|------|
| Propose 格式 | LLM 输出的结构化 Propose 数据格式 |
| Verify 规则 | Rule 层的验证规则清单 |
| Commit 协议 | 验证通过后写入数据库的事务协议 |

### 5.5 待设计 Conversation Window Manager 实现

| 需设计内容 | 说明 |
|-----------|------|
| Message Window Size | 维护最近多少条消息 |
| Area Focus Algorithm | 如何计算 Area 活跃度 |
| Entity Focus Algorithm | 如何计算 Entity 活跃度 |

---

## 6. 文档版本汇总

| 文档 | 最终版本 | 变更次数 |
|------|----------|----------|
| 01 | 1.3 | 3 次 |
| 02 | 1.5 | 5 次 |
| 03 | 1.4 | 4 次 |
| 04 | 1.2 | 3 次 |
| 05 | 1.1 | 2 次 |
| 06 | 1.0 | 新建 |

---

*本文档仅记录 06 引入的变更，不包含 01-05 之间的历史变更（参见各文档附录 B/C）。*
