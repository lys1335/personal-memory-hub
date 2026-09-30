# Phase 21 Post-Fix Pipeline Boundary Audit

**Date**: 2026-08-14
**Mode**: READ ONLY Audit
**Status**: Complete

---

## 1. Runtime Stability

### Cron 运行历史（修复后）

| 时间 | 状态 | Proposals | MemoryNodes |
|------|------|-----------|-------------|
| 2026-08-14 01:48:33 | completed | +20 | +17 |
| 2026-08-14 02:00:02 | completed | +20 | +18 |

### 错误统计

```
历史 UniqueViolation 总数: 256 次
Fix 后新错误: 0 次
Deduplicated warnings: 2 次 (正常行为)
```

### Proposal 与 MemoryNode 增长

```
日期         proposals_created  memory_nodes_created
2026-08-14  40                35
2026-08-13   7                 7
2026-08-12 2540              2540
```

### 当前数据库状态

```sql
-- Proposals
pending:  5
approved: 35
total:    40

-- MemoryNodes by level
L1: 25789
L2: 2
L3: 0

-- Candidates
candidate: 21152
confirmed: 42
```

---

## 2. EvidencePipelineService 实际职责

### 代码证据

```python
# evidence_pipeline_service.py:87-104
class EvidencePipelineService(BaseService):
    def __init__(self, session: AsyncSession):
        self.formulation = ContextWindowFormulator(session)
        self.interpreter = UserSemanticInterpreter()
        self.formation = FormationService(session)
        self.topics = TopicService(session)
        self.evolution = EvolutionService(session)
```

### Pipeline 流程

```
process_evidence(evidence_id, workspace_id)
  ↓
  Step 1: _form_context_window(evidence_id, workspace_id)
          → ContextWindowFormulator.formulate()
          → ContextWindow (in-memory, no DB)
  ↓
  Step 2: _interpret(context_window, evidence_id, workspace_id)
          → UserSemanticInterpreter.interpret()
          → InterpretationResult (in-memory, no DB)
  ↓
  Step 3: _form(interpretation, evidence_id, workspace_id)
          → FormationService.form()
          → Creates: Reconstruction + Candidate (DB)
  ↓
  Step 4: _extract_topics(interpretation, formation, workspace_id)
          → TopicService.extract_topics_from_summary()
          → Creates/Links Topics (DB)
  ↓
  Step 5: _evolve(candidate_id, workspace_id, entity_id, topic_ids)
          → EvolutionService.evolve()
          → Only if interpretation.user_owned == True
          → Creates: Memory evolution relationships (DB)
```

### 实际创建的数据

| 实体 | 由谁创建 | 说明 |
|------|----------|------|
| ContextWindow | ContextWindowFormulator | In-memory only |
| InterpretationResult | UserSemanticInterpreter | In-memory only |
| Reconstruction | FormationService | DB 写入 |
| Candidate | FormationService | DB 写入 |
| Topic | TopicService | DB 写入 |
| Memory evolution | EvolutionService | DB 写入（仅 user-owned）|

### 不创建的数据

| 实体 | 说明 |
|------|------|
| Proposal | EvidencePipelineService 不创建 Proposal |
| MemoryNode | EvidencePipelineService 不直接创建 MemoryNode |
| Evidence | 不处理 Evidence 摄入 |

---

## 3. ReflectionService 实际职责

### 代码证据

```python
# reflection_service.py:54-92
class ReflectionService(BaseService):
    async def reflect(...)
      ↓
      _acquire_scope()       → 查询 Candidates（无 pending proposal）
      ↓
      _run_engine_pipeline() → EvidenceEvolutionEngine + ReflectionEngine
      ↓
      _save_proposals()      → 创建 Proposal（DB）
      ↓
      _auto_approve_pending_proposals()
        ↓
        approve_proposal()   → 批准 Proposal + 创建 MemoryNode（DB）
```

### 完整职责清单

| # | 职责 | 方法 | 代码位置 |
|---|------|------|----------|
| 1 | Evidence scope acquisition | `_acquire_scope()` | reflection_service.py:1122 |
| 2 | Fact extraction | `_extract_facts()` | reflection_engine.py:147 |
| 3 | Proposal generation | `_generate_proposals()` | reflection_engine.py:244 |
| 4 | Proposal deduplication | `_save_proposals()` | reflection_service.py:1046 |
| 5 | Proposal approval | `approve_proposal()` | reflection_service.py:208 |
| 6 | MemoryNode creation | `approve_proposal()` | reflection_service.py:313 |
| 7 | L1 observation creation | `approve_proposal()` | reflection_service.py:313 |
| 8 | L2 Pattern creation | `approve_proposal()` | reflection_service.py:313 |
| 9 | L3 Belief creation | `approve_proposal()` | reflection_service.py:313 |
| 10 | Auto-approve logic | `_auto_approve_pending_proposals()` | reflection_service.py:986 |
| 11 | Cron execution | `reflect()` | app.py:1407 |
| 12 | Candidate status update | `approve_proposal()` | reflection_service.py:313 |
| 13 | Relationship creation | `approve_proposal()` | reflection_service.py:337 |

### 关键发现

**ReflectionService 实际承担的职责远超 "Reflection" 命名范围**：
- Evidence ingestion
- Candidate formation (通过 EvidenceEvolutionEngine)
- Proposal generation
- Proposal approval
- MemoryNode creation (L1/L2/L3)
- Historical evolution

---

## 4. Memory Pyramid Lifecycle

### 当前层级分布

```sql
level | count
------+-------
1     | 25789
2     | 2
```

### 每层创建者

| 层级 | 创建者 | 说明 |
|------|--------|------|
| L0 Evidence | ChatGPT Import | 原始数据摄入 |
| L1 Candidate | ReflectionService (via EvidenceEvolutionEngine) | 待处理候选 |
| L1 MemoryNode | ReflectionService (approve_proposal) | Observation |
| L2 MemoryNode | ReflectionService (approve_proposal) | Pattern |
| L3 MemoryNode | ReflectionService (approve_proposal) | Belief |

### 创建链路

```
Evidence (L0)
  ↓
  EvidenceEvolutionEngine.evolve()
  ↓
Candidate (L1 pending)
  ↓
  ReflectionEngine.reflect_pipeline()
  ↓
Proposal (L1 pending)
  ↓
  Auto-approve (confidence >= 0.9, level <= 3)
  ↓
MemoryNode (L1/L2/L3 active)
```

### 完整数据流

```
Step 1: _acquire_scope()
  SELECT ... FROM candidates
  WHERE status = 'candidate'
  AND NOT EXISTS (SELECT 1 FROM proposals WHERE candidate_id = candidates.id AND status = 'pending')

Step 2: EvidenceEvolutionEngine.evolve()
  - Extract facts via LLM
  - Build candidates with candidate_id lineage

Step 3: ReflectionEngine.reflect_pipeline()
  - Extract facts
  - Analyze interest trends
  - Generate proposals

Step 4: _save_proposals()
  - INSERT INTO proposals (P0 Fix: deduplicate by candidate_id)
  - Transaction boundary

Step 5: _auto_approve_pending_proposals()
  - SELECT proposals WHERE confidence >= threshold AND target_level <= max_level
  - For each: approve_proposal()

Step 6: approve_proposal()
  - UPDATE proposals SET status = 'approved'
  - INSERT INTO memory_nodes (level = target_level)
  - UPDATE candidates SET status = 'confirmed'
```

---

## 5. EvidencePipelineService vs ReflectionService

| Dimension | EvidencePipelineService | ReflectionService |
|---|---|---|
| Evidence ingestion | ❌ 不处理 | ❌ 不处理 |
| Context formation | ✅ ContextWindow | ❌ 不处理 |
| User interpretation | ✅ SemanticInterpreter | ❌ 不处理 |
| Reconstruction | ✅ FormationService | ❌ 不处理 |
| Candidate formation | ✅ FormationService | ✅ EvidenceEvolutionEngine |
| Proposal | ❌ 不创建 | ✅ 创建 |
| L1 MemoryNode | ❌ 不直接创建 | ✅ 创建 (approve_proposal) |
| L2 MemoryNode | ❌ 不直接创建 | ✅ 创建 (approve_proposal) |
| L3 MemoryNode | ❌ 不直接创建 | ✅ 创建 (approve_proposal) |
| Topic extraction | ✅ TopicService | ❌ 不处理 |
| Historical evolution | ✅ EvolutionService (user-owned) | ✅ EvolutionService (via approve_proposal relationships) |
| Transaction ownership | ✅ Owns transaction | ✅ Owns transaction (each method) |
| Cron | ❌ 未被调用 | ✅ 当前 Cron 调用者 |
| Phase 21 integration | ✅ Phase 21.1-21.8 | ❌ Phase 20 legacy |

### 核心差异

| 维度 | EvidencePipelineService | ReflectionService |
|------|------------------------|-------------------|
| 设计目标 | Evidence → Structured Candidate | Candidate → Proposal → Memory |
| 输入 | Single Evidence ID | Batch of Candidates |
| 输出 | Reconstruction + Candidate + Topics | Proposal + MemoryNode |
| 依赖 LLM | 否（用户语义解释） | 是（LLM fact extraction） |
| 事务边界 | 完整 pipeline | 每个方法独立事务 |

---

## 6. Architecture Verdict

### 回答用户假设

**假设 A**: EvidencePipelineService 应该理解为 "Evidence → structured candidate formation pipeline"
**结论**: ✅ **正确**

证据：
- 只接受单个 evidence_id 作为输入
- 通过 ContextWindow + Interpretation 形成结构化 Candidate
- 不处理批量候选
- 不生成 Proposal

**假设 B**: ReflectionService 应该理解为 "Memory reflection / abstraction / evolution pipeline"
**结论**: ✅ **正确**

证据：
- 接受 Candidate 批量作为输入
- 通过 LLM 提取 facts，生成 Proposal
- 通过 approve_proposal 创建 MemoryNode
- 处理 L1 → L2 → L3 的 Memory 层级演化

### 两者是否应该并存？

**结论**: ✅ **应该并存**

理由：
1. **职责分离清晰**：
   - EvidencePipelineService: Evidence → Candidate (单条，无 LLM)
   - ReflectionService: Candidate → Proposal → MemoryNode (批量，有 LLM)

2. **触发时机不同**：
   - EvidencePipelineService: 新 Evidence 到达时触发
   - ReflectionService: Cron 定时批量处理

3. **数据处理粒度不同**：
   - EvidencePipelineService: 单条 Evidence 深度处理
   - ReflectionService: 批量 Candidate 抽象演化

### 是否应该直接替换？

**结论**: ❌ **不应该直接替换**

理由：
1. 两者处理不同的数据阶段
2. ReflectionService 负责批量处理和 LLM 调用
3. EvidencePipelineService 负责结构化形成和 Topic 提取
4. 两者可以互补，但不能互相替代

### EvidencePipelineService 的正确层级

**定位为**: Evidence → Candidate 的 **Formation Pipeline**

```
Evidence (L0)
  ↓
ContextWindow (in-memory)
  ↓
Interpretation (in-memory)
  ↓
Reconstruction + Candidate (L1)
  ↓
Topics (linking)
```

### ReflectionService 的正确层级

**定位为**: Candidate → Memory 的 **Evolution Pipeline**

```
Candidate (L1 pending)
  ↓
Fact Extraction (LLM)
  ↓
Proposal (L1 pending)
  ↓
Approval (auto/manual)
  ↓
MemoryNode (L1/L2/L3 active)
```

### 两者之间的接口

**当前状态**: 无明确接口

**理想接口**:
```
EvidencePipelineService
  ↓
  output.candidate_id
  ↓
ReflectionService
  input: candidate_ids = [output.candidate_id]
```

**建议**: 在 Phase 22 或后续 Phase 中定义明确的接口。

---

## 7. Cron Verdict

### 当前 Cron 调用链

```python
# app.py:1386-1411
reflection_svc = ReflectionService(engine)
exec_result = await reflection_svc.reflect(
    workspace_id=workspace_id,
    scope="daily",
    limit=limit,
)
```

### 是否合理？

**结论**: ✅ **合理**

理由：
1. ReflectionService 承担完整的 Candidate → Memory 演化职责
2. Cron 需要批量处理候选池（_acquire_scope）
3. EvidencePipelineService 无法处理批量候选
4. 两者职责不同，Cron 调用 ReflectionService 是正确的

### EvidencePipelineService 应该由什么触发？

**建议**: 不通过 Cron 触发，而是通过以下方式：
1. Evidence 摄入完成时触发
2. API 端点手动触发
3. 独立的事件驱动任务

---

## 8. Phase 21.8 Reinterpretation

### 冻结文档定义

Phase 21.8 定义为：
```
Evidence → ContextWindow → Interpretation → Formation → Topic → Evolution
```

### 当前实现实际行为

实际实现为：
```
Evidence → ContextWindow → Interpretation → Formation → Topic → Evolution
```

### 是否存在设计偏差？

**结论**: ❌ **无明显偏差**

当前实现与文档定义一致。

### 重新评估 Phase 21.8 的定位

**原始理解（可能过宽）**:
- Phase 21.8 是 Cron 的替代方案
- EvidencePipelineService 应该接管整个 Memory 演化流程

**修正后的理解**:
- Phase 21.8 是一个独立的 Formation Pipeline
- 用于新 Evidence 到达时的结构化处理
- 与 ReflectionService 的批量演化职责不同

### 建议的架构调整（不在本阶段实施）

```
[New Evidence Arrival]
        ↓
EvidencePipelineService (Phase 21.8)
        ↓
  Reconstruction + Candidate + Topics
        ↓
ReflectionService (Phase 20, Cron)
        ↓
  Proposal → Approval → MemoryNode
```

两者关系：
- EvidencePipelineService: 结构化形成（单次，无 LLM）
- ReflectionService: 抽象演化（批量，有 LLM）
- 接口：EvidencePipelineService 输出的 Candidate 可进入 ReflectionService 的处理队列

---

## 9. 最终结论

### 核心问题回答

**Q: EvidencePipelineService 和 ReflectionService 到底是不是同一条 Pipeline？**

**A**: ❌ **不是同一条 Pipeline**

- EvidencePipelineService: Evidence → Candidate（Formation 阶段）
- ReflectionService: Candidate → Proposal → MemoryNode（Evolution 阶段）

**Q: EvidencePipelineService 是否更适合 Evidence → Candidate / L1 formation？**

**A**: ✅ **是**

证据：
- 代码职责清晰对应
- 不处理 Proposal 或 MemoryNode
- 单条 Evidence 处理模式

**Q: ReflectionService 是否更适合 L1 → L2 → L3 更高层 Memory Evolution？**

**A**: ✅ **是**

证据：
- approve_proposal 方法创建 L1/L2/L3 MemoryNode
- 处理批量 Candidate
- 当前 Cron 调用者

### 架构健康度评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 职责分离 | ⭐⭐⭐⭐ | 两者职责清晰分离 |
| 数据流 | ⭐⭐⭐ | 缺少明确接口定义 |
| 触发机制 | ⭐⭐⭐⭐ | Cron 调用正确 |
| 扩展性 | ⭐⭐⭐ | 接口需进一步设计 |

### 后续建议（非本阶段实施）

1. **Phase 22**: 定义 EvidencePipelineService 与 ReflectionService 的明确接口
2. **Phase 23**: 考虑将 EvidencePipelineService 的输出集成到 ReflectionService 的候选池
3. **ADR**: 记录两者职责划分的决策依据

---

**Audit complete. All findings documented.**
