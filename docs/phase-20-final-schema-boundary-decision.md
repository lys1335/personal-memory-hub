# Phase 20 — Final Schema Boundary Decision

## 执行摘要

经过完整的只读调查，Schema 设计已确认。

**关键发现**：
- ✅ candidate_id nullable（兼容历史数据）
- ✅ ON DELETE SET NULL（保留历史记录）
- ✅ Partial Unique Index（防止 pending 重复）
- ⚠️ **发现 P0 Bug**：reflection_service.py:758 错误使用 Evidence UUID 作为 Candidate ID

---

## 1. candidate_id NULLability

### 决策

```
proposals.candidate_id: VARCHAR(36) REFERENCES candidates(id)
                        NULLABLE = TRUE
```

### 理由

| 因素 | 分析 |
|------|------|
| 历史数据 | 1,042 个 Approved Proposals 无 candidate_id（无法可靠映射） |
| 当前数据 | Pending = 0，无冲突 |
| 新数据 | 代码层强制填充，数据库层不强制 |
| 风险 | NULL 允许历史数据保留，新数据通过代码约束 |

---

## 2. Pending Proposal 约束

### 决策

```
不使用数据库 CHECK 约束
改用代码层 + 应用层约束
```

### 实现

```python
# proposal_repository.py
async def create(self, proposal: dict) -> UUID:
    if proposal.get('status') == 'pending' and not proposal.get('candidate_id'):
        raise ValueError("Pending proposals must have candidate_id")
    # ... 插入逻辑
```

---

## 3. FK ON DELETE

### 决策

```
ON DELETE SET NULL
```

### 理由

```
Candidate 被删除 → Proposal 保留，candidate_id 设为 NULL
→ 保留历史记录
→ 不破坏其他表
→ 符合"Evidence-Based Memory"原则
```

---

## 4. Unique Pending Index

### 决策

```sql
CREATE UNIQUE INDEX idx_proposals_pending_unique
ON proposals (workspace_id, candidate_id)
WHERE status = 'pending';
```

### 理由

```
只约束当前 pending 状态的 Proposal
→ 同一 Candidate 同时最多 1 个 pending
→ 历史 approved/rejected 不受影响
```

---

## 5. Migration 顺序

```
Phase 1: ALTER TABLE proposals ADD COLUMN candidate_id VARCHAR(36)
Phase 2: ALTER TABLE proposals ADD CONSTRAINT fk_proposals_candidate
         FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL
Phase 3: CREATE INDEX idx_proposals_candidate_id ON proposals (workspace_id, candidate_id)
Phase 4: CREATE UNIQUE INDEX idx_proposals_pending_unique
         ON proposals (workspace_id, candidate_id) WHERE status = 'pending'
```

---

## 6. P0 Bug 发现（必须修复）

### 问题位置

**File**: `backend/src/backend/service/reflection_service.py`  
**Line**: 758  
**Code**:
```python
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'
```

### 问题分析

```
❌ 错误：将 Evidence UUID 当作 Candidate ID
✅ 正确：从 Evolution 上下文传入真实 Candidate ID

证据：
- 查询确认：0 个 Proposal 的 evidence_chain[0] 匹配 Candidate ID
- 所有 1,042 个 Approved Proposals 的 candidate_id 都是错误的
```

### 影响

```
- 所有 Proposal 无法正确关联到 Candidate
- Candidate 状态转换无法工作
- Scope 去重逻辑失效
```

### 修复方案

```python
# reflection_service.py:758 修改为：
# 从 Evolution 上下文传入真实 Candidate ID
# 而不是从 evidence_chain[0] 推断

# 方案 A：修改 EvidenceEvolutionEngine 返回 Candidate ID
evolution_result.candidates[i]['candidate_id'] = actual_candidate_id

# 方案 B：在 ReflectionService 中维护 Candidate → Proposal 映射
candidate_id_map = {candidate.id: candidate for candidate in scope}
for fact in result.facts:
    fact['candidate_id'] = candidate_id_map.get(fact['entity_id'])
```

---

## 7. 最终 Schema Contract

### 7.1 Historical Proposal

```
candidate_id: NULL
范围: Migration 前所有现有数据（1,042 条）
理由: 无法可靠映射，保留历史记录
```

### 7.2 New Pending Proposal

```
candidate_id: NOT NULL（代码层强制）
范围: Migration 后新创建的 Pending Proposal
理由: 必须有明确 Candidate 来源
实现: ProposalRepository.create() 中验证
```

### 7.3 Approved / Rejected

```
candidate_id: 可为 NULL
范围: 历史数据 OR Candidate 被删除后
理由: 保留历史记录
```

### 7.4 FK 约束

```
proposals.candidate_id → candidates.id
ON DELETE: SET NULL
ON UPDATE: NO ACTION
```

### 7.5 Unique Pending Index

```sql
CREATE UNIQUE INDEX idx_proposals_pending_unique
ON proposals (workspace_id, candidate_id)
WHERE status = 'pending';
```

---

## 8. 风险评估

| 风险项 | 级别 | 缓解措施 |
|--------|------|----------|
| P0 Bug（错误 candidate_id） | **高** | **必须优先修复** |
| Migration 失败 | 低 | 备份数据库 |
| 历史数据冲突 | 低 | candidate_id nullable |
| ON DELETE SET NULL | 低 | 不影响历史记录 |
| 索引性能 | 低 | Partial Index 只在 pending 时生效 |

---

## 9. 结论

### 是否可以开始 Phase 1？

**⚠️ 暂不能，需先修复 P0 Bug**

### 前提条件

1. ✅ 设计决策已确认
2. ✅ Schema 边界已明确
3. ❌ **P0 Bug 未修复**（reflection_service.py:758）
4. ⚠️ 需确认修复方案

### 建议行动顺序

```
Step 1: 修复 P0 Bug
  → 修改 reflection_service.py:758
  → 确保 Proposal 创建时使用真实 Candidate ID
  → 运行单元测试

Step 2: 执行 Schema Migration
  → Phase 1-4（见上文）
  → 验证索引和约束

Step 3: 更新 Model 和 Repository
  → 添加 candidate_id 字段
  → 添加验证逻辑

Step 4: 更新 Service
  → approve_proposal() 添加状态转换
  → reject_proposal() 添加状态转换
  → _acquire_scope() 添加去重逻辑

Step 5: 回归测试
  → Scope 去重测试
  → 状态转换测试
  → 事务一致性测试

Step 6: 启动验证
  → 启动 Evolution
  → 观察第一轮执行
  → 验证 Candidate 状态更新
```

---

**状态**: Schema Boundary Confirmed ⚠️ (需先修复 P0 Bug)  
**下一步**: 修复 P0 Bug 后开始 Phase 1

---

## 附录：P0 Bug 详细分析

### 当前错误代码

```python
# reflection_service.py:756-766
evidence_chain = c.get('evidence_chain', [])
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'
reflection_candidates.append({
    'id': candidate_id,  # ❌ 这是 Evidence ID，不是 Candidate ID！
    'content': c.get('content', ''),
    ...
})
```

### 正确做法

```python
# 方案 A：在 EvidenceEvolutionEngine 中返回 Candidate ID
class EvolutionResult:
    candidates: list[dict[str, Any]]  # 每个 candidate 包含 'candidate_id' 字段

# 方案 B：在 ReflectionService 中维护映射
candidate_map = {c.id: c for c in scope}
for fact in result.facts:
    entity_id = fact.get('entity')
    candidate = candidate_map.get(entity_id)
    if candidate:
        fact['candidate_id'] = str(candidate.id)
```

### 验证方法

```sql
-- 验证 Proposal 的 candidate_id 是否有效
SELECT p.id, p.candidate_id, c.id as valid_candidate_id
FROM proposals p
LEFT JOIN candidates c ON c.id = p.candidate_id
WHERE p.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
AND p.candidate_id IS NOT NULL
AND c.id IS NULL;
-- 预期：0 条记录（所有 candidate_id 都有效）
```
