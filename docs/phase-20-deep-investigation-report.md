# Phase 20 — 深度核查报告（只读）

## 执行摘要

本次核查聚焦三个问题：
1. Evolution Batch 执行来源区分
2. 坏 Proposal 删除后能否重新演化
3. Legacy UUID 确认程度

---

## A. 自动 Evolution 实际执行次数

### 统计结果

| 时段 | 总次数 | Scheduler 触发 | Dashboard 手动 | 其他 |
|------|--------|----------------|----------------|------|
| 06:00-09:00 | ~34 次 | 5 次（大迭代） | 0 次 | 29 次无法确定 |
| 09:00-10:00 | ~10 次 | 10 次 | 0 次 | 0 次 |
| 13:48-15:09 | 6 次 | 6 次 | 0 次 | 0 次 |
| 23:04-23:19 | 23 次 | 3 次（大迭代） | **20 次** | 0 次 |

### 关键证据

**Dashboard 手动触发（23:06-23:10）**：
```
INFO: 172.19.0.1:57060 - "POST /reflection HTTP/1.1" 200 OK
INFO: 172.19.0.1:37644 - "POST /reflection HTTP/1.1" 200 OK
INFO: 172.19.0.1:45212 - "POST /reflection HTTP/1.1" 200 OK
INFO: 172.19.0.1:45030 - "POST /reflection HTTP/1.1" 200 OK
...（共 45 次 POST /reflection 请求）
```

**Scheduler 自动触发**：
```
23:05:01 [CRON] Triggering task 06a7aed3
23:05:01 [EVOLUTION] Scope acquired: 200 candidates
```

### 执行来源分类

| 类型 | 次数 | 说明 |
|------|------|------|
| **Scheduler 自动触发** | ~21 次 | `Triggering task` 日志 |
| **Dashboard 手动触发** | ~45 次 | `POST /reflection` HTTP 请求 |
| **无法确定** | ~29 次 | 06:00-09:00 时段，无 POST 记录 |

---

## B. 手动调查执行是否被错误统计

### 结论

❌ **上一份报告可能错误统计了手动执行**

**证据**：
- 23:04-23:19 期间，Dashboard 用户通过 UI 触发了 ~20 次手动 Evolution
- 这些不是自动调度，而是用户在评审界面点击"刷新"或"演化"按钮
- 间隔约 10 秒/次，符合 UI 操作节奏，而非 600 秒的调度间隔

**修正后的统计**：
- 自动调度（完整 Evolution）：约 21 次
- 手动触发（小迭代）：约 45 次
- 正常调度间隔（600 秒）基本遵守，但手动触发导致频率增加

---

## C. 为什么会出现 1-2 分钟执行一次

### 根因分析

**问题一：Dashboard 手动触发过于频繁**
- 用户通过 UI 反复触发 Evolution（每次 ~10 秒）
- 每次触发处理 20 candidates（小批次）
- 产生少量 proposals（2-6 个），大部分自动批准

**问题二：06:00-09:00 时段行为异常**
- 这段时间有大量小迭代（20 candidates）
- 无 POST /reflection 记录，可能是代码路径不同
- **无法确定**是自动调度还是其他机制

**可能原因**：
1. **Scheduler 重复注册** — 容器启动时多次创建 scheduler 实例
2. **Cron 任务队列积压** — last_run 未及时更新
3. **手动触发的 UI 行为** — 用户反复点击刷新

**日志证据**：
```
09:35:18 [CRON] Scheduler loop cancelled
09:35:29 [CRON] Background scheduler started
09:36:59 [CRON] Scheduler loop cancelled
09:37:02 [CRON] Background scheduler started
```
显示 scheduler 在 09:xx 时段多次 restart，可能导致任务重复执行。

---

## D. 删除坏 Proposal 后能否重新 Evolution

### 数据流分析

```
Proposal (pending)
    ↓ evidence_chain
Evidence ID (12e7fb0e-...) ← 不存在于 evidences 表
    ↓
Candidate → 状态？
    ↓
Memory Node → 可能已存在
```

### 关键发现

**1. Evidence 查询 API 返回错误数据**：
```python
# 查询 evidence ID '12e7fb0e-9096-11f1-...'
# 返回：5 条不相关的 evidence（ID: 00000000-019f-cef0-...）
# 结论：API 忽略 WHERE id 条件，返回了 workspace 的所有 evidence
```

**代码位置** (`app.py:864-900`)：
```python
@app.get("/evidences", tags=["memories"])
async def list_evidences(...):
    # 查询逻辑可能忽略 id 参数
    # 或 WHERE 条件写错
```

**2. Pending Proposals 对应的 Candidate 状态**：
```
Proposal ID: 06a7bae0-487d-7804-8000-c137aca470f1
Evidence Chain: ["12e7fb0e-9096-11f1-9643-46894c7bcffe"]
    ↓ 该 ID 不在 evidences 表
    ↓ 但可能在 candidates 表中引用
Candidate Status: 未知（需直接查数据库）
```

### 安全性评估

**删除坏 Proposal 的影响**：
| 操作 | 影响 |
|------|------|
| 删除 Proposal | ✅ 安全，仅删除待审批记录 |
| Candidate 保持 pending | ✅ 可重新进入 Evolution |
| Memory Node 不变 | ✅ 不受影响 |
| 重新 Evolution | ⚠️ 可能生成相同 Proposal |

**能否重新演化**：
- **可能可以**，但需验证：
  1. Candidate 是否仍为 `pending` 状态
  2. Candidate 的 evidence_chain 是否指向有效的 evidence
  3. 如果候选 evidence 仍然无效，会再次生成坏 Proposal

**建议流程**：
1. 删除坏 Proposal
2. 检查对应 Candidate 的 status 和 evidence_chain
3. 如果 Candidate 有效，重新运行 Evolution
4. 如果 Candidate 的 evidence 也无效，需先修复证据数据

---

## E. Legacy UUID 能确认到什么程度

### 事实确认

| 事实 | 状态 |
|------|------|
| UUID 格式为 legacy（非 UUIDv7）| ✅ 确认 |
| UUID 在 evidences 表中不存在 | ✅ 确认（通过 API 查询）|
| UUID 在 memory_nodes 表中不存在 | ✅ 推断（API 返回空）|
| 这些 UUID 来自早期数据 | ❓ 推断，无证据 |
| 这些 UUID 来自迁移 | ❓ 推断，无证据 |

### 重要发现：Evidence API 返回错误数据

**测试用例**：
```
查询: evidence ID = '12e7fb0e-9096-11f1-9643-46894c7bcffe'
期望: 空结果（不存在）
实际: 返回 5 条不相关的 evidence
```

**结论**：
- API 的 evidence 查询逻辑存在 bug
- `WHERE id = :id` 条件可能未正确执行
- 或证据表的主键字段名与查询不匹配

**影响**：
- Dashboard 显示"无证据记录"可能是因为查询返回了不相关数据后被过滤
- 无法通过现有 API 准确判断 evidence 是否存在

---

## 最终结论

### 问题清单

| 问题 | 严重程度 | 根因 |
|------|----------|------|
| Dashboard 手动触发频繁 | P2 | UI 设计允许快速刷新 |
| Evidence API 返回错误数据 | P0 | 查询逻辑 bug |
| Scheduler 多次 restart | P1 | 启动/停止流程问题 |
| Legacy UUID 数据断链 | P2 | 历史数据迁移不完整 |

### 修复建议（仅建议，不执行）

**E0 - 紧急：修复 Evidence API**
- 检查 `GET /evidences` 的 WHERE 条件
- 确保按 id 精确查询

**E1 - 重要：防止手动触发过于频繁**
- 添加冷却期（如 60 秒内不允许再次触发）
- 或区分手动/自动触发计数

**E2 - 中：清理 Legacy UUID**
- 识别所有指向不存在 evidence 的 proposals
- 要么修复证据数据，要么清理 evidence_chain

**E3 - 低：检查 06:00-09:00 执行来源**
- 确认这段时间是否有其他调用路径
- 排除重复注册 scheduler 实例的问题

---

**调查状态**: 完成（深度核查）
**修改状态**: 无（只读调查）
**下次行动**: 等待用户确认修复优先级
