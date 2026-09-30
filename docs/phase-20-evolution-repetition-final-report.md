# Phase 20 — Evolution Repetition & Mapping Final Report

## 执行摘要

本轮调查**确认了核心设计缺陷**：
1. ✅ **Evolution 每 12 分钟重复处理相同 Candidates**
2. ✅ **Pending Proposals 从 92 增长到 353（5小时内 +263%）**
3. ✅ **相同 Evidence Chain 被重复使用 80+ 次**
4. ✅ **Candidates 状态永不更新，永远停留在 scope 中**

---

## 1. Evolution Repetition 分析

### 1.1 执行频率

```
日志显示：
2026-08-12 00:33:13 - Scope acquired: 200 candidates
2026-08-12 00:45:05 - Scope acquired: 200 candidates
2026-08-12 00:57:26 - Scope acquired: 200 candidates
...
间隔: 约 12 分钟/次
```

**最近 22 轮 Evolution（过去 5 小时）**：
- 每轮获取：200 candidates
- 每轮生成：~50 proposals
- 总提案：~1,100 proposals（但实际只有 353 pending + 973 approved = 1,326）

### 1.2 重复 Candidate 分析

**关键发现**：

| 指标 | 数值 |
|------|------|
| Total Candidates | 14,283 |
| Scope per round | 200 |
| Oldest candidates created | 2026-08-05 |
| Candidates still in 'candidate' status | 14,283 (100%) |

**重复率计算**：
- 每轮处理 200 个 oldest candidates
- Candidates 状态不更新
- **重复率 = 100%**（同一批 200 个被重复处理）

### 1.3 证据链重复使用

```
Top duplicate evidence chains (pending proposals):
  [80x] ['00000000-019f-d00e-643d-fe7b183d7752']
        First: 2026-08-11 23:19, Last: 2026-08-12 04:30
        → 同一证据链被生成 80 次！
  
  [53x] ['12ed0658-9096-11f1-9643-46894c7bcffe']
        → Legacy UUID 被重复引用 53 次
  
  [48x] ['12e6167c-9096-11f1-9643-46894c7bcffe']
        → Legacy UUID 被重复引用 48 次
```

**结论**：
```
❌ Evolution 反复处理同一批 Candidate
❌ 同一 Evidence Chain 生成多个 Proposal
❌ 没有去重机制，没有状态转换
```

---

## 2. LIMIT Starvation 分析

### 2.1 当前 Scope 查询

```sql
SELECT ... FROM candidates
WHERE workspace_id = :wid
AND status IN ('candidate', 'pending')
ORDER BY created_at ASC
LIMIT 200
```

### 2.2 饥饿验证

**数据**：
- Total candidates: 14,283
- Scope per round: 200
- Processed per round: 0（状态不变）
- Round interval: 12 minutes

**计算**：
```
Round 1: 处理 candidates 1-200
Round 2: 处理 candidates 1-200 ← 重复！
Round 3: 处理 candidates 1-200 ← 重复！
...
Round N: 处理 candidates 1-200 ← 永远循环
```

**结论**：
```
✅ 确认存在"头部饥饿"问题
❌ 新创建的 Candidates 永远无法进入 Evolution
❌ 只有最早的 200 个 Candidates 被反复处理
```

---

## 3. Candidate Coverage 分析

### 3.1 覆盖统计

| 类别 | 数量 | 百分比 |
|------|------|--------|
| Total Candidates | 14,283 | 100% |
| In scope (oldest 200) | 200 | 1.4% |
| Never in scope | 14,083 | 98.6% |
| Repeatedly processed | 200 | 1.4% |

### 3.2 覆盖率计算

```
假设每天运行 120 轮（24小时 × 60分钟 / 12分钟）
每天处理候选：200 × 120 = 24,000（但实际只有 14,283 个）
实际上：只有 200 个被处理，其余 14,083 个从未被处理
```

**结论**：
```
❌ Evolution 覆盖率极低（1.4%）
❌ 98.6% 的 Candidates 从未被处理
```

---

## 4. Proposal Growth 分析

### 4.1 增长模式

```
时间          | Pending | Approved | 新增
-------------|---------|----------|-----
23:00 (Day1) | 49      | 177      | -
00:00        | 74      | 185      | +25
01:00        | 60      | 140      | +200
02:00        | 65      | 170      | +235
03:00        | 67      | 184      | +251
04:00        | 38      | 117      | +155 (partial)
-------------|---------|----------|-----
Total        | 353     | 973      | 1,326
```

### 4.2 增长原因

**为什么 Pending 从 92 增长到 353？**

```
原因 1: 每轮生成 ~50 proposals，大部分 pending（confidence < 0.9）
原因 2: Approved 的 proposals 被消耗，但 Pending 不断积累
原因 3: 没有去重机制，相同 Evidence 生成多个 Proposal
原因 4: 同一批 Candidate 被重复处理
```

**净增长计算**：
```
每小时新增 proposals: ~50
每小时批准 proposals: ~30（假设 60% auto-approve）
每小时净增长: ~20 pending
5 小时净增长: ~100 pending
实际增长: 353 - 92 = 261（部分来自历史积累）
```

---

## 5. Pending Proposal Mapping 分析

### 5.1 分类统计

| 分类 | 数量 | 百分比 |
|------|------|--------|
| Legacy UUID (12xxxx) | 242 | 68.5% |
| Valid UUID | 111 | 31.5% |
| Empty | 0 | 0% |
| **Total** | **353** | **100%** |

### 5.2 映射可行性

**尝试映射方式**：
```python
# 方式 1: 通过 evidence_chain[0] 匹配（错误）
candidate_id = proposal.evidence_chain[0]
# 问题：这是 Evidence ID，不是 Candidate ID

# 方式 2: 通过 entity 匹配（模糊）
SELECT * FROM candidates WHERE entity_id = ?
# 问题：多个 candidate 可能有相同 entity
```

**映射结果**：
```
Can reliably map: 0（没有 candidate_id FK）
Cannot map: 353（100%）
```

**结论**：
```
❌ 无法将 Pending Proposals 映射到 Candidates
原因：缺少 candidate_id FK（Design Gap DG-001）
```

---

## 6. 为什么统计数字变化不明显

### 6.1 Candidates 不减少的原因

```
问题：为什么 14,283 个 Candidates 在多轮 Evolution 后没有减少？

答案：
1. Proposal 生成不改变 Candidate status
2. Proposal approved 不更新 Candidate → confirmed
3. Proposal rejected 不更新 Candidate → orphaned
4. 状态转换代码完全缺失
```

**代码证据**：
```python
# reflection_service.py:approve_proposal()
async with engine.begin() as conn:
    await conn.execute(text("UPDATE proposals SET status = 'approved'..."))
    await conn.execute(text("INSERT INTO memory_nodes..."))
    # ❌ 没有 UPDATE candidates SET status = 'confirmed'

# reflection_service.py:reject_proposal()
async with engine.begin() as conn:
    await conn.execute(text("UPDATE proposals SET status = 'rejected'..."))
    # ❌ 没有 UPDATE candidates SET status = 'orphaned'
```

### 6.2 MemoryNodes 增长缓慢的原因

```
问题：为什么 24,005 个 MemoryNodes 变化缓慢？

答案：
1. Evolution 主要生成 Pending Proposals
2. 只有 confidence >= 0.9 的 Proposals 被 auto-approve
3. Auto-approve 创建 MemoryNode
4. 大部分 Proposals 保持 pending（confidence < 0.9）
```

**数据验证**：
```
Total proposals: 1,326
Approved: 973 (73%)
Pending: 353 (27%)
```

### 6.3 Pending Proposals 增长的原因

```
问题：为什么 Pending 从 92 增长到 353？

答案：
1. 每轮生成 ~50 proposals
2. 部分 proposals 被 auto-approve（创建 MemoryNode）
3. 剩余 proposals 保持 pending
4. 没有机制清理或消费 pending proposals
```

---

## 7. 最终设计 implication

### 7.1 必须立即修复的问题

| 优先级 | 问题 | 影响 | 建议行动 |
|--------|------|------|---------|
| **P0** | 缺少 candidate_id FK | 无法去重、无法追溯 | 立即添加 FK |
| **P0** | 状态转换缺失 | Candidate 永远不更新 | 添加状态转换代码 |
| **P0** | Scope 无去重检查 | 重复处理同一批 Candidate | 添加 NOT EXISTS 子查询 |
| **P1** | Legacy Evidence | 68.5% Pending 无法验证 | 标记警告，人工审核 |
| **P1** | 头部饥饿 | 98.6% Candidates 从未处理 | 优化 Scope 查询 |

### 7.2 是否应该暂停 Evolution？

**建议**：
```
⚠️ 应该考虑暂停 Evolution，直到以下修复完成：
1. 添加 candidate_id FK
2. 实现状态转换逻辑
3. 添加 Scope 去重检查

理由：
- 当前 Evolution 正在产生大量重复、无效的 Proposals
- 68.5% 的 Pending Proposals 引用不存在的 Evidence
- 同一批 Candidate 被重复处理，浪费计算资源
- Pending Proposals 持续膨胀（92 → 353 in 5 hours）
```

**暂停条件**：
```
如果：
1. candidate_id FK 未添加
2. 状态转换未实现
3. Scope 去重未实现

则：
Evolution 每 12 分钟产生 ~50 个无效 Proposals
5 小时产生 ~250 个新增 Pending
预计 24 小时产生 ~1,200 个新增 Pending
```

---

## 8. 完整数据总结

### 8.1 当前系统状态

```
Candidates:
  Total: 14,283
  Status: 100% 'candidate'
  Evidence: 100% valid
  Processed: 0%（状态未更新）

Proposals:
  Total: 1,326
  Pending: 353 (27%)
  Approved: 973 (73%)
  Legacy evidence: 68.5% of pending

MemoryNodes:
  Total: 24,005
  With evidence: 23,205 (96.7%)
  Without evidence: 800 (3.3%)
```

### 8.2 Evolution 效率

```
每轮处理: 200 candidates
每轮生成: ~50 proposals
重复率: 100%（同一批 200 个）
覆盖率: 1.4%（200/14,283）
有效提案率: ~30%（剩余 70% 重复或无效）
```

---

## 9. 需要用户确认的决策

### 决策 1: 是否暂停 Evolution？

| 选项 | 方案 | 推荐度 |
|------|------|--------|
| **A** | 立即暂停，等待修复完成 | ⭐⭐⭐⭐ |
| **B** | 继续运行，接受浪费 | ⭐ |
| **C** | 降低频率（如 1 小时/次） | ⭐⭐ |

**推荐**：**A**（避免资源浪费和数据污染）

---

### 决策 2: Legacy Proposals 处理

| 选项 | 方案 | 推荐度 |
|------|------|--------|
| **A** | 标记警告，等待人工审核 | ⭐⭐⭐⭐ |
| **B** | 批量删除 | ⭐ |
| **C** | 尝试匹配 Candidate | ⭐⭐ |

**推荐**：**A**（保留历史，标记问题）

---

### 决策 3: 实施顺序

| 顺序 | 方案 | 推荐度 |
|------|------|--------|
| **A** | candidate_id FK → 状态转换 → Scope 去重 | ⭐⭐⭐⭐ |
| **B** | 其他顺序 | ⭐⭐ |

**推荐**：**A**（分阶段，降低风险）

---

## 10. 结论

### 核心问题

```
Evolution 系统设计存在根本性缺陷：

1. 缺少 Candidate-Proposal 关联（candidate_id FK）
2. 缺少状态转换逻辑（candidate → confirmed/orphaned）
3. 缺少 Scope 去重机制（NOT EXISTS pending proposal）

后果：
- 100% 重复处理同一批 Candidate
- 98.6% Candidate 从未被处理
- Pending Proposals 持续膨胀
- 68.5% Pending 引用无效 Evidence
```

### 建议行动

**立即**：
1. 暂停 Evolution Scheduler
2. 分析 353 个 Pending Proposals
3. 标记 Legacy Evidence Proposals

**短期**：
1. 添加 proposals.candidate_id FK
2. 实现状态转换代码
3. 添加 Scope 去重逻辑

**长期**：
1. 清理历史数据
2. 优化 Scope 查询（避免饥饿）
3. 添加 Proposal 去重机制

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下一步**: 等待用户确认三项决策
