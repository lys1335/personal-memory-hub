# Phase 21.8 Stage B — Integration Design Conflict Review

**审查日期**: 2026-08-13  
**审查范围**: Phase 21.8 Stage A Audit 中的 Design Conflicts  
**审查类型**: READ-ONLY DESIGN REVIEW  
**最终结论**: ⚠️ 发现关键 Design Conflicts，需修正后才能进入 Implementation

---

## 1. 架构违规发现

### 1.1 关键发现：ReflectionService 违规调用 Engine

```python
# backend/src/backend/service/reflection_service.py:724-766
from backend.engine.evidence_evolution_engine import EvidenceEvolutionEngine
# ...
evidence_engine = EvidenceEvolutionEngine()  # ❌ 直接创建 Engine 实例
evolution_result = await evidence_engine.evolve(...)  # ❌ Service 直接调用 Engine
```

**架构原则（D4）**:
> "No Cross-Engine Calls: Engine A never calls Engine B"
> "Composition Over Inheritance: internal composition uses composition"

**问题**: Service 不应该直接创建和调用 Engine。Engine 应该是 Service 的依赖注入，而不是运行时创建。

### 1.2 EvolutionEngine vs EvidenceEvolutionEngine 不一致

| 维度 | EvidenceEvolutionEngine (Phase 20) | EvolutionEngine (Phase 21.7) |
|------|-----------------------------------|------------------------------|
| 基类 | EngineBase | 无（混合体） |
| Session | 无（无状态） | 有（有状态） |
| 事务 | 不由 Engine 管理 | 未定义 |
| 调用方 | ReflectionService（违规） | 无外部调用 |

**问题**: Phase 21.7 EvolutionEngine 不遵循 EngineBase 模式，导致架构不一致。

---

## 2. P0-1 根因分析：Integration Entry Point

### 2.1 当前状态

```
Evidence (ingested by MemoryService)
    ↓
[ContextWindow] — 孤立，无调用
[InterpretationResult] — 孤立，无调用
[FormationService] — 孤立，无调用
[TopicService] — 孤立，无调用
[EvolutionEngine] — 孤立，无调用
```

### 2.2 架构原则检查

根据 D3.1 BaseService：
> "Transaction belongs to Service, not Repository"
> "One Use Case = One Transaction"

**现状**:
- BaseService 提供 `_commit()` 和 `_rollback()` 方法
- MemoryService 正确使用这些方法
- FormationService **不继承 BaseService**，没有事务管理

### 2.3 编排者选择

**选项 A**: 扩展现有 Service

| 现有 Service | 能否承担 | 理由 |
|-------------|---------|------|
| MemoryService | ❌ | 职责已过重（capture, import, merge, archive, lifecycle） |
| ReflectionService | ❌ | 职责已明确（batch evolution via proposals） |
| EntityService | ❌ | 职责单一（entity CRUD） |

**选项 B**: 新增 Phase 21 Orchestration Service

**推荐方案**: ✅ 新增 Service

**理由**:
1. Phase 21 Pipeline 是全新的业务场景（实时 Evidence → Memory）
2. 与 Phase 20 批量 Evolution 有本质区别
3. 需要独立的 transaction 管理
4. 符合单一职责原则

---

## 3. P0-2 根因分析：FormationService Transaction

### 3.1 现有事务模式

```python
# MemoryService.capture_memory() 示例：
memory_id = await self._memory_node_repo.create(memory_node)
await self._commit(self._memory_node_repo.session)  # ← Service 负责 commit
```

**关键发现**:
1. Service 继承 BaseService
2. BaseService 提供 `_commit()` 和 `_rollback()`
3. Repository 只 flush，不 commit

### 3.2 FormationService 问题

```python
# 当前实现（错误）：
class FormationService:  # ❌ 不继承 BaseService
    def __init__(self, session: AsyncSession):
        self.session = session
        # ...
    
    async def form(self, ...):
        # 创建 Reconstruction
        reconstruction = await self._create_reconstruction(...)
        # 创建 Candidate
        candidate = await self._create_candidate(...)
        # ❌ 没有 commit！
        return FormationResult(...)
```

**问题清单**:
1. FormationService 不继承 BaseService
2. 没有 `_commit()` 和 `_rollback()` 方法
3. 如果中间失败，数据处于不确定状态

### 3.3 修正方案

**方案 A**: FormationService 继承 BaseService（推荐）

```python
class FormationService(BaseService):  # ✅ 继承 BaseService
    def __init__(self, session: AsyncSession):
        super().__init__("FormationService")
        self.session = session
        # ...
    
    async def form(self, ...):
        try:
            # 创建逻辑...
            await self._commit(self.session)  # ✅ Service 负责 commit
            return FormationResult(success=True, ...)
        except Exception as e:
            await self._rollback(self.session, str(e))  # ✅ 正确回滚
            return FormationResult(success=False, error=str(e))
```

---

## 4. P0-3 根因分析：EvolutionEngine Rollback

### 4.1 EvolutionEngine 设计检查

```python
class EvolutionEngine:
    """Domain engine for Historical Memory Evolution."""
    
    def __init__(self, session: AsyncSession):
        self.session = session  # ❌ Engine 不应该持有 session
        # ...
    
    async def evolve(self, ...):
        # 创建 MemoryNode
        memory_node = await self._create_memory_node(candidate)
        # 创建 Relationship
        await self._create_relationship(...)
        # ❌ 没有 commit，没有 rollback
```

**架构违规**:
1. Engine 不应该持有 session（违反 Engine 无状态原则）
2. Engine 不应该有事务逻辑
3. 当前设计是 Service-like 的 Engine

### 4.2 正确的 Engine 设计

```python
class EvolutionEngine(EngineBase):  # ✅ 继承 EngineBase
    """Domain engine for Historical Memory Evolution."""
    
    def __init__(self):
        super().__init__("EvolutionEngine")
        # ❌ 不持有 session
    
    async def evolve(self, *, candidate_id, workspace_id, entity_id=None, topic_ids=None):
        # 返回 DomainResult，不管理事务
        # 业务逻辑在 Service 层实现
        pass
```

### 4.3 两种修正方案

**方案 A**: EvolutionEngine 改为真正的 Engine（推荐，架构一致）

```python
class EvolutionEngine(EngineBase):
    def __init__(self):
        super().__init__("EvolutionEngine")
    
    async def detect_relationships(self, *, candidate, historical_nodes):
        # 纯领域逻辑，无数据库访问
        return RelationshipDetectionResult(...)
    
    async def determine_decision(self, *, detection_result, candidate):
        # 纯领域逻辑
        return EvolutionDecision(...)
```

**方案 B**: EvolutionEngine 改为 EvolutionService（快速修复）

```python
class EvolutionService(BaseService):  # 改名
    def __init__(self, session: AsyncSession):
        super().__init__("EvolutionService")
        self.session = session
        # ... 现有逻辑保持不变
```

**推荐方案**: **方案 A**（改造为真正 Engine），但工作量较大。

**临时方案**: 在 EvidencePipelineService 中管理 EvolutionEngine 的事务。

---

## 5. Design Conflict 清单

### 5.1 P0 Conflicts

| 编号 | 冲突 | 影响 | 解决方案 |
|------|------|------|----------|
| P0-1 | 无 Integration Entry Point | Pipeline 无法启动 | 新增 EvidencePipelineService |
| P0-2 | FormationService 无 transaction 管理 | 数据可能不一致 | 继承 BaseService |
| P0-3 | EvolutionEngine 设计违规 | 架构不一致 | 改为 EngineBase 或继承 BaseService |
| P0-4 | ReflectionService 违规调用 Engine | 架构违规 | 需重构（Phase 21.8 范围外） |

### 5.2 P1 Conflicts

| 编号 | 冲突 | 影响 | 解决方案 |
|------|------|------|----------|
| P1-1 | entity_id 解析失败时 Formation 失败 | 无 fallback | 添加默认值或跳过 |
| P1-2 | Topic extraction 规则过于简单 | 质量低 | LLM extraction（Deferred） |
| P1-3 | Phase 20/21 Evolution 服务分工不明确 | 可能重复执行 | 明确分工 |

### 5.3 P2 Conflicts

| 编号 | 冲突 | 影响 | 解决方案 |
|------|------|------|----------|
| P2-1 | Semantic similarity 计算简单 | 关系检测准确性 | Embedding（Deferred） |
| P2-2 | Topic clustering 未实现 | Topic 去重 | LLM clustering（Deferred） |

---

## 6. Transaction Ownership Decision

### 6.1 原则

根据 BaseService 文档：
> "Transaction belongs to Service, not Repository"
> "One Use Case = One Transaction"

### 6.2 决策

```
Phase 21 Pipeline 事务边界：

Evidence (已存在)
    ↓
ContextWindow (内存，无事务)
    ↓
InterpretationResult (内存，无事务)
    ↓
EvidencePipelineService (事务开始)
    ├── FormationService.form()  ← 同事务
    ├── TopicService.extract()   ← 同事务
    └── EvolutionService.evolve() ← 同事务
    ↓
PipelineResult (事务提交)
```

**关键**: 所有写操作在同一个 transaction 中，要么全部成功，要么全部回滚。

### 6.3 FormationService 事务责任

**错误设计**（当前）:
```python
class FormationService:
    async def form(self, ...):
        # 自己管理事务 ❌
```

**正确设计**:
```python
class FormationService:  # 不继承 BaseService，不管理事务
    async def form(self, session, ...):
        # 使用传入的 session，不 commit
        # 只负责业务逻辑

# EvidencePipelineService 管理事务
class EvidencePipelineService(BaseService):
    async def process_evidence(self, ...):
        try:
            await formation_service.form(self.session, ...)
            await topic_service.extract(self.session, ...)
            await evolution_service.evolve(self.session, ...)
            await self._commit(self.session)  # ✅ Service 负责 commit
        except Exception as e:
            await self._rollback(self.session, str(e))  # ✅ Service 负责 rollback
```

---

## 7. Phase 21 Orchestration Decision

### 7.1 新 Service 定义

**名称**: `EvidencePipelineService`

**位置**: `backend/src/backend/service/evidence_pipeline_service.py`

**职责**:
1. 协调 Phase 21 Pipeline 全流程
2. 管理 transaction
3. 错误处理和日志
4. 不直接执行领域逻辑（委托给各组件）

**输入**:
- evidence_id: UUID
- workspace_id: UUID

**输出**:
- PipelineResult（包含 reconstruction_id, candidate_id, topic_ids）

**依赖**:
- session: AsyncSession（注入）
- FormationService（委托）
- TopicService（委托）
- EvolutionEngine（委托，作为纯 Engine）

### 7.2 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 是否新增 Service | ✅ 是 | 职责清晰，不污染现有 Service |
| 是否继承 BaseService | ✅ 是 | 符合 transaction 原则 |
| Evolution 是否同步 | ✅ 是 | 同一 transaction |
| 失败是否回滚 | ✅ 是 | 保证数据一致性 |
| FormationService 是否继承 BaseService | ❌ 否 | 作为纯业务逻辑组件 |

---

## 8. 最终调用链

### 8.1 完整 Pipeline

```
HTTP Request (POST /evidences)
    ↓
RESTAdapter
    ↓
MemoryService.capture_evidence()
    ↓
evidence_repo.create(evidence)
    ↓ [after insert hook]
EvidencePipelineService.process_evidence()
    ↓
Step 1: ContextWindowFormulator.formulate()  ← 内存操作
    ↓
Step 2: UserSemanticInterpreter.interpret()  ← 内存操作
    ↓
Step 3: FormationService.form(session, ...)   ← 同事务
    ↓
Step 4: TopicService.extract_and_link(session, ...) ← 同事务
    ↓
Step 5: EvolutionEngine.detect_and_evolve(session, ...) ← 同事务
    ↓
Step 6: _commit(session)  ← EvidencePipelineService 负责
    ↓
PipelineResult
```

### 8.2 Hook 集成点

**方案 A**: EvidenceRepository.after_insert() hook

```python
class EvidenceRepository(BaseRepository):
    async def create(self, evidence: Evidence) -> UUID:
        eid = await super().create(evidence)
        await self._trigger_pipeline(evidence)
        return eid
    
    async def _trigger_pipeline(self, evidence: Evidence):
        from backend.service.evidence_pipeline_service import EvidencePipelineService
        service = EvidencePipelineService(self.session)  # 传入 session
        await service.process_evidence(
            evidence_id=evidence.id,
            workspace_id=evidence.workspace_id,
        )
```

**方案 B**: API 层触发（推荐）

```python
@app.post("/evidences")
async def create_evidence(body: dict, session: AsyncSession = Depends(get_session)):
    # 创建 Evidence
    evidence = await evidence_repo.create(...)
    
    # 触发 Pipeline（可选）
    if os.environ.get("PHASE21_PIPELINE_ENABLED", "false") == "true":
        pipeline = EvidencePipelineService(session)
        await pipeline.process_evidence(
            evidence_id=evidence.id,
            workspace_id=evidence.workspace_id,
        )
    
    return {"evidence_id": evidence.id}
```

**推荐方案**: **方案 B**（API 层触发），理由：
1. 更清晰的控制流
2. 便于测试
3. 避免 Repository 层耦合业务逻辑

---

## 9. Failure / Rollback Strategy

### 9.1 整体策略

```python
class EvidencePipelineService(BaseService):
    async def process_evidence(self, *, evidence_id, workspace_id):
        try:
            # Step 1-5: Pipeline execution
            context_window = await self._form_context(evidence_id, workspace_id)
            interpretation = await self._interpret(context_window)
            formation = await self.formation_service.form(self.session, interpretation, evidence_id, workspace_id)
            topic_ids = await self.topic_service.extract(self.session, formation.semantic_summary, workspace_id)
            await self.evolution_engine.evolve(self.session, formation.candidate_id, workspace_id, topic_ids)
            
            # Success: Commit
            await self._commit(self.session)
            return PipelineResult(success=True, ...)
            
        except FormationError as e:
            # Formation failed: Rollback
            await self._rollback(self.session, f"Formation failed: {e}")
            return PipelineResult(success=False, error=str(e))
            
        except TopicError as e:
            # Topic failed: Rollback
            await self._rollback(self.session, f"Topic failed: {e}")
            return PipelineResult(success=False, error=str(e))
            
        except EvolutionError as e:
            # Evolution failed: Rollback
            await self._rollback(self.session, f"Evolution failed: {e}")
            return PipelineResult(success=False, error=str(e))
            
        except Exception as e:
            # Unknown error: Rollback
            await self._rollback(self.session, f"Unexpected error: {e}")
            return PipelineResult(success=False, error=str(e))
```

### 9.2 部分成功处理

**问题**: 如果 Formation 成功但 Evolution 失败，是否回滚 Formation？

**答案**: **是的，必须回滚**。

理由：
1. 保证数据一致性
2. 用户看不到部分结果
3. 可以重试整个 Pipeline

---

## 10. Scheduler Integration Strategy

### 10.1 现有 Scheduler

```python
# backend/app.py
_DEFAULT_EVOLUTION_TASK = {
    "type": "evolution",
    "interval_seconds": 600,
    "payload": {
        "workspace_id": "...",
        "limit": 200
    }
}
```

**作用**: 定期触发 Phase 20 批量 Evolution

### 10.2 Phase 21 Pipeline 触发方式

**不应使用 Cron**，原因：
1. Phase 21 是实时响应（Evidence 入库后）
2. Cron 会有延迟和不一致
3. 已有 REST API 可触发

**建议**: 
- Phase 20 Evolution: 保留现有 Cron
- Phase 21 Pipeline: API 触发（HTTP request 或内部调用）

---

## 11. API Integration Strategy

### 11.1 新增 API Endpoint

```python
# backend/app.py
@app.post("/pipeline/trigger")
async def trigger_pipeline(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """Trigger Phase 21 Pipeline for an Evidence."""
    from backend.service.evidence_pipeline_service import EvidencePipelineService
    
    evidence_id = UUID(body["evidence_id"])
    workspace_id = UUID(body["workspace_id"])
    
    service = EvidencePipelineService(session)
    result = await service.process_evidence(
        evidence_id=evidence_id,
        workspace_id=workspace_id,
    )
    
    return result.get_summary()
```

### 11.2 现有 API 扩展

```python
# 在 Evidence 创建 API 中集成
@app.post("/evidences")
async def create_evidence(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
):
    # 创建 Evidence
    evidence = await evidence_repo.create(...)
    
    # 触发 Pipeline（可选，基于配置）
    if os.environ.get("PHASE21_PIPELINE_ENABLED", "false") == "true":
        pipeline = EvidencePipelineService(session)
        await pipeline.process_evidence(
            evidence_id=evidence.id,
            workspace_id=evidence.workspace_id,
        )
    
    return {"evidence_id": evidence.id}
```

---

## 12. Phase 20 Compatibility

### 12.1 影响检查

| Phase 20 组件 | 是否受影响 | 说明 |
|--------------|-----------|------|
| Proposal.candidate_id | ✅ 无影响 | Phase 21 不修改 |
| Candidate lifecycle | ✅ 无影响 | Phase 21 创建新 Candidate |
| AUTO_APPROVE | ✅ 无影响 | Phase 21 不使用 |
| ReflectionEngine | ✅ 无影响 | Phase 21 独立 |
| EvidenceEvolutionEngine | ✅ 无影响 | Phase 20 批量用 |

### 12.2 共存策略

**Phase 20 Evolution** (批量):
- 触发: Cron scheduler
- 输入: 历史 Candidates
- 输出: Proposals → MemoryNodes

**Phase 21 Pipeline** (实时):
- 触发: Evidence 入库后
- 输入: 新 Evidence
- 输出: Reconstruction → Candidate → MemoryNode

**关键**: 两者使用不同的 Candidate 来源：
- Phase 20: 已有 Candidates（来自 EvidenceEvolutionEngine）
- Phase 21: 新形成的 Candidates（来自 FormationService）

---

## 13. 架构修正清单

### 13.1 Phase 21.8 Implementation 需要修正

| 编号 | 修正项 | 优先级 | 工作量 |
|------|--------|--------|--------|
| C1 | 新增 EvidencePipelineService | P0 | 中 |
| C2 | FormationService 移除 session 依赖 | P0 | 小 |
| C3 | FormationService 改为纯业务逻辑 | P0 | 小 |
| C4 | EvolutionEngine 改为继承 EngineBase | P1 | 大 |
| C5 | 添加 API endpoint | P1 | 中 |

### 13.2 Phase 21.8 范围外（需单独处理）

| 编号 | 修正项 | 优先级 | 说明 |
|------|--------|--------|------|
| R1 | ReflectionService 违规调用 Engine | P0 | 需重构 ReflectionService |
| R2 | EvidenceEvolutionEngine 架构 | P1 | 需评估是否引入 session |

---

## 14. 是否可以进入 Implementation

### 14.1 结论

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   DESIGN REVIEW: READY FOR IMPLEMENTATION                  ║
║                                                              ║
║   前提条件:                                                   ║
║   1. 新增 EvidencePipelineService                            ║
║   2. FormationService 改为纯业务逻辑（不继承 BaseService）      ║
║   3. EvolutionEngine 暂时保持混合设计，由 Pipeline Service 管理事务 |
║   4. 明确 Phase 20/21 Evolution 分工                          ║
║   5. 添加 Pipeline API endpoint                               ║
║                                                              ║
║   禁止事项:                                                   ║
║   - 不修改 Phase 20 代码                                      ║
║   - 不修改冻结的 Stage 2.1-2.4 设计                            ║
║   - 不新增 Migration                                          ║
║   - 不修改已有测试                                              ║
║   - 不重构 ReflectionService（范围外）                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

### 14.2 Implementation 优先级

| 优先级 | 任务 | 预计工作量 |
|--------|------|-----------|
| P0 | 新增 EvidencePipelineService | 中 |
| P0 | FormationService 重构（移除 session） | 小 |
| P1 | API endpoint 集成 | 中 |
| P1 | Transaction 测试 | 中 |
| P2 | 错误处理和日志 | 小 |

---

## 15. 附录：关键架构对比

### 15.1 Service 层正确示例（MemoryService）

```python
class MemoryService(BaseService):
    def __init__(self, memory_node_repo, evidence_repo, ...):
        super().__init__("MemoryService")
        self._memory_node_repo = memory_node_repo
        # ...
    
    async def capture_memory(self, ...):
        memory_id = await self._memory_node_repo.create(memory_node)
        await self._commit(self._memory_node_repo.session)  # ✅ 事务管理
        return CaptureResult(...)
```

### 15.2 Engine 层正确示例（EvidenceEvolutionEngine）

```python
class EvidenceEvolutionEngine(EngineBase):
    def __init__(self):
        super().__init__("EvidenceEvolutionEngine")
        # 无 session，无数据库访问
    
    async def evolve(self, *, evidence, provider):
        # 纯领域逻辑，返回 DomainResult
        return DomainResult.ok(EvolutionResult(...))
```

### 15.3 Phase 21 正确设计

```python
# FormationService — 纯业务逻辑
class FormationService:
    def __init__(self):
        pass  # 无依赖
    
    async def form(self, session, interpretation, ...):
        # 使用传入的 session
        # 不自己 commit/rollback
        pass

# EvolutionEngine — 真正的 Engine
class EvolutionEngine(EngineBase):
    def __init__(self):
        super().__init__("EvolutionEngine")
        # 无 session
    
    async def detect_relationships(self, *, candidate, historical_nodes):
        # 纯领域逻辑
        pass

# EvidencePipelineService — Orchestration
class EvidencePipelineService(BaseService):
    def __init__(self, session):
        super().__init__("EvidencePipelineService")
        self.session = session
        self.formation = FormationService()
        self.evolution = EvolutionEngine()
    
    async def process_evidence(self, ..., evidence_id, workspace_id):
        try:
            # 调用各组件
            formation = await self.formation.form(self.session, ...)
            await self.evolution.detect_and_evolve(self.session, ...)
            
            # 提交事务
            await self._commit(self.session)
            return PipelineResult(success=True)
        except Exception as e:
            await self._rollback(self.session, str(e))
            return PipelineResult(success=False, error=str(e))
```

---

**STOP** — Phase 21.8 Stage B Design Review 完成，等待下一步指示。
