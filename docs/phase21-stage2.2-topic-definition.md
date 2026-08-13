# Phase 21 Stage 2.2 — Topic Definition

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 2.2  
**调查日期**: 2026-08-13  
**范围**: 只读调查，定义 Topic 概念、结构与关系，不修改任何代码、数据库、Schema、测试或设计文档  

---

## 1. Decision Context

### 1.1 为什么需要 Topic

Stage 2.1 验证了 Reconstruction ↔ Candidate = 1:1，但发现了关键问题：

**场景**:
```
Reconstruction: "用户决定使用 PostgreSQL，并通过 Docker 部署 Memory Hub。"

如果只形成一个 Candidate:
  C1: "用户决定使用 PostgreSQL，并通过 Docker 部署 Memory Hub。"
  
问题: C1 包含多个独立语义单元，ReflectionEngine 难以判断:
  - "使用 PostgreSQL" 是否值得记忆？
  - "通过 Docker 部署" 是否值得记忆？
  - 两者是否应该分开评估？
```

**Phase 21 设计方向**:
> Candidate 应该是"可以独立交给 Proposal / Memory Evolution 判断的语义单元"。

**问题**: 如何定义"独立语义单元"的边界？

**答案**: Topic 是语义组织维度，用于划分 Reconstruction 中的独立语义单元。

### 1.2 核心问题

1. Topic 是什么？（定义）
2. Topic 与现有 Entity、Tag 的关系？（区分）
3. Topic 的数据结构？（Schema）
4. Topic 与 Reconstruction、Candidate 的关系？（Cardinality）
5. Topic 的生命周期？（Lifecycle）

---

## 2. Existing Architecture Evidence

### 2.1 Topic Window（已有设计）

**来源**: `01_MemoryHub_Foundation.md` §7

```markdown
## 7. Topic Window 设计

### 7.1 定位

Topic Window **不是**总结层。

### 7.2 作用

| 功能 | 说明 |
|------|------|
| 主题聚类 | 将相似话题归组 |
| 主题索引 | 建立话题的可检索索引 |
| 统计频率 | 记录话题出现频次 |

### 7.3 约束

- 不产生长期结论
- 可随时重建（无状态）
```

**生命周期**:
| 层级 | 保留周期 | 说明 |
|------|----------|------|
| Topic Window | 约 1 年 | 可重建，非关键数据 |

**关键观察**:
1. Topic Window 是**现有设计**，但不是 Topic 本身
2. Topic Window 是"主题聚类/索引/统计"，不是"语义单元"
3. Topic Window **不产生长期结论**，可重建

### 2.2 Memory Pyramid 中的 Topic

**来源**: `10_4_Implementation_ReflectionService.md` §3.3

```markdown
| 层级 | 类型 | 解释范围 | 示例 |
|------|------|----------|------|
| L0 | Historical Facts | 原始事实 | 聊天记录、导入文档 |
| L1 | Topic Knowledge | 单主题内总结 | "Personal Memory Hub 开发日志总结" |
| L2 | Cross-topic Pattern | 跨主题模式 | "用户选择工具时先验证架构再验证成本" |
| L3 | General Principle | 一般原则 | "用户长期决策：优先长期价值，避免重复返工" |
```

**关键观察**:
1. L1 是"Topic Knowledge"（单主题内总结）
2. L2 是"Cross-topic Pattern"（跨主题模式）
3. Topic 是**解释范围的维度**，不是独立实体

### 2.3 Semantic Uniqueness Principle

**来源**: `10_4_Implementation_ReflectionService.md` §3.5

```markdown
> **Semantic Uniqueness Principle**
> 在同一抽象层级内，同一语义空间应只有一个当前有效的 Memory 节点。
```

**关键观察**:
1. "同一语义空间" = 同一 Topic 内的语义空间
2. Topic 定义了"语义空间"的边界
3. 这是 Topic 存在的**核心原则**基础

### 2.4 Tag 体系（已有设计）

**来源**: `09_Database_Physical_Design.md` §09.4.10-11

```sql
CREATE TABLE memory_hub.tags (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    tag_type VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (tag_type IN ('system', 'ai', 'user')),
    color VARCHAR(7),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uk_tags_workspace_name UNIQUE (workspace_id, name)
);

CREATE TABLE memory_hub.tag_links (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    tag_id UUID NOT NULL REFERENCES memory_hub.tags(id),
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('entity', 'memory_node', 'archive')),
    target_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uk_tag_links UNIQUE (tag_id, target_type, target_id)
);
```

**关键观察**:
1. Tag 是**开放式语义索引**，不是事实
2. Tag 有三类：system（技术栈）、ai（自动提取）、user（手动创建）
3. Tag 关联到 entity、memory_node、archive
4. Tag **不直接关联 Candidate 或 Reconstruction**

### 2.5 Entity 体系（已有设计）

**来源**: `09_Database_Physical_Design.md` §09.4.4

```sql
CREATE TABLE memory_hub.entities (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    area_id UUID,
    parent_entity_id UUID REFERENCES memory_hub.entities(id),
    user_id UUID,
    
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN (
        'Project', 'Person', 'Organization', 'Tool', 'Technology',
        'Concept', 'Event', 'Location', 'Object', 'Agent', 'Model', 'Document'
    )),
    
    canonical_name VARCHAR(255) NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    observation_count INTEGER DEFAULT 0,
    belief_count INTEGER DEFAULT 0,
    pattern_count INTEGER DEFAULT 0,
    relationship_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uk_entities_type_name UNIQUE (workspace_id, entity_type, canonical_name)
);
```

**关键观察**:
1. Entity 是**具名的、独立的**对象
2. Entity 有层级关系（parent_entity_id）
3. Entity 是记忆的组织单位
4. **Entity ≠ Topic**（Entity 是"什么"，Topic 是"关于什么"）

---

## 3. Topic Semantics

### 3.1 Topic 的定义

**Phase 21 设计方向**:
> Topic 是语义组织维度，不是事实、Entity 或 Memory。

**我的定义**:
> Topic = 具有共同语义边界的讨论域，用于划分 Reconstruction 中的独立语义单元。

**关键特征**:
1. **语义性**: Topic 基于语义内容，不是基于时间或会话
2. **组织性**: Topic 用于组织 Evidence、Reconstruction、Candidate
3. **动态性**: Topic 可以随新 Evidence 演化
4. **独立性**: 一个 Topic 可以跨多个 Reconstruction 存在

### 3.2 Topic vs Entity vs Tag

| 维度 | Entity | Tag | Topic |
|------|--------|-----|-------|
| 本质 | 具名的独立对象 | 开放式语义索引 | 语义组织维度 |
| 示例 | "Memory Hub 项目" | "PostgreSQL" | "架构决策" |
| 持久性 | 永久 | 永久 | 动态（可演化） |
| 层级 | 有层级（parent） | 无层级 | 无层级（但可嵌套） |
| 创建 | 显式或自动 | 自动或手动 | 自动（语义聚类） |
| 归属 | 属于 Workspace/Area | 属于 Workspace | 属于 Workspace |

**关键区别**:
- **Entity 是"什么"**：Memory Hub 项目、PostgreSQL 数据库
- **Tag 是"标记"**：#PostgreSQL、#架构
- **Topic 是"讨论域"**：架构决策、工具选型

**示例**:
```
Entity: "Memory Hub 项目"
Tag: "PostgreSQL", "Docker"
Topic: "数据库选型决策"
```

一个 Topic 可以关联多个 Entity（Memory Hub、PostgreSQL、Docker）。
一个 Entity 可以关联多个 Topic（架构决策、部署方案、性能优化）。

### 3.3 Topic 的类型

根据 Phase 21 设计方向，Topic 可以分为：

| 类型 | 说明 | 示例 |
|------|------|------|
| **Explicit Topic** | 用户明确提及的主题 | "我们在讨论架构选型" |
| **Derived Topic** | 系统从 Evidence 中自动提取 | 从对话中提取"数据库选型"主题 |
| **Inherited Topic** | 从 Parent Topic 继承 | "PostgreSQL 特性"继承自"数据库选型" |

**注意**: Stage 2.2 只定义 Topic 的基本结构，Topic 来源（Explicit/Derived/Inherited）的详细设计留给后续 Stage。

---

## 4. Topic ↔ Reconstruction ↔ Candidate Analysis

### 4.1 关键问题

**问题**: 一个 Reconstruction 是否可以包含多个 Topic？

**场景**:
```
Reconstruction: "用户决定使用 PostgreSQL，并通过 Docker 部署 Memory Hub。"

可能包含的 Topic:
- Topic A: "数据库选型"（PostgreSQL）
- Topic B: "部署方案"（Docker）
- Topic C: "项目架构"（Memory Hub）
```

**答案**: **是**。一个 Reconstruction 可以包含多个 Topic。

### 4.2 关系模型

**Option 1: Topic 作为 Reconstruction 的元数据**

```sql
-- reconstruction 表新增字段
topic_ids JSONB DEFAULT '[]'  -- Topic ID 列表
```

**优点**:
- ✅ 简单：无需新表
- ✅ 符合现有架构风格（metadata JSONB）

**缺点**:
- ❌ 无法查询"某个 Topic 下的所有 Reconstruction"
- ❌ 无法表达 Topic 间的关系
- ❌ 违反"Topic 是独立语义组织维度"的原则

**结论**: **不推荐**。

---

**Option 2: 新增 Topic 表 + 关联表**

```sql
-- 新增 topics 表
CREATE TABLE memory_hub.topics (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_topic_id UUID REFERENCES memory_hub.topics(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 新增 topic_links 表（多对多）
CREATE TABLE memory_hub.topic_links (
    topic_id UUID NOT NULL REFERENCES memory_hub.topics(id),
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('reconstruction', 'candidate')),
    source_id UUID NOT NULL,
    
    PRIMARY KEY (topic_id, source_type, source_id)
);
```

**优点**:
- ✅ Topic 是独立实体
- ✅ 支持查询"某个 Topic 下的所有 Reconstruction/Candidate"
- ✅ 支持 Topic 层级关系（parent_topic_id）
- ✅ 符合现有架构风格（类似 tag_links）

**缺点**:
- ❌ 新增两张表
- ❌ 增加复杂度

**结论**: **推荐**。

---

**Option 3: 复用 Tag 表作为 Topic**

**分析**:
- Tag 已有 system/ai/user 类型
- 可以新增 topic 类型

**问题**:
- Tag 是"开放式语义索引"，Topic 是"语义组织维度"
- 语义不同，不应该混淆
- 违反"Entity 与 Tag 必须保持独立"的原则

**结论**: **不推荐**。

---

### 4.3 Cardinality 分析

#### Question 1: 一个 Topic 可以关联多少个 Reconstruction？

**Answer**: **N**（多个）

**理由**:
- Topic 是语义组织维度
- 多个 Reconstruction 可以属于同一 Topic
- 例如："数据库选型"Topic 可以关联多个阶段的 Reconstruction

#### Question 2: 一个 Reconstruction 可以关联多少个 Topic？

**Answer**: **N**（多个）

**理由**:
- 一个 Reconstruction 可以包含多个独立语义单元
- 例如："用户决定使用 PostgreSQL，并通过 Docker 部署"包含两个 Topic

#### Question 3: 一个 Topic 可以关联多少个 Candidate？

**Answer**: **N**（多个）

**理由**:
- 同一 Topic 下可以有多个 Candidate（不同时间、不同阶段）
- 例如："数据库选型"Topic 下可以有多个 Candidate（PostgreSQL、MySQL、SQLite 等选项）

#### Question 4: 一个 Candidate 可以关联多少个 Topic？

**Answer**: **N**（多个）

**理由**:
- Candidate 是 Reconstruction 的快照
- 如果 Reconstruction 有多个 Topic，Candidate 也继承这些 Topic

### 4.4 完整关系图

```
┌─────────────┐       N:M       ┌─────────────┐       N:M       ┌─────────────┐
│   Topic     │◄───────────────▶│Reconstruction│◄───────────────▶│  Candidate  │
└─────────────┘                 └─────────────┘                 └─────────────┘
      │                               │                               │
      │ 1:N                           │ 1:1                           │ 1:N
      ▼                               ▼                               ▼
┌─────────────┐                 ┌─────────────┐                 ┌─────────────┐
│   Entity    │                 │  Entity     │                 │  Proposal   │
│ (primary)   │                 │ (primary)   │                 │             │
└─────────────┘                 └─────────────┘                 └─────────────┘
```

**关键约束**:
- Topic ↔ Reconstruction = N:M（通过 topic_links）
- Reconstruction ↔ Candidate = 1:1（已验证）
- Candidate → Proposal = 1:N（Phase 20 设计）

---

## 5. Topic Lifecycle

### 5.1 Topic 状态机

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
              ┌──────────┐                               │
              │ initial  │◄──────────────────────────────┘
              └────┬─────┘
                   │
                   │ Evidence 积累
                   │ 语义确认
                   ▼
              ┌──────────┐     ┌──────────┐
              │  active  │────▶│  evolved │◄── 新 Evidence
              └────┬─────┘     └────┬─────┘
                   │                │
                   │ 语义漂移       │ 语义进一步演化
                   ▼                │
              ┌──────────┐     ┌────▼─────┐
              │superseded│────▶│ archived │
              └──────────┘     └──────────┘
                   │
                   └──→ 保留历史，不删除
```

### 5.2 状态转换规则

| 转换 | 触发条件 | 执行层 |
|------|----------|--------|
| initial → active | 足够 Evidence 支持，语义清晰 | EvidenceEvolutionEngine |
| active → evolved | 新 Evidence 到达，语义更新 | EvidenceEvolutionEngine |
| evolved → superseded | 新 Topic 版本形成 | EvidenceEvolutionEngine |
| any → archived | 用户手动归档 | Service |

### 5.3 Topic 与 Reconstruction 状态同步

| Topic 状态 | Reconstruction 状态 | 说明 |
|-----------|---------------------|------|
| initial | initial | 新发现 Topic |
| active | active | 语义清晰，可检索 |
| evolved | updated | 语义更新，保留历史 |
| superseded | superseded | 被新版本替代 |
| archived | archived | 手动归档 |

---

## 6. Schema Design

### 6.1 新增表

```sql
-- Topic 表
CREATE TABLE memory_hub.topics (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    parent_topic_id UUID REFERENCES memory_hub.topics(id),
    
    status VARCHAR(20) NOT NULL DEFAULT 'initial' CHECK (status IN (
        'initial', 'active', 'evolved', 'superseded', 'archived'
    )),
    
    evidence_count INTEGER NOT NULL DEFAULT 0,
    reconstruction_count INTEGER NOT NULL DEFAULT 0,
    
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_topics_workspace_name UNIQUE (workspace_id, name)
);

COMMENT ON TABLE memory_hub.topics IS '语义组织维度，用于划分 Reconstruction 中的独立语义单元';
COMMENT ON COLUMN memory_hub.topics.parent_topic_id IS '支持 Topic 层级关系（可选）';
COMMENT ON COLUMN memory_hub.topics.evidence_count IS '关联的 Evidence 数量（统计用）';
COMMENT ON COLUMN memory_hub.topics.reconstruction_count IS '关联的 Reconstruction 数量（统计用）';
```

### 6.2 关联表

```sql
-- Topic 关联表（多对多）
CREATE TABLE memory_hub.topic_links (
    topic_id UUID NOT NULL REFERENCES memory_hub.topics(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('reconstruction', 'candidate', 'entity')),
    source_id UUID NOT NULL,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (topic_id, source_type, source_id)
);

COMMENT ON TABLE memory_hub.topic_links IS 'Topic 与 Reconstruction/Candidate/Entity 的多对多关联';
```

### 6.3 索引

```sql
-- Topic 索引
CREATE INDEX idx_topics_workspace_id ON memory_hub.topics(workspace_id);
CREATE INDEX idx_topics_status ON memory_hub.topics(status);
CREATE INDEX idx_topics_parent_id ON memory_hub.topics(parent_topic_id);
CREATE INDEX idx_topics_created_at ON memory_hub.topics(created_at DESC);
CREATE INDEX idx_topics_name_gin ON memory_hub.topics USING gin(to_tsvector('simple', name));

-- Topic Links 索引
CREATE INDEX idx_topic_links_source ON memory_hub.topic_links(source_type, source_id);
CREATE INDEX idx_topic_links_topic_id ON memory_hub.topic_links(topic_id);
```

### 6.4 修改现有表

**无需修改 candidates 表**（Stage 2.1 已确认）。

**Reconstruction 表新增字段**（可选）:
```sql
-- 方案 A: 通过 topic_links 关联（推荐）
-- 不需要修改 reconstruction 表

-- 方案 B: 新增 primary_topic_id 字段（可选优化）
ALTER TABLE memory_hub.reconstructions ADD COLUMN primary_topic_id UUID REFERENCES memory_hub.topics(id);
CREATE INDEX idx_reconstructions_primary_topic ON memory_hub.reconstructions(primary_topic_id);
```

**推荐**: 方案 A（通过 topic_links），保持灵活性。

---

## 7. Topic Formation Algorithm

### 7.1 触发条件

Topic 可以在以下时机形成：
1. **Evidence 导入时**: EvidenceEvolutionEngine 提取 Entity 后，判断是否需要形成新 Topic
2. **Reconstruction 形成时**: 如果 Reconstruction 包含多个独立语义单元，形成多个 Topic
3. **定期聚类**: 定时任务对现有 Topic 进行聚类，合并相似 Topic

### 7.2 形成规则

**规则 1: Entity 主导**
- 如果多数 Evidence 关联到同一 Entity，形成该 Entity 下的 Topic
- 例如：多个 Evidence 关于"PostgreSQL"，形成"PostgreSQL 相关"Topic

**规则 2: 语义聚类**
- 如果多个 Evidence 语义相似，但涉及不同 Entity，形成跨 Entity 的 Topic
- 例如："PostgreSQL 选型"和"MySQL 选型"形成"数据库选型"Topic

**规则 3: 用户显式提及**
- 如果用户明确提及某个主题，形成 Explicit Topic
- 例如："我们在讨论架构选型"→ 形成"架构选型"Topic

### 7.3 与现有 Engine 的集成

**EvidenceEvolutionEngine 新增职责**:
```python
class EvidenceEvolutionEngine:
    async def evolve(self, *, evidence, provider) -> EvolutionResult:
        # Step 1: Entity Extraction
        entities = await self.extract_entities(evidence.content)
        
        # Step 2: Topic Formation (NEW)
        topics = await self.form_topics(entities, evidence)
        
        # Step 3: Reconstruction Formation
        reconstruction = await self.create_reconstruction(evidence, entities, topics)
        
        return EvolutionResult(
            reconstruction=reconstruction,
            topics=topics,
            entities=entities
        )
```

**关键观察**:
- Topic Formation 是 EvidenceEvolutionEngine 的新职责
- Topic 形成在 Reconstruction 形成**之前**或**同时**
- Topic 不影响 ReflectionEngine 的职责（仍只处理 Candidate）

---

## 8. Comparison with Existing Designs

### 8.1 Topic vs Topic Window

| 维度 | Topic Window | Topic |
|------|--------------|-------|
| 定义 | 主题聚类/索引/统计 | 语义组织维度 |
| 持久性 | 临时（约 1 年，可重建） | 永久（直到 archived） |
| 作用 | 短期组织 | 长期语义边界 |
| 与 Memory 关系 | 不产生 Memory | 划分 Memory 的语义空间 |
| 来源 | 现有设计（01 §7） | Phase 21 新增 |

**关键区别**:
- Topic Window 是"索引"，Topic 是"语义单元"
- Topic Window 可重建，Topic 不可重建（是 Memory 的组织维度）

### 8.2 Topic vs Tag

| 维度 | Tag | Topic |
|------|-----|-------|
| 本质 | 开放式语义索引 | 语义组织维度 |
| 示例 | "PostgreSQL" | "数据库选型决策" |
| 层级 | 无层级 | 可有层级（parent_topic_id） |
| 创建 | 自动或手动 | 自动（语义聚类） |
| 关联目标 | entity, memory_node, archive | reconstruction, candidate, entity |

**关键区别**:
- Tag 是"标记"，Topic 是"讨论域"
- Tag 可以是任意词汇，Topic 必须是语义完整的讨论域

### 8.3 Topic vs Entity

| 维度 | Entity | Topic |
|------|--------|-------|
| 本质 | 具名的独立对象 | 语义组织维度 |
| 示例 | "Memory Hub 项目" | "架构决策" |
| 存在 | 永久 | 动态演化 |
| 层级 | 有层级（parent_entity_id） | 可有层级（parent_topic_id） |

**关键区别**:
- Entity 是"什么"，Topic 是"关于什么"
- 一个 Entity 可以属于多个 Topic
- 一个 Topic 可以关联多个 Entity

---

## 9. Phase 20 Compatibility

### 9.1 不影响的部分

| Phase 20 设计 | Topic 影响 | 兼容性 |
|--------------|-----------|--------|
| proposals.candidate_id FK | 无影响 | ✅ 兼容 |
| Candidate lifecycle | 无影响 | ✅ 兼容 |
| Pending Proposal dedup | 无影响 | ✅ 兼容 |
| Evolution scope | 无影响 | ✅ 兼容 |

### 9.2 新增的影响

| 影响点 | 说明 |
|--------|------|
| EvidenceEvolutionEngine | 新增 Topic Formation 职责 |
| Reconstruction 表 | 无需修改（通过 topic_links 关联） |
| Candidate 表 | 无需修改 |

### 9.3 关键原则

> **Topic 不影响 Candidate lineage**。

Topic 是语义组织维度，不改变 Candidate 的 1:1 Reconstruction 关系。

---

## 10. Recommended Topic Model

### 10.1 最终决策

#### Question 1: Topic 是否应该作为独立表？

**Answer**: **是** ✅

**理由**:
1. Topic 是语义组织维度，不是简单的标记
2. 需要支持查询"某个 Topic 下的所有 Reconstruction/Candidate"
3. 需要支持 Topic 层级关系
4. 符合现有架构风格（类似 tag_links）

#### Question 2: Topic 与 Reconstruction 的关系？

**Answer**: **N:M** ✅

**理由**:
1. 一个 Reconstruction 可以包含多个 Topic
2. 一个 Topic 可以关联多个 Reconstruction
3. 通过 topic_links 表实现

#### Question 3: Topic 是否应该有层级？

**Answer**: **是**（可选）✅

**理由**:
1. 支持"父 Topic → 子 Topic"的语义关系
2. 例如："数据库选型" → "PostgreSQL 特性"
3. 通过 parent_topic_id 实现（NULL 表示顶级 Topic）

#### Question 4: Topic 是否应该关联 Entity？

**Answer**: **是** ✅

**理由**:
1. Topic 可以通过 topic_links 关联 Entity
2. 但不强制（有些 Topic 是跨 Entity 的）
3. 通过 source_type='entity' 实现

### 10.2 Schema 总结

```sql
-- 新增表
topics (id, workspace_id, name, description, parent_topic_id, status, evidence_count, reconstruction_count, metadata, timestamps)
topic_links (topic_id, source_type, source_id, created_at)

-- 无需修改
candidates (保持不变)
reconstructions (通过 topic_links 关联，不新增字段)
```

---

## 11. Required Changes to Stage 2.1 Decision

### 11.1 确认不变的决策

| Stage 2.1 决策 | Stage 2.2 影响 | 状态 |
|---------------|---------------|------|
| Reconstruction ↔ Candidate = 1:1 | 无影响 | ✅ 确认 |
| Reconstruction.entity_id NOT NULL | 无影响（Topic 可通过 topic_links 关联多 Entity） | ✅ 确认 |
| Reconstruction 持久化 | 无影响 | ✅ 确认 |

### 11.2 新增的决策

| 决策项 | 选择 |
|--------|------|
| Topic 是否独立表 | ✅ 是 |
| Topic ↔ Reconstruction | N:M |
| Topic 层级 | 支持（parent_topic_id） |
| Topic 与 Entity 关系 | 通过 topic_links 关联（可选） |

---

## 12. Deferred Questions

以下问题明确留给后续 Stage：

| 问题 | 优先级 | 所属 Stage | 理由 |
|------|--------|-----------|------|
| Topic 来源分类（Explicit/Derived/Inherited） | P1 | Stage 2.3 | 依赖 Context Window 设计 |
| Topic 聚类算法 | P1 | Stage 2.3 | 实现细节 |
| Topic 演化规则 | P2 | Stage 3 | 依赖 Historical Memory Evolution |
| Topic 与 Tag 的互操作性 | P2 | Deferred | 非核心问题 |
| Topic 删除策略 | P2 | Deferred | 边缘场景 |

---

## 附录 A: 完整关系图（Mermaid）

```mermaid
erDiagram
    TOPICS ||--o{ TOPIC_LINKS : "owns"
    RECONSTRUCTIONS ||--o{ TOPIC_LINKS : "linked"
    CANDIDATES ||--o{ TOPIC_LINKS : "linked"
    ENTITIES ||--o{ TOPIC_LINKS : "linked"
    RECONSTRUCTIONS ||--o| CANDIDATES : "forms (1:1)"
    TOPICS ||--o{ TOPICS : "parent (hierarchy)"
    
    TOPICS {
        UUID id
        UUID workspace_id
        VARCHAR name
        VARCHAR status
        UUID parent_topic_id
    }
    
    TOPIC_LINKS {
        UUID topic_id
        VARCHAR source_type
        UUID source_id
    }
    
    RECONSTRUCTIONS {
        UUID id
        UUID workspace_id
        UUID entity_id
        UUID candidate_id (UNIQUE)
    }
    
    CANDIDATES {
        UUID id
        UUID workspace_id
        UUID entity_id
    }
    
    ENTITIES {
        UUID id
        UUID workspace_id
        VARCHAR canonical_name
    }
```

---

## 附录 B: 关键设计决策总结

| 决策项 | 选择 | 理由 |
|--------|------|------|
| Topic 是否独立表 | **是** | 语义组织维度，需独立查询 |
| Topic ↔ Reconstruction | **N:M** | 一个 Reconstruction 可有多个 Topic |
| Topic 层级 | **支持** | parent_topic_id（可选） |
| Topic 与 Entity | **通过 topic_links** | 不强制，保持灵活 |
| Stage 2.1 决策修改 | **不需要** | 完全兼容 |

---

*本报告为只读调查，不修改任何代码、数据库、Schema、测试或设计文档。*
*Decision Statement 可直接用于 ADR 创建。*

---

**STOP** — 不编码、不提交 Git，等待下一步指示。
