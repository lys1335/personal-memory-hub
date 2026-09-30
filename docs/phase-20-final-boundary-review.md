# Phase 20 — Final Boundary Review: Candidate ID Propagation

## 执行摘要

🚨 **发现 P0 级别 Design Gap**

**当前 P0 Fix 存在严重 Alignment Bug**：
- EvidenceEvolutionEngine 的 Entity Grouping 逻辑会**跨 Candidate 合并 Facts**
- 违反设计文档明确的约束：**Proposal 必须属于单一 Candidate**
- Index mapping 方案不可靠（dict 顺序不确定、K≠M）

---

## 一、设计约束确认

### 1.1 Proposal-Candidate 关系

**来源**: `phase-20-candidate-proposal-lifecycle-design.md:148`

```
**推荐**: Candidate 1 : N Proposal（历史），但 Candidate 1 : 1 Pending Proposal（同时）

Candidate A
    ├── Proposal #1 (pending)     ← 当前生效
    ├── Proposal #2 (approved)    ← 历史（已创建 MemoryNode）
    ├── Proposal #3 (rejected)    ← 历史
    └── Proposal #4 (rejected)    ← 历史
```

### 1.2 关键原则

```
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

### 1.3 业务语义

| 问题 | 答案 |
|------|------|
| Proposal 是否允许多个 Candidate？ | ❌ **不允许** |
| 一个 Candidate 可以有多少 Proposal？ | ✅ 多个（历史记录） |
| 同时可以有多个 Pending Proposal 对应同一 Candidate？ | ❌ **不允许** |

---

## 二、当前实现问题

### 2.1 数据流追踪

```
[_acquire_scope()]
  ↓ 返回 list[candidate_dict] (N 个 candidates)
  ↓ 每个 dict 有 'id' (Candidate UUID)
  
[_run_engine_pipeline()]
  ↓ batch = candidates[i:i+BATCH_SIZE]
  ↓ batch_ids = [str(c.get('id')) for c in batch]
  
[EvidenceEvolutionEngine.evolve()]
  ↓ evidence = batch (携带 candidate_id? NO!)
  ↓ _extract_facts() → facts (丢失 candidate_id!)
  ↓ _build_candidates(facts, evidence, candidate_ids=batch_ids)
  
[_build_candidates()]  ← BUG LOCATION
  ↓ 按 entity 分组 facts (不保留 Candidate 边界)
  ↓ for idx, (entity, entity_facts_list) in enumerate(entity_facts.items()):
  ↓     candidate_id = candidate_ids[idx]  ← 错误！
  
[ReflectionService]
  ↓ 使用错误的 candidate_id
  ↓ 生成 Proposal
```

### 2.2 具体问题

| 问题 | 位置 | 影响 |
|------|------|------|
| Evidence dict 无 candidate_id | `evidence_evolution_engine.py` | 丢失 lineage |
| Fact dict 无 candidate_id | `evidence_evolution_engine.py:199-201` | 丢失 lineage |
| Entity Grouping 跨 Candidate | `evidence_evolution_engine.py:338-344` | 合并多个 Candidate |
| Index mapping 不可靠 | `evidence_evolution_engine.py:370-371` | 错配 |

---

## 三、Bug 复现测试

### 3.1 测试代码

```python
async def test_multi_candidate_same_entity():
    """多 Candidate → 同一 Entity"""
    candidate_ids = ["cand-A", "cand-B"]
    facts = [
        {"entity": "X", "source_ids": ["ev-A"], "candidate_id": "cand-A"},
        {"entity": "X", "source_ids": ["ev-B"], "candidate_id": "cand-B"},
    ]
    candidates = engine._build_candidates(facts, evidence, candidate_ids)
    
    # 当前结果：合并为一个 Proposal
    assert len(candidates) == 1  # ❌ 应该为 2
    assert candidates[0]['candidate_id'] == "cand-A"  # 随机选一个
```

### 3.2 测试结果

```
======================================================================
TEST: Multi-Candidate → Same Entity
======================================================================
Input:
  Candidate IDs: ['cand-A', 'cand-B']
  Facts: 2
    - Entity: X, Source: ['ev-A'], Candidate: cand-A
    - Entity: X, Source: ['ev-B'], Candidate: cand-B

Output:
  Candidates: 1
    [0] Entity: X, candidate_id: cand-A

Validation:
  ❌ FAIL: 合并为一个 Proposal（违反设计约束）
     candidate_id: cand-A
     应该有两个独立的 Proposal
```

---

## 四、根因分析

### 4.1 为什么 Index Mapping 失败

```
原因 1: dict.items() 顺序不确定
  - Python 3.7+ 保持插入顺序
  - 但插入顺序取决于 LLM 输出
  - 不保证与 candidate_ids 顺序一致

原因 2: K ≠ M
  - K = entity_facts 数量
  - M = candidate_ids 数量
  - 多对一：K < M（合并丢失）
  - 一对多：K > M（IndexError）

原因 3: Entity Grouping 丢失边界
  - 当前逻辑：按 entity 分组
  - 正确逻辑：按 (entity, candidate_id) 分组
```

### 4.2 信息丢失点

```
Candidate (id=cand-A, content="...")
    ↓ _acquire_scope()
candidate_dict = {'id': 'cand-A', 'content': '...', ...}
    ↓ 传入 Engine
evidence_dict = {'id': 'ev-001', 'content': '...'}
    ↓ ❌ 丢失 candidate_id！
_extract_facts()
facts = [{'entity': 'X', 'value': 'V', 'source_ids': ['ev-001']}]
    ↓ ❌ 无 candidate_id 信息
_build_candidates()
# 尝试通过 index 恢复 → 不可靠！
```

---

## 五、修复方案

### 方案 A: Evidence 携带 Candidate ID（推荐）

#### 5.1 修改点

**File 1**: `evidence_evolution_engine.py`

```python
# 修改 evolve() 方法
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

**File 2**: `evidence_evolution_engine.py`

```python
# 修改 _extract_facts() 方法
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
                break
```

**File 3**: `evidence_evolution_engine.py`

```python
# 修改 _build_candidates() 方法
def _build_candidates(self, facts, evidence, candidate_ids=None):
    # 按 (entity, candidate_id) 双重分组
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

#### 5.2 优势

| 维度 | 评估 |
|------|------|
| 设计一致性 | ✅ 符合 Candidate 1:N Proposal 设计 |
| 数据完整性 | ✅ 保留完整 lineage |
| 多对一处理 | ✅ 每个 Candidate 独立生成 Proposal |
| 一对多处理 | ✅ 同一 Candidate 可生成多个 Proposal |
| 实现复杂度 | 中（需要修改 3 个方法） |

---

### 方案 B: 引入中间表（备选，不推荐）

```sql
CREATE TABLE proposal_candidates (
    proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE,
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    PRIMARY KEY (proposal_id, candidate_id)
);
```

**结论**: 不推荐，因为设计文档明确规定 Proposal 属于单一 Candidate。

---

## 六、设计 Gap 清单

| Gap ID | 描述 | 严重程度 | 状态 |
|--------|------|----------|------|
| **DG-001** | Evidence dict 丢失 candidate_id | P0 | 待修复 |
| **DG-002** | Fact dict 丢失 candidate_id | P0 | 待修复 |
| **DG-003** | Entity Grouping 跨 Candidate 合并 | P0 | 待修复 |
| **DG-004** | Index mapping 不可靠 | P0 | 待修复 |

---

## 七、Regression Test 补充

### 7.1 必须测试的场景

```python
async def test_single_candidate_single_entity():
    """单一 Candidate → 单一 Entity"""
    candidate = await create_candidate(workspace_id, "content about X")
    proposals = await generate_proposals([candidate])
    for p in proposals:
        assert p.get('candidate_id') == str(candidate.id)

async def test_single_candidate_multi_entity():
    """单一 Candidate → 多个 Entity"""
    candidate = await create_candidate(workspace_id, "content with X and Y")
    proposals = await generate_proposals([candidate])
    candidate_ids = {p.get('candidate_id') for p in proposals}
    assert len(candidate_ids) == 1
    assert str(candidate.id) in candidate_ids

async def test_multi_candidate_same_entity():
    """多 Candidate → 同一 Entity（关键测试！）"""
    candidate_a = await create_candidate(workspace_id, "content about X")
    candidate_b = await create_candidate(workspace_id, "also about X")
    proposals = await generate_proposals([candidate_a, candidate_b])
    
    # 每个 Candidate 应该产生独立的 Proposal
    candidate_ids = {p.get('candidate_id') for p in proposals}
    assert str(candidate_a.id) in candidate_ids
    assert str(candidate_b.id) in candidate_ids

async def test_evidence_lineage_preserved():
    """Evidence → Fact → Proposal lineage 完整"""
    candidate = await create_candidate(workspace_id, "test content")
    proposals = await generate_proposals([candidate])
    for p in proposals:
        for eid in p.get('evidence_chain', []):
            evidence = await get_evidence(eid)
            assert evidence.candidate_id == candidate.id
```

---

## 八、结论

### 8.1 核心结论

```
✅ 设计文档明确：Proposal 必须属于单一 Candidate（1:N 关系）
❌ 当前 P0 Fix 违反设计：Entity Grouping 跨 Candidate 合并 Facts
🚨 这是 P0 级别的 Design Gap（DG-001 ~ DG-004）
```

### 8.2 建议行动顺序

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

### 8.3 是否可以进入 Schema Migration？

**❌ 暂不能**

前提条件：
1. ✅ 设计文档已确认（Proposal 属于单一 Candidate）
2. ❌ P0 Alignment Bug 尚未修复
3. ❌ Regression Tests 尚未覆盖多 Candidate 场景

---

## 九、最终决策

| 决策项 | 结论 |
|--------|------|
| Proposal 是否允许多个 Candidate | ❌ **不允许** |
| 当前 P0 Fix 是否安全 | ❌ **不安全** |
| 是否需要修复 P0 Alignment Bug | ✅ **必须修复** |
| 推荐修复方案 | **方案 A: Evidence 携带 candidate_id** |
| 是否可以进入 Schema Migration | ❌ **暂不能，需先修复 P0** |

---

**状态**: P0 Alignment Bug 已确认，等待用户批准修复方案

**下一步**: 批准后开始 P0 Alignment Fix 实施
