# Phase 21 — Design Consolidation & Architecture Conflict Review

**项目**: Personal Memory Hub  
**阶段**: Phase 21  
**调查日期**: 2026-08-12  
**范围**: 只读调查，不修改任何代码、数据库、Schema、测试或设计文档  

---

## 1. Executive Summary

Phase 21 进入 Design Consolidation 阶段，核心目标是验证 Phase 21 新设计方向与现有 Phase A–D、Phase 20 架构的一致性。

**总体结论**：

1. ✅ **基础架构已就绪**：EvidenceEvolutionEngine / ReflectionEngine 分离、Candidate 表结构、memory_relationships 表均已完成设计
2. ⚠️ **关键 Gap 存在**：Reconstruction、Topic、Conversation 模型均未定义，这是 Phase 21 的核心设计对象
3. ❌ **历史 Memory 共存机制未明确**：虽然 Schema 支持 `superseded` 状态和 `contradicts` 关系，但实际执行路径未定义
4. 🔴 **Phase 20 修复未完全落地**：`proposals.candidate_id` 全部为 NULL，Candidate lifecycle 未运行

---

## 2. Confirmed Design Decisions

### 2.1 Evidence 不可变原则

**来源**：
- `docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md` §5.1
- `docs/02_Data_Model/09_Database_Physical_Design.md` §09.9.1

**设计决策**：
> Observation 永不删除。所有后续认知升级必须基于 Evidence，不基于时间。

**状态**：✅ 已冻结

### 2.2 EvidenceEvolutionEngine ↔ ReflectionEngine 分离

**来源**：
- `docs/05_Implementation/ADR-EvidenceEvolution-Split.md`
- `docs/05_Implementation/D4.2g_EvidenceEvolutionEngine_Architecture.md`
- `docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md` §10.1-10.3

**设计决策**：
```
Stage 1: EvidenceEvolutionEngine (Information Extraction)
  Input: Evidence / MemoryNode
  Output: Candidate

Stage 2: ReflectionEngine (Reasoning)
  Input: Candidate
  Output: Proposal
```

**状态**：✅ 已冻结（D4.2g）

### 2.3 Candidate 是临时工作对象

**来源**：
- `docs/02_Data_Model/09_Database_Physical_Design.md` §09.4.13
- `docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md` §10.2

**设计决策**：
> EvidenceEvolution Engine 产生的 Candidate 必须标记 `status = 'candidate'`。
> Candidate 不进入 vector_documents。
> Candidate 不用于 Context Builder。

**合法状态值**：`candidate`, `confirmed`, `archived`, `orphaned`

**状态**：✅ 已冻结（Schema）

### 2.4 Proposal lineage

**来源**：
- `docs/phase-20-candidate-proposal-lifecycle-design.md`
- `docs/05_Implementation/D4.2d_ReflectionEngine_Architecture_v1.1.md`

**设计决策**：
```sql
ALTER TABLE proposals ADD COLUMN candidate_id UUID REFERENCES candidates(id);
CREATE UNIQUE INDEX idx_proposals_one_pending_per_candidate
ON proposals(workspace_id, candidate_id) WHERE status = 'pending';
```

**状态**：✅ Schema 已添加（Phase 20）  
⚠️ **实现 Gap**：`_save_proposals()` 未填充 `candidate_id`，所有 2,616 条 Proposal 的 `candidate_id` 为 NULL

### 2.5 Memory Evolution 历史共存原则

**来源**：
- `docs/02_Data_Model/09_Database_Physical_Design.md` §09.4.5, §09.4.14
- `docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md` §13

**设计决策**：
```sql
-- memory_nodes.status 支持：active, candidate, deprecated, superseded, orphaned
-- memory_relationships 支持：supports, derived_from, contradicts, attenuates
```

**关键约束**：
```sql
-- 单一活跃信念约束
CREATE UNIQUE INDEX uk_entities_single_active_belief 
ON memory_hub.memory_nodes(entity_id, level) 
WHERE level = 3 AND status = 'active';
```

**状态**：⚠️ Schema 支持历史共存，但执行路径未定义

---

## 3. Existing Design Support

### 3.1 完全支持 Phase 21 的设计

| 设计项 | 来源文档 | 支持程度 |
|--------|----------|----------|
| Evidence 不可变 | 05 §5.1, 09 §09.9.1 | ✅ 完整 |
| EvidenceEvolutionEngine 职责 | ADR, D4.2g | ✅ 完整 |
| ReflectionEngine 职责 | ADR, D4.2d | ✅ 完整 |
| Candidate 表结构 | 09 §09.4.13 | ✅ 完整 |
| memory_relationships 表 | 09 §09.4.14 | ✅ 完整 |
| MemoryNode 状态枚举 | 09 §09.4.5 | ✅ 完整 |
| Evidence Chain 追溯 | 05 §13, 09 §09.4.7 | ✅ 完整 |

### 3.2 部分支持的设计

| 设计项 | 来源文档 | 支持程度 | Gap |
|--------|----------|----------|-----|
| Conversation 处理 | 05 §4.1 | ⚠️ 仅描述输入 | 无 Conversation/Turn/Session 模型 |
| Entity 关联 | 09 §09.4.13 | ⚠️ candidate.entity_id | 无跨 Conversation Entity 关联机制 |
| Tag 体系 | 09 §09.4.10 | ⚠️ 基础表结构 | 无 Tag-to-Tag 关系，无 Tag 传播规则 |
| Semantic Index | 09 §07 | ⚠️ vector_documents | 无 Reconstruction 向量化策略 |
| Historical Memory | 09 §09.4.5, §09.4.14 | ⚠️ Schema 支持 | 无 superseded 转换执行路径 |

### 3.3 未定义的设计

| 设计项 | Phase 21 需求 | 现有设计状态 |
|--------|--------------|-------------|
| **Reconstruction** | 核心概念，语义快照 | ❌ 完全未定义 |
| **Topic** | 语义组织维度 | ❌ 完全未定义 |
| **Conversation Context** | 对话连续性 | ❌ 无 Turn/Session 模型 |
| **Context Window** | 语义窗口 | ❌ 未定义 |
| **Semantic Decision** | EXTEND/REFINE/CHANGE/NEW/UNRELATED/ABSTAIN | ❌ 未定义 |
| **User Fact Boundary** | 区分用户事实 vs AI 建议 | ❌ 无 is_user_generated 字段 |

---

## 4. Design Gaps

### 4.1 Gap 1: Reconstruction 未定义（P0）

**问题描述**：
Phase 21 核心设计是 `Semantic Reconstruction`，但现有文档中没有定义：
- Reconstruction 是什么
- Reconstruction 的数据结构
- Reconstruction 与 Evidence、Candidate 的关系
- Reconstruction 的生命周期

**影响**：
- Candidate Formation 无法定义语义边界
- Context Window 无法实现
- Cross-Conversation Continuity 无法支持

**候选设计方案**：

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | 新增 `reconstructions` 表 | 独立生命周期，清晰边界 | 新增表，需迁移 |
| B | 复用 `candidates` 表作为 Reconstruction | 无需新表 | 语义混淆 |
| C | 不建表，Reconstruction 作为内存对象 | 简单 | 无法持久化，无法追溯 |

**推荐**：方案 A（新增独立表），但需等待设计确认。

---

### 4.2 Gap 2: Topic 未定义（P0）

**问题描述**：
Phase 21 设计 Topic 是"语义组织维度"，不是 Candidate。但现有文档没有定义：
- Topic 的数据结构
- Topic 与 Candidate、Entity 的关系
- Topic 的生命周期

**影响**：
- 无法实现"一个 Topic 可以跨多个 Reconstruction"
- 无法实现"同一 Topic 可以产生多个 Candidate"

**候选设计方案**：

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | 新增 `topics` 表 | 独立生命周期 | 新增表 |
| B | 复用 `tags` 表作为 Topic | 无需新表 | 语义混淆（Tag ≠ Topic） |
| C | Topic 作为 Candidate.metadata 字段 | 简单 | 无法跨 Candidate 共享 |

**推荐**：方案 A，但需明确 Topic vs Tag 的边界。

---

### 4.3 Gap 3: Conversation/Turn/Session 模型缺失（P1）

**问题描述**：
现有设计中：
- `05 §4.1` 描述 "Stage 1: Conversation" 作为 Ingestion 输入
- 但没有定义 Conversation、Turn、Session 的数据库表结构
- 没有定义消息间的顺序关系
- 没有定义"用户短回复"如何关联前文

**影响**：
- 无法实现"对，就这样"的上下文理解
- 无法实现跨消息语义聚合
- Candidate 形成时无法获取对话历史

**候选设计方案**：

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | 新增 `conversations` 和 `turns` 表 | 完整模型 | 新增多表 |
| B | 复用 `evidences.metadata` 存储 conversation_id | 轻量 | 无结构化查询 |
| C | 不定义，依赖导入层传递上下文 | 简单 | 无法追溯 |

**推荐**：方案 B（轻量），但需明确 metadata 字段规范。

---

### 4.4 Gap 4: Evidence 来源标记缺失（P1）

**问题描述**：
Phase 21 要求区分"用户事实"和"AI 建议"，但：
- `evidences` 表没有 `is_user_generated` 字段
- `evidences.source` 只有 `conversation, manual, explicit_command, document, import`
- 无法区分同一条 Evidence 中哪些是用户说的、哪些是 AI 说的

**影响**：
- 无法防止 AI 建议被错误地当成用户事实
- 无法实现"用户确认"语义

**候选设计方案**：

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | 新增 `evidences.is_user_generated` 字段 | 明确 | 修改 Schema |
| B | 使用 `evidences.metadata` 存储原始消息角色 | 轻量 | 查询复杂 |
| C | 在 Ingestion 层拆分 User/Assistant 为独立 Evidence | 清晰 | 数据量翻倍 |

**推荐**：方案 C（拆分），但需评估数据量影响。

---

### 4.5 Gap 5: Semantic Decision 枚举未定义（P2）

**问题描述**：
Phase 21 设计候选决策：
- EXTEND: 继续补充同一语义状态
- REFINE: 同一主题的细化/澄清
- CHANGE: 同一主题但语义状态发生变化
- NEW: 形成新的独立语义主题
- UNRELATED: 与当前 Reconstruction 无关
- ABSTAIN: 信息不足，不可靠判断

现有设计中没有这个枚举。

**影响**：
- Reconstruction 协调逻辑无法实现
- 无法判断"是否属于同一语义状态"

**建议**：此枚举应在 Reconstruction 设计确定后定义。

---

## 5. Code vs Design Conflicts

### 5.1 Conflict 1: Candidate 状态转换代码缺失（P0）

**设计期望**（`phase-20-candidate-proposal-lifecycle-design.md` §4.2）：
```
candidate → confirmed (当 Proposal 被批准)
candidate → archived (当 Candidate 被弃用)
candidate → orphaned (当 Evidence 失效)
```

**代码实际**（`reflection_service.py`）：
- 搜索所有 `UPDATE candidates SET status` → **0 matches**
- 所有 16,505 个 Candidate 永久停留在 `status='candidate'`

**影响**：
- 重复 Evolution（每次重新处理全部 Candidate）
- 无法判断 Candidate 是否已被处理

---

### 5.2 Conflict 2: proposals.candidate_id 全部 NULL（P0）

**设计期望**（`phase-20-candidate-proposal-lifecycle-design.md` §2.2）：
```sql
ALTER TABLE proposals ADD COLUMN candidate_id UUID REFERENCES candidates(id);
```

**代码实际**（`reflection_service.py:_save_proposals()`）：
- INSERT 语句中**未包含** `candidate_id` 字段
- 所有 2,616 条 Proposal 的 `candidate_id` 为 NULL

**影响**：
- Candidate → Proposal lineage 断裂
- 无法追溯 Proposal 来源
- 无法实现"一个 Candidate 最多一个 pending Proposal"约束

---

### 5.3 Conflict 3: 查询条件使用未定义状态（P1）

**代码实际**（`reflection_service.py:1087`）：
```python
AND status IN ('candidate', 'pending')  # 'pending' 不在合法状态中！
```

**设计定义**（`09_Database_Physical_Design.md` §09.4.13）：
```sql
CHECK (status IN ('candidate', 'confirmed', 'archived', 'orphaned'))
```

**问题**：`pending` 不是 Candidate 的合法状态，但代码中使用了。

---

### 5.4 Conflict 4: EvidenceEvolutionEngine 未调用（P1）

**设计期望**（`ADR-EvidenceEvolution-Split.md` §3.1）：
```
Evidence (L1)
    ↓
EvidenceEvolutionEngine.evolve()
    ↓
Candidate (source_level=1)
```

**代码实际**：
- `evidence_evolution_engine.py` 已创建
- 但 `reflection_service.py` 中**未调用** `EvidenceEvolutionEngine.evolve()`
- Candidate 仍然由旧路径创建（直接调用 ReflectionEngine）

**影响**：
- EvidenceEvolutionEngine 分离未生效
- 职责边界未实现

---

## 6. Phase 20 Compatibility Review

### 6.1 已兼容的设计

| Phase 21 设计 | Phase 20 支持 | 兼容性 |
|--------------|--------------|--------|
| Candidate Snapshot | `candidates` 表存在 | ✅ 兼容 |
| Proposal Freeze | `proposals.candidate_id` FK 已添加 | ✅ Schema 兼容（实现 Gap） |
| Candidate → Proposal lineage | Phase 20 已设计 | ✅ 兼容（实现 Gap） |
| pending Proposal deduplication | 部分唯一索引已添加 | ✅ 兼容（实现 Gap） |
| Candidate confirmed/orphaned | 状态枚举已定义 | ✅ 兼容（实现 Gap） |

### 6.2 潜在冲突

| Phase 21 设计 | Phase 20 设计 | 冲突点 |
|--------------|--------------|--------|
| Reconstruction 作为中间层 | Candidate = Evidence Evolution 输出 | ⚠️ 需明确 Reconstruction → Candidate 关系 |
| 跨 Conversation Continuity | Candidate 有 entity_id 但无 conversation_id | ⚠️ 需扩展 Candidate 表或新增字段 |
| Topic 作为语义维度 | 无 Topic 概念 | ⚠️ 需新增 Topic 表或与 Tag 区分 |

### 6.3 结论

Phase 21 设计与 Phase 20 **基本兼容**，但需要：
1. 修复 Phase 20 未落地的实现（candidate_id NULL、lifecycle 未运行）
2. 明确 Reconstruction 与 Candidate 的边界
3. 定义 Topic 与现有 Tag/Entity 的关系

---

## 7. Historical Memory / Evolution Review

### 7.1 当前设计支持情况

**Schema 支持**：
```sql
-- memory_nodes.status 支持历史状态
CHECK (status IN ('active', 'candidate', 'deprecated', 'superseded', 'orphaned'))

-- memory_relationships 支持矛盾关系
CHECK (relationship_type IN ('supports', 'derived_from', 'contradicts', 'attenuates'))
```

**RLS 策略**：
```sql
-- 禁止直接更新/删除 MemoryNode
CREATE POLICY prohibit_update_memory_nodes ON memory_hub.memory_nodes
    FOR UPDATE USING (false);
CREATE POLICY prohibit_delete_memory_nodes ON memory_hub.memory_nodes
    FOR DELETE USING (false);
```

### 7.2 历史共存机制

**设计意图**（`09_Database_Physical_Design.md` §09.9.1）：
> 修正通过追加 CORRECT 记录实现，归档通过标记 status='deprecated' 实现

**但**：
- 没有定义"如何判断新 Memory 应 supersede 旧 Memory"
- 没有定义 `contradicts` 关系的创建时机
- 没有定义 `attenuates` 关系的创建时机
- 单一活跃信念约束（`uk_entities_single_active_belief`）可能导致新 Belief 创建失败

### 7.3 关键问题

**场景**：
```
M1 (L3 Belief): "用户决定使用 PostgreSQL" (status='active', created_at=2026-01-01)
M2 (L3 Belief): "用户重新评估后决定使用 SQLite" (status='active', created_at=2026-08-01)
```

**问题**：
1. M2 创建时，单一活跃信念约束会阻止 M2 成为 `active`
2. 没有定义如何将 M1 标记为 `superseded`
3. 没有定义何时创建 `contradicts` 关系

**结论**：**历史共存机制设计不完整**，属于 Phase 21 或 Future Design Gap。

---

## 8. Reconstruction Architecture Review

### 8.1 现状

**定义缺失**：
- 现有设计中**没有** `Reconstruction` 概念
- `05_MemoryLifecycle_ReflectionEngine.md` 只定义了 `Observation → Pattern → Belief → State` 路径
- 没有定义"语义快照"或"用户视角语义状态"

### 8.2 Phase 21 设计方向

**核心概念**：
```
Local Reconstruction: 理解新增 Evidence 当前表达的语义
Reconciliation: 将 Local Reconstruction 与已有 Reconstruction 进行语义协调
```

**决策枚举**：
- EXTEND, REFINE, CHANGE, NEW, UNRELATED, ABSTAIN

### 8.3 架构选项

| 选项 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | 新增 `reconstructions` 表 | 独立生命周期，清晰边界 | 新增表，需迁移 |
| B | 复用 `candidates` 表 | 无需新表 | 语义混淆（Candidate ≠ Reconstruction） |
| C | Reconstruction 作为内存对象 | 简单 | 无法持久化，无法追溯 |
| D | 将 Reconstruction 嵌入 Candidate.metadata | 轻量 | 查询复杂，边界模糊 |

**推荐**：选项 A（新增独立表），但需要明确：
1. Reconstruction 与 Candidate 的关系（1:1? 1:N?）
2. Reconstruction 的生命周期（是否独立于 Candidate？）
3. Reconstruction 是否进入 vector_documents？

---

## 9. Candidate Formation Review

### 9.1 当前形成机制

**入口**：`reflection_service.py:_save_candidates()`

**输入**：Evidence 列表（通过 evidence_chain 引用）

**输出**：Candidate（status='candidate', type='pattern'）

**问题**：
1. 每个 Evidence 独立形成 Candidate（1:1）
2. 没有 Conversation Context
3. 没有语义聚合
4. 没有"用户短回复"处理

### 9.2 Phase 21 目标

**Semantic Completeness**：
> 能够脱离当前 Conversation 后，用用户第一人称表达一个相对完整、可独立判断的语义命题。

**Semantic Independence**：
> Candidate 不应依赖当前 Conversation 的上下文才能理解。

**当前支持度**：❌ 不支持

### 9.3 形成阈值

**设计决策**（Phase 21）：
> "是否值得长期记忆"不是 Candidate Formation 的职责，而属于 Proposal 阶段。

**当前代码**：
- Candidate 创建时无阈值检查
- 所有 Evidence 都形成 Candidate
- 导致 16,505 个 Candidate（其中大量是噪音）

**结论**：需要定义 Candidate Formation Threshold。

---

## 10. Tag / Entity / Semantic Index Review

### 10.1 Tag 体系

**现有设计**（`09_Database_Physical_Design.md` §09.4.10）：
```sql
tags.tag_type CHECK (tag_type IN ('system', 'ai', 'user'))
tag_links.target_type CHECK (target_type IN ('entity', 'memory_node', 'archive'))
```

**Phase 21 方向**：
- Tag 是开放式语义索引，不是事实
- Tag 可以辅助 Context Discovery、Reconstruction Recall
- Tag 不应该单独决定 Semantic Continuity

**Gap**：
- 无 Tag-to-Tag 关系
- 无 Tag 传播规则
- 无 Explicit/Derived/Inherited 来源标记

### 10.2 Entity 体系

**现有设计**：
- `entities` 表支持 12 种 entity_type
- `parent_entity_id` 支持层级关系
- `aliases` 支持别名

**Phase 21 方向**：
- Entity 与 Tag 必须保持独立
- X/Twitter 应作为 Entity identity/alias，不是两个 Tag

**兼容性**：✅ 现有设计支持

### 10.3 Semantic Index

**现有设计**（`09_Database_Physical_Design.md` §07）：
- `vector_documents` 存储 embedding
- `importance_score` 用于排序
- 仅 L2/L3/L4 向量化

**Phase 21 方向**：
- Embedding 主要用于 Recall，不用于证明事实
- 重点索引对象：Reconstruction、Candidate
- Recall 综合多种信号：Conversation continuity、Explicit reference、Tag、Entity、Embedding、Temporal proximity

**Gap**：
- 无 Reconstruction 向量化策略
- 无多信号融合检索设计

---

## 11. Cross-Conversation Continuity Review

### 11.1 当前设计

**证据**：
- `evidences.metadata` 可能包含 `conversation_id`
- `candidates` 表无 `conversation_id` 字段
- `memory_nodes` 表无 `conversation_id` 字段

**结论**：当前设计**不支持**跨 Conversation 连续性。

### 11.2 Phase 21 需求

**必须支持**：
- 同一 Conversation 长期继续
- 旧 Conversation 几个月后重新打开
- 新 Conversation 继续同一领域
- 不同 Conversation 属于同一个长期项目
- 一个长期项目同时存在多个独立 Reconstruction

**设计决策**：
> Conversation ID 只能作为 Recall Signal，不能直接证明 Semantic Continuity。

### 11.3 实现选项

| 选项 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A | 新增 `conversation_groups` 表 | 显式分组 | 新增表 |
| B | 使用 Entity 作为连续性锚点 | 复用现有 | 语义不够精确 |
| C | 使用 Tag 作为连续性锚点 | 灵活 | 依赖 Tag 质量 |
| D | 使用 Embedding similarity | 自动化 | 不准确 |

**推荐**：组合方案（B + C + D），但需明确优先级。

---

## 12. Required ADRs / Architecture Updates

### 12.1 必须新建的 ADR

| ADR | 主题 | 理由 |
|-----|------|------|
| ADR-Phase21-01 | Reconstruction 架构 | 新概念，需正式记录 |
| ADR-Phase21-02 | Topic 定义 | 与 Tag/Entity 区分 |
| ADR-Phase21-03 | Historical Memory Evolution | superseded 转换机制 |

### 12.2 必须更新的设计文档

| 文档 | 更新内容 |
|------|----------|
| `05_MemoryLifecycle_ReflectionEngine.md` | 新增 Reconstruction 阶段 |
| `09_Database_Physical_Design.md` | 新增 reconstructions、topics 表 |
| `D4.2g_EvidenceEvolutionEngine_Architecture.md` | 明确与 Reconstruction 的关系 |
| `phase-20-candidate-proposal-lifecycle-design.md` | 补充 Proposal Freeze 设计 |

---

## 13. Deferred Design Gaps

以下 Gap 不属于 Phase 21 范围，应延后处理：

| Gap | 理由 | 建议阶段 |
|-----|------|----------|
| proposals.candidate_id NULL 修复 | Phase 20 遗留问题 | Phase 20 Fix |
| Candidate lifecycle 运行 | Phase 20 遗留问题 | Phase 20 Fix |
| Evidence API /evidences?id | 非 Phase 21 范围 | 独立任务 |
| 800 个 Orphan MemoryNodes | 数据质量问题 | 独立任务 |
| Scheduler startup compensation | 运维问题 | 独立任务 |
| Multi-source Fact lineage | 复杂设计问题 | Future Phase |

---

## 14. Phase 21 Design Boundary

### 14.1 Phase 21 范围

**必须设计**：
1. Reconstruction 实体/表结构
2. Topic 实体/表结构
3. Reconstruction Formation 算法（EXTEND/REFINE/CHANGE/NEW/UNRELATED/ABSTAIN）
4. Context Window 机制
5. Cross-Conversation Continuity 策略
6. User Fact Boundary 实现

**不包括**：
1. Phase 20 遗留问题修复
2. Evidence API 修复
3. Orphan MemoryNodes 清理
4. Scheduler 问题

### 14.2 与 Phase 20 的边界

| 问题 | Phase 20 | Phase 21 |
|------|----------|----------|
| Candidate 表结构 | ✅ 已定义 | 复用 |
| Proposal lineage | ✅ Schema 已添加 | 复用 |
| Reconstruction | ❌ 未定义 | ** Phase 21 定义** |
| Topic | ❌ 未定义 | ** Phase 21 定义** |
| Historical Evolution | ⚠️ Schema 支持 | ** Phase 21 明确机制** |

---

## 15. Recommended Next Phase

### 15.1 当前状态

**已完成**：
- ✅ Phase 21 Stage 1（只读调查）
- ✅ Phase 21 Stage 1.5（Design Heritage 调查）
- ✅ Phase 21 Design Consolidation（本报告）

**待完成**：
- ⏳ Phase 21 Stage 2（Design Decision）
- ⏳ Phase 21 Stage 3（Regression Test Design）
- ⏳ Phase 21 Stage 4（Implementation）

### 15.2 进入 Regression Test Design 的条件

**必须解决**：
1. Reconstruction 架构决策（ADR-Phase21-01）
2. Topic 定义决策（ADR-Phase21-02）
3. Historical Memory Evolution 机制决策

**可以延后**：
1. Phase 20 遗留问题修复（不影响 Phase 21 设计）
2. Tag 传播规则（不影响核心流程）

### 15.3 推荐下一步

**立即执行**：
1. 召开 Phase 21 Design Decision 会议
2. 确认 Reconstruction 架构（新增表 vs 复用）
3. 确认 Topic 与 Tag 的边界
4. 确认 Historical Memory Evolution 执行路径

**暂缓执行**：
1. Phase 20 candidate_id NULL 修复（先完成 Phase 21 设计）
2. Candidate lifecycle 运行（先完成 Phase 21 设计）

---

## 附录 A：文档引用清单

| 文档 | 路径 | 关键章节 |
|------|------|----------|
| Memory Hub Foundation | `docs/00_Overview/01_MemoryHub_Foundation.md` | §3-§5 |
| Schema/Archive/Reflect | `docs/03_Memory_System/04_Schema_Archive_Reflect.md` | §4-§5 |
| Memory Lifecycle | `docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md` | §4-§13 |
| Database Physical Design | `docs/02_Data_Model/09_Database_Physical_Design.md` | §09.4.5, §09.4.13-14 |
| EvidenceEvolution Split ADR | `docs/05_Implementation/ADR-EvidenceEvolution-Split.md` | §3-§4 |
| EvidenceEvolutionEngine Arch | `docs/05_Implementation/D4.2g_EvidenceEvolutionEngine_Architecture.md` | §1-§5 |
| ReflectionEngine Arch | `docs/05_Implementation/D4.2d_ReflectionEngine_Architecture_v1.1.md` | §2-§5 |
| Phase 20 Candidate Lifecycle | `docs/phase-20-candidate-proposal-lifecycle-design.md` | §2-§6 |
| Phase 20 Lifecycle Analysis | `docs/phase-20-candidate-lifecycle-analysis.md` | §1-§6 |

---

## 附录 B：数据统计

| 实体 | 数量 | 状态分布 |
|------|------|----------|
| Candidates | 16,505 | candidate: 16,505 (100%) |
| Evidences | 15,662 | - |
| Proposals | 2,616 | candidate_id NULL: 2,616 (100%) |
| MemoryNodes | 25,203 | active: ~?, superseded: 0 |

---

*本报告为只读调查，不修改任何代码、数据库、Schema、测试或设计文档。*
*发现的所有 Gap 和冲突已记录，等待用户指示下一步行动。*

---

**STOP** — 不编码、不提交 Git，等待下一步指示。
