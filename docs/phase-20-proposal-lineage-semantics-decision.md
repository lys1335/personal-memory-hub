# Phase 20 — Proposal Lineage Semantics Boundary Decision

## 执行摘要

🚨 **发现新的 P0 Design Gap**

设计文档已明确规定：
> **Proposal 必须属于单一 Candidate（1:N 关系）**

但当前 EvidenceEvolutionEngine 的 Entity Grouping 逻辑会**跨 Candidate 合并 Facts**，违反设计约束。

---

## 一、设计文档确认

### 1.1 Cardinality 设计

**来源**: `phase-20-candidate-proposal-lifecycle-design.md:148`

```markdown
**推荐**: Candidate 1 : N Proposal（历史），但 Candidate 1 : 1 Pending Proposal（同时）

Candidate A
    ├── Proposal #1 (pending)     ← 当前生效
    ├── Proposal #2 (approved)    ← 历史（已创建 MemoryNode）
    ├── Proposal #3 (rejected)    ← 历史
    └── Proposal #4 (rejected)    ← 历史
```

### 1.2 关键原则

```markdown
1. Pending Proposal 是 Candidate 的"锁"
   - 防止重复 Evolution
   - 等待人类或自动审批

2. Approved 后 Candidate 完成使命
   - 转为 confirmed
   - 不再进入 Evolution Scope

3. Rejected 后 Candidate 终止
   - 转为 orphaned
   - 标记为"尝试失败"
```

### 1.3 设计意图

**Proposal 的业务语义**：
- ✅ Proposal 是**针对单一 Candidate 的演化提案**
- ❌ Proposal **不是跨 Candidate 的综合分析结果**
- ⚠️ 一个 Candidate 可以产生多个 Proposal（历史），但**同时只有一个 Pending**

---

## 二、当前实现问题

### 2.1 EvidenceEvolutionEngine 的 Entity Grouping

```python
# evidence_evolution_engine.py:338-344
entity_facts: dict[str, list[dict[str, Any]]] = {}
for fact in facts:
    entity = fact.get("entity", "unknown")
    if entity not in entity_facts:
        entity_facts[entity] = []
    entity_facts[entity].append(fact)
```

**问题**：按 entity 分组，不保留 Candidate 边界。

### 2.2 数据流中的信息丢失

```
Candidate A (id=cand-A) ─┐
                          ├──→ Evidence A ──┐
Candidate B (id=cand-B) ─┘                  ├──→ LLM Extraction
Candidate C (id=cand-C) ─┐                  │
                          └──→ Evidence B ──┘
                                              ↓
                                          facts = [
                                            {entity: 'X', source_ids: ['ev-A', 'ev-B']},
                                            {entity: 'Y', source_ids: ['ev-B', 'ev-C']}
                                          ]
                                              ↓
                                          entity_facts = {
                                            'X': [fact1],  # 来自 A+B
                                            'Y': [fact2]   # 来自 B+C
                                          }
                                              ↓
                                          _build_candidates()
                                          # 尝试通过 index 恢复 candidate_id → 失败！
```

### 2.3 具体失败场景

| 场景 | 结果 | 是否符合设计 |
|------|------|-------------|
| A + B → 同一 Entity X | 合并为一个 Proposal，candidate_id 错误 | ❌ 违反 1:1 约束 |
| A → Entity X, A → Entity Y | 两个 Proposal 都关联到 A | ✅ 符合设计 |
| A → Entity X, B → Entity Y | 两个 Proposal 分别关联 A, B | ⚠️ 碰巧正确（依赖顺序） |
| A, B, C → 同一 Entity X | 一个 Proposal，candidate_id 随机选一个 | ❌ 违反设计 |

---

## 三、根本原因分析

### 3.1 设计 Gap

| Gap ID | 描述 | 严重程度 |
|--------|------|----------|
| **DG-001** | Evidence → Fact 阶段丢失 Candidate 来源信息 | **P0** |
| **DG-002** | Entity Grouping 不保留 Candidate 边界 | **P0** |
| **DG-003** | _build_candidates() 尝试用 index 恢复丢失的信息 | **P0** |

### 3.2 为什么 Index Mapping 不可行

```
原因 1: dict.items() 顺序不确定
  - Python 3.7+ 保持插入顺序，但插入顺序取决于 LLM 输出
  - 不保证与 candidate_ids 顺序一致

原因 2: 多对一映射（多个 Candidate → 同一 Entity）
  - entity_facts 数量 < candidate_ids 数量
  - 部分 Candidate 丢失

原因 3: 一对多映射（一个 Candidate → 多个 Entity）
  - entity_facts 数量 > candidate_ids 数量
  - IndexError 或错误关联

原因 4: Candidate 可能被过滤
  - 无有效 facts 的 Candidate 被跳过
  - 后续 index 偏移
```

---

## 四、正确设计方案

### 方案 A: Evidence 携带 Candidate ID（推荐）

**原理**：在 evidence dict 中保留原始 candidate_id，通过 source_ids 传递到 fact

#### 4.1 修改点

```python
# 1. EvidenceEvolutionEngine.evolve()
async def evolve(self, *, evidence, provider, candidate_ids=None):
    # 将 candidate_id 注入到每个 evidence dict
    enriched_evidence = []
    if candidate_ids:
        for i, ev in enumerate(evidence):
            ev_copy = ev.copy()
            ev_copy['candidate_id'] = candidate_ids[i] if i < len(candidate_ids) else None
            enriched_evidence.append(ev_copy)
    else:
        enriched_evidence = evidence
    
    facts, fact_log = await self._extract_facts(enriched_evidence, provider)
```

```python
# 2. EvidenceEvolutionEngine._extract_facts()
async def _extract_facts(self, evidence, provider):
    # 建立 evidence_id → candidate_id 映射
    evidence_candidate_map = {}
    for e in evidence:
        eid = e.get('id')
        cid = e.get('candidate_id')
        if eid and cid:
            evidence_candidate_map[eid] = cid
    
    # ... 原有 LLM 提取逻辑 ...
    
    # 将 candidate_id 注入到 fact 的 metadata
    for fact in facts:
        for sid in fact.get('source_ids', []):
            if sid in evidence_candidate_map:
                fact['candidate_id'] = evidence_candidate_map[sid]
                break  # 只取第一个匹配的 candidate_id
```

```python
# 3. EvidenceEvolutionEngine._build_candidates()
def _build_candidates(self, facts, evidence, candidate_ids=None):
    # 按 entity + candidate_id 双重分组
    entity_candidate_facts: dict[str, dict[str, list]] = {}
    for fact in facts:
        entity = fact.get('entity', 'unknown')
        cid = fact.get('candidate_id')  # 从 fact 中获取
        
        if entity not in entity_candidate_facts:
            entity_candidate_facts[entity] = {}
        if cid not in entity_candidate_facts[entity]:
            entity_candidate_facts[entity][cid] = []
        entity_candidate_facts[entity][cid].append(fact)
    
    candidates = []
    for entity, candidate_groups in entity_candidate_facts.items():
        for cid, entity_facts_list in candidate_groups.items():
            # 每个 (entity, candidate_id) 组合生成一个 candidate
            source_ids = []
            for f in entity_facts_list:
                source_ids.extend(f.get('source_ids', []))
            source_ids = list(set(source_ids))
            
            candidates.append({
                'entity': entity,
                'candidate_id': cid,  # ✅ 正确的 candidate_id
                'evidence_chain': source_ids[:10],
                ...
            })
    
    return candidates
```

#### 4.2 优势

| 维度 | 评估 |
|------|------|
| 设计一致性 | ✅ 符合 Candidate 1:N Proposal 设计 |
| 数据完整性 | ✅ 保留完整 lineage |
| 多对一处理 | ✅ 每个 Candidate 独立生成 Proposal |
| 一对多处理 | ✅ 同一 Candidate 可生成多个 Proposal |
| 实现复杂度 | 中（需要修改 3 个方法） |

---

### 方案 B: 引入中间表（备选）

**原理**：如果业务上确实允许 Proposal 综合多个 Candidate，使用多对多关系

```sql
-- 创建中间表
CREATE TABLE proposal_candidates (
    proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE,
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    PRIMARY KEY (proposal_id, candidate_id)
);
```

**结论**：**不推荐**，因为设计文档明确规定 Proposal 属于单一 Candidate。

---

## 五、当前实现与设计冲突分析

### 5.1 设计约束 vs 当前实现

| 设计约束 | 当前实现 | 冲突 |
|----------|----------|------|
| Proposal 属于单一 Candidate | Entity Grouping 跨 Candidate 合并 | ❌ 冲突 |
| Candidate 1:1 Pending Proposal | 无去重检查 | ❌ 冲突 |
| Evidence 可追溯 | 丢失 Candidate 来源信息 | ❌ 冲突 |

### 5.2 必须修复的 Priority

```
P0: Evidence 携带 candidate_id（DG-001）
P0: Entity Grouping 保留 Candidate 边界（DG-002）
P0: 删除 index mapping 逻辑（DG-003）
P1: Scope 去重检查
P1: Candidate 状态转换
```

---

## 六、Regression Test 补充

### 6.1 必须测试的场景

```python
async def test_single_candidate_single_entity():
    """Test: 单一 Candidate → 单一 Entity"""
    candidate = await create_candidate(workspace_id, "content about X")
    proposals = await generate_proposals([candidate])
    
    # 验证：Proposal 的 candidate_id 正确
    for proposal in proposals:
        assert proposal.get('candidate_id') == str(candidate.id)

async def test_single_candidate_multi_entity():
    """Test: 单一 Candidate → 多个 Entity"""
    candidate = await create_candidate(workspace_id, "content with X and Y")
    proposals = await generate_proposals([candidate])
    
    # 验证：所有 Proposal 都关联到同一个 Candidate
    candidate_ids = {p.get('candidate_id') for p in proposals}
    assert len(candidate_ids) == 1
    assert str(candidate.id) in candidate_ids

async def test_multi_candidate_same_entity():
    """Test: 多个 Candidate → 同一 Entity（设计冲突场景）"""
    candidate_a = await create_candidate(workspace_id, "content about X")
    candidate_b = await create_candidate(workspace_id, "also about X")
    
    proposals = await generate_proposals([candidate_a, candidate_b])
    
    # 验证：每个 Candidate 应该产生独立的 Proposal
    candidate_ids = {p.get('candidate_id') for p in proposals}
    assert str(candidate_a.id) in candidate_ids
    assert str(candidate_b.id) in candidate_ids
    # 不允许合并！

async def test_evidence_lineage_preserved():
    """Test: Evidence → Fact → Proposal 的 lineage 完整"""
    candidate = await create_candidate(workspace_id, "test content")
    proposals = await generate_proposals([candidate])
    
    for proposal in proposals:
        # 验证 evidence_chain 中的 Evidence 都属于该 Candidate
        for eid in proposal.get('evidence_chain', []):
            evidence = await get_evidence(eid)
            assert evidence.candidate_id == candidate.id
```

---

## 七、结论与建议行动

### 7.1 核心结论

```
✅ 设计文档明确：Proposal 必须属于单一 Candidate（1:N 关系）
❌ 当前实现违反设计：Entity Grouping 跨 Candidate 合并 Facts
🚨 这是 P0 级别的 Design Gap
```

### 7.2 建议行动顺序

```
Step 1: 修复 P0 Alignment Bug（当前任务）
  → Evidence 携带 candidate_id
  → Entity Grouping 保留 Candidate 边界
  → 删除 index mapping 逻辑

Step 2: 更新 Regression Tests
  → 添加多场景测试用例
  → 验证 design constraint

Step 3: 执行 Schema Migration（Phase 1）
  → 添加 proposals.candidate_id FK
  → 添加 Unique Index
  → 迁移历史数据（如有可能）

Step 4: 实现 Candidate 状态转换（Phase 2）
  → approve_proposal() 更新 Candidate → confirmed
  → reject_proposal() 更新 Candidate → orphaned
  → _acquire_scope() 添加 NOT EXISTS 去重
```

### 7.3 是否可以进入 Schema Migration？

**❌ 暂不能**

前提条件：
1. ✅ 设计文档已确认（Proposal 属于单一 Candidate）
2. ❌ P0 Alignment Bug 尚未修复
3. ❌ Regression Tests 尚未覆盖多 Candidate 场景

---

## 八、最终决策

| 决策项 | 结论 |
|--------|------|
| Proposal 是否允许多个 Candidate | ❌ **不允许**（设计约束） |
| 当前 Index Mapping 是否安全 | ❌ **不安全** |
| 是否需要修复 P0 Alignment Bug | ✅ **必须修复** |
| 推荐修复方案 | **方案 A: Evidence 携带 candidate_id** |
| 是否可以进入 Schema Migration | ❌ **暂不能，需先修复 P0** |

---

**状态**: P0 Alignment Bug 确认，等待用户批准修复方案 A

**下一步**: 批准后开始 P0 Alignment Fix 实施
