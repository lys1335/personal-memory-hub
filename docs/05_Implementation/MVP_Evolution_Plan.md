# Memory Evolution MVP 架构一致性审查与修订方案

> **审查日期**: 2026-07-26
> **审查依据**: Certified Architecture Baseline (D1–D6, GitHub HEAD)
> **审查性质**: 纯架构一致性审查，不涉及代码实现
> **状态**: CHANGE REQUIRED（4 项变更）

---

## 一、项目定位与边界

根据文档 `07_Boundary_Review` (P1-P9) 和 `ENG-002/003`：
- **Memory Hub 是 Witness，不是 Actor**：只观察、记录、组织、演化记忆，不做决策或推荐
- **Agent 始终在 Memory Hub 外部**：Ollama (qwen3:4b) 作为 LLM provider，不在 Memory Hub 内部嵌入 Agent 逻辑
- **Reflection 是演化，不是突变**：产生的是领域决策/建议，由 Engine 完成实际变更

✅ **PASS** — 与 D4.2d §2.7 "Explicitly NOT Owned" 一致。

---

## 二、当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| 数据摄入 (`MemoryService.capture`) | ✅ 已完成 | REST API + 批量导入 |
| 向量检索 (`QueryService.search`) | ✅ 已完成 | 语义搜索 + 重排 |
| 定时任务调度 (`TaskRuntime`) | ✅ 已完成 | Cron API + Dashboard UI |
| 日志查看器 | ✅ 已完成 | 后端日志写入 + Dashboard 展示 |
| MemoryEngine (Archive/Evidence) | ⚠️ 骨架 | 表结构存在，未实现核心逻辑 |
| EntityEngine | ❌ 未实现 | 实体解析/身份管理 |
| ReflectionEngine | ❌ 未实现 | 核心：事实提取、实体解析、兴趣分析、投影更新 |
| ReflectionService | ❌ 未实现 | Reflection 工作流编排 |
| QueryService (Projection) | ❌ 未实现 | 记忆金字塔抽象层级生成 |

---

## 三、MVP 目标

实现 **Memory Evolution 的最小可验证闭环**：

```
定时任务触发 → ReflectionService 编排 → 
ReflectionEngine (LLM 推理) → EntityEngine/MemoryEngine → 
Sandbox 存储 → Review API → 人工确认 → DB 写入
```

**关键约束**：
1. MVP 阶段 **不污染正式数据库**，先在 Sandbox 环境验证
2. 使用 **本地 Ollama Modelfile** 而非外部 AI（符合用户之前决策）
3. 输出以 **日志** 为主，DB 写入仅在人工确认后执行

---

## 四、实现准则

### 4.1 架构分层遵守五层模型 ✅ PASS

```
Entry Layer (REST/Cron Trigger)
  ↓
Service Layer (ReflectionService - MVP 仅编排)
  ↓
Engine Layer (ReflectionEngine - 核心算法)
  ↓
Repository Layer (SandboxRepo - MVP 专用)
  ↓
Database (Sandbox DB / 内存)
```

**证据**：
- D4 §2.2: "Engine may only call Repository. Engine must NOT call Service. Engine must NOT call other Engines."
- D4 §3.1 Principle #6: "No Cross-Engine Calls — Engine A must NOT call Engine B. Service is the only orchestrator."
- D4.2d §2.7: "LLM invocation — Service manages AI provider communication"

**严格遵守**：
- Engine 无数据库依赖（可独立单元测试）
- Service 编排 Engine + Repository
- 禁止跨层调用

### 4.2 服务独立性原则 (Service Independence) ✅ PASS

- MVP 阶段只新增 `ReflectionService`，**不调用其他 Service**
- 通过 `Shared Domain Engine` 协作（ReflectionService → ReflectionEngine / MemoryEngine / EntityEngine）
- EntityService MVP 范围：仅 `createEntity()` + `resolveEntity()`

**证据**：
- 10_4 §12.1: "ReflectionService → MemoryService: ❌ Forbidden — Service Independence Principle (G-005)"
- 10_4 §12.2: "ReflectionService → ReflectionEngine: ✅ Orchestrate — Domain Engine Principle"
- 10_4 §12.2: "ReflectionService → EntityEngine: ✅ Orchestrate — Shared Domain Engine Principle"

### 4.3 幂等性与 Scope 锁 ✅ PASS

- 同一 Scope 同一时刻仅一个 Reflection 执行
- 失败跳过不 Resume（等待下一周期重新计算已积累 Evidence）
- 最大 Reflection Horizon：可配置，默认 Daily 10 天

**证据**：
- 10_4 §9: "幂等性 + Scope 锁 — 同一 Scope 同一时刻仅一个执行"
- 10_4 §10.1: "Failure 跳过不 Resume — 等待下一周期重新计算已积累 Evidence"
- 10_4 §10.2: "Maximum Reflection Horizon — 可配置，默认 Daily 10 天"

### 4.4 L0 保护原则 ✅ PASS

- ReflectionService **绝不自主创建 L0**
- Recovery Baseline 只能源于用户交互或用户预授权
- 高层 Memory 存储演化解释，而非历史快照

**证据**：
- 10_4 §10.3: "Recovery Baseline 源于用户交互 — 系统绝不自主创建 L0"
- 10_4 §3.3: "Memory Pyramid 抽象基于解释范围（Scope），而非时间"
- 10_4 §3.4: "Reflection 目标：提升解释力 — 不是保存快照"

### 4.5 错误隔离 ✅ PASS

- Reflection 是 Enhancement Capability
- 失败必须局部化，不能使已提交的 Memory 无效
- 重试必须是安全的（幂等）

**证据**：
- 10_4 §10.1: "Reflection Failure Isolation — 失败跳过不 Resume"
- 10_4 §13.4: "Retry 不再生成 Candidate — 使用第一次的 Candidate 继续执行"
- 10_4 §14.7: "Failure Isolation — Reflection 故障保持局部"

### 4.6 增量传播 ✅ PASS

- 先更新本层（L1），再决定是否向上传播（L2→L3）
- 下层失败，上层立即停止传播
- 不重建整个金字塔

**证据**：
- 10_4 §3.6: "Incremental Propagation — 先更新本层，再决定是否向上传播"
- 10_4 §13.3: "Propagation Barrier — 下层失败，上层立即停止传播"

### 4.7 Sandbox First ✅ PASS

- MVP 使用 **内存/Sandbox 存储** 而非直接写生产 DB
- 所有演化结果写入日志，供人工审查
- Dashboard 增加 "Evolution Review" 功能（确认/驳回演化建议）

---

## 五、架构一致性审查结果

### Item 1: Reflection Provider Abstraction ❌ CHANGE REQUIRED

**问题**：MVP 草案中 FactExtractor 直接 "调用 Ollama reflection-engine Modelfile"。

**架构规定**：
- D4.2d §2.7: "**LLM invocation — Service manages AI provider communication**" — ReflectionEngine 明确不拥有 LLM 调用
- D4.2d §1.1: "ReflectionEngine is a stateless domain engine... It does not call databases directly. It operates on Domain Models provided by Repository."
- D4 §3.1 Principle #6: "No Cross-Engine Calls"
- D4 §2.2: "Engine may only call Repository. Engine must NOT call Service."

**结论**：ReflectionEngine **不应直接依赖 Ollama**。LLM 调用属于 Service 层职责。

**修正方案**：

引入 `ReflectionProvider` 抽象接口：
```python
class ReflectionProvider(Protocol):
    async def generate(self, prompt: str, context: dict) -> dict: ...
```

ReflectionService 拥有 Provider 实例：
```
ReflectionService (owns ReflectionProvider)
    ├── ReflectionEngine (stateless algorithm, depends on Provider interface)
    ├── MemoryEngine
    └── EntityEngine
```

MVP 实现 `OllamaReflectionProvider` 作为唯一实现：
- Provider 实现放在 `backend/src/backend/shared/providers/` 或 `infrastructure/`
- ReflectionEngine 通过 Provider interface 获取 LLM 推理结果，不直接调用 Ollama HTTP
- 未来替换为 OpenAI/本地模型只需更换 Provider 实现

**对应架构章节**：
- D4.2d §2.7: "LLM invocation — Service manages AI provider communication"
- D4 §2.2: "Engine may only call Repository"

---

### Item 2: Service vs Engine Orchestration ❌ CHANGE REQUIRED

**问题**：MVP 草案中 Phase E1 描述为：
```
ReflectionEngine
    -> MemoryEngine
    -> EntityEngine
```

以及 Phase E2 编排流程中 `EntityResolver` 调用 `EntityService.resolveEntity()`。

**架构规定**：
- D4 §3.1 Principle #6: "**No Cross-Engine Calls — Engine A must NOT call Engine B. Service is the only orchestrator.**"
- D4 §2.2: "Engine never calls Service. Engine never calls other Engines."
- D4.2d §1.2: "ReflectionEngine operates on Memories and Entities. It validates reflection candidates and ensures knowledge evolution follows domain rules. **It never calls MemoryEngine, EntityEngine, or RelationshipEngine directly. Service coordinates between Engines.**"
- 10_4 §6.1: "**ReflectionService 作为 Business Capability Orchestrator，协调多个共享 Domain Engine**"
- 10_4 §12.1: "ReflectionService → MemoryService: ❌ Forbidden — Service Independence Principle (G-005)"

**结论**：Engine 之间 **不允许互相调用**，Service 也不应直接调用其他 Service。所有编排必须在 ReflectionService 层完成。

**修正方案**：

Phase E1（ReflectionEngine）只包含 **纯算法组件**，不跨 Engine/Service：
```
ReflectionEngine (纯算法，无外部依赖)
├── FactExtractor — 从文本中提取结构化事实（LLM 输出解析）
├── InterestAnalyzer — 基于事实列表计算趋势（规则算法）
└── ProjectionUpdater — 生成 Memory Pyramid 更新建议（规则算法）
```

Phase E2（ReflectionService）负责完整编排：
```
ReflectionService.reflect(scope, limit)
    1. 从 Repository 获取候选 L0 Memories
    2. 调用 ReflectionEngine.FactExtractor.extract() → facts[]
    3. 调用 EntityEngine.resolve_entities(facts) → entity_map  ← 通过 Engine 而非 Service
    4. 调用 ReflectionEngine.InterestAnalyzer.analyze(facts) → trends
    5. 调用 ReflectionEngine.ProjectionUpdater.propose(facts, entity_map, trends) → proposals[]
    6. 将 proposals 写入 SandboxStorage
    7. 发布 DomainEvent: ReflectionCompleted
```

**关键修正**：
- ~~`EntityResolver.resolve()` 调用 `EntityService.resolveEntity()`~~ → 改为 `ReflectionService` 编排 `EntityService.resolveEntity()`（但 Service 间不能同步调用，见下）
- 实际上 Entity 解析应在 **MVP 阶段简化**：FactExtractor 输出中包含实体名称，ReflectionService 在 Sandbox 中暂存实体引用，待人工批准后由 EntityService 正式处理
- 或者：MVP 中 EntityResolver 作为 ReflectionEngine 的内部组件（不跨 Engine 调用），仅返回实体名称字符串，不尝试解析到 EntityID

**对应架构章节**：
- D4 §3.1 Principle #6: "No Cross-Engine Calls"
- D4.2d §1.2: "It never calls MemoryEngine, EntityEngine, or RelationshipEngine directly"
- 10_4 §6.1: "ReflectionService 编排工作流"
- 10_4 §12.1: "ReflectionService → MemoryService: ❌ Forbidden"

---

### Item 3: Reflection Decomposition ⚠️ PARTIALLY CONSISTENT / NEEDS CLARIFICATION

**问题**：MVP 草案将 ReflectionEngine 拆分为 FactExtractor / EntityResolver / InterestAnalyzer / ProjectionUpdater 四个子组件。

**架构规定**：
- 10_4 §7.1: "Pipeline 抽象阶段 — Select Scope → Collect Candidate Memories → Analyze Evidence → Generate Reflection → Validate Reflection → Persist Higher-level Memory → Link Evidence Chain → Propagate Upward → Emit Execution Log"
- 10_4 §7.2: "Semantic Evolution Decision — Create / Strengthen / Refine / Split"
- 10_4 §5: "四大 Capability — Reflect / Consolidate / Summarize / Evaluate"

**分析**：
- 架构文档定义了 **Reflection Pipeline 步骤**，但未强制规定这些步骤必须由独立 Engine 还是独立 Component 实现
- D4 §3.1 Principle #2: "One Capability → One Engine" — 但 FactExtractor / InterestAnalyzer 等是 Reflection Pipeline 的子步骤，不是独立的 Domain Capability
- D4.2d §1.1: "ReflectionEngine owns Reflection semantic validation, candidate evaluation, knowledge evolution validation, reflection consistency, knowledge consolidation rules, and reflection domain invariants" — 这些职责都属于 ReflectionEngine

**结论**：
- **可以拆分**为 ReflectionEngine 内部的独立 Component，但不应拆分为独立的 Engine
- FactExtractor 如果涉及 LLM 推理，其 LLM 调用必须通过 Provider abstraction（见 Item 1）
- EntityResolver 在 MVP 阶段应简化为内部组件（不跨 Engine 调用 EntityService）
- InterestAnalyzer 和 ProjectionUpdater 是纯规则算法，可作为 ReflectionEngine 内部组件

**修正方案**：

```
ReflectionEngine (单一 Engine，内部包含多个 Component)
├── FactExtractorComponent     — LLM 辅助的事实提取（通过 Provider）
├── InterestAnalyzerComponent   — 规则驱动的兴趣趋势分析
├── ProjectionUpdaterComponent  — 规则驱动的 Memory Pyramid 更新建议
└── ReflectionValidator         — 领域不变量验证（证据链完整性、语义唯一性等）
```

ReflectionService 调用 ReflectionEngine 的统一入口：
```python
result = reflection_engine.reflection_pipeline(scope, candidates)
```

**对应架构章节**：
- D4 §3.1 Principle #2: "One Capability → One Engine"
- D4.2d §1.1: "ReflectionEngine owns [all reflection-related responsibilities]"
- 10_4 §7.1: "Pipeline 抽象阶段"

---

### Item 4: Proposal Typing ⚠️ PARTIALLY CONSISTENT

**问题**：MVP 草案提到 proposals 类型为 `Create/Strengthen/Refine/Split`。

**架构规定**：
- 10_4 §7.2: "**Semantic Evolution Decision — Create / Strengthen / Refine / Split**"
- 10_4 §5.2: "ReflectionExecutionResult 是执行报告，不是业务数据"
- 10_4 §7.4: "**Evidence Completeness Constraint — 每条高层 Memory 必须有完整证据链**"

**结论**：
- MVP 草案中的 proposal 类型 `Create/Strengthen/Refine/Split` **与架构一致** ✅
- 但需要补充 `Ignore` 类型（当 Reflection 认为无需更新时）— 这是 ReflectionPipeline 的合法产出
- Proposal 应包含：type、target_level（L1/L2/L3）、evidence_chain（证据 ID 列表）、confidence、summary

**对应架构章节**：
- 10_4 §7.2: "Semantic Evolution Decision — Create / Strengthen / Refine / Split"

---

### Item 5: Evolution Configuration ⚠️ ARCHITECTURE AMBIGUOUS

**问题**：MVP 草案是否需要外部 evolution 配置文件（reflection.yaml）？

**架构规定**：
- D1 §2.2: "Configuration Management — Environment config, logging, error handling"
- 10_1 §11: "Configuration — Environment config, logging, error handling"
- 10_4 §8: "Trigger 四类 — Event / Schedule / Manual / System"
- 10_4 §10.2: "Maximum Reflection Horizon — 可配置"

**分析**：
- 架构文档提到了 "可配置" 的概念，但未定义具体的配置文件格式或位置
- D1 阶段已有基础配置管理（环境变量、logging），但 Reflection 相关参数未纳入
- 10_4 提到 "可配置" 但未指定配置来源

**结论**：❌ **ARCHITECTURE AMBIGUOUS** — 配置管理细节未在已冻结文档中定义。

**建议**：
- MVP 阶段使用 **环境变量** 传递配置（如 `REFLECTION_TEMPERATURE=0.3`、`REFLECTION_HORIZON_DAYS=10`）
- 这符合 D1 已有的配置模式（环境变量 + logging）
- 后续阶段可引入 YAML/JSON 配置文件（需 D1 文档更新）

---

## 六、修订后的 MVP_Evolution_Plan.md

以下是修订后的完整文档：
### Phase E1: ReflectionEngine 骨架（核心）

**文件**：`backend/src/backend/engine/reflection_engine.py`

ReflectionEngine 是单一 Engine，内部包含多个 Component。所有 LLM 调用通过 `ReflectionProvider` 接口。

```
ReflectionEngine (单一 Engine)
+-- FactExtractorComponent     -- LLM 辅助的事实提取（通过 Provider）
+-- InterestAnalyzerComponent   -- 规则驱动的兴趣趋势分析
+-- ProjectionUpdaterComponent  -- 规则驱动的 Memory Pyramid 更新建议
+-- ReflectionValidator         -- 领域不变量验证
```

**组件职责**：

1. **FactExtractorComponent**
   - 输入：一批 L0 Memory 的 content + ReflectionProvider
   - 输出：结构化事实列表 {entity, relation, timestamp, confidence}
   - 实现：ReflectionService 调用 Provider.generate() -> 解析 JSON -> 返回给 FactExtractorComponent
   - 注意：LLM 调用由 ReflectionService 通过 Provider 完成，ReflectionEngine 只负责解析和验证

2. **InterestAnalyzerComponent** -- 纯规则算法
   - 输入：事实列表 + 时间窗口
   - 输出：兴趣趋势（上升/下降/稳定）、关键词权重
   - 不依赖 LLM

3. **ProjectionUpdaterComponent** -- 纯规则算法
   - 输入：事实 + 实体名称列表 + 兴趣趋势
   - 输出：Memory Pyramid 更新建议列表
   - Proposal 类型：Create / Strengthen / Refine / Split / Ignore
   - 每个 proposal 包含：type、target_level（L1/L2/L3）、evidence_chain、confidence、summary
   - 遵循：Semantic Evolution Decision（10_4 7.2）

4. **ReflectionValidator**
   - 验证：证据链完整性（每条高层 Memory 必须有证据链 -- 10_4 7.4）
   - 验证：语义唯一性（同层同一语义空间只有一个有效 Memory -- 10_4 3.5）
   - 验证：L0 保护（不产生 L0 变更）

**Provider Abstraction**：
```python
# backend/src/backend/shared/providers/reflection_provider.py
from abc import ABC, abstractmethod

class ReflectionProvider(Protocol):
    @abstractmethod
    async def generate(self, prompt: str, context: dict) -> dict:
        """LLM inference entry point, returns structured JSON"""
        ...

# MVP 实现
class OllamaReflectionProvider(ReflectionProvider):
    def __init__(self, model: str = "reflection-engine", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature
    
    async def generate(self, prompt: str, context: dict) -> dict:
        # Call Ollama API
        ...
```

---

### Phase E2: ReflectionService 编排

**文件**：`backend/src/backend/service/reflection_service.py`

ReflectionService 是 **Business Capability Orchestrator**（10_4 6.1），拥有 ReflectionProvider 实例。

1. `reflect(scope="daily", limit=50)` -- 编排完整 Reflection 流程
2. `getReflectionStatus(taskId)` -- 查询执行状态
3. 返回：`ReflectionExecutionResult`（执行报告，非业务数据 -- 10_4 5.2）

**编排流程**：
```
ReflectionService.reflect(scope, limit)
    1. 从 Repository 获取候选 L0 Memories（按 scope 过滤）
    2. 调用 Provider.generate() -> raw_llm_output
    3. FactExtractorComponent.parse(raw_llm_output) -> facts[]
    4. 调用 EntityEngine.resolve_entities(facts) -> entity_map
       （或 MVP 简化：仅记录实体名称字符串，待人工批准后处理）
    5. InterestAnalyzerComponent.analyze(facts) -> trends
    6. ProjectionUpdaterComponent.propose(facts, entity_map, trends) -> proposals[]
    7. ReflectionValidator.validate(proposals) -> 验证通过/拒绝
    8. 将 proposals 写入 SandboxStorage（不写生产 DB）
    9. 发布 DomainEvent: ReflectionCompleted
```

**关键设计决策**：
- EntityResolver 跨 Service 调用 -> MVP 阶段 Entity 解析简化为名称匹配，不尝试解析到 EntityID
- 实体 ID 映射在人工批准后才正式创建（通过 EntityService）
- ReflectionService 不调用其他 Service（Service Independence Principle -- G-005）

---

### Phase E3: Sandbox Storage + Review API

**文件**：`backend/src/backend/repository/sandbox_repository.py`

1. 内存级存储（或 SQLite 临时表）
2. 存储 Reflection 产出物：facts, entities, proposals
3. 提供 Review API：
   - `GET /api/review/proposals` -- 列出待审建议
   - `POST /api/review/proposals/{id}/approve` -- 批准并写入正式 DB
   - `POST /api/review/proposals/{id}/reject` -- 驳回

**批准流程**：
```
Approval -> MemoryService.capture() / MemoryService.mergeMemories()
        -> EntityEngine.createEntity() (if new entity)
        -> 写入正式 memory_nodes 表
```

---

### Phase E4: Cron Integration + Dashboard UI

1. Cron API 增加 `type: "evolution"` 时调用 `ReflectionService.reflect()`
2. Dashboard 新增 "Evolution Review" tab（在 Log tab 旁）
   - 显示待审建议列表
   - 一键批准/驳回
   - 批准后自动同步到正式 DB

---

### Phase E5: 日志集成

1. Reflection 每个步骤写入日志（INFO level）
2. 日志 Tab 增加 "evolution" 关键字过滤
3. Dashboard 自动刷新日志（每 5s）

---

## 六、验证标准

| 检查项 | 验收方式 |
|--------|----------|
| 定时任务触发 Reflection | Cron API 设置 interval=60s，观察日志输出 |
| FactExtractor 正确提取 | 注入已知测试数据，验证 JSON 输出 |
| EntityResolver 正确解析 | MVP 阶段仅验证实体名称匹配 |
| InterestAnalyzer 趋势准确 | 对比手动标注结果 |
| ProjectionUpdater 建议合理 | 人工审查 proposals[] |
| Sandbox 隔离 | 确认不写入生产 memory_nodes 表 |
| Review API 批准生效 | 批准后 memory_nodes 出现新记录 |
| 日志完整性 | 日志 Tab 能看到全流程日志 |
| Provider 抽象 | 可替换 OllamaReflectionProvider 为 mock provider |

---

## 七、与现有代码的关系

| 现有文件 | 改动 |
|----------|------|
| `app.py` | 新增 `/api/review/*` 端点 |
| `docker-compose.yml` | 无需改动（已有 cron API） |
| `dashboard_server.py` | 新增 `/api/review` 代理 |
| `dashboard-main.html` | 新增 Evolution Review tab |
| `.gitignore` | 无需改动 |
| **新增** `shared/providers/reflection_provider.py` | ReflectionProvider 抽象接口 |
| **新增** `engine/reflection_engine.py` | ReflectionEngine + 内部 Components |
| **新增** `service/reflection_service.py` | ReflectionService 编排 |
| **新增** `repository/sandbox_repository.py` | Sandbox 存储 |

---

## 八、风险与缓解

| 风险 | 缓解 |
|------|------|
| Ollama 响应慢 | 异步执行 + timeout 控制 |
| LLM 输出不稳定 | temperature=0.3 + strict JSON schema |
| Sandbox 数据丢失 | 每次 Reflection 前导出到日志 |
| 实体冲突 | MVP 阶段简化为名称匹配，人工批准时处理 |
| 无限循环 | Scope 锁 + Maximum Reflection Horizon |
| Provider 耦合 | ReflectionProvider 接口隔离，MVP 仅一个实现 |

---

## 九、配置管理策略

**MVP 阶段使用环境变量**（符合 D1 已有配置模式）：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `REFLECTION_TEMPERATURE` | `0.3` | LLM 推理温度 |
| `REFLECTION_MODEL` | `reflection-engine` | Ollama 模型名 |
| `REFLECTION_HORIZON_DAYS` | `10` | 最大 Reflection 回溯天数 |
| `REFLECTION_INTERVAL_SECONDS` | `300` | 定时任务间隔 |
| `REFLECTION_LIMIT` | `50` | 每次处理的 L0 Memory 数量 |

后续阶段可引入 `reflection.yaml` 配置文件（需 D1 文档更新）。

---

*本方案基于 Certified Architecture Baseline (D1-D6) 编写，所有修改均有架构文档引用依据。*
*审查日期: 2026-07-26*
