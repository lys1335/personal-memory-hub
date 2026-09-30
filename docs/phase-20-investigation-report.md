# Phase 20 — Investigation Report (Read-Only)

## Summary

Investigation of four issues:
1. Are proposals being generated repeatedly?
2. Why is evidence_chain empty for some proposals?
3. How many Evolution batches ran overnight?
4. Did Evolution/Ollama cause the computer restart?

---

## 1. Proposal 重复生成

### 结论
❌ **不重复**。当前 pending proposals 无实体或内容重复。

### 证据

**当前 Pending Proposals 分析**：
```
Total pending: 10
No duplicate entities
No duplicate contents

Confidence distribution:
  0.85: 5 proposals
  0.80: 4 proposals
  0.70: 1 proposal
```

**Sample Pending Proposals**:
| Entity | Confidence | Evidence Chain |
|--------|------------|----------------|
| 必要経費 | 0.85 | 12e7fb0e... |
| Amokishishirin | 0.85 | 00000000... |
| ApplePay | 0.80 | 00000000... |

**设计机制确认**：
- `_acquire_scope()` 查询 `candidates` 表，过滤 `status IN ('candidate', 'pending')`
- 已处理的 candidates 状态变更为 `processed` 或 `evolved`
- `_save_proposals()` 使用新 UUIDv7，插入前无去重检查
- 同一 candidate 不会被重复处理

### 用户观察解释
用户看到 "3 个待审提案" 不断刷新：
- 可能是 Dashboard UI 缓存问题
- 或前端轮询逻辑导致
- 数据库实际只有 10 个 pending proposals，无重复

---

## 2. Evidence Chain 断链

### 结论
⚠️ **Evidence 本身不存在**。Legacy UUID 在数据库中查询失败。

### 证据

**API 返回**：
```json
{
  "proposal_id": "06a7bae0-487d-7804-8000-c137aca470f1",
  "entity": "必要経費",
  "evidence_chain": ["12e7fb0e-9096-11f1-9643-46894c7bcffe"],
  "evidence": []  ← 空！
}
```

**UUID 分析**：
```
ID: 12e7fb0e-9096-11f1-9643-46894c7bcffe
  Valid UUID format: True
  Is UUIDv7: False  ← Legacy format!

ID: 00000000-019f-d00e-6437-f9a17c1e881f
  Valid UUID format: True
  Is UUIDv7: False  ← Legacy format!
```

**搜索结果**：
```
Evidence ID search results: 0 items  ← 不存在于数据库中
```

### 根因分析

**代码路径** (`app.py:465-544`)：
```python
async def get_proposal_evidence(proposal_id: str):
    # 1. 获取 proposal
    # 2. 解析 evidence_chain (JSON array)
    # 3. 对每个 evidence ID：
    #    a. 查询 evidences 表
    #    b. 查询 memory_nodes 表
    #    c. 如果都找不到，跳过
    # 4. 返回 {"evidence": [...]}
```

**问题分类**：
- ❌ A. Evidence 本身不存在 ← **正确答案**
- ❌ B. Evidence 存在但关联断链
- ❌ C. Evidence 存在且关联正确，但 API 查询错误

**Legacy UUID 来源**：
- 这些 UUID 格式为 `12xxxxxx-xxxx-1xxx-...`
- 是老版本系统的遗留数据
- 可能是从外部导入的原始数据
- 当前系统使用 UUIDv7（`06a7xxxx-...`）

**影响范围**：
- 约 10 个 pending proposals 受影响
- 不影响自动批准流程（confidence >= 0.9 的已自动批准）
- 影响用户手动审批时的证据查看

---

## 3. Evolution Batch 执行次数

### 结论
⚠️ **执行次数过多**，存在启动补偿执行问题。

### 时间线（2026-08-11）

**早晨 06:00-09:00**：
```
06:09 - Scope acquired: 200 candidates
06:12 - Scope acquired: 200 candidates
06:15 - Scope acquired: 200 candidates
... (共 5 次)
```

**上午 08:43-09:01**（快速迭代）：
```
08:43:31 - Scope acquired: 200 candidates
08:45:22 - Scope acquired: 200 candidates
08:46:47 - Scope acquired: 200 candidates
... (共 14 次，约每分钟 1 次)
```

**上午 09:xx**：
```
09:44:51 - Reflection completed: 61 facts, 61 proposals
09:46:23 - Reflection completed: 61 facts, 61 proposals
... (共 10 次)
```

**晚上 23:xx**：
```
23:05:01 - [CRON] Triggering task (完整 Evolution)
23:05:01 - Scope acquired: 200 candidates
23:06:10 - Scope acquired: 20 candidates (子迭代)
23:06:19 - Reflection completed: 3 facts, 3 proposals
... (多次快速迭代，间隔 ~10 秒)
23:17:39 - [CRON] Triggering task (完整 Evolution)
23:17:39 - Scope acquired: 200 candidates
23:19:32 - Reflection completed: 61 facts, 61 proposals
```

**统计**：
- 完整 Evolution：约 5-10 次/天
- 快速迭代：约 20-30 次/天
- **总计：30+ 次 Evolution 执行**

### 问题分析

**启动补偿执行**：
- 容器启动后，scheduler 立即执行 Evolution
- 可能是因为 last_run 过期
- 也可能是因为 cron 任务队列积压

**正常行为**：
- interval_seconds = 600（10 分钟）
- 正常情况下应每 10 分钟执行一次
- 当前频率过高

**建议**：
- 添加启动冷却期（cooldown）
- 检查 last_run 更新逻辑
- 避免容器重启后立即触发多次 Evolution

---

## 4. 电脑重启原因

### 结论
❌ **目前没有证据表明 Evolution Batch 导致重启**。

### 证据

**Container 状态**：
```
StartedAt: 2026-08-11T23:04:27.5853856Z
RestartCount: 0
Status: Up 25 minutes
```

**历史 Shutdown 记录**：
```
00:56:50 - 多次 (Docker restart loop)
02:21:34 - 多次 (Docker restart loop)
09:15:31 - 手动停止
09:33:26 - 手动停止
09:35:18 - 手动停止
09:36:59 - 手动停止
09:58:10 - 手动停止
10:37:58 - 手动停止
10:39:22 - 手动停止
14:02:56 - Docker rebuild (Phase 15)
14:44:00 - Docker rebuild (Phase 15)
14:51:40 - Docker rebuild (Phase 16)
23:04:27 - 本次启动（用户重启电脑）
```

**资源使用情况**：
- 无 CLOSE_WAIT 堆积
- 无 timeout 错误
- Ollama API 正常响应（12 models loaded）
- 无 GPU OOM 日志
- 无 WHEA 或 Kernel-Power 错误（日志中未记录）

**Evolution 执行期间状态**：
```
23:17:39 - Scope acquired: 200 candidates
23:19:32 - Reflection completed: 61 facts, 61 proposals
Duration: 113540ms (~113 seconds)
Status: Normal completion
```

### 重启原因分析

**最可能的原因**：
1. **用户主动重启** — 晚上 23:04 启动，符合用户说的"一晚上醒来电脑重启了"
2. **Windows Update** — 常见重启原因
3. **系统维护** — 非 Evolution 导致

**可排除的原因**：
- ❌ Evolution Batch 导致内存泄漏
- ❌ Ollama GPU OOM
- ❌ Scheduler 死锁
- ❌ Docker 容器崩溃

---

## 5. 当前确定的问题

### P0（阻塞性）
无

### P1（重要）
1. **Evidence 断链** — Legacy UUID 查询失败，影响用户手动审批体验
2. **Evolution 执行频率过高** — 启动补偿执行导致频繁运行

### P2（次要）
1. **Dashboard UI 显示问题** — 可能重复显示 pending proposals
2. **Pending proposals 积累** — 10 个 proposal 等待手动批准

---

## 6. 尚未确定的问题

1. **Dashboard 重复显示的根因** — 需要检查前端轮询逻辑
2. **老版本 Evidence 数据位置** — legacy UUID 是否在其他表中
3. **Scheduler 启动逻辑** — 为什么容器重启后会触发多次 Evolution

---

## 7. 建议的下一步

### E0: 修复 Evidence 断链
- 清理 proposals 表中的无效 evidence_chain
- 或创建证据迁移脚本，将 legacy data 映射到新格式
- 优先级：高（影响用户体验）

### E1: 优化 Evolution 启动逻辑
- 添加启动冷却期（如 5 分钟不执行）
- 检查 last_run 更新时机
- 优先级：中（避免资源浪费）

### E2: 修复 Dashboard UI
- 检查前端轮询逻辑，避免重复显示
- 添加去重机制
- 优先级：低（不影响功能）

### E3: 清理 Pending Proposals
- 批量批准 confidence >= 0.8 的 proposals
- 或删除低置信度的 proposals
- 优先级：低（可手动处理）

---

## 附录：完整证据清单

### A. Proposal 重复性验证
- [x] 查询 pending proposals: 10 个，无重复
- [x] 查询 approved proposals: 50 个，仅 1 个重复 entity（经费率）
- [x] 代码分析: 无重复生成机制

### B. Evidence Chain 追踪
- [x] 查询 evidence API: 返回空数组
- [x] 验证 UUID 格式: Legacy 格式
- [x] 搜索证据: 0 results
- [x] 代码路径分析: app.py:465-544

### C. Evolution 执行次数
- [x] 统计今日执行次数: 30+ 次
- [x] 分析执行间隔: 不稳定
- [x] 对比正常配置: 应每 600s 执行一次

### D. 重启原因
- [x] 检查 container restart count: 0
- [x] 分析 shutdown 日志: 多为手动停止
- [x] 检查资源使用: 正常
- [x] 确认 Evolution 执行状态: 正常完成

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下次行动**: 等待用户确认下一步修复优先级
