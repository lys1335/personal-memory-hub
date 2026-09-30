# Phase 20 — Final Purge Eligibility Report

## 执行摘要

**关键发现（修正）**：
1. ⚠️ **不是所有 353 个 Pending Proposals 都可以删除**
2. ✅ **其中 247 个（70%）可以安全删除**
3. ⚠️ **其中 106 个（30%）有下游依赖，需要保留**
   - 79 个有 Approved  counterparts
   - 27 个已有 MemoryNode

---

## 1. 分类结果

| 类别 | 数量 | 百分比 | 说明 |
|------|------|--------|------|
| **Safe to Delete** | 247 | 70.0% | 无 Approved  counterparts，无 MemoryNode |
| **Keep (Approved)** | 79 | 22.4% | 有 Approved  counterparts，证据已验证 |
| **Keep (MemoryNode)** | 27 | 7.6% | 已有 MemoryNode 依赖 |
| **Total** | **353** | **100%** | |

---

## 2. 时间线确认

```
最早 Pending: 2026-08-11 23:13:30
最晚 Pending: 2026-08-12 04:30:55
Evolution 运行: 2026-08-11 23:10:00 ~ 2026-08-12 04:30:00

结论：所有 353 个都产生于错误 Evolution 期间 ✅
```

---

## 3. 重复性分析

```
Total Pending:      353
Unique Chains:      14
Duplication Rate:   96.0%

Top Duplicates:
  [80x] ['00000000-019f-d00e-643d-fe7b183d7752']
  [53x] ['12ed0658-9096-11f1-9643-46894c7bcffe']
  [48x] ['12e6167c-9096-11f1-9643-46894c7bcffe']
```

---

## 4. 为什么部分 Pending 需要保留？

### 4.1 有 Approved Counterparts

**原因**：
- 同一 evidence_chain 既生成了 Pending Proposal，也生成了 Approved Proposal
- Approved Proposal 可能已经创建了 MemoryNode
- 如果删除 Pending，可能会丢失后续处理的状态

**示例**：
```
Evidence Chain: ['00000000-019f-d00e-643d-fe7b183d7752']
  - Pending Proposal A (created 23:19)
  - Approved Proposal B (created 23:25) → MemoryNode created
  - Pending Proposal C (created 23:37)
  ... 共 80 个重复
  
处理建议：
  - 保留 Approved Proposal B 及其 MemoryNode
  - 删除其他 79 个 Pending Proposals
```

### 4.2 有 MemoryNode 依赖

**原因**：
- 某些 Pending Proposal 的 evidence_chain 已经对应了 MemoryNode
- 删除 Proposal 不会删除 MemoryNode，但可能影响追溯

---

## 5. 安全删除 SQL

```sql
-- Step 1: 备份（可选但推荐）
CREATE TABLE proposals_backup_20260812 AS
SELECT * FROM proposals
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
AND status = 'pending';

-- Step 2: 安全删除（247 个）
DELETE FROM proposals
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
AND status = 'pending'
AND id NOT IN (
    -- 保留有 Approved counterparts 的 Pending
    SELECT p1.id
    FROM proposals p1
    WHERE p1.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
    AND p1.status = 'pending'
    AND EXISTS (
        SELECT 1 
        FROM proposals p2
        WHERE p2.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
        AND p2.status = 'approved'
        AND p2.evidence_chain = p1.evidence_chain
    )
)
AND id NOT IN (
    -- 保留有 MemoryNode 依赖的 Pending
    SELECT p.id
    FROM proposals p
    WHERE p.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
    AND p.status = 'pending'
    AND EXISTS (
        SELECT 1 
        FROM memory_nodes mn
        WHERE mn.workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
        AND mn.evidence_links::text = p.evidence_chain::text
    )
);

-- Step 3: 验证
SELECT COUNT(*) as remaining_pending
FROM proposals
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
AND status = 'pending';
-- 预期结果: 106
```

---

## 6. 风险矩阵

| 操作 | 风险 | 影响 | 推荐度 |
|------|------|------|--------|
| **删除 247 个 Safe Proposals** | **低** | 仅删除重复数据 | ⭐⭐⭐⭐ |
| 删除所有 353 个 | **高** | 可能丢失有依赖的数据 | ❌ |
| 保留所有 353 个 | **中** | 继续占用空间 | ⭐⭐ |

---

## 7. 最终建议

### 短期行动（建议立即执行）

```
✅ 删除 247 个 Safe to Delete 的 Pending Proposals
✅ 保留 106 个有依赖的 Pending Proposals
✅ 创建备份表 proposals_backup_20260812
```

### 中期行动（等待用户确认）

```
1. 添加 proposals.candidate_id FK（Design Gap DG-001）
2. 实现状态转换逻辑（approve → confirmed, reject → orphaned）
3. 添加 Scope 去重检查（NOT EXISTS pending proposal）
4. 修复 Evidence API bug（GET /evidences 不支持 id 参数）
```

### 长期行动

```
1. 分析 106 个保留的 Pending Proposals
2. 清理 Legacy Evidence（如果存在）
3. 优化 Evolution 算法避免重复
```

---

## 8. 回答用户问题

### Q1: 是否可以安全认定 353 个 Pending Proposal 全部是错误数据？

**回答**：**⚠️ 部分可以**

- ✅ **247 个（70%）**：可以安全认定为错误数据
- ❌ **106 个（30%）**：有下游依赖，需要保留

### Q2: 哪些 Proposal 可以明确归入本次错误运行？

**回答**：**全部 353 个**（时间戳都在错误窗口内）

### Q3: 哪些 Proposal 必须保留？

**回答**：**106 个**
- 79 个有 Approved counterparts
- 27 个有 MemoryNode 依赖

### Q4: 哪些 Proposal 无法判断？

**回答**：**0 个**（全部可以明确分类）

### Q5: 是否可以将"批量删除"作为下一阶段唯一的数据清理动作？

**回答**：**⚠️ 部分可以**

- ✅ **可以删除 247 个**（Safe to Delete）
- ❌ **不能删除全部 353 个**（106 个有依赖）

---

## 9. 总结

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 20 Final Classification                             │
├─────────────────────────────────────────────────────────────┤
│  Total Pending:                    353                     │
├─────────────────────────────────────────────────────────────┤
│  Safe to Delete:                   247 (70.0%)             │
│  Keep (has approved):               79 (22.4%)             │
│  Keep (has MemoryNode):             27 ( 7.6%)             │
├─────────────────────────────────────────────────────────────┤
│  All within error window:         YES ✅                  │
│  High duplication rate:           YES (96%)               │
│  Safe to partially delete:        YES ✅                  │
└─────────────────────────────────────────────────────────────┘
```

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**建议行动**: 等待用户确认删除 247 个 Safe Proposals
