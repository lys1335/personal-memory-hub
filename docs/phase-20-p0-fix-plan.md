# Phase 20 — P0 Candidate ID Propagation Fix Plan

## 一、Root Cause 分析

### 1.1 错误代码位置

**File**: `backend/src/backend/service/reflection_service.py`  
**Line**: 758  
**错误代码**:
```python
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'
```

### 1.2 根本原因

```
❌ 当前错误流程：
Candidate (id=cand_123)
    ↓ _acquire_scope()
Candidates list
    ↓ EvidenceEvolutionEngine.evolve()
Evolved candidates (dict with evidence_chain)
    ↓ reflection_service.py:758
candidate_id = evidence_chain[0]  ← 这是 Evidence UUID，不是 Candidate ID！
    ↓
ReflectionEngine.reflect_pipeline()
    ↓
Proposal creation
    ↓
candidate_id = Evidence UUID (错误!)

✅ 正确流程：
Candidate (id=cand_123)
    ↓ _acquire_scope()
Candidates list (携带 id)
    ↓ EvidenceEvolutionEngine.evolve()
EvolutionResult.candidates (携带原始 candidate_id)
    ↓ reflection_service.py (修复后)
candidate_id = original_candidate.id  ← 正确的 Candidate ID！
    ↓
ReflectionEngine.reflect_pipeline()
    ↓
Proposal creation
    ↓
candidate_id = cand_123 (正确!)
```

### 1.3 Candidate ID 丢失位置

| 步骤 | 函数 | 状态 |
|------|------|------|
| 1 | `_acquire_scope()` | ✅ 获取 Candidate ID |
| 2 | `_run_engine_pipeline()` | ⚠️ 传递 Candidates 给 Engine |
| 3 | `EvidenceEvolutionEngine.evolve()` | ❌ 输出 dict，无 candidate_id 字段 |
| 4 | `reflection_service.py:758` | ❌ 错误推导 candidate_id |
| 5 | `ReflectionEngine.reflect_pipeline()` | ⚠️ 接收错误的 candidate_id |
| 6 | `_save_proposals()` | ❌ INSERT 不含 candidate_id |

**结论**: Candidate ID 在步骤 3-4 丢失/错误化

---

## 二、完整调用链追踪

### 2.1 数据流（从 Scope 到 Proposal）

```
[_acquire_scope] (reflection_service.py:1054)
  ↓ SELECT candidates FROM db (id, entity_id, content, ...)
  ↓ 返回 list[dict] with 'id' field
  
[_run_engine_pipeline] (reflection_service.py:650)
  ↓ 接收 candidates: list[dict]
  ↓ 分批次处理 (BATCH_SIZE)
  
  [Batch Loop] (reflection_service.py:710)
    ↓ batch = candidates[i:i+BATCH_SIZE]
    
    [EvidenceEvolutionEngine.evolve()] (evidence_evolution_engine.py:64)
      ↓ 输入: evidence=list[dict]
      ↓ 输出: EvolutionResult(candidates=[dict, ...])
      ↓ 每个 candidate dict: {entity, content, evidence_chain, confidence, ...}
      ↓ ❌ 无 candidate_id 字段
      
    [Bug Location] (reflection_service.py:755-766)
      ↓ for c in evolution_result.candidates:
      ↓ evidence_chain = c.get('evidence_chain', [])
      ↓ candidate_id = evidence_chain[0]  ← BUG!
      ↓ reflection_candidates.append({'id': candidate_id, ...})
      
    [ReflectionEngine.reflect_pipeline()] (reflection_engine.py:50)
      ↓ 输入: candidates=list[dict] (带错误的 id)
      ↓ 输出: {facts, entities, proposals}
      
  ↓ 合并所有 batch 结果
  
[_save_proposals] (reflection_service.py:1000)
  ↓ 输入: proposals=list[dict]
  ↓ ❌ INSERT 不含 candidate_id 字段
  
[Database]
  ↓ proposals 表无 candidate_id 列
  ↓ 所有 Proposal 的 candidate_id 都是 NULL 或错误值
```

### 2.2 关键发现

```
发现 1: EvidenceEvolutionEngine 输出格式不包含 candidate_id
  → EvolutionResult.candidates[i] 是纯 dict
  → 没有保留原始 Candidate 的 ID
  
发现 2: reflection_service.py:758 尝试从 evidence_chain 推导
  → 假设 evidence_chain[0] 是 Candidate ID
  → 实际上 evidence_chain[0] 是 Evidence UUID
  → 这是错误的伪关联
  
发现 3: _save_proposals() 不保存 candidate_id
  → 即使传入 candidate_id，INSERT 也不包含该字段
  → 需要同时修改 Model 和 Migration
```

---

## 三、所有 Proposal Creation Paths

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
                reflection_candidates.append({
                    'id': candidate_id,  # 错误的 ID
                    ...
                })
        
        result = await reflection_engine.reflect_pipeline(scope=scope, candidates=reflection_candidates, ...)
        all_proposals.extend(result.get("proposals", []))
```

**修复点**: Line 758

### 3.2 Path 2: Manual API Call

**Location**: `app.py` (API endpoint)

```
POST /api/evolution/reflect
  ↓
ReflectionService.reflect()
  ↓
反射_service.py:92
  ↓
同 Path 1
```

**结论**: 所有入口都经过同一个 Pipeline，只需修复一处

### 3.3 Path 3: Tests / Fixtures

**检查**: 是否有直接创建 Proposal 的测试

```bash
grep -rn "proposal.*create\|Proposal(" backend/tests/ 2>/dev/null
```

**建议**: 更新测试以验证 candidate_id 正确性

---

## 四、推荐修复方案

### 方案 A: 在 EvolutionResult 中携带 Candidate ID（推荐）

**原理**: 让 EvidenceEvolutionEngine 的输出携带原始 Candidate ID

**修改点**:

#### 4.1.1 EvidenceEvolutionEngine（最小修改）

**File**: `backend/src/backend/engine/evidence_evolution_engine.py`

```python
# 当前（第 121 行附近）
# Step 5: Build candidates
candidates = []
for entity, entity_facts in grouped.items():
    candidates.append({
        "entity": entity,
        "content": "...",
        "evidence_chain": source_ids,
        "confidence": avg_confidence,
        # 新增：携带原始 Candidate ID
        "candidate_id": entity_facts[0].get("candidate_id"),  # ← 需要传递
    })

return EvolutionResult(candidates=candidates, ...)
```

#### 4.1.2 ReflectionService Pipeline（核心修复）

**File**: `backend/src/backend/service/reflection_service.py`

```python
# 修改前（Line 755-766）
if evolution_result.candidates:
    reflection_candidates = []
    for c in evolution_result.candidates:
        evidence_chain = c.get('evidence_chain', [])
        candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'  # BUG!
        reflection_candidates.append({
            'id': candidate_id,
            ...
        })

# 修改后
if evolution_result.candidates:
    reflection_candidates = []
    for c in evolution_result.candidates:
        candidate_id = c.get('candidate_id')  # ✅ 从 EvolutionResult 获取
        if not candidate_id:
            logger.warning(f"Missing candidate_id for evolution result, skipping")
            continue
        reflection_candidates.append({
            'id': candidate_id,  # ✅ 正确的 Candidate ID
            'content': c.get('content', ''),
            ...
        })
```

#### 4.1.3 _save_proposals()（Schema 依赖）

**File**: `backend/src/backend/service/reflection_service.py`

```python
# 修改前（Line 1029-1050）
await conn.execute(text("""
    INSERT INTO proposals (
        id, workspace_id, type, source_level, target_level,
        entity, evidence_chain, confidence, summary, content,
        status, created_at, updated_at
    ) VALUES (
        :id, :workspace_id, :type, :source_level, :target_level,
        :entity, :evidence_chain, :confidence, :summary, :content,
        'pending', NOW(), NOW()
    )
"""), {...})

# 修改后（需要 Schema Migration 配合）
await conn.execute(text("""
    INSERT INTO proposals (
        id, workspace_id, candidate_id, type, source_level, target_level,
        entity, evidence_chain, confidence, summary, content,
        status, created_at, updated_at
    ) VALUES (
        :id, :workspace_id, :candidate_id, :type, :source_level, :target_level,
        :entity, :evidence_chain, :confidence, :summary, :content,
        'pending', NOW(), NOW()
    )
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

---

## 五、具体修改清单

### 5.1 必须修改的文件

| 文件 | 行号 | 修改内容 | 优先级 |
|------|------|----------|--------|
| `reflection_service.py` | 758 | 修复 candidate_id 推导逻辑 | **P0** |
| `reflection_service.py` | 1029-1050 | _save_proposals() 添加 candidate_id | **P0** |
| `proposal_repository.py` | 29-58 | create() 添加 candidate_id 参数 | **P1** |
| `proposal_model.py` | 14-31 | 添加 candidate_id 字段定义 | **P1** |
| `evidence_evolution_engine.py` | 121+ | EvolutionResult 携带 candidate_id | **P1** |

### 5.2 可选修改的文件

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `reflection_engine.py` | _generate_proposals() 添加 candidate_id | P2 |
| `test_reflection_engine.py` | 添加 candidate_id 验证测试 | P2 |
| `test_service_layer.py` | 添加状态转换测试 | P2 |

---

## 六、候选方案对比

### 方案 A vs 方案 B

| 维度 | 方案 A（Engine 携带） | 方案 B（Service 映射） |
|------|----------------------|----------------------|
| 代码清晰度 | ✅ 高 | ⚠️ 中 |
| 修改范围 | 3 个文件 | 2 个文件 |
| 性能影响 | ✅ 无 | ✅ 无 |
| 可维护性 | ✅ 高 | ⚠️ 中 |
| 推荐度 | ⭐⭐⭐⭐ | ⭐⭐ |

**推荐**: 方案 A

---

## 七、历史 Approved Proposals 处理

### 7.1 现状

```
Total Approved: 1,042
candidate_id = NULL（当前 Schema 无此列）
无法可靠映射到 Candidate
```

### 7.2 处理原则

```
✅ 不尝试自动映射
✅ 保持 NULL
✅ 等待后续可靠来源
❌ 不使用 evidence_chain[0] 推断
❌ 不使用 entity 模糊匹配
❌ 不使用 content 推断
```

### 7.3 未来可能的恢复方式

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

## 八、Regression Test 设计

### 8.1 核心测试用例

```python
async def test_candidate_id_propagation():
    """Test: Candidate ID correctly propagated to Proposal"""
    # Arrange
    candidate = await create_candidate(workspace_id, "test_content")
    
    # Act
    proposals = await generate_proposals([candidate])
    
    # Assert
    assert len(proposals) > 0
    for proposal in proposals:
        assert proposal.get('candidate_id') == str(candidate.id)
        assert proposal.get('candidate_id') != proposal.get('evidence_chain', [None])[0]

async def test_evidence_uuid_not_used_as_candidate_id():
    """Test: Evidence UUID never used as Candidate ID"""
    candidate = await create_candidate(workspace_id, "test_content")
    evidence_uuid = "00000000-019f-xxxx-xxxx-xxxxxxxxxxxx"  # Sample evidence UUID
    
    proposals = await generate_proposals([candidate])
    
    for proposal in proposals:
        assert proposal.get('candidate_id') != evidence_uuid
        assert proposal.get('candidate_id') == str(candidate.id)

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

### 8.2 测试文件位置

```
backend/tests/test_candidate_id_propagation.py  （新建）
backend/tests/test_service_layer.py  （更新）
backend/tests/test_reflection_engine.py  （更新）
```

---

## 九、实施顺序

### Phase P0: 修复 Candidate ID 传递（必须先做）

```
Step 1: 修改 EvidenceEvolutionEngine
  → EvolutionResult.candidates 携带 candidate_id
  
Step 2: 修改 reflection_service.py:758
  → 使用正确的 candidate_id 推导
  
Step 3: 修改 _save_proposals()
  → INSERT 包含 candidate_id 字段
  
Step 4: 运行单元测试
  → 验证 candidate_id 正确性
  
Step 5: 启动 Evolution 验证
  → 观察新 Proposal 的 candidate_id
```

### Phase 1: Schema Migration（P0 修复后进行）

```
Step 1: 创建 Alembic migration
  → ALTER TABLE proposals ADD COLUMN candidate_id VARCHAR(36)
  → ADD CONSTRAINT fk_proposals_candidate
  → CREATE INDEX idx_proposals_candidate_id
  → CREATE UNIQUE INDEX idx_proposals_pending_unique
  
Step 2: 运行 migration
  → 验证历史数据兼容
  
Step 3: 更新 Proposal 模型
  → 添加 candidate_id 字段
  
Step 4: 更新 ProposalRepository
  → create() 方法添加 candidate_id 参数
  
Step 5: 运行集成测试
```

### Phase 2: 状态转换逻辑（可选）

```
Step 1: 修改 approve_proposal()
  → 添加 Candidate → confirmed 更新
  
Step 2: 修改 reject_proposal()
  → 添加 Candidate → orphaned 更新
  
Step 3: 修改 _acquire_scope()
  → 添加 NOT EXISTS pending proposal 去重
  
Step 4: 运行完整回归测试
```

---

## 十、风险评估

| 风险项 | 级别 | 缓解措施 |
|--------|------|----------|
| P0 Bug 修复引入新 bug | 中 | 完整回归测试 |
| Migration 失败 | 低 | 备份数据库 |
| 历史数据兼容 | 低 | candidate_id nullable |
| 性能影响 | 低 | 索引优化 |
| 并发问题 | 低 | 事务隔离 |

---

## 十一、结论

### P0 修复是否可以独立进行？

**是的。**

```
P0 修复（Candidate ID 传递）与 Schema Migration 可以分步进行：

Phase P0: 代码修复（不需要 Schema 变更）
  → 修改 EvidenceEvolutionEngine 输出格式
  → 修改 reflection_service.py:758
  → 修改 _save_proposals() 添加 candidate_id 参数
  → 验证新 Proposal 正确携带 candidate_id
  
Phase 1: Schema Migration（P0 验证后进行）
  → ALTER TABLE proposals ADD COLUMN candidate_id
  → 添加 FK 和索引
  → 更新模型和 Repository
```

### 是否可以进入编码？

**⚠️ 暂不能，需先确认方案**

前提条件：
1. ✅ Root Cause 已确认
2. ✅ 调用链已追踪
3. ✅ 修复方案已设计
4. ⚠️ 需要用户确认方案 A 还是方案 B
5. ⚠️ 需要用户确认是否分步实施（P0 + Schema Migration 分开）

---

**状态**: P0 Fix Plan 已完成，等待用户确认
**下一步**: 确认后开始 Phase P0 实施
