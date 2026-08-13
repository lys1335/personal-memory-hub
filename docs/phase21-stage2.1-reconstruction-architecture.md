# Phase 21 Stage 2.1 — Reconstruction Architecture Decision

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 2.1  
**调查日期**: 2026-08-13  
**范围**: 只读调查，不修改任何代码、数据库、Schema、测试或设计文档  

---

## 1. Decision Context

### 1.1 决策背景

Phase 21 的核心设计方向是引入 **Semantic Reconstruction** 概念，作为 Evidence → Candidate 之间的中间层。

**核心需求**：
1. 用户短回复（如"对，就这样"）需要结合前文理解
2. Conversation 可能偏离主题后再回来
3. 不同 Conversation 可能属于同一个长期语义状态
4. 几个月后重新打开旧 Conversation 需要能继续同一语义状态

**问题**：现有架构中没有 Reconstruction 概念，Candidate 直接由 EvidenceEvolutionEngine 创建。

### 1.2 决策目标

决定 Reconstruction 在 Personal Memory Hub 中应该是什么架构实体：
- 是否需要持久化为独立数据模型？
- 与 Candidate 的边界是什么？
- 生命周期如何管理？

---

## 2. Existing Architecture Constraints

### 2.1 现有 Pipeline 设计

**来源**: `D4.2d_ReflectionEngine_Architecture_v1.1.md` §1.2

```
Evidence → EvidenceEvolutionEngine → Candidate → ReflectionEngine → Proposal → Approval → MemoryNode
```

**关键观察**：
- EvidenceEvolutionEngine 的直接输出是 Candidate
- 没有中间 Reconstruction 层
- Candidate 被定义为"Reflection 工作对象"

### 2.2 Candidate 表结构

**来源**: `09_Database_Physical_Design.md` §09.4.13

```sql
CREATE TABLE memory_hub.candidates (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    area_id UUID,
    
    content TEXT NOT NULL,
    candidate_type VARCHAR(20) CHECK (candidate_type IN ('pattern', 'belief')),
    
    evidence_source VARCHAR(50) DEFAULT 'observation',
    evidence_id UUID,
    evidence_chain JSONB NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0,
    evidence_strength FLOAT DEFAULT 0.0,
    
    status VARCHAR(20) NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate', 'confirmed', 'archived', 'orphaned'
    )),
    
    ingested_by VARCHAR(50) DEFAULT 'ingestion_pipeline',
    ingestion_timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    verified_at TIMESTAMPTZ,
    verified_by VARCHAR(50) CHECK (verified_by IN ('rule_engine', 'reflection_engine')),
    
    modified_by VARCHAR(50),
    modification_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_candidate_has_evidence CHECK (evidence_count >= 1),
    CONSTRAINT chk_candidate_evidence_chain_not_empty CHECK (jsonb_array_length(evidence_chain) > 0)
);

COMMENT ON TABLE memory_hub.candidates IS 'Reflection 工作对象，Promotion 后晋升为正式 MemoryNode';
```

**关键约束**：
1. `evidence_chain` 必须非空（CHECK 约束）
2. `evidence_count >= 1`（CHECK 约束）
3. `entity_id` 必须关联到 Entity（FK 约束）
4. `status` 只能是四个值之一

### 2.3 EvidenceEvolutionEngine 职责

**来源**: `D4.2g_EvidenceEvolutionEngine_Architecture.md`

EvidenceEvolutionEngine 负责：
- Entity Extraction（LLM）
- Pattern Discovery（Rule）
- Evidence Aggregation（Rule）
- Evidence Chain Construction（Rule）
- Confidence Estimation（Rule）

**输出**: Candidate

**关键观察**：
- EvidenceAggregation 是将多个 Evidence 聚合成一个 Candidate 的步骤
- 但当前设计中，这个聚合结果直接成为 Candidate
- 没有"聚合后的语义状态"这一中间概念

### 2.4 ReflectionEngine 职责

**来源**: `D4.2d_ReflectionEngine_Architecture_v1.1.md` §2.1

ReflectionEngine 负责：
- Memory Creation Decision（是否创建新 Memory）
- Merge Decision（是否合并到现有 Memory）
- Split Decision（是否拆分为多个 Memory）
- Strengthen Decision（是否加强现有 Memory 置信度）
- Refine Decision（是否精炼现有 Memory 内容）
- Reject Decision（是否拒绝 Candidate）

**输入**: Candidate

**关键观察**：
- ReflectionEngine 的决策是基于 Candidate 的
- 如果 Candidate 语义不完整，ReflectionEngine 无法做出正确决策
- 这就是 Phase 21 引入 Reconstruction 的原因

---

## 3. Current Candidate Semantics

### 3.1 现有定义

**设计文档定义**：
> Candidate = Reflection 工作对象，Promotion 后晋升为正式 MemoryNode

**Phase 21 讨论定义**：
> Candidate = 从 Semantic Reconstruction 中形成的、可以独立交给 Memory Evolution 判断的语义快照。

### 3.2 现有语义问题

**问题 1**: Candidate 直接等于 Evidence 聚合结果

```
当前流程：
Evidence_1 ─┐
Evidence_2 ─┼→ EvidenceAggregation → Candidate
Evidence_3 ─┘
```

**问题**: 如果 Evidence_1 是 AI 的建议，Evidence_2 是用户的确认，直接聚合会得到：
```
Candidate.content = "AI建议 + 用户确认"（混合内容）
```

这违反了 Phase 21 的核心原则：
> AI 的陈述、建议、分析只能作为上下文，不能直接变成用户事实

**问题 2**: Candidate 没有语义重构过程

```
当前流程：
Evidence → [黑盒聚合] → Candidate
```

**问题**: "黑盒聚合"是什么？是简单拼接？是 LLM 总结？是规则提取？

当前代码（`reflection_service.py`）中，Candidate 创建逻辑不清晰，但显然缺少语义重构步骤。

**问题 3**: Candidate 无法表达"用户视角语义状态"

**示例场景**：
```
Conversation A:
  User: "我在考虑架构选择"
  AI: "你应该采用 A 架构"
  User: "对，就这样"

Conversation B (几个月后):
  User: "继续讨论架构"
  System: "找到 Conversation A 的语义状态"
```

**问题**: 如何找到 Conversation A 的语义状态？
- 如果只存了 Candidate = "你应该采用 A 架构"，这是 AI 的建议，不是用户事实
- 如果只存了 Candidate = "对，就这样"，这是无意义的短回复
- 正确的语义状态应该是："我确认采用 A 架构"

**结论**: 需要一个语义重构步骤，将分散的 Evidence 重构成"用户视角语义状态"。

---

## 4. Reconstruction Responsibilities

### 4.1 核心职责

**Reconstruction 应该负责**：
1. **语义聚合**: 将一组相关 Evidence 聚合成语义单元
2. **用户视角转换**: 将混合内容（AI 建议 + 用户确认）转换为纯用户事实
3. **语义完整性检查**: 确保 Reconstruction 有足够的证据支持
4. **跨会话连续性**: 支持识别"这是同一个长期语义状态"

**Reconstruction 不应该负责**：
1. ~~提案生成~~（这是 ReflectionEngine 的职责）
2. ~~审批决策~~（这是 Service 层的职责）
3. ~~Memory 创建~~（这是 Approval 的职责）

### 4.2 Reconstruction 输出

**Reconstruction 应该输出**：
1. **semantic_content**: 用户视角的语义状态（第一人称）
2. **evidence_refs**: 引用的 Evidence ID 列表
3. **decision_type**: EXTEND / REFINE / CHANGE / NEW / UNRELATED / ABSTAIN
4. **confidence**: 语义完整性置信度
5. **lineage**: 追溯链（哪些 Evidence → 哪个 Reconstruction → 哪个 Candidate）

**Reconstruction 不输出**：
1. ~~Proposal~~（由 ReflectionEngine 生成）
2. ~~MemoryNode~~（由 Approval 创建）

### 4.3 Reconstruction 与 Candidate 的关系

**关键问题**: Reconstruction 和 Candidate 是同一个东西吗？

**分析**：

| 维度 | Reconstruction | Candidate |
|------|---------------|-----------|
| 定义 | 语义重构的中间状态 | 可以独立判断的语义快照 |
| 生命周期 | 短生命周期（形成后可能更新） | 长生命周期（直到 Proposal 审批） |
| 持久化 | 可选（见下文分析） | 必须持久化 |
| 状态 | initial / active / updated / superseded | candidate / confirmed / archived / orphaned |
| 输出 | semantic_content + decision_type | content + evidence_chain + status |

**结论**: Reconstruction 和 Candidate 是**不同阶段**的概念：
- Reconstruction 是"形成过程"
- Candidate 是"形成结果"

**类比**：
```
Reconstruction ≈ 草稿
Candidate ≈ 定稿
```

---

## 5. Architecture Options

### Option A — Persistent Reconstruction Entity

**设计**：
```sql
CREATE TABLE memory_hub.reconstructions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES memory_hub.workspace(id),
    entity_id UUID NOT NULL REFERENCES memory_hub.entities(id),
    
    semantic_content TEXT NOT NULL,
    decision_type VARCHAR(20) CHECK (decision_type IN (
        'EXTEND', 'REFINE', 'CHANGE', 'NEW', 'UNRELATED', 'ABSTAIN'
    )),
    
    evidence_refs JSONB NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0,
    confidence FLOAT DEFAULT 0.0,
    
    parent_reconstruction_id UUID REFERENCES memory_hub.reconstructions(id),
    
    status VARCHAR(20) NOT NULL DEFAULT 'initial' CHECK (status IN (
        'initial', 'active', 'updated', 'superseded', 'archived'
    )),
    
    candidate_id UUID REFERENCES memory_hub.candidates(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_reconstruction_evidence CHECK (evidence_count >= 1)
);
```

**Pipeline**：
```
Evidence → EvidenceEvolutionEngine → [Reconstruction] → Candidate → ReflectionEngine → Proposal
```

**优点**：
1. ✅ 语义清晰：Reconstruction ≠ Candidate
2. ✅ 支持跨会话连续性：可以查询"这个 Entity 的最近 active Reconstruction"
3. ✅ 支持人工调试：可以看到语义重构的中间结果
4. ✅ 支持失败重试：Reconstruction 失败不影响 Evidence
5. ✅ 符合 Evidence-Based Memory 原则：每层都有明确 lineage

**缺点**：
1. ❌ 新增表：增加 Schema 复杂度
2. ❌ 新增状态管理：Reconstruction 有自己的状态机
3. ❌ 数据冗余：semantic_content 和 Candidate.content 可能相似
4. ❌ 性能开销：新增 JOIN 查询

**数据生命周期**：
```
initial → active → updated → superseded
                ↓
            archived (手动)
            
superseded 的 Reconstruction 保留作为历史，不删除
```

**与现有架构兼容性**：
- ✅ EvidenceEvolutionEngine 输出 Reconstruction（需修改）
- ✅ Candidate 保持现有结构（无需修改）
- ✅ ReflectionEngine 输入从 Candidate 改为 Candidate（无需修改）
- ⚠️ 需要新增 ReconstructionRepository

---

### Option B — Candidate as Reconstruction

**设计**：
不新增表，Candidate 表承担 Reconstruction 职责。

**修改 Candidate 表**：
```sql
-- 新增字段
ALTER TABLE memory_hub.candidates ADD COLUMN decision_type VARCHAR(20);
ALTER TABLE memory_hub.candidates ADD COLUMN parent_candidate_id UUID;
ALTER TABLE memory_hub.candidates ADD COLUMN reconstruction_version INTEGER DEFAULT 1;
```

**Pipeline**：
```
Evidence → EvidenceEvolutionEngine → Candidate (reconstruction version 1)
                                      ↓ (如果有新 Evidence)
                                 Candidate (reconstruction version 2, parent = v1)
                                      ↓
                                 ReflectionEngine
```

**优点**：
1. ✅ 无需新增表
2. ✅ 简单：只有一个实体
3. ✅ 符合现有架构

**缺点**：
1. ❌ 语义混淆：Candidate 既是"草稿"又是"定稿"
2. ❌ 状态冲突：`candidate` 状态既表示"待处理"又表示"语义重构中"
3. ❌ lineage 复杂：需要自引用 Parent 字段
4. ❌ 违反单一职责：Candidate 承担了过多职责

**关键冲突**：
```
现有定义：
  Candidate = "Reflection 工作对象，Promotion 后晋升为正式 MemoryNode"

Phase 21 需求：
  Reconstruction = "语义重构的中间状态"
  Candidate = "语义快照，可以独立判断"

如果合并：
  Candidate = "语义重构的中间状态" AND "语义快照"
  
问题：何时是"中间状态"？何时是"快照"？
答案：不明确。
```

**结论**：**不推荐**。语义混淆会导致后续维护困难。

---

### Option C — Ephemeral Reconstruction

**设计**：
Reconstruction 不作为持久化实体，仅在内存中计算。

**Pipeline**：
```
Evidence → EvidenceEvolutionEngine → [in-memory Reconstruction] → Candidate → ReflectionEngine → Proposal
```

**实现方式**：
- EvidenceEvolutionEngine 内部计算 Reconstruction
- Reconstruction 结果直接生成 Candidate
- 不存储 Reconstruction 对象

**优点**：
1. ✅ 最简单：无需新增表
2. ✅ 无状态管理负担
3. ✅ 符合现有架构

**缺点**：
1. ❌ **无法支持跨会话连续性**：
   - 用户几个月后重新打开 Conversation
   - 系统无法找到之前的 Reconstruction
   - 只能重新计算（可能结果不同）
   
2. ❌ **无法支持人工调试**：
   - 无法查看历史 Reconstruction
   - 无法追溯"为什么形成这个 Candidate"
   
3. ❌ **无法支持失败重试**：
   - Reconstruction 失败只能重新处理所有 Evidence
   - 无法定位具体问题

4. ❌ **不符合 Evidence-Based Memory 原则**：
   - Evidence 永久保留
   - 但 Reconstruction 不保留
   - 导致"证据在，语义不在"

**关键问题**：
> 如果 Reconstruction 不持久化，"系统凭什么找到 R1？"

**答案**：
- 通过 Entity 关联：找到同一 Entity 的所有 Evidence
- 通过 Tag 关联：找到同一 Tag 的所有 Evidence
- 通过 Embedding 相似：找到语义相似的 Evidence

**但这些问题**：
1. 都是"Recall Signal"，不是"语义状态"
2. 重新计算的 Reconstruction 可能与原来不同
3. 无法保证"继续同一语义状态"

**结论**：**不推荐**，除非明确放弃跨会话连续性需求。

---

### Option D — Hybrid: Persistent Reconstruction + Candidate Snapshot

**设计**：
结合 Option A 和 Option C 的优点。

**核心思想**：
- Reconstruction 持久化，但只保存必要信息
- Candidate 保持现有结构，但引用 Reconstruction
- Reconstruction 是"可检索的语义状态"，不是"完整 Conversation 记录"

**Schema**：
```sql
CREATE TABLE memory_hub.reconstructions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    
    -- 语义快照（压缩表示）
    semantic_summary TEXT NOT NULL,
    decision_type VARCHAR(20),
    confidence FLOAT,
    
    -- 追溯链
    evidence_refs JSONB NOT NULL,
    parent_reconstruction_id UUID,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'active',
    
    -- 关联
    candidate_id UUID UNIQUE REFERENCES memory_hub.candidates(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**关键设计**：
1. `semantic_summary` 是压缩表示，不是完整内容
2. `evidence_refs` 是 Evidence ID 列表，不是 Evidence 内容
3. `candidate_id` 是 UNIQUE 约束，确保 1:1 关系
4. `parent_reconstruction_id` 支持版本链

**Pipeline**：
```
Evidence → EvidenceEvolutionEngine → Reconstruction (保存 semantic_summary)
                                       ↓
                                 Candidate (引用 Reconstruction.id)
                                       ↓
                                 ReflectionEngine
```

**优点**：
1. ✅ 支持跨会话连续性：可以查询"Entity 的 active Reconstruction"
2. ✅ 数据量可控：只保存 summary，不保存完整内容
3. ✅ lineage 清晰：Evidence → Reconstruction → Candidate
4. ✅ 支持人工调试：可以查看 semantic_summary
5. ✅ 符合现有架构：Candidate 表结构不变

**缺点**：
1. ⚠️ 仍需新增表
2. ⚠️ 需定义 semantic_summary 的生成规则

**与 Option A 的区别**：
- Option A: 保存完整 semantic_content
- Option D: 只保存 semantic_summary（压缩）

**结论**：**推荐**。平衡了功能完整性和系统复杂度。

---

## 6. Evidence ↔ Reconstruction ↔ Candidate Lineage

### 6.1 关系定义

**Evidence → Reconstruction**:
- 一个 Evidence 可以属于多个 Reconstruction（语义重叠）
- 一个 Reconstruction 引用多个 Evidence（证据聚合）
- 关系类型：`supports`（通过 memory_evidences 表）

**Reconstruction → Candidate**:
- 一个 Reconstruction 形成一个 Candidate（1:1）
- Candidate 引用 Reconstruction.id（通过 candidate_id 字段）
- 关系类型：`derived_from`（通过 memory_relationships 表）

**Candidate → Proposal**:
- 一个 Candidate 可以产生多个 Proposal（历史记录）
- 但同一时间最多一个 pending Proposal（Phase 20 约束）
- 关系类型：`proposals.candidate_id` FK

### 6.2 Lineage 查询示例

**查询"某 Candidate 的证据链"**：
```sql
SELECT 
    c.id AS candidate_id,
    r.id AS reconstruction_id,
    r.semantic_summary,
    e.id AS evidence_id,
    e.content AS evidence_content
FROM memory_hub.candidates c
JOIN memory_hub.reconstructions r ON c.candidate_id = r.id
JOIN jsonb_array_elements(r.evidence_refs) AS ref ON true
JOIN memory_hub.evidences e ON e.id = ref::uuid
WHERE c.id = :candidate_id;
```

**查询"某 Entity 的 Reconstruction 历史"**：
```sql
SELECT 
    r.id,
    r.semantic_summary,
    r.decision_type,
    r.status,
    r.created_at,
    parent.id AS parent_reconstruction_id
FROM memory_hub.reconstructions r
LEFT JOIN memory_hub.reconstructions parent ON r.parent_reconstruction_id = parent.id
WHERE r.entity_id = :entity_id
ORDER BY r.created_at DESC;
```

### 6.3 Lineage 完整性约束

**约束 1**: Evidence 必须存在
```sql
-- 在 Application Layer 验证
-- Reconstruction.evidence_refs 中的所有 ID 必须存在于 evidences 表
```

**约束 2**: Reconstruction 必须有 Evidence
```sql
CHECK (jsonb_array_length(evidence_refs) >= 1)
```

**约束 3**: Candidate 必须引用 Reconstruction
```sql
-- candidate.candidate_id 必须指向有效的 reconstruction.id
-- （或者反向：reconstruction.candidate_id 必须唯一）
```

---

## 7. Persistence Boundary Analysis

### 7.1 持久化必要性评估

| 需求 | 是否必须持久化 | 理由 |
|------|--------------|------|
| 跨 Conversation 使用 | ✅ 是 | 否则无法找到历史语义状态 |
| 跨 Session 使用 | ✅ 是 | 否则重启后丢失 |
| 几个月后继续 | ✅ 是 | 这是核心需求 |
| 支持 Evolution | ✅ 是 | 需要历史版本 |
| 审计 Evidence lineage | ✅ 是 | Evidence-Based Memory 原则 |
| 重新计算 Candidate | ⚠️ 可选 | 可以重跑 EvidenceEvolutionEngine |
| 保留历史 Reconstruction | ✅ 是 | 支持追溯 |
| 人工调试 | ✅ 是 | 需要查看中间结果 |
| 失败重试 | ✅ 是 | 需要定位问题 |
| 数据量爆炸 | ❌ 否 | 只保存 summary，不保存完整内容 |

**结论**: **必须持久化**，但可以采用压缩表示（Option D）。

### 7.2 持久化内容选择

**Option A（完整保存）**：
```
semantic_content = 完整的第一人称语义状态
```
- 优点：信息完整
- 缺点：数据量大，可能与 Candidate.content 重复

**Option D（压缩保存）**：
```
semantic_summary = 压缩的语义状态（关键信息提取）
```
- 优点：数据量小，聚焦核心信息
- 缺点：可能丢失细节

**推荐**: Option D，但需定义 semantic_summary 的生成规则。

---

## 8. Lifecycle Analysis

### 8.1 Reconstruction 状态机

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
              ┌──────────┐                               │
              │ initial  │◄──────────────────────────────┘
              └────┬─────┘
                   │
                   │ 新 Evidence 到达
                   │ 语义发生变化
                   ▼
              ┌──────────┐     ┌──────────┐
              │  active  │────▶│  updated │◄── 进一步演化
              └────┬─────┘     └────┬─────┘
                   │                │
                   │ Candidate      │ 被新的 Reconstruction
                   │ 创建成功       │ supersede
                   ▼                │
              ┌──────────┐     ┌────▼─────┐
              │superseded│────▶│ archived │
              └──────────┘     └──────────┘
                   │
                   └──→ 保留历史，不删除
```

### 8.2 状态转换规则

| 转换 | 触发条件 | 执行层 |
|------|----------|--------|
| initial → active | EvidenceEvolutionEngine 成功创建 | Engine |
| active → updated | 新 Evidence 到达，语义更新 | Engine |
| updated → superseded | 新的 active Reconstruction 创建 | Engine |
| active/updated → archived | 用户手动归档 | Service |
| any → orphaned | Evidence 失效（可选） | Service |

### 8.3 Reconstruction 与 Candidate 状态同步

| Reconstruction 状态 | Candidate 状态 | 说明 |
|--------------------|---------------|------|
| initial | - | 未形成 Candidate |
| active | candidate | 正常状态 |
| updated | candidate | Candidate 引用新的 Reconstruction |
| superseded | candidate / confirmed | 历史版本保留 |
| archived | archived | 手动归档 |

**关键约束**：
- 一个 Entity 同一时间只能有一个 `active` Reconstruction
- 一个 Reconstruction 只能有一个 `candidate`（1:1）
- `superseded` 的 Reconstruction 保留作为历史

---

## 9. Cross-Conversation Continuity Implications

### 9.1 场景分析

**场景 1**: 同一 Conversation 长期继续
```
Conversation A (Day 1):
  Evidence_1, Evidence_2, Evidence_3
  → Reconstruction_R1 (active)
  → Candidate_C1

Conversation A (Day 30):
  Evidence_4, Evidence_5
  → 找到 R1（通过 Entity + status='active'）
  → Reconstruction_R2 (updated, parent=R1)
  → Candidate_C2
```

**场景 2**: 不同 Conversation 继续同一语义状态
```
Conversation A (Month 1):
  Evidence_1, Evidence_2
  → Reconstruction_R1 (active, Entity=E1)

Conversation B (Month 3):
  Evidence_3, Evidence_4
  → 通过 Entity=E1 找到 R1
  → Reconstruction_R2 (updated, parent=R1)
```

**场景 3**: 旧 Conversation 重新打开
```
Conversation A (Month 1):
  Evidence_1, Evidence_2
  → Reconstruction_R1 (superseded)
  → Candidate_C1 (confirmed)

Conversation A (Month 6, 重新打开):
  Evidence_5, Evidence_6
  → 通过 Entity=E1 + 查询历史 Reconstruction
  → 找到 R1（superseded）
  → 判断是否继续（语义漂移检查）
  → Reconstruction_R3 (active, 可能不是 R1 的直接延续)
```

### 9.2 关键问题

**问题**: "系统凭什么找到 R1？"

**答案（Option D）**：
1. 通过 `entity_id` 关联
2. 通过 `status='active'` 过滤
3. 通过 `semantic_summary` 的 Embedding 相似度辅助

**问题**: "是否真的需要保存完整 Conversation Reconstruction？"

**答案（Option D）**：
- 不需要保存完整内容
- 只需要保存 `semantic_summary`（压缩表示）
- 原始 Evidence 通过 `evidence_refs` 追溯

---

## 10. Repository / Service / Engine Impact

### 10.1 需要新增的组件

| 组件 | 类型 | 职责 |
|------|------|------|
| ReconstructionRepository | Repository | CRUD + 查询 |
| ReconstructionService | Service | 状态转换 + 业务逻辑 |
| ReconstructionEngine（可选） | Engine | 语义摘要生成 |

### 10.2 需要修改的组件

| 组件 | 修改内容 |
|------|----------|
| EvidenceEvolutionEngine | 输出从 Candidate 改为 Reconstruction |
| ReflectionService | 新增 `_save_reconstructions()` 方法 |
| CandidateRepository | 新增 `candidate_id` 字段查询 |

### 10.3 不需要修改的组件

| 组件 | 理由 |
|------|------|
| ReflectionEngine | 输入仍是 Candidate |
| ProposalRepository | 不受影响 |
| MemoryNode | 不受影响 |

---

## 11. Database Impact

### 11.1 新增表

```sql
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
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_reconstruction_evidence_chain CHECK (jsonb_array_length(evidence_refs) > 0)
);
```

### 11.2 新增索引

```sql
CREATE INDEX idx_reconstructions_workspace_id ON memory_hub.reconstructions(workspace_id);
CREATE INDEX idx_reconstructions_entity_id ON memory_hub.reconstructions(entity_id);
CREATE INDEX idx_reconstructions_status ON memory_hub.reconstructions(status);
CREATE INDEX idx_reconstructions_candidate_id ON memory_hub.reconstructions(candidate_id);
CREATE INDEX idx_reconstructions_parent_id ON memory_hub.reconstructions(parent_reconstruction_id);
CREATE INDEX idx_reconstructions_created_at ON memory_hub.reconstructions(created_at DESC);
```

### 11.3 修改现有表

**Candidate 表新增字段**：
```sql
-- 不需要修改，通过 reconstruction.candidate_id 反向引用
-- 或者新增 candidate.reconstruction_id 字段（可选）
```

**Decision**: 不修改 Candidate 表，通过 Reconstruction.candidate_id 维护关系。

---

## 12. Comparison Matrix

| 维度 | Option A | Option B | Option C | Option D |
|------|----------|----------|----------|----------|
| 语义清晰度 | ✅ 高 | ❌ 低 | ✅ 高 | ✅ 高 |
| 跨会话连续性 | ✅ 支持 | ⚠️ 部分 | ❌ 不支持 | ✅ 支持 |
| 数据量 | ⚠️ 大 | ✅ 小 | ✅ 最小 | ✅ 小 |
| 实现复杂度 | ⚠️ 中 | ✅ 低 | ✅ 最低 | ⚠️ 中 |
| 状态管理 | ⚠️ 新增 | ❌ 混乱 | ✅ 无 | ⚠️ 新增 |
| lineage 完整性 | ✅ 完整 | ⚠️ 自引用 | ❌ 断裂 | ✅ 完整 |
| 与现有架构兼容 | ⚠️ 需修改 | ✅ 兼容 | ✅ 兼容 | ⚠️ 需修改 |
| 人工调试支持 | ✅ 支持 | ⚠️ 困难 | ❌ 不支持 | ✅ 支持 |
| 失败重试支持 | ✅ 支持 | ⚠️ 部分 | ❌ 不支持 | ✅ 支持 |
| 符合 Evidence-Based | ✅ 是 | ⚠️ 模糊 | ❌ 否 | ✅ 是 |

---

## 13. Recommended Architecture

### 13.1 推荐方案

**Recommended: Option D — Hybrid: Persistent Reconstruction + Candidate Snapshot**

### 13.2 选择理由

**为什么选 Option D**：
1. ✅ 支持跨会话连续性（核心需求）
2. ✅ 数据量可控（只保存 summary）
3. ✅ lineage 清晰（Evidence → Reconstruction → Candidate）
4. ✅ 符合 Evidence-Based Memory 原则
5. ✅ 支持人工调试和失败重试

**为什么不选 Option A**：
- 数据量大，可能与 Candidate.content 重复
- 需要定义 semantic_content 的完整格式

**为什么不选 Option B**：
- 语义混淆（Candidate 既是草稿又是定稿）
- 状态管理复杂（`candidate` 状态含义不清）
- 违反单一职责原则

**为什么不选 Option C**：
- 无法支持跨会话连续性（核心需求）
- 不符合 Evidence-Based Memory 原则
- 无法支持人工调试

### 13.3 解决什么问题

1. **语义重构缺失**: 提供明确的 Reconstruction 阶段
2. **跨会话连续性**: 支持几个月后继续同一语义状态
3. **User Fact Boundary**: 在 Reconstruction 阶段明确区分用户事实和 AI 建议
4. **Lineage 完整性**: 提供 Evidence → Reconstruction → Candidate 的完整追溯链

### 13.4 引入什么成本

1. **新增表**: `reconstructions` 表
2. **新增状态机**: Reconstruction 有自己的状态管理
3. **代码修改**: EvidenceEvolutionEngine 输出改为 Reconstruction
4. **设计成本**: 需定义 semantic_summary 生成规则

### 13.5 明确留给后续 Stage 的问题

| 问题 | 所属 Stage | 理由 |
|------|-----------|------|
| Topic 定义 | Stage 2.2 | 与 Reconstruction 独立 |
| Context Window | Stage 2.3 | 依赖 Reconstruction 设计 |
| User Fact Boundary 实现 | Stage 2.4 | 依赖 Reconstruction 设计 |
| Historical Memory Evolution | Stage 3 | 属于 Evolution 层 |
| Tag Lifecycle | Deferred | 不属于 Phase 21 |
| Semantic Index | Deferred | 不属于 Phase 21 |

---

## 14. ADR Decision Statement

### 14.1 Decision

**ADR-Phase21-01: Reconstruction Architecture**

**Status**: Proposed

**Context**：
Phase 21 需要引入 Semantic Reconstruction 概念，作为 Evidence → Candidate 之间的中间层。当前架构中 EvidenceEvolutionEngine 直接输出 Candidate，缺少语义重构步骤。这导致：
1. 无法正确处理"用户短回复"场景
2. 无法支持跨会话连续性
3. 无法区分用户事实和 AI 建议

**Decision**：
引入独立的 `reconstructions` 表作为持久化实体，位于 EvidenceEvolutionEngine 和 Candidate 之间。

**Pipeline**：
```
Evidence → EvidenceEvolutionEngine → Reconstruction → Candidate → ReflectionEngine → Proposal
```

**Schema**：
```sql
CREATE TABLE memory_hub.reconstructions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    
    semantic_summary TEXT NOT NULL,
    decision_type VARCHAR(20),
    confidence FLOAT,
    
    evidence_refs JSONB NOT NULL,
    evidence_count INTEGER NOT NULL,
    
    parent_reconstruction_id UUID,
    
    status VARCHAR(20) NOT NULL DEFAULT 'initial',
    candidate_id UUID UNIQUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Consequences**：
- ✅ 支持跨会话连续性
- ✅ 数据量可控（只保存 summary）
- ✅ lineage 完整
- ⚠️ 需新增表和 Repository
- ⚠️ 需修改 EvidenceEvolutionEngine 输出

**References**：
- `D4.2g_EvidenceEvolutionEngine_Architecture.md`
- `phase21-design-consolidation.md`
- Phase 21 Stage 2.1 讨论记录

---

## 15. Deferred Questions

以下问题明确留给后续 Stage 或 Future Phase：

| 问题 | 优先级 | 所属 Stage |
|------|--------|-----------|
| Topic 定义和表结构 | P0 | Stage 2.2 |
| Context Window 机制 | P1 | Stage 2.3 |
| User Fact Boundary 实现 | P1 | Stage 2.4 |
| Semantic Decision 枚举细化 | P2 | Stage 2.2 |
| Reconstruction 与 Tag 关系 | P2 | Deferred |
| Reconstruction 与 Entity 关系细化 | P2 | Stage 2.2 |
| Historical Memory Evolution 机制 | P0 | Stage 3 |
| Embedding 在 Reconstruction Recall 中的应用 | P2 | Deferred |

---

## 附录 A：关键设计决策总结

| 决策项 | 选择 | 理由 |
|--------|------|------|
| Reconstruction 是否持久化 | ✅ 是 | 支持跨会话连续性 |
| 独立表 vs 复用 Candidate | ✅ 独立表 | 语义清晰，职责单一 |
| 保存完整内容 vs 压缩摘要 | ✅ 压缩摘要 | 数据量可控 |
| 与 Candidate 关系 | 1:1 | 每个 Reconstruction 形成一个 Candidate |
| 状态机 | initial → active → updated → superseded | 支持版本链 |
| Lineage 维护 | evidence_refs JSONB | 轻量，可查询 |

---

*本报告为只读调查，不修改任何代码、数据库、Schema、测试或设计文档。*
*Decision Statement 可直接用于 ADR 创建。*

---

**STOP** — 不编码、不提交 Git，等待下一步指示。
