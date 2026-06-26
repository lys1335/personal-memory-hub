# Personal AI Memory Hub — Schema / Archive / Reflect 设计文档

> **版本**: 1.0  
> **日期**: 2026-06-18  
> **阶段**: 第四阶段  
> **状态**: 已确认  
> **作者**: 系统架构组

---

## 1. 设计目标

### 1.1 为什么需要长期可演进 Schema

Memory Hub 是个人 AI 平台的长期记忆基础设施，设计目标是支撑未来 5~10 年的持续使用。

**核心挑战**：

* 用户认知会随时间变化
* 新场景会带来新数据类型
* 模型能力会持续进步
* 存储成本会下降
* 检索需求会增长

如果 Schema 设计过于固化，每次需求变化都需要迁移数据库，这将：

1. 增加维护成本
2. 产生停机风险
3. 阻碍功能迭代速度

**设计原则**：

> 未来新增能力时，主要新增数据，而非修改 Schema。

### 1.2 优先考虑未来 5~10 年扩展

本阶段 Schema 设计围绕以下长期目标展开：

* **统一 Node 模型** — 所有记忆内容统一为 MemoryNode，通过 Level 区分
* **统一 Edge 模型** — 所有关系统一为 Relationship，通过 type 区分
* **统一检索模型** — Graph + Vector + Archive + Context Builder 协同
* **多 Workspace 支持** — 单用户 / 家庭 / 团队场景无缝扩展
* **向量化分层** — 不是所有数据都向量化，按价值分层
* **Reflect 可解释** — 推导链完整记录，支持 Explainable Memory

---

## 2. 最终核心表结构

### 2.1 核心表清单

共 **11 张核心表**：

| # | 表名 | 说明 |
|---|------|------|
| 1 | `workspace` | 顶层容器，支持单用户/家庭/团队 |
| 2 | `user_profiles` | 用户档案 |
| 3 | `areas` | 一级领域划分 |
| 4 | `entities` | 实体（Project 也作为 Entity 存储） |
| 5 | `memory_nodes` | 记忆节点（Observation/Pattern/Belief/State） |
| 6 | `relationships` | 实体间关系 |
| 7 | `vector_documents` | 独立向量层 |
| 8 | `tags` | 标签体系 |
| 9 | `tag_links` | 标签关联 |
| 10 | `archives` | 归档数据 |
| 11 | `tasks` | 统一任务表（替代原 ingestion_queue / reflection_queue / archive_queue） |

### 2.2 Project 不再单独建表

**决策**：Project 作为 `entities` 表中 `entity_type = 'Project'` 的记录存储。

**理由**：

* Project 本质上也是一个 Entity，具有生命周期和状态变化。
* 与 Area、Object 等共用同一张表，减少表数量。
* 通过 `parent_id` 和 `entity_type` 区分层级关系。
* 与 03 ADR-003（Entity Type 体系）一致。

---

## 3. Workspace / Area / Entity 结构

### 3.1 最终结构

```
Workspace
  ↓
  User
    ↓
    Area
      ↓
      Entity
        ├─ entity_type = Project
        ├─ entity_type = Object
        ├─ entity_type = Person
        └─ ...
```

### 3.2 说明

* **Workspace** — 顶层容器，一个 Workspace 可包含多个 User。
* **User** — 系统使用者，通过 `user_profiles` 表管理。
* **Area** — 一级领域划分（AI / Work / Family / Finance 等），通过 `areas` 表管理。
* **Entity** — 所有实体统一存储在 `entities` 表中，通过 `entity_type` 区分。

### 3.3 未来扩展无需迁移 Schema

以下新增类型均可通过 `entities.entity_type` 字段扩展：

| 新增类型 | entity_type 值 | 说明 |
|----------|---------------|------|
| Agent | `agent` | AI Agent |
| Tool | `tool` | 使用的工具 |
| Model | `model` | AI 模型 |
| Document | `document` | 文档 |
| Person | `person` | 人物 |

**关键原则**：

> 未来新增 Entity Type 只需插入新数据，无需修改 Schema。

---

## 4. 主键与外键设计

### 4.1 统一原则：全部 UUIDv7

**决策**：所有表的主键和外键均使用 `UUIDv7`，禁止使用自增 ID。

### 4.2 使用 UUIDv7 的理由

| 理由 | 说明 |
|------|------|
| 时间有序 | UUIDv7 包含时间戳，天然按创建时间排序，利于范围查询 |
| 分布式友好 | 多节点生成 UUID 不会产生冲突，适合未来多 Workspace 同步 |
| 兼容 Supabase | Supabase 原生支持 UUID 类型和索引 |
| 兼容 SQLite | SQLite 可通过扩展支持 UUID |
| 导入导出安全 | UUID 不暴露内部序列号，导出时无需担心 ID 碰撞 |
| 多 Workspace 隔离 | 不同 Workspace 的 UUID 不会冲突，支持合并 |
| Graph 扩展 | 未来迁移 Neo4j/Memgraph 时，UUID 可直接映射为节点 ID |

### 4.3 外键关系图

```
workspace (id)
  ├─ user_profiles (workspace_id)
  │     └─ areas (workspace_id)
  │           └─ entities (workspace_id, area_id, parent_id)
  │                 ├─ memory_nodes (entity_id)
  │                 └─ relationships (source_id, target_id)
  ├─ vector_documents (workspace_id)
  ├─ tags (workspace_id)
  ├─ tag_links (workspace_id)
  ├─ archives (workspace_id)
  └─ tasks (workspace_id)
```

### 4.4 核心外键约束

| 子表 | 外键列 | 引用表 | 引用列 | 说明 |
|------|--------|--------|--------|------|
| user_profiles | workspace_id | workspace | id | 用户属于 Workspace |
| areas | workspace_id | workspace | id | 领域属于 Workspace |
| areas | parent_area_id | areas | id | 领域可嵌套（可选） |
| entities | workspace_id | workspace | id | 实体属于 Workspace |
| entities | area_id | areas | id | 实体属于 Area |
| entities | parent_entity_id | entities | id | 实体可嵌套（如 Project → SubProject） |
| entities | user_id | user_profiles | id | 实体创建者 |
| memory_nodes | entity_id | entities | id | 记忆节点属于 Entity |
| memory_nodes | parent_node_id | memory_nodes | id | 记忆节点可嵌套 |
| relationships | source_id | entities | id | 关系起点 |
| relationships | target_id | entities | id | 关系终点 |
| vector_documents | workspace_id | workspace | id | 向量文档属于 Workspace |
| vector_documents | entity_id | entities | id | 向量文档关联 Entity |
| vector_documents | memory_node_id | memory_nodes | id | 向量文档关联 MemoryNode |
| tags | workspace_id | workspace | id | 标签属于 Workspace |
| tag_links | workspace_id | workspace | id | 标签关联属于 Workspace |
| tag_links | tag_id | tags | id | 标签关联指向 Tag |
| archives | workspace_id | workspace | id | 归档属于 Workspace |
| archives | source_archive_id | archives | id | 归档可嵌套（Yearly 包含 Monthly） |
| tasks | workspace_id | workspace | id | 统一任务表属于 Workspace |

---

## 5. Memory 模型

### 5.1 MemoryNode 层级

MemoryNode 是 `memory_nodes` 表中的记录，通过 `level` 字段区分类型：

| Level | 类型 | 说明 | 价值 |
|-------|------|------|------|
| L1 | Observation | 事实记录，保留历史 | 基础 |
| L2 | Pattern | 从 Observation 中归纳出的模式 | 提升 |
| L3 | Belief | AI 基于 Pattern 形成的认知推断 | 再提升 |
| L4 | State | 实体的当前状态结论 | 最高 |

**核心认知**：

> Observation → Pattern → Belief → State  
> 价值逐层提升。

### 5.2 Memory 全部保留

**决策**：Memory 永不因归档而删除。

**理由**：

* 所有 MemoryNode 永久保留在 `memory_nodes` 表中。
* Archive 是认知压缩，不是数据搬迁。
* 原始 Observation 是推导链的起点，不可丢失。
* 未来模型能力提升后，可重新分析历史 Observation。

### 5.3 新增：memory_relationships（概念设计）

**计划新增表**：`memory_relationships`

**用途**：MemoryNode 之间的关系。

**支持的关系类型**：

| 关系 | 说明 | 示例 |
|------|------|------|
| `derived_from` | 推导来源 | Belief derived_from Pattern |
| `supports` | 支持 | Observation supports Belief |
| `contradicts` | 矛盾 | Observation contradicts Belief |
| `attenuates` | 减弱 | 新证据削弱原有 Belief 的置信度 |

**设计意义**：

* 形成 Memory Graph，连接 MemoryNode 之间的语义关系。
* 支持 Explainable Memory：AI 能解释某个 Belief 是如何从 Observation 推导出来的。
* 与 `relationships` 表互补：前者连接 Entity，后者连接 MemoryNode。

---

## 6. Relationship 模型

### 6.1 统一进入 relationships 表

**决策**：所有关系统一存储在 `relationships` 表中，禁止为不同关系单独建表。

### 6.2 核心关系列表

采用"核心关系 + 可扩展"策略，第一版包含 10 种核心关系：

| 关系 | 方向 | 说明 | 示例 |
|------|------|------|------|
| `belongs_to` | 子→父 | 隶属关系 | Project belongs_to Area |
| `part_of` | 部分→整体 | 组成部分 | Entity part_of Workspace |
| `uses` | 使用者→工具 | 使用关系 | Project uses Supabase |
| `depends_on` | 依赖方→被依赖方 | 依赖关系 | Project depends_on API |
| `related_to` | 双向 | 一般关联 | Entity related_to Entity |
| `affects` | 影响方→受影响方 | 影响关系 | Decision affects Project |
| `derived_from` | 推导方→源数据 | 推导来源 | Belief derived_from Observation |
| `owns` | 所有者→被拥有 | 拥有关系 | User owns Entity |
| `created_by` | 产物→创造者 | 创建关系 | Project created_by User |
| `about` | 内容→主题 | 主题关联 | Observation about User |

### 6.3 relationships 表关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDv7 | 主键 |
| workspace_id | UUIDv7 | 所属 Workspace |
| source_id | UUIDv7 | 关系起点 Entity ID |
| target_id | UUIDv7 | 关系终点 Entity ID |
| relationship_type | VARCHAR | 关系类型（10 种核心 + 可扩展） |
| strength | FLOAT | 关系强度（0.0~1.0，可选） |
| created_at | TIMESTAMP | 创建时间 |
| metadata | JSONB | 扩展元数据 |

---

## 7. Vector Layer 设计

### 7.1 新增 vector_documents 表

**决策**：使用独立的 `vector_documents` 表存储向量数据，不要把 embedding 直接放入 `memory_nodes`。

### 7.2 原因

| 原因 | 说明 |
|------|------|
| 性能 | embedding 列体积大，影响查询性能 |
| 灵活性 | 不同场景使用不同的 embedding 模型 |
| 独立性 | 向量检索与记忆存储解耦 |
| 扩展性 | 未来支持多种向量数据库（pgvector / Qdrant / Milvus） |

### 7.3 vector_documents 建议字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDv7 | 主键 |
| workspace_id | UUIDv7 | 所属 Workspace |
| source_type | VARCHAR | 来源类型（memory_node / archive / entity_summary） |
| source_id | UUIDv7 | 来源记录 ID |
| area_id | UUIDv7 | 所属 Area |
| entity_id | UUIDv7 | 所属 Entity |
| memory_level | INTEGER | MemoryNode Level（L1-L4） |
| importance_score | FLOAT | 重要性评分（0.0~1.0） |
| content | TEXT | 原始内容 |
| embedding | VECTOR(1536) | 向量嵌入（pgvector 格式） |
| created_at | TIMESTAMP | 创建时间 |

---

## 8. 向量化策略

### 8.1 两层分离

| 层 | 表 | 定位 |
|----|----|------|
| 全量事实库 | `memory_nodes` | 保留所有 Observation，不向量化 |
| 高价值认知索引 | `vector_documents` | 仅向量化高价值内容 |

### 8.2 各 Level 向量化策略

| Level | 类型 | 向量化策略 | 说明 |
|-------|------|-----------|------|
| L1 | Observation | **选择性** | 通过 importance_gate 过滤，不全部向量化 |
| L2 | Pattern | **100%** | 模式具有较高检索价值 |
| L3 | Belief | **100%** | 认知推断是核心检索目标 |
| L4 | State | **100%** | 当前状态是高频查询内容 |

### 8.3 向量库的定位

> 向量库不是事实仓库，而是认知入口。

**理由**：

* Observation 是事实，通过 `memory_nodes` 表直接查询。
* Pattern / Belief / State 是认知，通过向量检索快速定位。
* 避免大量低价值 Observation 淹没高价值 Belief 的检索结果。

---

## 9. 检索排序策略

### 9.1 Final Score 公式

```
Final Score = Similarity + Importance
```

### 9.2 参数说明

| 参数 | 来源 | 说明 |
|------|------|------|
| Similarity | 向量余弦相似度 | 语义匹配程度 |
| Importance | importance_score 字段 | 内容重要性评分 |

### 9.3 设计意图

> 避免大量低价值 Observation 淹没高价值 Belief。

**理由**：

* 纯向量相似度检索会将所有同语义内容排在前列，不考虑价值差异。
* 加入 Importance 评分后，高价值认知（Pattern/Belief/State）在检索结果中优先展示。
* Observation 虽然保留全部，但重要性评分较低，不会过度干扰检索结果。

---

## 10. pgvector 策略

### 10.1 MVP 方案

**技术栈**：Supabase + pgvector（ivfflat 索引）

**理由**：

* Supabase 原生支持 PostgreSQL，pgvector 是 PostgreSQL 扩展。
* ivfflat 索引在 MVP 阶段性能足够，实现简单。
* 无需引入额外的向量数据库服务。
* 降低初期运维成本。

### 10.2 Future Upgrade Path

**明确记录未来升级路线，避免后续遗忘**：

| 阶段 | 方案 | 升级条件 |
|------|------|----------|
| MVP | Supabase + pgvector (ivfflat) | 数据量 < 100 万条 |
| 升级 1 | Supabase + pgvector (hnsw) | 数据量增长，ivfflat 性能不足 |
| 升级 2 | 独立向量数据库 (Qdrant / Milvus / Weaviate) | 需要分布式部署、多副本、跨云同步 |

**升级策略**：

* 所有向量数据存储在 `vector_documents.embedding` 列中。
* 升级时只需更换向量检索引擎，不修改 Schema。
* 通过抽象层隔离向量数据库实现，方便切换。

---

## 11. Tag 体系

### 11.1 三层 Tag

| 层 | 类型 | 来源 | 说明 |
|----|------|------|------|
| 1 | System Tag | 系统自动生成 | 技术栈、工具名、框架名 |
| 2 | AI Tag | AI 自动维护 | 从内容中自动提取的主题标签 |
| 3 | User Tag | 用户手动创建 | 用户自定义的分类标签 |

### 11.2 tags 表新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| tag_type | VARCHAR | 取值：`system` / `ai` / `user` |

### 11.3 设计原则

| 原则 | 说明 |
|------|------|
| Tag 是元数据 | 不是主要交互入口 |
| AI 自动维护 | 系统根据内容自动打标签 |
| 用户可修改 | 用户可以调整 AI 生成的标签 |
| 不要求用户维护 | 用户不需要主动管理标签体系 |

### 11.4 tag_links 表

用于建立 Tag 与 Entity / MemoryNode / Archive 的多对多关联：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDv7 | 主键 |
| workspace_id | UUIDv7 | 所属 Workspace |
| tag_id | UUIDv7 | 标签 ID |
| target_type | VARCHAR | 目标类型（entity / memory_node / archive） |
| target_id | UUIDv7 | 目标记录 ID |

---

## 12. Archive 体系

### 12.1 重要原则

> Memory 永不搬迁。  
> Archive 不是冷存储。  
> Archive 是**认知压缩层**。

**理由**：

* Archive 是对原始 Memory 的总结和压缩，不是替代。
* 原始 Memory 永久保留在 `memory_nodes` 表中。
* Archive 支持 Time Travel：可以追溯到任意历史时刻的认知状态。

### 12.2 归档层级

| 层级 | 说明 | MVP 是否实施 |
|------|------|-------------|
| Monthly Archive | 月度归档 | ✅ 是 |
| Yearly Archive | 年度归档 | ✅ 是 |
| Quarterly Archive | 季度归档 | ❌ 否（未来按需增加） |

**MVP 不做 Quarterly Archive**，保留 `archive_type` 扩展能力，未来按需增加。

### 12.3 Archive 全部向量化

**决策**：Archive 内容全部进入 `vector_documents` 表。

**理由**：

* Archive 是高价值认知压缩，检索价值高于原始 Observation。
* 支持 Time Travel 能力：通过向量检索回溯历史认知。

### 12.4 archives 建议字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDv7 | 主键 |
| workspace_id | UUIDv7 | 所属 Workspace |
| period_start | DATE | 归档起始日期 |
| period_end | DATE | 归档结束日期 |
| archive_type | VARCHAR | 类型：monthly / yearly（可扩展） |
| summary | TEXT | 归档摘要 |
| source_count | INTEGER | 来源 MemoryNode 数量 |
| created_at | TIMESTAMP | 创建时间 |

---

## 13. Archive 与 Memory 关系

### 13.1 新增：archive_sources（概念设计）

**用途**：Archive 可追溯原始 Memory。

**设计思路**：

* 每条 Archive 记录与其来源的 MemoryNode 建立关联。
* 支持从 Archive 追溯到原始的 Observation。
* 为 Explainable Memory 提供完整链路。

**关键字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| archive_id | UUIDv7 | 归档 ID |
| source_memory_node_id | UUIDv7 | 来源 MemoryNode ID |
| contribution_weight | FLOAT | 贡献权重（0.0~1.0） |

---

## 14. Reflect 体系

### 14.1 Reflect vs Archive

| 维度 | Reflect | Archive |
|------|---------|---------|
| 职责 | 负责思考 | 负责总结 |
| 输出 | 进入 memory_nodes | 进入 archives 表 |
| 触发 | Evidence Driven + Debounce | 定时（月度/年度） |
| 内容 | 认知分析、模式提取、状态刷新 | 月度/年度回顾 |

### 14.2 Reflect 结果进入 memory_nodes

**决策**：Reflect 的分析结果（Pattern / Belief / State）作为 MemoryNode 写入 `memory_nodes` 表。

### 14.3 tasks 统一任务表

**决策**：`tasks` 表统一管理所有任务类型（INGESTION / REFLECTION / ACTIVATION / ARCHIVE），不再为不同队列分别建表。

### 14.4 核心任务

| 任务 | 说明 | 输出 Level |
|------|------|-----------|
| Pattern Extraction | 从 Observation 中提取模式 | L2 Pattern |
| Belief Extraction | 从 Pattern 中提取认知 | L3 Belief |
| State Activation | 评估 Belief 是否应激活为 State | 运行时 |
| Memory Verification | 验证无效或过时的认知（基于证据而非时间） | 标记废弃 |

### 14.5 Reflect 分级

采用两级 Reflect：

| 级别 | 名称 | 触发条件 | 说明 |
|------|------|----------|------|
| 轻 | Light Reflect | Queue 满（≥N 条 Observation）或兜底定时 | 快速聚类、生成候选 Pattern |
| 重 | Heavy Reflect | 每日/每周定时执行 | 深度认知分析、Belief 更新、State 激活评估 |

### 14.6 memory_nodes 新增字段：generated_by

| 字段 | 类型 | 说明 |
|------|------|------|
| generated_by | VARCHAR | 生成来源 |

**取值**：

| 值 | 说明 |
|----|------|
| `user` | 用户手动创建 |
| `manual` | 人工录入（非用户直接输入） |
| `ai_reflect` | AI Reflect 生成 |
| `archive` | Archive 推导生成 |

**用途**：

* 追溯每条 MemoryNode 的来源。
* 支持 Explainable Memory。
* 区分用户输入与 AI 推断。

---

## 15. Context Builder 最终设计

> **Phase B 补充**：ContextBuilder 是 Domain Engine，不属于 Service。ContextService 是 Application Service 层，负责编排 ContextBuilder Engine 和 ActivationEngine。ContextService **不拥有独立 Repository**（参见 10_1 第 4.4 章）。

### 15.1 最终读取顺序

| 层 | 名称 | 说明 |
|----|------|------|
| Layer 1 | Current Session | 最近会话内容 |
| Layer 2 | Current Entity | 当前 Entity 相关记忆 |
| Layer 3 | Graph Expansion | 通过 Relationship 图扩展的相关记忆 |
| Layer 4 | Global Cognitive Memory | 全局认知记忆（高置信度 Belief/State） |

### 15.2 核心原则

> Entity 优先，Graph 优先，Vector 辅助。

**说明**：

* **Entity 优先** — 先通过 Area/Project 定位相关 Entity。
* **Graph 优先** — 再通过 Relationship 图扩展找到关联记忆。
* **Vector 辅助** — 最后通过向量检索补充语义相关记忆。

### 15.3 固定 Context Budget

与 02 文档保持一致：

| 层级 | 预算占比 | 说明 |
|------|----------|------|
| Layer 1 | 40% | 当前会话 |
| Layer 2 | 30% | 当前 Entity |
| Layer 3 | 20% | Graph 扩展 |
| Layer 4 | 10% | 全局认知 |

### 15.4 新增：Context Trace

**能力**：记录本次回答使用了哪些 Memory、哪些 Entity、哪些 Archive。

**用途**：

* 可解释性：用户可追溯 AI 回答的依据。
* 调试：开发者可分析 Context 构建效果。
* 审计：记录 AI 决策的知识来源。

**记录内容**：

| 字段 | 说明 |
|------|------|
| session_id | 会话 ID |
| memory_ids | 使用的 MemoryNode ID 列表 |
| entity_ids | 使用的 Entity ID 列表 |
| archive_ids | 使用的 Archive ID 列表 |
| layer_breakdown | 各层使用的 token 比例 |

### 15.5 Context Builder 内部模块

参见 06 第 10.3 章，Context Builder 由三个内部模块组成：

| 模块 | 职责 |
|------|------|
| Context Ranker | 按优先级排序（State > Belief > Pattern > Observation） |
| Context Compressor | 去重、摘要、截断，确保 Token Budget |
| Context Assembler | 按四层结构组装最终 Context |

---

## 16. Graph 扩展能力验证

### 16.1 未来扩展场景验证

以下场景验证后证明：**主要新增数据，而非修改 Schema**。

| 扩展场景 | 所需变更 | 是否修改 Schema |
|----------|----------|----------------|
| 新增 Entity Type（如 Agent） | 插入 `entities.entity_type = 'agent'` | ❌ 否 |
| 新增 Relationship（如 shares） | 插入 `relationships.relationship_type = 'shares'` | ❌ 否 |
| 新增 Agent | 创建 Agent Entity + Relationship | ❌ 否 |
| 新增 Tool | 创建 Tool Entity + Relationship | ❌ 否 |
| 新增 Model | 创建 Model Entity + Relationship | ❌ 否 |
| 新增 Workspace | 创建新 Workspace 记录 | ❌ 否 |
| 新增 Memory Graph | 使用 `memory_relationships` 表 | ⚠️ 新增表 |
| 迁移 Neo4j | UUIDv7 直接映射为节点 ID | ❌ 否 |
| 迁移 Memgraph | UUIDv7 直接映射为节点 ID | ❌ 否 |
| 迁移 Kuzu | UUIDv7 直接映射为节点 ID | ❌ 否 |

### 16.2 结论

> 当前 Schema 设计已验证支持未来 5~10 年的主要扩展场景。  
> 唯一需要新增表的是 `memory_relationships`（MemoryNode 之间的关系），但这属于计划内扩展，不影响现有 Schema。

---

## 17. 最终架构原则

### 17.1 统一 Node 模型

> 一切皆 Entity。

所有实体统一存储在 `entities` 表中，通过 `entity_type` 区分类型。

### 17.2 统一 Edge 模型

> 一切皆 Relationship。

所有关系统一存储在 `relationships` 表中，通过 `relationship_type` 区分类型。

### 17.3 统一 Memory 模型

> Observation → Pattern → Belief → State

所有记忆内容统一存储在 `memory_nodes` 表中，通过 `level` 区分层级。

### 17.4 统一 Retrieval 模型

> Graph + Vector + Archive + Context Builder

检索由四个维度协同完成：

| 维度 | 说明 |
|------|------|
| Graph | 通过 Entity → Relationship → Entity 遍历 |
| Vector | 通过 `vector_documents` 语义检索 |
| Archive | 通过 `archives` 回溯历史认知 |
| Context Builder | 按 Layer 1-4 优先级组合 |

### 17.5 最终目标

> 未来 5~10 年演进过程中，尽量避免数据库大规模迁移。

**实现路径**：

1. 统一 Node/Edge/Memory 模型，减少表数量。
2. 全部使用 UUIDv7，支持分布式和多 Workspace。
3. 向量层独立，支持未来升级向量引擎。
4. Reflect 结果进入 MemoryNode，保持推导链完整。
5. Archive 作为认知压缩层，不替代原始 Memory。
6. Context Builder 固定四层结构，预算比例可调。

---

## 附录 A：核心表字段速查

| 表名 | 关键字段 |
|------|----------|
| workspace | id, name, created_at |
| user_profiles | id, workspace_id, name, created_at |
| areas | id, workspace_id, name, parent_area_id |
| entities | id, workspace_id, area_id, parent_entity_id, entity_type, created_by_user_id |
| memory_nodes | id, entity_id, parent_node_id, level, content, generated_by |
| relationships | id, workspace_id, source_id, target_id, relationship_type, strength |
| vector_documents | id, workspace_id, source_type, source_id, memory_level, importance_score, content, embedding |
| tags | id, workspace_id, name, tag_type |
| tag_links | id, workspace_id, tag_id, target_type, target_id |
| archives | id, workspace_id, period_start, period_end, archive_type, summary |
|| reflect_tasks | id, workspace_id, task_type, status, created_at | → 已合并入 `tasks` 表（参见 08） |

---

## 附录 B：文档变更记录

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|----------|------|
| 1.3 | 2026-06-26 | Phase B 修订：第 15 章补充 ContextBuilder 是 Domain Engine，ContextService 不拥有独立 Repository（参见 10_1） | ✅ 已确认 |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

---

## 附录 C：术语表

| 术语 | 说明 |
|------|------|
| Ingestion Engine | 接收 Conversation，输出 Observation（参见 06 第 3.2 章） |
| Reflection Engine | 执行 Reflection Workflow，输出 Pattern/Belief（参见 06 第 3.3 章） |
| Activation Engine | 执行 State Activation，输出运行时 State（参见 06 第 3.4 章） |
| Retrieval Engine | 执行 Vector/Graph/Hybrid 检索（参见 06 第 3.5 章） |
| Context Builder | 四层 Context 构建，含 Ranker/Compressor/Assembler 模块（参见 06 第 3.6 章） |
| Scheduler | 统一 `tasks` 表任务调度器（参见 06 第 3.7 章 / 08 第 9 章） |
