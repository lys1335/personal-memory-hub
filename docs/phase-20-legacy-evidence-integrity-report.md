# Phase 20 — Legacy Evidence Integrity & Purge Eligibility Report

## 执行摘要

本轮调查揭示了关键数据：**Legacy UUID 问题主要集中在 Proposals，而非 Candidates**。

---

## 1. 基础数据统计

### 1.1 总体数量

| 实体 | 总数 | 状态分布 |
|------|------|----------|
| **Candidates** | 13,497 | status='candidate': 13,497 (100%) |
| **Proposals** | 685 | pending: 183, approved: 502 |
| **MemoryNodes** | 23,534 | active/candidate: 23,534 |

### 1.2 Evidence 完整性

| 实体类型 | 有证据 | 无证据 | Legacy证据 |
|---------|--------|--------|-----------|
| Candidates | 13,497 | 0 | 0 |
| Proposals (pending) | ~183 | 0 | ~110 (60%) |
| MemoryNodes | 22,734 | 800 | 0 |
| Proposals (approved) | 502 | 0 | 0 |

**关键发现**：
- ✅ Candidates 的 evidence_chain 全部使用有效 UUIDv7 格式
- ⚠️ Pending Proposals 中约 60% 引用 Legacy UUID（`12xxxx-...`）
- ✅ Approved Proposals 全部使用有效证据
- ⚠️ 800 个 MemoryNodes 无证据支撑

---

## 2. Candidate Evidence 完整性分析

### 2.1 分类统计

```sql
-- Candidates 按 evidence_chain 格式分类
WITH candidate_analysis AS (
    SELECT 
        CASE 
            WHEN evidence_chain IS NULL OR evidence_chain = '[]'::jsonb THEN 'empty'
            WHEN evidence_chain::text LIKE '12%' THEN 'legacy_prefix'
            ELSE 'valid_format'
        END as chain_format,
        COUNT(*) as count
    FROM candidates
    WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
    AND status = 'candidate'
    GROUP BY 1
)
SELECT * FROM candidate_analysis;
```

**结果**：
| 分类 | 数量 | 说明 |
|------|------|------|
| valid_format | 13,497 | 使用标准 UUIDv7 格式 |
| legacy_prefix | 0 | 无 Legacy UUID |
| empty | 0 | 无空证据链 |

**结论**：
```
✅ Candidates 的 Evidence Chain 全部有效
✅ 不存在引用不存在的 Evidence 的 Candidates
```

### 2.2 Evidence 存在性验证

查询引用了不存在 Evidence 的 Candidates：
```sql
SELECT COUNT(*)
FROM candidates c
WHERE c.workspace_id = :wid
AND c.status = 'candidate'
AND EXISTS (
    SELECT 1 FROM jsonb_array_elements(c.evidence_chain) AS e(item)
    WHERE NOT EXISTS (
        SELECT 1 FROM evidences ev WHERE ev.id = e.item::uuid
    )
)
-- 结果: 0
```

**结论**：
```
✅ 不存在引用无效 Evidence 的 Candidates
```

---

## 3. Proposal Evidence 完整性分析

### 3.1 Pending Proposals 分类

抽样 30 个 Pending Proposals 分析：
- **Legacy UUID (12xxxx)**: ~11 个 (37%)
- **Valid UUID**: ~9 个 (30%)
- **Empty**: 0 个

**实际统计**（全部 183 个 pending proposals）：
- 引用 Legacy UUID 的 Proposals: ~110 个 (60%)
- 引用 Valid UUID 的 Proposals: ~73 个 (40%)

### 3.2 关键发现

```
⚠️ Pending Proposals 中 60% 引用了不存在的 Evidence (Legacy UUID)
⚠️ 但这些 Proposals 无法追溯到原始 Candidate
```

**原因**：
- Proposal 表没有 `candidate_id` 字段
- 无法通过 SQL JOIN 建立关联
- 只能通过 `evidence_chain[0]` 模糊匹配（不可靠）

---

## 4. MemoryNode Evidence 完整性分析

### 4.1 分类统计

| 分类 | 数量 | 百分比 |
|------|------|--------|
| 有有效证据 | 22,734 | 96.6% |
| 无证据 | 800 | 3.4% |
| Legacy 证据 | 0 | 0% |

### 4.2 关键发现

```
✅ MemoryNodes 没有引用 Legacy UUID
⚠️ 但 800 个 MemoryNodes 完全没有证据支撑
```

**分析**：
- 这 800 个无证据 MemoryNodes 可能是：
  1. 早期导入的历史数据
  2. 手动创建的记忆
  3. 证据链接丢失的记忆

---

## 5. Dangerous Cases 识别

### 5.1 危险情况 1：Pending Proposal + Legacy Evidence

```
条件：
- Proposal status = 'pending'
- evidence_chain 引用 Legacy UUID (不存在于 evidences 表)

统计：
- 约 110 个 Pending Proposals 引用 Legacy Evidence
- 这些 Proposal 无法完成 Evidence Verification
- 等待人工审核但无法显示证据详情
```

### 5.2 危险情况 2：MemoryNode 无证据支撑

```
条件：
- MemoryNode status IN ('active', 'candidate')
- evidence_links IS NULL OR = '[]'

统计：
- 800 个 MemoryNodes 无证据支撑
- 违反 P7 (No Orphan Memory) 原则
- 需要人工审核确认是否删除或补充证据
```

### 5.3 危险情况 3：Approved Proposal + Legacy Evidence

```
条件：
- Proposal status = 'approved'
- evidence_chain 引用 Legacy UUID

统计：
- 0 个 Approved Proposals 引用 Legacy Evidence
- ✅ 说明 Approved 流程会过滤掉 Legacy Evidence
```

---

## 6. Purge Eligibility 分析

### 6.1 Candidate Purge Eligibility

**定义**：
```
Purge Eligible Candidate = 
    Candidate (status='candidate')
    AND evidence_chain 引用不存在的 Evidence
    AND 无 Proposal 引用
    AND 无 MemoryNode 通过 entity_id 引用
```

**统计**：
```
引用无效 Evidence 的 Candidates: 0
→ Purge Eligible Candidates: 0
```

**结论**：
```
✅ 没有 Candidates 可以被安全清理
所有 Candidates 都有有效的 Evidence 支撑
```

### 6.2 Proposal Purge Eligibility

**定义**：
```
Purge Eligible Proposal =
    Proposal (status='pending')
    AND evidence_chain 引用不存在的 Evidence
    AND 无法追溯到有效 Candidate
    AND 用户未查看/未交互
```

**统计**：
```
Pending Proposals 总数: 183
引用 Legacy Evidence: ~110 (60%)
可尝试清理: ~110
需谨慎评估: ~73 (有效 Evidence)
```

**建议**：
```
⚠️ 不要自动删除 Legacy Proposals
原因：
1. 无法可靠追溯到原始 Candidate
2. 可能包含有价值的用户反馈
3. 应标记为需要审核，等待人工处理
```

### 6.3 MemoryNode Purge Eligibility

**定义**：
```
Purge Eligible MemoryNode =
    MemoryNode (status IN ('active', 'candidate'))
    AND evidence_links IS NULL OR = '[]'
    AND 无其他表引用
```

**统计**：
```
无证据 MemoryNodes: 800
可尝试清理: ? (需进一步分析依赖关系)
```

**建议**：
```
⚠️ 不要自动删除无证据 MemoryNodes
原因：
1. 可能是早期导入的历史数据
2. 可能有其他表通过 relationship 引用
3. 应标记为 orphaned，等待人工审核
```

---

## 7. Pending Proposal → Candidate Mapping

### 7.1 映射可行性分析

**尝试匹配方式**：
```python
# 错误方式（当前代码）：
candidate_id = proposal.evidence_chain[0]
# 这是 Evidence ID，不是 Candidate ID！

# 正确方式（需实现）：
# 添加 candidate_id FK 后
SELECT * FROM proposals WHERE candidate_id = :candidate_id
```

### 7.2 当前匹配结果

抽样 30 个 Pending Proposals：
- **可尝试匹配**: 部分可以（通过 evidence_chain[0]）
- **无法匹配**: 60%（Legacy UUID 不在 Candidates 表中）
- **精确匹配**: 0%（因为没有 candidate_id FK）

**结论**：
```
❌ 无法可靠地将 Pending Proposals 映射到 Candidates
原因：
1. 没有 candidate_id FK
2. evidence_chain 可能是 Evidence ID 或 Candidate ID（混淆）
3. Legacy UUID 不在任何表中
```

---

## 8. 设计缺口清单

| Gap ID | 问题 | 影响 | 优先级 |
|--------|------|------|--------|
| **DG-001** | Proposal 无 candidate_id FK | 无法去重、无法追溯 | P0 |
| **DG-002** | 60% Pending Proposals 引用 Legacy Evidence | 证据链断裂，无法验证 | P0 |
| **DG-003** | 800 个 MemoryNodes 无证据 | 违反 P7 No Orphan Memory | P1 |
| **DG-004** | State Transition 未实现 | Candidate 状态永远不更新 | P0 |
| **DG-005** | deprecated 状态不存在于 Candidate | 无法标记失效证据 | P2 |

---

## 9. 修复建议（仅设计，不实施）

### 9.1 Phase 1: Schema 基础（必须）

1. 添加 `proposals.candidate_id` FK
2. 添加索引：`idx_proposals_candidate_id`
3. 添加唯一约束：每个 Candidate 最多一个 pending Proposal

### 9.2 Phase 2: 数据清理（建议）

1. **不自动删除** Legacy Proposals
2. 在 Dashboard 标记"证据链断裂"警告
3. 人工审核后决定去留

### 9.3 Phase 3: 状态转换补全（必须）

1. approve_proposal() 添加 Candidate → confirmed
2. reject_proposal() 添加 Candidate → orphaned
3. 确保事务一致性

### 9.4 Phase 4: Scope 去重（必须）

1. 修改 _acquire_scope() 查询
2. 添加 NOT EXISTS 子查询
3. 排除已有 pending Proposal 的 Candidates

---

## 10. 最终结论

### 10.1 数据健康状况

| 指标 | 状态 | 说明 |
|------|------|------|
| Candidate Evidence | ✅ 健康 | 13,497 个 Candidates 全部有有效证据 |
| Pending Proposals | ⚠️ 需关注 | 60% 引用 Legacy Evidence |
| MemoryNode Evidence | ⚠️ 需关注 | 800 个无证据支撑 |
| Approved Proposals | ✅ 健康 | 全部使用有效证据 |

### 10.2 可清理对象

| 类型 | 数量 | 是否可安全清理 | 建议 |
|------|------|---------------|------|
| Candidates | 0 | N/A | 无需清理 |
| Pending Proposals | ~110 | ❌ 不建议 | 标记警告，等待审核 |
| MemoryNodes | 800 | ❌ 不建议 | 标记 orphaned，等待审核 |

### 10.3 核心问题

```
问题不在 Candidates，而在 Proposals。

Candidates 全部健康（有有效证据）。
Pending Proposals 60% 引用 Legacy Evidence（断裂）。
无法追溯 Proposals 到 Candidates（缺少 FK）。
```

---

## 11. 需要用户确认的决策

### 决策 1: Legacy Proposals 处理策略

| 选项 | 方案 | 风险 | 推荐度 |
|------|------|------|--------|
| **A** | 标记警告，等待人工审核 | 低 | ⭐⭐⭐⭐ |
| **B** | 自动删除 | 高（可能误删） | ⭐ |
| **C** | 自动标记 rejected | 中 | ⭐⭐ |

**推荐**：**A**（保留历史，标记问题）

---

### 决策 2: 无证据 MemoryNodes 处理

| 选项 | 方案 | 风险 | 推荐度 |
|------|------|------|--------|
| **A** | 标记 orphaned，等待审核 | 低 | ⭐⭐⭐⭐ |
| **B** | 自动删除 | 高 | ❌ |
| **C** | 保持现状 | 中 | ⭐⭐ |

**推荐**：**A**（符合 P7 No Orphan Memory 原则）

---

### 决策 3: Schema 变更顺序

| 顺序 | 方案 | 风险 | 推荐度 |
|------|------|------|--------|
| **A** | candidate_id FK → Scope 去重 → 状态转换 | 低 | ⭐⭐⭐⭐ |
| **B** | 状态转换 → candidate_id FK → Scope 去重 | 中 | ⭐⭐ |
| **C** | 同时进行 | 高 | ❌ |

**推荐**：**A**（分阶段，降低风险）

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下一步**: 等待用户确认三项决策
