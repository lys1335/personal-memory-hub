# Phase 20 — Evolution Scope / Proposal Deduplication Analysis

## 执行摘要

本轮核查确认了一个**严重的架构缺陷**：
**Proposal 与 Candidate 之间没有正式关联，导致无法判断"是否已有 pending Proposal"**

---

## 1. 设计规定

### 1.1 设计文档中的 Scope 排除规则

**搜索范围**：
- `docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md`
- `docs/02_Data_Model/*.md`
- 所有设计文档

**结论**：
```
设计文档没有定义该机制。
```

设计文档定义了 Evolution Workflow：
```
Observation Pool → Candidate Discovery → Pattern Proposal → Evidence Verification → Pattern (confirmed)
```

但**没有定义**：
- 已有 pending Proposal 的 Candidate 是否应排除出 Scope
- Proposal 生成后 Candidate 应如何标记
- 如何防止重复生成 Proposal

---

## 2. 当前代码实际行为

### 2.1 `_acquire_scope()` 实现

**代码位置**：`reflection_service.py:1080-1090`

```python
result = await conn.execute(text("""
    SELECT ... FROM candidates
    WHERE workspace_id = :workspace_id
    AND status IN ('candidate', 'pending')
    ORDER BY created_at ASC
    LIMIT :limit
"""))
```

**关键问题**：
1. **没有检查 Proposal 存在性** — 不查询 `proposals` 表
2. **没有检查 Candidate 是否已有 pending Proposal**
3. **只按 `status` 和 `created_at` 排序**
4. **无条件排除已有 Proposal 的 Candidate**

### 2.2 为什么再次取得这些 Candidate

**原因**：
```python
# Candidate 状态从未更新
# 永远是 'candidate'
# WHERE status IN ('candidate', 'pending') 永远匹配
```

**数据验证**：
```sql
SELECT status, COUNT(*) FROM candidates GROUP BY status;
-- 结果: candidate: 13,146

SELECT status, COUNT(*) FROM proposals GROUP BY status;
-- 结果: pending: 92, approved: 291+
```

**结论**：所有 Candidate 都满足 `status = 'candidate'`，每次都进入 Scope。

---

## 3. Proposal 与 Candidate 的关联关系

### 3.1 数据库 Schema 检查

**Proposals 表列**：
```
id, workspace_id, type, source_level, target_level,
entity, evidence_chain, confidence, summary, content,
status, approved_by, approved_at, rejected_reason,
created_at, updated_at
```

**Candidates 表列**：
```
id, workspace_id, entity_id, area_id, content,
candidate_type, evidence_source, evidence_id, evidence_chain,
evidence_count, evidence_strength, status, ingested_by,
ingestion_timestamp, verified_at, verified_by,
modified_by, modification_reason, created_at, updated_at, source_level
```

### 3.2 关键发现

**❌ Proposals 表没有 `candidate_id` 字段**

```sql
-- 验证结果
SELECT COUNT(*) FROM information_schema.columns 
WHERE table_name = 'proposals' AND column_name = 'candidate_id';
-- 结果: 0 (不存在)
```

### 3.3 代码中的"伪关联"

**代码位置**：`reflection_service.py:756-758`

```python
# 错误做法：用 evidence_chain[0] 作为 candidate_id
evidence_chain = c.get('evidence_chain', [])
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'
reflection_candidates.append({
    'id': candidate_id,  # ← 这不是真正的 Candidate ID！
    ...
})
```

**问题**：
1. `evidence_chain[0]` 是 Evidence ID，不是 Candidate ID
2. 如果 evidence_chain 为空，使用 `entity_{i}` 作为假 ID
3. 这导致无法通过 Proposal 回溯到原始 Candidate

### 3.4 能否可靠判断"已有 pending Proposal"

**答案**：**不能**

**原因**：
1. 无 `candidate_id` 外键关联
2. 无法通过 SQL JOIN 连接 Proposals 和 Candidates
3. 只能通过 `evidence_chain` 模糊匹配（不可靠）
4. Legacy UUID 导致证据链匹配失效

**验证查询尝试**：
```sql
-- 尝试关联（不可靠）
SELECT p.id, c.id 
FROM proposals p 
JOIN candidates c ON p.evidence_chain::text LIKE '%' || c.id || '%'
WHERE p.status = 'pending';
-- 结果: 0 或不可靠的匹配
```

---

## 4. 真正的重复 Evolution 根因

### 4.1 多层缺陷叠加

| 层级 | 缺陷 | 影响 |
|------|------|------|
| **Schema** | 无 `candidate_id` 字段 | 无法建立关联 |
| **Logic** | 无去重检查 | 每次重新处理 |
| **State** | 无状态转换 | 永远卡在 `candidate` |
| **Design** | 未定义排除规则 | 无规范依据 |

### 4.2 数据流追踪

```
Evolution #1:
  Candidate A (status=candidate)
    ↓ _acquire_scope()
    ↓ 无去重检查
    ↓ Evolution Engine
  Proposal X (status=pending, 无 candidate_id)
    ↓ 保存成功
  Candidate A (status=candidate) ← 未更新！

Evolution #2 (10分钟后):
  Candidate A (status=candidate) ← 仍然存在！
    ↓ _acquire_scope()
    ↓ 无去重检查（因为无关联）
    ↓ Evolution Engine
  Proposal Y (status=pending, 无 candidate_id) ← 重复！
    ↓ 保存成功
  Candidate A (status=candidate) ← 仍未更新！
```

### 4.3 问题总结

**核心问题**：系统根本没有机制判断"这个 Candidate 是否已有 pending Proposal"

**直接原因**：
1. Proposal 表缺少 `candidate_id` 字段
2. `_acquire_scope()` 不检查 Proposal 存在性
3. Candidate 状态不反映 Proposal 生命周期

---

## 5. 四种状态转换方案分析

### A. Proposal pending → Candidate → confirmed

**设计一致性**：❌ 不符合现有设计
- 设计文档说 `confirmed` 是最终状态（创建 MemoryNode 后）
- Proposal pending 时还未审批，不应提前 confirmed

**问题**：
- 如果 Proposal 被 reject，Candidate 已 confirmed，无法重新生成
- 违反设计文档的"confirmed = 已创建 MemoryNode"定义

### B. Proposal pending → Candidate → candidate + Scope 排除

**设计一致性**：⚠️ 部分符合
- 需要新增 Scope 排除逻辑
- 不改变 Candidate 状态语义
- 但需要建立 Proposal-Candidate 关联

**问题**：
- 需要修改 Schema（添加 candidate_id）
- 需要修改 _acquire_scope() 查询逻辑

### C. 增加新的 pending 状态

**设计一致性**：❌ 不符合现有设计
- 设计文档定义的状态：candidate, confirmed, archived, orphaned
- `pending` 不在合法状态列表中
- Repository 层会拒绝此状态

### D. 其它机制

**选项 D1**：在 Proposal 表添加 `candidate_id` + 在 Scope 查询中排除
- 优点：符合设计，明确关联
- 缺点：需要修改 Schema 和查询逻辑

**选项 D2**：添加 `last_proposal_at` 时间戳到 Candidate
- 优点：无需修改 Proposal 表
- 缺点：仍需查询 Proposal 表判断是否存在

**选项 D3**：添加 `proposal_count` 字段到 Candidate
- 优点：简单计数
- 缺点：无法区分 pending/approved/rejected

---

## 6. 当前确认的设计缺陷

### P0: Schema 缺失

**问题**：`proposals` 表缺少 `candidate_id` 字段

**证据**：
```sql
-- 验证结果
column_name = 'candidate_id' → 0 results
```

**影响**：
- 无法建立 Proposal-Candidate 关联
- 无法实现去重逻辑
- 无法追踪 Proposal 来源

### P0: Scope 查询缺失去重逻辑

**问题**：`_acquire_scope()` 不检查 Proposal 存在性

**证据**：
```python
# reflection_service.py:1080-1090
# 只有 status 过滤，无 Proposal 检查
WHERE workspace_id = :workspace_id
AND status IN ('candidate', 'pending')
```

**影响**：
- 每次 Evolution 重新处理所有 Candidate
- 产生大量重复 Proposal

### P1: 状态转换代码缺失

**问题**：没有任何代码更新 Candidate 状态

**证据**：
```bash
grep -rn "UPDATE.*candidates.*SET.*status" backend/src
# 结果: 0 matches
```

**影响**：
- Candidate 永远停留在 `candidate` 状态
- 无法表达 Proposal 生命周期

### P1: 代码使用伪关联

**问题**：用 `evidence_chain[0]` 作为 fake candidate_id

**证据**：
```python
# reflection_service.py:758
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'
```

**影响**：
- 关联不可靠
- 无法回溯真实来源

---

## 7. 修复前需要人工决定的事项

### 决策 1: 是否接受现有设计？

**现状**：设计文档未定义"已有 pending Proposal 的 Candidate"的处理方式

**选项 A**：沿用现有设计，认为 Candidate 可被多次 Evolution
- 需要添加去重机制（在 Scope 查询层）
- 不修改 Schema

**选项 B**：扩展设计，定义完整的 Candidate-Proposal 生命周期
- 需要添加 `candidate_id` 到 Proposals 表
- 需要定义状态转换规则

**决策点**：请确认采用哪种设计方向。

### 决策 2: `confirmed` 状态的触发时机

**设计文档定义**：Pattern (confirmed) 是 Evidence Verification 后的状态

**问题**：是在 Proposal approved 后变 confirmed，还是创建 MemoryNode 后？

**选项 A**：Proposal approved 后立即变 confirmed
- 优点：明确标记已审批
- 缺点：如果后续发现问题，无法重新生成

**选项 B**：创建 MemoryNode 后才变 confirmed
- 优点：符合设计文档的"confirmed → MemoryNode"流程
- 缺点：Pending Proposal 期间 Candidate 仍可能重复处理

**决策点**：请确认 `confirmed` 的确切触发时机。

### 决策 3: 如何处理现有的 92 个重复 Pending Proposals？

**现状**：92 个 pending proposals，部分由相同 Candidate 生成

**选项 A**：保留所有，手动清理
- 优点：数据完整
- 缺点：用户看到重复建议

**选项 B**：批量删除，保留最近的
- 优点：清理脏数据
- 缺点：可能丢失用户已查看的 proposal

**选项 C**：标记为 deprecated，不删除
- 优点：保留历史，不干扰 UI
- 缺点：需要额外字段

**决策点**：请确认清理策略。

---

## 8. 结论

### 8.1 核心发现

**现有设计中根本没有防止重复 Evolution 的机制**

这不是 bug，而是**设计 gap**：
- Schema 未定义关联
- 代码未实现去重
- 文档未规定规则

### 8.2 问题层次

| 层次 | 问题 | 状态 |
|------|------|------|
| Schema | 无 candidate_id | ❌ 缺失 |
| Logic | 无去重检查 | ❌ 缺失 |
| State | 无状态转换 | ❌ 缺失 |
| Design | 无排除规则 | ❌ 未定义 |

### 8.3 建议行动

**短期**（治标）：
1. 清理 92 个重复 pending proposals
2. 修复 Evidence API（添加 id 参数）

**中期**（治本）：
1. 确认设计方向（决策 1）
2. 添加 `candidate_id` 到 Proposals 表
3. 实现 Scope 去重逻辑
4. 定义状态转换规则

**长期**（优化）：
1. 统一状态定义
2. 添加 Proposal-Candidate 生命周期追踪
3. 实现完整的 Candidate 状态机

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下一步**: 等待用户确认决策 1-3
