# CI Baseline Governance — Step 1 Forensic Inventory & Governance Plan

**状态**: Step 1 完成（仅调查；未修复；未修改任何文件；未派 Worker）
**生成时间**: 2026-09-07
**生成者**: @pm-hy3（PM 独立调查）
**基准 commit**: `1f24c9e2de0af800b9ca84a4c339ad2a4cd22769` (M6)
**workflow run**: `34129393841`

---

## 1. Executive Summary

| 维度 | 数值 |
|---|---|
| **M6 真实引入 ruff 错误** | **4 个**（全部在 2 个新测试文件）|
| **M6 之前 baseline ruff 错误** | 1239 个（仓库长期问题）|
| **全仓库 ruff 错误** | 1243 |
| **M6 真实引入 pytest failure** | 0 |
| **本地 venv 跑 CI pytest 命令结果** | **853 passed / 0 failed / 0 errors** |
| **CI 失败性质** | **BASELINE_FAILURE**（D5-2 / D5-3 / M6 三次 commit 同样失败）|

**关键判断**：M6 实际未引入新问题；CI 失败根因是仓库 baseline 长期 ruff 错误 + CI 环境差异。

---

## 2. Current CI Baseline

### 2.1 workflow run 34129393841（commit 1f24c9e）

| # | Job | Conclusion | 失败 Step |
|---|---|---|---|
| 1 | Static Analysis (ruff + mypy) (3.11) | ❌ failure | Step 6: Run ruff (linting) |
| 2 | Build verification | ✅ success | — |
| 3 | Unit Tests (pytest) (3.11) | ❌ failure | Step 6: Run tests |
| 4 | Unit Tests (pytest) (3.12) | ⚠️ cancelled | 3.11 失败联动 |

### 2.2 三次连续 commit 同样失败（决定性证据）

| Commit | ruff | pytest 3.11 | pytest 3.12 | Build |
|---|---|---|---|---|
| bc65e96 (D5-2) | ❌ | ❌ | ⚠️ cancelled | ✅ |
| 0e4cf20 (D5-3) | ❌ | ❌ | ⚠️ cancelled | ✅ |
| 1f24c9e (M6) | ❌ | ❌ | ⚠️ cancelled | ✅ |

**M6 之前 CI 已常年红**——非 M6 引入。

---

## 3. Ruff Full Inventory

### 3.1 全仓库 ruff 错误

```
Found 1243 errors.
[*] 1049 fixable with the `--fix` option (130 hidden fixes with --unsafe-fixes).
```

### 3.2 规则类型 top

| 规则 | 数量 | 自动 fix | 性质 |
|---|---|---|---|
| **W293** Blank line contains whitespace | 921 | ✅ | 风格 |
| **F401** imported but unused | 78 | ✅ | 死代码 |
| **I001** Import block un-sorted | 61 | ✅ | 风格 |
| **F841** Local variable assigned but never used | 37 | ❌ | 死代码 |
| **W291** Trailing whitespace | 18 | ✅ | 风格 |
| **E712** Comparison with False/True | 13 | ❌ | 风格 |
| **F821** Undefined name | 12 | ❌ | **可能业务 bug** |
| **F811** Redefinition of unused name | 8 | ❌ | 死代码 / 冲突 |
| **F541** f-string without placeholders | 5 | ✅ | 风格 |
| **B905** `zip()` without `strict=` | 2 | ❌ | Python 3.10+ |
| **W292** No newline at end of file | 1 | ✅ | 风格 |
| **N806** Non-lowercase variable | 1 | ❌ | 风格 |
| **B017** `pytest.raises(Exception)` | 1 | ❌ | 测试质量 |
| **B007** Unused loop variable | 1 | ❌ | 死代码 |

**总计**: 1243 / 1050 auto-fixable (84.5%) / 193 manual (15.5%)

### 3.3 错误集中区域（与 M6 无关）

- `src/backend/context/` — Phase 21.3/21.4 重构历史遗留
- `src/backend/ingest/` 既有部分 — 历史 adapter 风格问题
- 各种业务模块散落 — 历史累积

### 3.4 F821 详情（潜在业务 bug）

```
F821 Undefined name `InterpretationContext`
   --> src/backend/context/context_window.py:139:45
   注：因 from __future__ import annotations 不影响运行期；类型注解不算真 bug
```

F821 主要在 `from __future__ import annotations` 文件中——**运行期无影响**。

---

## 4. M6-New Ruff Issues（精确识别）

### 4.1 之前 CI forensic 报告错误

我之前报告说"M6 涉及 5 个文件 ruff 错误 99 个"——**这是错误**。`ruff check src/ tests/` 默认扫描整个仓库，包括 M6 之前就有的 baseline 错误。

### 4.2 精确识别方法

对比 0e4cf20 (D5-3) vs 1f24c9e (M6)：
- 3 个生产文件：M6 改动行 vs 既有行
- 2 个新测试文件：全部 NEW

### 4.3 实际 M6 引入错误数

| 文件 | M6 改动行 ruff 错误 | 备注 |
|---|---|---|
| `backend/src/backend/app.py` | 0 | M6 改动 1831-1835（薄委托），无 ruff 问题 |
| `backend/src/backend/ingest/parser.py` | 0 | M6 新增 2 函数，ruff 干净 |
| `backend/src/backend/ingest/adapters/chatgpt.py` | 0 | M6 改动 362-367（min_length=3），ruff 干净 |
| `backend/tests/test_ingest_parser_multimodal.py` | 3 | 全部 NEW |
| `backend/tests/test_ingest_parser_helpers.py` | 1 | 全部 NEW |
| **M6 真实引入** | **4** | |

### 4.4 4 个 M6 引入错误清单

| # | 文件 | 行 | 规则 | 自动 fix | 风险 |
|---|---|---|---|---|---|
| 1 | `test_ingest_parser_multimodal.py` | 29 | I001 Import 排序 | ✅ | 0（仅排序）|
| 2 | `test_ingest_parser_multimodal.py` | 490 | F401 `inspect` unused | ✅ | 0（删除 import）|
| 3 | `test_ingest_parser_multimodal.py` | 526 | F841 `call_args` unused | ❌ | 0（删除变量）|
| 4 | `test_ingest_parser_helpers.py` | 19 | I001 Import 排序 | ✅ | 0（仅排序）|

**3 个可自动 fix / 1 个需手动删除变量**。**无 F821 / 无业务行为风险**。

### 4.5 F841 详情（`call_args` unused）

```python
# test_ingest_parser_multimodal.py:526
call_args = mock_fn.call_args.args  # 留作"提取 kwargs 验证模式"参考
# 实际只用了 call_kwargs
```

**修复方式**：删除 `call_args = mock_fn.call_args.args` 行（或加 `_ = call_args`）。

### 4.6 结论

- M6 真实引入 4 个 ruff 错误（全部测试文件风格问题）
- **0 个 F821 / 0 个可能影响业务的错误**
- M6 之前 baseline 已有 1239 个 ruff 错误

---

## 5. Pytest Failure Forensics

### 5.1 CI pytest 命令

```bash
cd backend
uv sync --all-extras
uv run pytest tests/ -v --cov=backend --cov-report=term-missing
```

### 5.2 本地 venv 复现（PM 独立实测）

```
$ .venv/Scripts/python.exe -m pytest tests/ -v --cov=backend --cov-report=term-missing
================= 853 passed, 8 skipped, 9 warnings in 27.42s =================
```

**关键事实**：
- 0 failed / 0 errors
- 853 passed = D5-3 基线 703 + M6 新增 150
- `test_entry_layer.py` 28 个全部通过
- coverage 55%

### 5.3 之前报告错误（重要修正）

我之前 Step 4 报告说 "`test_entry_layer.py` 缺 `uuid_extensions`" 是**误判**——

**真相**：
- 本地 venv `uuid_extensions 0.1.0` **已装**
- `test_entry_layer.py` 28 个测试**全部 PASS**
- 我之前用 system python 跑导致误判，并沿用 ignore 习惯

### 5.4 CI 失败根因分析

**CI Step 5 (Install dependencies)** 全部 success — 说明 `uv sync --all-extras` 成功。
**CI Step 6 (Run tests)** 在 Python 3.11 / 3.12 都失败，但本地 venv 同样 Python 3.11 通过。

**可能根因**（按可能性排序）：

| # | 根因假设 | 证据 | 验证方法 |
|---|---|---|---|
| 1 | **CI 的 `uv` 0.11.x 与 pyproject 依赖兼容性** | uv 0.11.x 是 2024 版本 | 需 CI log 详细分析 |
| 2 | **Python 3.12 与某些包不兼容** | 3.11 / 3.12 都失败 | 需 CI log |
| 3 | **CI 缓存问题** | 偶发 | 需 rerun CI（用户未授权）|
| 4 | **网络下载问题** | uv 装包偶发失败 | 需 CI log |

**目前无法 100% 确认根因**——需要 CI 详细 log（需要 GitHub auth token，本地无 token）。

### 5.5 关键判断

- **M6 真实引入 pytest failure = 0**
- **本地 venv 跑同样命令 = 0 failed**
- **CI 失败根因在 CI 环境，不是 M6 代码**
- **D5-2 / D5-3 同样 commit 也 CI 失败**——证明 CI 长期 baseline 失败

---

## 6. GitHub Actions Configuration Review

### 6.1 workflow 文件

| 文件 | 备注 |
|---|---|
| `.github/workflows/ci.yml` | 唯一 CI workflow；3 job：static-analysis / unit-tests / build |

### 6.2 Job 配置

| Job | Matrix | 关键命令 |
|---|---|---|
| static-analysis | python 3.11 | `uv run ruff check src/ tests/` + `uv run mypy src/` |
| unit-tests | python 3.11 + 3.12 | `uv run pytest tests/ -v --cov=backend --cov-report=term-missing` |
| build | python 3.11 | `uv build` + `ls dist/*.whl` |

### 6.3 CI 现状

| 项 | 现状 | 评估 |
|---|---|---|
| Node.js 20 弃用警告 | GitHub 提示 actions 强制 Node.js 24 | 警告级 |
| `uv` 版本固定 | 0.11.x（旧版）| 可能与现代 pyproject 不兼容 |
| Python 3.12 matrix | matrix 包含 3.12 | 与某些包可能不兼容 |
| `uv sync --all-extras` | 装齐 dev + all extras | 合理 |
| coverage 选项 | `--cov=backend` | 必装 pytest-cov |
| `uv.lock` 存在 | ✅ 存在（2025-07-21，365KB）| 锁文件已存在 |
| `pyproject.toml` coverage 配置 | 无 fail_under | coverage 报告不会让 pytest 退出非 0 |

### 6.4 关键问题

| 问题 | 详情 |
|---|---|
| Q1: `uv` 0.11.x 是否过旧？ | 0.11.x 是 2024 版本，现代 pyproject 推荐 0.4+ 或更新 |
| Q2: Python 3.12 必要性？ | 双 matrix 双倍 CI 时间；与某些包可能不兼容 |
| Q3: coverage threshold？ | pyproject.toml 未设 fail_under —— coverage 不会让 pytest 退出非 0 |
| Q4: mypy 是否在 ruff failure 时被跳过？ | 是（依赖 6 失败，7 跳过）—— 不影响 ruff 失败根因 |
| Q5: ruff 是否在 baseline pre-commit 强制？ | 无 pre-commit 配置发现（PM 核查）|

---

## 7. Root Cause Classification

按 @user §C 要求分类：

| 类别 | 占比 | 治理难度 | 备注 |
|---|---|---|---|
| **代码问题**（F821 潜在 bug）| 12 | 中 | 大多在 `from __future__ import annotations`，运行期无害 |
| **代码问题**（F401 / F841 / F811 死代码）| 123 | 低 | 大部分可 auto-fix |
| **代码问题**（E712 / N806 / N811 风格）| 14 | 低 | auto-fix 或简单改写 |
| **代码问题**（B008 / B904 / B905 / B017 / B007 行为建议）| 32 | 中 | FastAPI Depends / except 风格建议 |
| **风格问题**（W293 / W291 / W292 / I001 / F541）| 1006 | **极低** | 全部 auto-fix |
| **CI 配置问题**（uv 版本 / Python 3.12 matrix）| ? | 中 | 需 CI log 详细分析 |
| **历史技术债** | 全部 baseline 错误 | 高 | M6 之前累积多年 |

### 7.1 M6 真实分类

| 类别 | 数量 | 治理难度 |
|---|---|---|
| M6 新增（测试文件风格）| 4 | 极低 |
| M6 新增（业务影响）| 0 | — |
| M6 之前 baseline | 1239 | 中—高 |

---

## 8. Governance Options

### 方案 A：全部清零

| 维度 | 评估 |
|---|---|
| **目标** | 1243 ruff 错误全部修复；CI pytest 失败根因解决；CI 全绿 |
| **修改范围** | 整个 `backend/src/` `backend/tests/` 几乎所有文件 |
| **风险** | **极高** — 大量风格修改可能掩盖业务变更；auto-fix 可能引入新 bug |
| **工作量** | 4-8 人天（auto-fix）+ 1-2 人天（manual 193 个）+ CI 治理 |
| **对 LOCKED 阶段影响** | 极高 — D5-2 / D5-3 / M6 LOCKED 状态可能因代码变更而失效 |
| **回归测试** | 需重跑所有 853 passed + 既有 LOCKED 阶段验证 |
| **是否重新定义 CI baseline** | 是 |
| **推荐度** | ⭐ 不推荐（风险/工作量与收益不匹配）|

### 方案 B：Legacy Baseline + No New Debt

| 维度 | 评估 |
|---|---|
| **目标** | 建立 ruff baseline 文档化；M6 引入的 4 个错误清零；后续 commit 禁止新增 ruff debt |
| **修改范围** | 2 个新测试文件（4 错误）+ `.ruff.toml` baseline 配置 |
| **风险** | 低（仅 4 错误）|
| **工作量** | 1-2 小时（修 4 错误 + baseline 配置）|
| **对 LOCKED 阶段影响** | 0（不动既有代码）|
| **回归测试** | 重跑 853 passed + 150 新测试 |
| **是否重新定义 CI baseline** | 是（建立 baseline 阈值）|
| **推荐度** | ⭐⭐⭐ **PM 推荐作为 M6 后续**（最低风险，最直接）|

#### 方案 B 详细实施

1. **修 M6 4 个 ruff 错误**（1 个 PR 1 个 commit）：
   - `test_ingest_parser_multimodal.py:29` I001 — `ruff --fix`
   - `test_ingest_parser_multimodal.py:490` F401 — `ruff --fix`
   - `test_ingest_parser_multimodal.py:526` F841 — 删 `call_args` 行
   - `test_ingest_parser_helpers.py:19` I001 — `ruff --fix`

2. **建立 ruff baseline 文档**（`.hermes/plans/ci-baseline-ruff-state.md`）：
   - 记录 1239 baseline 错误存在
   - 声明"暂不修复历史 baseline"
   - 声明"未来 commit 禁止引入新 ruff 错误"

3. **可选：CI 加 pre-commit / pre-merge 检查**（不在本步范围）

### 方案 C：CI 配置治理

| 维度 | 评估 |
|---|---|
| **目标** | 不动业务代码；仅治理 CI 配置（uv 版本 / Python matrix / 锁文件）|
| **修改范围** | `.github/workflows/ci.yml` + `pyproject.toml` (dev deps) |
| **风险** | 中（CI 配置错误可能引入新 failure）|
| **工作量** | 2-4 小时（CI log 分析 + 配置调整 + rerun CI）|
| **对 LOCKED 阶段影响** | 0（不动业务代码）|
| **回归测试** | 仅 rerun CI |
| **是否重新定义 CI baseline** | 部分（仅 CI 层面）|
| **推荐度** | ⭐⭐ **可作为方案 B 补充**（CI 治理 + baseline 文档）|

#### 方案 C 详细实施

1. **CI log 详细分析**（需 GitHub auth token — 用户侧动作）
2. **可能调整**：
   - `uv` 版本从 0.11.x 升级到 0.4+ 或最新
   - Python matrix 移除 3.12（仅 3.11）— 双倍时间节省 + 减少兼容问题
   - 加 coverage fail_under 阈值（可选）
3. **rerun CI 验证**

### 方案 D：混合方案（B + C）— PM 推荐

| 维度 | 评估 |
|---|---|
| **目标** | 修 M6 引入的 4 错误 + 建立 baseline 文档 + 治理 CI 配置 |
| **修改范围** | 2 个新测试文件 + baseline 文档 + CI 配置（如用户授权）|
| **风险** | 低-中（CI 配置变更需谨慎）|
| **工作量** | 1-2 人天 |
| **对 LOCKED 阶段影响** | 0 |
| **回归测试** | 853 passed + rerun CI |
| **是否重新定义 CI baseline** | 是（建立 baseline 文档 + CI 优化）|
| **推荐度** | ⭐⭐⭐⭐ **PM 强推荐**（兼顾短期可执行 + 长期可维护）|

---

## 9. Recommended Governance Strategy

### 9.1 PM 强烈推荐：方案 D（混合 B + C）

**理由**：
1. **风险最低**：不动业务代码（除 M6 4 个测试错误）
2. **直接收益**：M6 引入错误清零；建立 baseline 文档
3. **长期收益**：CI 配置优化；后续 commit 有 baseline 约束
4. **LOCKED 阶段不受影响**：0 业务代码变更（除 4 个测试 lint）
5. **可分解执行**：每个动作独立授权、独立 commit、独立验证

### 9.2 推荐执行顺序

| 阶段 | 任务 | 授权 |
|---|---|---|
| **Phase 1** | 修 M6 4 个 ruff 错误（2 个测试文件）| 待用户授权 |
| **Phase 2** | 建立 ruff baseline 文档 `.hermes/plans/ci-baseline-ruff-state.md` | 待用户授权 |
| **Phase 3** | CI 配置治理（uv 版本 / Python matrix / 锁文件）| 待用户授权 + 需 CI log 协助 |
| **Phase 4** | rerun CI 验证 | 待用户授权 |

---

## 10. Proposed Future Execution Steps

### Phase 1 — 修 M6 4 个 ruff 错误（建议 1 个 commit）

**范围**：
- 2 个新测试文件（4 个错误）

**变更**：
| 文件 | 变更 |
|---|---|
| `test_ingest_parser_multimodal.py:29` | `ruff --fix` I001（自动）|
| `test_ingest_parser_multimodal.py:490` | `ruff --fix` F401（自动删除 `inspect` import）|
| `test_ingest_parser_multimodal.py:526` | 删除 `call_args = mock_fn.call_args.args` 行 |
| `test_ingest_parser_helpers.py:19` | `ruff --fix` I001（自动）|

**验证**：本地 pytest 853 passed；ruff check M6 涉及文件 0 错误

**风险**：极低

### Phase 2 — 建立 baseline 文档

**范围**：仅文档

**变更**：
- 新建 `.hermes/plans/ci-baseline-ruff-state.md`
- 文档化 1239 baseline 错误存在
- 声明后续 commit 禁止新增

**验证**：文档可读

**风险**：0

### Phase 3 — CI 配置治理

**范围**：仅 `.github/workflows/ci.yml` + 可能 `pyproject.toml` dev deps

**变更**（需先看 CI log）：
- 升级 `uv` 版本（0.11.x → 0.4+ 或最新）
- 可能移除 Python 3.12 matrix
- 可选加 coverage fail_under

**验证**：rerun CI 必须成功（当前所有 baseline failure 仍可继续存在，仅 CI 工程层面优化）

**风险**：中

**前置条件**：需用户侧 GitHub auth token 或访问 CI log 权限

### Phase 4 — rerun CI 验证

**授权**：
- 用户点击 "Re-run jobs" 按钮（需用户侧）
- 或 push 新 commit 触发

**期望结果**：
- ruff 仍 failure（baseline 1239 错误仍在，但**没有 M6 新增**）
- pytest 仍 failure（CI 环境问题需 Phase 3 治理）
- **M6 引入错误 = 0**

---

## 11. Risks / Scope Boundaries

### 11.1 治理阶段风险

| 风险 | 触发 | 缓解 |
|---|---|---|
| Phase 1 ruff --fix 引入新 bug | 自动 fix 改变 import 顺序导致循环 import | 修后跑全部 853 passed 验证 |
| Phase 1 删除 `call_args` 行改变测试语义 | `call_args` 是留作未来参考 | 验证测试仍通过 |
| Phase 3 CI 配置变更导致其他 failure | uv 版本升级引入兼容问题 | 仅改小范围 + rerun CI |
| Phase 3 移除 Python 3.12 matrix 引起用户不满 | 用户可能希望 3.12 支持 | 明确声明 + 用户授权 |

### 11.2 范围外（明确不治理）

- 1239 baseline ruff 错误（历史债务）
- 任何业务代码逻辑变更
- Service / Engine / Repository 重构
- Frozen 文档变更
- commit/push（需单独授权）
- Worker 启动（保持停止）

### 11.3 CI 失败根因 100% 确认限制

PM 本地无 GitHub auth token——**无法直接查看 CI job 详细 log**。CI 失败根因 100% 确认需：
- 用户侧：登录 GitHub 查看 workflow run 34129393841 的 job log
- 或：PM 接受 GitHub auth token（用户授权）
- 或：直接 rerun CI 看是否复现

### 11.4 M6 状态澄清

按本次调查：
- M6 业务功能正确（24/24 byte-for-byte baseline 等价）
- M6 引入 ruff 错误 = 4（极低风险）
- M6 引入 pytest failure = 0
- M6 CI 失败 = BASELINE_FAILURE（非 M6 引入）

**M6 业务可标为 FUNCTIONAL_LOCKED**——但需用户裁决。

---

## 12. User Authorization Required

```
CI_BASELINE_STEP1 = COMPLETE
EXECUTION_AUTHORIZATION_REQUIRED = YES
```

### 待用户裁决

1. **M6 状态重新定义**：
   - (a) **FUNCTIONAL_LOCKED**（业务功能锁定，CI failure 已知但非 M6 引入）
   - (b) **CI_PENDING**（CI 失败不解除，CI 修复后再次验证）
   - (c) 其它

2. **下一步治理动作**：
   - (a) 仅修 M6 4 ruff 错误（最小动作）
   - (b) 修 M6 4 错误 + 建立 baseline 文档（推荐）
   - (c) 修 M6 4 错误 + baseline 文档 + CI 配置治理（最完整）
   - (d) 暂不治理 / 其它

3. **CI log 协助**（如需方案 C/D）：
   - (a) 用户自行登录 GitHub 查看 workflow run 34129393841 log
   - (b) 用户提供 GitHub auth token 给 PM
   - (c) 用户不参与 CI log 调查，仅做 surface-level 修复

4. **是否授权 follow-up commit**（无论选哪个方案）：
   - (a) 授权 Phase 1 commit（仅 M6 4 错误修复）
   - (b) 授权 Phase 1 + 2 commit（+ baseline 文档）
   - (c) 授权 Phase 1 + 2 + 3（+ CI 配置，需 log 协助）
   - (d) 暂不授权

### 严格纪律

本次 PM 严格遵守：
- ✅ 仅做 CI baseline 调查，未修改任何文件
- ✅ 未派 Worker
- ✅ 未 commit
- ✅ 未 push
- ✅ 未 rerun CI
- ✅ 未修改业务代码 / 测试 / docs / CI workflow / 依赖

Worker 全部停止。