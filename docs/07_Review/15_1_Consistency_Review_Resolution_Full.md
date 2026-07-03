# Personal AI Memory Hub — 15_1 Consistency Review Resolution

> **版本**: 1.0
> **日期**: 2026-07-03
> **阶段**: Phase C — 一致性审查裁决
> **状态**: 已裁决
> **来源**: 15_Consistency_Review_Report_Full.md（Phase C Stage 1 一致性审查报告）
> **性质**: 官方裁决记录 — 对审查报告中每一项发现的正式裁定

---

## 1. Purpose

本文件是对 `15_Consistency_Review_Report_Full.md` 中全部 17 项发现（P0×2 + P1×8 + P2×5 + 额外 P0-03）的正式裁决记录。

每项发现裁定为以下之一：

- **Accepted（接受）** — 批准执行修正
- **Partially Accepted（部分接受）** — 批准执行修正，但限定范围或调整方式
- **Rejected（拒绝）** — 不执行，保留现状

本裁决成为 Phase C Stage 1 的官方决策记录。

---

## 2. Terminology Consistency — 术语一致性

### P0-01: "MemoryNode Level" 与 "Memory Pyramid Layer" 混用

- **裁定**: **Rejected**
- **原建议**: 在 01 §4 中统一采用"MemoryNode Level (L1-L4)"作为主术语
- **理由**: 三种命名体系各有上下文适用性。"记忆类型"适用于认知科学语境，"MemoryNode Level"适用于数据库/工程语境，"Memory Pyramid"适用于反射引擎语境。统一为单一术语会损失语境精确性。ChangeReport_03 已建立映射关系，足够清晰。

### P0-02: "State (L4)" 是否落库存在矛盾

- **裁定**: **Accepted**
- **原建议**: 统一声明 State 不在 memory_nodes 表中持久化。在 vector_documents 中 memory_level=4 添加注释说明
- **修正内容**: 在 09 §09.4.9 vector_documents 表的 memory_level 列注释中添加说明："memory_level = 4 仅用于向量检索元数据标记，不代表 State 作为 MemoryNode 持久化。State 是运行时认知状态（参见 05 §1.1）。"
- **理由**: memory_nodes 表的 CHECK 已正确排除 level=4。矛盾仅在于 vector_documents 表的 memory_level=4 语义不清。只需添加注释说明，不改动 schema。

### P1-01: "Evidence" vs "Observation" 术语混用

- **裁定**: **Accepted**
- **原建议**: 在 INDEX.md 或 01 的术语表中增加 Evidence vs Observation 的明确区分说明
- **修正内容**: 在 INDEX.md 的术语表部分增加 Evidence/Observation 关系说明
- **理由**: Evidence 和 Observation 在现有文档中确实存在语义模糊。澄清有助于 AI 开发者和人类开发者理解 Ingestion 流程。

### P1-02: "Reflection" vs "Reflect" 命名不一致

- **裁定**: **Rejected**
- **原建议**: 统一为"Reflection"作为名词，"reflect"作为动词
- **理由**: 文件名 04_Schema_Archive_Reflect.md 是历史产物，更改文件名涉及大量引用更新，风险大于收益。正文中 Reflection/reflect 的使用已在各文档中保持一致。此为 P1 级别，暂不执行。

### P1-03: "Archive" 语义在不同文档中略有差异

- **裁定**: **Partially Accepted**
- **原建议**: 在 05 §4 Archive 章节补充"Archive 是认知压缩，不是冷存储"
- **修正内容**: 仅在 05 §4 的 Archive 定义处补充一句说明，不修改其他文档
- **理由**: 04 的"不是冷存储"是关键区分，应在 05 中补充以保持一致性。但无需修改 10_1，因为其定义已足够清晰。
---

## 3. Naming Consistency — 命名一致性

### P1-04: 文档编号体系不一致

- **裁定**: **Rejected**
- **原建议**: 在 INDEX.md 中增加"文档编号体系说明"
- **理由**: 编号体系反映了文档生成的历史顺序和 Phase 划分。Phase A（01-09）和 Phase B（10_1-14）使用不同编号空间是有意为之。目录结构与文档编号的不对应是历史遗留，重构编号的风险远大于收益。

### P1-05: "Engine" 命名在 02 与 10_1 之间有差异

- **裁定**: **Partially Accepted**
- **原建议**: 在 02 中明确 ContextBuilder 是独立 Engine
- **修正内容**: 在 02 标题下方或 §1 中增加一句话说明："ContextBuilder 是独立 Engine（参见 10_1 §6.2 Engine #8），并非 MemoryEngine 的子组件。"
- **理由**: 02 标题"MemoryEngine ContextBuilder"确实容易引发误解，但修改标题涉及大量引用更新。采用轻量级补充说明即可解决。

### P2-01: 中英混用风格

- **裁定**: **Rejected**
- **理由**: 用户明确要求"Do NOT change document language"。Phase A 偏中文、Phase B 偏英文的风格差异保留。

---

## 4. Cross-Document References — 交叉引用

### P1-06: 10_5 (EntityService) 对 10_6 (TaskRuntime) 的引用不完整

- **裁定**: **Accepted**
- **原建议**: 在 10_5 §7 末尾添加引用："参考 10_6 §4 (Task Chaining via Events), §6 (Idempotency), §5.4 (Recovery)"
- **修正内容**: 在 10_5 §7.2 Merge Workflow 流程图之后添加参考引用段落
- **理由**: 10_5 §7 描述了 Merge 后通过 Task Runtime 异步执行的流程，但未引用 10_6 的具体规范，导致实现者需要跨文档查找 Task Chaining、Idempotency、Recovery 的细节。

### P1-07: 10_7 (API Entry) 对 G-050~G-055 的引用

- **裁定**: **Accepted**
- **原建议**: 在 10_7 §2 末尾添加："本节设计对应 Guidelines G-050~G-055（参见 13_Architecture_Guidelines 附录）"
- **修正内容**: 在 10_7 §2 末尾添加反向引用
- **理由**: 单向引用破坏了可追溯性。10_7 是 G-050~G-055 的来源文档，应反向引用。

### P1-08: ChangeReport 系列的引用完整性

- **裁定**: **Rejected**
- **原建议**: 在每个 ChangeReport 末尾添加"连锁影响"章节
- **理由**: 用户明确要求"Do NOT perform any additional refactoring"。ChangeReport 的孤立状态是历史产物，新增章节属于重构范畴。

### P1-09: 12_Engineering_Register 的"首次出现"引用不完整

- **裁定**: **Accepted**
- **原建议**: 修正 G-001 的"首次出现"为"13 §1"。调查 G-019 和 G-038 重复
- **修正内容**: 
  1. 修正 13 中 G-001 的"首次出现"字段（从"10_1"改为"13 §1"）
  2. 删除 G-038（见 P0-03）
  3. 修正 12 的 Guideline 汇总表中 G-001 的引用
- **理由**: G-001 确实在 13 §1 定义，10_1 只是引用源。G-019/G-038 重复是明确的错误。

### P2-02: INDEX.md 的文档状态跟踪

- **裁定**: **Rejected**
- **理由**: 用户指令限定为 Step 2 中明确列出的 9 项修正。INDEX.md 状态修正虽被报告识别，但未在 Step 2 的 Approved changes 列表中。保留现状。
---

## 5. Engineering Principles Consistency — 工程原则一致性

### P0-03: G-019 与 G-038 重复定义

- **裁定**: **Accepted**
- **原建议**: 删除 G-038，保留 G-019
- **修正内容**: 
  1. 从 13_Architecture_Guidelines.md 中删除 G-038 定义（§3 中 G-038 条目）
  2. 从 13 的 Guideline 汇总表中删除 G-038 行
  3. 从 12_Engineering_Register.md 的 Guideline 汇总表中删除 G-038 行
  4. 确保 13 §5 的 G-019 保留不变
- **理由**: 同一原则被定义两次违反 G-001 "One Capability, One Implementation"。这是必须修复的硬性错误。

### P1-10: "Service → Repository" 跨层规则在 10_1 与 08 之间有差异

- **裁定**: **Partially Accepted**
- **原建议**: 在 10_1 §6.3 的 Composite Engine 图示下方增加注释
- **修正内容**: 在 10_1 §6.3 的 MemoryEngine 图示与"MemoryEngine 不直接访问 Repository"文字之间，增加一行说明："MemoryEngine 作为 Composite Engine，其子 Engine（Archive/Evidence/Relationship/Candidate）均不直接访问 Repository。数据持久化由 MemoryService 编排完成。"
- **理由**: 图示确实可能误导读者认为 Composite Engine 可以直接访问 Repository。补充说明即可消除歧义，无需改动架构图。

### P1-11: TaskRuntime 的"Domain Agnostic"与"被 Service 编排"之间的关系

- **裁定**: **Accepted**
- **原建议**: 在 10_6 §2 增加说明："所有业务 Service 通过 TaskService 提交 Task，不直接调用 TaskRuntime。"
- **修正内容**: 在 10_6 §2.3 正确定位章节的文本描述后增加说明段落
- **理由**: 10_6 §2 强调 Domain Agnostic，但读者可能疑惑业务 Service 如何与 TaskRuntime 交互。明确 TaskService 为唯一入口即可。

### P2-03: 10_5 与 G-025 一致

- **裁定**: **N/A** — 无问题，无需裁决
---

## 6. Structure & Style Consistency — 文档结构与风格

### P2-04: 文档元数据格式不一致

- **裁定**: **Rejected**
- **理由**: 用户明确要求"Do NOT change document language"和"Do NOT normalize writing style"。

### P2-05: 版本号管理方式不一致

- **裁定**: **Rejected**
- **理由**: 同上，用户限定仅执行 Step 2 中明确列出的 9 项修正。

### P2-06: 部分文档缺少附录

- **裁定**: **Rejected**
- **理由**: 用户明确要求"Do NOT add appendices"。

### P2-07: 表格样式差异

- **裁定**: **Rejected**
- **理由**: 风格类问题，不在 Step 2 批准的修正范围内。

---

## 7. Document Completeness — 文档完整性

### P2-08: 14_Final_Implementation_Review 状态标记

- **裁定**: **Rejected**
- **理由**: 不在 Step 2 批准的修正范围内。

### P2-09: ChangeReport 系列完整性

- **裁定**: **Rejected**
- **理由**: 不在 Step 2 批准的修正范围内。

---

## 8. Resolution Summary Table

| Finding ID | 优先级 | 裁定 | 修正文档 | 修正内容 |
|------------|--------|------|----------|----------|
| P0-01 | P0 | Rejected | — | 术语体系各有适用语境，无需统一 |
| P0-02 | P0 | **Accepted** | 09 | 添加 State (L4) 在 vector_documents 中的注释说明 |
| P1-01 | P1 | **Accepted** | INDEX/01 | 增加 Evidence vs Observation 术语澄清 |
| P1-02 | P1 | Rejected | — | 文件名历史原因，不改 |
| P1-03 | P1 | **Partially Accepted** | 05 | 在 05 §4 补充 Archive 说明 |
| P1-04 | P1 | Rejected | — | 编号体系反映历史，不改 |
| P1-05 | P1 | **Partially Accepted** | 02 | 在 02 §1 增加 ContextBuilder 独立性说明 |
| P2-01 | P2 | Rejected | — | 语言风格差异保留 |
| P1-06 | P1 | **Accepted** | 10_5 | 添加 10_5 → 10_6 交叉引用 |
| P1-07 | P1 | **Accepted** | 10_7 | 添加 10_7 → 13 反向引用 |
| P1-08 | P1 | Rejected | — | 不在 Step 2 范围内 |
| P1-09 | P1 | **Accepted** | 13, 12 | 修正 G-001 引用，删除 G-038 |
| P2-02 | P2 | Rejected | — | 不在 Step 2 范围内 |
| P0-03 | P0 | **Accepted** | 13, 12 | 删除 G-038 重复定义 |
| P1-10 | P1 | **Partially Accepted** | 10_1 | 在 Composite Engine 图示下增加注释 |
| P1-11 | P1 | **Accepted** | 10_6 | 澄清 TaskService 为唯一入口 |
| P2-03 | P2 | N/A | — | 已确认一致 |
| P2-04 | P2 | Rejected | — | 风格不改 |
| P2-05 | P2 | Rejected | — | 风格不改 |
| P2-06 | P2 | Rejected | — | 不改附录 |
| P2-07 | P2 | Rejected | — | 风格不改 |
| P2-08 | P2 | Rejected | — | 不在 Step 2 范围内 |
| P2-09 | P2 | Rejected | — | 不在 Step 2 范围内 |

**裁定统计**:
- Accepted: 7 项
- Partially Accepted: 3 项
- Rejected: 13 项
- N/A: 1 项

---

## 9. Approved Changes Execution List

以下 9 项修正将在 Step 2 中执行：

1. **P0-03**: 删除 G-038 重复定义，保留 G-019
2. **P0-02**: 澄清 State (L4) 在 vector_documents 中的语义
3. **P1-01**: 在术语表中澄清 Evidence vs Observation
4. **P1-03**: 在 05 §4 补充 Archive 说明
5. **P1-06**: 在 10_5 §7 添加 → 10_6 交叉引用
6. **P1-07**: 在 10_7 §2 添加 → 13 反向引用
7. **P1-09**: 修正 G-001 首次出现引用 + 删除 G-038
8. **P1-10**: 在 10_1 §6.3 Composite Engine 图示下增加注释
9. **P1-11**: 在 10_6 §2 澄清 TaskService 为唯一入口

---

*本文件为 Phase C Stage 1 的官方裁决记录。*
*所有 Accepted 和 Partially Accepted 项目将在 Step 2 中执行。*
*Rejected 项目保留现状，不作任何修改。*
