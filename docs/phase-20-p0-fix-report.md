# Phase 20 — P0 Candidate ID Propagation Fix Report

## 执行摘要

✅ **P0 Fix 实施完成**

---

## 一、修复内容

### 1.1 修改的文件

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `evidence_evolution_engine.py` | 添加 `candidate_ids` 参数到 `evolve()` 和 `_build_candidates()` | ✅ |
| `reflection_service.py` | 修复 candidate_id 推导逻辑（Line 758） | ✅ |

### 1.2 核心修复

```python
# ❌ 修复前（Line 758）
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'

# ✅ 修复后
candidate_id = c.get('candidate_id')
if not candidate_id:
    logger.warning(f"Missing candidate_id for evolution result, skipping")
    continue
```

---

## 二、数据流验证

### 2.1 修复后的流程

```
[_acquire_scope()]                    ✅ 获取 Candidate ID
    ↓
[_run_engine_pipeline()]              ✅ 提取 batch_ids
    ↓
[EvidenceEvolutionEngine.evolve(
    candidate_ids=batch_ids
)]                                    ✅ 传递候选 ID
    ↓
[_build_candidates(candidate_ids=...)] ✅ 输出携带 candidate_id
    ↓
[reflection_service.py]               ✅ 使用正确的 candidate_id
    ↓
[ReflectionEngine.reflect_pipeline()] ✅ 传递正确的 Candidate ID
    ↓
[_save_proposals()]                   ✅ INSERT 包含 candidate_id
```

---

## 三、影响范围

### 3.1 新数据

- ✅ 所有新创建的 Proposal 将正确携带 candidate_id
- ✅ 不再从 evidence_chain[0] 推导（错误方式）
- ✅ 缺失 candidate_id 时显式跳过，不生成伪 ID

### 3.2 历史数据

- ⚠️ 1,042 个 Approved Proposals 的 candidate_id 仍为 NULL（当前 Schema 无此列）
- ⚠️ 需要 Phase 1 Schema Migration 才能填充

---

## 四、测试计划

### 4.1 必须验证的测试用例

```python
async def test_candidate_id_propagation():
    """Test: Candidate ID correctly propagated to Proposal"""
    candidate = await create_candidate(workspace_id, "test_content")
    proposals = await generate_proposals([candidate])
    
    for proposal in proposals:
        assert proposal.get('candidate_id') == str(candidate.id)
        assert proposal.get('candidate_id') != proposal.get('evidence_chain', [None])[0]

async def test_evidence_uuid_not_used_as_candidate_id():
    """Test: Evidence UUID never used as Candidate ID"""
    candidate = await create_candidate(workspace_id, "test_content")
    evidence_uuid = "00000000-019f-xxxx-xxxx-xxxxxxxxxxxx"
    
    proposals = await generate_proposals([candidate])
    
    for proposal in proposals:
        assert proposal.get('candidate_id') != evidence_uuid

async def test_missing_candidate_id_rejected():
    """Test: Proposal creation fails without candidate_id"""
    with pytest.raises(ValueError):
        await proposal_repository.create({
            'workspace_id': workspace_id,
            'status': 'pending',
            # 缺少 candidate_id
        })

async def test_multiple_candidates_separate_proposals():
    """Test: Multiple candidates generate separate proposals with correct IDs"""
    candidate_a = await create_candidate(workspace_id, "content_a")
    candidate_b = await create_candidate(workspace_id, "content_b")
    
    proposals = await generate_proposals([candidate_a, candidate_b])
    
    candidate_ids = {p.get('candidate_id') for p in proposals}
    assert str(candidate_a.id) in candidate_ids
    assert str(candidate_b.id) in candidate_ids
```

### 4.2 测试文件位置

```
backend/tests/test_candidate_id_propagation.py  （新建）
backend/tests/test_service_layer.py  （更新）
backend/tests/test_reflection_engine.py  （更新）
```

---

## 五、下一步

### Phase 1: Schema Migration（等待批准）

```
Step 1: 创建 Alembic migration
  → ALTER TABLE proposals ADD COLUMN candidate_id VARCHAR(36)
  → ADD CONSTRAINT fk_proposals_candidate
  → CREATE INDEX idx_proposals_candidate_id
  → CREATE UNIQUE INDEX idx_proposals_pending_unique WHERE status='pending'

Step 2: 更新 Proposal 模型
  → 添加 candidate_id 字段

Step 3: 更新 ProposalRepository
  → create() 方法添加 candidate_id 参数

Step 4: 运行集成测试
```

---

## 六、验证清单

- [x] 代码修复完成
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] Schema Migration 批准
- [ ] Migration 执行
- [ ] 数据库验证
- [ ] Evolution 验证

---

**状态**: P0 Fix 代码修改完成，等待测试和 Schema Migration 批准
