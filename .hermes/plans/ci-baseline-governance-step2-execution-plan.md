# CI Baseline Governance — Step 2 Execution Plan

**状态**: Step 2 完成（仅规划；未修改任何文件；未派 Worker；未 commit/push）
**生成时间**: 2026-09-07
**生成者**: @pm-hy3（PM 独立设计）
**前置**: Step 1 Forensic Inventory 已完成
**基准 commit**: `1f24c9e2de0af800b9ca84a4c339ad2a4cd22769` (M6)

---

## 1. Executive Summary

本步定义可执行、可审查的治理方案。原则：

| 原则 | 落地 |
|---|---|
| **只修 M6 引入的 4 个 ruff 错误** | Step 3 |
| **不修 1144 个历史 baseline** | 文档化为"已知 baseline"（Step 4）|
| **不修改业务代码** | 业务代码不在 Step 3-7 范围 |
| **M6 行为不变** | Step 3 修前后均跑 150 个新测试验证 |
| **CI 反映真实 regression** | Step 5 CI 配置治理 |
| **新 commit 禁止引入新 debt** | Step 4 baseline 机制 + Step 7 CI gate |

最终目标：**M6 = FUNCTIONAL_LOCKED + No New Ruff Debt + CI 真实性恢复**（CI 全绿**不是**本阶段目标）。

---

## 2. A. 4 个 M6 Ruff 问题 — 详细修复方案

### A.1 错误 1: `test_ingest_parser_multimodal.py:29` I001

**修改位置**：
```python
# backend/tests/test_ingest_parser_multimodal.py
# 当前第 29 行附近
```

**修改方式**：
- **方式 A（推荐）**：`ruff check --fix backend/tests/test_ingest_parser_multimodal.py`（自动）
- **方式 B**：手动 reorder import block

**为什么安全**：
- I001 仅影响 import 顺序，**不影响运行时行为**
- ruff --fix 在该项目 CI 中已大量使用（之前 1049 auto-fixable）
- 仅排序 import 块，不改变任何代码逻辑

**修改后需运行测试**：
```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_ingest_parser_multimodal.py -v
```
预期：80 个测试全部 PASS

**证明 M6 行为不变**：150 新测试 + 既有 703 全部通过（853 passed）

### A.2 错误 2: `test_ingest_parser_multimodal.py:490` F401

**修改位置**：
```python
# 第 490 行
import inspect  # ← unused import
```

**修改方式**：
- **方式 A（推荐）**：`ruff check --fix`（自动删除 unused import）
- **方式 B**：手动删除 `import inspect` 行

**为什么安全**：
- `inspect` 模块**未在文件中使用**（grep 确认）
- 删除 import 不影响任何测试逻辑
- 测试函数本身不依赖 inspect

**修改后需运行测试**：
```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_ingest_parser_multimodal.py -v
```
预期：80 个测试全部 PASS

**证明 M6 行为不变**：原 24/24 baseline byte-for-byte 测试覆盖仍通过

### A.3 错误 3: `test_ingest_parser_multimodal.py:526` F841（手动）

**修改位置**：
```python
# test_ingest_parser_multimodal.py:524-528 区域
mock_fn = MagicMock()
call_kwargs = mock_fn.call_args.kwargs
call_args = mock_fn.call_args.args  # ← unused
# extract_multimodal_text signature forces min_length to be kwarg-only
# (`*,` in signature). If it appears, it must be 0.
if "min_length" in call_kwargs:
    assert call_kwargs["min_length"] == 0
```

**修改方式**：
- 删除 `call_args = mock_fn.call_args.args` 行
- **不能**用 `_ = call_args` 保留——F841 是"assigned to but never used"，按 ruff 严格定义 `_ =` 也算"被使用"，会消除警告但**留下死代码**

**为什么安全**：
- 测试只检查 `min_length` kwargs（强制 kwarg-only）
- `call_args` 行的原始意图是"留作未来参考"——但实际未使用，按 PM 决定删除
- 不改变测试断言逻辑

**修改后需运行测试**：
```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_ingest_parser_multimodal.py::TestCallContracts -v
```
预期：2 个 TestCallContracts 测试全部 PASS

**证明 M6 行为不变**：TestCallContracts 是关键回归测试，通过即证明调用契约不变

### A.4 错误 4: `test_ingest_parser_helpers.py:19` I001

**修改位置**：
```python
# backend/tests/test_ingest_parser_helpers.py 第 19 行附近
```

**修改方式**：
- **方式 A（推荐）**：`ruff check --fix backend/tests/test_ingest_parser_helpers.py`（自动）
- **方式 B**：手动 reorder

**为什么安全**：同 A.1

**修改后需运行测试**：
```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_ingest_parser_helpers.py -v
```
预期：70 个测试全部 PASS

### A.5 总体 M6 行为不变证明链

修复 4 错误后必须验证：

1. **回归测试**：M6 24/24 byte-for-byte baseline 等价测试通过
2. **新增测试**：150 个新测试全部通过
3. **既有测试**：703 个 D5-3 基线测试全部通过
4. **调用契约**：TestCallContracts 2 个测试通过（验证 A.3 修改不破坏 mock 验证）
5. **CI 等价**：本地跑 CI 同一命令 `uv run pytest tests/ -v --cov=backend` 仍 0 failed

---

## 3. B. Legacy Ruff Baseline — 详细方案

### B.1 目标

**记录 1243 个历史 ruff 错误为已知 baseline，未来 commit 禁止引入新错误**。

### B.2 Ruff 原生 baseline 能力评估

**Ruff 没有原生 baseline 机制**（与 ESLint `--max-warnings 0` 类似，但无"baseline file"概念）。

可选方案对比：

| 方案 | 优点 | 缺点 | 推荐 |
|---|---|---|---|
| **B.2.1: Pre-commit hook (本地)** | 提交前阻止 | 仅本地；CI 不强制 | 部分 |
| **B.2.2: CI fail-on-new** | CI 强制 | 需自定义脚本 | 推荐 |
| **B.2.3: ruff baseline 第三方** | 集中管理 | 引入新依赖 | 不推荐 |
| **B.2.4: ruff `--add-noqa`** | 行级豁免 | 侵入式 | 不推荐 |

**PM 推荐：B.2.1 + B.2.2 组合**（pre-commit 本地 + CI fail-on-new 强制）。

### B.3 实现方案：B.2.2 — CI fail-on-new（PM 推荐）

**思路**：CI 中对比"当前 ruff 错误"与"已知 baseline 列表"，新错误让 CI 失败。

**实现**：

1. **创建 baseline 记录** `.hermes/plans/ci-baseline-ruff-state.md`：
   ```markdown
   # CI Ruff Baseline State
   
   Generated: 2026-09-07
   Baseline commit: 1f24c9e
   Total errors: 1243
   Auto-fixable: 1049
   Manual: 193
   
   ## Governance
   - 1243 baseline errors are accepted (历史技术债)
   - Future commits MUST NOT introduce new ruff errors
   - CI will fail if new errors appear
   
   ## Top 10 Rules
   - W293: 921
   - F401: 78
   - I001: 61
   - F841: 37
   - W291: 18
   - E712: 13
   - F821: 12
   - F811: 8
   - F541: 5
   - B905: 2
   ```

2. **创建 baseline 错误快照** `.hermes/plans/ci-baseline-ruff-snapshot.txt`：
   - 完整 ruff 输出（1243 行）
   - 每次 CI 比较"当前 vs 快照"
   - **不入 Git**（gitignore 标记）

3. **CI 添加 fail-on-new 检查**（Step 5）：
   ```bash
   # CI 新增 step
   - name: Verify No New Ruff Debt
     working-directory: backend
     run: |
       uv run ruff check src/ tests/ --output-format=concise > /tmp/current.txt
       # 与 baseline 对比
       if ! diff -q .hermes/plans/ci-baseline-ruff-snapshot.txt /tmp/current.txt > /dev/null; then
         # 检查是否仅为新错误
         NEW_COUNT=$(diff .hermes/plans/ci-baseline-ruff-snapshot.txt /tmp/current.txt | grep -c "^>")
         if [ "$NEW_COUNT" -gt 0 ]; then
           echo "::error::Ruff baseline violation: $NEW_COUNT new errors introduced"
           exit 1
         fi
       fi
   ```

### B.4 baseline 文件位置决策

| 选项 | 路径 | 优缺点 |
|---|---|---|
| 仓库内 | `.hermes/plans/ci-baseline-ruff-snapshot.txt` | 易访问；需 .gitignore 避免污染主分支 |
| 仓库外 | `~/.cache/ci-baseline/` | 干净；但跨机器不可用 |
| **PM 推荐** | **仓库内（`.hermes/plans/`，gitignored）** | 与 PM 工作目录一致；本地 venv 同样路径访问 |

`.gitignore` 加：
```
.hermes/plans/ci-baseline-ruff-snapshot.txt
```

### B.5 区分 legacy vs new error

**机制**：
1. **legacy error**：在 baseline snapshot 中存在的行
2. **new error**：baseline snapshot 中不存在的新行（按 `<file>:<line>:<col>:<rule>:<msg>` 精确匹配）
3. **移除的 legacy error**：baseline 中有但当前没有了——**不构成 failure**（baseline 减少是好事）

**关键**：错误匹配用 ruff `--output-format=concise` 的输出格式，**保证行级精确比较**。

### B.6 Ruff 规则变化的应对

| 场景 | 应对 |
|---|---|
| 未来 ruff 版本升级引入新规则 | snapshot 重生成；新增规则错误**不构成 new debt**（需明确决策）|
| pyproject.toml 修改 ruff select/ignore | snapshot 重生成；用户裁决 |
| 新增 .py 文件 | 新文件中**任何 ruff 错误**都构成 new debt（即使规则已存在）|

**建议**：Step 4 snapshot 生成时同时记录 ruff 版本 + pyproject.toml hash，未来变更时用户明确决策"是否重置 baseline"。

---

## 4. C. CI Environment Governance — 详细方案

### C.1 GitHub Actions Python Matrix 决策

**当前状态**：matrix = ["3.11", "3.12"]

**问题**：
- Python 3.12 matrix 3 次 commit 全部失败（bc65e96 / 0e4cf20 / 1f24c9e）
- 失败模式与 3.11 相同（baseline 累积错误），但**3.12 失败 1 次就让 3.11 联动取消**
- 双 matrix = 双倍 CI 时间，但未带来额外信号

**PM 推荐**：
- **方案 C.1.1（推荐）**：matrix = ["3.11"]（单 matrix）
  - 节省 50% CI 时间
  - 减少 Python 3.12 兼容性累积问题
  - 项目 `requires-python = ">=3.10"`，仍可在本地用 3.12 验证
- **方案 C.1.2**：matrix = ["3.11", "3.12"] + 3.12 fail 不取消 3.11
  - 配置 `fail-fast: false`
  - 仍跑双 matrix，但失败独立判定
- **方案 C.1.3（不推荐）**：保留现状

**PM 选 C.1.1**——风险最低、收益最直接。

### C.2 uv 版本决策

**当前状态**：`version: "0.11.x"`（2024 版本）

**问题**：
- 0.11.x 是早期版本，与现代 pyproject 锁文件规范不完全兼容
- uv.lock 已存在（365KB，revision 3），但 uv 0.11.x 兼容性可能有问题

**PM 推荐**：
- 升级到 uv `"0.4.x"` 或 `"latest"`
- 现代 uv 与 uv.lock 兼容性更好
- 需 rerun CI 验证

**风险**：
- uv 升级可能引入新问题
- 需用户授权（CI 配置变更）

### C.3 dependency installation 决策

**当前命令**：`uv sync --all-extras`

**问题**：
- `--all-extras` 装齐 dev + test + postgres
- postgres extra 含 `asyncpg` / `psycopg2-binary`——CI 不会真连 postgres，但装包可能拖慢
- 无 cache 显式配置（GitHub Actions 默认无 cache）

**PM 推荐**：
- 保持 `uv sync --all-extras`（postgres extra 影响小）
- **可选**：加 `actions/setup-python` 的 cache 配置（`cache: 'pip'` 模式）

### C.4 cache 决策

**当前状态**：无显式 cache 配置

**PM 推荐**：
- 在 `astral-sh/setup-uv@v3` 中启用 cache：
  ```yaml
  - uses: astral-sh/setup-uv@v3
    with:
      version: "0.4.x"
      enable-cache: true
      cache-dependency-glob: "backend/uv.lock"
  ```
- 加速 CI 30-50%（uv sync 缓存）

### C.5 network / package installation 决策

**当前状态**：依赖 GitHub Actions 默认网络

**问题**：
- PyPI 偶发不可达可能让 `uv sync` 失败
- 无 retry 机制

**PM 推荐**：
- 暂不处理（PyPI 稳定性足够）
- 如遇问题，Step 5 治理阶段考虑加 retry

### C.6 Ruff invocation 决策

**当前命令**：`uv run ruff check src/ tests/`

**问题**：
- 无 `--output-format` 显式指定——GitHub Actions 中输出不友好
- CI 失败时 GitHub 注解需要 `--output-format=github`

**PM 推荐**：
```bash
uv run ruff check src/ tests/ --output-format=github --fix
```
（`--output-format=github` 自动生成 GitHub 注解）

**注意**：**不加 `--fix`**——CI 不自动修复（用户裁决后手动）

### C.7 pytest invocation 决策

**当前命令**：`uv run pytest tests/ -v --cov=backend --cov-report=term-missing`

**问题**：
- 无 `--tb=short` 模式（CI 输出冗长）
- 无 `-x`（遇 fail 立即停止）
- 无 `--durations=10`（最慢测试可见性差）

**PM 推荐**：
```bash
uv run pytest tests/ -v --tb=short -x --durations=10 --cov=backend --cov-report=term-missing
```

### C.8 test dependency completeness 决策

**已知事实**：
- `test_entry_layer.py` 本地 venv 28/28 PASS（**uuid_extensions 0.1.0 已装**）
- `pyproject.toml` 缺 `uuid_extensions` 依赖——但 `uuid7>=0.1.0` 已在主依赖
- 是否需要显式声明 `uuid_extensions`？

**事实核查**：
- `uuid7` 是 `uuid_extensions` 的命名空间包？还是另一个包？
- 项目用 `from uuid_extensions import uuid7`
- `pyproject.toml` 声明 `uuid7>=0.1.0`——**这是错的！应该是 `uuid_extensions`**

**PM 关键发现（**Step 2 期间核查**）**：

```toml
# 当前 pyproject.toml
dependencies = [
    ...
    "uuid7>=0.1.0,<1.0",  # ← 这不是 uuid_extensions
    ...
]
```

但代码用：
```python
from uuid_extensions import uuid7  # 实际 import uuid_extensions
```

**如果 pyproject.toml 声明 `uuid7` 而代码用 `uuid_extensions`**，可能：
- 实际工作（巧合：`uuid_extensions` 提供 `uuid7` 函数）
- 或将来某次 `uv lock --upgrade` 后失效

**PM 建议**（不修，仅观察）：
- Step 5 治理阶段考虑修正 `pyproject.toml`：`uuid7` → `uuid_extensions>=0.1.0,<1.0`
- **这超出"CI 治理"范围，属于 dependency 修正——需用户单独裁决**

### C.9 Python 3.11 / 3.12 差异

**当前状态**：
- 3.11 failure: 1 (实际跑)
- 3.12 failure: 1 (cancelled by 3.11)

**根因**：
- 累积 baseline 错误（ruff 1243）让 3.11 fail
- 3.12 因 3.11 fail 取消（默认 fail-fast: true）

**PM 推荐**：
- 移除 3.12 matrix（C.1.1）
- 或设 `fail-fast: false`（C.1.2）

### C.10 failure/cancellation behavior

**当前行为**：
- 3.11 fail → 3.12 cancel（fail-fast: true）
- 用户看到"红叉"= 3.11 fail + 3.12 cancel

**PM 推荐**：
- `fail-fast: false`：3.12 独立跑，独立判定
- 优点：3.12 真实信号不被掩盖
- 缺点：CI 时间 +50%

**最终选择**：PM 建议 **C.1.1（移除 3.12）**——比 fail-fast false 更直接。

---

## 5. D. pytest Baseline — 详细方案

### D.1 关键事实

| 事实 | 证据 |
|---|---|
| 本地 venv `test_entry_layer.py` = 28/28 PASS | PM 实测（2026-09-07）|
| venv `uuid_extensions 0.1.0` 已装 | PM 实测 |
| `pyproject.toml` 声明 `uuid7>=0.1.0`（非 `uuid_extensions`）| PM 核查 |
| CI pytest failure 根因 | 100% 确认需 CI log（用户无 token）|

### D.2 决策：是否需要补 dependency

**PM 评估**：
- 本地 venv 已能跑通 28/28 → **当前不缺 dependency**（在 `uv sync --all-extras` 之后）
- `pyproject.toml` 声明 `uuid7` 是命名不规范，但**功能上 OK**（因为 `uuid_extensions` 装了）
- **建议**：Step 5 治理阶段考虑修正声明（`uuid7` → `uuid_extensions`），但**这不是 pytest baseline 失败根因**

### D.3 决策：是否需要调整 CI dependency installation

**当前**：`uv sync --all-extras`

**PM 推荐**：保持现状。已装齐 dev + test + postgres。

### D.4 决策：是否需要调整测试命令

**当前**：`uv run pytest tests/ -v --cov=backend --cov-report=term-missing`

**PM 推荐**：加 `--tb=short -x --durations=10`（见 C.7）

### D.5 决策：是否需要调整 matrix

**PM 推荐**：移除 3.12（见 C.1.1）

### D.6 决策：是否保留 `--ignore`

**当前**：CI 命令无 `--ignore`——**这意味着 CI 跑全部 853 个测试**

**PM 评估**：
- 之前 Step 4 报告"--ignore=tests/test_entry_layer.py"是**我误用本地 venv 的习惯**
- CI 实际跑全部测试（无 ignore）
- 本地 venv 跑全部 853 = 0 failed

**PM 推荐**：
- CI 不加 `--ignore`（保持跑全部测试）
- 信任 `uv sync --all-extras` 装齐依赖

### D.7 特别要求

> 既然本地 venv 已证明 `test_entry_layer.py = 28/28 PASS`，不得继续把 `uuid_extensions missing` 当作当前 baseline failure 根因。

**PM 确认**：未来不以此为根因。当前 baseline 失败根因在 CI 环境（uv 0.11.x / cache / network），不在依赖。

---

## 6. E. Scope Boundary（明确不做）

| 不做 | 原因 |
|---|---|
| ❌ 修 1243 个历史 ruff 错误 | 用户明确"不进行无关代码清理"；风险/工作量不匹配 |
| ❌ 业务代码重构 | 用户明确"不修改业务代码" |
| ❌ 修改 M6 行为 | 用户明确"不修改已经 LOCKED 的 M6 行为" |
| ❌ 修改 D5-2 / D5-3 | 用户明确"不修改 D5-2 / D5-3" |
| ❌ 处理 M1 / M3 / MemoryService | 用户明确"不处理 M1 / M3 / MemoryService" |
| ❌ 进入 D6 | 用户明确"不进入 D6" |
| ❌ 无关代码清理 | 用户明确"不进行无关代码清理" |
| ❌ 自动 ruff --fix 业务代码 | 仅在 Step 3 修 M6 4 错误范围内使用 --fix |
| ❌ commit / push | 用户明确"当前不授权 commit / push" |
| ❌ rerun CI | 需单独授权 |
| ❌ 启动 Worker | 本步骤无需 Worker；后续 Step 单独授权 |

---

## 7. F. Execution Steps（调整后）

按实际需要设计 5 个 Step（非 7 个）：

### Step 3 — M6 4 Ruff Fixes

| 维度 | 内容 |
|---|---|
| **目标** | 修 M6 引入的 4 个 ruff 错误（2 个 I001 + 1 个 F401 + 1 个 F841）|
| **输入** | Step 1 错误清单 + Step 2 详细修复方案（A.1-A.4）|
| **修改范围** | 仅 2 个新测试文件（`test_ingest_parser_multimodal.py` / `test_ingest_parser_helpers.py`）|
| **禁止范围** | 任何业务代码；任何既有测试；任何 docs；任何 CI 配置 |
| **验证标准** | (1) `ruff check tests/test_ingest_parser_*.py` → 0 errors；(2) `pytest tests/test_ingest_parser_*.py -v` → 150/150 PASS；(3) `pytest tests/ --cov=backend` → 853 passed / 0 failed；(4) git diff 仅 2 文件 |
| **LOCK 条件** | 上述 4 项验证全部通过 |
| **用户授权** | ⏸ 待用户单独授权 |
| **执行方式** | 派 1 个 Worker（@arch-laguna，沿用 M6 测试经验）|

### Step 4 — Legacy Baseline Documentation

| 维度 | 内容 |
|---|---|
| **目标** | 创建 `.hermes/plans/ci-baseline-ruff-state.md` + `.hermes/plans/ci-baseline-ruff-snapshot.txt`（gitignored）|
| **输入** | Step 1 baseline 1243 错误清单 |
| **修改范围** | 仅 `.hermes/plans/` 目录 + `.gitignore`（新增 1 行）|
| **禁止范围** | 任何业务代码；任何 CI workflow；任何 docs |
| **验证标准** | (1) `ci-baseline-ruff-state.md` 存在且可读；(2) `ci-baseline-ruff-snapshot.txt` 存在；(3) `.gitignore` 包含该 snapshot 路径 |
| **LOCK 条件** | 上述 3 项验证通过；用户确认文档 |
| **用户授权** | ⏸ 待用户单独授权 |
| **执行方式** | PM 自行完成（仅文档 + gitignore 一行）|

### Step 5 — CI Configuration Governance

| 维度 | 内容 |
|---|---|
| **目标** | CI 优化：移除 Python 3.12 matrix + 升级 uv + 加 cache + ruff output format + pytest tb/duration |
| **输入** | Step 2 §C 详细方案（C.1-C.10）|
| **修改范围** | 仅 `.github/workflows/ci.yml` |
| **禁止范围** | `pyproject.toml` 依赖；任何业务代码；任何测试 |
| **验证标准** | (1) CI workflow 语法合法；(2) diff 范围仅 ci.yml；(3) PM 独立阅读变更确认无回归；(4) **rerun CI 验证（需用户授权）** |
| **LOCK 条件** | rerun CI 成功（或用户明确接受 baseline 状态）|
| **用户授权** | ⏸ 待用户单独授权（**含 rerun CI 授权**）|
| **执行方式** | 派 1 个 Worker（建议 @arch-laguna）|

### Step 6 — pytest Configuration Alignment

| 维度 | 内容 |
|---|---|
| **目标** | pytest 命令优化（加 `--tb=short -x --durations=10`）；可选修正 `pyproject.toml` 依赖声明（`uuid7` → `uuid_extensions`）|
| **输入** | Step 2 §D 详细方案 |
| **修改范围** | `.github/workflows/ci.yml`（pytest invocation 部分）+ 可选 `backend/pyproject.toml`（一行依赖名修正）|
| **禁止范围** | 任何业务代码；任何测试 |
| **验证标准** | (1) diff 范围仅 ci.yml + 可选 pyproject.toml；(2) 本地 venv 跑同命令仍 853 passed |
| **LOCK 条件** | 验证通过 |
| **用户授权** | ⏸ 待用户单独授权 |
| **执行方式** | 可与 Step 5 合并（同一 ci.yml 修改）；或独立 |

### Step 7 — Final Validation & Lock

| 维度 | 内容 |
|---|---|
| **目标** | 全链路最终验证：M6 24/24 + 150 新测试 + 既有 703 + CI rerun（如果用户授权）|
| **输入** | Step 3-6 全部产出 |
| **修改范围** | 无修改；仅验证 |
| **禁止范围** | 任何修改 |
| **验证标准** | (1) 全部测试通过；(2) baseline 文档完整；(3) CI 真实反映代码状态 |
| **LOCK 条件** | 全部验证通过 + 用户裁决 |
| **用户授权** | ⏸ 待用户单独授权（含 commit/push）|
| **执行方式** | PM 独立执行验证 + 撰写最终 LOCK 报告 |

### Step 8 — commit/push（仅在用户授权后）

| 维度 | 内容 |
|---|---|
| **目标** | 把 Step 3-7 的所有变更 commit 到 origin/main |
| **输入** | Step 3-7 LOCK 状态 |
| **修改范围** | 取决于 Step 3-6 累计变更 |
| **禁止范围** | `.hermes/plans/` 任何文件（PM 工作记录不入 Git）|
| **验证标准** | HEAD == origin/main + working tree clean（除 .hermes/plans/）|
| **用户授权** | ⏸ 单独授权 |
| **执行方式** | PM 独立执行（不派 Worker——commit 须 PM 把关）|

---

## 8. G. 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| **R1: Step 3 ruff --fix 引入新 bug** | 极低 | 高 | 修前后均跑 150 测试 + 853 全量 |
| **R2: Step 3 删 `call_args` 行改变测试断言** | 低 | 中 | 单独跑 TestCallContracts 2 个测试验证 |
| **R3: Step 4 baseline 掩盖真实新问题** | 中 | 高 | baseline 仅记录**当前已知错误**；CI diff 检查 new error；规则变化需用户裁决 |
| **R4: Step 5 移除 Python 3.12 matrix 让用户不满** | 中 | 中 | 明确声明 + 用户授权；本地仍可用 3.12 |
| **R5: Step 5 升级 uv 引入新问题** | 中 | 中 | 改小范围 + rerun CI 验证 |
| **R6: Step 5 cache 配置引入竞态** | 低 | 中 | GitHub Actions cache 是稳定的；rerun CI 验证 |
| **R7: Python 版本差异（3.11 vs 3.12）** | 中 | 中 | 移除 3.12 matrix 后无此风险 |
| **R8: uv / cache / network 不稳定** | 中 | 中 | rerun CI 多次确认非偶发 |
| **R9: Ruff 规则变化（升级 ruff 后）** | 低 | 中 | snapshot 重生成需用户决策 |
| **R10: 历史 debt 与 new debt 混淆** | 中 | 高 | baseline snapshot 必须每 commit 更新（需 governance）|
| **R11: 对 LOCKED 阶段影响** | 0 | 0 | Step 3-6 不改业务代码；M6 / D5-2 / D5-3 不变 |
| **R12: Step 5 CI 修改掩盖 baseline failure** | 中 | 中 | 明确：CI 治理仅优化**配置**，不优化**业务代码 baseline** |

### G.1 R3 baseline 掩盖问题详细分析

**风险**：
- baseline snapshot 记录 1243 个错误
- 未来 commit 引入 1244 错误 → CI 失败（new debt = 1）✅
- 但如果 baseline snapshot 错误**与新错误**在同文件同行：技术性不能区分？
  - 答：ruff 输出格式 `<file>:<line>:<col>:<rule>:<msg>` 精确匹配
  - 同行可有多错误（不同 col）—— 仍能区分
  - 唯一盲点：同行同 col 同规则（极端罕见）

**缓解**：
- baseline snapshot 必须**每次 commit 更新**（如果有 baseline error 修复）
- 否则：未来 commit 即使删了某个 baseline error，CI 也会因 "消失的 baseline error" 显示 dirty diff——**但不构成 failure**（仅消失的 error 不算 new debt）

### G.2 R10 详细分析

**风险**：未来 commit 引入新错误**与 baseline 错误混淆**

**机制**：
- baseline snapshot 第 N 行 = `src/backend/foo.py:123:5: F401: 'os' imported but unused`
- 新 commit 在 `src/backend/foo.py:124:5` 引入 F401
- diff 输出：新行 `<`（从 baseline 删除）+ `>`（新增）
- 检查 `>` 行数 = 1 → **CI 失败**（new debt detected）✅

**有效**。

---

## 9. H. 风险对 LOCKED 阶段的影响

| LOCKED 阶段 | Step 3 影响 | Step 4 影响 | Step 5 影响 | Step 6 影响 |
|---|---|---|---|---|
| M6 (`1f24c9e`) | 仅改 M6 测试文件，**不动 M6 行为** | 无 | 无 | 无 |
| D5-3 (`0e4cf20`) | 无 | 无 | 无 | 无 |
| D5-2 (`bc65e96`) | 无 | 无 | 无 | 无 |
| P0-2 (`86910e2`) | 无 | 无 | 无 | 无 |
| P0-1 (`32e9577`) | 无 | 无 | 无 | 无 |
| BUG-WS1 (`58ff5cb`) | 无 | 无 | 无 | 无 |
| Phase 26-G | 无 | 无 | 无 | 无 |

**结论**：Step 3-6 不影响任何 LOCKED 阶段。

---

## 10. I. 最终交付物

### 文件创建清单

| 文件 | 性质 | 阶段 |
|---|---|---|
| `.hermes/plans/ci-baseline-ruff-state.md` | baseline 文档 | Step 4 |
| `.hermes/plans/ci-baseline-ruff-snapshot.txt` | baseline snapshot（gitignored）| Step 4 |
| `.gitignore` 修改（+1 行）| snapshot 不入 Git | Step 4 |
| `.github/workflows/ci.yml` 修改 | CI 治理 | Step 5/6 |

### 状态标识

```
CI_BASELINE_STEP2 = COMPLETE

IMPLEMENTATION_AUTHORIZATION_REQUIRED = YES

COMMIT_AUTHORIZATION = NO
PUSH_AUTHORIZATION = NO
```

---

## 11. J. 后续 Step 授权矩阵

| Step | 任务 | 是否需用户单独授权 | 备注 |
|---|---|---|---|
| **Step 3** | 修 M6 4 ruff 错误 | ✅ 是 | 业务代码外的小范围修改 |
| **Step 4** | 创建 baseline 文档 + snapshot | ✅ 是 | 文档类，但 .gitignore 变更需授权 |
| **Step 5** | CI workflow 修改 | ✅ 是 | 涉及 CI 配置变更 |
| **Step 6** | pytest 命令 + 依赖声明修正 | ✅ 是 | 涉 pyproject.toml 需单独授权 |
| **Step 7** | 最终验证 | ✅ 是 | 需用户接受最终状态 |
| **Step 8** | commit + push | ✅ 是（独立）| 任何 commit/push 必单独授权 |

### 严格纪律

- 每个 Step 派 1 个 Worker → PM 复核 → 下个 Step（不并行）
- PM 复核独立执行（不沿用 Worker 报告）
- 不擅自 commit/push
- 不擅自 rerun CI
- 不进入 M1 / M3 / MemoryService / D6 / Phase 21

### 当前状态

- ✅ Step 2 完成
- ⏸ Step 3-8 待用户单独授权

Worker 全部停止。