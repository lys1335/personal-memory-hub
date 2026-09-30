# Phase 20 — Candidate Lifecycle Analysis Report

## 执行摘要

本轮调查揭示了 Candidate 生命周期的**严重设计缺陷**：
1. **代码与文档状态机不一致**
2. **状态转换代码完全缺失**
3. **所有 Candidates 永久卡在 `candidate` 状态**
4. **导致重复 Evolution 和重复 Proposals**

---

## 1. 当前代码实际状态机

### 1.1 代码定义的状态

**Repository 层** (`candidate_repository.py:217`):
```python
valid_statuses = ("candidate", "confirmed", "archived", "orphaned")
```

**ORM 模型** (`memory_models.py:705`):
```python
"""
Status: candidate, confirmed, archived, orphaned
"""
status: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate")
```

**Database 约束**:
```sql
-- 无 CHECK 约束！
-- 只有以下约束：
chk_candidate_type: CHECK (candidate_type IN ('pattern', 'belief'))
chk_candidate_has_evidence: CHECK (evidence_count >= 1)
chk_candidate_evidence_strength: CHECK (evidence_strength BETWEEN 0.0 AND 1.0)
chk_candidate_evidence_chain_not_empty: CHECK (jsonb_array_length(evidence_chain) > 0)
```

### 1.2 代码实际使用的状态

**Evolution 查询** (`reflection_service.py:1087`):
```python
WHERE status IN ('candidate', 'pending')
```

**Proposal 创建** (`reflection_service.py:932`):
```python
"status": "candidate"  # ← 新候选项设置为 candidate
```

**数据库实际值**:
```
candidate: 13,146
pending: 0
confirmed: 0
archived: 0
orphaned: 0
```

### 1.3 实际状态转换图

```
┌─────────────────────────────────────────────────────────────┐
│                      实际代码行为                            │
└─────────────────────────────────────────────────────────────┘

[EvidenceEvolutionEngine]
    ↓ creates
Candidate (status='candidate')
    ↓ Evolution processed
    ↓ (NO STATUS UPDATE!)
Candidate (status='candidate') ← 永远停留在这里
    ↓ 下次 Evolution 再次处理
    ↓ (NO STATUS UPDATE!)
...无限循环...

Proposals 生成:
    ↓
proposal (status='pending')
    ↓ auto-approve (conf >= 0.9)
proposal (status='approved')
    ↓ approve_proposal()
MemoryNode (L2/L3)
```

### 1.4 状态转换缺失清单

| 转换 | 设计期望 | 代码实际 | 状态 |
|------|----------|----------|------|
| candidate → confirmed | ✓ | ✗ | **缺失** |
| candidate → archived | ✓ | ✗ | **缺失** |
| candidate → orphaned | ✓ | ✗ | **缺失** |
| candidate → processed | ✗ | ✗ | **未定义** |
| candidate → pending | ? | 使用但未设置 | **混淆** |

---

## 2. 当前设计文档状态机

### 2.1 设计文档定义

**文档来源**: `docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md`

**第 11 节 - Reflection Workflow**:
```
Observation Pool
  ↓
Candidate Discovery
  ↓
Pattern Proposal
  ↓
Evidence Verification
  ↓
Pattern (confirmed)    ← 明确的设计状态
  ↓
Belief Evaluation
  ↓
Belief (confirmed)     ← 明确的设计状态
  ↓
State Activation
```

**第 10.2 节 - EvidenceEvolution Engine**:
```
* EvidenceEvolution Engine 产生的 Candidate 必须标记 `status = 'candidate'`。
* Candidate 不进入 vector_documents。
* Candidate 不用于 Context Builder。
```

**第 10.3 节 - Reflection Engine**:
```
**职责**：
* 对 Candidate 进行推理分析。
* 判断是否需要创建/强化/拆分/拒绝。
* 输出 Proposal（建议）。

**约束**：
* Reflection Engine 不直接创建 MemoryNode。
* Reflection Engine 不直接分析 Evidence。
* 所有决策输出为 Proposal，需经 Approval 才能成为 Memory。
```

### 2.2 设计文档中的状态定义

根据设计文档，Candidate 生命周期应该是：

```
candidate (待处理)
    ↓ Evolution + Reflection
pending (待审批) ← 文档未明确定义
    ↓ Review (手动或自动)
confirmed (已确认) → 创建 MemoryNode
    ↓
active (MemoryNode 状态)
```

**但是**：设计文档**没有明确规定** Candidate 在 Proposal 创建后应该更新为什么状态。

### 2.3 设计文档与代码的冲突

| 项目 | 设计文档 | 代码实现 |
|------|----------|----------|
| 合法状态 | candidate, confirmed, archived, orphaned | candidate, pending |
| 状态转换 | 未明确定义 | 完全没有 |
| Evolution 后 | 应该创建 Proposal | 创建 Proposal，但不更新 Candidate |
| Proposal approved 后 | 应该创建 MemoryNode | 创建 MemoryNode，但不更新 Candidate |
| Proposal rejected 后 | 应该标记 Candidate | 无处理 |

---

## 3. Code vs Design 差异

### 3.1 状态名称不一致

| 设计文档 | 代码实际 | 问题 |
|----------|----------|------|
| `candidate` | `candidate` | ✅ 一致 |
| `confirmed` | 不存在 | ❌ 代码未实现 |
| `archived` | 不存在 | ❌ 代码未实现 |
| `orphaned` | 不存在 | ❌ 代码未实现 |
| `pending` | `pending` (用于 Proposals) | ⚠️ 混淆：用于 Candidate 查询但未设置 |

### 3.2 状态转换缺失

**设计期望**:
```
candidate → confirmed (当 Proposal 被批准)
candidate → archived (当 Candidate 被弃用)
candidate → orphaned (当 Evidence 失效)
```

**代码实际**:
```
candidate → candidate (永不变)
```

### 3.3 查询条件不一致

**Repository 层**:
```python
valid_statuses = ("candidate", "confirmed", "archived", "orphaned")
```

**Service 层** (`reflection_service.py:1087`):
```python
AND status IN ('candidate', 'pending')
```

**问题**: `pending` 不在 Repository 定义的合法状态中！

---

## 4. `processed` 的正确语义分析

### 4.1 当前代码使用情况

搜索 `processed` 关键词：
```bash
grep -rn "processed" backend/src --include="*.py"
# 结果: 0 matches for candidate status
```

**结论**: `processed` 在当前代码中**从未被使用**。

### 4.2 设计文档中的使用

搜索设计文档：
```bash
grep -i "processed" docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md
# 结果: 无明确定义
```

**结论**: 设计文档也**未定义** `processed` 状态。

### 4.3 语义分析

**选项 A**: `processed` = "已处理过，不再重新处理"
- 优点: 防止重复 Evolution
- 缺点: 不符合设计文档的状态定义

**选项 B**: `processed` = "已生成 Proposal，等待审批"
- 优点: 符合工作流逻辑
- 缺点: 与 `pending` 语义重叠

**选项 C**: 不使用 `processed`，使用设计文档的 `confirmed`
- 优点: 符合设计文档
- 缺点: 需要理解 `confirmed` 的确切时机

### 4.4 推荐语义

基于设计文档第 11 节的工作流：

```
candidate (待处理)
    ↓ Evolution + Reflection
candidate (已生成 Proposal，等待审批) ← 应该保持 candidate 状态
    ↓ Proposal approved
confirmed (已确认) → 创建 MemoryNode
    ↓
(不再需要 Candidate，MemoryNode 独立存在)
```

**关键发现**: 设计文档**没有要求**在生成 Proposal 后更新 Candidate 状态。

Candidate 应该在**被批准并创建 MemoryNode 后**才变为 `confirmed`。

---

## 5. Proposal 生命周期与 Candidate 状态关系

### 5.1 情况 A: Evolution 成功 → Proposal 创建 → Proposal pending

**设计期望** (根据文档):
- Candidate 保持 `candidate` 状态
- 等待用户审批或自动批准

**代码实际**:
- Candidate 保持 `candidate` 状态 ✅
- Proposal 设置为 `pending` ✅
- **问题**: 下次 Evolution 会再次处理同一个 Candidate

**正确性**: ⚠️ **部分正确**
- 状态转换符合设计
- 但缺少"已生成 Proposal"的标记机制

### 5.2 情况 B: Evolution 成功 → Proposal auto-approved → Memory Node 创建

**设计期望** (根据文档):
- Candidate 应该变为 `confirmed`
- 或者保持 `candidate` 直到显式确认

**代码实际**:
- Candidate 保持 `candidate` 状态 ❌
- Proposal 变为 `approved` ✅
- MemoryNode 创建成功 ✅
- **缺失**: 没有更新 Candidate 状态

**正确性**: ❌ **错误**
- 应该更新 Candidate 为 `confirmed`
- 否则下次 Evolution 会再次处理

### 5.3 情况 C: Evolution 成功 → Proposal rejected

**设计期望** (根据文档):
- Candidate 应该变为 `orphaned` 或保持 `candidate`

**代码实际**:
- Candidate 保持 `candidate` 状态 ⚠️
- Proposal 变为 `rejected` ✅
- **缺失**: 没有更新 Candidate 状态

**正确性**: ⚠️ **可接受但非最优**
- 保持 `candidate` 允许重新生成 Proposal
- 但应该记录 rejection 历史

### 5.4 情况 D: Evolution 执行失败

**设计期望** (根据文档):
- Candidate 应该保持 `candidate` 状态（可重试）
- 或者标记为 `orphaned`（如果持续失败）

**代码实际**:
- Candidate 保持 `candidate` 状态 ✅
- Proposal 未创建 ✅
- **正确**: 符合设计

**正确性**: ✅ **正确**

### 5.5 情况 E: Evolution 成功 → 没有产生 Proposal

**设计期望** (根据文档):
- Candidate 应该变为 `confirmed`（如果是最终结论）
- 或者保持 `candidate`（如果需要更多证据）

**代码实际**:
- Candidate 保持 `candidate` 状态 ⚠️
- 无 Proposal 生成 ✅
- **缺失**: 没有判断是否需要推进 Candidate

**正确性**: ⚠️ **可接受但需优化**

---

## 6. 当前确认的设计缺陷

### 6.1 P0: 状态转换代码完全缺失

**证据**:
```python
# 搜索所有 UPDATE candidates SET status...
# 结果: 0 matches
```

**影响**:
- 所有 13,146 个 Candidates 永久停留在 `candidate` 状态
- 每次 Evolution 重新处理全部 Candidates
- 生成大量重复 Proposals

### 6.2 P1: 查询条件与设计不一致

**证据**:
```python
# repository/candidate_repository.py:217
valid_statuses = ("candidate", "confirmed", "archived", "orphaned")

# service/reflection_service.py:1087
AND status IN ('candidate', 'pending')  # 'pending' 不在合法状态中！
```

**影响**:
- 查询条件使用了未定义的状态 `pending`
- 可能导致未来状态定义变更时的兼容性问题

### 6.3 P1: Evidence API 不支持按 ID 查询

**证据**:
```python
# app.py:864-899
@app.get("/evidences")
async def list_evidences(
    workspace_id: str = Query(None),
    keyword: str = Query(None),  # 只有 keyword，没有 id
    limit: int = Query(5)
):
```

**影响**:
- Dashboard 无法显示 Proposal 的证据详情
- 用户看到"无证据记录"错误信息

### 6.4 P2: Legacy UUID 数据污染

**证据**:
```
8,829 candidates 引用 legacy UUID (12xxxx-9096-...)
15,662 evidences 使用 UUIDv7 (000000-019f-...)
```

**影响**:
- 坏证据链导致 Proposal 无法显示证据
- 可能影响 Evidence Verification 步骤

---

## 7. 修复前必须确定的设计决策

### 决策 1: Candidate 在 Proposal 生成后应该保持什么状态？

**选项 A**: 保持 `candidate`（允许重新生成）
- 优点: 简单，符合当前行为
- 缺点: 导致重复处理

**选项 B**: 标记为 `pending`（等待审批）
- 优点: 明确区分"待处理"和"待审批"
- 缺点: 需要修改查询条件

**选项 C**: 不更新状态，但添加"已处理时间"字段
- 优点: 保留历史信息
- 缺点: 需要修改表结构

**决策点**: 需要用户确认哪种语义符合设计意图。

### 决策 2: Proposal 批准后，Candidate 应该变为 `confirmed` 吗？

**选项 A**: 是，变为 `confirmed`
- 优点: 符合设计文档状态机
- 缺点: 无法重新生成 Proposal

**选项 B**: 否，保持 `candidate`
- 优点: 允许重新生成（如果之前被拒绝）
- 缺点: 不符合设计文档

**决策点**: 需要明确 `confirmed` 的语义是"已批准"还是"最终确认"。

### 决策 3: 如何处理现有的 13,146 个 `candidate` 状态的 Candidates？

**选项 A**: 批量更新为 `processed`（临时状态）
- 优点: 立即解决重复问题
- 缺点: 引入非设计状态

**选项 B**: 保持现状，仅修复后续逻辑
- 优点: 不破坏现有数据
- 缺点: 历史数据仍然重复

**选项 C**: 批量清理，只保留最近的
- 优点: 减少数据量
- 缺点: 可能丢失有用信息

**决策点**: 需要评估数据量和业务价值。

### 决策 4: Legacy UUID 证据链如何处理？

**选项 A**: 删除引用 legacy UUID 的 Candidates
- 优点: 清理脏数据
- 缺点: 可能丢失有效信息

**选项 B**: 标记为 `orphaned`
- 优点: 保留数据，标记问题
- 缺点: 需要额外处理逻辑

**选项 C**: 尝试修复证据链
- 优点: 数据完整性
- 缺点: 工作量巨大

**决策点**: 需要评估 Legacy UUID 的重要性。

---

## 8. 状态机对比总结

### 8.1 设计文档状态机

```
candidate → confirmed → (MemoryNode created)
    ↓
archived (弃用)
    ↓
orphaned (证据失效)
```

### 8.2 代码实际状态机

```
candidate ──────────────────────────────────→ candidate
    ↓ (Evolution)                              ↓ (永远)
    └──────────────────────────────────────────┘
    
Proposal: pending → approved → (MemoryNode)
           ↓
         rejected
```

### 8.3 关键差异

| 方面 | 设计 | 代码 |
|------|------|------|
| 状态转换 | 有明确定义 | **完全缺失** |
| confirmed 状态 | 应该设置 | **从未设置** |
| archived 状态 | 应该支持 | **从未使用** |
| orphaned 状态 | 应该支持 | **从未使用** |
| pending 状态 | 未定义 | **被使用但未设置** |

---

## 9. 建议的修复路径

### Phase 1: 紧急修复（P0）

**E0**: 添加 Candidate 状态更新逻辑
```python
# 在 approve_proposal() 中
await conn.execute(text("""
    UPDATE candidates 
    SET status = 'confirmed' 
    WHERE id = :candidate_id
"""), {"candidate_id": proposal_candidate_id})
```

**E1**: 修复 Evidence API
```python
@app.get("/evidences")
async def list_evidences(
    workspace_id: str = Query(None),
    id: str = Query(None),  # 添加 id 参数
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

### Phase 2: 设计对齐（P1）

**E2**: 统一状态定义
- 删除 `pending` 在 Candidate 查询中的使用
- 明确 `confirmed` 的触发时机

**E3**: 添加状态转换日志
- 记录每次状态变更的原因和时间

### Phase 3: 数据清理（P2）

**E4**: 清理 Legacy UUID 引用
- 标记或删除引用不存在 evidence 的 candidates

**E5**: 处理现有 13,146 个 Candidates
- 根据业务需求决定保留或清理

---

## 10. 结论

### 当前状态

1. **设计文档定义**: Candidate 有 4 种状态（candidate, confirmed, archived, orphaned）
2. **代码实现**: 只使用 `candidate` 状态，从未更新
3. **数据库**: 所有 13,146 个 Candidates 都是 `candidate` 状态
4. **后果**: 每次 Evolution 重复处理所有 Candidates，生成大量重复 Proposals

### 核心问题

**不是"如何处理坏 Proposals"**，而是**"如何修复 Candidate 生命周期管理"**。

删除坏 Proposals 只是治标，不修复状态机问题，坏 Proposals 会再次生成。

### 建议行动

1. **立即**: 修复 Evidence API（E0）
2. **短期**: 确定 Candidate 状态转换语义（决策 1-4）
3. **中期**: 实现状态转换代码（Phase 1）
4. **长期**: 清理历史数据（Phase 3）

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下一步**: 等待用户确认设计决策 1-4
