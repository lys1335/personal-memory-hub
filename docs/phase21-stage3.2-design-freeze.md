# Phase 21 Stage 3.2 — Design Freeze & Implementation Plan

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 3.2  
**调查日期**: 2026-08-13  
**状态**: 🟡 DESIGN FROZEN WITH DEFERRED GAPS  
**范围**: 只读调查，不修改任何代码、数据库、Schema、测试或设计文档  

---

## 1. Design Sources Reviewed

### 已审查的设计文档

| 文档 | 阶段 | 审查状态 |
|------|------|----------|
| `docs/phase21-design-consolidation.md` | Stage 1 Consolidation | ✅ 已审查 |
| `docs/phase21-stage2.1-reconstruction-architecture.md` | Stage 2.1 Reconstruction | ✅ 已审查 |
| `docs/phase21-stage2.1a-reconstruction-relationship-validation.md` | Stage 2.1A Relationship Validation | ✅ 已审查 |
| `docs/phase21-stage2.2-topic-definition.md` | Stage 2.2 Topic | ✅ 已审查 |
| `docs/phase21-stage2.3-context-window-definition.md` | Stage 2.3 Context Window | ✅ 已审查 |
| `docs/phase21-stage2.4-user-fact-boundary.md` | Stage 2.4 User Fact Boundary | ✅ 已审查 |
| `docs/phase21-stage3-regression-test-design.md` | Stage 3 Regression Test Design | ✅ 已审查 |
| `docs/phase21-stage3.1-phase20-final-verification.md` | Phase 20 Baseline | ✅ 已确认 |

### Phase 20 Baseline 确认

**Commit**: `6cf2ebb` — `fix: persist proposal.candidate_id for Phase 20 lineage`

**已验证**:
- ✅ Migration 002 已应用（candidate_id UUID, FK, partial unique index）
- ✅ Phase 20 Regression Tests: 14/14 PASS
- ✅ Real Pipeline E2E: 5 新 Proposal 正确写入 candidate_id
- ✅ Historical Data: 2717 NULL 保持原状

---

## 2. Final Pipeline Confirmation

### 确认的最终架构

```
Evidence (Immutable, L0)
    ↓
Context Window (Temporary, Semantic Expansion)
    ↓
Reconstruction (Persistent, Versioned, L1)
    ↓ 1:1
Candidate (Fixed Snapshot, Work Object)
    ↓ 1:N
Proposal (Decision Object)
    ↓
Memory Evolution → MemoryNode (L1/L2/L3+)
```

### 关键约束确认

| 层级 | 实体 | 约束 | Schema 状态 |
|------|------|------|-------------|
| L0 | Evidence | Immutable, no role field | ✅ 现有 |
| Context | Context Window | Temporary, not persisted | ⏸️ 未实现 |
| L1 | Reconstruction | Persistent, semantic_summary, evidence_refs | ❌ 需新建表 |
| L1.5 | Candidate | 1:1 with Reconstruction, fixed snapshot | ✅ 现有 |
| L2 | Proposal | candidate_id FK, lifecycle pending→approved/rejected | ✅ 已修复 |
| L3+ | MemoryNode | Level 1/2/3, status active/superseded/etc | ✅ 现有 |

---

## 3. Reconstruction Freeze

### 3.1 为什么需要 Reconstruction

**设计决策**: ✅ 已确认

1. **用户短回复需要上下文**: "对，就这样" 必须理解前文
2. **Conversation 可能偏离主题**: Topic drift 需要语义连续性
3. **跨 Conversation 语义连续性**: 同一长期语义状态需要重建
4. **版本链支持迭代理解**: 同一 Entity 的多轮对话需要版本管理

### 3.2 Reconstruction 职责

| 职责 | 状态 | 说明 |
|------|------|------|
| 语义重构 | ✅ | 从 Evidence 序列中提取用户语义 |
| 版本管理 | ✅ | parent_reconstruction_id 形成版本链 |
| 语义摘要 | ✅ | semantic_summary 保存压缩后的语义 |
| 证据引用 | ✅ | evidence_refs 指向来源 Evidence |
| 置信度评估 | ✅ | confidence 评估语义确定性 |
| 决策类型 | ✅ | decision_type: direct/confirmed/rejected/corrected/selected |

### 3.3 Schema 设计确认

**需新增表**: `reconstructions`

```sql
CREATE TABLE reconstructions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    
    -- 语义内容
    semantic_summary TEXT NOT NULL,
    decision_type VARCHAR(50),
    
    -- 证据链
    evidence_refs JSONB NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0,
    
    -- 置信度
    confidence FLOAT NOT NULL DEFAULT 0.0,
    
    -- 版本链
    parent_reconstruction_id UUID REFERENCES reconstructions(id),
    
    -- 生命周期
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN (
        'active', 'superseded', 'archived'
    )),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_reconstruction_has_evidence CHECK (jsonb_array_length(evidence_refs) > 0)
);

-- 唯一约束：每个 Candidate 只有一个活跃 Reconstruction
CREATE UNIQUE INDEX uk_reconstructions_one_active_per_candidate 
ON reconstructions(candidate_id) WHERE status = 'active';
```

**⚠️ 当前状态**: 数据库**没有** `reconstructions` 表，需要 Migration。

### 3.4 版本链确认

```
R1 (active) → C1
  ↓ superseded
R2 (parent=R1, active) → C2
  ↓ superseded
R3 (parent=R2, active) → C3
```

**关键保证**:
- R2 创建时 R1 变为 superseded
- C1 保持历史快照，不被修改
- Proposal(C1) 的 candidate_id 不会自动转移到 C2

---

## 4. Topic Freeze

### 4.1 Topic 定义确认

**设计决策**: ✅ 已确认

- Topic ≠ Tag（Tag 是轻量标签，Topic 是长期语义组织）
- Topic ≠ Entity（Entity 是具体对象，Topic 是语义维度）
- Topic 支持层级结构（parent_topic_id）

### 4.2 Schema 设计确认

**需新增表**: `topics`, `topic_links`

```sql
CREATE TABLE topics (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    parent_topic_id UUID REFERENCES topics(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE topic_links (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    topic_id UUID NOT NULL REFERENCES topics(id),
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('reconstruction', 'candidate', 'entity')),
    target_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX uk_topic_links_target 
ON topic_links(topic_id, target_type, target_id);
```

### 4.3 N:M 关系确认

```
Reconstruction R1
    ↓
topic_links (N)
    ↓
Topics T1, T2, T3
```

---

## 5. Context Window Freeze

### 5.1 Context Window 定义确认

**设计决策**: ✅ 已确认

```
Context Window = 
    Reconstruction Recall (向前查找相关 Reconstruction)
    +
    Semantic Expansion (扩展搜索相关 Evidence)
    +
    Topic Filtering (按 Topic 过滤)
    +
    Budget Control (Token 预算控制: 默认 4000, 硬上限 8000)
```

### 5.2 关键规则确认

| 规则 | 状态 |
|------|------|
| Context Window 不持久化 | ✅ |
| AI Evidence 可进入 Context | ✅ |
| AI Evidence 不可直接成为 Candidate | ✅ |
| 短回复向前扩展 | ✅ |
| Topic Drift 有边界 | ✅ |
| 跨 Conversation Recall | ✅ |

---

## 6. User Fact Boundary Freeze

### 6.1 User-owned Semantic 定义确认

**设计决策**: ✅ 已确认

**包括**:
- direct statement, confirmation, rejection, correction
- selection, preference, decision, intention
- belief, constraint

**严格禁止**:
- pure AI statement
- AI recommendation
- hypothetical
- third-party statement
- roleplay
- ambiguous standalone response

### 6.2 AI + User Confirmation 规则

| 场景 | 结果 |
|------|------|
| AI 建议 + 用户确认 | → User Fact ✅ |
| AI 建议 + 用户否定 | → 否定状态的 User Fact ✅ |
| AI 建议 + 用户未确认 | → 不形成 Candidate ❌ |
| 纯 AI 陈述 | → 不形成 Candidate ❌ |

---

## 7. Evidence Role 前提

### 7.1 当前 Schema 状态

**evidences 表字段**:
```
id, workspace_id, entity_id, area_id, user_id,
evidence_type, content, raw_content,
confidence, importance, signal_strength,
source, _meta, created_at, updated_at
```

**缺失字段**:
- ❌ role（无法区分 user/assistant）
- ❌ parent_evidence_id
- ❌ sequence
- ❌ conversation_id

### 7.2 设计确认

**推荐方案**: 在 `_meta` JSONB 中存储 role

```python
metadata = {
    "role": "user",  # 或 "assistant", "system"
    "conversation_id": "...",
    "message_id": "...",
    "sequence": 1
}
```

### 7.3 导入逻辑确认

**需修改**:
- [ ] `chatgpt.py`: 保留 Assistant messages
- [ ] `open_webui.py`: 保留 Assistant messages

---

## 8. Historical Memory Evolution

### 8.1 设计确认

**核心原则**: ✅ 已确认

```
旧 Candidate (C1)
    ↓ 新 User Fact 出现
旧 Candidate 保持历史状态（不被修改）
    ↓
新 Reconstruction (R2)
    ↓
新 Candidate (C2)
    ↓
Memory Relationship
    - superseded: C1 → C2
    - contradicts: C1 ↔ C2
```

### 8.2 Schema 支持确认

**memory_nodes.status**: `active, candidate, deprecated, superseded, orphaned` ✅

**memory_relationships.type**: `supports, derived_from, contradicts, attenuates` ✅

### 8.3 ⚠️ 发现 Gap

**Historical Memory Evolution 的具体执行路径未定义**:
- Schema 支持 superseded 状态和 contradicts 关系
- **但未定义**: 何时触发 Evolution？如何判断应 supersede 还是 contradict？

**建议**: Deferred to Phase 21.7

---

## 9. Tag / Topic / Entity Boundary

### 9.1 三层架构确认

| 层级 | 实体 | 用途 | 示例 |
|------|------|------|------|
| Entity | 具体对象 | 语义锚点 | "Personal Memory Hub 项目" |
| Topic | 语义维度 | 长期组织 | "开发工具选择" |
| Tag | 轻量标签 | 灵活分类 | "#postgres", "#docker" |

### 9.2 边界确认

- Topic 是长期语义组织（持久化）
- Tag 是轻量标签（可动态添加删除）
- Entity 是具体对象（如项目、工具）

---

## 10. Schema Compatibility

### 10.1 现有 Schema 审查

**已确认兼容**:
- ✅ candidates 表有 evidence_chain, entity_id 字段
- ✅ proposals 表有 candidate_id FK（Phase 20 已修复）
- ✅ memory_nodes 表有 parent_node_id, status 字段
- ✅ memory_relationships 表支持多种关系类型
- ✅ evidences 表有 _meta JSONB 可存 role

### 10.2 需新增 Schema

| 表名 | 用途 | 依赖 |
|------|------|------|
| reconstructions | 语义重构持久化 | entities, workspaces |
| topics | 长期语义组织 | workspaces |
| topic_links | Reconstruction-Topic 关联 | topics, reconstructions, candidates, entities |

---

## 11. Engine / Service Boundary

### 11.1 现有职责确认

| 组件 | 职责 | Phase 21 变更 |
|------|------|---------------|
| EvidenceEvolutionEngine | Evidence → Candidate | 增加 Reconstruction 中间层 |
| ReflectionEngine | Candidate → Proposal | 不变 |
| ReflectionService | Orchestration | 增加 Reconstruction 调用 |
| Repository Layer | Data Access | 新增 ReconstructionRepository |

### 11.2 Phase 21 职责调整

**新 Pipeline**:
```
EvidenceEvolutionEngine
    ↓ Evidence
ContextWindowService (NEW)
    ↓ Context Evidence
ReconstructionEngine (NEW)
    ↓ Reconstruction
ReflectionEngine
    ↓ Proposal
Candidate → Memory Evolution
```

---

## 12. Regression Alignment

### 12.1 测试数量统计

| 优先级 | 数量 | 覆盖范围 |
|--------|------|----------|
| **P0** | 30 | Core functionality, must pass |
| **P1** | 20 | Important features |
| **P2** | 5 | Enhanced coverage |
| **Total** | 55 | |

### 12.2 Phase 20 Baseline

**已确认**: 14/14 PASS (test_phase20_regression.py)

---

## 13. Implementation Order

### 13.1 推荐实施顺序

```
Phase 21.1: Evidence role + Assistant Evidence preservation
    ↓
Phase 21.2: Reconstruction persistence/schema/repository
    ↓
Phase 21.3: Context Window
    ↓
Phase 21.4: User-centric semantic interpretation
    ↓
Phase 21.5: Reconstruction → Candidate formation
    ↓
Phase 21.6: Topic / topic_links
    ↓
Phase 21.7: Historical Memory Evolution
    ↓
Phase 21.8: Phase 21 Integration / E2E
```

### 13.2 各阶段详细说明

#### Phase 21.1: Evidence Role
- 目标: 在 _meta 中存储 role
- 修改: chatgpt.py, open_webui.py
- 测试: test_evidence_role_regression.py

#### Phase 21.2: Reconstruction
- 目标: 创建 reconstructions 表
- 修改: migration, models, repository
- 测试: test_reconstruction_lineage.py

#### Phase 21.3: Context Window
- 目标: 实现 Context Window 服务
- 修改: service 层
- 测试: test_context_window_regression.py

#### Phase 21.4: User Fact Boundary
- 目标: 实现 User Fact 判断逻辑
- 修改: engine 层
- 测试: test_user_fact_boundary.py

#### Phase 21.5: Reconstruction → Candidate
- 目标: 完成 Formation pipeline
- 修改: service 层 orchestration
- 测试: test_e2e_scenarios.py

#### Phase 21.6: Topic
- 目标: 创建 topics/topic_links 表
- 修改: migration, models, repository
- 测试: test_topic_regression.py

#### Phase 21.7: Historical Memory Evolution
- 目标: 实现 Evolution 算法
- 修改: engine 层
- 测试: test_temporal_semantics.py

#### Phase 21.8: Integration
- 目标: 完整 E2E 测试
- 修改: 无
- 测试: test_e2e_scenarios.py

---

## 14. Phase 21 Scope Boundary

### 14.1 Phase 21 做什么

- ✅ Evidence role 字段（通过 _meta）
- ✅ Assistant Evidence 保留
- ✅ Reconstruction 持久化
- ✅ Context Window 实现
- ✅ User Fact Boundary 判断
- ✅ Topic / topic_links
- ✅ Historical Memory Evolution 算法

### 14.2 Phase 21 不做什么（Deferred）

- ❌ Evidence API bug 修复
- ❌ 800 orphan MemoryNodes 清理
- ❌ Scheduler compensation/cooldown
- ❌ PYC deployment reliability
- ❌ Multi-source Fact lineage
- ❌ Topic clustering algorithm
- ❌ Semantic Index
- ❌ Evidence API 重构

---

## 15. Deferred Design Gaps

### 15.1 P0 Gaps

| Gap | 影响 | 建议 |
|-----|------|------|
| Evidence.role 字段 | 无法区分 user/assistant | 使用 _meta 存储 |
| 导入逻辑过滤 AI Evidence | Context Window 无法获得 AI 上下文 | 修改 chatgpt.py, open_webui.py |
| Historical Memory Evolution 算法 | 无法自动建立 superseded/contradicts 关系 | Phase 21.7 实现 |

### 15.2 P1 Gaps

| Gap | 影响 | 建议 |
|-----|------|------|
| Evidence.parent_evidence_id | 无法表达消息父子关系 | Phase 21.1 考虑 |
| Context Window budget 精确数值 | 默认 4000/8000 tokens 需调优 | Phase 21.3 实现后调优 |
| Topic clustering algorithm | 无法自动发现 Topic | Deferred |

### 15.3 P2 Gaps

| Gap | 影响 | 建议 |
|-----|------|------|
| Ambiguity Resolution | 模糊确认的处理策略 | Deferred |
| Long Evidence Chunking | 超长 Evidence 的处理 | Deferred |
| User Fact Classification | 语义分类算法 | Phase 21.4 实现 |

---

## 16. Final Freeze Decision

### 评估结果

| 检查项 | 状态 |
|--------|------|
| Stage 2.1–2.4 设计一致性 | ✅ 一致 |
| Phase 20 baseline 可用性 | ✅ 14/14 PASS |
| Schema 兼容性 | ✅ 兼容 |
| Engine/Service 边界清晰 | ✅ 清晰 |
| Regression Test 覆盖 | ✅ 55 tests 规划 |
| Implementation Order | ✅ 明确 |

### 🟡 FINAL DECISION

**PHASE 21 DESIGN FROZEN WITH DEFERRED GAPS**

### 冻结的设计

1. ✅ Reconstruction 架构（Stage 2.1）
2. ✅ Reconstruction 关系模型（Stage 2.1A）
3. ✅ Topic 定义（Stage 2.2）
4. ✅ Context Window 定义（Stage 2.3）
5. ✅ User Fact Boundary（Stage 2.4）
6. ✅ Regression Test Design（Stage 3）

### 允许 Deferred 的 Gap

1. ⏸️ Evidence.role 实现方案（使用 _meta）
2. ⏸️ Historical Memory Evolution 算法
3. ⏸️ Topic clustering algorithm
4. ⏸️ Context Window budget 精确数值

---

## 17. Next Steps

### 立即可执行

```bash
# 1. 确认 Phase 21.1 开始
# 2. 创建 Migration 003: Add reconstructions table
# 3. 创建 Migration 004: Add topics and topic_links tables
# 4. 修改 chatgpt.py 和 open_webui.py 保留 AI Evidence
# 5. 实现 Reconstruction 核心逻辑
```

---

**STOP** — 等待用户确认后开始 Phase 21 Implementation。
