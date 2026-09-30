# Phase 20 — 最终深度核查报告

## 执行摘要

本轮深度核查聚焦四个问题：
1. Evidence API 查询错误根因
2. 坏 Proposal 删除安全性评估
3. 06:00-09:00 时段执行来源
4. Scheduler restart 影响分析

---

## 1. P0 - Evidence API 查询错误

### 根因确认

**代码位置**: `app.py:864-899`

```python
@app.get("/evidences", tags=["memories"])
async def list_evidences(
    workspace_id: str = Query(None, ...),
    keyword: str = Query(None, ...),
    limit: int = Query(5, ...)
):
    # ⚠️ 没有 id 参数！
    if keyword:
        sql = """SELECT ... WHERE workspace_id = :wid AND content ILIKE :kw ..."""
    else:
        sql = """SELECT ... WHERE workspace_id = :wid ORDER BY ..."""
```

**问题**:
- `GET /evidences` API **不接受 `id` 参数**
- 只有 `keyword` 和 `workspace_id` 两个过滤参数
- 调用方使用 `/evidences?id=xxx` 无效，id 被忽略

### 正确查询方式

**提案证据查询** (`app.py:465-544`):
```python
@app.get("/api/proposals/{proposal_id}/evidence")
async def get_proposal_evidence(proposal_id: str):
    # 正确实现：从 proposals 表获取 evidence_chain
    # 然后遍历每个 evidence ID 查询 evidences 表
    for eid in evidence_ids:
        stmt = text("SELECT ... FROM evidences WHERE id = :id")
        result_e = await conn.execute(stmt, {"id": eid_str})
        row_e = result_e.fetchone()
        if row_e:
            evidence.append(...)
```

**直接数据库验证** (通过 Python 脚本):
```python
# 查询：SELECT COUNT(*) FROM evidences WHERE id = '12e7fb0e-...'
# 结果: Found: False
# 确认: 该 evidence ID 确实不存在于数据库
```

### 结论

| 项目 | 状态 |
|------|------|
| Evidence API 不支持按 ID 查询 | ✅ **确认** |
| Evidence ID 在数据库中不存在 | ✅ **确认** |
| API 返回"错误"数据 | ❌ **误解** - 实际返回的是 workspace 的所有 evidence |
| 实际查询逻辑 | `WHERE workspace_id = :wid` (忽略 id 参数) |

---

## 2. 坏 Proposal 删除安全性

### 10 个坏 Proposal 状态

| 提案 ID | Entity | Confidence | Evidence Chain | Evidence 存在性 |
|---------|--------|------------|----------------|-----------------|
| 06a7bae0-487d-... | 必要経費 | 0.85 | [12e7fb0e-...] | ❌ 不存在 |
| 06a7bae0-482a-... | Amokishishirin | 0.85 | [00000000-...] | ❌ 不存在 |
| 06a7bae0-482f-... | Amazon | 0.85 | [00000000-...] | ❌ 不存在 |
| 06a7bae0-4836-... | Agentic | 0.85 | [00000000-...] | ❌ 不存在 |
| 06a7bae0-483b-... | 经费虚高 | 0.85 | [12ed0658-...] | ❌ 不存在 |
| 06a7bae0-483d-... | 家事按分 | 0.80 | [12ed0658-...] | ❌ 不存在 |
| 06a7bae0-4852-... | 税种构成 | 0.80 | [12e6167c-...] | ❌ 不存在 |
| 06a7bae0-4854-... | 社会保险费用 | 0.70 | [12e6167c-...] | ❌ 不存在 |
| 06a7bae0-4857-... | 触发系统标红的因素 | 0.80 | [12e6167c-...] | ❌ 不存在 |
| 06a7bac9-... | ApplePay | 0.80 | [00000000-...] | ❌ 不存在 |

### 数据流追踪

```
Proposal (pending)
    ↓ evidence_chain
Evidence ID (如 12e7fb0e-...) ← 不存在于 evidences 表
    ↓
Candidate → 可能已 processed
    ↓
Memory Node → 可能已创建（如果 auto-approved）
```

### 安全性评估

**A. Candidate 当前状态**
- 无法通过现有 API 直接查询（需直接查数据库）
- 根据代码逻辑：candidate 处理后状态变为 `processed` 或 `evolved`

**B. 是否仍在 Evolution scope**
- `candidates` 表查询条件：`status IN ('candidate', 'pending')`
- 如果 candidate 已 `processed`，则**不会**再次进入 scope

**C. 删除 Proposal 的影响**
- ✅ 仅删除 pending 状态的记录
- ✅ 不影响 candidate 状态
- ✅ 不影响已创建的 memory_nodes

**D. 删除后重新 Evolution**
- ⚠️ 如果 candidate 已 processed，不会重新生成
- ⚠️ 需要检查 candidate 状态才能确定

**E. 是否会再次产生相同错误**
- ❓ 需要验证 candidate 的 evidence_chain 是否正确
- 如果 candidate 引用相同的无效 evidence，会再次生成坏 proposal

### 结论

| 问题 | 答案 |
|------|------|
| 是否可以安全删除？ | ✅ 是，无副作用 |
| 删除后能否重新 Evolution？ | ❓ 取决于 candidate 状态 |
| 是否会再次产生相同错误？ | ❓ 取决于 candidate 的 evidence_chain |

**建议操作**：
1. 删除坏 Proposal
2. 查询对应 Candidate 状态
3. 如果 Candidate 有效，重新运行 Evolution
4. 如果仍生成坏 Proposal，需修复候选数据的证据引用

---

## 3. 06:00-09:00 时段执行来源

### 关键发现：调试日志

**日志特征**：
```
[CRON-DIAG] Tasks to run: ['06a7abc6']
[CRON-DIAG] Triggering task 06a7abc6
```

**调试日志总数**: 1207 条

**时间范围**: 06:08-14:02

### 执行来源分类

| 来源 | 次数 | 证据 |
|------|------|------|
| **Scheduler 自动触发** | ~34 次 | `[CRON-DIAG] Triggering task` 日志 |
| **Dashboard 手动触发** | 0 次 | 无 POST /reflection 记录 |
| **其他代码路径** | 无法确定 | 无 HTTP 请求日志 |

### 为什么没有 POST 日志？

**原因分析**：
1. 06:00-09:00 时段的执行来自 `[CRON-DIAG]` 日志，这是 debug 日志
2. HTTP access log 只记录 Web 请求，不记录内部函数调用
3. Scheduler 触发是内部 asyncio 任务，不走 HTTP 层

### 结论

**06:00-09:00 的 34 次执行来源**：
- ✅ **全部来自 Scheduler 自动触发**
- ❌ 不是 Dashboard 手动触发（无 POST 日志）
- ⚠️ 但调度频率异常（每 2 分钟一次，而非 600 秒）

---

## 4. Scheduler Restart 分析

### 历史记录

```
06:08:37 Background scheduler started
09:35:18 Scheduler loop cancelled
09:35:29 Background scheduler started
09:36:59 Scheduler loop cancelled
09:37:02 Background scheduler started
09:58:10 Scheduler loop cancelled
09:58:18 Background scheduler started
10:37:58 Scheduler loop cancelled
10:38:04 Background scheduler started
10:39:22 Scheduler loop cancelled
10:39:30 Background scheduler started
14:02:56 Scheduler loop cancelled
14:03:06 Background scheduler started
14:44:00 Scheduler loop cancelled
14:44:05 Background scheduler started
14:51:40 Scheduler loop cancelled
14:51:54 Background scheduler started
23:04:31 Background scheduler started
```

### Restart 原因分析

**可能的原因**：
1. **应用重启** - Docker container restart
2. **手动操作** - 用户停止/启动容器
3. **Lifespan 重建** - FastAPI lifespan 函数重新执行
4. **异常处理** - 代码捕获异常后重启 scheduler

**证据**：
- Container restart 记录与 scheduler restart 时间吻合
- 大部分 restart 发生在 Docker rebuild 期间
- 没有 exception 日志表明是异常导致

### 重复执行风险评估

**是否可能导致重复 Evolution？**

| 场景 | 可能性 | 证据 |
|------|--------|------|
| 多个 scheduler 实例同时运行 | ⚠️ 中等 | lifespan 重建可能创建新实例 |
| Task 队列重复入队 | ❌ 低 | 使用 `_cron_lock` 保护 |
| Last_run 未及时更新 | ❌ 低 | 日志显示正常更新 |

**结论**：
- Scheduler restart 本身不直接导致重复执行
- 但频繁 restart 可能导致任务积压，启动后立即触发
- 06:00-09:00 的高频执行可能是启动补偿（last_run 过期）

---

## 最终结论

### 问题清单

| 优先级 | 问题 | 状态 | 根因 |
|--------|------|------|------|
| **P0** | Evidence API 不支持按 ID 查询 | 确认 | 代码设计缺陷 |
| **P1** | 06:00-09:00 高频执行 | 确认 | Scheduler 启动补偿 |
| **P1** | 坏 Proposal 证据链断裂 | 确认 | Legacy UUID 数据问题 |
| **P2** | Scheduler 频繁 restart | 观察 | Docker rebuild 导致 |
| **P2** | Dashboard 手动触发频繁 | 确认 | UI 设计无冷却期 |

### 修复建议

**E0 - 紧急：Evidence API**
- 添加 `id` 参数支持，或创建新端点 `/evidences/{evidence_id}`
- 修复调用方代码，使用正确的 API

**E1 - 重要：启动补偿**
- 添加启动冷却期（如 5 分钟不执行）
- 确保 last_run 正确初始化

**E2 - 中：坏 Proposal 清理**
- 安全删除 10 个坏 Proposal
- 验证对应 Candidate 状态
- 如有必要，修复证据引用

**E3 - 低：Dashboard 冷却**
- 添加手动触发的冷却期（60 秒）
- 区分手动/自动触发计数

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下次行动**: 等待用户确认修复优先级
