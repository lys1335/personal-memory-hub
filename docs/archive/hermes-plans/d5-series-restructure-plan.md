# D5 系列重构 — 执行计划

**状态**: PLAN（只读，待 @user 审核批准）
**生成时间**: 2026-09-04
**生成者**: @pm-hy3
**项目**: personal-memory-hub (F:\LI_YONGSHUN\AI\personal-memory-hub)
**关联裁决**: 原 PMH 群组裁决 → 重新对齐 → 选项 A（重新规划 D5 系列）

---

## 1. 背景与事实基础

### 1.1 仓库现状（已核实）

- 仓库根无 `src/`，代码位于 `backend/src/backend/` 子树
- Phase 1 (P0-1 / P0-2) 已完成并同步到 origin/main（commit `32e9577` + `86910e2`）
- 工作区干净，无未提交修改

### 1.2 顶层包结构（已盘点）

```
backend/src/backend/
├── app.py              — composition root
├── context/            — 上下文管理
├── engine/             — 引擎层
├── entry/              — 入口层
├── evolution/          — 【重构目标】evolution_engine.py + evolution_service.py
├── ingest/             — 摄入模块（含 adapters/）
├── repository/         — 仓储层（18 个 repository 文件）
├── service/            — 服务层（14 个 service 文件）
└── shared/
    ├── domain/         — 领域模型（含 proposal_model.py）
    └── infrastructure/
        ├── config/
        ├── database/
        ├── di/         — 依赖注入（container.py）
        └── logging/
            ├── protocols/    — 协议抽象
            └── providers/    — 提供者实现
                └── reflection_provider.py
```

### 1.3 evolution/ 包引用情况（已核实）

**被引用方**（仅 2 处）：
- `backend/src/backend/app.py:198` — `from backend.evolution.evolution_service import EvolutionService`
- `backend/src/backend/service/evidence_pipeline_service.py:27` — `from backend.evolution.evolution_service import EvolutionService`

**evolution/ 包内容**：
- `__init__.py`
- `evolution_engine.py`
- `evolution_service.py`

### 1.4 其他 D5 相关项现状

| 项 | 当前位置 | 备注 |
|---|---|---|
| `MemoryHubError` | `backend/src/backend/service/exceptions.py:32` | 需迁至 `shared/` |
| Composition Root | `backend/src/backend/app.py:2030` | 已存在 |
| Repo 注入化 | `shared/infrastructure/di/container.py` + 18 个 repository | 已完成 |
| 共享抽取器 | 不存在 | 未涉及 |
| Ingest 模块 | `backend/src/backend/ingest/` + `adapters/` | 已存在 |

---

## 2. 目标

将 `evolution/` 包正确归位到 `service/` 命名约定下；将 `MemoryHubError` 迁至 `shared/`；保持现有架构风格（不引入新抽象、不改变依赖注入模式、不重写逻辑）。

**非目标（明确不做）**：
- 不重写 evolution 业务逻辑
- 不改变 DI 容器结构
- 不删除任何测试
- 不修改任何 alembic 迁移
- 不引入 extractor 共享层（除非 @user 额外授权）
- 不扩大范围至 D1–D7 其它项

---

## 3. 执行步骤（单线程）

### Step 1 — D5-1：evolution/ 包职责与依赖调查（**只读**）

**Worker**: @arch-laguna
**前置**: 当前可启动（无需依赖）
**目标**: 摸清 `evolution_engine.py` 与 `evolution_service.py` 的真实职责、外部依赖、被测试覆盖情况，为迁移/删除决策提供事实

**任务内容**（只读）：

1. `cd F:\LI_YONGSHUN\AI\personal-memory-hub`
2. 读取并报告：
   - `backend/src/backend/evolution/__init__.py` 完整内容
   - `backend/src/backend/evolution/evolution_engine.py` 类/函数清单 + 1 行职责概述 + 外部依赖（import）
   - `backend/src/backend/evolution/evolution_service.py` 类/函数清单 + 1 行职责概述 + 外部依赖（import）
3. 全仓搜索引用：
   - `rg "evolution_engine|evolution_service|EvolutionService|EvolutionEngine" --type py`
   - `rg "from backend.evolution|import backend.evolution" --type py`
4. 测试覆盖：
   - `find backend/tests -type f -name "*.py" | xargs grep -l "evolution" 2>/dev/null`
   - 列出涉及 evolution 的测试文件 + 每个文件的测试用例数
5. 文档引用：
   - `grep -r "evolution" backend/docs/ docs/ 2>/dev/null | head -50`（仅文件路径，不输出文件内容除非必要）

**输出要求**:
- 两个 evolution 文件的职责摘要
- 全仓引用清单（含文件路径与行号）
- 测试覆盖统计
- 文档引用清单
- **明确给出建议**：A) 迁移至 `service/`（推荐）/ B) 原地保留 / C) 删除（需证据支撑），并附理由

**约束**: 不修改任何文件；不输出超过需要的代码；不展开业务逻辑分析

---

### Step 2 — D5-2：按 D5-1 结论迁移或删除 evolution/ 包（**可执行**）

**Worker**: @agnes-worker
**前置**: Step 1 完成且结论明确（迁移/原地/删除三选一）
**授权**: 需 @user 单独授权（不在本计划默认范围）

**任务模板**（按 D5-1 结论二选一）：

**情形 A — 迁移至 service/**：
1. 将 `evolution_engine.py`、`evolution_service.py` 内容迁入 `backend/src/backend/service/`（新文件名待 D5-1 决定）
2. 更新所有引用：
   - `app.py:198`
   - `evidence_pipeline_service.py:27`
3. 删除 `backend/src/backend/evolution/` 空目录
4. 运行：`cd backend && python -m pytest tests/ -x -q`（必须全绿）
5. 运行：`git diff --stat`（确认无混入）

**情形 B — 原地保留**：
- 仅更新文档说明，无需代码变更
- 记录决议到 `docs/CODEX_CONTEXT.md`（如有权限）或交付报告

**情形 C — 删除**：
- 必须先有 D5-1 证据证明无业务逻辑依赖
- 删除 evolution/ 目录与所有引用
- 运行测试必须全绿

**交付**:
- `git diff --stat` 输出
- 测试运行结果
- 明确的"完成 / 未完成 / 阻塞"结论

**约束**: 不 commit/push；不修改 DI 容器；不修改测试用例；如遇测试失败立即上报不擅自调整

---

### Step 3 — D5-3：MemoryHubError 迁移（**可执行**）

**Worker**: @agnes-worker
**前置**: Step 2 完成
**授权**: 需 @user 单独授权（不在本计划默认范围）

**任务内容**:

1. 在 `backend/src/backend/shared/domain/`（或 `shared/` 下经 D5-1 确认的合适位置）新建 `exceptions.py`
2. 从 `backend/src/backend/service/exceptions.py:32` 迁移 `MemoryHubError` 类定义
3. 全仓搜索 `MemoryHubError` 引用：
   - `rg "MemoryHubError" --type py`
4. 更新所有 import 路径（保持 import 风格一致）
5. 决定 `service/exceptions.py` 处理：
   - 若仅含 `MemoryHubError` → 删除文件
   - 若含其他 exception → 保留并仅移除 `MemoryHubError`
6. 运行：`cd backend && python -m pytest tests/ -x -q`（必须全绿）
7. 运行：`git diff --stat`

**交付**:
- 新文件路径
- 更新后的引用清单
- 测试运行结果
- `git diff --stat`

**约束**: 不 commit/push；不修改 exception 行为；不引入新的 exception 类型；不改变 `service/exceptions.py` 中其他内容

---

## 4. 纪律与边界

### 4.1 PM 严格遵守

- 单线程派发：一次只 @ 一个 Worker，Worker @ 回 PM 后再派下一步
- 超时可主动确认 Worker 状态，但 Worker 不可用时必须上报 @user
- 不扩大授权范围：本计划仅含 D5-1~D5-3；D5-4（共享抽取器）需 @user 另行批准
- 不自行切换 Worker 或重新派发

### 4.2 Worker 严格遵守

- 仅响应 @pm-hy3 的指派，不响应群组内其他成员
- 完成或阻塞时 @pm-hy3，不 @user
- 不修改本计划范围外的文件
- 不 commit/push（另行授权）

### 4.3 验证

- 每步 Worker 必须运行测试并报告结果
- PM 收到回报后判断是否进入下一步
- @user 拥有最终验收权

---

## 5. 风险与回滚

| 风险 | 回滚策略 |
|---|---|
| D5-2 测试失败 | 不提交变更，`git checkout` 恢复，由 PM 上报 @user |
| D5-3 测试失败 | 同上 |
| Worker 不可用 | PM 上报 @user 等待整备 |
| evolution 业务行为变化 | 立即停止并上报（违反"不重写逻辑"约束） |

---

## 6. 待 @user 裁决

1. **是否批准 Step 1（D5-1 调查）立即执行？**
2. **是否预先批准 Step 2/Step 3 的执行框架**（仍需每步单独 @ 确认）？
3. **D5-4 共享抽取器是否纳入本计划？**（当前建议：不纳入）
4. **Worker 选派**：D5-1 用 @arch-laguna，D5-2/D5-3 用 @agnes-worker —— 是否同意？
5. **路径假设**：本计划所有路径基于已核实事实，是否需要进一步核实？

**批准后**，PM 将立即派 @arch-laguna 启动 Step 1。
