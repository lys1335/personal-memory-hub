# M1/M3/M6 只读调查报告

**状态**: 调查完成（READ-ONLY）
**调查时间**: 2026-09-06 ~ 2026-09-07
**调查者**: @arch-laguna（PM: @pm-hy3 派发）
**前置**: D5-3 FINAL CLOSED @ commit `0e4cf20`
**修改文件数**: 0
**新建文件数**: 0
**commit/push**: 无

---

## §1. app.py composition root

**文件**: `backend/src/backend/app.py`（**2032 行**，78 KB）

### 顶层符号清单

| 类别 | 符号 | 行号 |
|---|---|---|
| 模块 docstring | `Personal Memory Hub - FastAPI Application` | 1–5 |
| stdlib imports | `asyncio, json, logging, os, sys, threading, asynccontextmanager, asdict, datetime/timedelta, Path, Any, UUID` | 7–18 |
| 路径修复 | `sys.path.insert(0, ...)` | 21 |
| shared imports | `generate_uuid, CronSafetyValidator` | 23–24 |
| third-party | `FastAPI/Body/Depends/HTTPException/Query/Request/Header, CORSMiddleware, HTMLResponse/Response, AsyncSession` | 26–29 |
| backend imports | `entry.dto, entry.rest_adapter, service.{entity_service,memory_service,query_service,reflection_service,task_service}, shared.infrastructure.{config.settings,database.engine}` | 31–39 |
| 全局常量 | `AUTO_APPROVE_PROPOSALS, AUTO_APPROVE_THRESHOLD, AUTO_APPROVE_MAX_LEVEL` | 99–103 |
| 全局缓存 | `_perf_cache`, `_perf_cache_ttl` | 106–110 |
| FastAPI 依赖工厂 | `require_cron_admin`, `validate_no_test_task`, `get_session`, `get_repositories`, `get_services` | 46, 83, 113, 120, 151 |
| 生命周期 | `lifespan(app)` | 219–271 |
| App 实例 | `app = FastAPI(...)` + CORS | 275–289 |
| HTTP endpoints | 38 个 `@app.get/post/put`（health/performance/memory/proposal/entity/cron/sandbox/logs/dashboard） | 296–1998 |
| 模块级状态 | `_cron_lock, _cron_tasks, _CRON_DIR, _CRON_DATA_FILE, _sandbox_proposals, _sandbox_lock, _SANDBOX_DATA_FILE, _cron_scheduler_task, DEFAULT_WORKSPACE, _services, _services_ready, _services_init_event` | 1186–1321 |
| 同步工具函数 | `_load_cron_tasks, _save_cron_tasks, _initialize_default_tasks, _load_sandbox, _save_sandbox` | 1197, 1207, 1229, 1608, 1621 |
| 后台循环 | `_cron_scheduler_loop` | 1263–1310 |
| 嵌套函数 | `_extract_content_text` + `_extract_multimodal_text` | **1830, 1863** |

### 初始化顺序（`get_services` 内）

1. `EmbeddingService`（`settings.PMH_OLLAMA_BASE_URL / EMBEDDING_MODEL`）
2. `MemoryService`（注入 8 个 repo + `embedding_service`）
3. `QueryService`（6 个 repo）
4. `EntityService`（entity_repo + relationship_repo）
5. `ReflectionService`（memory_node_repo + candidate_repo + relationship_repo）
6. `TaskService`（task_repo）
7. **Phase 21 编排**: `EvidencePipelineService(session)`、`FormationService(session)`、`TopicService(session)`、`EvolutionService(session)` — 直接以 session 而非 repo 注入

### composition root 责任边界

- ✅ 入口薄路由 + 依赖工厂（DI 容器雏形）
- ⚠️ **同一文件内同时承担**: cron 状态机（持久化 JSON 文件 + threading.Lock + 后台轮询 loop）、sandbox 提案管理、performance 监控缓存、log viewer
- ⚠️ Phase 21 services 用 `session` 而非 repo 注入，与 D3 BaseService 的「Repository-mediated」约定不一致
- ⚠️ `app.py:1863 _extract_multimodal_text` 是定义在 endpoint 内的 **嵌套函数**，逻辑与 `ingest/adapters/chatgpt.py:375` 高度重复（见 §3）

---

## §2. 当前编排层 / 调用链

### EvidencePipelineService

**文件**: `backend/src/backend/service/evidence_pipeline_service.py`（**304 行**）

责任矩阵：

| 责任 | 行为 | 行号 |
|---|---|---|
| 事务所有权 | OWN（begin / commit / rollback 全包） | 97–99, 171, 193 |
| 子服务编排 | 持有 `ContextWindowFormulator` / `UserSemanticInterpreter` / `FormationService` / `TopicService` / `EvolutionService` | 100–104 |
| 流程步骤 | Form ContextWindow → Interpret → Form → Extract Topics（user-only）→ [deprecated _evolve] | 127–168 |
| 错误边界 | try/except → `PipelineResult(success=False, error=str(e))` | 191–206 |
| 退化路径 | `_evolve()` 已 deprecated，由 `EvolutionService.evolve_entity_history()` 替代 | 281–304 |
| **P2 bug 痕迹** | line 168 `topic_ids = []` 在 if 之后无条件覆盖 | 155–168 |

### 调用链图

```
Entry (app.py)
  └─ Depends(get_services)
      ├─ get_repositories(session) → 12 repositories
      │   └─ get_services(...)
      │       ├─ MemoryService ── [8 repo + EmbeddingService]
      │       ├─ QueryService   ── [6 repo]
      │       ├─ EntityService  ── [2 repo]
      │       ├─ ReflectionService ── [3 repo + ReflectionProvider(opt)]
      │       │   └─ _run_engine_pipeline (lazy import)
      │       │       ├─ backend.engine.reflection_engine.ReflectionEngine
      │       │       └─ backend.engine.evidence_evolution_engine.EvidenceEvolutionEngine
      │       ├─ TaskService    ── [1 repo]
      │       └─ Phase 21 (session-injected):
      │           ├─ EvidencePipelineService
      │           │   ├─ ContextWindowFormulator (backend/context/)
      │           │   ├─ UserSemanticInterpreter (backend/context/)
      │           │   ├─ FormationService (Phase 21.5)
      │           │   │   └─ ReconstructionRepository + CandidateRepository + EntityRepository
      │           │   ├─ TopicService (Phase 21.6) → TopicRepository
      │           │   └─ EvolutionService (Phase 21.7)
      │           │       └─ CandidateRepository + MemoryNodeRepository
      │           │           + RelationshipRepository + TopicRepository
      │           ├─ FormationService (standalone, also in get_services)
      │           ├─ TopicService
      │           └─ EvolutionService
```

### 事务边界

- Entry 不持有事务
- `MemoryService` / `QueryService` / `EntityService` / `ReflectionService` / `TaskService`: **不提交**（持 repo，repo 持 session）
- `EvidencePipelineService`: **OWN**（line 171 `_commit`, 193 `_rollback`）
- `FormationService` / `TopicService` / `EvolutionService`: **不 commit/rollback**（line 17 comment: "the caller's responsibility"），复用 pipeline 事务
- **风险**: Phase 21 services 在 `get_services` 中**被重复实例化**（line 201–204 各一份），与 `EvidencePipelineService` 内部持有的不是同一对象 → 状态分裂

### Orchestrator / Pipeline 关键字

- `EvidencePipelineService`（Phase 21 主编排）
- `FormationPipeline` 类（line 483–514，**保留为向后兼容**，显式注释让用 `FormationService` 替代）
- `TaskService`（任务执行编排）
- `ReflectionService`（reflection 业务编排，调用 Engine）
- `MemoryService.import_memories`（line 452–481，调用 `ImportPipeline`）

---

## §3. 共享抽取器

### 全仓 `extractor` 关键字清单

| 类型 | 位置 | 返回 | 用途 |
|---|---|---|---|
| 嵌套函数 `_extract_multimodal_text` | `backend/src/backend/app.py:1863` | `str`（`"\n".join(texts)`）| `get_evidence_memories` 端点解析 multimodal content |
| 实例方法 `_extract_multimodal_text` | `backend/src/backend/ingest/adapters/chatgpt.py:375` | `list[str]` | ChatGPT adapter 解析 multimodal content |
| 模块函数 `extract_text_segments` | `backend/src/backend/ingest/parser.py:61` | `str` | 跨 adapter 通用：按多 key 列表从 dict 递归取首个非空值 |
| 模块函数 `try_parse_json` | `backend/src/backend/ingest/parser.py:15` | `dict|list|None` | JSON 解析 + 失败返回 None |
| 模块函数 `sanitize_content` | `backend/src/backend/ingest/parser.py:31` | `str` | 内容清洗（strip/newlines/truncate） |
| 引擎内方法 `_extract_facts` | `engine/reflection_engine.py:141` | LLM 抽 facts | reflection 业务（**不应**提到 parser 层） |
| 引擎内方法 `_extract_facts` | `engine/evidence_evolution_engine.py:160` | LLM 抽 facts | evolution 业务（**不应**提到 parser 层） |
| 业务方法 `extract_topics_from_summary` | `service/topic_service.py:109` | `list[UUID]` | topic 提取（业务，与解析无关） |
| 业务方法 `_extract_conversations / _extract_timestamp` | `ingest/adapters/open_webui.py:190, 207` | list / str | Open WebUI 专属抽取（合理内聚） |

### 是否存在共享抽取器

**否**。**唯一显式共享模块**是 `backend/ingest/parser.py`（仅含 `try_parse_json` / `sanitize_content` / `extract_text_segments` 三个 helpers）。

### 重复点（事实）

1. **`_extract_multimodal_text`** 在两处独立实现：
   - `app.py:1863` 嵌套函数（depth ≤ 5，返回 `str`）
   - `chatgpt.py:375` 实例方法（depth ≤ 5，返回 `list[str]`）
   - 跳过 key 集合在两处均含 `asset_pointer / content_type / metadata / decoding_id / direction / tool_audio_direction / frames_asset_pointers / video_container_asset_pointer / expiry_datetime`
   - **调用入口**: `app.py:1852/1859` 在 endpoint 内使用；`chatgpt.py:359` 在 ChatGPTAdapter 内使用

2. **JSON 解析逻辑** `app.py:1840–1848`（`_json.loads` → 失败 fallback `ast.literal_eval`）与 `parser.py:try_parse_json` 仅做 `json.loads`，**行为不一致**（app.py 多 fallback 一层）

### 建议合并点（建议，非事实）

- 将 `_extract_multimodal_text` 提取到 `backend/ingest/parser.py`（或新建 `backend/ingest/multimodal.py`），统一返回 `list[str]`，调用方决定 join
- `app.py:1840-1848` 的 JSON 解析应委托 `parser.try_parse_json` 或新增 `try_parse_python_dict`
- `chatgpt.py` 内的 `_extract_multimodal_text` 替换为导入调用
- `app.py` 的端点逻辑应下沉到 service 或 ingest 层

### 抽取器形态分类

- **当前**: inline 嵌套函数 + 重复实现混用
- **建议**: 已抽取（parser.py）+ 单点提取 multimodal 目标态

---

## §4. Service / Engine / Repository 依赖

### 顶层目录结构

```
backend/src/backend/
├── entry/             (D5: HTTP 适配层, 4 文件)
├── service/           (D3: 14 文件, 9 BaseService 子类 + base/dto/exceptions/embedding/entity_resolution)
├── engine/            (D4: 9 文件, 8 engine + base)
├── repository/        (D2: 22 文件, 12 repo + base/exceptions/pagination/proposal/query/types/workspace)
├── context/           (Phase 21.3-21.4: 4 文件, ContextWindow + Formulator + Interpretation + Interpreter)
├── shared/            (infrastructure + providers)
└── ingest/            (D6+? : 7 文件, base + dto + exceptions + parser + registry + adapters/{chatgpt, open_webui})
```

### 依赖图（service → 注入项）

| Service | 注入项数 | 注入列表 |
|---|---|---|
| **MemoryService** | **9** | memory_node_repo, evidence_repo, relationship_repo, archive_repo, tag_repo, task_repo, memory_query_repo, vector_doc_repo?, embedding_service? |
| QueryService | 6 | memory_node_repo, memory_query_repo, entity_repo, entity_query_repo, vector_query_repo, vector_doc_repo |
| EntityService | 2 | entity_repo, relationship_repo |
| **ReflectionService** | **4** | memory_node_repo, candidate_repo, relationship_repo, reflection_provider? |
| TaskService | 1 | task_repo |
| EvidencePipelineService | 5 (session + 4 子 service) | session + ContextWindowFormulator + UserSemanticInterpreter + FormationService + TopicService + EvolutionService |
| FormationService | 4 (session + 3 repo) | session + ReconstructionRepository + CandidateRepository + EntityRepository |
| TopicService | 2 (session + 1 repo) | session + TopicRepository |
| EvolutionService | 5 (session + 4 repo) | session + CandidateRepository + MemoryNodeRepository + RelationshipRepository + TopicRepository |
| EmbeddingService | 0 (stateless) | ollama_base_url, model |

### 循环依赖识别

- `service → service`: **无环**（仅 `EvidencePipelineService` → `EvolutionService/FormationService/TopicService`，单向；被引用的 service 不再反向 import 编排层）
- `service → engine`: **无 import**（仅 `reflection_service.py:915–916` 在函数体内 lazy-import `EvidenceEvolutionEngine / ReflectionEngine`，避免模块级循环）
- `engine → service`: **无 import**（仅 `engine/base.py` 提及「domain exception」文本）
- `engine → engine`: 无引用（每个 engine 仅依赖 base + provider）
- ✅ 当前依赖图是 **DAG**

### God Service 确认

- **MemoryService** = 9 个注入项 + 1053 行 → **确认是 God Service**
  - 注入对象横跨 memory_node / evidence / relationship / archive / tag / task / vector 7 个 repo + embedding 1 service
  - 内部公开方法至少包含: `capture_memory / search_memory / reflect_memory / retrieve_memory / list_memories / import_memories / approve_proposal / reject_proposal / list_proposals / get_proposal_evidence` 等（基于 app.py 调用形态推断）
  - 风险：违反 SRP（混读/写/lifecycle/reflection 调度），新增依赖时构造函数参数爆炸，DI 工厂 `get_services` line 164–174 已显式拖累

---

## §5. Frozen 影响

### 相关 Frozen 范围（事实）

1. **架构冻结**（`docs/05_Implementation/ARCHITECTURE-FREEZE-CHECKLIST.md`，2026-08-05）
   - 状态: ✅ **ARCHITECTURE FROZEN**
   - 允许: 文档修正、ADR 新增、术语更新
   - 禁止: **新增 Engine 无 ADR、Pipeline 重构无 ADR、术语变更无 Terminology Freeze 更新**

2. **Repository Layer Frozen**（`D2_Repository_Layer_Plan.md` §15.2-15.3）
   - Repository 契约 frozen，任何变更需 ADR

3. **Service Contracts**（`D3.7_Error_Handling_DTO_Models.md`, `D3.8_Service_Test_Suite.md`）
   - Error Taxonomy 7 类 frozen
   - Service contracts frozen，测试 = 契约黑盒

4. **Engine Contracts**（`engine/__init__.py:14` 注释 + `D4_*`）
   - "Engine contracts are stable. Changes require ADR."

5. **Phase 21.* 冻结范围**（ADR-D5-2, ADR-D5-3 引用）
   - `evolution/` 包 frozen（Phase 21.7）
   - Topic 子系统（Phase 21.6 Stage 2.2 frozen design）

### M1/M3/M6 触及点判定

| Task | 触及 | 是否触 Frozen |
|---|---|---|
| **M1** composition root 重构（拆分 `app.py` 2032 行） | **不**改 Service/Engine/Repository 契约；只移动 HTTP endpoint / 拆 cron 状态机 / 拆 sandbox | **可能不触** Frozen contract（属于 Entry Layer 内部结构调整）。但若拆分涉及新增 Service 入口或新增 Engine，则触 Frozen → **需 ADR** |
| **M3** 编排层重构（`EvidencePipelineService` 重构 + 去除重复实例化 + `_extract_content_text` / `_extract_multimodal_text` 下沉） | 修改 Service 内部分层、修改 `get_services` 工厂 | **需审视**: 若 `EvidencePipelineService.process_evidence` 签名变更 → 触 Service contract Frozen → **需 ADR**。若仅内部实现调整 → **不触**。`FormationPipeline` 类（line 483）已有「向后兼容」注释，可作为前例 |
| **M6** 共享抽取器合并（`app.py:1863` + `chatgpt.py:375` 提取到 `backend/ingest/parser.py` 或新模块） | 修改 `app.py` 内部 + `chatgpt.py` import；**不**改 public API | **不触** Frozen（属于内部实现 + ingest adapter 内部，Entry contract 不变） |

### 是否需要 Controlled Defrost

- **M1**: **可能需要**（如拆 cron 状态机到独立模块，需评估是否构成 Service / Engine 数量变更）
- **M3**: **需要局部 Controlled Defrost**（涉及 `EvidencePipelineService` 重构，需要 ADR 明确：「process_evidence 签名是否变更」「FormationPipeline 兼容性策略」）
- **M6**: **不需要 Defrost**（纯内部重构，公共契约零变更）

### M3 Defrost 建议范围

**允许清单**:
- `EvidencePipelineService` 内部子服务实例化去重（仅 `get_services` 工厂调整）
- `_evolve()` 已 deprecated 方法移除
- `FormationPipeline` 类（向后兼容壳）标记 `@deprecated` 并保留至下个 major 版本
- 事务所有权文档注释强化

**禁止清单**:
- **不得新增 Engine**（frozen）
- **不得修改 Error Taxonomy**（frozen）
- **不得修改 public Service 签名**而不发 ADR（frozen）
- **不得修改 Repository 契约**（frozen）
- **不得修改 Pipeline 拓扑**（form → interpret → form → topic）而发 ADR（frozen）

---

## §6. M1/M3/M6 任务定义 v1 初稿要素

### M1 — composition root 重构

- **代码变更范围**:
  - `backend/src/backend/app.py`（2032 → 拆分为多文件，目标 ≤500 行）
  - 抽出候选:
    - `backend/entry/http/health.py`（health/performance/logs endpoints）
    - `backend/entry/http/memory.py`（memory capture/search/retrieve/list/proposals/evidence）
    - `backend/entry/http/entity.py`（entity/area/list endpoints）
    - `backend/entry/http/cron.py`（cron task CRUD + scheduler loop + cron/sandbox state）
    - `backend/entry/http/reflection.py`（reflect/trigger endpoints）
    - `backend/entry/http/dashboard.py`（HTML/proxy endpoints）
  - `backend/entry/di.py`（独立 `get_repositories` / `get_services` 工厂，含 Phase 21 services 合并去重）
- **测试适配规则**:
  - 现有 `tests/` 中所有 endpoint 调用路径不变（URL 不变、payload 不变）
  - DI 工厂改为 FastAPI `app.include_router(router, dependencies=[Depends(get_services)])` 形式，测试覆盖 `get_services` 返回 dict 的 keys
- **文档产出**:
  - 新增 `docs/05_Implementation/ADR-D5-1.x-app-py-split.md`（如构成 Service 入口新增需 ADR；否则仅实施报告）
  - 实施报告: `docs/d5-1.x-composition-root-refactor.md`
- **验证清单**:
  - [ ] `pytest backend/tests/` 全绿
  - [ ] `app.py` 行数 ≤500
  - [ ] 所有现有 HTTP 端点 URL/响应 schema 不变
  - [ ] `get_services` 不再重复实例化 Phase 21 services（MemoryService 实例数 = 1，Formation/Topic/Evolution 各 1）
- **执行顺序**: 先抽出 di.py → 再拆 endpoints → 最后清理 app.py
- **Frozen 处理**: 不触 Frozen；提交前确认无新增 Service

### M3 — 编排层重构

- **代码变更范围**:
  - `backend/src/backend/service/evidence_pipeline_service.py`（304 行 → 保留，但修复 line 168 `topic_ids = []` bug）
  - `backend/src/backend/app.py:get_services`（line 195–215，Phase 21 services 实例化去重）
  - `_evolve()` 方法移除（已 deprecated，line 281–304）
  - `FormationPipeline` 类标记 `@deprecated`（`formation_service.py:483`）
- **测试适配规则**:
  - `test_evidence_persistence_fix.py` / `test_p0_evidence_uuid_fix.py` 等 Phase 21 集成测试无 breaking change
  - 需新增 `tests/test_evidence_pipeline_service_dedup.py`（验证单次实例化）
- **文档产出**:
  - **必须**: `docs/05_Implementation/ADR-D5-3.x-pipeline-refactor.md`（包含：签名变更？FormationPipeline 退役策略？`_evolve` 删除窗口？）
  - 实施报告: `docs/d5-3.x-pipeline-orchestrator-refactor.md`
- **验证清单**:
  - [ ] `process_evidence` 签名不变（除非 ADR 明确声明 breaking）
  - [ ] Phase 21 services 各仅 1 实例
  - [ ] `_evolve()` 已删除且无内部调用
  - [ ] `FormationPipeline` 标记 deprecated 但保留
  - [ ] 事务边界保持（pipeline OWN / others reuse）
- **执行顺序**: 先 ADR → 写 dedup 测试 → 改 `get_services` → 修复 line 168 bug → 删除 `_evolve`
- **Frozen 处理**: **Controlled Defrost** — 严格按 §5 允许/禁止清单执行，ADR 必须含「不修改 Pipeline 拓扑」声明

### M6 — 共享抽取器合并

- **代码变更范围**:
  - 新增 `backend/ingest/parser.py` 增加 `extract_multimodal_text(data, depth=0, max_depth=5) -> list[str]`
  - `backend/src/backend/app.py:1863` 嵌套函数删除，改为 `from backend.ingest.parser import extract_multimodal_text`
  - `backend/src/backend/ingest/adapters/chatgpt.py:375` 实例方法删除，改为相同 import
  - `app.py:1830 _extract_content_text` 重构为委托 ingest 层（含 `_json.loads → ast.literal_eval` fallback 也下沉）
- **测试适配规则**:
  - 不动现有测试（公共接口零变更）
  - 新增 `tests/test_ingest_parser_multimodal.py`（覆盖两处原行为的兼容 case）
- **文档产出**:
  - 仅实施报告: `docs/d5-6.x-shared-extractor-merge.md`（无需 ADR — 纯内部重构）
- **验证清单**:
  - [ ] `_extract_multimodal_text` 全仓仅 1 处实现（在 parser.py）
  - [ ] `app.py` 与 `chatgpt.py` 行为输出与重构前等价（逐 case 对比）
  - [ ] `pytest backend/tests/` 全绿
- **执行顺序**: 先写测试 → 提取到 parser.py → 改两处调用方 → 删除原嵌套/方法 → 跑测试
- **Frozen 处理**: 不需要 Defrost；纯 ingest/entry 内部重构

### 三者协同执行顺序建议

**M6 → M1 → M3**（M6 风险最低可并行；M1 先建 di.py 为 M3 的去重做铺垫；M3 最后做语义性最强的修改）

---

## §7. 明确区分

### 事实（来自 grep / wc / read_file）

- HEAD = `0e4cf20`
- `app.py` 2032 行；`evidence_pipeline_service.py` 304 行
- `MemoryService.__init__` 注入 9 项（8 repo + 1 service）
- `_extract_multimodal_text` 在 `app.py:1863` + `chatgpt.py:375` 两处实现（行为同构、返回类型不同）
- `EvidencePipelineService` line 168 `topic_ids = []` 在 if 块外无条件重置
- `get_services` line 201–204 重复实例化 Phase 21 services
- 依赖图 DAG（service/service、service/engine、engine/service、engine/engine 均无环）
- `extract_text_segments` / `sanitize_content` / `try_parse_json` 已在 `backend/ingest/parser.py` 共享
- ARCHITECTURE-FROZEN 状态（2026-08-05）：Engine/Service/Repository 契约 frozen，变更需 ADR

### 风险

- MemoryService 9 依赖 → DI 工厂 line 164–174 难维护，新增第 10 依赖会爆炸
- EvidencePipelineService line 168 在 if (`interpretation.user_owned`) 之外写 `topic_ids = []`，若 if 不触发、变量未在 else 初始化过，则函数返回时 `topic_ids` 未定义（unbound error）
- Phase 21 services 重复实例化 → `EvidencePipelineService` 持有的 `FormationService/TopicService/EvolutionService` 与 `get_services` 返回 dict 中的同名实例**不是同一个对象**；但二者共用 session，所以事务一致，但**对象状态可能分裂**（如 cache）
- `_extract_multimodal_text` 重复实现 + skip_keys 集合需手动同步，未来 ChatGPT 格式扩展时容易遗漏 `app.py` 一侧
- `app.py` 2032 行同时承担: 入口路由 + cron 状态机 + sandbox 持久化 + performance 缓存 + log viewer → 单文件 modification blast radius 大

### 建议（重构方向）

- M1: 按 HTTP domain 拆分 endpoint 到 router；cron 状态机抽到 `backend/cron/` 包
- M3: `EvidencePipelineService` 子服务从 `get_services` 工厂复用；修复 line 168
- M6: `_extract_multimodal_text` 提取到 `backend/ingest/parser.py`；`app.py` 端点的 `_extract_content_text` 下沉为 service 方法

### 必须修改的内容（明确边界）

1. `app.py:1863` 嵌套 `_extract_multimodal_text` → 删除并改 import（M6）
2. `chatgpt.py:375` 实例方法 → 删除并改 import（M6）
3. `get_services` line 195–215 → Phase 21 services 单实例化（M3）
4. `evidence_pipeline_service.py:168` → 修复 `topic_ids` 作用域 bug（M3）
5. `evidence_pipeline_service.py:281-304 _evolve()` → 删除（M3，deprecated）
6. `formation_service.py:483 FormationPipeline` → 标记 `@deprecated`（M3，**保留**作为向后兼容）

### 不建议触动（保持冻结）

- Engine 内部算法（reflection_engine / evidence_evolution_engine 的 fact 抽取逻辑）
- Repository 契约（12 个 repo 的 public method 签名）
- Error Taxonomy 7 类
- Pipeline 拓扑（Form → Interpret → Form → Topic）
- 术语（Evidence / Candidate / Proposal / MemoryNode / Fact）

---

## 待 PM / @user 决策

1. **M3 是否进入 Controlled Defrost 流程？**（推荐：是 — 因涉及 Service 内部重构）
2. **M6 是否可作为 M1 的前置？**（推荐：是 — M6 风险最低，可独立 ship）
3. **MemoryService 拆分是否纳入 M1 范围？**（当前 M1 初稿**未**含；待 PM 决定是否另开 M2 或并入 M1）
4. **`FormationPipeline` 退役策略**: 标记 deprecated 后下个 major 版本删除？保留 N 个版本？（待 PM 决策时间窗口）

---

## 报告元数据

- **调查者**: @arch-laguna（PM @pm-hy3 派发）
- **调查时间**: 2026-09-06 ~ 2026-09-07
- **前置**: D5-3 @ `0e4cf20`（FINAL CLOSED）
- **修改文件数**: 0
- **新建文件数**: 0
- **commit/push**: 无
- **进入 M1/M3/M6 实施**: 否（仅调查 + 起草建议）
