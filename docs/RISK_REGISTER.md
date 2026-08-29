# Personal Memory Hub — Risk Register

**状态**：ACTIVE  
**基线版本**：Step 1 验收后 (2026-08-28)  
**维护者**：@review-nemo（验证后落盘），后续由 PM 更新

---

## 1. 当前验收基线（Step 1 PASS / LOCK）

| 项目 | 结果 | 证据 |
|------|------|------|
| **全量测试** | 703 passed / 0 failed / 8 skipped（PG 环境） | `uv run pytest` 实跑 |
| **Alembic 从零库可复现** | 001_initial → 002 → 003 → 004 真实执行成功，19 表落地，`alembic_version=004_add_topics` | `uv run alembic upgrade head`（online，非 dry-run） |
| **零生产行为变更** | `git diff` 仅 8 个测试文件（220+/108-），全为断言/导入/mock 修复 | `git diff --stat` |
| **workspace_id 真实 bug 隔离** | 保留为 BUG-WS1，未纳入 Step 1 | 计划文档标记 |

---

## 2. 已验证风险登记（按严重度）

### P0 — 必须在后续 Phase 解决

| ID | 风险 | 影响 | 发现来源 | 状态 |
|----|------|------|----------|------|
| **R-001** | **Alembic baseline 缺 001_initial**（已修复） | 此前 schema 不可从零复现 | Step 1 前 | ✅ **已闭环**（Step 1 手写 001_initial） |
| **R-002** | **CI 强依赖 PostgreSQL** | 无 PG 即红；`003/004` 使用 `postgresql.JSONB()/UUID()`，`env.py` 无 sqlite 分支；GitHub Actions 需配 PG service | Step 1 验证 | 🟡 记录，待 CI 配置 |
| **R-003** | **`.env` 的 `DATABASE_URL` 不生效** | Settings 前缀为 `PMH_`，实际需 `PMH_DATABASE_URL`；当前 `.env` 写的是无前缀键 | Step 1 验证 | 🟡 记录，待修正 |

### P1 — 架构一致性风险

| ID | 风险 | 影响 | 发现来源 | 状态 |
|----|------|------|----------|------|
| **R-004** | **Dual `_extract_facts()` 并存** | `evidence_evolution_engine.py:160` 与 `reflection_engine.py:141` 各有一个；可能双重 LLM 调用、候选重复、source_level 污染 | Step 1 前 + 验证 | 🟢 记录，Step 2 处理 |
| **R-005** | **source_level 三处默认值不一致** | `reflection_service.py:1000` 默认 2 / `:1190` 取 `level` 默认 2 / `:1305` 默认 1 —— 候选/提案层级决策不可信 | Step 1 前 + 验证 | 🟢 记录，Step 2 处理 |
| **R-006** | **D5 层边界系统性越界** | `app.py`/`cli.py`/cron 直连 repo/engine；`service↔ingest` 双向依赖；`service→context`；`evolution→repo` 直连 | arch-laguna 侦察 + 验证 | 🟢 记录，Step 2 处理 |
| **R-007** | **BUG-WS1：`EvidencePipelineService._interpret` 未透传 `workspace_id`** | 导致解释器无 workspace 上下文；测试曾被放宽断言掩盖（假绿） | Step 1 验证 | 🔴 **冻结**，待单独授权修复 |
| **R-008** | **覆盖率仅 15.41%**（15,772 evidences / 2,431 candidates） | 大量证据未演化为候选，记忆系统核心价值未释放 | agnes-worker 报告 | 🟢 记录，**先修 baseline 再提升** |

### P2 — 运维/卫生风险

| ID | 风险 | 影响 | 发现来源 | 状态 |
|----|------|------|----------|------|
| **R-009** | **159 未跟踪脚本/报告污染仓库** | `backend/scripts/rebuild_phase*.py`、`backend/scripts/phase24_c_*.py`、`docs/diagnostic-report-*.md` 等 | agnes-worker 报告 | 🟢 记录，后续清理 |
| **R-010** | **schema 细节：`areas.parent_area_id` / `entities.parent_entity_id` 标 `nullable=False` 却 `ON DELETE SET NULL`** | 逻辑矛盾；建议后续迁移改 `nullable=True` | 001_initial 审查 | 🟢 记录，后续迁移修正 |
| **R-011** | **`proposals` 表主键 String vs `candidate_id` UUID 异构** | 001 用 String PK，002 加 UUID FK，类型不一致 | 001/002 对比 | 🟢 记录，不阻塞 |

---

## 3. 已明确移除的风险（Step 1 验证中被证伪）

| 原风险 | 验证结果 | 备注 |
|--------|----------|------|
| `candidate_id` 血统断裂（Proposal 写入时不填） | **FALSE** | Phase 26-G-B.6 已修复：`ProposalRepository` 与 `reflection_service.py` 均写入 `candidate_id` |
| `alembic/env.py` 为裸 raw SQL | **FALSE** | 正确 `import backend...engine.Base` + `target_metadata = Base.metadata` |

---

## 4. 后续执行序列（已与 @user 确认）

```
STEP_1 = PASS / LOCK
    ↓
RISK_REGISTER.md 落盘（本文档）     ← 当前
    ↓
临时验证库清理（已完成）
    ↓
重新汇报
    ↓
等待 @user 决定 BUG-WS1 (R-007)
    ↓
之后才考虑 Step 2 (R-004/005/006)
    ↓
覆盖率提升 (R-008) / 清理 (R-009) / CI 修正 (R-002/003) / schema 细节 (R-010/011)
```

---

## 5. 变更记录

| 日期 | 版本 | 变更 | 作者 |
|------|------|------|------|
| 2026-08-28 | 1.0 | 初版：基于 Step 1 验收结果落盘 | @review-nemo |

---

> **注**：本登记仅记录**已验证**风险。未经验证的推测不入表。后续每轮验收后由 PM 更新，保持与代码/测试/文档三方一致。