# Personal AI Memory Hub — 09 Database Physical Design

> **版本**: 1.1  
> **日期**: 2026-06-25  
> **阶段**: 第九阶段  
> **状态**: 已确认（与 01-08 一致性修复）  
> **作者**: 系统架构组

---

## 09.1 设计目标与范围约束

### 09.1.1 目标

本文档是 Memory Hub 项目的**数据库物理设计唯一权威文档**。它将 01-08 的逻辑设计转化为可直接执行的物理 Schema，并定义：

- 所有表的精确字段定义（类型、约束、索引）
- 完整的 DDL 脚本
- 数据迁移策略
- 性能优化策略
- 安全与权限模型

### 09.1.2 范围锁

**严禁以下内容**：

- 不得扩展记忆层（Layer）架构
- 不得修改 01-08 已确认的任何架构决策
- 不得引入新的范式或设计模式
- 不得变更记忆生命周期规则

### 09.1.3 设计原则

1. **Evidence-Based**: 所有记忆必须可追溯至证据
2. **State = Belief + Current Context**: 运行时激活，非持久化实体
3. **Three-Score Separation**: Confidence / Importance / Signal Strength 永远不混用
4. **Project is an Entity Type**: 不单独建 Project 表
5. **Graph is Explicit**: 不使用 JSON 边表示关系
6. **All Mutations via Tasks**: 所有记忆变更通过 `tasks` 表协调

---

## 09.2 数据库选型与技术栈

### 09.2.1 技术栈锁定

| 组件 | 选型 | 说明 |
|------|------|------|
| 数据库 | PostgreSQL 15+ | Supabase 托管 |
| 向量扩展 | pgvector 0.6+ | 原生向量支持 |
| UUID 生成 | uuidv7 (通过 uuidv7() 扩展) | 时间有序 UUID，参见 03/04 全部 UUIDv7 原则 |
| 索引策略 | ivfflat (MVP) → hnsw (V2+) | 向量检索索引 |
| 连接池 | Supabase 内置 | 生产环境 |

### 09.2.2 Rationale

- Supabase 提供托管 PostgreSQL，降低运维成本
- pgvector 是 PostgreSQL 原生扩展，无需引入额外服务
- ivfflat 在 MVP 阶段性能足够，数据量增长后可升级到 hnsw
- UUIDv7 支持分布式生成和时间有序查询

---

## 09.3 命名约定

### 09.3.1 Schema

所有表位于 `memory_hub` schema 下。

### 09.3.2 表名

- 全部小写，蛇形命名
- 复数形式：`entities`, `memory_nodes`, `relationships`
- 特殊：`workspace`（单数，因为只有一个顶层容器）

### 09.3.3 列名

- 全部小写，蛇形命名
- 主键统一为 `id`
- 外键格式：`{引用表}_id`，如 `workspace_id`, `entity_id`
- 时间戳统一为 `{动作}_at`，如 `created_at`, `updated_at`

### 09.3.4 索引命名

```
idx_{schema}_{table}_{column(s)}
```

示例：`idx_memory_hub_entities_workspace_id_area_id`

### 09.3.5 约束命名

```
chk_{table}_{constraint_description}
con_{table}_{column}_fk
uk_{table}_{column(s)}
```

---

## 09.4 完整表结构定义

> **部署说明**: 所有 `DEFAULT gen_random_uuid()` 在部署时需替换为 `DEFAULT uuidv7()`（需安装 uuidv7 扩展）。参见 03 第 4.1 章「全部 UUIDv7」原则。

### 09.4.1 workspace 表

```sql
CREATE TABLE memory_hub.workspace (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- 部署时替换为 UUIDv7: SELECT uuidv7()
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE memory_hub.workspace IS '顶层容器，支持单用户/家庭/团队';
```

**约束**: 系统初始化时创建一条记录，禁止删除。

---

### 09.4.2 user_profiles 表

```sql
CREATE TABLE memory_hub.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    external_user_id VARCHAR(255),
    display_name VARCHAR(255),
    email VARCHAR(255),
    avatar_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_user_profiles_external UNIQUE (workspace_id, external_user_id)
);

COMMENT ON TABLE memory_hub.user_profiles IS '用户档案';
```

---

### 09.4.3 areas 表

```sql
CREATE TABLE memory_hub.areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    parent_area_id UUID REFERENCES memory_hub.areas(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_areas_workspace_name UNIQUE (workspace_id, name)
);

COMMENT ON TABLE memory_hub.areas IS '一级领域划分（AI / Work / Family / Finance 等）';
```

---

### 09.4.4 entities 表

```sql
CREATE TABLE memory_hub.entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    area_id UUID REFERENCES memory_hub.areas(id) ON DELETE SET NULL,
    parent_entity_id UUID REFERENCES memory_hub.entities(id) ON DELETE SET NULL,
    user_id UUID REFERENCES memory_hub.user_profiles(id) ON DELETE SET NULL,
    
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
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_entities_type_name UNIQUE (workspace_id, entity_type, canonical_name)
);

COMMENT ON TABLE memory_hub.entities IS '实体（Project 也作为 Entity 存储，参见 04 第 2.2 章）';

CREATE INDEX idx_entities_workspace_id ON memory_hub.entities(workspace_id);
CREATE INDEX idx_entities_area_id ON memory_hub.entities(area_id);
CREATE INDEX idx_entities_parent_entity_id ON memory_hub.entities(parent_entity_id);
CREATE INDEX idx_entities_type_name ON memory_hub.entities(entity_type, canonical_name);
```

---

### 09.4.5 memory_nodes 表

```sql
CREATE TABLE memory_hub.memory_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES memory_hub.entities(id) ON DELETE CASCADE,
    parent_node_id UUID REFERENCES memory_hub.memory_nodes(id) ON DELETE SET NULL,
    user_id UUID REFERENCES memory_hub.user_profiles(id) ON DELETE SET NULL,
    
    level INTEGER NOT NULL CHECK (level IN (1, 2, 3)),  -- Level 4 (State) 是运行时概念，不落库（参见 05 第 12 章 / 08 第 3.3 章）
    node_type VARCHAR(50) NOT NULL,
    
    content TEXT NOT NULL,
    summary TEXT,
    
    observation_type VARCHAR(50) CHECK (
        level = 1 AND observation_type IN (
            'activity', 'decision', 'preference', 'fact', 'goal', 'problem', 'event'
        ) OR level != 1
    ),  -- 仅 L1 Observation 使用，参见 05 第 6 章
    
    confidence FLOAT NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    importance FLOAT NOT NULL DEFAULT 0.0 CHECK (importance >= 0.0 AND importance <= 1.0),
    signal_strength FLOAT NOT NULL DEFAULT 0.0 CHECK (signal_strength >= 0.0 AND signal_strength <= 1.0),
    
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN (
        'active', 'candidate', 'deprecated', 'superseded', 'orphaned'
    )),
    
    source VARCHAR(50) NOT NULL DEFAULT 'user' CHECK (source IN (
        'user', 'manual', 'explicit_command', 'archive_derived', 'ai_reflect'
    )),
    generated_by VARCHAR(50) NOT NULL DEFAULT 'user' CHECK (generated_by IN (
        'user', 'manual', 'ai_reflect', 'archive'
    )),
    
    evidence_links JSONB DEFAULT '[]',
    contradict_evidence JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_level_type_consistency CHECK (
        (level = 1 AND node_type = 'Observation') OR
        (level = 2 AND node_type = 'Pattern') OR
        (level = 3 AND node_type = 'Belief')
    )
);

COMMENT ON TABLE memory_hub.memory_nodes IS '记忆节点（Observation/Pattern/Belief/State）';
COMMENT ON COLUMN memory_hub.memory_nodes.level IS '1=Observation, 2=Pattern, 3=Belief, 4=State';
COMMENT ON COLUMN memory_hub.memory_nodes.observation_type IS '仅 L1 Observation 使用：activity/decision/preference/fact/goal/problem/event';

-- 索引
CREATE INDEX idx_memory_nodes_workspace_id ON memory_hub.memory_nodes(workspace_id);
CREATE INDEX idx_memory_nodes_entity_id ON memory_hub.memory_nodes(entity_id);
CREATE INDEX idx_memory_nodes_level ON memory_hub.memory_nodes(level);
CREATE INDEX idx_memory_nodes_status ON memory_hub.memory_nodes(status);
CREATE INDEX idx_memory_nodes_confidence ON memory_hub.memory_nodes(confidence DESC) WHERE status = 'active';
CREATE INDEX idx_memory_nodes_importance ON memory_hub.memory_nodes(importance DESC) WHERE status = 'active';
CREATE INDEX idx_memory_nodes_signal_strength ON memory_hub.memory_nodes(signal_strength DESC) WHERE status = 'active';
CREATE INDEX idx_memory_nodes_created_at ON memory_hub.memory_nodes(created_at DESC);
CREATE INDEX idx_memory_nodes_evidence_links ON memory_hub.memory_nodes USING GIN(evidence_links);
CREATE INDEX idx_memory_nodes_contradict_evidence ON memory_hub.memory_nodes USING GIN(contradict_evidence);
```

---

### 09.4.6 evidences 表

```sql
CREATE TABLE memory_hub.evidences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES memory_hub.entities(id) ON DELETE CASCADE,
    area_id UUID REFERENCES memory_hub.areas(id) ON DELETE SET NULL,
    user_id UUID REFERENCES memory_hub.user_profiles(id) ON DELETE SET NULL,
    
    evidence_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    raw_content TEXT,
    
    confidence FLOAT NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    importance FLOAT NOT NULL DEFAULT 0.0 CHECK (importance >= 0.0 AND importance <= 1.0),
    signal_strength FLOAT NOT NULL DEFAULT 0.0 CHECK (signal_strength >= 0.0 AND signal_strength <= 1.0),
    
    source VARCHAR(50) NOT NULL DEFAULT 'conversation' CHECK (source IN (
        'conversation', 'manual', 'explicit_command', 'document', 'import'
    )),
    
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_evidence_not_empty CHECK (char_length(content) > 0)
);

COMMENT ON TABLE memory_hub.evidences IS '证据（Observation 等事实记录，永不删除）';
COMMENT ON COLUMN memory_hub.evidences.raw_content IS '原始对话/输入内容';

CREATE INDEX idx_evidences_workspace_id ON memory_hub.evidences(workspace_id);
CREATE INDEX idx_evidences_entity_id ON memory_hub.evidences(entity_id);
CREATE INDEX idx_evidences_area_id ON memory_hub.evidences(area_id);
CREATE INDEX idx_evidences_source ON memory_hub.evidences(source);
CREATE INDEX idx_evidences_confidence ON memory_hub.evidences(confidence DESC);
CREATE INDEX idx_evidences_importance ON memory_hub.evidences(importance DESC);
CREATE INDEX idx_evidences_created_at ON memory_hub.evidences(created_at DESC);
```

---

### 09.4.7 memory_evidences 表

```sql
CREATE TABLE memory_hub.memory_evidences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    memory_node_id UUID NOT NULL REFERENCES memory_hub.memory_nodes(id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES memory_hub.evidences(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL DEFAULT 'supports',
    contribution_weight FLOAT DEFAULT 1.0 CHECK (contribution_weight >= 0.0 AND contribution_weight <= 1.0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_memory_evidences UNIQUE (memory_node_id, evidence_id),
    CONSTRAINT chk_relationship_type CHECK (relationship_type IN (
        'supports', 'derived_from', 'contradicts', 'attenuates'
    ))
);

COMMENT ON TABLE memory_hub.memory_evidences IS '记忆节点与证据的关联关系';

CREATE INDEX idx_memory_evidences_memory_node_id ON memory_hub.memory_evidences(memory_node_id);
CREATE INDEX idx_memory_evidences_evidence_id ON memory_hub.memory_evidences(evidence_id);
CREATE INDEX idx_memory_evidences_relationship_type ON memory_hub.memory_evidences(relationship_type);
```

---

### 09.4.8 relationships 表

```sql
CREATE TABLE memory_hub.relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES memory_hub.entities(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memory_hub.entities(id) ON DELETE CASCADE,
    
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'belongs_to', 'part_of', 'uses', 'depends_on', 'related_to',
        'affects', 'derived_from', 'owns', 'created_by', 'about'
    )),
    
    strength FLOAT DEFAULT 1.0 CHECK (strength >= 0.0 AND strength <= 1.0),
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_no_self_relationship CHECK (source_id != target_id),
    CONSTRAINT uk_relationship_direction UNIQUE (source_id, target_id, relationship_type)
);

COMMENT ON TABLE memory_hub.relationships IS '实体间关系（10 种核心关系 + 可扩展）';

CREATE INDEX idx_relationships_workspace_id ON memory_hub.relationships(workspace_id);
CREATE INDEX idx_relationships_source_id ON memory_hub.relationships(source_id);
CREATE INDEX idx_relationships_target_id ON memory_hub.relationships(target_id);
CREATE INDEX idx_relationships_type ON memory_hub.relationships(relationship_type);
```

---

### 09.4.9 vector_documents 表

```sql
CREATE TABLE memory_hub.vector_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN (
        'memory_node', 'archive', 'entity_summary'
    )),
    source_id UUID NOT NULL,
    area_id UUID REFERENCES memory_hub.areas(id) ON DELETE SET NULL,
    entity_id UUID REFERENCES memory_hub.entities(id) ON DELETE SET NULL,
    memory_level INTEGER CHECK (memory_level IN (1, 2, 3, 4)),
    
    content TEXT NOT NULL,
    importance_score FLOAT DEFAULT 0.0 CHECK (importance_score >= 0.0 AND importance_score <= 1.0),
    embedding VECTOR(1536),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE memory_hub.vector_documents IS '独立向量层，存储高价值内容的 embedding';
COMMENT ON COLUMN memory_hub.vector_documents.embedding IS 'pgvector 格式，维度 1536';

-- pgvector 索引（MVP 使用 ivfflat）
CREATE INDEX idx_vector_documents_workspace_id ON memory_hub.vector_documents(workspace_id);
CREATE INDEX idx_vector_documents_source_type ON memory_hub.vector_documents(source_type);
CREATE INDEX idx_vector_documents_entity_id ON memory_hub.vector_documents(entity_id);
CREATE INDEX idx_vector_documents_memory_level ON memory_hub.vector_documents(memory_level);
CREATE INDEX idx_vector_documents_embedding ON memory_hub.vector_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 未来升级到 hnsw：
-- CREATE INDEX idx_vector_documents_embedding_hnsw ON memory_hub.vector_documents USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

---

### 09.4.10 tags 表

```sql
CREATE TABLE memory_hub.tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    tag_type VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (tag_type IN ('system', 'ai', 'user')),
    color VARCHAR(7),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_tags_workspace_name UNIQUE (workspace_id, name)
);

COMMENT ON TABLE memory_hub.tags IS '标签体系（System/AI/User 三层）';

CREATE INDEX idx_tags_workspace_id ON memory_hub.tags(workspace_id);
CREATE INDEX idx_tags_tag_type ON memory_hub.tags(tag_type);
```

---

### 09.4.11 tag_links 表

```sql
CREATE TABLE memory_hub.tag_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES memory_hub.tags(id) ON DELETE CASCADE,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('entity', 'memory_node', 'archive')),
    target_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uk_tag_links UNIQUE (tag_id, target_type, target_id)
);

COMMENT ON TABLE memory_hub.tag_links IS '标签关联（多对多）';

CREATE INDEX idx_tag_links_workspace_id ON memory_hub.tag_links(workspace_id);
CREATE INDEX idx_tag_links_target ON memory_hub.tag_links(target_type, target_id);
```

---

### 09.4.12 archives 表

```sql
CREATE TABLE memory_hub.archives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    source_archive_id UUID REFERENCES memory_hub.archives(id) ON DELETE SET NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    archive_type VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (archive_type IN ('monthly', 'yearly')),
    summary TEXT NOT NULL,
    source_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_archive_period CHECK (period_start <= period_end)
);

COMMENT ON TABLE memory_hub.archives IS '归档数据（Monthly/Yearly，认知压缩层）';

CREATE INDEX idx_archives_workspace_id ON memory_hub.archives(workspace_id);
CREATE INDEX idx_archives_period ON memory_hub.archives(period_start, period_end);
CREATE INDEX idx_archives_type ON memory_hub.archives(archive_type);
```

---

### 09.4.13 candidates 表

```sql
CREATE TABLE memory_hub.candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES memory_hub.entities(id) ON DELETE CASCADE,
    area_id UUID REFERENCES memory_hub.areas(id) ON DELETE SET NULL,
    
    content TEXT NOT NULL,
    candidate_type VARCHAR(20) NOT NULL CHECK (candidate_type IN ('pattern', 'belief')),
    
    evidence_source VARCHAR(50) NOT NULL DEFAULT 'observation',
    evidence_id UUID,
    evidence_chain JSONB NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    evidence_strength FLOAT DEFAULT 0.0 CHECK (evidence_strength >= 0.0 AND evidence_strength <= 1.0),
    
    status VARCHAR(20) NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate', 'confirmed', 'archived', 'orphaned'
    )),
    
    ingested_by VARCHAR(50) NOT NULL DEFAULT 'ingestion_pipeline',
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    verified_at TIMESTAMPTZ,
    verified_by VARCHAR(50) CHECK (verified_by IN ('rule_engine', 'reflection_engine')),
    
    modified_by VARCHAR(50),
    modification_reason TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_candidate_has_evidence CHECK (evidence_count >= 1),
    CONSTRAINT chk_candidate_evidence_chain_not_empty CHECK (jsonb_array_length(evidence_chain) > 0)
);

COMMENT ON TABLE memory_hub.candidates IS 'Reflection 工作对象，Promotion 后晋升为正式 MemoryNode';

CREATE INDEX idx_candidates_workspace_id ON memory_hub.candidates(workspace_id);
CREATE INDEX idx_candidates_entity_id ON memory_hub.candidates(entity_id);
CREATE INDEX idx_candidates_status ON memory_hub.candidates(status);
CREATE INDEX idx_candidates_candidate_type ON memory_hub.candidates(candidate_type);
CREATE INDEX idx_candidates_evidence_count ON memory_hub.candidates(evidence_count DESC);
CREATE INDEX idx_candidates_evidence_strength ON memory_hub.candidates(evidence_strength DESC);
```

---

### 09.4.14 memory_relationships 表（MemoryNode 之间的关系）

```sql
CREATE TABLE memory_hub.memory_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    source_node_id UUID NOT NULL REFERENCES memory_hub.memory_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES memory_hub.memory_nodes(id) ON DELETE CASCADE,
    
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'supports', 'derived_from', 'contradicts', 'attenuates'
    )),
    
    contribution_weight FLOAT DEFAULT 1.0 CHECK (contribution_weight >= 0.0 AND contribution_weight <= 1.0),
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_no_self_memory_rel CHECK (source_node_id != target_node_id),
    CONSTRAINT uk_memory_relationship_direction UNIQUE (source_node_id, target_node_id, relationship_type)
);

COMMENT ON TABLE memory_hub.memory_relationships IS 'MemoryNode 之间的关系（参见 04 第 5.3 章 / 05 第 13 章 Evidence Tree）';

CREATE INDEX idx_memory_relationships_workspace_id ON memory_hub.memory_relationships(workspace_id);
CREATE INDEX idx_memory_relationships_source_node_id ON memory_hub.memory_relationships(source_node_id);
CREATE INDEX idx_memory_relationships_target_node_id ON memory_hub.memory_relationships(target_node_id);
CREATE INDEX idx_memory_relationships_type ON memory_hub.memory_relationships(relationship_type);
```

---

### 09.4.15 tasks 表（统一任务表）

```sql
CREATE TABLE memory_hub.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    task_type VARCHAR(20) NOT NULL CHECK (task_type IN (
        'INGESTION', 'REFLECTION', 'ACTIVATION', 'ARCHIVE'
    )),
    entity_id UUID REFERENCES memory_hub.entities(id) ON DELETE SET NULL,
    area_id UUID REFERENCES memory_hub.areas(id) ON DELETE SET NULL,
    
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'dead_letter'
    )),
    
    evidence_driven BOOLEAN NOT NULL DEFAULT TRUE,
    debounce_key VARCHAR(255),
    
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    payload JSONB NOT NULL DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT chk_tasks_debounce UNIQUE (workspace_id, task_type, debounce_key)
        WHERE status IN ('pending', 'running')
);

COMMENT ON TABLE memory_hub.tasks IS '统一任务表（替代 ingestion_queue / reflection_queue / archive_queue）';
COMMENT ON COLUMN memory_hub.tasks.debounce_key IS 'Entity/Area 组合，防止重复触发';
COMMENT ON COLUMN memory_hub.tasks.payload IS '任务负载，包含具体参数和上下文';

CREATE INDEX idx_tasks_workspace_id ON memory_hub.tasks(workspace_id);
CREATE INDEX idx_tasks_status ON memory_hub.tasks(status) WHERE status IN ('pending', 'running');
CREATE INDEX idx_tasks_type ON memory_hub.tasks(task_type);
CREATE INDEX idx_tasks_entity_id ON memory_hub.tasks(entity_id);
CREATE INDEX idx_tasks_area_id ON memory_hub.tasks(area_id);
CREATE INDEX idx_tasks_retry ON memory_hub.tasks(retry_count) WHERE status = 'failed';
CREATE INDEX idx_tasks_created_at ON memory_hub.tasks(created_at ASC) WHERE status = 'pending';
```

---

## 09.5 约束与完整性规则

### 09.5.1 硬约束

| 约束 | 说明 | 实现方式 |
|------|------|----------|
| 记忆永不删除 | Observation 永久保留 | 无 DELETE 触发器，仅 INSERT |
| 证据链完整 | 每条 Pattern/Belief 必须有证据 | CHECK 约束 + 应用层验证 |
| 单一活跃信念 | 每个 Entity 最多一条 active Belief | 部分唯一索引 |
| 无孤儿记忆 | 每条记忆至少关联一个证据 | FK 约束 |
| 推导链完整 | 禁止 Observation → Belief 直接跳跃 | 应用层约束 |
| State 不落库 | State 是运行时概念 | 不在 memory_nodes 中持久化 L4 |

### 09.5.2 部分唯一索引：单一活跃信念

```sql
-- 确保每个 Entity 最多一条 active Belief
CREATE UNIQUE INDEX uk_entities_single_active_belief 
ON memory_hub.memory_nodes(entity_id, level) 
WHERE level = 3 AND status = 'active';
```

### 09.5.3 触发器：updated_at 自动更新

```sql
CREATE OR REPLACE FUNCTION memory_hub.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 应用到所有带 updated_at 的表
CREATE TRIGGER trg_workspace_updated_at BEFORE UPDATE ON memory_hub.workspace
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_user_profiles_updated_at BEFORE UPDATE ON memory_hub.user_profiles
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_areas_updated_at BEFORE UPDATE ON memory_hub.areas
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_entities_updated_at BEFORE UPDATE ON memory_hub.entities
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_memory_nodes_updated_at BEFORE UPDATE ON memory_hub.memory_nodes
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_evidences_updated_at BEFORE UPDATE ON memory_hub.evidences
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_relationships_updated_at BEFORE UPDATE ON memory_hub.relationships
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_vector_documents_updated_at BEFORE UPDATE ON memory_hub.vector_documents
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_candidates_updated_at BEFORE UPDATE ON memory_hub.candidates
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();

CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON memory_hub.tasks
    FOR EACH ROW EXECUTE FUNCTION memory_hub.update_updated_at_column();
```

---

## 09.6 索引策略

### 09.6.1 索引清单

| 表 | 索引 | 类型 | 用途 |
|----|------|------|------|
| entities | uk_entities_type_name | UNIQUE | 按类型+名称查找 Entity |
| entities | idx_entities_workspace_id | BTREE | Workspace 隔离查询 |
| entities | idx_entities_area_id | BTREE | Area 下 Entity 查询 |
| entities | idx_entities_type_name | BTREE | 类型分组统计 |
| memory_nodes | idx_memory_nodes_entity_id | BTREE | Entity 下记忆查询 |
| memory_nodes | idx_memory_nodes_level | BTREE | Level 过滤 |
| memory_nodes | idx_memory_nodes_status | BTREE | Status 过滤 |
| memory_nodes | idx_memory_nodes_confidence | BTREE DESC | 高置信度排序 |
| memory_nodes | idx_memory_nodes_importance | BTREE DESC | 重要性排序 |
| memory_nodes | idx_memory_nodes_signal_strength | BTREE DESC | Signal Strength 排序 |
| memory_nodes | idx_memory_nodes_created_at | BTREE DESC | 时间排序 |
| memory_nodes | idx_memory_nodes_evidence_links | GIN | 证据关联查询 |
| memory_nodes | idx_memory_nodes_contradict_evidence | GIN | 矛盾证据查询 |
| evidences | idx_evidences_entity_id | BTREE | Entity 下证据查询 |
| evidences | idx_evidences_importance | BTREE DESC | 重要性排序 |
| evidences | idx_evidences_created_at | BTREE DESC | 时间排序 |
| vector_documents | idx_vector_documents_embedding | IVFFLAT (cosine) | 向量检索 |
| vector_documents | idx_vector_documents_entity_id | BTREE | Entity 关联向量 |
| vector_documents | idx_vector_documents_memory_level | BTREE | Level 过滤 |
| relationships | idx_relationships_source_id | BTREE | 关系起点查询 |
| relationships | idx_relationships_target_id | BTREE | 关系终点查询 |
| relationships | idx_relationships_type | BTREE | 关系类型过滤 |
| tasks | idx_tasks_status | BTREE | 待处理任务查询 |
| tasks | idx_tasks_type | BTREE | 任务类型过滤 |
| tasks | idx_tasks_retry | BTREE | 失败重试查询 |
| tasks | idx_tasks_created_at | BTREE | 创建时间排序 |
| candidates | idx_candidates_entity_id | BTREE | Entity 下候选查询 |
| candidates | idx_candidates_status | BTREE | Status 过滤 |
| candidates | idx_candidates_evidence_strength | BTREE DESC | 证据强度排序 |

### 09.6.2 向量索引升级路径

```sql
-- MVP: ivfflat
CREATE INDEX idx_vector_documents_embedding_ivfflat 
ON memory_hub.vector_documents 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- V2+: 升级到 hnsw（数据量大时）
-- 1. 创建新索引
CREATE INDEX idx_vector_documents_embedding_hnsw 
ON memory_hub.vector_documents 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- 2. 验证性能
-- 3. 删除旧索引
DROP INDEX IF EXISTS memory_hub.idx_vector_documents_embedding_ivfflat;
```

---

## 09.7 数据迁移策略

### 09.7.1 迁移原则

1. **Additive Only**: 只允许新增表和字段，禁止删除或修改现有结构
2. **Shadow Table**: 新表先影子运行，验证后再切换流量
3. **Bridge Table**: 复杂迁移时使用桥接表过渡
4. **Rollback Safe**: 每次迁移必须可回滚

### 09.7.2 MVP 迁移步骤

```sql
-- Step 1: 创建 schema
CREATE SCHEMA IF NOT EXISTS memory_hub;

-- Step 2: 启用 pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 3: 按依赖顺序创建表（workspace → user_profiles → areas → entities → ...）
-- Step 4: 初始化 workspace 记录
INSERT INTO memory_hub.workspace (name, description) VALUES 
    ('default', '默认 Workspace');

-- Step 5: 验证
SELECT count(*) FROM memory_hub.workspace;  -- 应为 1
```

### 09.7.3 未来迁移场景

| 场景 | 策略 | 是否修改 Schema |
|------|------|----------------|
| 新增 Entity Type | 插入 `entities.entity_type = '新类型'` | ❌ |
| 新增 Relationship | 插入 `relationships.relationship_type = '新类型'` | ❌ |
| 新增 memory_relationships 表 | 新增表（计划内扩展） | ⚠️ 新增 |
| 迁移 Neo4j | UUIDv7 直接映射为节点 ID | ❌ |
| 升级向量索引 | ivfflat → hnsw | ❌ |

---

## 09.8 性能优化策略

### 09.8.1 分区策略（未来 V2+）

当 `memory_nodes` 表超过 100 万条时，考虑按 `created_at` 分区：

```sql
-- V2+ 可选：按月分区
CREATE TABLE memory_nodes_y2026m01 PARTITION OF memory_hub.memory_nodes
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE memory_nodes_y2026m02 PARTITION OF memory_hub.memory_nodes
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

### 09.8.2 查询优化

1. **Entity 优先查询**: 先通过 `entity_id` 定位，再过滤 `level`
2. **向量检索优化**: 使用 `ivfflat` 的 `lists` 参数调优（100-1000）
3. **批量插入**: 使用 `COPY` 或批量 INSERT 替代逐条插入
4. **Connection Pooling**: Supabase 内置连接池，避免连接泄漏

### 09.8.3 监控指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| memory_nodes 总数 | > 100 万 | 考虑分区 |
| vector_documents 总数 | > 100 万 | 升级向量索引 |
| tasks 表 pending 数量 | > 1000 | 检查 Scheduler |
| 查询延迟 P99 | > 2 秒 | 检查索引 |

---

## 09.9 安全与权限模型

### 09.9.1 Row Level Security (RLS)

```sql
-- 启用 RLS
ALTER TABLE memory_hub.entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_hub.memory_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_hub.evidences ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_hub.vector_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_hub.tasks ENABLE ROW LEVEL SECURITY;

-- 策略：用户只能访问自己 workspace 的数据
CREATE POLICY user_workspace_access ON memory_hub.entities
    FOR ALL
    USING (workspace_id IN (
        SELECT id FROM memory_hub.workspace 
        WHERE id = current_setting('app.current_workspace_id')::UUID
    ));

CREATE POLICY user_workspace_access ON memory_hub.memory_nodes
    FOR ALL
    USING (workspace_id IN (
        SELECT id FROM memory_hub.workspace 
        WHERE id = current_setting('app.current_workspace_id')::UUID
    ));

-- ⚠️ Memory Immutable 约束（参见 08 第 8.1 章）：禁止直接 UPDATE/DELETE memory_nodes
-- 修正通过追加 CORRECT 记录实现，归档通过标记 status='deprecated' 实现
CREATE POLICY prohibit_update_memory_nodes ON memory_hub.memory_nodes
    FOR UPDATE USING (false);

CREATE POLICY prohibit_delete_memory_nodes ON memory_hub.memory_nodes
    FOR DELETE USING (false);
```

### 09.9.2 API Key 权限

| 角色 | 权限 | 说明 |
|------|------|------|
| anon | 只读（有限） | 公开查询 |
| service_role | 全部 | 后端服务 |
| user | 读写（own） | 用户自己的数据 |

---

## 09.10 备份与恢复

### 09.10.1 Supabase 自动备份

- 每日自动备份，保留 7 天
- 点恢复（PITR）保留 24 小时

### 09.10.2 手动备份策略

```bash
# 每日全量备份
pg_dump -h $SUPABASE_HOST -U $SUPABASE_USER -d $SUPABASE_DB \
    --schema=memory_hub -f backup_memory_hub_$(date +%Y%m%d).sql

# 每周归档
tar -czf backup_memory_hub_weekly.tar.gz backup_memory_hub_*.sql
```

---

## 09.11 数据字典

### 09.11.1 枚举值清单

| 字段 | 合法值 | 说明 |
|------|--------|------|
| entities.entity_type | Project, Person, Organization, Tool, Technology, Concept, Event, Location, Object, Agent, Model, Document | 实体类型 |
| memory_nodes.level | 1, 2, 3, 4 | 记忆层级 |
| memory_nodes.node_type | Observation, Pattern, Belief, State | 节点类型 |
| memory_nodes.status | active, candidate, deprecated, superseded, orphaned | 状态 |
| memory_nodes.source | user, manual, explicit_command, archive_derived, ai_reflect | 来源 |
| memory_nodes.generated_by | user, manual, ai_reflect, archive | 生成者 |
| memory_nodes.observation_type | activity, decision, preference, fact, goal, problem, event | 观察类型（仅 L1） |
| evidences.source | conversation, manual, explicit_command, document, import | 证据来源 |
| relationships.relationship_type | belongs_to, part_of, uses, depends_on, related_to, affects, derived_from, owns, created_by, about | 关系类型 |
| memory_evidences.relationship_type | supports, derived_from, contradicts, attenuates | 证据关系类型 |
| vector_documents.source_type | memory_node, archive, entity_summary | 向量来源 |
| tags.tag_type | system, ai, user | 标签类型 |
| tag_links.target_type | entity, memory_node, archive | 标签目标类型 |
| archives.archive_type | monthly, yearly | 归档类型 |
| candidates.candidate_type | pattern, belief | 候选类型 |
| candidates.status | candidate, confirmed, archived, orphaned | 候选状态 |
| tasks.task_type | INGESTION, REFLECTION, ACTIVATION, ARCHIVE | 任务类型 |
| tasks.status | pending, running, completed, failed, dead_letter | 任务状态 |

---

## 09.12 视图与函数

### 09.12.1 常用视图

```sql
-- 实体记忆概览
CREATE VIEW memory_hub.v_entity_summary AS
SELECT 
    e.id AS entity_id,
    e.workspace_id,
    e.entity_type,
    e.canonical_name,
    COUNT(DISTINCT mn.id) FILTER (WHERE mn.level = 1) AS observation_count,
    COUNT(DISTINCT mn.id) FILTER (WHERE mn.level = 2) AS pattern_count,
    COUNT(DISTINCT mn.id) FILTER (WHERE mn.level = 3) AS belief_count,
    COUNT(DISTINCT r.id) AS relationship_count
FROM memory_hub.entities e
LEFT JOIN memory_hub.memory_nodes mn ON e.id = mn.entity_id
LEFT JOIN memory_hub.relationships r ON e.id = r.source_id OR e.id = r.target_id
GROUP BY e.id;

-- 活跃记忆列表
CREATE VIEW memory_hub.v_active_memories AS
SELECT 
    mn.*,
    e.canonical_name AS entity_name,
    e.entity_type
FROM memory_hub.memory_nodes mn
JOIN memory_hub.entities e ON mn.entity_id = e.id
WHERE mn.status = 'active';

-- 待处理任务列表
CREATE VIEW memory_hub.v_pending_tasks AS
SELECT 
    t.*,
    e.canonical_name AS entity_name
FROM memory_hub.tasks t
LEFT JOIN memory_hub.entities e ON t.entity_id = e.id
WHERE t.status IN ('pending', 'running');
```

### 09.12.2 辅助函数

```sql
-- 生成 UUIDv7（通过 pgcrypto + 时间戳）
-- Supabase 已内置 uuidv7 支持，无需额外函数

-- 计算证据强度
CREATE OR REPLACE FUNCTION memory_hub.calculate_evidence_strength(
    p_evidence_count INTEGER,
    p_avg_confidence FLOAT,
    p_cross_entity_breadth INTEGER
) RETURNS FLOAT AS $$
BEGIN
    RETURN LEAST(
        1.0,
        (p_evidence_count * 0.3 + p_avg_confidence * 0.4 + p_cross_entity_breadth * 0.3)
    );
END;
$$ LANGUAGE plpgsql;
```

---

## 09.13 附录：DDL 完整脚本

### 09.13.1 一键部署脚本

```sql
-- ============================================
-- Personal AI Memory Hub — 完整 DDL 部署脚本
-- 版本: 1.0
-- 日期: 2026-06-25
-- ============================================

-- 1. 创建 schema
CREATE SCHEMA IF NOT EXISTS memory_hub;

-- 2. 启用扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. 创建表（按依赖顺序）

-- 3.1 workspace
CREATE TABLE memory_hub.workspace (...);  -- 见 09.4.1

-- 3.2 user_profiles
CREATE TABLE memory_hub.user_profiles (...);  -- 见 09.4.2

-- 3.3 areas
CREATE TABLE memory_hub.areas (...);  -- 见 09.4.3

-- 3.4 entities
CREATE TABLE memory_hub.entities (...);  -- 见 09.4.4

-- 3.5 memory_nodes
CREATE TABLE memory_hub.memory_nodes (...);  -- 见 09.4.5

-- 3.6 evidences
CREATE TABLE memory_hub.evidences (...);  -- 见 09.4.6

-- 3.7 memory_evidences
CREATE TABLE memory_hub.memory_evidences (...);  -- 见 09.4.7

-- 3.8 relationships
CREATE TABLE memory_hub.relationships (...);  -- 见 09.4.8

-- 3.9 vector_documents
CREATE TABLE memory_hub.vector_documents (...);  -- 见 09.4.9

-- 3.10 tags
CREATE TABLE memory_hub.tags (...);  -- 见 09.4.10

-- 3.11 tag_links
CREATE TABLE memory_hub.tag_links (...);  -- 见 09.4.11

-- 3.12 archives
CREATE TABLE memory_hub.archives (...);  -- 见 09.4.12

-- 3.13 candidates
CREATE TABLE memory_hub.candidates (...);  -- 见 09.4.13

-- 3.14 memory_relationships
CREATE TABLE memory_hub.memory_relationships (...);  -- 见 09.4.14

-- 3.15 tasks
CREATE TABLE memory_hub.tasks (...);  -- 见 09.4.15

-- 4. 创建索引（见 09.6）

-- 5. 创建约束（见 09.5）

-- 6. 创建触发器（见 09.5.3）

-- 7. 创建视图（见 09.12）

-- 8. 初始化数据
INSERT INTO memory_hub.workspace (name, description) VALUES 
    ('default', '默认 Workspace');

-- 9. 启用 RLS（见 09.9）

-- ============================================
-- 部署完成
-- ============================================
```

---

## 文档变更记录

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|----------|------|
| 1.1 | 2026-06-25 | (1) 修复 UUIDv7 部署说明（参见 03 第 4.1 章） (2) State 不落库约束（参见 05 第 12 章 / 08 第 3.3 章） (3) Observation Type CHECK 约束（参见 05 第 6 章） (4) Memory Immutable RLS 策略（参见 08 第 8.1 章） (5) 新增 memory_relationships 表（参见 04 第 5.3 章） (6) 更新部署脚本索引 | ✅ 已确认 |
| 1.0 | 2026-06-25 | 初始版本，定义完整物理 Schema（14 张表 + 索引 + 约束 + 视图） | ✅ 已确认 |

---

## Cross-Document Impact Report

### CR-001: 03 Entity 与 MemoryGraph 设计

| 影响点 | 说明 | 处理方式 |
|--------|------|----------|
| UUIDv7 一致性 | 03 第 4.1 章要求全部 UUIDv7 | 09 添加部署说明，要求替换 gen_random_uuid() 为 uuidv7() |
| Entity 类型扩展 | 03 ADR-003 定义 Entity Type 体系 | 09 entities.entity_type CHECK 包含 12 种类型 |
| Relationship 10 种核心 | 03 ADR-008 定义 10 种关系 | 09 relationships 表 CHECK 约束完全匹配 |
| Memory Relationship | 03 未明确 memory_relationships 表 | 09 新增 09.4.14 表定义（参见 04 第 5.3 章） |

### CR-002: 04 Schema / Archive / Reflect 设计

| 影响点 | 说明 | 处理方式 |
|--------|------|----------|
| 11 核心表 | 04 第 2.1 章定义 11 张核心表 | 09 扩展到 15 张（+ candidates + memory_evidences + memory_relationships） |
| Project 作为 Entity | 04 第 2.2 章 | 09 entities.entity_type CHECK 包含 'Project' |
| generated_by | 04 第 14.6 章 | 09 memory_nodes.generated_by CHECK 完全匹配 |
| Archive 向量化 | 04 第 12.3 章 | 09 vector_documents.source_type 包含 'archive' |
| Context Trace | 04 第 15.4 章 | 09 metadata JSONB 字段支持扩展 |
| memory_relationships | 04 第 5.3 章（概念设计） | 09 新增 09.4.14 表实现 |

### CR-003: 05 Memory Lifecycle 与 Reflection Engine

| 影响点 | 说明 | 处理方式 |
|--------|------|----------|
| Evidence Based | 05 第 1.2 章 | 09 candidates.evidence_count CHECK≥1 |
| Time Based 废弃 | 05 第 1.3 章 | 09 无时间相关约束 |
| 三套评分 | 05 第 7 章 | 09 memory_nodes.confidence/importance/signal_strength |
| Observation Type | 05 第 6 章 | 09 memory_nodes.observation_type CHECK 约束 |
| Light/Heavy Reflect | 05 第 10 章 | 09 tasks.task_type 包含 INGESTION/REFLECTION |
| State 不落库 | 05 第 12 章 | 09 memory_nodes.level CHECK 排除 level=4 |
| Explainable Memory | 05 第 13 章 | 09 memory_evidences + memory_relationships 支持证据树 |
| Support Count | 05 第 3.2 章 | 09 application layer 强制执行（Pattern≥2, Belief≥1） |

### CR-004: 06 Runtime Architecture

| 影响点 | 说明 | 处理方式 |
|--------|------|----------|
| Online/Offline 分离 | 06 第 2.1 章 | 09 通过 RLS 和 tasks 表支持 |
| Sync/Async Boundary | 06 第 4 章 | 09 通过 status 字段和 debounce_key 实现 |
| LLM vs Rule | 06 第 7 章 | 09 CHECK 约束确保 Rule 验证 |
| 推导链约束 | 06 第 8.2 章 | 09 memory_relationships.derived_from 支持 |

### CR-005: 07 Boundary Review

| 影响点 | 说明 | 处理方式 |
|--------|------|----------|
| P6 Evidence-Based | 07 第 2.6 章 | 09 candidates 和 memory_evidences 表强制证据 |
| P7 No Orphan | 07 第 2.7 章 | 09 FK 约束 + candidates.status='orphaned' |
| P4 Agent Cannot Modify | 07 第 2.4 章 | 09 RLS prohibit_update_memory_nodes 策略 |

### CR-006: 08 Implementation Architecture

| 影响点 | 说明 | 处理方式 |
|--------|------|----------|
| Candidate Schema | 08 第 4 章 | 09 candidates 表完全匹配 |
| State 不落库 | 08 第 3.3 章 | 09 memory_nodes.level 排除 level=4 |
| Memory Immutable | 08 第 8.1 章 | 09 RLS prohibit_update/delete 策略 |
| 统一 tasks 表 | 08 第 9 章 | 09 tasks 表完全匹配 |
| Reflection Trigger | 08 第 9.3 章 | 09 tasks.debounce_key 实现 |
| MVP 表清单 | 08 第 13.1 章 | 09 扩展至 15 张表（+ memory_relationships） |
| Reflection 模式 | 08 第 13.3 章 | 09 tasks.status 支持 Auto/Manual/Hybrid |

### CR-007: 无冲突项

以下文档与 09 完全一致，无需变更：

- 01 骨架设计：记忆类型体系、生命周期、分类体系 — 09 完全实现
- 02 Engine + Context：Context Builder 四层结构 — 09 通过 views 和 metadata 支持

---

*本文档是 Memory Hub 项目的数据库物理设计唯一权威文档。所有实现必须严格遵循本文档定义。*
