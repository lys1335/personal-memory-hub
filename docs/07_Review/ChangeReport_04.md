# ChangeReport_04 — Review 变更报告

> **日期**: 2026-06-18  
> **触发文档**: `04_Schema_Archive_Reflect.md`  
> **被 Review 文档**: `01_MemoryHub_Foundation.md`、`02_MemoryEngine_ContextBuilder.md`、`03_Entity_MemoryGraph.md`  
> **Review 范围**: 结构冲突、名称冲突、设计冲突、过时描述

---

## 变更总览

| # | 源文档 | 修改内容 | 影响范围 | 兼容性 |
|---|--------|----------|----------|--------|
| 1 | 01 | 附录 A 术语表补充 5 个新术语 | 附录 A | ✅ 向后兼容 |
| 2 | 01 | 附录 B 版本号 1.1 → 1.2 | 附录 B | ✅ 无影响 |
| 3 | 02 | 第 5.3 节工作流图 `识别 Project` → `识别 Entity` | 第 5 章 | ✅ 语义升级 |
| 4 | 02 | 第 6.1 节架构图 `Layer 2: Project Memory` → `Current Entity Memory` | 第 6 章 | ✅ 语义升级 |
| 5 | 02 | 第 6.3 节标题和内容 `Project Memory` → `Current Entity Memory` | 第 6 章 | ✅ 语义升级 |
| 6 | 02 | 第 7.1 节预算表 `项目相关` → `Entity 相关` | 第 7 章 | ✅ 语义升级 |
| 7 | 02 | 第 11 章架构图 `PROJ[Project]` → `ENTITY[Entity]` | 第 11 章 | ✅ 语义升级 |
| 8 | 02 | 第 11 章架构图 `ID_PROJ` → `ID_ENT` | 第 11 章 | ✅ 语义升级 |
| 9 | 02 | 附录 A 术语表补充 5 个新术语 | 附录 A | ✅ 向后兼容 |
| 10 | 02 | 附录 B 版本号 1.1 → 1.2 | 附录 B | ✅ 无影响 |
| 11 | 03 | ADR-011 核心表从 5 张扩展为 11 张 | 第 9 章 | ✅ 信息补充 |
| 12 | 03 | 第 11 章数据流补充 `vector_documents` 和 `reflect_tasks` | 第 11 章 | ✅ 信息补充 |
| 13 | 03 | 附录 C 版本号 1.0 → 1.1 | 附录 C | ✅ 无影响 |

---

## 详细变更说明

### 变更 1：01 附录 A 术语表补充新术语

**修改内容**：

在术语表中新增 5 个术语：

| 术语 | 说明 |
|------|------|
| Workspace | 顶层容器，支持单用户/家庭/团队场景（参见 04） |
| MemoryNode | 记忆节点，通过 Level 区分类型（L1-L4）（参见 03/04） |
| Reflect | 认知分析任务，负责思考；Archive 负责总结（参见 04） |
| Archive | 认知压缩层，不是冷存储（参见 04） |
| vector_documents | 独立向量层，存储高价值内容的 embedding（参见 04） |

**修改原因**：

- 04 引入了 Workspace、MemoryNode、Reflect、Archive、vector_documents 等新概念。
- 01 作为总纲文档，术语表应覆盖所有后续文档中的核心术语。

**影响范围**：

- 01 附录 A。

**是否破坏兼容性**：✅ 否。纯补充。

---

### 变更 2：02 第 5.3 节工作流图 `识别 Project` → `识别 Entity`

**修改内容**：

- Mermaid 图中 `PROJ[识别 Project]` 替换为 `ENT[识别 Entity]`。
- 流程说明第 3 步从"识别 Project"更新为"识别 Entity"，增加注释"Project 也作为 Entity 存储，参见 04"。

**修改原因**：

- 04 明确 Project 不再单独建表，而是作为 `entities.entity_type = 'Project'` 存储。
- 02 的 Context Builder 工作流中"识别 Project"应更新为"识别 Entity"，与 04 保持一致。

**影响范围**：

- 02 第 5.3 节。

**是否破坏兼容性**：✅ 否。语义升级，不影响逻辑。

---

### 变更 3：02 第 6.1 节架构图 `Layer 2: Project Memory` → `Current Entity Memory`

**修改内容**：

- Mermaid 图中 `L2[Layer 2: Project Memory]` 替换为 `L2[Layer 2: Current Entity Memory]`。

**修改原因**：

- 04 第 15 章 Context Builder 最终设计中，Layer 2 名称为"Current Entity"而非"Project Memory"。

**影响范围**：

- 02 第 6.1 节。

**是否破坏兼容性**：✅ 否。

---

### 变更 4：02 第 6.3 节标题和内容更新

**修改内容**：

- 标题从"Layer 2 — Project Memory"更新为"Layer 2 — Current Entity Memory"。
- 内容从"当前 Project 相关记忆"更新为"当前 Entity 相关记忆"。
- 范围说明增加"Project 也作为 Entity 存储，参见 04"。

**修改原因**：

- 与 04 第 15 章 Context Builder 最终设计对齐。

**影响范围**：

- 02 第 6.3 节。

**是否破坏兼容性**：✅ 否。

---

### 变更 5：02 第 7.1 节预算表更新

**修改内容**：

- Layer 2 的说明从"项目相关，次重要"更新为"Entity 相关，次重要"。

**修改原因**：

- 与 Layer 2 名称变更保持一致。

**影响范围**：

- 02 第 7.1 节。

**是否破坏兼容性**：✅ 否。

---

### 变更 6-7：02 第 11 章架构图更新

**修改内容**：

- `ORG_MODEL` 子图中 `PROJ[Project]` → `ENTITY[Entity]`。
- `CBLayer` 子图中 `ID_PROJ[识别Project]` → `ID_ENT[识别Entity]`。
- 连线 `ID_AREA --> ID_PROJ` → `ID_ENT`，`ID_PROJ --> R_CALL` → `ID_ENT --> R_CALL`。

**修改原因**：

- 与 04 的 Entity 统一模型对齐。
- 架构图需要反映最新的组织模型。

**影响范围**：

- 02 第 11 章。

**是否破坏兼容性**：✅ 否。

---

### 变更 8：02 附录 A 术语表补充新术语

**修改内容**：

在术语表末尾新增 5 个术语（与变更 1 相同）。

**修改原因**：

- 与 01 保持一致，确保两份文档术语表覆盖相同的术语集。

**影响范围**：

- 02 附录 A。

**是否破坏兼容性**：✅ 否。

---

### 变更 9：03 ADR-011 核心表从 5 张扩展为 11 张

**修改内容**：

| 原表数 | 新表数 | 新增表 |
|--------|--------|--------|
| 5 | 11 | `vector_documents`、`tag_links`、`reflect_tasks`、`user_profiles` |

同时更新"下一步"说明，增加对 04 的引用。

**修改原因**：

- 04 明确核心表为 11 张，03 的 ADR-011 需要反映最新设计结论。

**影响范围**：

- 03 第 9 章。

**是否破坏兼容性**：✅ 否。信息补充。

---

### 变更 10：03 第 11 章数据流总结补充

**修改内容**：

- 持久化行从 `entities/memory_nodes/relationships/archives/tags` 更新为 `entities/memory_nodes/relationships/archives/tags/vector_documents/reflect_tasks`。

**修改原因**：

- 与 ADR-011 的 11 张表清单保持一致。

**影响范围**：

- 03 第 11 章。

**是否破坏兼容性**：✅ 否。

---

## Review 结论

| 检查项 | 结果 |
|--------|------|
| 结构冲突 | ✅ 已修复（02 的 Project 层级与 04 的 Entity 统一模型） |
| 名称冲突 | ✅ 已修复（Layer 2: Project Memory → Current Entity Memory） |
| 设计冲突 | ✅ 已修复（03 ADR-011 核心表数量从 5 扩展到 11） |
| 过时描述 | ✅ 已修复（01/02 术语表、03 数据流总结） |
| 兼容性影响 | ✅ 无破坏性变更 |

**总体评估**：四份文档现在在设计上完全一致。01 定义宏观分类，02 定义 API 与上下文构建，03 定义数据建模，04 定义 Schema/Archive/Reflect。各文档通过交叉引用保持关联。
