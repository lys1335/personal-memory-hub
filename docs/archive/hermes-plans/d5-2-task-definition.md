# D5-2 evolution/ 包重构 — 任务定义 v2

**状态**: TASK DEFINITION v2（基于 §5.1 预检发现修订；待 @user 再次授权）
**生成时间**: 2026-09-04
**生成者**: @pm-hy3
**前置依赖**: D5-1 PASS；D5-2 §5.1 预检 PASS（含 4 项裁决）
**授权范围**: 仅 D5-2；Step 3 MemoryHubError 迁移仍需单独授权
**v1 → v2 修订要点**: 见 §0；新增 §3.5 import 完整分类；§6.2 测试约束放宽

---

## 0. v1 → v2 修订要点

| 项 | v1 | v2 | 原因 |
|---|---|---|---|
| EvolutionEngine 删除 | 明确删除（§6.1）| 仍删除，但增加测试适配约束（§6.2）| @user 裁决 1(a)：允许最小必要测试适配 |
| 测试修改 | 明确禁止（§6.2）| **仅允许**对 `test_evolution_regression.py` 因 `EvolutionEngine` 删除而失效的引用/断言做最小适配（§6.2）| @user 裁决 1(a) |
| EvolutionResult 范围 | 模糊 | 仅迁移 `evolution/evolution_result.py`；`engine/evidence_evolution_engine.py` 内同名类保持不动（§3.3）| @user 裁决 2(a) |
| TopicEvolutionService | 未提及 | 随 `evolution_engine.py` 删除而消失；不单独迁出（§3.4）| 预检发现 `TopicEvolutionService` 定义在 `evolution_engine.py` 中；Engine 删除后类自然消解 |
| VALID_TRANSITIONS | 模糊 | 仅保留 `evolution_service.py` 内一份；Engine 删除后 `evolution_engine.py` 内重复定义自然消解（§3.5）| @user 裁决 4 |
| import 完整清单 | 仅 4 处（v1 §1.3）| **完整 12 处分类**（§3.5）| 预检发现 v1 清单漏报 |
| D5-1 删除依据 | "测试无依赖"（错误）| 修正为"测试有引用，需适配"（§2）| 预检纠正 D5-1 表述错误 |

---

## 1. 背景与事实基础（沿用 v1，§1 不变）

- 仓库根无 `src/`，代码位于 `backend/src/backend/`
- Phase 1 (P0-1 / P0-2) 已完成并同步
- D5-1 调查结论：方案 A 基于证据成立

---

## 2. 删除 EvolutionEngine 的依据（证据链 v2）

| 证据 | 来源 |
|---|---|
| **不属 Engine**：`EvolutionEngine` 继承 `object`，未继承 `EngineBase` | D5-1 报告 |
| **全仓生产代码无运行时引用**：仅 `evolution/__init__.py` 导出；`app.py` / `evidence_pipeline_service.py` 仅 import `EvolutionService` | §5.1 预检引用统计 |
| **与 EvolutionService 11 方法重复** | D5-1 报告 |
| **`TopicEvolutionService` / `VALID_TRANSITIONS` / `TopicEvolutionResult` 跨文件重复** | §5.1 预检 |
| **测试有引用但可适配**：`test_evolution_regression.py:18-19` 引用 `EvolutionEngine` 与 `TopicEvolutionService`；可通过 import 适配与测试用例重新指向 `EvolutionService` 解决 | §5.1 预检 + @user 裁决 1(a) |
| **不影响业务语义**：所有 11 方法在 `EvolutionService` 已有等价实现 | D5-1 报告 |

**结论**：删除 `EvolutionEngine` 不会破坏运行时行为；测试需做最小适配但业务语义不变。

---

## 3. 代码变更范围

### 3.1 移动

| 源文件 | 目标文件 | 动作 |
|---|---|---|
| `backend/src/backend/evolution/evolution_service.py` | `backend/src/backend/service/evolution_service.py` | 内容迁移（保留所有 import、类、方法体、docstring）|
| `backend/src/backend/evolution/evolution_result.py` | `backend/src/backend/shared/domain/evolution_result.py` | 内容迁移（保留所有内容）|

### 3.2 删除

| 文件/类 | 删除依据 |
|---|---|
| `backend/src/backend/evolution/evolution_engine.py`（含 `EvolutionEngine`、`TopicEvolutionService` 类）| 见 §2 证据链 |
| `backend/src/backend/evolution/__init__.py` | 包内文件迁走/删除后变空 |
| `backend/src/backend/evolution/evolution_result.py` | 迁至 `shared/domain/`（见 §3.1）|
| `backend/src/backend/evolution/evolution_service.py` | 迁至 `service/`（见 §3.1）|
| 整个 `backend/src/backend/evolution/` 目录（含 `__pycache__/`）| 上述文件全部处置后目录为空 |

### 3.3 EvolutionResult 边界（明确）

| 类 | 位置 | 处置 |
|---|---|---|
| `EvolutionResult`（`evolution/evolution_result.py:41`）| 迁移至 `shared/domain/evolution_result.py` | 改名空间冲突：`engine/evidence_evolution_engine.py:30` 也有同名类（不同 dataclass）|
| `EvolutionResult`（`engine/evidence_evolution_engine.py:30`）| **保持不动** | 不强行合并/重命名（@user 裁决 2(a)）|

**重要**：两个 `EvolutionResult` 是不同 dataclass，迁移后 `shared/domain/evolution_result.py` 内的类与 `engine/evidence_evolution_engine.py:30` 内的类在 Python 解释器层面不冲突（不同模块路径），不需任何处理。test_evidence_evolution_engine.py 与 test_p0_evidence_uuid_fix.py 引用的始终是 `engine.evidence_evolution_engine.EvolutionResult`，不受迁移影响。

### 3.4 TopicEvolutionService / TopicEvolutionResult 去向

| 类 | 原位置 | 处置 |
|---|---|---|
| `TopicEvolutionService` | `evolution/evolution_engine.py:449` | **随 Engine 删除而消失**；不单独迁出（@user 裁决 3 隐含：仅位置/import 调整可纳入，发现业务变化立即上报）|
| `TopicEvolutionResult` | `evolution/evolution_result.py:117` | 随 `evolution_result.py` 迁移至 `shared/domain/evolution_result.py` |

**重要**：`TopicEvolutionService` 类本身只在 `evolution/__init__.py` 导出 + `test_evolution_regression.py:20` 引用，**无生产代码运行时调用**。测试中 `test_evolution_regression.py` 引用 `TopicEvolutionService` 的用例属于"测试本身验证该类"的元测试，删除类后该测试用例需适配（见 §6.2）。

### 3.5 VALID_TRANSITIONS 重复定义

| 定义位置 | 处置 |
|---|---|
| `evolution/evolution_engine.py:45` | 随 Engine 删除而消失（@user 裁决 4：自然消解）|
| `evolution/evolution_service.py:49` | 保留（迁至 `service/evolution_service.py:49`）|

**重要**：`VALID_TRANSITIONS` 出现在 `__init__.py` 与 `evolution_service.py`（迁后）和测试中。`__init__.py` 删除后仅剩 `service/evolution_service.py` 与测试中的引用——测试引用需适配 import（见 §6.2）。

### 3.6 import / 引用完整清单（12 处 backend.evolution + 相关）

#### 3.6.1 production 代码（必须更新 import）

| # | 文件 | 行 | 当前 | 新 |
|---|---|---|---|---|
| 1 | `backend/src/backend/app.py` | 198 | `from backend.evolution.evolution_service import EvolutionService` | `from backend.service.evolution_service import EvolutionService` |
| 2 | `backend/src/backend/service/evidence_pipeline_service.py` | 27 | `from backend.evolution.evolution_service import EvolutionService` | `from backend.service.evolution_service import EvolutionService` |

#### 3.6.2 evolution/ 包内自引用（删除目录后自动消解）

| # | 文件 | 行 | 当前 | 处置 |
|---|---|---|---|---|
| 3 | `backend/src/backend/evolution/evolution_engine.py` | 25 | `from backend.evolution.evolution_result import (...)` | 文件删除 |
| 4 | `backend/src/backend/evolution/evolution_service.py` | 28 | `from backend.evolution.evolution_result import (...)` | 迁至 `service/` 后改为 `from backend.shared.domain.evolution_result import (...)` |
| 5 | `backend/src/backend/evolution/__init__.py` | 3 | `from backend.evolution.evolution_result import (...)` | 文件删除 |
| 6 | `backend/src/backend/evolution/__init__.py` | 9 | `from backend.evolution.evolution_engine import (...)` | 文件删除 |

#### 3.6.3 测试代码（按 §6.2 规则处理）

| # | 文件 | 行 | 当前 | 新（最小适配）|
|---|---|---|---|---|
| 7 | `backend/tests/test_evolution_regression.py` | 18-27 | `from backend.evolution.evolution_engine import EvolutionEngine, TopicEvolutionService, VALID_TRANSITIONS` + `from backend.evolution.evolution_result import (...)` | `from backend.service.evolution_service import VALID_TRANSITIONS` + `from backend.shared.domain.evolution_result import EvolutionResult, EvolutionDecision, RelationshipAction, TopicEvolutionResult` |
| 8 | `backend/tests/test_pipeline_integration.py` | 304 | `from backend.evolution.evolution_service import EvolutionService` | `from backend.service.evolution_service import EvolutionService` |
| 9 | `backend/tests/test_pipeline_integration.py` | 363 | `from backend.evolution.evolution_service import EvolutionService` | `from backend.service.evolution_service import EvolutionService` |
| 10 | `backend/tests/test_pipeline_integration.py` | 398 | `from backend.evolution.evolution_service import EvolutionService` | `from backend.service.evolution_service import EvolutionService` |
| 11 | `backend/tests/test_pipeline_integration.py` | 516 | `from backend.evolution.evolution_service import EvolutionService` | `from backend.service.evolution_service import EvolutionService` |

#### 3.6.4 文档/字符串引用（无需修改）

| 位置 | 类型 |
|---|---|
| `backend/src/backend/service/reflection_service.py:905,915,950,985,989` | 字符串/docstring/局部 import，引用 `EvidenceEvolutionEngine`（**不同类**，属 `engine/` 不属 `evolution/`），无需修改 |
| `backend/src/backend/evolution/__init__.py` docstring | 文件删除 |

### 3.7 删除 `evolution/` 后的最终目录状态

```
backend/src/backend/evolution/   → 【删除整个目录】
```

确认无残留：`find backend/src/backend/evolution -type f` 应为 0 结果。

---

## 4. Phase 21.7 Frozen 状态处理（沿用 v1 §3）

**性质**: Phase 21.7 **受控结构性解冻（Controlled Structural Defrost）**

### 4.1 允许清单 ✅

- 包位置调整（`evolution/` → `service/` + `shared/domain/`）
- import 路径更新（11 处已知，§3.6.1 + §3.6.3）
- 死代码删除（`EvolutionEngine`、`TopicEvolutionService`）
- 类型/结果对象归位（`EvolutionResult` / `TopicEvolutionResult` 统一至 `shared/domain/`）
- 测试最小适配（仅限因 `EvolutionEngine` 删除而失效的引用与断言；§6.2 详细规则）

### 4.2 禁止清单 ❌

- 修改 `EvolutionService` 的方法签名、行为、docstring、返回值
- 修改业务逻辑、状态转换、判定规则、`VALID_TRANSITIONS` 值
- 修改数据库 schema 或 alembic 迁移
- 修改 DI 容器（`shared/infrastructure/di/container.py`）
- 新增测试用例
- 借机修复其它问题（lint、typo、未关联 TODO）
- 修改 `engine/evidence_evolution_engine.py` 内同名 `EvolutionResult` 类
- 添加新功能、新方法、新依赖
- 重新组织 `engine/` 或 `service/` 下其它模块
- 修改 `phase21-final-freeze-audit.md` 或 `phase21-7-historical-memory-evolution.md`

### 4.3 验证纪律

- Worker 必须保留所有方法签名、docstring、行内注释
- 若任何方法体需修改，立即停止并上报 @pm-hy3

---

## 5. 验证清单

### 5.1 执行前（沿用 v1，Worker 必须先做）

- [ ] `cd F:\LI_YONGSHUN\AI\personal-memory-hub`
- [ ] `pwd` 确认仓库根
- [ ] `git status` 记录工作区当前状态
- [ ] `git log -1 --oneline` 确认 HEAD
- [ ] 完整 grep §3.6.1 / §3.6.2 / §3.6.3 三类引用，确认无新增引用

### 5.2 执行后（Worker 必须做）

- [ ] 全仓搜索 `backend.evolution` → 应为 0 结果
- [ ] 全仓搜索 `EvolutionEngine` → 应为 0 结果（除 D5-1 报告、ADR、本任务定义文档中的说明文字）
- [ ] 全仓搜索 `TopicEvolutionService` → 应为 0 结果（除文档说明）
- [ ] 全仓搜索 `EvolutionService` → 应仅出现在：
  - `backend/src/backend/service/evolution_service.py`
  - `backend/src/backend/app.py`
  - `backend/src/backend/service/evidence_pipeline_service.py`
  - 测试文件
- [ ] 全仓搜索 `EvolutionResult` → 应仅出现在：
  - `backend/src/backend/shared/domain/evolution_result.py`
  - `backend/src/backend/service/evolution_service.py`
  - `backend/src/backend/engine/evidence_evolution_engine.py`（**保留**，不属本任务）
  - 测试文件
- [ ] 全仓搜索 `TopicEvolutionResult` → 应仅出现在：
  - `backend/src/backend/shared/domain/evolution_result.py`
  - `backend/src/backend/service/evolution_service.py`
  - 测试文件
- [ ] `cd backend && python -m pytest tests/ -x -q` → **全绿**
- [ ] `git diff --stat` → 变更范围应仅含 §3.6.1 + §3.6.3 列出的文件
- [ ] `git diff backend/src/backend/shared/infrastructure/di/container.py` → 应为空（DI 未修改）
- [ ] `git diff backend/alembic/versions/` → 应为空（migration 未修改）
- [ ] `git status` → 工作区变更应仅含预期范围（untracked 文件除外）

### 5.3 范围外变更检查（沿用 v1）

- 不含任何 `*.md` 在 `docs/` 下的非预期修改（ADR 与 execution report 例外）
- 不含任何非 §3.6.3 列出的测试文件变更
- 不含任何 alembic 迁移变更
- 不含任何 DI / config / 配置文件变更
- 不含任何 `repository/`、`engine/`、`service/` 下其它模块变更（除 §3.1/3.6.1 明确允许的）

---

## 6. 交付边界

### 6.1 Worker 允许做（v2 更新）

- 修改 `app.py` 的 1 行 import（§3.6.1 #1）
- 修改 `evidence_pipeline_service.py` 的 1 行 import（§3.6.1 #2）
- 新增 `backend/src/backend/service/evolution_service.py`（内容复制自 `evolution/evolution_service.py`，仅 1 处 import 改为 `shared/domain/evolution_result`，§3.6.2 #4）
- 新增 `backend/src/backend/shared/domain/evolution_result.py`（内容复制自 `evolution/evolution_result.py`）
- 删除 `evolution/` 整个目录（含所有文件 + `__pycache__/`）
- 修改 `backend/tests/test_evolution_regression.py` import（§3.6.3 #7）
- 修改 `backend/tests/test_pipeline_integration.py` 4 处 import（§3.6.3 #8-11）
- 新增 `docs/05_Implementation/ADR-D5-2-Evolution-Service-Migration.md`
- 新增 `docs/d5-2-execution-report.md`

### 6.2 Worker 测试修改边界（v2 新增 / 关键）

**允许**：
- 仅修改 §3.6.3 #7-11 列出的 5 处 import（`backend.evolution.X` → `backend.service.X` / `backend.shared.domain.X`）
- 仅在因 `EvolutionEngine` / `TopicEvolutionService` 类消失而无法运行既有测试用例时，最小适配该用例的引用与断言（仅指向 `EvolutionService` 的等价方法或修改断言使其引用 `EvolutionService`）
- 不改变测试原本验证的业务语义

**禁止**：
- 删除任何测试用例（除非该用例仅验证 `EvolutionEngine` / `TopicEvolutionService` 类的存在性，且该存在性已无业务意义——此类情况需立即上报不自行删除）
- 删除整个 `test_evolution_regression.py` 文件
- 新增任何测试用例
- 修改测试断言的业务期望值
- 修改测试夹具、mock、setup
- 修改任何其它测试文件（除 §3.6.3 列出的 5 处 import 外）

**`test_evolution_regression.py` 适配示例**（仅说明边界，非指令）：
- 第 36-63 行的 `VALID_TRANSITIONS` 断言：仅需修改文件顶部 import（`VALID_TRANSITIONS` 来源从 `evolution_engine` 改为 `evolution_service`），断言不变
- 第 116-150 行 `TestEvolutionResult`：仅需修改 import，`EvolutionResult` 引用不变
- 第 191-310 行 `TestTopicEvolutionResult`：仅需修改 import
- 任何引用 `EvolutionEngine` 或 `TopicEvolutionService` 的用例（若有）：上报 @pm-hy3 决定，不自行适配

### 6.3 Worker 不允许做（沿用 v1 §6.2，更新 §6.2 测试项已独立）

- 修改 `EvolutionService` 的方法体、签名、docstring
- 修改 `VALID_TRANSITIONS` 值
- 修改 `engine/evidence_evolution_engine.py`（含其内同名 `EvolutionResult`）
- 修改任何非 §3.6 列出的 production 文件
- 修改 `service/exceptions.py`（属 Step 3 范围）
- `git commit`、`git push`、任何远程操作
- 修复任何 lint / typo / 顺手优化
- 修改 `docs/CODEX_CONTEXT.md`
- 修改 `phase21-final-freeze-audit.md` 或 `phase21-7-historical-memory-evolution.md`

### 6.4 异常处理（沿用 v1）

| 情况 | 动作 |
|---|---|
| 发现本任务未覆盖的 `backend.evolution` 引用 | 立即停止，上报 @pm-hy3 |
| 测试失败 | 立即停止，**不要** `git checkout` 或自行修复，上报 @pm-hy3 |
| 发现 §3.6.3 未列出的测试需要适配 | 立即停止，上报 @pm-hy3 |
| `git diff --stat` 显示范围外变更 | 立即 `git checkout` 恢复范围外变更，上报 @pm-hy3 |
| `test_evolution_regression.py` 内用例验证 `EvolutionEngine` 类自身存在性（非业务行为）| 立即停止，上报 @pm-hy3 决定是否删除该用例 |
| 任何超出本任务定义的边界 | 立即停止，上报 @pm-hy3 |

---

## 7. 文档层记录（沿用 v1 §4）

### 7.1 现有文档体系调查结论

| 用途 | 现有位置 | 复用策略 |
|---|---|---|
| 阶段实施报告 | `docs/phase21-7-historical-memory-evolution.md`、`docs/05_Implementation/D5_Implementation_Report.md` | **不修改** |
| 架构冻结清单 | `docs/05_Implementation/ARCHITECTURE-FREEZE-CHECKLIST.md` | **不修改** |
| ADR 范式 | `docs/05_Implementation/ADR-EvidenceEvolution-Split.md` | **新增 ADR**：`docs/05_Implementation/ADR-D5-2-Evolution-Service-Migration.md` |
| CODEX 上下文 | `docs/CODEX_CONTEXT.md` | **不修改** |

### 7.2 ADR 必须包含

1. 背景：D5-1 调查结论（指 `.hermes/plans/d5-1-investigation-report.md`）
2. 决策：方案 A — `EvolutionService` 迁 `service/`；`EvolutionResult` / `TopicEvolutionResult` 迁 `shared/domain/`；`EvolutionEngine` / `TopicEvolutionService` 删除
3. 理由：
   - `EvolutionService` 继承 `BaseService`，符合 Service 契约
   - `EvolutionEngine` 违反 Engine 契约，是死代码
   - `TopicEvolutionService` 定义在 `EvolutionEngine` 内，Engine 删除后随之消失
   - `VALID_TRANSITIONS` / `TopicEvolutionResult` 跨文件重复，删除 Engine 后自然消解
   - 测试适配范围仅限 import，不改变业务语义
4. **D5-1 vs §5.1 预检差异说明**：D5-1 报告"测试无依赖"已修正为"测试有引用，需最小适配"
5. Phase 21.7 受控结构性解冻说明（性质、允许/禁止清单沿用本任务 §4）
6. 变更范围：2 处 production import + 5 处测试 import + 2 个文件移动 + 1 个文件删除 + 测试最小适配
7. 验证结果：测试输出、`git diff --stat`、全仓搜索结果
8. Frozen 状态恢复：D5-2 完成后 Phase 21.7 仍视为 FROZEN
9. 回滚方案：`git checkout` + 重启 gateway

### 7.3 execution report 必须包含

1. Worker 任务派发与回报时间线
2. Worker 实际产出（git diff、测试输出、搜索结果）
3. PM 验证结论

---

## 8. 执行顺序（严格，v2 闸门更新）

```
1. @user 授权 D5-2 v2（本任务定义）
   ↓
2. @pm-hy3 派发 @agnes-worker 完整任务定义
   ↓
3. @agnes-worker 执行 §5.1 预检（v1 已完成，可复用结果，但需重新确认无新增引用）
   ↓
4. @pm-hy3 确认预检无异常
   ↓
5. @agnes-worker 执行 §6.1 变更
   ↓
6. @agnes-worker 执行 §5.2 / §5.3 验证
   ↓
7. @agnes-worker @pm-hy3 回报完整交付
   ↓
8. @pm-hy3 PM 层验证 → @user 报告 → 等待下一步授权
```

**绝不**：PM 不得自行进入 Step 3；Worker 不得 commit/push；Worker 不得修改范围外文件；任何适配边界模糊处立即停止上报。

---

## 9. 待 @user 再次裁决

1. **是否批准 D5-2 任务定义 v2？**
2. **批准后是否立即派 @agnes-worker 执行？**
3. **`test_evolution_regression.py` 适配规则（§6.2）是否同意？**
4. **ADR 路径**：`docs/05_Implementation/ADR-D5-2-Evolution-Service-Migration.md` 是否同意？
5. **execution report 路径**：`docs/d5-2-execution-report.md` 是否同意？
6. **任何边界需进一步调整？**

收到你最终授权后，我才会派 @agnes-worker。
