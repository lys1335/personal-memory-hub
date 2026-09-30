# Phase 26 — Proposal Formation & L1 Validation Report

## Executive Summary

Phase 26-A Preflight 只读调查已完成。**关键发现：当前架构不支持直接从 Candidate 创建 L1 MemoryNode。**

---

## Phase 26-A — Preflight 只读审计

### 1. ReflectionService 调用链（已确认）

```
Cron Task (type='evolution')
  → app.py: /api/cron/tasks/{id}/run
  → reflection_svc.reflect(workspace_id, scope='daily', limit=200)
    → _acquire_scope() → SELECT candidates WHERE status='candidate' AND NOT EXISTS proposal
    → _run_engine_pipeline(scope, candidates, workspace_id)
      → Stage 1: EvidenceEvolutionEngine.evolve() → evolved_candidates
      → Stage 2: ReflectionEngine.reflect_pipeline() → proposals
    → _save_proposals(proposals, workspace_id)
    → _auto_approve_pending_proposals(workspace_id)  [if AUTO_APPROVE=true]
```

**重要发现**：`_run_engine_pipeline()` 是**两阶段流水线**：
- Stage 1: EvidenceEvolutionEngine（从现有候选生成新候选）
- Stage 2: ReflectionEngine（提取 facts 和 proposals）

### 2. Candidate 如何进入 ReflectionService

`_acquire_scope()` 查询条件（line 1157-1180）：

```sql
SELECT ... FROM candidates
WHERE workspace_id = :workspace_id
  AND status = 'candidate'
  AND NOT EXISTS (
    SELECT 1 FROM proposals 
    WHERE proposals.candidate_id = candidates.id 
      AND proposals.status = 'pending'
  )
ORDER BY created_at ASC
LIMIT :limit
```

**筛选条件**：
- ✅ status = 'candidate'（所有 2,469 个 Candidate 都满足）
- ✅ 没有 pending 状态的 Proposal（当前 0 个 Proposal，全部满足）
- ✅ workspace_id 匹配（当前只有 1 个 workspace）

**结论**：**2,469 个 Candidate 全部符合 ReflectionService 的处理条件**。

### 3. Proposal 创建条件 / Gate

ReflectionEngine 生成的 Proposal 需要满足：

1. **Entity Resolution**: candidate 必须有 entity_id（✅ 全部 2,469 个都有有效 entity_id）
2. **LLM 推理**: 使用 `PMH_REFLECTION_MODEL`（当前配置：`reflection-engine:small`）
3. **去重约束**: `_save_proposals()` 按 candidate_id 去重，同一 batch 内只保留第一个 proposal

**Unique Constraint**（数据库层）：
```sql
uk_proposals_pending_per_candidate UNIQUE (workspace_id, candidate_id) 
  WHERE status = 'pending'
```

### 4. approve_proposal() 如何创建 MemoryNode

**关键发现**：`approve_proposal()` 创建的是 **L2/L3，不是 L1**！

```python
# reflection_service.py line 245
level = prop["target_level"]
node_type = "Pattern" if level == 2 else "Belief" if level == 3 else "Observation"

# INSERT INTO memory_nodes (line 326)
```

**Auto-approve 逻辑**（line 426-455）：
```python
threshold = float(os.environ.get('AUTO_APPROVE_THRESHOLD', '0.95'))
max_level = int(os.environ.get('AUTO_APPROVE_MAX_LEVEL', '3'))

if min_confidence < threshold:
    return 0  # Skip auto-approve

if target_level > max_level:
    return 0  # Skip auto-approve

# Find proposals for L{target_level}
SELECT ... WHERE target_level = :target_level AND confidence >= :threshold
```

**环境变量配置**：
- `AUTO_APPROVE=true`
- `AUTO_APPROVE_THRESHOLD=0.9`
- `AUTO_APPROVE_MAX_LEVEL=3`

**结论**：`approve_proposal()` 创建 L2/L3，**不创建 L1**。

### 5. L1 entity_id 来源

如果 Proposal.target_level = 1，则：
```python
level = 1
node_type = "Observation"  # 根据 CHECK constraint
entity_id = candidate.entity_id  # ✅ 正确来源
```

**但实际风险**：
- ReflectionEngine 可能生成 target_level >= 2 的 proposal
- 需要验证 LLM 输出格式

### 6. Candidate → Proposal 唯一约束

**数据库约束**（已确认）：
```sql
uk_proposals_pending_per_candidate UNIQUE (workspace_id, candidate_id) WHERE status = 'pending'
```

**应用层去重**（P0 Fix，line 1059-1080）：
```python
deduplicated: dict[str, dict[str, Any]] = {}
for prop in proposals:
    candidate_id = prop.get("candidate_id")
    if candidate_id and candidate_id not in deduplicated:
        deduplicated[candidate_id] = prop
```

**结论**：**幂等性有双重保障**。

### 7. 重复执行风险

**低风险提示**：
1. `_acquire_scope()` 排除已有 pending proposal 的 candidate
2. Unique constraint 防止重复插入
3. 已处理的 candidate 下次不会被选中

**风险等级**：🟢 低风险

### 8. Cron Task 当前配置

**发现**：没有 `cron_tasks` 表，使用内存存储（`_cron_tasks` dict）。

当前配置（从日志和代码推断）：
- Task ID: `06a7dd65`（从 memory 记录）
- Type: `evolution`
- Payload: `{workspace_id, limit: 200}`

**验证状态**：
```bash
curl GET /api/cron/tasks  # Docker 内无 curl
```

**替代方案**：通过 Python httpx 或直接调用 service 方法。

### 9. EvolutionService 意外触发风险

**当前状态**：
- Phase 24-E 未调用 EvolutionService
- 没有 L1 MemoryNodes，所以 EvolutionService 没有输入

**风险**：如果 Cron 任务配置错误，可能意外触发 EvolutionService。

**缓解措施**：
1. 先验证 Cron 任务类型是 `evolution` 不是 `evolution_v2`
2. 监控日志中是否有 `[EVOLUTION]` 相关输出

---

## 关键发现总结

### ✅ 支持的操作

1. **Candidate → Proposal**：ReflectionService._save_proposals()
2. **Proposal → L2/L3**：ReflectionService.approve_proposal()
3. **幂等性保障**：Unique constraint + 应用层去重
4. **All 2,469 candidates eligible**：满足所有查询条件

### ❌ 不支持的操作

1. **Candidate → L1**：无直接路径！
2. **自动批准阈值**：AUTO_APPROVE_THRESHOLD=0.9（可能过高）
3. **LLM 依赖**：需要 reflection-engine:small 模型可用

---

## 架构问题：L1 创建路径缺失

### 问题

**当前架构设计**：
- Phase 24-E: Evidence → Candidate
- Phase 25+: Candidate → Proposal → **L2/L3**

**缺失环节**：
- Candidate → L1 MemoryNode 的路径未定义！

### 可能的解决方案

**方案 A**：修改 ReflectionService，添加 L1 创建逻辑
```python
if proposal.target_level == 1:
    # Create L1 MemoryNode
    self._create_l1_memory_node(proposal, workspace_id)
```

**方案 B**：在 Proposal 批准后自动触发 L1 创建
```python
# 在 _auto_approve_pending_proposals() 中
if prop.target_level == 1:
    await self.approve_proposal(...)  # 但这个方法创建 L2/L3
```

**方案 C**：手动为每个 Candidate 创建 L1
```python
# 绕过 Proposal，直接创建 L1
for candidate in candidates[:10]:
    l1 = MemoryNode(
        level=1,
        node_type="Observation",
        entity_id=candidate.entity_id,
        content=candidate.content,
        ...
    )
```

### 推荐方案

**先进行 10-Candidate Canary 测试**，验证：
1. ReflectionService 能成功为 10 个 Candidate 生成 Proposal
2. Proposal 的 target_level 是否正确（应为 1）
3. 如果 target_level >= 2，需要调整 LLM prompt

---

## 风险评估

| 风险 | 概率 | 影响 | 状态 |
|------|------|------|------|
| LLM 模型不可用 | 中 | 高 | ⚠️ 需验证 |
| target_level >= 2 导致 L2/L3 跳过 L1 | 高 | 中 | ⚠️ 需验证 |
| AUTO_APPROVE 自动批准 L2/L3 | 中 | 低 | ⚠️ 需监控 |
| Unique constraint violation | 低 | 低 | ✅ 已防护 |
| Transaction failure | 低 | 中 | ⚠️ 需监控 |

---

## 建议执行策略

### Phase 26-B: 10-Candidate Canary

**目标**：验证 ReflectionService 能正确处理 10 个 Candidate。

**步骤**：
1. 选择最早创建的 10 个 Candidate
2. 手动调用 `reflect(workspace_id, scope='entity', limit=10)`
3. 验证 Proposal 生成数量和内容
4. 检查 target_level 分布
5. **暂不自动批准**

### Phase 26-C: Canary Gate 检查点

**成功标准**：
- [ ] 10/10 Candidate 生成 Proposal
- [ ] Proposal target_level = 1（或明确知道为什么是其他值）
- [ ] 无 transaction failures
- [ ] L1 创建路径明确（或识别为缺失）

### Phase 26-D: Full Proposal Formation

**仅在 Canary Gate 通过后执行**。

---

## 结论

**Phase 26-A Preflight: COMPLETE**

**关键发现**：
1. ✅ 2,469 Candidates 全部 eligible
2. ✅ 幂等性有双重保障
3. ⚠️ **L1 创建路径缺失** — 需要确认设计意图
4. ⚠️ **AUTO_APPROVE=true** 可能意外创建 L2/L3

**建议下一步**：
执行 Phase 26-B 10-Candidate Canary 测试，验证 Proposal 生成和 target_level 分布。

**等待用户确认是否继续到 Phase 26-B。**
