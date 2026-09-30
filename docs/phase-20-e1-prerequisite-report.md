# Phase 20 — E1 前置核查最终报告

## 执行摘要

E1 前置核查发现**严重设计缺陷**：Candidates 状态永不更新，导致：
1. 每次 Evolution 重新处理所有 13146 个 candidates
2. 生成重复 proposals（92 个 pending）
3. 坏证据链问题持续存在

---

## A. 10+ 个坏 Proposal 是否可以安全删除且不会丢失 Candidate

### 结论
✅ **可以安全删除 Proposal，Candidate 不受影响**

### 证据

**数据查询结果**：
```
Total candidates: 13,146
Candidate status: ALL are 'candidate' (13,146)
Non-candidate status: 0

Total proposals (pending): 92
Total proposals (approved): 5,936+
```

**Proposal → Candidate 关系**：
- Proposal 由 Evolution 从 Candidate 生成
- 删除 Proposal **不会**影响 Candidate 状态
- Candidate 保持 `candidate` 状态，等待下次 Evolution 处理

**安全性评估**：
| 操作 | 影响 |
|------|------|
| DELETE FROM proposals WHERE id = ? | ✅ 仅删除提案记录 |
| Candidate 状态变化 | ❌ 无影响 |
| Evidence 数据 | ❌ 无影响 |
| Memory Nodes | ❌ 无影响 |

---

## B. 删除后重新 Evolution 是否能够重新生成 Proposal

### 结论
⚠️ **会重新生成，但会再次产生相同错误**

### 原因分析

**Evolution 流程**：
```python
# reflection_service.py:1080-1090
result = await conn.execute(text("""
    SELECT ... FROM candidates
    WHERE workspace_id = :workspace_id
    AND status IN ('candidate', 'pending')  # ← 所有 candidate 都符合
    ORDER BY created_at ASC
    LIMIT :limit
"""))
```

**关键发现**：
- `_acquire_scope()` 查询条件：`status IN ('candidate', 'pending')`
- **所有 13,146 个 candidates 都满足此条件**
- 没有代码将 candidate 状态更新为 `processed` 或 `evolved`

**设计缺陷**：
```python
# reflection_service.py - 查找不到任何 UPDATE candidates SET status...
# evidence_evolution_engine.py - 查找不到任何状态更新
```

**结果**：
- 删除 92 个 pending proposals 后
- 重新运行 Evolution
- 会重新处理相同的 13,146 个 candidates
- 会再次生成相似的 proposals
- 坏证据链问题会再次出现

---

## C. 如果重新 Evolution 仍然生成相同的 legacy UUID，准确指出来源

### 结论
**Legacy UUID 来源于原始 Evidence 数据，非系统生成**

### 追踪路径

**证据链来源**：
```python
# evidence_evolution_engine.py:169-175
evidence_id = e.get("id", None)  # 从输入 evidence 获取 ID
if not evidence_id:
    evidence_id = str(generate_uuid())  # 如果没有才生成新 UUID

evidence_ids = [e.get("id") or str(generate_uuid()) for e in evidence]
# ↑ 直接使用证据的 ID，不生成新 ID
```

**Fact 提取**：
```python
# evidence_evolution_engine.py:194-195
fact["source_ids"] = evidence_ids[:2]  # 引用原始证据 ID
```

**Candidate 生成**：
```python
# evidence_evolution_engine.py:353
candidate = {
    "evidence_chain": source_ids[:10],  # 继承自 fact 的 source_ids
}
```

**Proposal 生成**：
```python
# reflection_service.py:1046
proposals.append({
    "evidence_chain": candidate_evidence_chain,  # 继承自 candidate
})
```

### Legacy UUID 来源确认

**数据库证据**：
```
Evidence IDs in database:
  Prefix 00000000...: 15,662 evidences (UUIDv7 format)
  
Candidate evidence chains reference:
  ["00000000-019f-d00e...": 3,262 candidates
  ["12e81ff8-9096-11f1...": 867 candidates ← Legacy format!
  ["12eb174e-9096-11f1...": 559 candidates ← Legacy format!
  ...
```

**Legacy UUID 特征**：
- 格式：`12xxxxxx-xxxx-1xxx-...`（非 UUIDv7）
- 时间戳部分：`12e7fb0e` ≈ 2024-08 左右
- 当前 UUIDv7：`00000000-019f-d00e-...`（时间戳前缀为 0）

**根因**：
1. 早期数据导入时使用了 legacy UUID
2. 这些 UUID 被存储在 evidences 表的 `id` 字段
3. Evolution 处理时继承这些 ID 到 candidates
4. 生成 proposals 时继承到 evidence_chain
5. 但 `GET /evidences` API 不支持按 ID 查询（Bug）
6. Dashboard 显示"无证据记录"

---

## D. Candidate 是否已经不可重新 Evolution

### 结论
❌ **Candidate 仍可重新 Evolution，但会产生相同错误**

### 当前状态

| 项目 | 数量 | 说明 |
|------|------|------|
| 总 Candidates | 13,146 | 全部 status='candidate' |
| 在 Evolution Scope | 13,146 | 全部符合 `status IN ('candidate','pending')` |
| 引用 Legacy UUID | 8,829 | 67% 的 candidates |
| 引用 UUIDv7 | 4,317 | 33% 的 candidates |

### 重新 Evolution 的行为

**预期行为**（根据设计）：
1. 处理 candidate
2. 提取 facts
3. 生成 proposals
4. 更新 candidate status 为 `processed`（**未实现**）

**实际行为**：
1. 处理 candidate ✅
2. 提取 facts ✅
3. 生成 proposals ✅
4. 更新 candidate status ❌ **缺失！**

**结果**：
- 每次 Evolution 都重新处理所有 13,146 个 candidates
- 生成大量重复 proposals
- 坏证据链问题持续存在

---

## E. 设计缺陷总结

### 问题 1：Candidate 状态永不更新

**位置**：`reflection_service.py`, `evidence_evolution_engine.py`

**缺失代码**：
```python
# 应该在 Evolution 完成后执行：
await conn.execute(text("""
    UPDATE candidates 
    SET status = 'processed' 
    WHERE id = :id
"""), {"id": candidate_id})
```

**影响**：
- 所有 candidates 永远保持在 `candidate` 状态
- 每次 Evolution 重新处理相同数据
- proposals 表积累大量重复记录

### 问题 2：Evidence API 不支持按 ID 查询

**位置**：`app.py:864-899`

**当前实现**：
```python
@app.get("/evidences")
async def list_evidences(
    workspace_id: str = Query(None),
    keyword: str = Query(None),  # ← 只有 keyword，没有 id
    limit: int = Query(5)
):
```

**缺失功能**：
- 没有 `id` 参数
- Dashboard 调用 `/evidences?id=xxx` 无效
- 返回 workspace 的所有 evidence，而非指定 ID 的 evidence

### 问题 3：Legacy UUID 数据污染

**来源**：
- 早期数据导入
- 迁移过程
- 外部系统集成

**影响范围**：
- 8,829 个 candidates 引用 legacy UUID
- 92 个 pending proposals 证据链断裂
- Dashboard 显示"无证据记录"

---

## F. 修复建议

### E0 - 紧急：修复 Evidence API
```python
@app.get("/evidences")
async def list_evidences(
    workspace_id: str = Query(None),
    id: str = Query(None),  # ← 添加 id 参数
    keyword: str = Query(None),
    limit: int = Query(5)
):
    if id:
        sql = "SELECT ... WHERE id = :id"
    elif keyword:
        sql = "SELECT ... WHERE content ILIKE :kw"
    else:
        sql = "SELECT ... WHERE workspace_id = :wid"
```

### E1 - 重要：添加 Candidate 状态更新
```python
# 在 _save_proposals 或 _auto_approve_pending_proposals 后
for candidate in evolved_candidates:
    await conn.execute(text("""
        UPDATE candidates 
        SET status = 'processed' 
        WHERE id = :id
    """), {"id": candidate['id']})
```

### E2 - 重要：清理 Legacy UUID
```sql
-- 方案 A：删除引用 legacy UUID 的 candidates
DELETE FROM candidates
WHERE workspace_id = 'fd0223ed-...'
AND evidence_chain::text LIKE '%12%-%9096%';

-- 方案 B：标记为已处理，跳过下次 Evolution
UPDATE candidates
SET status = 'skipped'
WHERE workspace_id = 'fd0223ed-...'
AND evidence_chain::text LIKE '%12%-%9096%';
```

### E3 - 低：添加启动冷却期
```python
# 防止容器重启后立即触发大量 Evolution
if (now - last_run).total_seconds() < 300:  # 5 分钟冷却
    logger.info("Skipping evolution: cooldown period")
    return
```

---

## G. 最终结论

### 是否可以安全删除坏 Proposals？
✅ **是**，删除不会影响 candidates 或其他数据

### 删除后重新 Evolution 能否工作？
⚠️ **部分能**，但会再次生成相似 proposals（因为 candidate 状态未更新）

### Legacy UUID 来源？
**原始证据数据**，非系统生成，存在于早期导入的数据中

### Candidate 是否仍可 Evolution？
✅ **是**，所有 13,146 个 candidates 仍在 scope 中

### 核心设计缺陷？
**Candidate 状态永不更新**，导致重复处理和证据链断裂问题持续存在

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**建议行动**: 按优先级实施 E0, E1, E2 修复
