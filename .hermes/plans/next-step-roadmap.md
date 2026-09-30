# M6 后项目阶段裁决 / Next-Step Roadmap

**状态**: PM 计划裁决（仅文档；未派 Worker；未实施；未 commit/push）
**生成时间**: 2026-09-07
**生成者**: @pm-hy3
**基准**: Git HEAD = `1f24c9e` @ `origin/main`
**前置**: M6 FINAL CLOSED / LOCKED @ `1f24c9e2de0af800b9ca84a4c339ad2a4cd22769`

---

## 1. 当前项目状态（事实基线）

### 1.1 Git 状态

| 项 | 值 |
|---|---|
| **HEAD** | `1f24c9e` M6: shared multimodal text extractor consolidation |
| **origin/main** | `1f24c9e`（一致）|
| **HEAD == origin/main** | ✅ |
| **tracked working tree** | clean |
| **untracked（168 个）** | D5/phase 历史 + `.hermes/plans/` + 各种诊断/脚本（不入 Git）|

### 1.2 最近 10 commits

```
1f24c9e M6: shared multimodal text extractor consolidation
0e4cf20 D5-3: MemoryHubError migration documentation completion
bc65e96 D5-2: evolution service migration / restructure
86910e2 P0-2: Change proposals.source_level to Integer + migration
32e9577 P0-1: Remove source_level from candidates INSERT
58ff5cb BUG-WS1: propagate workspace_id to semantic interpreter
7a9f649 Step 1: add 001_initial baseline migration and fix 53 red tests
eb9cadb docs: sync project phase status navigation
d468271 feat: Phase 26-G-B.6 entity resolution fix and evolution pipeline
655c00b docs: lock Phase 26-G-B.6 final rebuild validation
```

### 1.3 `.hermes/plans/` 内容（PM 工作目录，不入 Git）

| 文件 | 状态 |
|---|---|
| `d5-1-investigation-report.md` | D5-1 调查完成（已 LOCKED）|
| `d5-2-task-definition.md` | D5-2 任务定义 |
| `d5-2-execution-record.md` | D5-2 执行记录（LOCKED）|
| `d5-3-task-definition.md` | D5-3 任务定义 |
| `d5-3-execution-report.md` | D5-3 执行报告（LOCKED）|
| `d5-series-restructure-plan.md` | D5 系列重组计划 |
| `m1-m3-m6-investigation-report.md` | M1/M3/M6 调查 |
| `m6-task-definition.md` | M6 任务定义 v3 |
| `m6-execution-report.md` | M6 执行报告（FINAL CLOSED）|

---

## 2. 已完成阶段（LOCKED）

| 阶段 | 状态 | 落地 commit |
|---|---|---|
| **Phase 26-G-B.6** | LOCKED | `d468271` / `655c00b` |
| **P0-1 修复** | LOCKED | `32e9577` |
| **P0-2 修复** | LOCKED | `86910e2` |
| **BUG-WS1** | LOCKED | `58ff5cb` |
| **D5-2 evolution/ 迁移** | FINAL CLOSED / LOCKED | `bc65e96` |
| **D5-3 MemoryHubError 迁移** | FINAL CLOSED / LOCKED | `0e4cf20` |
| **M6 共享抽取器合并** | FINAL CLOSED / LOCKED | `1f24c9e` |

**当前累计 LOCKED 阶段**: 6 个 D5/Phase 阶段 + M6 实施，共 7 个 LOCKED 节点。

---

## 3. 未完成 / 仍存在的事项

### 3.1 已定义但未授权实施

| 项 | 来源 | 状态 |
|---|---|---|
| **M1 — composition root 拆分** | m1-m3-m6-investigation-report.md §6 | 用户已明确"暂不实施"|
| **M3 — 编排层重构** | m1-m3-m6-investigation-report.md §6 | 用户已明确"暂不实施"|
| **MemoryService God Service 拆分** | m1-m3-m6-investigation-report.md §6 | 用户明确"另立独立任务"|
| **M3 Controlled Defrost** | 用户裁决 | 需另立任务 |
| **D5-3 Step 3 hardening** | d5-3-task-definition.md | 方案 A（不执行）|
| **FormationPipeline deprecation 退役时间** | d5-3-task-definition.md | 暂无 major version |
| **`test_entry_layer.py` uuid_extensions 缺失** | Step 4 实际发现 | 单独 ADR 任务（用户已标注）|

### 3.2 不在 D5/M 范围但存在的事项

- **`docs/05_Implementation/D6_Architecture_Verification_and_Implementation_Readiness.md`** — 阶段 D6 已存在但未在本次 PMH 主线推进
- 各种 `phase*.md` / `rebuild_phase*.py` 历史脚本（untracked）
- 各种 `dryrun_26gb*.py` 临时脚本（untracked）

---

## 4. 计划文档与实际 Git 状态一致性

| 计划文档 | 实际状态 | 一致？ |
|---|---|---|
| `d5-series-restructure-plan.md` | D5-2 + D5-3 已落地 | ✅ 文档与实际一致 |
| `d5-3-task-definition.md` | Step 1/2/4/5 LOCKED；Step 3 NOT EXECUTED | ✅ 文档已记录 |
| `m6-task-definition.md` v3 | M6 实施 LOCKED | ✅ |
| `m6-execution-report.md` | 完整记录 Step 1-6 实际 | ✅ |

**结论**: 计划文档与 Git 状态**完全一致**，无悬空任务。

---

## 5. 下一阶段候选分析

### 5.1 候选 1 — M1（composition root 拆分）

| 维度 | 评估 |
|---|---|
| **来源** | m1-m3-m6-investigation-report.md §6 |
| **复杂度** | 中（2032 行 → 拆分 HTTP endpoint + DI 工厂）|
| **风险** | 中（HTTP 端点响应不变，DI 调整可能影响 test_entry_layer）|
| **Frozen 影响** | 可能需要 Controlled Defrost（HTTP endpoint 边界）|
| **依赖** | 无前置；M6 已完成共享 helper 抽取 |
| **用户态度** | "**M1：暂不实施。Composition Root / app.py 拆分另行授权**"（明确不实施）|

**结论**: **用户明确不实施**，本轮 Roadmap 不应作为推荐。

### 5.2 候选 2 — M3（编排层重构）

| 维度 | 评估 |
|---|---|
| **来源** | m1-m3-m6-investigation-report.md §6 |
| **复杂度** | 高（涉及 Service 内部重构、Controlled Defrost、ADR）|
| **风险** | 高（编排层变更可能影响 evidence pipeline / evolution pipeline）|
| **Frozen 影响** | **必须 Controlled Defrost** |
| **依赖** | 需先有 ADR；需冻结定义 |
| **用户态度** | "**M3：暂不实施**... 保持 process_evidence 签名与 Pipeline 拓扑不变"（明确不实施 + 额外约束）|

**结论**: **用户明确不实施 + 额外约束**（保持签名与拓扑），本轮 Roadmap 不应作为推荐。

### 5.3 候选 3 — MemoryService 拆分（用户已明确"另立独立任务"）

| 维度 | 评估 |
|---|---|
| **来源** | m1-m3-m6-investigation-report.md §6（用户裁决）|
| **复杂度** | 高（9 个依赖项，God Service 拆分需要谨慎）|
| **风险** | 高（影响所有使用 MemoryService 的调用点）|
| **Frozen 影响** | 需 Controlled Defrost + ADR |
| **依赖** | 需先有完整 task definition；需 Phase 21 配合 |
| **用户态度** | "**另立独立任务**"（明确划出 M1 范围，需独立 task definition + 独立授权）|

**结论**: **用户已划为独立任务**，需独立 task definition 后再授权。本次不应作为下一步推荐。

### 5.4 候选 4 — D6 Architecture Verification

| 维度 | 评估 |
|---|---|
| **来源** | `docs/05_Implementation/D6_Architecture_Verification_and_Implementation_Readiness.md` |
| **复杂度** | 待评估 |
| **风险** | 待评估 |
| **用户态度** | 本次 PMH 主线未明确涉及 D6 |

**结论**: 用户未在 PMH 主线明确启动 D6。

### 5.5 候选 5 — Phase 21 formation 重构

| 维度 | 评估 |
|---|---|
| **来源** | d5-3-task-definition.md 历史提及；用户裁决"FormationPipeline 当前只允许规划为 deprecated + 保留" |
| **复杂度** | 高 |
| **风险** | 高（影响 evolution 业务）|
| **用户态度** | "**暂不决定 major version 删除时间**"（不紧迫）|

**结论**: **不紧迫**，不推荐为下一阶段。

### 5.6 候选 6 — `test_entry_layer.py` uuid_extensions 依赖修复

| 维度 | 评估 |
|---|---|
| **来源** | M6 Step 4 PM 实测发现；用户已标注 |
| **复杂度** | 低（添加依赖到 pyproject.toml）|
| **风险** | 低（仅补依赖）|
| **Frozen 影响** | 无 |
| **依赖** | 无 |
| **价值** | 恢复全量测试可见性（当前 825 passed 但仍有 22 错误基线未覆盖）|

**结论**: **低风险、低复杂度**，但**用户未明确授权**——建议作为独立可选项。

### 5.7 候选 7 — M6-EX 后续清理 / M6 文档归档

| 维度 | 评估 |
|---|---|
| **来源** | M6 FINAL CLOSED 后自然延伸 |
| **复杂度** | 低（删除 `.hermes/plans/m6-execution-report.md` 已无需；或归档历史 untracked）|
| **风险** | 低 |
| **价值** | 清理工作目录，便于后续 task definition 编排 |

**结论**: 不构成"实施阶段"，是**运维**。

---

## 6. 推荐下一阶段

### ⚠️ 关键判断

按用户 PMH 主线历程（Phase 26-G → P0-1/P0-2 → BUG-WS1 → D5-2 → D5-3 → M6），**主要技术债已基本清理**：
- D5-2 重组完成
- D5-3 MemoryHubError 集中完成
- M6 共享抽取器去重完成

**M1 / M3 / MemoryService 拆分已被用户明确"暂不实施"**——这是有意识的"刹车"。

### 推荐：暂不启动新实施阶段

**理由**：
1. 用户对 M1 / M3 / MemoryService 拆分**有意识的暂缓**——非技术阻塞，是 PM 决策
2. Phase 21 formation 重构用户也"暂不决定"——非紧迫
3. M6 完成后**没有强紧迫的下游任务**
4. Worker 纪律问题（review-nemo 5 次 / agnes-worker 4 次 / @coder-ox 1 次）需要**先行治理**，避免下一阶段继续失序
5. D6 / Phase 21 / MemoryService 拆分需要**独立 task definition 起草 + 独立授权**才能启动

### 推荐方案：A. PM 暂缓 + 计划裁决归档

| 阶段 | 任务 | 授权 |
|---|---|---|
| **A. 计划裁决归档** | 把本 Roadmap 落到 `.hermes/plans/next-step-roadmap.md` | 已在执行（本文档）|
| **B. Worker 纪律治理** | 用户裁决：是否群组通报 review-nemo / agnes-worker / @coder-ox 越权 | 待用户裁决 |
| **C. 等待下一阶段授权** | 任何新阶段（M1 / M3 / MemoryService / D6 / Phase 21 / uuid_extensions 修）均需独立 task definition + 独立授权 | 待用户启动 |

### 备选方案（如用户有具体偏好）

| 备选 | 启动条件 |
|---|---|
| **B1. MemoryService 拆分独立任务定义** | 用户授权"启动 MemoryService 独立 task definition 起草" |
| **B2. M1 task definition 独立起草** | 用户授权"启动 M1 独立 task definition 起草" |
| **B3. M3 task definition 独立起草 + ADR 起草** | 用户授权"启动 M3 独立 task definition + Controlled Defrost ADR 起草" |
| **B4. D6 启动** | 用户授权"启动 D6" |
| **B5. uuid_extensions 依赖补齐** | 用户授权"补齐 uuid_extensions + 验证 test_entry_layer.py 全绿" |
| **B6. Phase 21 formation 重构** | 用户授权"启动 Phase 21 formation 重构 task definition" |

---

## 7. 推荐方案 C 的目标与范围

### 目标
- 把 Roadmap 文档落地到 `.hermes/plans/next-step-roadmap.md`
- 不派 Worker
- 不实施
- 不 commit/push
- 等待用户对下一阶段（或 Worker 纪律治理）的明确授权

### 预计 Step 结构
无实施 Step——仅是文档归档（Step 1）+ 等待授权（Step 2）。

---

## 8. 依赖关系

| 项 | 依赖 |
|---|---|
| Roadmap 文档归档 | 无（独立 PM 任务）|
| Worker 纪律治理 | 需用户裁决 |
| 任何新实施阶段 | 需独立 task definition 起草 + 独立授权 |
| M1 / M3 / MemoryService | 需先有完整 task definition + 用户显式授权 |
| uuid_extensions 修复 | 需用户显式授权（无前置）|
| Phase 21 formation | 需先有完整 task definition + 用户显式授权 |

---

## 9. 风险 / 阻塞项

| 风险 | 状态 | 缓解 |
|---|---|---|
| M1/M3/MemoryService 拆分被遗忘 | 用户已明确"暂不实施" | Roadmap 文档记录在案；用户重新启动时引用 |
| Worker 纪律持续违规 | review-nemo 5 + agnes-worker 4 + coder-ox 1 | 待用户裁决通报 / 暂停发言权 |
| test_entry_layer.py 持续 ignore | 缺 uuid_extensions | 备选 B5 待用户授权 |
| D6 / Phase 21 无明确启动信号 | 用户未在本轮 PMH 主线涉及 | Roadmap 记录备选；用户启动时再行编排 |
| 168 个 untracked 文件累积 | 持续历史 | 不在 PMH 范围；可由用户单独清理 |

---

## 10. 是否需要用户授权

| 行动 | 是否需要用户授权 |
|---|---|
| Roadmap 文档归档（本文档落地）| **否**（PM 自我工作记录）|
| Worker 纪律治理 | **是**（需用户裁决）|
| 任何新实施阶段 | **是**（需独立 task definition + 独立授权）|
| 任何 commit/push | **是**（需用户授权，与 M6 一样）|

---

## 11. NEXT_AUTHORIZATION_REQUIRED

```
NEXT_AUTHORIZATION_REQUIRED = YES
```

### 等待用户授权以下任一项

1. **Worker 纪律通报**（review-nemo / agnes-worker / @coder-ox 越权记录是否群组通报）
2. **下一阶段选择**：
   - (a) 暂缓新实施，等待用户后续指令（推荐）
   - (b) 启动 MemoryService 拆分独立 task definition
   - (c) 启动 M1 独立 task definition
   - (d) 启动 M3 独立 task definition + Controlled Defrost ADR
   - (e) 启动 D6
   - (f) 补齐 uuid_extensions 依赖
   - (g) 启动 Phase 21 formation 重构 task definition
   - (h) 其它（用户指定）

### 严格纪律重申

- **PM → 一个 Worker → PM → 下一个 Worker**（不并行）
- **不擅自启动新阶段**
- **不擅自 commit/push**
- **不擅自修改业务代码 / 测试 / docs**

PM 严格按授权边界执行，Worker 全部停止，等待用户裁决。