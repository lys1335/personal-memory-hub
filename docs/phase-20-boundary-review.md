# Phase 20 — Pre-Implementation Boundary Review

## 执行摘要

本轮 READ-ONLY 调查确认了四个关键边界问题：
1. **Proposal deprecated 状态不存在** — 需设计替代方案
2. **Legacy Evidence Candidate 不能自动 orphaned** — 需分类处理
3. **事务边界不完整** — approved 不更新 candidate，rejected 不标记 orphaned
4. **Scope 规则符合设计预期**

---

## 1. Proposal 合法 Status 检查

### 1.1 数据库 Schema

**Proposals 表列**：
```
id, workspace_id, type, source_level, target_level,
entity, evidence_chain, confidence, summary, content,
status, approved_by, approved_at, rejected_reason,
created_at, updated_at
```

**❌ 没有 candidate_id 字段**（需添加）

### 1.2 现有 Status 值

**代码定义**（proposal_repository.py:55）：
```python
"status": "pending"  # 创建时固定为 pending
```

**实际使用**（reflection_service.py）：
- `pending` — 创建 Proposal
- `approved` — approve_proposal() 更新
- `rejected` — reject_proposal() 更新

**数据库实际值**：
```sql
SELECT DISTINCT status FROM proposals;
-- 结果: pending, approved, rejected
```

### 1.3 deprecated 状态分析

**❌ deprecated 不存在于**：
- Schema（无此值定义）
- Repository（无此状态处理）
- Service（无此状态逻辑）
- API（无此状态过滤）
- 前端（无此状态显示）

**结论**：
```
不能新增 deprecated 状态作为临时方案。
需要使用现有合法 status 设计隔离方案。
```

### 1.4 替代方案设计

**选项 A：保留原样，人工审核**
- 断裂证据的 Proposal 保持 `pending`
- Dashboard 显示"证据链断裂"警告
- 用户手动决定删除或保留

**选项 B：使用现有 status 表达**
- 标记为 `rejected`，reason = "evidence_chain_broken"
- 但这会错误表达"用户已拒绝"的语义

**推荐方案：选项 A**
- 不修改 Proposal status
- 在 Dashboard 层面增加"证据完整性"标记
- 等待人工审核决定后续

---

## 2. Legacy Evidence Candidate 分类调查

### 2.1 调查范围

**目标**：约 8,829 个引用 Legacy Evidence UUID 的 Candidates

**Legacy UUID 特征**：
- 格式：`12xxxxxx-xxxx-1xxx-...`（非 UUIDv7）
- 数据库 evidences 表：全部为 `00000000-019f-...` 格式

### 2.2 分类查询设计

**Group A: evidence_chain 全部不存在**
```sql
SELECT c.id, c.content
FROM candidates c
WHERE c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM jsonb_array_elements(c.evidence_chain) AS e(id)
    JOIN evidences ev ON ev.id = e.id::uuid
)
AND c.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219';
```

**Group B: evidence_chain 部分存在**
```sql
SELECT c.id, c.content,
       COUNT(DISTINCT CASE WHEN e.id IS NOT NULL THEN 1 END) as valid_count,
       COUNT(*) as total_count
FROM candidates c
LEFT JOIN LATERAL jsonb_array_elements(c.evidence_chain) AS e(id) ON true
LEFT JOIN evidences ev ON ev.id = e.id::uuid
WHERE c.status = 'candidate'
AND c.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
GROUP BY c.id, c.content
HAVING COUNT(CASE WHEN e.id IS NOT NULL THEN 1 END) > 0
AND COUNT(CASE WHEN e.id IS NOT NULL THEN 1 END) < COUNT(*);
```

**Group C: 已有 pending Proposal**
```sql
SELECT c.id, c.content
FROM candidates c
JOIN proposals p ON p.evidence_chain::text LIKE '%' || c.id || '%'
WHERE c.status = 'candidate'
AND p.status = 'pending'
AND c.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219';
```

**Group D: 没有 Proposal**
```sql
SELECT c.id, c.content
FROM candidates c
WHERE c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p
    WHERE p.evidence_chain::text LIKE '%' || c.id || '%'
    AND p.status = 'pending'
)
AND c.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219';
```

### 2.3 能否可靠恢复证据关系？

**答案：不能**

**原因**：
1. Legacy UUID 格式与现有 UUIDv7 完全不同
2. evidences 表无对应记录
3. 无法通过 entity/content 反推（多义性）
4. 历史数据可能已丢失

### 2.4 能否确认为历史导入数据？

**答案：高度可能，但无法 100% 确认**

**证据**：
- Legacy UUID `12xxxx-...` 格式不符合当前 UUIDv7 规范
- 数据库中所有 evidences 都是 `000000-019f-...` 格式
- 推测来源：早期导入、测试数据、或旧版本系统

**结论**：
```
不能自动 orphaned，需要人工审核确认数据来源。
建议：保留数据，标记为 "evidence_broken"，等待用户决策。
```

---

## 3. 事务边界检查

### 3.1 approve_proposal 事务流

**代码位置**：reflection_service.py:225-360

```python
async with engine.begin() as conn:  # ← 开启事务
    # Step 1: 更新 proposal status
    await conn.execute(text("""
        UPDATE proposals SET status = 'approved', ...
    """))
    
    # Step 2: 创建 memory_node
    await conn.execute(text("""
        INSERT INTO memory_nodes (...)
    """))
    
    # Step 3: 创建 relationships
    for candidate_id in evidence_target_ids:
        # ...
    
    # ❌ 缺失：没有更新 candidates.status
    # 应该在此处添加：
    # UPDATE candidates SET status = 'confirmed' WHERE id = :candidate_id
    
# 事务提交（implicit commit）
```

**问题**：
- ✅ Proposal 更新和 MemoryNode 创建在同一事务（一致）
- ❌ Candidate 状态未更新（设计缺口）
- ⚠️ 如果 MemoryNode 创建失败，Proposal 会回滚到 pending（正确）
- ⚠️ 但如果后续需要补充 Candidate 更新，需要额外事务

### 3.2 reject_proposal 事务流

**代码位置**：reflection_service.py:450-470

```python
async with engine.begin() as conn:  # ← 开启事务
    await conn.execute(text("""
        UPDATE proposals SET status = 'rejected', rejected_reason = :reason
        WHERE id = :id AND workspace_id = :workspace_id
    """))
    
    # ❌ 缺失：没有更新 candidates.status
    # 应该在此处添加：
    # UPDATE candidates SET status = 'orphaned' WHERE id = :candidate_id
    
# 事务提交
```

**问题**：
- ✅ Proposal 更新成功
- ❌ Candidate 状态未更新（设计缺口）
- 现有设计声称 "rejected → orphaned"，但代码未实现

### 3.3 事务一致性评估

| 操作 | Proposal | MemoryNode | Candidate | 一致性 |
|------|----------|------------|-----------|--------|
| Approve | ✅ approved | ✅ created | ❌ 仍为 candidate | **不一致** |
| Reject | ✅ rejected | - | ❌ 仍为 candidate | **不一致** |

**设计缺口**：
1. approve 成功后，Candidate 应变为 confirmed
2. reject 成功后，Candidate 应变为 orphaned
3. 当前代码未实现这两步

---

## 4. Evolution Scope 规则验证

### 4.1 当前 Scope 查询

```python
# reflection_service.py:1080-1090
WHERE workspace_id = :workspace_id
AND status IN ('candidate', 'pending')
ORDER BY created_at ASC
LIMIT :limit
```

### 4.2 三条路径验证

**路径 A: Proposal pending → Evolution #2**
```
Candidate A (candidate) 
  → Proposal #1 (pending)
  → Evolution #2
  → _acquire_scope() 查询: status='candidate' ✓
  → Candidate A 仍在 scope（无去重）❌
  → 生成 Proposal #2（重复）❌
```

**路径 B: Proposal rejected → Evolution #3**
```
Candidate A (candidate)
  → Proposal #1 (rejected)
  → Candidate 状态未变（仍为 candidate）❌
  → Evolution #3
  → _acquire_scope() 查询: status='candidate' ✓
  → Candidate A 仍在 scope（无变化）
  → 可能再次生成 Proposal ❌
```

**路径 C: Proposal approved → MemoryNode created → Evolution #4**
```
Candidate A (candidate)
  → Proposal #1 (approved)
  → MemoryNode created
  → Candidate 状态未变（仍为 candidate）❌
  → Evolution #4
  → _acquire_scope() 查询: status='candidate' ✓
  → Candidate A 仍在 scope（重复处理）❌
```

### 4.3 Scope 规则设计

**新规则**（需实现）：
```sql
SELECT * FROM candidates c
WHERE c.workspace_id = :wid
AND c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p
    WHERE p.candidate_id = c.id
    AND p.status = 'pending'
)
ORDER BY c.created_at ASC
LIMIT :limit;
```

**注意**：此规则依赖 `candidate_id` FK，需先实施 Schema 变更。

---

## 5. Design Gap 清单

| Gap ID | 问题 | 位置 | 影响 |
|--------|------|------|------|
| **DG-001** | proposals 无 candidate_id FK | schema | 无法去重 |
| **DG-002** | approve 不更新 candidate status | service | 状态不一致 |
| **DG-003** | reject 不更新 candidate status | service | 状态不一致 |
| **DG-004** | Scope 无去重检查 | service | 重复 Evolution |
| **DG-005** | deprecated status 不存在 | schema | 无法标记失效证据 |

---

## 6. 需要用户确认的决策

### 决策 1: Legacy Evidence 候选项处理

**问题**：8,829 个引用不存在 Evidence 的 Candidates 如何处理？

| 选项 | 方案 | 风险 | 推荐度 |
|------|------|------|--------|
| **A** | 保留并等待人工审核 | 低 | ⭐⭐⭐ |
| **B** | 自动标记 orphaned | 高（可能误删） | ⭐ |
| **C** | 批量删除 | 极高（数据丢失） | ❌ |

**推荐**：选项 A
- 保留数据，不自动修改状态
- 在 Dashboard 标记"证据链断裂"
- 等待人工审核决定后续

---

### 决策 2: 事务边界补全

**问题**：approve/reject 后是否需要立即更新 Candidate 状态？

| 选项 | 方案 | 事务影响 | 推荐度 |
|------|------|----------|--------|
| **A** | 同一事务内更新 | 强一致性 | ⭐⭐⭐⭐ |
| **B** | 异步更新 | 最终一致性 | ⭐⭐ |
| **C** | 暂不更新 | 状态延迟 | ⭐ |

**推荐**：选项 A
- 在 approve_proposal() 和 reject_proposal() 中添加 Candidate 状态更新
- 保持事务完整性

---

### 决策 3: 92 个 Pending Proposals 处理

**问题**：现有 92 个 pending proposals 如何分类？

**分类标准**：
1. evidence_chain 全部有效 → 保留，迁移 candidate_id
2. evidence_chain 部分有效 → 保留，标记 warning
3. evidence_chain 全部断裂 → 标记 deprecated（需定义替代方案）

**推荐方案**：
```
使用 existing status 表达：
- 断裂的 Proposal 保持 pending，但添加 metadata 标记
- Dashboard 显示"证据链不完整"警告
- 等待人工审核
```

---

### 决策 4: Schema 变更顺序

**问题**：是否需要先添加 candidate_id 再实施其他变更？

| 顺序 | 方案 | 风险 | 推荐度 |
|------|------|------|--------|
| **A** | candidate_id → Scope 去重 → 状态转换 | 低 | ⭐⭐⭐⭐ |
| **B** | 状态转换 → candidate_id → Scope 去重 | 中 | ⭐⭐ |
| **C** | 同时进行 | 高（回滚困难） | ❌ |

**推荐**：选项 A
- 分阶段实施，降低风险
- 每阶段可独立验证

---

## 7. 实施路线图（建议）

### Phase 1: Schema 基础（1 天）
1. 添加 `proposals.candidate_id` 字段
2. 添加索引和唯一约束
3. 数据迁移脚本（模糊匹配）

### Phase 2: 状态转换补全（1 天）
1. approve_proposal() 添加 Candidate 更新
2. reject_proposal() 添加 Candidate 更新
3. 单元测试

### Phase 3: Scope 去重（0.5 天）
1. 修改 _acquire_scope() 查询
2. 添加 NOT EXISTS 子查询
3. 性能测试

### Phase 4: 数据清理（可选）
1. 分析 92 个 pending proposals
2. 标记断裂证据的 Proposal
3. 人工审核后决定去留

---

## 8. 最终约束检查

### 已遵守的约束
- ✅ 未引入 processed 状态
- ✅ 未修改现有四状态定义
- ✅ 未改变既有生命周期语义
- ✅ 未执行任何数据库修改
- ✅ 未修改代码
- ✅ 未运行 Evolution
- ✅ 未删除任何 Proposal 或 Candidate

### 待用户确认的事项
- ⏳ 决策 1: Legacy Evidence Candidates 处理策略
- ⏳ 决策 2: 事务边界补全方案
- ⏳ 决策 3: 92 个 Pending Proposals 分类策略
- ⏳ 决策 4: Schema 变更实施顺序

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下一步**: 等待用户确认四项决策后进入 Implementation
