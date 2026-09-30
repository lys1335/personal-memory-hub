# Phase 26-A.1 — L1 Creation Boundary Adjudication

## Executive Summary

经过全面的只读审计，发现了**关键架构设计**和**当前实现的差异**。

**核心结论**：
1. ✅ `approve_proposal()` **可以**创建 L1（当 target_level=1 时）
2. ✅ L1 创建路径**存在**：Candidate → Proposal → approve_proposal() → L1
3. ⚠️ 但当前实现中 entity_id 传递**可能存在问题**
4. ✅ Phase 26-B Canary **应该执行**，以验证实际行为

---

## 一、设计溯源结果

### 1.1 关键文档定义

**phase22-10-clean-rebuild-implementation-design.md**:

```markdown
### ReflectionService
| Aspect | Specification |
|--------|---------------|
| **Primary Duty** | L1 Evolution: Candidate → L1 MemoryNode |
| **Creates MemoryNode** | YES (L1 Observation only) |

### L1 Boundary
Input:  Candidate (with entity_id)
Process: Fact extraction → Proposal generation → Approval
Output: L1 MemoryNode (Observation)
```

**phase22-memory-pyramid-evolution-audit.md**:

```
ReflectionService.approve_proposal()
  → Direct SQL INSERT for L1 MemoryNode
  → NO call to EvolutionService
```

### 1.2 设计意图 vs 代码实现

| 方面 | 设计意图 | 代码实际 | 一致性 |
|------|----------|----------|--------|
| L1 创建者 | ReflectionService | ReflectionService | ✅ 一致 |
| L1 创建方式 | approve_proposal() | approve_proposal() | ✅ 一致 |
| target_level | 由 ReflectionEngine 决定 | 由 ReflectionEngine 决定 | ✅ 一致 |
| entity_id 传递 | 从 Candidate 到 L1 | **可能丢失** | ⚠️ 需验证 |

---

## 二、ReflectionEngine 的 target_level 决策逻辑

### 2.1 代码位置：reflection_engine.py:292-316

```python
source_level = 1  # Default for L1 Evidence
if candidates and entity_facts:
    first_fact = entity_facts[0]
    source_id = first_fact.get("source_ids", [None])[0]
    if source_id and source_id in candidate_by_id:
        candidate = candidate_by_id[source_id]
        source_level = candidate.get("level", candidate.get("source_level", 1))

max_level = 5  # L5 is the maximum abstraction level

if avg_confidence >= 0.8 and len(entity_facts) >= 3 and source_level < max_level:
    proposal_type = "Strengthen"
    target_level = source_level + 1  # L1→L2
elif avg_confidence >= 0.6 and len(entity_facts) >= 2 and source_level < max_level:
    proposal_type = "Create"
    target_level = source_level + 1  # L1→L2
elif avg_confidence >= 0.9:
    proposal_type = "Refine"
    target_level = source_level  # Refine at same level
else:
    proposal_type = "Split"
    target_level = source_level  # Keep at same level
```

### 2.2 关键发现

**当前 2,469 个 Candidate 的 source_level 分布**：
```sql
source_level | count
-------------+-------
           1 |  2469
```

**这意味着**：
- 所有 Candidate 的 source_level = 1（L1 级别）
- 只有当 len(entity_facts) >= 2 时，才会创建 target_level = 2 的 Proposal
- 由于事实密度低（92% 批次只有 1 个事实），大部分 Proposal 的 target_level = 1

**结论**：
- ✅ **大部分 Proposal 会是 target_level = 1**
- ✅ **approve_proposal() 会创建 L1 MemoryNode**
- ✅ **L1 创建路径是存在的**

---

## 三、approve_proposal() 的 entity_id 传递分析

### 3.1 代码位置：reflection_service.py:230-250

```python
# Get entity_id from candidate via proposal's candidate_id
candidate_id = prop.get("candidate_id")
if candidate_id:
    candidate_result = await conn.execute(
        text("SELECT entity_id FROM candidates WHERE id = :id LIMIT 1"),
        {"id": str(candidate_id)},
    )
    candidate_row = candidate_result.fetchone()
    if candidate_row and candidate_row[0]:
        entity_id = candidate_row[0]
else:
    logger.warning(
        "Proposal %s has no candidate_id, L1 will have NULL entity_id",
        proposal_id,
    )
```

### 3.2 关键发现

**entity_id 传递链**：
```
Candidate.entity_id (UUID) 
    ↓ FK: proposals.candidate_id
Proposal.candidate_id
    ↓ SELECT query in approve_proposal()
L1 MemoryNode.entity_id
```

**验证当前 2,469 个 Candidate 的 entity_id**：
```sql
SELECT COUNT(*) FROM candidates 
WHERE entity_id IS NOT NULL 
  AND entity_id != '00000000-0000-0000-0000-000000000000';
-- Result: 2469 (100%)
```

**结论**：✅ **所有 Candidate 都有有效的 entity_id，entity_id 传递链是完整的。**

---

## 四、三种候选架构分析

### Architecture A：当前代码实际支持的路径

```
Candidate (source_level=1)
    ↓ ReflectionEngine
Proposal (target_level=1, type=Refine/Split)
    ↓ approve_proposal()
L1 MemoryNode (level=1, type=Observation, entity_id from Candidate)
```

**优点**：
- ✅ 符合设计文档
- ✅ entity_id 传递完整
- ✅ target_level 逻辑清晰

**缺点**：
- ⚠️ 由于事实密度低，大部分 Proposal 都是 target_level=1
- ⚠️ L2/L3 需要 ≥2 facts，几乎不会触发

### Architecture B：Formation 阶段直接创建 L1（未实现）

```
Evidence → FormationService → L1 MemoryNode（直接）
```

**现状**：❌ 当前 FormationService 不创建 L1，只创建 Candidate

### Architecture C：通用路径（当前代码支持）

```
Candidate (source_level=N)
    ↓ ReflectionEngine
Proposal (target_level=N 或 N+1)
    ↓ approve_proposal()
MemoryNode (level=target_level)
```

**优点**：
- ✅ 支持 L1→L2→L3 多级演化
- ✅ target_level 由 ReflectionEngine 动态决定

**缺点**：
- ⚠️ 当前事实密度不足以触发 L2

---

## 五、关键设计确认

### 5.1 L1 创建所有者

**L1_CREATION_OWNER: ReflectionService**

代码证据：
- `reflection_service.py:208` — approve_proposal() 方法
- `reflection_service.py:326` — INSERT INTO memory_nodes (level=1)

### 5.2 L1 创建触发器

**L1_CREATION_TRIGGER: Proposal with target_level=1 AND confidence >= AUTO_APPROVE_THRESHOLD**

代码证据：
- `reflection_service.py:1011` — threshold = float(os.environ.get("AUTO_APPROVE_THRESHOLD", "0.9"))
- `reflection_service.py:1026` — SELECT ... WHERE confidence >= :threshold AND target_level <= :max_level

### 5.3 L1 创建路径

**L1_CREATION_PATH**:
```
Cron Task (type='evolution')
  → ReflectionService.reflect(workspace_id, scope='daily', limit=200)
    → _acquire_scope() → Query candidates WHERE status='candidate'
    → _run_engine_pipeline()
      → EvidenceEvolutionEngine.evolve() → Extract facts
      → ReflectionEngine.reflect_pipeline() → Generate proposals
    → _save_proposals() → INSERT proposals
    → _auto_approve_pending_proposals()
      → approve_proposal() → INSERT memory_nodes (level=1)
```

### 5.4 ReflectionService 职责

**REFLECTION_ROLE: L1 Evolution（从 Candidate 到 L1 MemoryNode）**

包括：
1. 获取 pending candidates
2. 使用 LLM 提取事实和生成 Proposal
3. 保存 Proposal 到数据库
4. 自动批准符合条件的 Proposal
5. 创建 L1/L2/L3 MemoryNode（根据 target_level）

### 5.5 EvolutionService 职责

**EVOLUTION_ROLE: L2/L3 Evolution（从 L1 历史到 Pattern/Belief）**

包括：
1. 按 entity_id 聚合历史 L1
2. 检查阈值（≥3 facts, confidence≥0.8 for L2; ≥2 facts, confidence≥0.6 for L2 Create）
3. 创建 L2 Pattern 或 L3 Belief

**重要**：当前 EvolutionService 只在 EvidencePipelineService 中被调用，不在 ReflectionService 中。

### 5.6 approve_proposal() 职责

**APPROVE_PROPOSAL_ROLE: 批准 Proposal 并创建对应层级的 MemoryNode**

- 当 target_level=1 → 创建 L1 Observation
- 当 target_level=2 → 创建 L2 Pattern
- 当 target_level=3 → 创建 L3 Belief

---

## 六、Candidate 语义确认

**CANDIDATE_SEMANTICS: Candidate 是 Evidence 解释后的中间产物，等待 Reflection 处理形成 L1**

具体含义：
1. Candidate 代表一条证据被解释后的"待处理记忆单元"
2. Candidate 有 entity_id（实体关联）
3. Candidate 有 evidence_chain（证据溯源）
4. Candidate 等待 ReflectionService 将其转化为 L1 MemoryNode
5. Candidate.status = 'candidate' 表示待处理，'confirmed' 表示已处理

---

## 七、发现的设计冲突

### CONFLICT-001: ReflectionService vs EvolutionService 边界

| 来源 | 说法 |
|------|------|
| phase22-10 文档 | ReflectionService 负责 L1 Evolution；EvolutionService 负责 L2/L3 |
| phase22-memory-pyramid 文档 | "ReflectionService does NOT use EvolutionService ← DESIGN GAP" |
| 当前代码 | ReflectionService 有 approve_proposal()，根据 target_level 创建 L1/L2/L3 |
| 当前代码 | EvolutionService 只在 EvidencePipelineService 中被调用 |

**影响**：
- ReflectionService 可以创建 L2/L3（通过 approve_proposal()）
- 但 EvolutionService 也可以创建 L2/L3（通过 evolve_entity_history()）
- 两条路径并存，可能造成重复创建

**建议裁决**：
1. **短期**：ReflectionService 通过 target_level 创建 L1/L2/L3
2. **长期**：统一使用 EvolutionService 处理 L2/L3，ReflectionService 只负责 L1

### CONFLICT-002: AUTO_APPROVE 阈值与事实密度

| 配置 | 值 | 影响 |
|------|-----|------|
| AUTO_APPROVE_THRESHOLD | 0.9 | 高置信度才批准 |
| AUTO_APPROVE_MAX_LEVEL | 3 | 最多到 L3 |
| Fact density | 92% 批次只有 1 fact | L2 创建条件（≥2 facts）很少满足 |

**影响**：
- 大部分 Proposal 会是 target_level=1（Refine/Split）
- 只有少数 Proposal 会是 target_level=2（Strengthen/Create）
- L2/L3 创建非常罕见

---

## 八、最终裁决

### L1_CREATION_OWNER:
**ReflectionService**（通过 approve_proposal() 方法）

### L1_CREATION_TRIGGER:
**Proposal with target_level=1 AND confidence >= AUTO_APPROVE_THRESHOLD (0.9)**

### L1_CREATION_PATH:
```
Candidate → ReflectionEngine → Proposal(target_level=1) → approve_proposal() → L1 MemoryNode
```

### REFLECTION_ROLE:
**从 Candidate 提取事实、生成 Proposal、自动批准、创建 L1/L2/L3 MemoryNode**

### EVOLUTION_ROLE:
**按 entity_id 聚合历史 L1、检测 Pattern/Belief、创建 L2/L3 MemoryNode**

### APPROVE_PROPOSAL_ROLE:
**根据 Proposal.target_level 创建对应层级的 MemoryNode（L1/L2/L3）**

### CANDIDATE_SEMANTICS:
**Evidence 解释后的中间产物，等待 Reflection 转化为 L1 MemoryNode**

### RECOMMENDED_ARCHITECTURE:
**Architecture A（当前实现）** — 保持 ReflectionService 负责 L1，EvolutionService 负责 L2/L3（可选增强）

### CURRENT_IMPLEMENTATION:
**PARTIALLY_CONFORMING** — L1 创建路径存在，但 L2/L3 由两条路径并存（ReflectionService + EvolutionService）

### CODE_CHANGES_REQUIRED:
**NO**（Phase 26-B 先验证，可能需要后续调整）

---

## 九、Phase 26-B Canary 决策

### GO / NO-GO: **GO（有条件）**

**条件**：
1. ✅ L1 创建路径存在且 entity_id 传递完整
2. ✅ 所有 2,469 个 Candidate 都有有效 entity_id
3. ✅ 大部分 Proposal 会是 target_level=1（符合 L1 创建预期）
4. ⚠️ 需要验证 AUTO_APPROVE 是否会意外批准 L2/L3

**Canary 目标**：
1. 验证 ReflectionService 能成功处理 10 个 Candidate
2. 确认 Proposal target_level 分布
3. 确认 L1 entity_id 正确性
4. 确认无重复创建

**风险缓解**：
1. 先设置 AUTO_APPROVE=false 进行测试
2. 验证后再开启 AUTO_APPROVE

---

## 十、等待用户裁决

**请确认**：
1. 是否接受"PARTIALLY_CONFORMING"的当前实现状态？
2. 是否允许 Phase 26-B 以 AUTO_APPROVE=false 开始测试？
3. 是否需要先解决 CONFLICT-001（双路径问题）再继续？

---

*Report generated: 2026-08-15*
*Auditor: Phase 26-A.1 L1 Creation Boundary Adjudication*
