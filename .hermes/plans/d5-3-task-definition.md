# D5-3 MemoryHubError 迁移 — 任务定义 v2

**状态**: TASK DEFINITION v2（基于 @user 裁决修订；Step 1 已授权；Step 2/3/4 仍需单独授权）
**生成时间**: 2026-09-05
**生成者**: @pm-hy3
**前置依赖**: D5-2 LOCKED + PUSHED @ `bc65e96`
**调查来源**: `.hermes/plans/d5-3-investigation-report.md`（arch-laguna 调查报告）

---

## 0. v1 → v2 修订要点

| # | 项 | v1 | v2 | 裁决依据 |
|---|---|---|---|---|
| 1 | Step 3 测试 | 新增 `tests/shared/test_exceptions_migration.py` 验证双 import 同义 | **Step 3 改为可选 hardening**（非 LOCK 必需） | @user 裁决 1：双 import 同义测试隐式要求 `service.exceptions` 保留 re-export，是新增兼容性 API，与"零测试业务修改"约束不符 |
| 2 | 架构依据 | "与 evolution_result.py 同构" + 4 条优缺点 | §2 完整 Layered Architecture 论证 + 明确层级关系图 | @user 裁决 2：必须结合 Layered Architecture / shared/domain 职责 / 跨包角色论证 |
| 3 | Frozen 判断 | "不需要受控解冻" | **明确记录 NO CONTROLLED DEFROST REQUIRED** + 4 条证据 | @user 裁决 3：必须把验证依据写清楚 |
| 4 | Step 2/3 关系 | Step 3 "可选"但又写"LOCK 必需条件" | 明确：Step 2 = LOCK 必需；Step 3 = optional hardening（独立授权）| @user 裁决 4：不能同时写"optional"和"LOCK prerequisite" |
| 5 | Worker 选派 | Step 1-4 均 agnes-worker | 保持一致 | 无变更 |
| 6 | `DomainError` 处置 | 子方案 (i) 仅迁 marker | 保持 | 无变更 |

---

## 1. 背景与事实基础

### 1.1 MemoryHubError 当前定义

- **文件**: `backend/src/backend/service/exceptions.py:32-38`
- **类**: `MemoryHubError(Exception)` —— 纯 marker 基类，无 `__init__`、无方法
- **架构角色**: 跨包共享异常根；`Entry Layer translates MemoryHubError subclasses into protocol-specific error responses`

### 1.2 service/exceptions.py 共 15 个类（347 行）

| 行号 | 类 | 继承 | 处置 |
|---|---|---|---|
| 32 | `MemoryHubError` | `Exception` | **迁移至 `shared/domain/exceptions.py`** |
| 41 | `DomainError` | `MemoryHubError` | **不动**（保留在 service/exceptions.py） |
| 85–347 | 13 个领域异常 | `DomainError` 或其子类 | **不动** |

### 1.3 全仓引用（5 处 = 2 个生产文件）

| 文件 | 行号 | 使用方式 | 处置 |
|---|---|---|---|
| `service/exceptions.py` | 32 | 类定义 | 删除（迁走）|
| `service/exceptions.py` | 36 | docstring | 保留（仍准确）|
| `service/exceptions.py` | 41 | 继承 | 改为 `from backend.shared.domain.exceptions import MemoryHubError` |
| `ingest/exceptions.py` | 8 | import | 改路径 |
| `ingest/exceptions.py` | 11 | 继承 | 不动（类继承关系不变）|

**测试代码**: 0 处直接引用 `MemoryHubError`。

---

## 2. 目标位置：架构依据（v2 补强）

### 2.1 最终决策

**`MemoryHubError` 目标位置：`backend/src/backend/shared/domain/exceptions.py`**

### 2.2 为什么属于 `shared/domain/` 而非 `shared/exceptions.py`？

#### 论据 1：Layered Architecture 职责切分

当前仓库的 `shared/` 实际结构已确立明确的层级职责：

```
backend/src/backend/shared/
├── domain/                            # 跨业务包共享的领域类型（值对象/异常根）
├── infrastructure/                    # 技术关注点（config/db/di/logging/uuid 工具）
├── protocols/                         # 协议抽象（空目录，无先例）
└── providers/                         # 提供者实现（空目录，无先例）
```

`shared/domain/` 的实际承载内容：
- `evolution_result.py`（D5-2 新迁入）—— 跨业务包共享的领域结果类型
- `memory_models.py` —— 领域模型
- `proposal_model.py` —— 领域模型
- `__init__.py` 注释: `"D1 only: Base classes"` —— **明确为基类预留空间**

`shared/infrastructure/` 的实际承载内容：
- `config/`、`database/`、`di/`、`logging/`、`uuid.py` —— 全部为技术关注点

`shared/` 顶层（不含子目录）目前**无任何文件**，无承载"领域异常根"的先例。

#### 论据 2：`MemoryHubError` 的语义角色

- **跨 package 共享的基类** —— 被 `service/`（DomainError）和 `ingest/`（ImportFrameworkError）共同继承
- **领域异常根** —— D3.7_Error_Handling_DTO_Models.md 中描述为 "domain error" 的根节点
- **无技术关注点依赖** —— 不依赖 config/db/di/logging/uuid 等任何 infrastructure 内容
- **承载语义为"领域契约"** —— Entry Layer 按此契约翻译错误响应

因此 `MemoryHubError` 是**领域契约**，应位于 `shared/domain/`（与 `evolution_result.py` 完全同质：都是"被多个业务包共享的非业务类型"）。

#### 论据 3：与现有架构一致性

D5-2 已确立范式："跨业务包共享的领域类型" → `shared/domain/`

```
D5-2 先例:  backend.evolution.evolution_result
            → backend.shared.domain.evolution_result   (✅ LOCKED + PUSHED @ bc65e96)

D5-3 类比:  backend.service.exceptions::MemoryHubError
            → backend.shared.domain.exceptions::MemoryHubError
```

两者都是"被多个业务包引用、无业务语义、需跨层共享"——结构同构，归位一致。

### 2.3 明确层级关系（v2 必备）

D5-3 完成后，目标层级关系为：

**Service 侧**：
```
backend.shared.domain.MemoryHubError
        ↑
backend.service.exceptions.DomainError(MemoryHubError)
        ↑
backend.service.exceptions.{ValidationError, NotFoundError, DuplicateError,
                             DomainIntegrityError, TransactionError,
                             ServiceUnavailableError, ReflectionError,
                             ImportError} (DomainError 子类)
        ↑
backend.service.exceptions.{TaskNotFoundError(NotFoundError),
                             TaskAlreadyRunningError(DomainIntegrityError),
                             TaskCancellationError(DomainError)}
```

**Ingest 侧**：
```
backend.shared.domain.MemoryHubError
        ↑
backend.ingest.exceptions.ImportFrameworkError(MemoryHubError)
```

**结论**：`MemoryHubError` 是"被 service 和 ingest 同时继承的领域契约根"。归位于 `shared/domain/` 是有意设计，不是偶然的文件搬迁。

### 2.4 替代位置否决记录

| 候选 | 否决理由 |
|---|---|
| `shared/exceptions.py` | `shared/` 顶层目前无任何文件；与 `shared/domain/` 子层结构不符；无先例 |
| `shared/infrastructure/exceptions.py` | `infrastructure/` 是技术关注点；D3.7 "Infrastructure Error never crosses Service boundary"；与 MemoryHubError 跨包共享角色相反 |
| `service/exceptions.py` 不动 | 与 D5 系列 plan 意图冲突；MemoryHubError 是跨包共享类型，应位于跨层位置 |

---

## 3. Frozen 状态判断：**NO CONTROLLED DEFROST REQUIRED**（v2 明确）

### 3.1 结论

**`MemoryHubError` 迁移属于"跨层基类归位"，不触及任何业务逻辑、状态机或边界。** **NO CONTROLLED DEFROST REQUIRED.**

### 3.2 验证依据

#### 证据 1：Phase 21.* Frozen 文档中无 `MemoryHubError` 引用

`grep -rn "MemoryHubError" docs/phase21-*` —— 0 命中

Phase 21.* 冻结范围仅覆盖 `evolution/` 包内的业务实现（`EvolutionEngine`、`EvolutionService`、`VALID_TRANSITIONS` 等），不覆盖位于 `service/exceptions.py:32` 的纯 marker 基类。

#### 证据 2：无冻结架构事实依赖

Phase 21.* 冻结的"架构事实"包括：
- evolution 调用链（EvidencePipelineService → EvolutionService → EvolutionResult）
- Topic status transitions（VALID_TRANSITIONS）
- Historical Memory immutability
- L2/L3 abstraction formation

`MemoryHubError` 不参与以上任何事实——它是"在错误处理时翻译这些调用链结果的契约"，但其本身不参与业务逻辑。

#### 证据 3：本次仅改变"exception base 的归属"

变更前：`MemoryHubError` 定义在 `backend/service/exceptions.py`
变更后：`MemoryHubError` 定义在 `backend/shared/domain/exceptions.py`

**未改变**：
- `MemoryHubError` 的语义（marker 基类）
- `DomainError` 的实现与所有 13 个领域异常的行为
- 任何 `raise` / `except` 语句
- Entry Layer 的错误响应翻译逻辑（依赖 `DomainError` 子类，不依赖 `MemoryHubError` 本身）

#### 证据 4：D3.7 原则对齐

D3.7_Error_Handling_DTO_Models.md 明确：
> "Exception types are version-controlled architecture contracts"

迁移属于"架构契约的物理位置调整"，**不**属于"架构契约本身变更"。符合 D3.7 原则，无需解冻声明。

### 3.3 与 D5-2 受控解冻的对比

| 项 | D5-2 | D5-3 |
|---|---|---|
| 解冻范围 | evolution/ 包（Phase 21.7 冻结） | 无（不涉及任何 frozen 阶段）|
| 性质 | structural refactoring only | 跨层基类归位 |
| 业务语义变更 | 零（530→530 行） | 零（删除 6 行 + 新增 6 行，方法体不变）|
| 解冻声明 | 必需 | **不需要** |

---

## 4. 目标

将 `MemoryHubError` 从 `service/exceptions.py` 迁至 `shared/domain/exceptions.py`，保持所有业务语义、所有子类继承关系、所有调用方行为不变。

**非目标**：
- 不迁移 `DomainError` 或其 13 个子类
- 不修改任何业务逻辑、异常行为、错误响应翻译逻辑
- 不修改 alembic 迁移、DI 容器、其它 service 文件
- 不引入新的异常类型或层级
- **不在 `service/exceptions.py` 保留 `MemoryHubError` re-export**（避免隐式新增兼容性 API）

---

## 5. 执行步骤（单线程）

### Step 1 — D5-3-1：预检（只读）— **已授权**

**Worker**: @agnes-worker
**前置**: 当前可启动
**授权**: ✅ @user 已授权（2026-09-05）

**任务**（只读，详见 dispatch 内容）：
1. `cd F:\LI_YONGSHUN\AI\personal-memory-hub`
2. `git status` — 工作区干净（应仅含 D5-2 既有 untracked 文件）
3. `git log -1 --oneline` — HEAD 应为 `bc65e96`
4. `grep -rn "class MemoryHubError" backend/ --include="*.py"` — 应仅 1 处
5. `grep -rn "from backend.service.exceptions import MemoryHubError" backend/ --include="*.py"` — 应仅 1 处
6. `grep -rn "from backend.shared.domain.exceptions" backend/ --include="*.py"` — 应 0 命中
7. `ls backend/src/backend/shared/domain/exceptions.py 2>&1` — 应不存在
8. `ls backend/tests/shared/ 2>&1` — 检查目录是否存在
9. `grep -rn "MemoryHubError" backend/tests/ --include="*.py"` — 应 0 命中

**异常检查**（任一立即停止上报）：HEAD 不是 `bc65e96` / 工作区意外变更 / grep 不符 / `shared/domain/exceptions.py` 已存在

**输出**: 与调查对比，明确 (A)/(B)/(C)

---

### Step 2 — D5-3-2：实施迁移（LOCK 必需）— **待授权**

**Worker**: @agnes-worker
**前置**: Step 1 PASS
**授权**: 待 @user 单独授权（**LOCK 必需条件**）

**任务**：

1. **新建** `backend/src/backend/shared/domain/exceptions.py`：

```python
"""Cross-package shared exception base classes.

MemoryHubError is the architecture root for all MemoryHub exceptions.
Located in shared/domain/ because:
- It is a cross-package shared type (referenced by service/ and ingest/)
- It has no technical infrastructure dependencies (config/db/di/logging)
- It is a domain-level contract consumed by Entry Layer for error translation

DomainError and its subclasses remain in service/exceptions.py to
preserve the service-level implementation contract and avoid breaking
existing imports.
"""
from __future__ import annotations


class MemoryHubError(Exception):
    """Base exception for all MemoryHub errors.

    All service-level exceptions inherit from this class.
    Entry Layer translates MemoryHubError subclasses into protocol-specific
    error responses.
    """
```

2. **修改** `backend/src/backend/service/exceptions.py`：
   - 删除 L32–L38 原 `MemoryHubError` 类定义（含 docstring）
   - 在 import 块（顶部）新增：
     ```python
     from backend.shared.domain.exceptions import MemoryHubError
     ```
   - **保留**: 所有其它 14 个类、`DomainError`、所有现有 import、所有 docstring

3. **修改** `backend/src/backend/ingest/exceptions.py:8`：
   - `from backend.service.exceptions import MemoryHubError` → `from backend.shared.domain.exceptions import MemoryHubError`
   - **保留**: `ImportFrameworkError(MemoryHubError)` 继承不变

4. **运行** 验证（沿用 D5-2 测试基线）：
   ```bash
   cd backend
   python -c "from backend.shared.domain.exceptions import MemoryHubError; from backend.service.exceptions import DomainError; assert issubclass(DomainError, MemoryHubError)"
   python -m pytest tests/ -x -q
   cd ..
   git diff --stat
   git diff backend/alembic/versions/   # 应为空
   git diff backend/src/backend/shared/infrastructure/di/container.py   # 应为空
   ```

**交付**：
- §6 验证清单完整 PASS
- 测试运行结果（703 passed / 8 skipped / 0 failed / 0 errors）
- `git diff --stat` 输出
- 明确"完成 / 阻塞"结论

**约束**:
- 不 commit/push
- 不修改任何测试
- 不修改 alembic / DI / 其它文件
- 不在 `service/exceptions.py` 保留 `MemoryHubError` re-export
- 测试失败立即停止上报，不自行修复

---

### Step 3 — D5-3-3：可选 hardening（**非 LOCK 必需**）— **待授权**

**Worker**: @agnes-worker
**前置**: Step 2 PASS
**授权**: 待 @user 单独授权（**独立授权**；**非 LOCK 必需**）

**说明（v2 明确）**:
- Step 3 是"可选加固"，**不**是 Step 2 / LOCK 的前置条件
- Step 3 与 Step 2 是**独立授权**关系
- 即使 Step 3 未授权/未执行，D5-3 仍可在 Step 2 完成 + LOCK 验证后视为完成

**如 @user 批准 Step 3，可选执行**：

**方案 A（推荐删除）**：**不执行 Step 3**，保持测试零修改

**方案 B（执行 Step 3）**：仅当确有必要保留 `service.exceptions.MemoryHubError` 作为 compatibility re-export 时执行——
- 修改 `service/exceptions.py` 显式 re-export：`from backend.shared.domain.exceptions import MemoryHubError  # noqa: F401  # compatibility re-export for external integrations`
- 新增 `tests/shared/test_exceptions_migration.py` 验证双 import 同义
- 在 ADR 中明确记录"compatibility re-export 是有意设计而非意外保留"
- 必须由 @user 在 Step 3 授权时明确说明兼容性依据

**当前 v2 默认**: **方案 A**（不执行 Step 3）

---

### Step 4 — D5-3-4：文档产出（LOCK 必需）— **待授权**

**Worker**: @agnes-worker
**前置**: Step 2 PASS（Step 3 与 Step 4 独立）
**授权**: 待 @user 单独授权（**LOCK 必需条件**）

**任务**：

1. **新建** `docs/05_Implementation/ADR-D5-3-MemoryHubError-Migration.md`，必含章节：
   - **Status**: Accepted
   - **Context**: D5-2 已迁 evolution 类型 + MemoryHubError 是 ingest/service 共享根
   - **Decision**: 4 条（迁 marker / service 保留 / DomainError 不动 / ingest 改 import）
   - **Architecture Rationale**: 引用 v2 §2 完整论证 + 层级关系图
   - **Frozen Status**: **NO CONTROLLED DEFROST REQUIRED** + 引用 v2 §3.2 四条证据
   - **Consequences**: 与 D5-2 同构 / 跨包共享类型收口 / 测试零修改
   - **References**: D5-1、D5-2 ADR、d5-series-restructure-plan、d5-3-task-definition v2

2. **追加** `docs/05_Implementation/ADR-D5-2-Evolution-Service-Migration.md:46` 一行：
   - `D5-3 (MemoryHubError migration) — ✅ COMPLETED (commit XXX)` （XXX 在 Step 5 commit 后填）

3. **新建** `.hermes/plans/d5-3-execution-report.md`（PM 工作记录，非架构文档）

---

### Step 5 — D5-3-5：commit / push — **不在本计划默认范围**

待单独授权。沿用 D5-2 闸门：单 commit、精确 add、push 后核对 `origin/main == HEAD`。

---

## 6. 验证清单

### 6.1 Step 1 预检 PASS 条件

- [ ] HEAD = `bc65e96`
- [ ] 工作区干净（仅 D5-2 既有 untracked）
- [ ] `grep "class MemoryHubError"` 仅 1 处（service/exceptions.py:32）
- [ ] `grep "from backend.service.exceptions import MemoryHubError"` 仅 1 处（ingest/exceptions.py:8）
- [ ] `grep "from backend.shared.domain.exceptions"` 0 命中
- [ ] `shared/domain/exceptions.py` 不存在
- [ ] 测试代码 0 处直接引用 `MemoryHubError`

### 6.2 Step 2 实施 + LOCK PASS 条件

- [ ] `grep "class MemoryHubError" backend/src/` → 仅 `shared/domain/exceptions.py`
- [ ] `grep "from backend.service.exceptions import MemoryHubError" backend/` → **0 命中**（确认无 re-export）
- [ ] `grep "from backend.shared.domain.exceptions import MemoryHubError" backend/` → 2 命中（service + ingest）
- [ ] `python -c "...issubclass(DomainError, MemoryHubError)"` → 无错误
- [ ] `cd backend && python -m pytest tests/ -x -q` → 全绿（703 passed / 8 skipped / 0 failed / 0 errors）
- [ ] `git diff --stat` 范围仅含预期文件
- [ ] 无 alembic 迁移变更
- [ ] 无 DI 容器变更
- [ ] 无测试断言变更

### 6.3 Step 4 文档 LOCK PASS 条件

- [ ] ADR `ADR-D5-3-MemoryHubError-Migration.md` 已创建，含 §Architecture Rationale + §Frozen Status 章节
- [ ] D5-2 ADR 第 46 行已追加 D5-3 COMPLETED 行（commit hash 占位可暂留 XXX）
- [ ] execution report 已创建

---

## 7. 纪律与边界

### 7.1 PM 严格遵守

- 单线程派发（一次一个 Worker）
- Step 1 通过才派 Step 2
- Step 2/3/4 需分别单独授权
- 不进入 Step 5 commit/push（另行授权）
- 超时可主动确认 Worker 状态，不可用时上报 @user

### 7.2 Worker 严格遵守

- 仅响应 @pm-hy3 指派
- 完成或阻塞时 @pm-hy3，不 @user
- 不修改本计划范围外的文件
- 不 commit/push

### 7.3 不变边界（v1 → v2 保持）

- 不迁移 `DomainError`
- 不修改其它 13 个 exception
- 不修改异常行为
- 不改 DI
- 不改 Alembic
- 不改业务逻辑
- 不 commit/push
- 不进入 D5-3 实施（Step 2/3/4 待单独授权）

---

## 8. 风险与回滚

| 风险 | 回滚策略 |
|---|---|
| 测试失败 | 不提交变更，`git checkout` 恢复，上报 @user |
| 循环导入 | 立即停止（shared/domain/exceptions.py 不应依赖任何上层）|
| Entry 层翻译逻辑破坏 | 立即停止（DomainError 子类路径不应改变）|
| Worker 不可用 | PM 上报 @user 等待整备 |
| 业务行为变化 | 立即停止（违反"零业务变更"约束）|

---

## 9. 待 @user 裁决（v2 修订后）

1. **是否批准 D5-3 任务定义 v2？**
2. **Step 1 预检已授权（已派发）** —— 是否同意预检执行？
3. **Step 2 实施**：待 Step 1 PASS 后单独授权 —— 是否预先批准框架？
4. **Step 3 hardening**：v2 默认方案 A（不执行），是否同意？
5. **Step 4 文档**：待 Step 2 PASS 后单独授权 —— 是否预先批准框架？
6. **`DomainError` 处置**：仅迁 marker（子方案 i）—— 是否同意？
7. **目标位置**：`shared/domain/exceptions.py` —— 是否同意？
8. **Frozen**：NO CONTROLLED DEFROST REQUIRED —— 是否同意？

**Step 1 预检回报后再决定 Step 2/3/4 授权。**
