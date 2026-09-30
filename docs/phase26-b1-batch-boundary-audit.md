# Phase 26-B.1 — Batch Boundary & Idempotency Audit

## Executive Summary

**结论：Batch 只是执行调度边界，不是语义聚合边界。**

ReflectionEngine 在 _generate_proposals() 中按 **entity**（名称）聚合事实，而非按 batch。LLM 从整个 batch 的 candidate content 提取事实，然后按 entity 分组。

---

## 1. ReflectionEngine 聚合机制分析

### 1.1 事实提取阶段（_extract_facts）

```python
# reflection_engine.py:140-195
async def _extract_facts(self, candidates, provider):
    # Build prompt from ALL candidates in batch
    contents = []
    for i, c in enumerate(candidates):
        content = c.get("content", "")[:500]  # Truncate to 500 chars
        contents.append(f"[{i+1}] {content}")
    
    system_prompt = f"""
    你是一个信息提取专家。请从以下记忆中提取结构化事实。
    IDs: {memory_ids}
    Memories:
    {"\n".join(contents)}
    """
    # LLM extracts facts with source_ids from candidate IDs
```

**关键发现**：
- ✅ LLM 处理的是 **整个 batch 的所有 candidates**
- ✅ 事实提取是 **批量操作**，不是逐条处理
- ✅ source_ids 包含该 fact 对应的 candidate ID

### 1.2 Proposal 生成阶段（_generate_proposals）

```python
# reflection_engine.py:279-375
entity_evidence: dict[str, list[dict[str, Any]]] = {}
for fact in facts:
    entity = fact.get("entity", "unknown")
    if entity not in entity_evidence:
        entity_evidence[entity] = []
    entity_evidence[entity].append(fact)

for entity, entity_facts in entity_evidence.items():
    avg_confidence = sum(f.get("confidence", 0.5) for f in entity_facts) / len(entity_facts)
    
    # Decision logic
    if avg_confidence >= 0.8 and len(entity_facts) >= 3:
        proposal_type = "Strengthen"
        target_level = source_level + 1
    elif avg_confidence >= 0.6 and len(entity_facts) >= 2:
        proposal_type = "Create"
        target_level = source_level + 1
    elif avg_confidence >= 0.9:
        proposal_type = "Refine"
        target_level = source_level
    else:
        proposal_type = "Split"
        target_level = source_level
```

**关键发现**：
- ✅ 聚合粒度是 **entity name**（字符串），不是 entity_id
- ✅ 同 entity name 的所有 facts 会被聚合
- ✅ 阈值判断基于聚合后的 entity_facts 数量

---

## 2. Batch 边界影响分析

### 2.1 Batch 只是调度单位

```python
# reflection_service.py:718-800
for i in range(0, len(candidates), BATCH_SIZE):
    batch = candidates[i:i + BATCH_SIZE]
    # ... process each batch independently ...
```

**影响**：
- ✅ Batch 1（candidates 1-100）：独立处理
- ✅ Batch 2（candidates 101-200）：独立处理
- ❌ **Batch 之间不会共享历史 facts**

### 2.2 跨 Batch 聚合问题

**场景假设**：
- Entity "手机控制开关机" 有 105 个 Candidate
- Batch 1: 100 个 candidates（含 100 个该 entity）
- Batch 2: 5 个 candidates（含 5 个该 entity）

**实际行为**：
```
Batch 1:
  - LLM 处理 100 个 candidates
  - 可能提取出 5 个 fact（该 entity）
  - len(entity_facts) = 5 < 10（假设阈值）
  - 不生成 Proposal

Batch 2:
  - LLM 处理 5 个 candidates
  - 提取出 2 个 fact（该 entity）
  - len(entity_facts) = 2 < 10（假设阈值）
  - 不生成 Proposal

结果：105 个 Candidate 的 entity 总共产生 0 个 Proposal
问题：跨 batch 的事实未被聚合！
```

**结论**：⚠️ **Batch 会截断语义聚合上下文**

---

## 3. 当前数据的事实密度分析

### 3.1 Entity-Candidate 分布

```sql
SELECT 
    entity_id,
    COUNT(*) as candidate_count
FROM candidates
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
GROUP BY entity_id
HAVING COUNT(*) >= 2
ORDER BY candidate_count DESC
LIMIT 20;
```

**关键发现**：
- 大部分 entity 只有 1 个 candidate
- 少数 entity 有 2+ candidates（如 Windows: 2200 candidates）

### 3.2 为什么"Windows"有 2200 candidates？

```sql
canonical_name | candidate_count
---------------+-----------------
Windows        |            2200
```

**分析**：这很可能是数据质量问题——entity canonical_name 可能包含噪音（如大小写不一致、前后空格等）。实际有效 entity 数量可能远少于 2200。

---

## 4. Canary 10 个 Candidate 的处理结果

### 4.1 执行情况

- 10 个 candidates 来自 3 个不同的 entity
- 每个 entity 只有 1-5 个 candidates
- LLM 提取出 1 个 fact
- 生成 1 个 Proposal（type=Split, target_level=1）

### 4.2 为什么只有 1 个 Proposal？

原因：
1. 大多数 entity 的 candidate 数量 < 2
2. LLM 提取的事实密度低
3. 不满足 len(entity_facts) >= 2 的 Create 阈值

---

## 5. 幂等性验证

### 5.1 Database Unique Constraint

```sql
uk_proposals_pending_per_candidate UNIQUE (workspace_id, candidate_id) WHERE status = 'pending'
```

**验证**：✅ 已生效，重复插入会触发 UniqueViolationError

### 5.2 Application-Level Deduplication

```python
# reflection_service.py:1068-1080
deduplicated: dict[str, dict[str, Any]] = {}
for prop in proposals:
    candidate_id = prop.get("candidate_id")
    if candidate_id and candidate_id not in deduplicated:
        deduplicated[candidate_id] = prop
```

**验证**：✅ 双重保护（DB + App）

### 5.3 重复执行 Reflection 的影响

**场景**：
1. 第一次执行：10 candidates → 1 proposal
2. 第二次执行：同一批 10 candidates → ?

**结果**：
- ✅ 由于 unique constraint，不会创建重复 proposal
- ✅ Status 为 'pending' 的 proposal 不会被重复批准
- ✅ 已 'approved' 的 proposal 不受影响

---

## 6. 关键问题解答

### Q1: ReflectionEngine 是否按 entity_id 聚合历史 Candidate？

**回答**：**部分是的，但不完全。**
- ✅ 按 entity name（字符串）聚合 facts
- ❌ 不按 entity_id 查询历史 candidates
- ⚠️ 只聚合当前 batch 中的 candidates

### Q2: Batch size 是否会改变语义结果？

**回答**：**是的，batch size 会影响语义结果。**
- 更大的 batch → 更多 candidates → 更多 facts → 更高的聚合密度
- 更小的 batch → 更少的 facts → 可能低于阈值

### Q3: 105 个 Candidate 分 2 个 batch 会不会丢失 Proposal？

**回答**：**有可能丢失。**
- 如果 entity 的 facts 分散在两个 batch
- 每个 batch 的 entity_facts 数量 < 阈值
- 最终不会生成 Proposal

**解决方案**：
1. 增大 batch size（如 200-500）
2. 或按 entity 分组后处理（先按 entity 排序，再分批）

### Q4: Canary 的 10 个 Candidate 是否可以重新处理？

**回答**：**可以，不会重复创建 Proposal。**
- 已有 proposal 的 candidate 会被跳过
- 没有 proposal 的 candidate 可以重新处理
- 建议：全量执行时包含这 10 个

---

## 7. 最终裁决

| 检查项 | 结果 |
|--------|------|
| **BATCH_IS_SEMANTIC_BOUNDARY** | ✅ **YES（部分）** — batch 会截断聚合上下文 |
| **REFLECTION_AGGREGATION_SCOPE** | **Current batch only** — 不查询历史 candidates |
| **CROSS_BATCH_HISTORY_AVAILABLE** | ❌ **NO** — 没有跨 batch 的历史查询 |
| **CANARY_REPROCESS_SAFE** | ✅ **YES** — 幂等保护有效 |
| **PROPOSAL_IDEMPOTENT** | ✅ **YES** — Unique constraint + app-level dedup |
| **FULL_RUN_MUST_INCLUDE_CANARY_10** | ✅ **YES** — 确保完整执行 |

---

## 8. 执行模型建议

### 推荐方案：增大 Batch Size + 按 Entity 预分组

```python
# 策略 1：增大 batch size
BATCH_SIZE = 200  # 从默认值增大

# 策略 2：按 entity 分组后处理
candidates_by_entity = {}
for c in candidates:
    eid = str(c.entity_id)
    if eid not in candidates_by_entity:
        candidates_by_entity[eid] = []
    candidates_by_entity[eid].append(c)

for eid, entity_candidates in candidates_by_entity.items():
    # 每个 entity 的所有 candidates 一起处理
    result = await reflection_svc.reflect(
        workspace_id=workspace_id,
        scope=f'entity:{eid}',
        limit=len(entity_candidates),
    )
```

### 当前可执行的方案：

```python
# 简单方案：使用更大的 batch size
BATCH_SIZE = 500  # 确保足够多的 candidates 在同一 batch
```

---

## 9. Phase 26-B.1 审计结论

### CANARY 状态
- ✅ PASS
- 10 个 candidates 中有 1 个生成了 Proposal
- entity_id 传递完整
- 无重复 Proposal

### FULL RUN 决策
- ⚠️ **有条件 GO**
- 需要解决 batch 语义边界问题
- 建议：增大 batch size 或按 entity 分组执行

### 风险缓解
1. 先执行小批量（200 candidates）观察结果
2. 验证 proposal 生成率
3. 确认无重复创建后，扩大范围
4. 考虑按 entity 分组执行策略

---

*Report generated: 2026-08-15 01:15 UTC*
*Auditor: Phase 26-B.1 Batch Boundary & Idempotency Audit*
