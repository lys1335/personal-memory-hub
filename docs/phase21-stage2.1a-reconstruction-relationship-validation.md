# Phase 21 Stage 2.1A — Reconstruction Relationship Validation

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 2.1A  
**调查日期**: 2026-08-13  
**范围**: 只读调查，验证 Reconstruction ↔ Candidate 和 Reconstruction ↔ Entity 的关系模型  

---

## 1. Validation Scope

### 1.1 验证目标

验证 Stage 2.1 提出的两个关键关系设计：
1. Reconstruction ↔ Candidate 的基数关系（1:1 vs 1:N）
2. Reconstruction ↔ Entity 的绑定约束（单一 vs 多实体）

### 1.2 禁止范围

以下问题明确排除在本阶段外：
- Topic Definition（Stage 2.2）
- Context Window（Stage 2.3）
- Historical Memory Evolution（Stage 3）
- User Fact Boundary（Stage 2.4）
- Tag Lifecycle（Deferred）
- Semantic Index（Deferred）

---

## 2. Existing Architecture Evidence

### 2.1 Candidate 表的 Entity 绑定

**来源**: `09_Database_Physical_Design.md` §09.4.13

```sql
CREATE TABLE memory_hub.candidates (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL REFERENCES memory_hub.entities(id) ON DELETE CASCADE,
    area_id UUID REFERENCES memory_hub.areas(id) ON DELETE SET NULL,
    ...
);
```

**关键约束**：
- `entity_id UUID NOT NULL` — 强制绑定单一 Entity
- `ON DELETE CASCADE` — Entity 删除时 Candidate 级联删除
- 索引：`idx_candidates_entity_id`

**结论**：现有架构**强制**每个 Candidate 绑定一个 Entity。

### 2.2 Phase 20 Candidate → Proposal 关系

**来源**: `phase-20-candidate-proposal-lifecycle-design.md` §3.1

```
Candidate 1 : N Proposal（历史）
Candidate 1 : 1 Pending Proposal（同时）
```

**设计约束**：
```sql
-- 部分唯一索引：每个 Candidate 最多一个 pending Proposal
CREATE UNIQUE INDEX idx_proposals_one_pending_per_candidate
ON proposals(workspace_id, candidate_id)
WHERE status = 'pending';
```

**关键原则**：
> Pending Proposal 是 Candidate 的"锁"，防止重复 Evolution。

### 2.3 EvidenceEvolutionEngine 的 Entity 关联

**来源**: `D4.2g_EvidenceEvolutionEngine_Architecture.md`

```python
# 输出结构
{
    "entity_id": UUID | None,  # Associated entity
    "entities": ["entity1", "entity2"],  # Extracted entity names
    ...
}
```

**观察**：
- Engine 可以提取多个 Entity 名称
- 但最终输出只有一个 `entity_id`（主实体）
- 这暗示了"主实体 + 元数据记录其他实体"的设计模式

### 2.4 单一活跃信念约束

**来源**: `09_Database_Physical_Design.md` §09.5.2

```sql
-- 确保每个 Entity 最多一条 active Belief
CREATE UNIQUE INDEX uk_entities_single_active_belief 
ON memory_hub.memory_nodes(entity_id, level) 
WHERE level = 3 AND status = 'active';
```

**设计意图**：
- 每个 Entity 在同一时间只能有一个"当前状态"
- 这支持了"单一主实体"的设计哲学

---

## 3. Reconstruction Semantics

### 3.1 Reconstruction 的定义

**Phase 21 Stage 2.1 定义**：
> Reconstruction = 将一组相关 Evidence 重构成当前阶段的、以用户第一人称表达的语义状态。

**关键特征**：
1. **语义聚合**: 将分散的 Evidence 聚合成语义单元
2. **用户视角转换**: 转换为第一人称表达
3. **临时性**: 是 Candidate Formation 的中间状态
4. **可演化**: 可以随新 Evidence 更新（版本链）

### 3.2 Reconstruction 与 Candidate 的区别

| 维度 | Reconstruction | Candidate |
|------|---------------|-----------|
| 定义 | 语义重构的**过程** | 语义重构的**结果** |
| 生命周期 | 短（形成后可能更新） | 长（直到 Proposal 审批） |
| 状态 | initial/active/updated/superseded | candidate/confirmed/archived/orphaned |
| 持久化 | 必须（支持跨会话） | 必须（Phase 20 设计） |
| 输出 | semantic_summary | content + evidence_chain |
| 职责 | 语义聚合 + 用户视角转换 | 独立判断的语义快照 |

**关键洞察**：
> Reconstruction 是"草稿"，Candidate 是"定稿"。

---

## 4. Reconstruction ↔ Candidate Analysis

### 4.1 场景分析

#### 场景 A: 单一 Evidence → 单一 Reconstruction → 单一 Candidate

```
Evidence: "我倾向于采用 A。"
    ↓
R1: "我倾向于采用 A。"
    ↓
C1: "我倾向于采用 A。"
```

**关系**: R1 ↔ C1 = **1:1** ✅

**分析**: 这是最简单的场景，语义完整，无需分割。

---

#### 场景 B: 新 Evidence → 新版本 Reconstruction → 新 Candidate?

```
原始:
  Evidence_1: "我倾向于采用 A。"
  R1: "我倾向于采用 A。"
  C1: "我倾向于采用 A。"

新 Evidence:
  Evidence_2: "重新考虑后，我觉得 B 更合适。"
  
选项 A: R1 被更新成 R2（R1 不再存在）
  ❌ 违反"证据不可变"原则
  ❌ 丢失历史语义状态
  
选项 B: R1/R2 是版本链（R2.parent = R1）
  ✅ 保留历史
  ✅ 支持追溯
  ✅ 符合 Evidence-Based Memory
  
选项 C: R1/R2 是完全不同的 Reconstruction
  ⚠️ 无法表达"演化"关系
  ⚠️ 难以查询"这个语义状态的演化历史"
```

**推荐**: 选项 B — 版本链关系。

**Schema 支持**:
```sql
parent_reconstruction_id UUID REFERENCES memory_hub.reconstructions(id)
```

**关键问题**: R2 是否形成新的 C2？

**分析**:
- 如果 C1 已被 Proposal approved → C1 变成 confirmed → 不能修改 → 必须创建 C2
- 如果 C1 仍是 candidate 状态 → 可以更新 C1.content？
  - ❌ 违反"Candidate 是语义快照"原则
  - ✅ 应该创建新的 C2，C1 保持历史

**结论**: 每个 Reconstruction Version 应该对应一个独立的 Candidate。

---

#### 场景 C: 一个 Reconstruction → 多个 Candidate?

```
Reconstruction:
  "用户决定采用 PostgreSQL，并通过 Docker 部署 Memory Hub。"

Topic Segmentation（Stage 2.2）后:
  Topic 1: PostgreSQL 相关
    → Candidate 1: "用户决定使用 PostgreSQL"
  Topic 2: Docker 相关
    → Candidate 2: "用户决定通过 Docker 部署"
  Topic 3: Memory Hub 相关
    → Candidate 3: "用户准备重新设计 Candidate Formation"
```

**关键判断**: 
- 这是 **Topic Segmentation** 的问题，不是 Reconstruction 本身的问题
- Stage 2.1 明确排除 Topic 设计
- 在 Topic 未定义前，Reconstruction 应该是"语义完整的单元"

**结论**: 
- Stage 2.1 层面: Reconstruction → Candidate = **1:1**
- Stage 2.2 层面: 可能需要 Reconstruction → Topic → Candidate 的中间层

---

#### 场景 D: 长 Reconstruction → 多个 Candidate?

```
Reconstruction:
  "用户决定采用 PostgreSQL，并通过 Docker 部署，同时准备重新设计 Candidate Formation。"

如果强行分割:
  Candidate A: "用户决定采用 PostgreSQL"
  Candidate B: "用户决定通过 Docker 部署"
  Candidate C: "用户准备重新设计 Candidate Formation"
```

**问题**: 
- 这种分割违反了"Semantic Completeness"原则
- 每个 Candidate 应该能够"独立交给 Proposal 判断"
- 分割后的 Candidate 可能语义不完整

**结论**: 
- 不应该在 Reconstruction 层面进行 Topic Segmentation
- 如果确实需要多 Candidate，应该在 ReflectionEngine 层面通过"Split Decision"处理

---

#### 场景 E: 多个 Reconstruction → 一个 Candidate?

```
R1: "用户决定使用 PostgreSQL。"
R2: "用户准备通过 Docker 部署。"

Semantic Reconciliation:
R3: "用户决定使用 PostgreSQL，并通过 Docker 部署。"

R3 产生:
  C1: "用户决定使用 PostgreSQL，并通过 Docker 部署。"
```

**关系**: R1 + R2 → R3 → C1

**分析**:
- R3 是 R1 和 R2 的"语义协调结果"
- R3.parent 应该指向 R1（或 R2）
- C1 应该关联 R3（1:1）

**关键问题**: R1 和 R2 的状态如何处理？
- 如果 R1/R2 是"initial"状态（未形成 Candidate）→ 可以被 R3 supersede
- 如果 R1/R2 已形成 C1/C2 → 应该保持历史，R3 作为新版本

---

### 4.2 Cardinality 选项比较

#### Option 1: Reconstruction 1:1 Candidate

**设计**:
```sql
-- reconstruction 表
candidate_id UUID UNIQUE REFERENCES candidates(id)

-- candidates 表（不变）
-- 无 reconstruction_id 字段
```

**Pipeline**:
```
Evidence → Reconstruction → Candidate → Proposal
   (1)        (1)          (1)        (N)
```

**优点**:
1. ✅ 语义清晰：每个 Reconstruction 形成一个 Candidate
2. ✅ 符合现有架构：Candidate 表结构不变
3. ✅ 支持版本链：parent_reconstruction_id 表达演化
4. ✅ Phase 20 兼容：Candidate → Proposal 关系不受影响

**缺点**:
1. ⚠️ 如果一个 Reconstruction 确实需要多个 Candidate（Topic Segmentation），需要额外机制

**适用场景**: 
- Stage 2.1 层面（Topic 未定义）
- 语义完整的 Reconstruction

---

#### Option 2: Reconstruction 1:N Candidate

**设计**:
```sql
-- reconstruction 表（不变）

-- candidates 表新增字段
reconstruction_id UUID REFERENCES reconstructions(id)
```

**Pipeline**:
```
Evidence → Reconstruction → Candidate_1
                     ↓
                   Candidate_2
                     ↓
                   Candidate_3
```

**优点**:
1. ✅ 支持一个 Reconstruction 产生多个 Candidate
2. ✅ 为 Topic Segmentation 预留空间

**缺点**:
1. ❌ **破坏 Phase 20 设计**: Candidate 的 entity_id 是 NOT NULL，如果多个 Candidate 共享一个 Reconstruction，如何分配 entity_id？
2. ❌ **违反单一活跃信念**: 同一 Entity 可能有多个 active Candidate
3. ❌ **复杂化 lineage**: Candidate → Reconstruction 是多对一，追溯困难
4. ❌ **Stage 2.2 才需要**: Topic 未定义前，不需要这个灵活性

**结论**: **不推荐**。这是 Stage 2.2 的问题。

---

#### Option 3: 多个 Reconstruction Version → 一个 Candidate Snapshot

**设计**:
```sql
-- reconstruction 表
status: initial → active → updated → superseded
parent_reconstruction_id: 版本链

-- candidate 表（不变）
-- 只关联最新的 active Reconstruction
```

**Pipeline**:
```
R1 (initial) → C1
R2 (active, parent=R1) → C1 (更新)
R3 (active, parent=R2) → C1 (更新)
```

**问题**:
1. ❌ **违反"Candidate 是语义快照"原则**: C1 的内容应该固定，不能随 Reconstruction 更新而改变
2. ❌ **丢失历史**: 如果 C1 被 Proposal 审批，后续 R2/R3 的变化无法追溯
3. ❌ **与 Phase 20 冲突**: Candidate confirmed 后不应该再变化

**结论**: **不推荐**。

---

#### Option 4: Reconstruction 与 Candidate 完全独立，通过 lineage 连接

**设计**:
```sql
-- reconstruction 表（不变）

-- candidates 表新增字段
reconstruction_id UUID REFERENCES reconstructions(id)

-- 新增表：reconstruction_candidate_lineage
CREATE TABLE reconstruction_candidate_lineage (
    reconstruction_id UUID REFERENCES reconstructions(id),
    candidate_id UUID REFERENCES candidates(id),
    relationship_type VARCHAR(20) CHECK (relationship_type IN ('forms', 'evolves_from', 'supersedes')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (reconstruction_id, candidate_id)
);
```

**优点**:
1. ✅ 完全灵活：支持任意关系
2. ✅ 不破坏现有架构

**缺点**:
1. ❌ **过度复杂**: 引入额外的关联表
2. ❌ **查询复杂**: 需要 JOIN 才能找到关系
3. ❌ **不必要**: Stage 2.1 不需要这么灵活

**结论**: **不推荐**。

---

### 4.3 关键问题回答

#### Question: Candidate 是 Reconstruction 的"最终结果"，还是"可独立语义单元"？

**分析**:

根据 Phase 21 设计方向：
> Candidate = 可以独立交给 Proposal / Memory Evolution 判断的语义快照。

**解读**:
- "语义快照"意味着 Candidate 应该是**固定的、不可变的**
- 一旦形成，Candidate 的内容不应该随 Reconstruction 更新而改变
- 如果 Reconstruction 演化，应该形成**新的 Candidate**

**结论**: 
> Candidate 是 Reconstruction 在某个时间点的"最终结果"快照。

**推论**:
- 每个 Reconstruction Version 应该对应一个独立的 Candidate
- Reconstruction ↔ Candidate = **1:1**

---

## 5. Cardinality Options

### 5.1 推荐模型

**Recommended**: Option 1 — Reconstruction 1:1 Candidate

**Schema**:
```sql
-- reconstructions 表
CREATE TABLE memory_hub.reconstructions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL,  -- 主实体
    
    semantic_summary TEXT NOT NULL,
    decision_type VARCHAR(20),
    confidence FLOAT,
    
    evidence_refs JSONB NOT NULL,
    evidence_count INTEGER NOT NULL,
    
    parent_reconstruction_id UUID REFERENCES memory_hub.reconstructions(id),
    
    status VARCHAR(20) NOT NULL DEFAULT 'initial',
    candidate_id UUID UNIQUE REFERENCES memory_hub.candidates(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- candidates 表（不变）
-- 通过 reconstruction.candidate_id 反向引用
```

**关系图**:
```
Evidence (N) → Reconstruction (1) → Candidate (1) → Proposal (N)
                ↑                      ↑
           entity_id (FK)         entity_id (FK)
                ↓                      ↓
             Entity (1) ←——————— Entity (1)
```

**关键约束**:
1. 一个 Reconstruction 对应一个 Candidate（candidate_id UNIQUE）
2. 一个 Candidate 对应一个 Reconstruction（通过 FK 反向约束）
3. 一个 Entity 可以有多个 Reconstruction（按时间排序）
4. 版本链通过 parent_reconstruction_id 表达

---

### 5.2 版本链设计

**场景**: R1 → R2 → R3 演化

```
R1 (initial, entity=E1) → C1 (candidate)
    ↓ parent
R2 (active, entity=E1, parent=R1) → C2 (candidate)
    ↓ parent
R3 (active, entity=E1, parent=R2) → C3 (candidate)
```

**状态转换**:
- R1: initial → superseded（当 R2 创建）
- R2: initial → active → superseded（当 R3 创建）
- R3: initial → active

**Candidate 状态**:
- C1: candidate → confirmed（如果 Proposal 批准）
- C2: candidate
- C3: candidate

**关键原则**:
> 旧的 Candidate 保持历史，新的 Reconstruction 形成新的 Candidate。

---

## 6. Version / Snapshot Analysis

### 6.1 Reconstruction 版本 vs Candidate 快照

| 概念 | Reconstruction | Candidate |
|------|---------------|-----------|
| 本质 | 语义重构过程 | 语义快照结果 |
| 可变性 | 可变（版本链） | 不可变（快照） |
| 生命周期 | 短（可能被 superseded） | 长（直到 Proposal 审批） |
|  purpose | 支持演化追溯 | 独立判断单元 |

### 6.2 何时创建新 Candidate

**规则**:
1. 当 Reconstruction 从 `initial` → `active` 时，创建 Candidate
2. 当 Reconstruction 被更新（新 Evidence 到达），创建新版本的 Reconstruction，形成新的 Candidate
3. 旧的 Candidate 保持历史，不被修改

**例外**:
- 如果旧 Candidate 仍是 `candidate` 状态（未审批），是否应该废弃？
  - ✅ 应该：标记为 `orphaned`，因为已有更新的 Candidate
  - ❌ 不应该：保留作为历史（但这样会导致同一语义状态有多个 Candidate）

**推荐**: 标记为 `orphaned`，因为"Pending Proposal 是 Candidate 的锁"，新 Candidate 应该获得锁。

---

## 7. Reconstruction ↔ Entity Analysis

### 7.1 当前约束

**现有设计**:
```sql
-- candidates 表
entity_id UUID NOT NULL REFERENCES memory_hub.entities(id)

-- reconstructions 表（Stage 2.1 提议）
entity_id UUID NOT NULL REFERENCES memory_hub.entities(id)
```

**约束**: 强制绑定单一 Entity。

### 7.2 场景分析

**场景**: 
```
Reconstruction: "我决定使用 PostgreSQL，并通过 Docker 部署 Memory Hub。"

涉及的 Entity:
- PostgreSQL（Technology）
- Docker（Tool）
- Memory Hub（Project）
```

**问题**: 应该绑定哪个 Entity？

**选项分析**:

#### 选项 A: 单一 primary_entity

**设计**:
```sql
entity_id UUID NOT NULL  -- 主实体
metadata JSONB           -- 包含其他相关 Entity ID
```

**优点**:
1. ✅ 符合现有架构（candidates 表已这样设计）
2. ✅ 简单：查询时只需 JOIN 一次
3. ✅ 支持"单一活跃信念"约束

**缺点**:
1. ⚠️ 需要定义"主实体"的选择规则
2. ⚠️ 其他 Entity 只能通过 metadata 查询

**推荐**: ✅ **推荐**。这是最符合现有架构的方案。

---

#### 选项 B: 多个 entities（N:N 关系）

**设计**:
```sql
-- 新增表
CREATE TABLE reconstruction_entities (
    reconstruction_id UUID REFERENCES reconstructions(id),
    entity_id UUID REFERENCES entities(id),
    is_primary BOOLEAN DEFAULT false,
    PRIMARY KEY (reconstruction_id, entity_id)
);
```

**优点**:
1. ✅ 灵活：可以表达多实体关系
2. ✅ 查询方便：标准 JOIN

**缺点**:
1. ❌ **破坏现有架构**: candidates 表强制单一 entity_id
2. ❌ **与单一活跃信念冲突**: 同一时间多个 Entity 可能有 active Reconstruction
3. ❌ **Stage 2.2 才需要**: Topic 未定义前，不需要这么灵活

**结论**: **不推荐**。

---

#### 选项 C: Reconstruction 不直接绑定 Entity

**设计**:
```sql
-- reconstruction 表无 entity_id
-- Entity 关联通过 Candidate 或 Topic 间接表达
```

**优点**:
1. ✅ 灵活

**缺点**:
1. ❌ **违反现有架构**: 所有记忆对象都绑定 Entity
2. ❌ **查询困难**: 无法按 Entity 查询 Reconstruction
3. ❌ **不一致**: 与 candidates、evidences、memory_nodes 的设计哲学冲突

**结论**: **不推荐**。

---

#### 选项 D: 其他（如 Entity Graph）

**分析**: 这属于"Entity 关系图"设计，超出 Stage 2.1 范围。

**结论**: **Deferred**。

---

### 7.3 主实体选择规则

**建议规则**:
1. **内容主导**: Reconstruction 内容主要关于哪个 Entity？
2. **证据集中**: 多数 Evidence 关联到哪个 Entity？
3. **用户意图**: 用户主要想表达关于哪个 Entity 的语义？
4. **默认规则**: 如果无法判断，选择第一个提取的 Entity

**实现**: 在 EvidenceEvolutionEngine 的 Entity Extraction 阶段确定主实体。

---

## 8. Relationship Matrix

### 8.1 完整关系图

```
┌─────────────┐     N:1      ┌─────────────┐     1:1      ┌─────────────┐     1:N      ┌─────────────┐
│   Evidence   │────────────▶│Reconstruction│────────────▶│ Candidate   │────────────▶│  Proposal   │
│              │             │              │             │             │             │             │
│ - id         │             │ - id         │             │ - id        │             │ - id        │
│ - content    │             │ - entity_id  │             │ - entity_id │             │ - entity_id │
│ - entity_id  │             │ - status     │             │ - status    │             │ - status    │
│              │             │ - parent_id  │             │ - content   │             │ - content   │
└─────────────┘             └─────────────┘             └─────────────┘             └─────────────┘
      │                           │                           │                           │
      │ 1:N                       │ 1:1                       │ 1:1                       │ N:1
      ▼                           ▼                           ▼                           ▼
┌─────────────┐             ┌─────────────┐             ┌─────────────┐             ┌─────────────┐
│   Entity    │◀────────────│Reconstruction│             │ Candidate   │────────────▶│  MemoryNode │
│             │   N:1       │   (primary) │             │   (snapshot)│  1:1        │             │
└─────────────┘             └─────────────┘             └─────────────┘             └─────────────┘
```

### 8.2 关系详细说明

| 关系 | 基数 | 说明 |
|------|------|------|
| Evidence → Reconstruction | N:1 | 多个 Evidence 可以属于同一个 Reconstruction |
| Reconstruction → Entity | N:1 | Reconstruction 有 N 个相关 Entity，但只有一个 primary_entity |
| Reconstruction → Reconstruction | 1:1 (self) | 版本链：parent_reconstruction_id |
| Reconstruction → Candidate | 1:1 | 每个 Reconstruction 形成一个 Candidate |
| Candidate → Entity | N:1 | Candidate 绑定单一 Entity（现有设计） |
| Candidate → Proposal | 1:N | 一个 Candidate 可以产生多个 Proposal（历史） |
| Proposal → MemoryNode | 1:1 | 一个 Proposal 形成一个 MemoryNode（如果批准） |

### 8.3 Lineage 追溯路径

**路径 1**: Candidate → Evidence
```sql
SELECT e.* FROM evidences e
JOIN reconstructions r ON e.id = ANY(r.evidence_refs)
WHERE r.candidate_id = :candidate_id;
```

**路径 2**: Candidate → Parent Reconstruction
```sql
SELECT r.* FROM reconstructions r
JOIN candidates c ON r.candidate_id = c.id
WHERE c.id = :candidate_id
AND r.parent_reconstruction_id IS NOT NULL;
```

**路径 3**: Entity → All Reconstructions
```sql
SELECT r.* FROM reconstructions r
WHERE r.entity_id = :entity_id
ORDER BY r.created_at DESC;
```

---

## 9. Phase 20 Compatibility

### 9.1 不影响的部分

| Phase 20 设计 | Reconstruction 影响 | 兼容性 |
|--------------|-------------------|--------|
| proposals.candidate_id FK | 无影响 | ✅ 兼容 |
| Candidate lifecycle | 无影响 | ✅ 兼容 |
| Pending Proposal dedup | 无影响 | ✅ 兼容 |
| Evolution scope | 无影响 | ✅ 兼容 |

### 9.2 需要确认的部分

**问题**: Reconstruction 更新是否会导致 Candidate ID 改变？

**答案**: **不会**。

**原因**:
1. 每个 Reconstruction Version 形成独立的 Candidate
2. 旧的 Candidate 保持历史，不被修改
3. 新的 Reconstruction Version 形成新的 Candidate（新的 ID）

**示例**:
```
T1: R1 → C1 (id=C001)
T2: R2 (parent=R1) → C2 (id=C002)
T3: R3 (parent=R2) → C3 (id=C003)

C001, C002, C003 是三个独立的 Candidate
C001 的 Proposal lineage 不受影响
```

### 9.3 关键原则

> **Reconstruction 演化不破坏 Candidate lineage**。

每个 Candidate 是其 Reconstruction Version 的固定快照，不受后续演化的影响。

---

## 10. Recommended Relationship Model

### 10.1 最终决策

#### Question 1: Reconstruction ↔ Candidate 应该是？

**Answer**: **1:1**

**理由**:
1. Candidate 是"语义快照"，应该是固定的
2. 每个 Reconstruction Version 形成独立的 Candidate
3. 符合 Phase 20 设计（Candidate → Proposal 1:N）
4. 支持版本链追溯（通过 parent_reconstruction_id）

#### Question 2: Reconstruction 是否应该允许多个 Entity？

**Answer**: **否**（Stage 2.1 层面）

**理由**:
1. 符合现有架构（candidates 表强制单一 entity_id）
2. 支持"单一活跃信念"约束
3. Topic Segmentation（Stage 2.2）会解决这个问题
4. 多实体关系可以通过 metadata 辅助表达

#### Question 3: candidate_id UUID UNIQUE 是否应该保留？

**Answer**: **是**

**理由**:
1. 确保 1:1 关系
2. 支持反向查询（Candidate → Reconstruction）
3. 符合现有架构风格

#### Question 4: entity_id UUID NOT NULL 是否应该保留？

**Answer**: **是**

**理由**:
1. 符合现有架构（candidates、evidences、memory_nodes 都这样设计）
2. 支持 Entity 优先查询
3. Topic 设计（Stage 2.2）不会改变这个约束

#### Question 5: Stage 2.1 哪部分需要修改？

**Answer**: **不需要修改**。

Stage 2.1 的原始设计：
```sql
candidate_id UUID UNIQUE  -- ✅ 保留
entity_id UUID NOT NULL   -- ✅ 保留
```

完全符合本验证的结论。

---

### 10.2 完整 Schema

```sql
-- Reconstruction 表
CREATE TABLE memory_hub.reconstructions (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES memory_hub.entities(id) ON DELETE CASCADE,
    
    semantic_summary TEXT NOT NULL,
    decision_type VARCHAR(20) CHECK (decision_type IN (
        'EXTEND', 'REFINE', 'CHANGE', 'NEW', 'UNRELATED', 'ABSTAIN'
    )),
    confidence FLOAT CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    evidence_refs JSONB NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 1),
    
    parent_reconstruction_id UUID REFERENCES memory_hub.reconstructions(id),
    
    status VARCHAR(20) NOT NULL DEFAULT 'initial' CHECK (status IN (
        'initial', 'active', 'updated', 'superseded', 'archived'
    )),
    
    candidate_id UUID UNIQUE REFERENCES memory_hub.candidates(id),
    
    metadata JSONB DEFAULT '{}',  -- 可选：记录其他相关 Entity ID
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_reconstruction_evidence_chain CHECK (jsonb_array_length(evidence_refs) > 0)
);

-- 索引
CREATE INDEX idx_reconstructions_workspace_id ON memory_hub.reconstructions(workspace_id);
CREATE INDEX idx_reconstructions_entity_id ON memory_hub.reconstructions(entity_id);
CREATE INDEX idx_reconstructions_status ON memory_hub.reconstructions(status);
CREATE INDEX idx_reconstructions_candidate_id ON memory_hub.reconstructions(candidate_id);
CREATE INDEX idx_reconstructions_parent_id ON memory_hub.reconstructions(parent_reconstruction_id);
CREATE INDEX idx_reconstructions_created_at ON memory_hub.reconstructions(created_at DESC);
```

---

## 11. Required Changes to Stage 2.1 Decision

### 11.1 确认不变的决策

| Stage 2.1 决策 | 验证结果 | 状态 |
|---------------|---------|------|
| Reconstruction 持久化 | ✅ 必须持久化 | 确认 |
| 独立表（Option D） | ✅ 推荐 | 确认 |
| candidate_id UUID UNIQUE | ✅ 1:1 关系 | 确认 |
| entity_id UUID NOT NULL | ✅ 单一主实体 | 确认 |
| semantic_summary（压缩） | ✅ 数据量可控 | 确认 |

### 11.2 新增的约束

| 约束 | 说明 |
|------|------|
| 版本链约束 | parent_reconstruction_id 形成版本链 |
| 状态转换约束 | initial → active → updated → superseded |
| Candidate 创建规则 | 每个 active Reconstruction 必须对应一个 Candidate |
| 旧 Candidate 处理 | 新 Candidate 形成后，旧 Candidate 应标记为 orphaned（如果仍是 candidate 状态） |

### 11.3 明确留给后续 Stage 的问题

| 问题 | 所属 Stage |
|------|-----------|
| Topic Segmentation 规则 | Stage 2.2 |
| 多 Entity 关系（如果确实需要） | Stage 2.2（通过 Topic） |
| Semantic Reconciliation 算法 | Stage 2.3 |
| Context Window 定义 | Stage 2.3 |

---

## 12. Deferred Questions

以下问题明确留给后续 Stage 或 Future Phase：

| 问题 | 优先级 | 所属 Stage | 理由 |
|------|--------|-----------|------|
| Topic Segmentation 何时触发 | P0 | Stage 2.2 | Topic 未定义 |
| 多 Entity Reconstruction 如何处理 | P1 | Stage 2.2 | 可通过 metadata 暂存 |
| Reconstruction 失败重试机制 | P2 | Stage 3 | 属于 Engineering 问题 |
| 历史 Reconstruction 查询优化 | P2 | Deferred | 性能问题，非设计问题 |
| Reconstruction 与 Tag 关系 | P2 | Deferred | Tag Lifecycle 已推迟 |

---

## 附录 A: 关键设计决策总结

| 决策项 | 选择 | 理由 |
|--------|------|------|
| Reconstruction ↔ Candidate | **1:1** | Candidate 是语义快照，固定不变 |
| Reconstruction ↔ Entity | **N:1**（单一主实体） | 符合现有架构，支持单一活跃信念 |
| 版本链 | **parent_reconstruction_id** | 支持演化追溯 |
| 旧 Candidate 处理 | **orphaned** | 避免重复 Evolution |
| Stage 2.1 原决策 | **确认不变** | 验证通过 |

---

## 附录 B: 关系图（Mermaid）

```mermaid
erDiagram
    EVIDENCES ||--o{ RECONSTRUCTIONS : "evidence_refs"
    RECONSTRUCTIONS ||--o| CANDIDATES : "candidate_id (1:1)"
    RECONSTRUCTIONS ||--o{ RECONSTRUCTIONS : "parent_reconstruction_id (version chain)"
    RECONSTRUCTIONS }o--|| ENTITIES : "entity_id (N:1)"
    CANDIDATES ||--o{ PROPOSALS : "candidate_id (1:N)"
    
    EVIDENCES {
        UUID id
        UUID workspace_id
        UUID entity_id
        TEXT content
    }
    
    RECONSTRUCTIONS {
        UUID id
        UUID workspace_id
        UUID entity_id
        TEXT semantic_summary
        VARCHAR status
        UUID parent_reconstruction_id
        UUID candidate_id (UNIQUE)
        JSONB evidence_refs
    }
    
    CANDIDATES {
        UUID id
        UUID workspace_id
        UUID entity_id
        TEXT content
        VARCHAR status
    }
    
    ENTITIES {
        UUID id
        UUID workspace_id
        VARCHAR canonical_name
    }
    
    PROPOSALS {
        UUID id
        UUID workspace_id
        UUID candidate_id
        VARCHAR status
    }
```

---

*本报告为只读调查，不修改任何代码、数据库、Schema、测试或设计文档。*
*验证结论可直接用于 Stage 2.1 决策冻结。*

---

**STOP** — 不编码、不提交 Git，等待下一步指示。
