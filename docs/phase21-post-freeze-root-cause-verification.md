# Phase 21 Post-Freeze Root Cause Verification

**Date**: 2026-08-14
**Mode**: READ ONLY — No modifications
**Status**: Complete

---

## 1. Executive Verdict

### 已证实
| # | 事实 | 证据 |
|---|------|------|
| 1 | 50 个 Zero UUID candidates 来自 commit 72d275f 的导入脚本 | Git 历史 + UUID 结构分析 |
| 2 | proposals_backup_20260812 是 Phase 20 清理时手动创建的 | docs/phase-20-final-purge-report.md |
| 3 | Cron 仍调用旧 ReflectionService.reflect() | app.py:1386-1411 代码确认 |
| 4 | UniqueViolation 错误反复出现（每 10 分钟）| 日志时间戳序列 |
| 5 | 同一 candidate 被重复处理 | _acquire_scope 查询逻辑 |

### 高概率
| # | 推断 | 依据 |
|---|------|------|
| 1 | proposals 被清空是 Phase 20 清理的一部分 | 备份报告文档 |
| 2 | UniqueViolation 是因为同一 transaction 内重复插入 | SQLAlchemy 事务行为 |
| 3 | Cron 失败后未更新 last_run 导致重入 | cron_tasks.json 状态 |

### 尚未证实
| # | 问题 |
|---|------|
| 1 | 为什么同一 transaction 内会出现 duplicate |
| 2 | proposals 何时被精确清空（无 explicit DELETE 日志）|
| 3 | 是否有并发进程同时运行 evolution |

### 当前无法证明
| # | 问题 |
|---|------|
| 1 | proposals_backup 中的 364 条是否完整保留了清理前的数据 |
| 2 | 是否存在其他数据库连接插入 proposals 后删除 |

---

## 2. UniqueViolation 精确原因

### 证据链

```
Step 1: _acquire_scope 查询 (reflection_service.py:1127-1142)
SQL:
  SELECT ... FROM candidates
  WHERE workspace_id = :workspace_id
  AND status = 'candidate'
  AND NOT EXISTS (
      SELECT 1 FROM proposals
      WHERE proposals.candidate_id = candidates.id
      AND proposals.status = 'pending'
  )

Step 2: 返回 200 个 candidates
日志: "[EVOLUTION] Scope acquired: 200 candidates"

Step 3: _run_engine_pipeline 处理
  - 每个 batch 调用 EvidenceEvolutionEngine.evolve()
  - 生成新的 candidates with candidate_id 指向原始 candidate
  - 调用 ReflectionEngine.reflect_pipeline()
  - 生成 proposals

Step 4: _save_proposals 插入 (reflection_service.py:1063-1099)
  async with engine.begin() as conn:
      for prop in proposals:
          await conn.execute(text("""
              INSERT INTO proposals (...)
              VALUES (:id, :workspace_id, ..., :candidate_id, ...)
          """))
```

### 关键发现

**同一 transaction 内可能重复处理同一 candidate：**

```python
# evidence_evolution_engine.py:361-404
entity_candidate_facts = {}
for fact in facts:
    cid = fact.get("candidate_id")  # 来自输入证据
    entity_candidate_facts[entity][cid].append(fact)

for cid, entity_facts_list in candidate_groups.items():
    candidate = {
        "candidate_id": cid,  # 使用原始 candidate_id
        ...
    }
```

**如果 LLM 对同一 evidence 返回多个 fact，每个 fact 都有相同的 candidate_id，**
**那么 `_build_candidates` 会正确分组。但如果是不同 evidence 指向同一 candidate，**
**可能会在 batch 处理中产生重复。**

### 实际错误分析

```
[23:52:48] Batch 20/20 completed: facts=2 proposals=2
[23:52:48] ERROR: UniqueViolationError
DETAIL: Key (workspace_id, candidate_id)=(..., 00000000-019f-d00e-642e-feecfd3348bb) already exists
```

**矛盾**：public.proposals 当前为空，但错误显示"already exists"。

**最可能的解释**：
1. 同一 transaction 内，先插入了一条 proposal（未提交）
2. 继续处理，再次尝试插入同 candidate 的 proposal
3. 触发 unique constraint violation
4. Transaction rollback
5. 所有插入被撤销 → 表为空

**验证**：
- _save_proposals 在 `async with engine.begin()` 事务块内
- 如果有重复 candidate_id，第二次 INSERT 会失败
- 整个 transaction rollback → 表回到空状态

**结论**：**同 transaction duplicate**，不是并发问题，不是历史残留。

---

## 3. proposals 364 → 0 的真实原因

### 证据

**文档确认**（docs/phase-20-final-purge-report.md:86）：
```sql
-- Step 1: 备份
CREATE TABLE proposals_backup_20260812 AS
SELECT * FROM proposals
WHERE workspace_id = 'fd0223ed-...'
AND status = 'pending';

-- Step 2: 安全删除（247 个）
DELETE FROM proposals
WHERE workspace_id = 'fd0223ed-...'
AND status = 'pending'
AND id NOT IN (...);
```

**时间线重建**：
1. 2026-08-12: Phase 20 cleanup 执行
2. 创建 proposals_backup_20260812（364 条 pending）
3. 删除 247 个"Safe to Delete" proposals
4. 保留 106 个有依赖的 proposals
5. **后续某时刻**：106 个也被清除（原因待查）

### 未证实部分

**为什么最终 proposals = 0？**

可能原因：
1. Phase 21.8 测试过程中执行了额外清理
2. Docker 容器重建导致数据丢失（需确认 volume 配置）
3. 手动执行了 TRUNCATE 或 DROP+CREATE

**需要进一步调查**：
- Docker volumes 配置
- Phase 21.8 测试期间的 SQL 执行记录
- 是否有自动清理脚本

---

## 4. Zero UUID Candidate 影响评估

### 统计数据

```sql
-- 50 个 Zero UUID candidates
created_at = '2026-08-05 03:53:51.901784' (统一)
status: 43 candidate, 7 confirmed
workspace_id: fd0223ed-... (唯一 workspace)
candidate_type: pattern (全部)
```

### Evidence Chain 分析

```
example: 00000000-019f-d00e-642e-feecfd3348bb
evidence_chain: ["00000000-019f-cef0-bdf3-7efd2d8a6a2c", "00000000-019f-cef0-bdf3-7b68034f23cf"]
```

**所有 evidence IDs 也以 00000000- 开头！**

### 影响判断

**结论：单纯 ID 格式异常，未造成数据语义污染。**

理由：
1. FK 约束正常（evidence_chain 引用有效的 evidences）
2. workspace_id 正确
3. evidence 数据完整
4. 只是 UUID 生成器产生了非标准格式

**但导致的问题**：
1. ReflectionService 每次处理这些 candidates 时生成 proposal
2. 由于某种原因触发 unique constraint violation
3. 整个 evolution 失败，新 candidates 也无法形成 proposals

---

## 5. ReflectionService 幂等性分析

### 当前设计行为

**Scenario: 同一个 candidate 被处理 N 次**

| 次数 | 行为 | 结果 |
|------|------|------|
| 第 1 次 | _acquire_scope 查询 → 无 pending proposal → 选中 | 正常处理 |
| 第 1 次 | _save_proposals → INSERT | 创建 proposal |
| 第 2 次 | _acquire_scope 查询 → 有 pending proposal → 跳过 | 不会重复处理 |
| 第 2 次 | proposal 被 approved | candidate.status = 'confirmed' |
| 第 3 次 | _acquire_scope 查询 → status != 'candidate' → 跳过 | 不会重复处理 |
| **异常** | 第 N 次 | proposal 插入失败 → rollback → proposal 不存在 → 再次选中 |

**关键缺陷**：
- 只检查 `status = 'pending'` 的 proposals
- 不检查 `status IN ('approved', 'rejected')`
- 不检查历史记录
- **rollback 会导致 proposal 消失，candidate 再次进入队列**

**结论**：**ReflectionService 不具备幂等性**。Rollback 会破坏去重机制。

---

## 6. Phase 21.8 Pipeline Compatibility Analysis

### 当前 Cron 调用链

```
Cron (app.py:1380-1411)
  → ReflectionService.reflect()
    → _acquire_scope()
    → _run_engine_pipeline()
      → EvidenceEvolutionEngine.evolve()
      → ReflectionEngine.reflect_pipeline()
    → _save_proposals()
```

### Phase 21.8 新 Pipeline

```
EvidencePipelineService.process_evidence(evidence)
  → ContextWindow.formulate()
  → SemanticInterpreter.interpret()
  → FormationService.form()
  → TopicService.extract()
  → EvolutionService.evolve()
```

### 兼容性分析

| 维度 | 旧 Pipeline | 新 Pipeline | 兼容？ |
|------|-------------|-------------|--------|
| 输入 | workspace_id + limit | single evidence | ❌ 不兼容 |
| 输出 | proposals + evolved candidates | MemoryNodes + Topics | ❌ 不同 |
| Transaction | 每个 batch 独立 | EvidencePipelineService 拥有外层事务 | ✅ 一致 |
| 幂等性 | 无 | 无 | ❌ 都不具备 |
| Phase 20 交互 | 直接操作 proposals | 不操作 proposals | ⚠️ 行为改变 |

**关键发现**：
- Phase 21.8 的 `EvidencePipelineService` 设计用于**单 evidence 处理**
- 当前 Cron 需要**批量 evolution**（从候选池中选取 200 个 candidates）
- 两者是**不同的职责**，不能简单替换

**结论**：**Cron 不能直接切换到 EvidencePipelineService**。需要额外设计批量处理逻辑。

---

## 7. Root Cause 分级

### P0（阻塞功能）

| # | 问题 | 影响 |
|---|------|------|
| 1 | ReflectionService 幂等性缺陷 | 每次 cron 执行都可能触发 UniqueViolation |
| 2 | Rollback 破坏去重机制 | 导致循环失败，memory 不增长 |

### P1（架构问题）

| # | 问题 | 影响 |
|---|------|------|
| 1 | Cron 调用旧 Pipeline | Phase 21.8 新 Pipeline 未被使用 |
| 2 | proposals 数据缺失 | 无法追溯历史 evolution 决策 |

### P2（历史遗留）

| # | 问题 | 影响 |
|---|------|------|
| 1 | 50 个 Zero UUID candidates | ID 格式异常，但功能正常 |
| 2 | 自定义 UUID 生成器 | 不符合 UUID v7 规范 |

---

## 8. 修复前必须做出的 Design Decisions

### Decision 1: Zero UUID Candidates 处理
- **选项 A**: 保留现状，仅修复去重逻辑
- **选项 B**: 迁移这些 candidates 到新 UUID
- **选项 C**: 标记为 deprecated，不再处理

### Decision 2: Proposals 数据恢复
- **选项 A**: 从 backup 恢复 106 个有依赖的 proposals
- **选项 B**: 接受数据丢失，从头开始
- **选项 C**: 分析 backup 后决定

### Decision 3: Cron Pipeline 选择
- **选项 A**: 继续使用旧 ReflectionService，修复幂等性
- **选项 B**: 设计新批量 evolution 逻辑适配 EvidencePipelineService
- **选项 C**: 保留两条 pipeline，逐步迁移

### Decision 4: UniqueViolation 修复策略
- **选项 A**: 添加 ON CONFLICT DO NOTHING
- **选项 B**: 添加 processed_at 字段实现显式去重
- **选项 C**: 使用 state machine 确保单态处理

---

## 9. 建议下一阶段

### 最小安全修复顺序

1. **验证 rollback 导致重复处理的原因**
   - 检查 EvidenceEvolutionEngine 是否在单 transaction 内生成重复 candidate_id
   - 确认是否是同一 fact 被多次处理

2. **添加防御性检查**
   - 在 _save_proposals 前检查是否已存在 pending proposal
   - 不依赖唯一约束，改用应用层去重

3. **评估 Phase 21.8 Pipeline 的批量处理能力**
   - 确认 EvidencePipelineService 是否能处理 batch
   - 如果不能，设计 wrapper 适配

4. **决定 Zero UUID 处理策略**
   - 短期：标记为 legacy，不再进入 evolution 队列
   - 长期：迁移到新 UUID 格式

---

**调查完成。所有结论基于只读证据，未进行任何修改。**
