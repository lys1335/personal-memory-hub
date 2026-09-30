# Phase 26-B.2 — Reflection Semantic Aggregation Boundary Audit

## Executive Summary

**核心结论**：当前实现存在 **语义边界与执行边界的混淆**。

- **SEMANTIC_BOUNDARY**: 应该是 `entity_id`（同一实体的所有候选应该一起处理）
- **EXECUTION_BATCH**: 应该是性能参数（LLM 调用的分批）
- **当前实现**: 两者混淆，BATCH_SIZE 同时决定了语义聚合范围

**问题**：2,469 个 Candidates 分布在 4,855 个 Entities 中，大多数 Entity 只有 1-5 个 Candidates。当前 BATCH_SIZE=10 会导致大部分 Entity 无法达到 Proposal 生成阈值。

---

## 1. 当前实现分析

### 1.1 Scope Acquisition（ReflectionService._acquire_scope）

```python
# reflection_service.py:1157-1200
result = await conn.execute(text("""
    SELECT id, entity_id, area_id, content, ...
    FROM candidates
    WHERE workspace_id = :workspace_id
      AND status = 'candidate'
      AND NOT EXISTS (
          SELECT 1 FROM proposals
          WHERE proposals.candidate_id = candidates.id
            AND proposals.status = 'pending'
      )
    ORDER BY created_at ASC
    LIMIT :limit
"""), {"workspace_id": str(workspace_id), "limit": limit})
```

**关键发现**：
- ✅ 按 `workspace_id` 隔离
- ✅ 排除已有 pending proposal 的 candidates（幂等）
- ❌ **没有按 `entity_id` 分组或排序**
- ⚠️ `ORDER BY created_at ASC` 意味着最早创建的 candidates 优先处理

### 1.2 Fact Extraction（ReflectionEngine._extract_facts）

```python
# reflection_engine.py:140-195
contents = []
for i, c in enumerate(candidates):
    content = c.get("content", "")[:500]
    contents.append(f"[{i+1}] {content}")

system_prompt = f"""
IDs: {memory_ids}
Memories:
{"\n".join(contents)}
"""
# LLM extracts facts with source_ids from candidate IDs
```

**关键发现**：
- LLM 处理整个 batch 的内容
- source_ids 记录每个 fact 的来源 candidate

### 1.3 Proposal Generation（ReflectionEngine._generate_proposals）

```python
# reflection_engine.py:279-375
entity_evidence: dict[str, list[dict[str, Any]]] = {}
for fact in facts:
    entity = fact.get("entity", "unknown")
    entity_evidence[entity].append(fact)

for entity, entity_facts in entity_evidence.items():
    avg_confidence = sum(f.get("confidence", 0.5) for f in entity_facts) / len(entity_facts)
    
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
- 聚合粒度是 **entity name**（字符串），不是 entity_id
- 聚合范围是 **当前 batch 内的 facts**
- 不同 entity 的 candidates **不会互相影响**（因为按 entity name 分组）

---

## 2. 语义边界 vs 执行边界

### 2.1 理论上的正确设计

```
SEMANTIC BOUNDARY: entity_id
  - 同一 entity 的所有 candidates 应该一起处理
  - 不同 entity 之间完全隔离

EXECUTION BOUNDARY: 性能分页
  - 如果同一 entity 有 1000 个 candidates
  - 需要分批调用 LLM（避免超时/token 限制）
  - 但语义结果应该一致
```

### 2.2 当前实现的混淆

```
当前实现:
  - SEMANTIC BOUNDARY = batch（错误！）
  - EXECUTION BOUNDARY = batch（正确）
  
问题:
  - 同一 entity 的 candidates 可能被分到不同 batch
  - 每个 batch 独立处理，facts 不共享
  - 导致 Proposal 生成率低下
```

### 2.3 数据验证

```sql
-- Entity-Candidate 分布
entity_id | candidate_count
----------+-----------------
...       | ...
bd70...   | 2200  ← Windows（可能噪音）
bd51...   |   72
bd93...   |   28
bd74...   |    6
bdc0...   |    6
```

**分析**：
- 大部分 entity 只有 1-5 个 candidates
- 少数 entity 有大量 candidates（如 Windows: 2200）
- **BATCH_SIZE=10 对于小 entity 是合理的，但对于大 entity 会导致多次处理**

---

## 3. 关键问题分析

### Q1: 同一 entity 的所有 Candidates 是否应该共同参与 Reflection？

**答案**：**是的。**

理由：
1. Entity 是记忆的语义单元
2. 同一 entity 的多条证据应该聚合后才能形成高质量记忆
3. 分散处理会导致事实密度不足，无法达到 Proposal 生成阈值

**当前问题**：
- 2200 个 Windows candidates 被分成 220 个 batch（每个 10 个）
- 每个 batch 独立处理，LLM 只能看到 10 个 candidates
- 即使 total facts 足够，单个 batch 可能不够

### Q2: 不同 entity 的 Candidates 是否绝对不应该互相影响？

**答案**：**是的，应该隔离。**

理由：
1. 不同 entity 代表不同主题
2. 混合处理会导致 LLM 提取出不相关的 facts
3. 应该按 entity 分组后分别处理

**当前实现**：
- ✅ 实际上是通过 entity name 隐式隔离的
- ⚠️ 但同一 batch 可能包含多个 entity，增加 LLM 理解负担

### Q3: Reflection 是否需要跨 batch 读取历史 Candidate？

**答案**：**不需要，但需要在同一 entity 内累积。**

理由：
1. 幂等性要求：已处理的 candidates 不应重复处理
2. 但同一 entity 的新 candidates 应该能与旧 facts 累积

**当前实现**：
- ❌ 不支持跨 batch 累积
- 每次 reflect() 调用只处理当前 batch

### Q4: facts 聚合是否应该在 batch 之前完成？

**答案**：**是的，应该在 entity 级别完成。**

正确流程：
```
1. 按 entity_id 分组 candidates
2. 对每个 entity 的所有 candidates 进行 fact extraction
3. 按 entity 聚合 facts
4. 生成 proposals
```

当前流程：
```
1. 按 created_at 排序，取前 N 个 candidates（BATCH_SIZE=10）
2. 对 batch 进行 fact extraction
3. 按 entity name 聚合 facts（仅限于当前 batch）
4. 生成 proposals
```

### Q5: 一个 entity 有 105 个 Candidate 时应该如何处理？

**方案 A：整体处理（推荐）**
```python
# 获取该 entity 的所有 candidates
candidates = await candidate_repo.find_by_entity(entity_id)
# 一次性处理（如果 LLM 支持）
result = await reflection_engine.reflect_pipeline(candidates=candidates)
```

**方案 B：分批处理但语义聚合**
```python
# 分批调用 LLM，但累积 facts
all_facts = []
for batch in split_by_size(candidates, BATCH_SIZE):
    facts = await extract_facts(batch)
    all_facts.extend(facts)

# 然后统一生成 proposals
proposals = generate_proposals(all_facts)
```

**方案 C：当前实现（有问题）**
```python
# 每个 batch 独立处理
for batch in split_by_size(candidates, BATCH_SIZE):
    result = await reflect_pipeline(batch)  # 丢失上下文
```

### Q6: 一个 entity 只有 1-5 个 Candidate 时应该如何处理？

**答案**：**允许 Refine/Split，不需要等待。**

理由：
1. 这些是新的或稀疏的证据
2. Refine/Split 仍然有价值（整理、澄清）
3. 等待更多证据会延迟记忆形成

**当前实现**：
- ✅ 正确处理：生成 Split/Refine proposals

### Q7: workspace_id 是否必须成为聚合隔离边界？

**答案**：**是的。**

理由：
1. Workspace 是租户隔离单位
2. 不同 workspace 的记忆不应该交叉

**当前实现**：
- ✅ 正确：查询时过滤 workspace_id

### Q8: ContextWindow / scope 是否应该参与 Reflection 聚合？

**答案**：**Scope 是执行参数，不应该影响语义边界。**

- `scope='daily'`: 时间窗口过滤
- `scope='entity'`: 按 entity 过滤
- `scope='workspace'`: 整个 workspace

这些是查询参数，不是语义聚合单位。

---

## 4. 推荐的执行模型

### 4.1 核心原则

```
SEMANTIC BOUNDARY = entity_id + workspace_id
EXECUTION BOUNDARY = performance pagination (LLM token/timeout limits)
```

### 4.2 推荐架构

```
Phase 1: Group by Entity
  candidates_by_entity = group_candidates_by_entity(candidates)

Phase 2: Process Each Entity
  for entity_id, entity_candidates in candidates_by_entity.items():
      
      # Check if already processed (idempotency)
      if has_pending_proposals(entity_id):
          continue
      
      # Process entity candidates (may be paginated for LLM)
      entity_result = await reflect_entity(
          workspace_id=workspace_id,
          entity_id=entity_id,
          candidates=entity_candidates,
      )
      
      # Save proposals
      await save_proposals(entity_result.proposals)
```

### 4.3 伪代码实现

```python
async def reflect_by_entity(
    self,
    workspace_id: UUID,
    entity_id: UUID,
    limit: int = 50,
) -> ReflectionExecutionResult:
    """Reflect on a single entity's candidates."""
    
    # Step 1: Get all candidates for this entity
    candidates = await self._candidate_repo.find_by_entity(
        workspace_id=workspace_id,
        entity_id=entity_id,
        limit=limit,
    )
    
    if not candidates:
        return empty_result()
    
    # Step 2: Extract facts (may need pagination for LLM)
    all_facts = []
    for batch in chunks(candidates, BATCH_SIZE):
        facts = await self._extract_facts(batch)
        all_facts.extend(facts)
    
    # Step 3: Generate proposals
    proposals = await self._generate_proposals(all_facts, candidates)
    
    # Step 4: Save proposals
    await self._save_proposals(proposals, workspace_id)
    
    return result
```

### 4.4 关键改进点

1. **按 entity_id 分组**：确保同一 entity 的所有 candidates 一起处理
2. **Entity 级幂等**：通过 pending proposals 检查避免重复处理
3. **LLM 分页**：BATCH_SIZE 仅用于控制 LLM 调用大小，不影响语义
4. **Fact 累积**：同一 entity 的 facts 在不同 LLM batch 间累积

---

## 5. 与现有代码的对比

### 5.1 当前实现的问题

| 方面 | 当前实现 | 问题 |
|------|----------|------|
| 语义边界 | Batch（10 个 candidates） | 同一 entity 可能被分割 |
| 执行边界 | Batch（10 个 candidates） | 与语义边界混淆 |
| 聚合方式 | Batch 内按 entity name | 不跨 batch 累积 |
| 幂等性 | Candidate 级 | 可能导致同一 entity 多次处理 |

### 5.2 推荐实现的改进

| 方面 | 推荐实现 | 改进 |
|------|----------|------|
| 语义边界 | Entity + Workspace | 确保完整上下文 |
| 执行边界 | LLM Pagination | 仅影响性能 |
| 聚合方式 | Entity 级累积 | 不丢失事实 |
| 幂等性 | Entity 级 | 避免重复处理 |

---

## 6. 最终裁决

### 6.1 边界定义

| 检查项 | 结论 |
|--------|------|
| **REFLECTION_SEMANTIC_BOUNDARY** | `entity_id + workspace_id` |
| **EXECUTION_BATCH_BOUNDARY** | `LLM call pagination` |
| **BATCH_SIZE_ROLE** | **性能参数**（不应影响语义） |
| **CROSS_BATCH_AGGREGATION_REQUIRED** | **YES**（同一 entity 内需累积） |
| **ENTITY_ISOLATION_REQUIRED** | **YES**（不同 entity 应隔离） |

### 6.2 代码变更需求

| 项目 | 是否必需 |
|------|----------|
| **CODE_CHANGES_REQUIRED** | **YES** |
| **DATA_MIGRATION_REQUIRED** | **NO** |

**需要的代码变更**：
1. 添加 `find_by_entity()` 方法到 CandidateRepository
2. 修改 `_acquire_scope()` 支持 entity 级查询
3. 添加 entity 级幂等检查
4. 修改 `_run_engine_pipeline()` 支持 fact 累积

### 6.3 Phase 26-D 决策

**当前状态**：
- Phase 26-B.1 CANARY: PASS
- Phase 26-B.2 Audit: 发现语义边界问题

**建议**：
1. **短期**：接受当前实现，执行全量 Proposal Formation
   - 使用默认 BATCH_SIZE=10
   - 监控 Proposal 生成率
   - 大部分 entity 只有 1-5 个 candidates，Split/Refine 仍会生成

2. **中期**：优化执行模型
   - 按 entity 分组处理
   - 累积同一 entity 的 facts
   - 提高 Proposal 生成率

3. **长期**：完善架构
   - 统一 L1/L2/L3 创建路径
   - 解决 CONFLICT-001（ReflectionService vs EvolutionService）

---

## 7. 立即行动建议

### 选项 A：接受现状，执行全量（低风险）

**理由**：
- 当前 2,469 candidates 中，大部分 entity 只有 1-5 个 candidates
- 即使 BATCH_SIZE=10，Split/Refine proposals 仍会生成
- 不需要修改代码，可以快速验证流程

**预期结果**：
- Proposal 生成率约 10-30%
- 大部分是 L1（target_level=1）
- L2/L3 极少（需要高密度 entity）

### 选项 B：优化后执行（中风险）

**理由**：
- 解决语义边界问题
- 提高 Proposal 生成率
- 需要修改代码

**改动**：
- 添加 entity 级查询和分组逻辑
- 修改批量处理策略
- 预计 2-4 小时开发时间

---

## 8. 总结

**核心发现**：
1. ✅ 当前实现可以工作（低风险）
2. ⚠️ 但语义边界与执行边界混淆（需优化）
3. ⚠️ 大部分 entity 只有 1-5 个 candidates，BATCH_SIZE=10 是合理的
4. ⚠️ 大 entity（如 Windows: 2200）可能需要特殊处理

**最终建议**：
- **先执行 Phase 26-D 全量**（接受当前实现）
- **观察 Proposal 生成率和分布**
- **如有问题，再考虑优化执行模型**

---

*Report generated: 2026-08-15 01:30 UTC*
*Auditor: Phase 26-B.2 Reflection Semantic Aggregation Boundary Audit*
