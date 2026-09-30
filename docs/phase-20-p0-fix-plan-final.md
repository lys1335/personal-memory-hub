# Phase 20 — P0 Candidate ID Propagation Fix Plan

## 执行摘要

**Root Cause**: `reflection_service.py:758` 将 Evidence UUID 错认为 Candidate ID  
**影响**: 所有 1,042 个 Approved Proposals 的 candidate_id 错误（实际为 NULL 或错误值）  
**修复策略**: 分两阶段实施，先修复代码传递链，再执行 Schema Migration

---

## 一、Root Cause 确认

### 1.1 错误代码

**位置**: `reflection_service.py:756-766`

```python
# ❌ 错误代码
for c in evolution_result.candidates:
    evidence_chain = c.get('evidence_chain', [])
    candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'  # BUG!
    reflection_candidates.append({
        'id': candidate_id,  # 这是 Evidence UUID，不是 Candidate ID！
        ...
    })
```

### 1.2 验证结果

```sql
-- 查询确认：0 个 Proposal 的 evidence_chain[0] 匹配 Candidate ID
SELECT COUNT(*) FROM proposals p
JOIN candidates c ON c.id::text = LEFT(p.evidence_chain::text, 36)
WHERE p.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219';
-- 结果: 0
```

**结论**: 历史 1,042 个 Approved Proposal 无法通过 evidence_chain 恢复 Candidate ID

---

## 二、完整数据流追踪

### 2.1 当前错误流程

```
[_acquire_scope] (reflection_service.py:1054)
  ↓ SELECT id, entity_id, content, ... FROM candidates
  ↓ 返回 list[dict]，每个 dict 有 'id' 字段（Candidate UUID）
  
[_run_engine_pipeline] (reflection_service.py:700)
  ↓ batch = candidates[i:i+BATCH_SIZE]
  ↓ 每个 batch 是 list[dict]，dict 包含 {'id': candidate_uuid, ...}
  
  [EvidenceEvolutionEngine.evolve()] (evidence_evolution_engine.py:64)
    ↓ 输入: evidence=list[dict]（携带 Candidate ID）
    ↓ 处理: LLM 提取 facts
    ↓ 输出: EvolutionResult(candidates=[dict, ...])
    ↓ ❌ 输出 dict 不包含原始 candidate_id
    
  [BUG LOCATION] (reflection_service.py:755-766)
    ↓ for c in evolution_result.candidates:
    ↓ evidence_chain = c.get('evidence_chain', [])
    ↓ candidate_id = evidence_chain[0]  ← 错误！这是 Evidence UUID
    ↓ reflection_candidates.append({'id': candidate_id, ...})
    
  [ReflectionEngine.reflect_pipeline()] (reflection_engine.py:50)
    ↓ 输入: candidates=list[dict]（携带错误的 id）
    ↓ 输出: {proposals=[dict, ...]}
    
[_save_proposals] (reflection_service.py:1000)
  ↓ INSERT INTO proposals (id, workspace_id, type, ...) VALUES (...)
  ↓ ❌ SQL 不含 candidate_id 字段
```

### 2.2 Candidate ID 丢失点

| 步骤 | 函数 | Candidate ID 状态 |
|------|------|-------------------|
| 1 | `_acquire_scope()` | ✅ 存在（从 DB 读取） |
| 2 | `_run_engine_pipeline()` | ✅ 存在（传递给 Engine） |
| 3 | `EvidenceEvolutionEngine.evolve()` | ❌ **丢失**（输出无此字段） |
| 4 | `reflection_service.py:758` | ❌ **错误推导**（用 Evidence UUID 替代） |
| 5 | `ReflectionEngine.reflect_pipeline()` | ⚠️ 接收错误值 |
| 6 | `_save_proposals()` | ❌ **未保存**（INSERT 无此字段） |

**关键发现**:
- Candidate ID 在步骤 3 丢失（Engine 输出格式问题）
- 在步骤 4 被错误推导（Evidence UUID 冒充 Candidate ID）
- 在步骤 6 未被保存（Schema 缺失 + 代码缺失）

---

## 三、Proposal Creation Paths

### 3.1 Path 1: Evolution Pipeline（主要路径）

**Location**: `reflection_service.py:700-810`

```python
async def _run_engine_pipeline(...):
    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i:i + BATCH_SIZE]
        
        # Stage 1: Evidence Evolution
        evolution_result = await evidence_engine.evolve(evidence=batch, ...)
        
        # Stage 2: Reflection（BUG LOCATION）
        if evolution_result.candidates:
            for c in evolution_result.candidates:
                evidence_chain = c.get('evidence_chain', [])
                candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'  # BUG!
        
        result = await reflection_engine.reflect_pipeline(...)
        all_proposals.extend(result.get("proposals", []))
```

**修复点**: Line 758

### 3.2 Path 2: Manual API Call

**Location**: `app.py` → `ReflectionService.reflect()` → 同 Path 1

**结论**: 所有入口经过同一个 Pipeline，只需修复一处

### 3.3 Path 3: Tests / Fixtures

**检查**: 无直接创建 Proposal 的测试，所有测试经过 Service 层

---

## 四、推荐修复方案

### 方案 A: 在 EvolutionResult 中携带 Candidate ID（推荐）

**原理**: 让 EvidenceEvolutionEngine 的输出保留原始 Candidate ID

#### 4.1.1 修改 EvidenceEvolutionEngine

**File**: `backend/src/backend/engine/evidence_evolution_engine.py`

```python
# 修改 evolve() 方法，在输出中保留 candidate_id
async def evolve(self, *, evidence: list[dict], provider) -> EvolutionResult:
    # 输入 evidence 携带 candidate_id（来自 _acquire_scope）
    # 处理...
    
    # 输出时保留
    candidates = []
    for fact in facts:
        candidates.append({
            "entity": fact.get("entity"),
            "content": "...",
            "evidence_chain": fact.get("source_ids", []),
            "confidence": fact.get("confidence", 0.9),
            "candidate_id": fact.get("candidate_id"),  # ✅ 新增
        })
    
    return EvolutionResult(candidates=candidates, ...)
```

#### 4.1.2 修复 reflection_service.py:758

**File**: `backend/src/backend/service/reflection_service.py`

```python
# 修改前
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'

# 修改后
candidate_id = c.get('candidate_id')  # ✅ 从 EvolutionResult 获取
if not candidate_id:
    logger.warning(f"Missing candidate_id for evolution result")
    continue
```

#### 4.1.3 修改 _save_proposals()

**File**: `backend/src/backend/service/reflection_service.py`

```python
# 修改前
await conn.execute(text("""
    INSERT INTO proposals (id, workspace_id, type, ...) VALUES (...)
"""), {...})

# 修改后（需要 Schema Migration 配合）
await conn.execute(text("""
    INSERT INTO proposals (id, workspace_id, candidate_id, type, ...) VALUES (...)
"""), {
    ...
    "candidate_id": prop.get('candidate_id'),  # ✅ 新增
})
```

### 方案 B: 在 Service 层维护映射（备选）

**原理**: 不修改 Engine 输出，在 Service 层维护 Candidate ID 映射

**缺点**: 
- 需要额外的映射逻辑
- 增加复杂度
- 不如方案 A 清晰

**推荐**: 方案 A

---

## 五、具体修改清单

### 5.1 Phase P0: 代码修复（不需要 Schema 变更）

| 文件 | 行号 | 修改内容 | 风险 |
|------|------|----------|------|
| `evidence_evolution_engine.py` | 121+ | EvolutionResult 携带 candidate_id | 低 |
| `reflection_service.py` | 758 | 修复 candidate_id 推导逻辑 | 低 |
| `reflection_service.py` | 1029+ | _save_proposals() 添加 candidate_id 参数 | 中（需 Schema） |

### 5.2 Phase 1: Schema Migration（P0 验证后进行）

| 步骤 | 操作 | 风险 |
|------|------|------|
| 1 | `ALTER TABLE proposals ADD COLUMN candidate_id VARCHAR(36)` | 低 |
| 2 | `ADD CONSTRAINT fk_proposals_candidate FOREIGN KEY (...)` | 中 |
| 3 | `CREATE INDEX idx_proposals_candidate_id` | 低 |
| 4 | `CREATE UNIQUE INDEX idx_proposals_pending_unique WHERE status='pending'` | 中 |
| 5 | 更新 Proposal 模型 | 低 |
| 6 | 更新 ProposalRepository.create() | 低 |

---

## 六、历史 Approved Proposals 处理

### 6.1 现状

```
Total Approved: 1,042
candidate_id: NULL（当前无此列）
无法可靠映射到 Candidate
```

### 6.2 处理原则

```
✅ 不尝试自动映射
✅ 保持 NULL
✅ 等待后续可靠来源
❌ 不使用 evidence_chain[0] 推断
❌ 不使用 entity 模糊匹配
❌ 不使用 content 推断
```

### 6.3 未来可能的恢复方式

```
如果未来有可靠来源：
1. 通过 Evidence chain 追溯原始 Evidence
2. 通过 Evidence 追溯原始 Candidate（需额外字段）
3. 人工审核确认关联

当前阶段：
- candidate_id nullable
- 新数据必须填充
- 历史数据保持 NULL
```

---

## 七、Regression Test 设计

### 7.1 核心测试用例

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

### 7.2 测试文件位置

```
backend/tests/test_candidate_id_propagation.py  （新建）
backend/tests/test_service_layer.py  （更新）
backend/tests/test_reflection_engine.py  （更新）
```

---

## 八、实施顺序

### Phase P0: 代码修复（立即执行）

```
Step 1: 修改 EvidenceEvolutionEngine
  → EvolutionResult.candidates 携带 candidate_id
  
Step 2: 修改 reflection_service.py:758
  → 使用正确的 candidate_id 推导
  
Step 3: 运行单元测试
  → 验证 candidate_id 正确性
  
Step 4: 启动 Evolution 验证
  → 观察新 Proposal 的 candidate_id
```

### Phase 1: Schema Migration（P0 验证后进行）

```
Step 1: 创建 Alembic migration
  → ALTER TABLE proposals ADD COLUMN candidate_id
  → ADD CONSTRAINT FK
  → CREATE INDEX
  
Step 2: 运行 migration
  → 验证历史数据兼容
  
Step 3: 更新模型和 Repository
  → 添加 candidate_id 字段
  
Step 4: 运行集成测试
```

### Phase 2: 状态转换（可选）

```
Step 1: 修改 approve_proposal()
  → 添加 Candidate → confirmed
  
Step 2: 修改 reject_proposal()
  → 添加 Candidate → orphaned
  
Step 3: 修改 _acquire_scope()
  → 添加 NOT EXISTS pending proposal 去重
```

---

## 九、风险评估

| 风险项 | 级别 | 缓解措施 |
|--------|------|----------|
| P0 Bug 修复引入新 bug | 中 | 完整回归测试 |
| Migration 失败 | 低 | 备份数据库 |
| 历史数据兼容 | 低 | candidate_id nullable |
| 性能影响 | 低 | 索引优化 |
| 并发问题 | 低 | 事务隔离 |

---

## 十、结论

### P0 修复是否可以独立进行？

**是的。**

```
Phase P0: 代码修复（不需要 Schema 变更）
  → 修改 EvidenceEvolutionEngine 输出格式
  → 修改 reflection_service.py:758
  → 验证新 Proposal 正确携带 candidate_id
  
Phase 1: Schema Migration（P0 验证后进行）
  → ALTER TABLE proposals ADD COLUMN candidate_id
  → 添加 FK 和索引
  → 更新模型和 Repository
```

### 是否可以进入编码？

**✅ 可以，需用户确认方案 A**

前提条件：
1. ✅ Root Cause 已确认
2. ✅ 调用链已追踪
3. ✅ 修复方案已设计
4. ⚠️ 需要用户确认方案 A（推荐）
5. ⚠️ 需要用户确认分步实施

---

**状态**: P0 Fix Plan 已完成  
**下一步**: 等待用户确认后开始 Phase P0 实施
