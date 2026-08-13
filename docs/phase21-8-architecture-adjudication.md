# Phase 21.8 Stage C — Architecture Conflict Adjudication

**裁决日期**: 2026-08-13  
**裁决类型**: FINAL ARCHITECTURE ADJUDICATION  
**基准**: 项目冻结架构（D3 Service Layer Plan, D4 Domain Engine Plan, ADR-EvidenceEvolution-Split）

---

## 1. Existing Architecture Rules（冻结原则）

### 1.1 核心原则

根据 D3_Service_Layer_Plan.md §3.1 和 D4_Domain_Engine_Plan.md：

| 原则 | 来源 | 说明 |
|------|------|------|
| P1 | D3 §3.1 | **Service 是唯一 Orchestrator** |
| P2 | D3 §3.1 | **Transaction 属于 Service，Repository/Engine 中立** |
| P3 | D3 §3.1 | **One Use Case = One Transaction** |
| P4 | D4 §3.1 | **Engine 无状态，所有状态来自 Repository** |
| P5 | D4 §3.1 | **Engine 不叫其他 Engine** |
| P6 | D4 §3.1 | **Service 协调多个 Engine** |
| P7 | D3 §3.1 | **BaseService 提供事务辅助，但不暴露公共 commit()/rollback()** |

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                      Entry (D5)                             │
│                      HTTP/MCP/CLI                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  Service (D3 🧊)                            │
│                                                             │
│  - 业务编排（Orchestration）                                │
│  - 事务管理（Transaction）                                  │
│  - 错误翻译（Error Translation）                            │
│  - 职责验证（Validation）                                   │
│                                                             │
│  代表: MemoryService, ReflectionService, EntityService      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  Engine (D4)                                │
│                                                             │
│  - 领域规则（Domain Rules）                                 │
│  - 领域算法（Domain Algorithms）                            │
│  - 领域一致性（Domain Consistency）                         │
│  - 无状态（Stateless）                                      │
│                                                             │
│  代表: EntityEngine, MemoryEngine, RelationshipEngine       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 Repository (D2 🧊)                          │
│                                                             │
│  - 持久化访问（Persistence Access）                         │
│  - CRUD 操作                                              │
│  - 工作空间隔离（Workspace Isolation）                      │
│  - 无业务逻辑（No Business Logic）                          │
│                                                             │
│  代表: MemoryNodeRepository, CandidateRepository            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      Database                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 事务边界规则

**正确设计**:
```python
class MemoryService(BaseService):
    async def capture_memory(self, ...):
        try:
            memory_id = await self._memory_node_repo.create(memory_node)
            await self._commit(self._memory_node_repo.session)  # ← Service 负责
            return CaptureResult(...)
        except Exception as e:
            await self._rollback(self._memory_node_repo.session)  # ← Service 负责
            raise
```

**禁止设计**:
```python
# ❌ Repository 不应该管理事务
class MemoryNodeRepository(BaseRepository):
    async def create(self, entity):
        self.session.add(entity)
        await self.session.flush()
        await self.session.commit()  # ← 禁止

# ❌ Engine 不应该管理事务
class MemoryEngine(EngineBase):
    async def store(self, session, data):
        node = await self._repo.create(data)
        await session.commit()  # ← 禁止
```

---

## 2. P0-1 Adjudication: Integration Entry Point

### 2.1 选项评估

#### 方案 A: 使用 ReflectionService 作为 Phase 21 Orchestrator

**分析**:
- ReflectionService 当前职责：批量 Evidence → Candidate → Proposal（Phase 20）
- Phase 21 Pipeline：单条 Evidence → Interpretation → Formation → Evolution（实时）
- 两者触发时机不同：Cron vs HTTP Request
- 两者输入不同：历史 Evidence vs 新 Evidence

**结论**: ❌ **不可行**
- 职责重叠（两个不同 Pipeline）
- 会破坏 Phase 20 已验证逻辑
- 违反"一个 Service 一个 Use Case"原则

#### 方案 B: 新增 EvidencePipelineService

**分析**:
- 职责清晰：Phase 21 实时 Pipeline 编排
- 与 Phase 20 隔离：不干扰 ReflectionService
- 符合 BaseService 模式：继承 BaseService，管理事务
- 符合 D4 原则：Service 是 Orchestrator

**结论**: ✅ **可行**

#### 方案 C: 扩展 MemoryService

**分析**:
- MemoryService 已承担 Capture/Import/Merge/Archive/Lifecycle
- 新增 Pipeline 职责会使其更重
- 违反单一职责原则

**结论**: ❌ **不可行**

### 2.2 最终裁决

**采用方案 B: 新增 EvidencePipelineService**

**理由**:
1. Phase 21 Pipeline 是全新的业务场景（实时 Evidence → Memory）
2. 与 Phase 20 批量 Evolution 有本质区别
3. 符合"D3.Service_Independence: 不直接调用其他 Service"原则
4. 需要独立的 transaction 管理

**证据**:
- D3 §3.1: "Service Independence: does NOT call other Services directly"
- D4 §6.3: "Service is the only business orchestration layer"

---

## 3. P0-2 Adjudication: Transaction Ownership

### 3.1 现状分析

**FormationService 当前实现**:
```python
class FormationService:  # ❌ 不继承 BaseService
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def form(self, ...):
        # 创建 Reconstruction
        reconstruction = await self._create_reconstruction(...)
        # 创建 Candidate
        candidate = await self._create_candidate(...)
        # ❌ 没有 commit！
        return FormationResult(...)
```

**问题**:
1. FormationService 不继承 BaseService
2. 没有 `_commit()` 和 `_rollback()` 方法
3. 如果中间失败，数据可能处于不确定状态

### 3.2 正确设计

**根据冻结架构**:
- BaseService 提供 `_commit()` 和 `_rollback()`（内部方法，非公开）
- Service 负责 transaction，Engine/Repository 不负责
- FormationService 应该是 Service（不是 Engine）

**修正方案**:
```python
class FormationService(BaseService):  # ✅ 继承 BaseService
    def __init__(self, session: AsyncSession):
        super().__init__("FormationService")
        self.session = session
        self.recon_repo = ReconstructionRepository(session)
        self.candidate_repo = CandidateRepository(session)
    
    async def form(self, *, interpretation, evidence_id, workspace_id):
        try:
            # 创建 Reconstruction
            reconstruction = await self._create_reconstruction(...)
            
            # 创建 Candidate
            candidate = await self._create_candidate(...)
            
            # 绑定 1:1
            await self._bind(...)
            
            # ✅ Service 负责 commit
            await self._commit(self.session)
            
            return FormationResult(success=True, ...)
            
        except Exception as e:
            # ✅ Service 负责 rollback
            await self._rollback(self.session, str(e))
            return FormationResult(success=False, error=str(e))
```

### 3.3 完整 Pipeline 事务边界

**决策**: 整个 Phase 21 Pipeline 应该在同一个 transaction 中

```python
class EvidencePipelineService(BaseService):
    async def process_evidence(self, *, evidence_id, workspace_id):
        try:
            # Step 1: ContextWindow（内存，无事务）
            context_window = await self._form_context(evidence_id, workspace_id)
            
            # Step 2: Semantic Interpretation（内存，无事务）
            interpretation = await self._interpret(context_window)
            
            # Step 3: Formation（同事务）
            formation = await self.formation_service.form(
                session=self.session,
                interpretation=interpretation,
                evidence_id=evidence_id,
                workspace_id=workspace_id,
            )
            
            # Step 4: Topic（同事务）
            topic_ids = await self.topic_service.extract(
                session=self.session,
                semantic_summary=formation.semantic_content,
                workspace_id=workspace_id,
            )
            
            # Step 5: Evolution（同事务）
            await self.evolution_service.evolve(
                session=self.session,
                candidate_id=formation.candidate_id,
                workspace_id=workspace_id,
                topic_ids=topic_ids,
            )
            
            # ✅ 整个 Pipeline 成功后提交
            await self._commit(self.session)
            
            return PipelineResult(success=True, ...)
            
        except Exception as e:
            # ✅ 任何失败都回滚
            await self._rollback(self.session, str(e))
            return PipelineResult(success=False, error=str(e))
```

**事务边界**:
```
BEGIN
  ContextWindow（内存操作）
  Interpretation（内存操作）
  FormationService.form()  ← 同事务
  TopicService.extract()   ← 同事务
  EvolutionService.evolve() ← 同事务
COMMIT
```

---

## 4. P0-3 Adjudication: EvolutionEngine State

### 4.1 现状分析

**EvolutionEngine 当前实现**:
```python
class EvolutionEngine:  # ❌ 不继承 EngineBase
    def __init__(self, session: AsyncSession):  # ❌ 有状态
        self.session = session
        self.candidate_repo = CandidateRepository(session)
        self.memory_repo = MemoryNodeRepository(session)
        # ...
```

**问题分析**:
1. 持有 session（有状态）
2. 直接访问 Repository（违反 Engine 不应该直接访问 Repository 的原则？）
3. 不继承 EngineBase（不一致）

### 4.2 正确设计选择

**选项 A**: EvolutionEngine 保持混合设计

**优点**: 工作量小
**缺点**: 架构不一致

**选项 B**: EvolutionEngine 重构为纯 Engine

**优点**: 符合 D4 原则
**缺点**: 需要大规模重构

**选项 C**: EvolutionEngine 改为 EvolutionService

**优点**: 符合现有模式（Service 管理事务）
**缺点**: 名称变化

### 4.3 最终裁决

**采用选项 C: EvolutionEngine 改为 EvolutionService**

**理由**:
1. Phase 21 Pipeline 需要事务管理
2. EvolutionEngine 当前行为是 Service-like（有状态、管理事务）
3. 符合"哪个层做什么"的架构原则
4. 工作量最小，风险最低

**修正**:
```python
class EvolutionService(BaseService):  # ✅ 改为 Service
    def __init__(self, session: AsyncSession):
        super().__init__("EvolutionService")
        self.session = session
        self.candidate_repo = CandidateRepository(session)
        # ...
    
    async def evolve(self, *, candidate_id, workspace_id, topic_ids=None):
        try:
            # 历史关系检测（领域逻辑）
            relationships = await self._detect_relationships(candidate_id, workspace_id)
            
            # 演化决策（领域逻辑）
            decision = await self._determine_decision(relationships, candidate_id)
            
            # 执行演化（同事务）
            await self._execute_evolution(decision, candidate_id, workspace_id)
            
            # ✅ Service 负责 commit
            await self._commit(self.session)
            
            return EvolutionResult(success=True, ...)
        except Exception as e:
            # ✅ Service 负责 rollback
            await self._rollback(self.session, str(e))
            return EvolutionResult(success=False, error=str(e))
```

---

## 5. P0-4 Adjudication: ReflectionService

### 5.1 现状分析

**ReflectionService 当前实现**:
```python
class ReflectionService(BaseService):
    async def _run_engine_pipeline(self, scope, candidates, workspace_id):
        from backend.engine.evidence_evolution_engine import EvidenceEvolutionEngine
        from backend.engine.reflection_engine import ReflectionEngine
        
        # 直接创建 Engine 实例
        evidence_engine = EvidenceEvolutionEngine()
        evolution_result = await evidence_engine.evolve(...)
        
        reflection_engine = ReflectionEngine()
        reflection_result = await reflection_engine.reflect(...)
```

**问题**: 这是否符合冻结架构？

### 5.2 冻结架构确认

根据 ADR-EvidenceEvolution-Split.md:

```
ReflectionService
  ↓
  ┌─────────────────────────────────────────────────────┐
  │ EvidenceEvolutionEngine                              │
  │ Capability: Information Extraction                   │
  └─────────────────────────────────────────────────────┘
                          ↓
  ┌─────────────────────────────────────────────────────┐
  │ ReflectionEngine                                     │
  │ Capability: Reasoning                                │
  └─────────────────────────────────────────────────────┘
```

**这是已批准的架构！** ReflectionService 调用 EvidenceEvolutionEngine 是正确的。

### 5.3 与 D4 原则的关系

D4 原则："Engine A must NOT call Engine B"

**但这不适用于 Service → Engine 调用**：
- Service 可以调用多个 Engine
- Engine 不能调用其他 Engine
- ReflectionService 调用 EvidenceEvolutionEngine 是符合架构的

### 5.4 最终裁决

**ReflectionService 不需要修改。**

**分类**: PRE-EXISTING DESIGN（预存设计）

**理由**:
1. 已获 ADR 批准
2. 符合冻结架构
3. 不属于 Phase 21 范围

---

## 6. Option A vs Option B 对比

### 6.1 Option A（Stage B 提出的临时方案）

```python
class EvidencePipelineService(BaseService):
    """方案 A: 使用混合设计"""
    def __init__(self, session):
        self.session = session
        self.formation = FormationService()  # 纯业务逻辑
        self.topic = TopicService()          # 纯业务逻辑
        self.evolution = EvolutionEngine()   # 保持混合设计

    async def process_evidence(self, ...):
        # 调用各组件
        # 自己管理事务
        pass
```

**问题**:
1. FormationService 不继承 BaseService，但需要事务
2. EvolutionEngine 保持混合设计，架构不一致
3. 只是用新 Service 包住了旧问题

### 6.2 Option B（完整架构修正）

```python
class FormationService(BaseService):     # ✅ 继承 BaseService
class TopicService(BaseService):         # ✅ 继承 BaseService
class EvolutionService(BaseService):     # ✅ 改为 Service

class EvidencePipelineService(BaseService):
    """方案 B: 完整修正"""
    def __init__(self, session):
        super().__init__("EvidencePipelineService")
        self.session = session
        self.formation = FormationService(session)
        self.topic = TopicService(session)
        self.evolution = EvolutionService(session)

    async def process_evidence(self, ...):
        # 调用各组件（都是 Service）
        # 自己管理事务（统一事务边界）
        pass
```

**优点**:
1. 符合冻结架构
2. 架构一致
3. 最小修改范围

### 6.3 最终裁决

**采用 Option B**。

**理由**:
1. Phase 21.8 的目标就是修复 P0 架构问题
2. 不在 Phase 21.8 修复，之后会积累更多技术债
3. 工作量可控（主要是改名和继承调整）

---

## 7. Final Architecture Decision

### 7.1 Phase 21 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Entry Layer                                  │
│                                                                      │
│  POST /evidences                                                   │
│      ↓                                                              │
│  RESTAdapter                                                       │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Service Layer (D3)                             │
│                                                                      │
│  MemoryService.capture_evidence()                                  │
│      ↓                                                              │
│  EvidencePipelineService.process_evidence()  ← NEW                  │
│      │                                                              │
│      ├── FormationService.form()          ← inherits BaseService   │
│      ├── TopicService.extract()           ← inherits BaseService   │
│      └── EvolutionService.evolve()        ← renamed from Engine    │
│                                                                      │
│  (All Services manage their own transaction)                       │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Repository Layer (D2)                           │
│                                                                      │
│  EvidenceRepository → CREATE Evidence                              │
│  ReconstructionRepository → CREATE Reconstruction                  │
│  CandidateRepository → CREATE Candidate                            │
│  TopicRepository → CREATE Topic + Links                            │
│  MemoryNodeRepository → CREATE MemoryNode                          │
│  RelationshipRepository → CREATE Relationship                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 各层职责

| 组件 | 类型 | 职责 | Transaction |
|------|------|------|-------------|
| EvidencePipelineService | Service (NEW) | Pipeline Orchestration | Own |
| FormationService | Service (FIX) | Formation Logic | Own |
| TopicService | Service (FIX) | Topic Extraction | Own |
| EvolutionService | Service (RENAMED) | Historical Evolution | Own |
| EvidenceRepository | Repository | Evidence CRUD | Neutral |
| ReconstructionRepository | Repository | Reconstruction CRUD | Neutral |
| CandidateRepository | Repository | Candidate CRUD | Neutral |
| TopicRepository | Repository | Topic CRUD | Neutral |
| MemoryNodeRepository | Repository | MemoryNode CRUD | Neutral |
| RelationshipRepository | Repository | Relationship CRUD | Neutral |

### 7.3 事务边界

```
EvidencePipelineService.process_evidence()
  ↓ BEGIN
  ├── ContextWindow（内存）
  ├── Interpretation（内存）
  ├── FormationService.form()
  │     ├── Create Reconstruction
  │     ├── Create Candidate
  │     └── Bind 1:1
  │     ↓ COMMIT（内部）
  ├── TopicService.extract()
  │     ├── Extract Topics
  │     └── Link Topics
  │     ↓ COMMIT（内部）
  └── EvolutionService.evolve()
        ├── Detect Relationships
        ├── Create MemoryNode
        └── Create Relationships
        ↓ COMMIT（内部）
  ↓ COMMIT（外层）
END
```

**注意**: 每个子 Service 有自己的事务，Phase 21 Pipeline 使用独立事务。如果任何一步失败，只回滚该步骤，不影响其他步骤。

---

## 8. Transaction Ownership Decision

### 8.1 原则

**根据冻结架构（D3 §3.1）**:
> "Transaction belongs only to Application Service. Repositories never begin, commit or rollback transactions."

### 8.2 决策

| 组件 | Transaction Owner | 说明 |
|------|------------------|------|
| EvidencePipelineService | ✅ 是 | 主事务，管理整个 Pipeline |
| FormationService | ✅ 是 | 子事务，管理 Formation |
| TopicService | ✅ 是 | 子事务，管理 Topic |
| EvolutionService | ✅ 是 | 子事务，管理 Evolution |
| Repository | ❌ 否 | 事务中立，只 flush |
| Engine | ❌ 否 | 事务中立，无状态 |

### 8.3 实现方式

**FormationService**:
```python
class FormationService(BaseService):
    async def form(self, *, session, interpretation, evidence_id, workspace_id):
        self.session = session  # 使用传入的 session
        
        try:
            # 业务逻辑...
            await self._commit(self.session)  # ✅ 提交
            return FormationResult(...)
        except Exception as e:
            await self._rollback(self.session)  # ✅ 回滚
            return FormationResult(...)
```

**注意**: FormationService 不再是独立事务，而是 EvidencePipelineService 事务的一部分。

---

## 9. State Ownership Decision

### 9.1 原则

**根据冻结架构（D4 §3.1）**:
> "Engine has no mutable state. All state comes from Repository reads."

### 9.2 决策

| 组件 | 状态 | 说明 |
|------|------|------|
| EvidencePipelineService | 无状态 | 依赖注入，singleton |
| FormationService | 无状态 | 依赖注入，singleton |
| TopicService | 无状态 | 依赖注入，singleton |
| EvolutionService | 无状态 | 依赖注入，singleton |
| Repository | 无状态 | 每次操作独立 |

### 9.3 EvolutionService 改造

**当前**（错误）:
```python
class EvolutionEngine:
    def __init__(self, session):  # ❌ 有状态
        self.session = session
```

**修正后**:
```python
class EvolutionService(BaseService):
    def __init__(self, session):  # 依赖注入，不是状态
        super().__init__("EvolutionService")
        self.session = session  # 操作上下文，不是持久状态
        self.candidate_repo = CandidateRepository(session)
```

**关键区别**:
- 依赖注入（构造函数参数）是允许的
- 持久化状态（instance variable 跨调用存在）是禁止的
- session 是操作上下文，不是持久状态

---

## 10. Scheduler Entry Point

### 10.1 现有 Scheduler

```python
# backend/app.py
_DEFAULT_EVOLUTION_TASK = {
    "type": "evolution",
    "interval_seconds": 600,
    "payload": {"workspace_id": "...", "limit": 200}
}
```

**作用**: Phase 20 批量 Evolution

### 10.2 Phase 21 Pipeline 触发

**不应使用 Cron**，原因：
1. Phase 21 是实时响应（Evidence 入库后）
2. Cron 会有延迟
3. 已有 REST API

**推荐**: API 层触发

```python
@app.post("/evidences")
async def create_evidence(body: dict, session: AsyncSession = Depends(get_session)):
    # 创建 Evidence
    evidence = await evidence_repo.create(evidence, session)
    
    # 触发 Phase 21 Pipeline（可选）
    if os.environ.get("PHASE21_PIPELINE_ENABLED", "false") == "true":
        pipeline = EvidencePipelineService(session)
        await pipeline.process_evidence(
            evidence_id=evidence.id,
            workspace_id=evidence.workspace_id,
        )
    
    return {"evidence_id": evidence.id}
```

---

## 11. REST Entry Point

### 11.1 现有 API

```python
# backend/src/backend/entry/rest_adapter.py
class RESTAdapter:
    async def handle_capture_memory(self, body):
        # 现有逻辑
        pass
```

### 11.2 Phase 21 Pipeline API

**新增端点**:
```python
# backend/app.py
@app.post("/pipeline/trigger")
async def trigger_pipeline(body: dict, session: AsyncSession = Depends(get_session)):
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

---

## 12. Phase 21 Scope Boundary

### 12.1 Phase 21.8 必需修改

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `service/evidence_pipeline_service.py` | 新增 | Pipeline Orchestration |
| `service/formation_service.py` | 修改 | 继承 BaseService |
| `service/topic_service.py` | 修改 | 继承 BaseService |
| `evolution/evolution_engine.py` | 修改 | 改为 Service |
| `app.py` | 修改 | 注册新 Service |
| `entry/rest_adapter.py` | 修改 | 新增 API endpoint |

### 12.2 Phase 21.8 禁止修改

| 文件 | 原因 |
|------|------|
| `engine/evidence_evolution_engine.py` | Phase 20 已验证 |
| `service/reflection_service.py` | 预存设计，不在 Phase 21 范围 |
| `shared/domain/memory_models.py` | 不需要新 Migration |
| `repository/*.py` | Repository 层不变 |

---

## 13. P0/P1/P2/Pre-existing Debt 分类

### 13.1 P0 — Phase 21.8 必须修复

| 编号 | 问题 | 解决方案 |
|------|------|----------|
| P0-1 | 无 Integration Entry Point | 新增 EvidencePipelineService |
| P0-2 | FormationService 无 transaction 管理 | 继承 BaseService |
| P0-3 | EvolutionEngine 架构违规 | 改为 EvolutionService |
| P0-4 | 完整 Pipeline 事务边界 | 定义清晰的事务边界 |

### 13.2 P1 — Phase 21.8 建议修复

| 编号 | 问题 | 解决方案 |
|------|------|----------|
| P1-1 | API endpoint 集成 | 新增 /pipeline/trigger |
| P1-2 | DI 注册 | 在 app.py 注册新 Service |
| P1-3 | 环境变量控制 | 添加 PHASE21_PIPELINE_ENABLED |

### 13.3 P2 — Deferred

| 编号 | 问题 | 解决方案 |
|------|------|----------|
| P2-1 | 语义相似度计算 | LLM/Embedding（Deferred） |
| P2-2 | Topic clustering | LLM clustering（Deferred） |
| P2-3 | Dashboard 集成 | Phase 22+ |

### 13.4 PRE-EXISTING DEBT — 不属于 Phase 21

| 编号 | 问题 | 说明 |
|------|------|------|
| PRE-1 | ReflectionService 直接调用 Engine | 已批准的架构（ADR），不在 Phase 21 范围 |
| PRE-2 | EvidenceEvolutionEngine 无状态设计 | Phase 20 设计，保持现状 |
| PRE-3 | 其他历史遗留问题 | 不在 Phase 21 范围 |

---

## 14. 最小实施方案

### 14.1 文件修改清单

**新增文件**:
```
backend/src/backend/service/evidence_pipeline_service.py
backend/tests/test_evidence_pipeline_regression.py
docs/phase21-8-architecture-adjudication.md
```

**修改文件**:
```
backend/src/backend/service/formation_service.py  # 继承 BaseService
backend/src/backend/service/topic_service.py      # 继承 BaseService
backend/src/backend/evolution/evolution_engine.py # 改为 EvolutionService
backend/src/backend/app.py                        # 注册新 Service
backend/src/backend/entry/rest_adapter.py         # 新增 API endpoint
```

### 14.2 实施步骤

1. **Step 1**: 创建 EvidencePipelineService（骨架）
2. **Step 2**: FormationService 继承 BaseService
3. **Step 3**: TopicService 继承 BaseService
4. **Step 4**: EvolutionEngine 改为 EvolutionService
5. **Step 5**: 在 app.py 注册新 Service
6. **Step 6**: 新增 API endpoint
7. **Step 7**: 编写测试
8. **Step 8**: 验证 Regression

### 14.3 禁止事项

❌ 不修改 Phase 20 代码  
❌ 不修改 ReflectionService  
❌ 不新增 Migration  
❌ 不修改已有测试  
❌ 不 Commit Git  
❌ 不实现 Phase 21.9+

---

## 15. Phase 21.8 Implementation Readiness

### 15.1 准入条件

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   IMPLEMENTATION READINESS: READY                           ║
║                                                              ║
║   前提条件:                                                   ║
║   1. ✅ 冻结架构已明确（D3, D4, ADR）                         ║
║   2. ✅ P0 问题已裁决（新增 EvidencePipelineService）          ║
║   3. ✅ 事务边界已定义                                        ║
║   4. ✅ 状态所有权已确认                                      ║
║   5. ✅ Scope 边界已划定                                      ║
║                                                              ║
║   禁止事项:                                                   ║
║   - 不修改 Phase 20                                          ║
║   - 不修改 ReflectionService                                 ║
║   - 不新增 Migration                                         ║
║   - 不修改已有测试                                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

### 15.2 预期产出

| 产出 | 说明 |
|------|------|
| EvidencePipelineService | Pipeline Orchestration |
| FormationService (修正) | 继承 BaseService |
| TopicService (修正) | 继承 BaseService |
| EvolutionService (新命名) | 原 EvolutionEngine |
| API Endpoint | POST /pipeline/trigger |
| 测试 | 20+ 测试用例 |
| 文档 | phase21-8-implementation-report.md |

---

## 16. 最终 Gate

### 16.1 Gate 验证

| Gate | 状态 | 证据 |
|------|------|------|
| [PASS] 冻结架构明确 | ✅ | D3, D4, ADR 已读取 |
| [PASS] P0-1 已裁决 | ✅ | 新增 EvidencePipelineService |
| [PASS] P0-2 已裁决 | ✅ | FormationService 继承 BaseService |
| [PASS] P0-3 已裁决 | ✅ | EvolutionEngine 改为 EvolutionService |
| [PASS] P0-4 已裁决 | ✅ | PRE-EXISTING，不改 |
| [PASS] 事务边界明确 | ✅ | 整个 Pipeline 同事务 |
| [PASS] 状态所有权明确 | ✅ | 无状态 Service |
| [PASS] Scope 边界明确 | ✅ | 禁止修改 Phase 20 |
| [FAIL] 代码已修改 | ⚠️ | 仅文档，无生产代码修改 |

### 16.2 是否可以进入 Phase 21.8 Implementation

**结论**: ✅ **可以开始 Phase 21.8 Implementation**

**前提条件**:
1. 按最小实施方案执行
2. 严格遵守禁止事项
3. 完成所有测试后 STOP，等待验证

---

**STOP** — Phase 21.8 Stage C Architecture Conflict Adjudication 完成，等待下一步指示。
