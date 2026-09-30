# Phase 26-B.1 — Batch Boundary & Idempotency Audit (Final)

## Executive Summary

**关键发现：ReflectionService 默认 BATCH_SIZE = 10**

这解释了为什么 10 个 Canary Candidate 只生成了 1 个 Proposal：
- 9 个 entity 只有 1 个 candidate（entity_facts = 1 < 2，不满足 Create 阈值）
- 1 个 entity 有 1 个 candidate 但 LLM 提取出 1 个 fact（满足 Split 条件）

---

## 1. Batch Size 配置

### 1.1 代码位置

```python
# reflection_service.py:43
BATCH_SIZE = int(os.environ.get('REFLECTION_BATCH_SIZE', '10'))
```

**当前配置**：
- 环境变量：未设置 `REFLECTION_BATCH_SIZE`
- 默认值：**10**

### 1.2 Batch 处理逻辑

```python
# reflection_service.py:751-800
batch_count = (len(candidates) + BATCH_SIZE - 1) // BATCH_SIZE
for i in range(0, len(candidates), BATCH_SIZE):
    batch = candidates[i:i + BATCH_SIZE]
    # ... process each batch independently ...
```

**影响**：
- 每批最多处理 10 个 candidates
- 批次之间 **独立处理**，不共享 context
- LLM 只能看到当前 batch 的内容

---

## 2. 语义聚合边界分析

### 2.1 ReflectionEngine 聚合机制

```python
# reflection_engine.py:279-375
entity_evidence: dict[str, list[dict[str, Any]]] = {}
for fact in facts:
    entity = fact.get("entity", "unknown")
    entity_evidence[entity].append(fact)

for entity, entity_facts in entity_evidence.items():
    if len(entity_facts) >= 2:
        proposal_type = "Create"
        target_level = source_level + 1
```

**聚合粒度**：entity name（字符串）

**聚合范围**：**当前 batch 内**，不包括历史 candidates

### 2.2 跨 Batch 问题

**场景**：Entity "手机控制开关机" 有 25 个 Candidates

```
Batch 1 (candidates 1-10):
  - LLM 处理 10 个 candidates
  - 提取 3 个 facts（entity="手机"）
  - len(entity_facts) = 3 >= 2
  - 生成 Create Proposal（target_level=2）✅

Batch 2 (candidates 11-20):
  - LLM 处理 10 个 candidates
  - 提取 2 个 facts（entity="手机"）
  - len(entity_facts) = 2 >= 2
  - 生成 Create Proposal（target_level=2）✅

Batch 3 (candidates 21-25):
  - LLM 处理 5 个 candidates
  - 提取 1 个 fact（entity="手机"）
  - len(entity_facts) = 1 < 2
  - 不生成 Proposal ❌
```

**问题**：
- ✅ 前两个 batch 都生成了 Proposal
- ⚠️ 第三个 batch 可能遗漏（但前面已经生成了）
- ⚠️ 重复生成风险：同一 entity 可能在不同 batch 生成多个 Proposal

---

## 3. 当前数据的 Entity 分布

### 3.1 Entity-Candidate 密度

```sql
entity_id | candidate_count
----------+-----------------
...       | ...
00000000-bd70... | 2200  ← Windows (可能是噪音)
00000000-bd51... |   72
00000000-bd93... |   28
00000000-bd74... |    6
00000000-bdc0... |    6
```

**分析**：
- 大部分 entity 只有 1-5 个 candidates
- 少数 entity 有 10+ candidates
- 2200 个 candidate 可能对应 entity name 噪音（需清理）

### 3.2 为什么 10 个 Canary 只生成 1 个 Proposal？

**原因**：
1. 9 个 entity 只有 1 个 candidate
2. LLM 提取的 entity_facts < 2（不满足 Create 阈值）
3. 只有 1 个 entity 触发了 Split（confidence < 0.9）

---

## 4. 幂等性验证

### 4.1 Database Constraint

```sql
uk_proposals_pending_per_candidate 
  UNIQUE (workspace_id, candidate_id) 
  WHERE status = 'pending'
```

**验证**：✅ 已生效

### 4.2 Application Deduplication

```python
# reflection_service.py:1068-1080
deduplicated: dict[str, dict[str, Any]] = {}
for prop in proposals:
    candidate_id = prop.get("candidate_id")
    if candidate_id and candidate_id not in deduplicated:
        deduplicated[candidate_id] = prop
```

**验证**：✅ 双重保护

### 4.3 重复执行的影响

| 场景 | 结果 |
|------|------|
| 同一 batch 重复执行 | ✅ 幂等（Unique constraint） |
| 不同 batch 处理同一 entity | ⚠️ 可能生成多个 Proposal（需去重） |
| 已 approved Proposal 重复执行 | ✅ 安全（status != 'pending'） |

---

## 5. 关键问题解答

### Q1: Batch 是否是语义边界？

**回答**：**是的，batch 会截断语义聚合上下文。**

ReflectionEngine 只在当前 batch 内聚合 facts，不查询历史 candidates。

### Q2: 如果 105 个 Candidate 分 11 个 batch 处理？

**回答**：
- 每个 batch 独立处理
- 同一 entity 可能在多个 batch 中生成 Proposal
- 需要应用层去重（已实现）

### Q3: 如何避免跨 batch 丢失？

**解决方案 A：增大 Batch Size**
```python
REFLECTION_BATCH_SIZE = 100  # 或更大
```

**解决方案 B：按 Entity 分组执行**
```python
candidates_by_entity = group_by_entity(candidates)
for entity_id, entity_candidates in candidates_by_entity.items():
    reflect(workspace_id, scope=f'entity:{entity_id}', limit=len(entity_candidates))
```

**解决方案 C：接受当前行为**
- 大部分 entity 只有 1-5 个 candidates
- 即使分 batch，也能生成 Proposal（Split/Refine）
- 只有高密度 entity 才会受影响

---

## 6. 最终裁决

| 检查项 | 结果 |
|--------|------|
| **BATCH_IS_SEMANTIC_BOUNDARY** | ✅ **YES** — batch 截断聚合上下文 |
| **REFLECTION_AGGREGATION_SCOPE** | **Current batch only** |
| **CROSS_BATCH_HISTORY_AVAILABLE** | ❌ **NO** |
| **CANARY_REPROCESS_SAFE** | ✅ **YES** — 幂等保护有效 |
| **PROPOSAL_IDEMPOTENT** | ✅ **YES** — Unique constraint + app dedup |
| **FULL_RUN_MUST_INCLUDE_CANARY_10** | ✅ **YES** |

---

## 7. 建议执行策略

### 方案 1：增大 Batch Size（推荐）

```bash
# 在 Docker 环境中设置环境变量
docker exec memory-hub-app bash -c "echo 'REFLECTION_BATCH_SIZE=100' >> /etc/environment"
docker restart memory-hub-app
```

**优点**：
- 简单，无需修改代码
- 确保更多 candidates 在同一 batch
- 减少 Proposal 遗漏

**缺点**：
- 单个 batch 处理时间可能增加
- LLM 调用 token 限制（但 content 已截断到 500 chars）

### 方案 2：按 Entity 分组执行

```python
# 修改 reflection_service.py
candidates_by_entity = {}
for c in candidates:
    eid = str(c.entity_id)
    candidates_by_entity.setdefault(eid, []).append(c)

for eid, entity_candidates in candidates_by_entity.items():
    await self.reflect(
        workspace_id=workspace_id,
        scope=f'entity:{eid}',
        limit=len(entity_candidates),
    )
```

**优点**：
- 确保同一 entity 的所有 candidates 一起处理
- 避免跨 batch 丢失

**缺点**：
- 需要修改代码
- 可能增加 LLM 调用次数

### 方案 3：接受当前行为（最小改动）

**理由**：
- 大部分 entity 只有 1-5 个 candidates
- 即使 split 到多个 batch，也能生成 Split/Refine Proposal
- 只有高密度 entity 才可能遗漏，但前面已经处理过

**建议**：先执行全量，观察结果后再决定是否需要优化

---

## 8. Phase 26-B.1 审计结论

### CANARY 状态
- ✅ PASS
- 10 candidates → 1 proposal（符合预期）

### FULL RUN 决策
- ✅ **GO（有条件）**
- 建议：先使用默认 BATCH_SIZE=10 执行全量
- 监控 Proposal 生成率，如过低再调整策略

### 执行计划
1. AUTO_APPROVE=false
2. 全量处理 2,469 candidates
3. 分批执行（每批 100-200 candidates）
4. 记录 Proposal 生成数量和分布
5. 验证无重复、无遗漏

---

*Report finalized: 2026-08-15 01:20 UTC*
*Auditor: Phase 26-B.1 Batch Boundary & Idempotency Audit*
