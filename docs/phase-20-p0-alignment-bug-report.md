# Phase 20 — P0 Fix Revalidation: Candidate ID Alignment

## 执行摘要

🚨 **发现 P0 Alignment Bug**

当前 P0 修复使用 `candidate_ids[idx]` 基于 entity 分组索引映射，
这会导致严重的 Candidate ID 错配风险。

---

## 一、当前实现分析

### 1.1 数据流

```
[_acquire_scope()]
  ↓ 返回 list[candidate_dict] (N 个 candidates)
  
[_run_engine_pipeline()]
  ↓ batch = candidates[i:i+BATCH_SIZE]  (M 个 candidates)
  ↓ batch_ids = [str(c.get('id')) for c in batch]  (M 个 IDs)
  
[EvidenceEvolutionEngine.evolve()]
  ↓ evidence = batch  (M 个 evidence dicts)
  ↓ _extract_facts()  → LLM 提取 facts
  ↓ _build_candidates(facts, evidence, candidate_ids=batch_ids)
  
[_build_candidates()]
  ↓ 按 entity 分组 facts → entity_facts (K 个 entity groups)
  ↓ for idx, (entity, entity_facts_list) in enumerate(entity_facts.items()):
  ↓     candidate_id = candidate_ids[idx]  ← BUG!
```

### 1.2 关键问题

| 问题 | 说明 |
|------|------|
| **K ≠ M** | Entity 分组数量不一定等于 Candidate 数量 |
| **顺序不确定** | `dict.items()` 顺序不保证与输入一致 |
| **多对一** | 多个 Candidate 可能产生同一个 Entity |
| **一对多** | 一个 Candidate 可能产生多个 Entity |
| **丢失** | 无 facts 的 Candidate 会被跳过 |

---

## 二、错配场景分析

### 场景 A: 一对一映射（理想情况）

```
Candidate A → Evidence A → Entity X
Candidate B → Evidence B → Entity Y

entity_facts = {
    'X': [...],  # idx=0
    'Y': [...]   # idx=1
}

candidate_ids = ['cand-A', 'cand-B']

candidate_ids[0] = 'cand-A' → Entity X ✅
candidate_ids[1] = 'cand-B' → Entity Y ✅
```

**状态**: 碰巧正确，但依赖巧合

---

### 场景 B: 多 Candidate → 同一 Entity（失败）

```
Candidate A → Evidence A → Entity X
Candidate B → Evidence B → Entity X

entity_facts = {
    'X': [fact_from_A, fact_from_B]  # idx=0 (合并!)
}

candidate_ids = ['cand-A', 'cand-B']

candidate_ids[0] = 'cand-A' → Entity X ❌
candidate_ids[1] = ??? (无对应 entity)

结果:
- Entity X 关联到 cand-A（错误！应为 A+B）
- cand-B 完全丢失
```

**状态**: ❌ **严重错配**

---

### 场景 C: 多 Candidate → 部分相同 Entity（失败）

```
Candidate A → Evidence A → Entity X
Candidate B → Evidence B → Entity Y
Candidate C → Evidence C → Entity X

entity_facts = {
    'X': [fact_from_A, fact_from_C]  # idx=0 (合并!)
    'Y': [fact_from_B]               # idx=1
}

candidate_ids = ['cand-A', 'cand-B', 'cand-C']

candidate_ids[0] = 'cand-A' → Entity X ❌ (应为 A+C)
candidate_ids[1] = 'cand-B' → Entity Y ✅
candidate_ids[2] = 'cand-C' → ??? (无对应 entity)

结果:
- Entity X 只关联到 cand-A，丢失 cand-C
- cand-C 完全丢失
```

**状态**: ❌ **严重错配**

---

### 场景 D: 单 Candidate → 多 Entity（失败）

```
Candidate A → Evidence A → Entity X
             → Evidence A → Entity Y

entity_facts = {
    'X': [fact1]  # idx=0
    'Y': [fact2]  # idx=1
}

candidate_ids = ['cand-A']

candidate_ids[0] = 'cand-A' → Entity X ✅
candidate_ids[1] = ??? (越界！)

结果:
- Entity X 正确关联到 cand-A
- Entity Y 获得 IndexError 或错误值
```

**状态**: ❌ **IndexError 或错配**

---

### 场景 E: Candidate 无有效 Entity（失败）

```
Candidate A → Evidence A → (LLM 未提取到有效 entity)
Candidate B → Evidence B → Entity Y

entity_facts = {
    'Y': [fact_from_B]  # idx=0
}

candidate_ids = ['cand-A', 'cand-B']

candidate_ids[0] = 'cand-A' → Entity Y ❌ (错误关联！)
candidate_ids[1] = 'cand-B' → ??? (丢失)

结果:
- Entity Y 错误关联到 cand-A
- cand-B 完全丢失
```

**状态**: ❌ **严重错配**

---

## 三、根本原因

### 3.1 数据丢失点

```
证据链：
Candidate (id=cand-A)
    ↓ _acquire_scope()
candidate_dict = {'id': 'cand-A', 'content': '...', ...}
    ↓ 传入 EvidenceEvolutionEngine
evidence_dict = {'id': 'ev-001', 'content': '...'}
    ↓ ❌ candidate_id 丢失！
_extract_facts()
facts = [{'entity': 'X', 'value': 'V', 'source_ids': ['ev-001'], ...}]
    ↓ ❌ 无 candidate_id 信息
_build_candidates()
# 尝试通过 index 恢复 → 不可靠！
```

### 3.2 关键缺失

```
❌ evidence dict 不包含 candidate_id
❌ fact dict 不包含 candidate_id
❌ entity_facts 不包含 candidate_id 来源信息
```

---

## 四、推荐修复方案

### 方案 A: 在 Evidence 中携带 Candidate ID（推荐）

**原理**: 在 evidence dict 中保留原始 candidate_id，通过 source_ids 传递到 fact

**修改点**:

#### 4.1.1 EvidenceEvolutionEngine.evolve()

```python
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

#### 4.1.2 EvidenceEvolutionEngine._extract_facts()

```python
async def _extract_facts(self, evidence, provider):
    # 从 evidence 中提取 candidate_id
    evidence_candidate_map = {}
    for e in evidence:
        eid = e.get('id')
        cid = e.get('candidate_id')
        if eid and cid:
            evidence_candidate_map[eid] = cid
    
    # ... 原有逻辑 ...
    
    # 将 candidate_id 注入到 fact 的 metadata
    for fact in facts:
        for sid in fact.get('source_ids', []):
            if sid in evidence_candidate_map:
                fact['candidate_id'] = evidence_candidate_map[sid]
                break
```

#### 4.1.3 EvidenceEvolutionEngine._build_candidates()

```python
def _build_candidates(self, facts, evidence, candidate_ids=None):
    # 不再使用 index mapping
    # 直接从 fact 中提取 candidate_id
    
    entity_facts = {}
    for fact in facts:
        entity = fact.get('entity', 'unknown')
        if entity not in entity_facts:
            entity_facts[entity] = []
        entity_facts[entity].append(fact)
    
    candidates = []
    for entity, entity_facts_list in entity_facts.items():
        # 从 facts 中提取 candidate_id（可能有多个）
        candidate_ids_found = set()
        for f in entity_facts_list:
            cid = f.get('candidate_id')
            if cid:
                candidate_ids_found.add(cid)
        
        # 使用第一个找到的 candidate_id（或 None）
        candidate_id = list(candidate_ids_found)[0] if candidate_ids_found else None
        
        candidates.append({
            'entity': entity,
            'candidate_id': candidate_id,  # ✅ 从 fact 中获取
            ...
        })
    
    return candidates
```

### 方案 B: 保持 batch 结构传递（备选）

**原理**: 不改变 Engine 接口，在 Service 层维护映射

```python
# reflection_service.py
# 维护 candidate_id → evidence_id 映射
evidence_to_candidate = {}
for ev in batch:
    cid = ev.get('id')  # 这里的 id 就是 candidate_id
    if cid:
        evidence_to_candidate[cid] = cid

# 传递给 Engine（需要修改 Engine 接口）
evolution_result = await evidence_engine.evolve(
    evidence=batch,
    provider=provider,
    evidence_to_candidate=evidence_to_candidate,  # 新参数
)
```

---

## 五、Regression Test 补充

### 5.1 必须新增的测试用例

```python
async def test_multi_candidate_same_entity():
    """测试：多个 Candidate 产生同一 Entity 时，candidate_id 正确合并"""
    # Candidate A 和 B 都产生 Entity X
    candidate_a = await create_candidate(workspace_id, "content_a_about_x")
    candidate_b = await create_candidate(workspace_id, "content_b_about_x")
    
    proposals = await generate_proposals([candidate_a, candidate_b])
    
    # 应该有一个 Proposal 关联到 Entity X
    # candidate_id 应该包含 A 和 B（或至少其中一个）
    assert len(proposals) > 0
    for proposal in proposals:
        cid = proposal.get('candidate_id')
        assert cid in [str(candidate_a.id), str(candidate_b.id)]

async def test_single_candidate_multi_entity():
    """测试：单个 Candidate 产生多个 Entity 时，每个 Entity 都有正确的 candidate_id"""
    candidate = await create_candidate(workspace_id, "content_with_multiple_entities")
    
    proposals = await generate_proposals([candidate])
    
    # 每个 Proposal 都应该关联到同一个 candidate
    for proposal in proposals:
        assert proposal.get('candidate_id') == str(candidate.id)

async def test_candidate_no_entity():
    """测试：Candidate 无有效 Entity 时，不应产生错配"""
    candidate = await create_candidate(workspace_id, "irrelevant_content")
    
    proposals = await generate_proposals([candidate])
    
    # 即使没有 proposals，也不应该有其他 Candidate 的 ID 被错误关联
    # （这个测试依赖于其他 Candidate 同时存在）
```

---

## 六、结论

### 当前 P0 Fix 状态

| 检查项 | 状态 |
|--------|------|
| Index mapping 安全 | ❌ **不安全** |
| 场景 A（一对一） | ⚠️ 碰巧正确 |
| 场景 B（多对一） | ❌ **失败** |
| 场景 C（部分相同） | ❌ **失败** |
| 场景 D（一对多） | ❌ **失败** |
| 场景 E（无 Entity） | ❌ **失败** |

### 是否需要修复？

**🚨 是的，这是 P0 级别的 Alignment Bug**

### 是否影响 Schema Migration？

**是的，必须先修复 Alignment 问题，再执行 Schema Migration**

---

## 七、建议行动

```
Step 1: 修复 EvidenceEvolutionEngine
  → 在 evidence dict 中携带 candidate_id
  → 在 fact dict 中携带 candidate_id
  → 在 _build_candidates() 中从 fact 提取 candidate_id（不使用 index）

Step 2: 更新测试
  → 添加多 Candidate → 单 Entity 场景测试
  → 添加单 Candidate → 多 Entity 场景测试

Step 3: 验证修复
  → 运行单元测试
  → 运行集成测试

Step 4: 执行 Schema Migration
  → Phase 1 开始
```

---

**状态**: P0 Fix 存在 Alignment Bug，需要修复后才能进入 Schema Migration

**下一步**: 等待用户确认修复方案（推荐方案 A）
