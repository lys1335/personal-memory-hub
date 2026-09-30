# Phase 26-G-B.6 Rebuild Completion Forensics

## 关键发现

Rebuild 脚本执行约 10 小时后，日志显示 "completed successfully"，但 Agent 报告 "Memory is full"。

**正确判定方法**：

1. **检查 PID 状态**
   ```bash
   docker exec memory-hub-app bash -c "cat /proc/147/status 2>/dev/null | grep -E 'Name|State' || echo 'Process 147 not found (TERMINATED)'"
   ```
   - 返回 "not found" = 进程已终止
   - 返回 "State: Z (dead)" 或 "State: D (uninterruptible)" = 异常终止

2. **检查 Container OOMKilled**
   ```bash
   docker inspect memory-hub-app --format='OOMKilled: {{.State.OOMKilled}}'
   ```
   - `false` = 未被 OOM 杀死
   - `true` = 被 OOM 杀死（需要进一步调查）

3. **检查 Exit Code**
   ```bash
   docker inspect memory-hub-app --format='ExitCode: {{.State.ExitCode}}'
   ```
   - `0` = 正常退出
   - `137` = SIGKILL（可能是 OOM）
   - 其他 = 异常退出

4. **检查日志最后几行**
   ```bash
   docker exec memory-hub-app bash -c "tail -10 /tmp/rebuild_output.log"
   ```
   - 必须包含 "completed successfully" 或 "Rebuild Phase Completed"
   - 不能有 "Traceback" 或 "Exception"（除非是非致命错误）

5. **数据库稳定性验证**（4 次采样）
   ```bash
   # T0
   docker exec memory-hub-db psql -U postgres -d memory_hub -c "SELECT COUNT(*) FROM candidates WHERE evidence_source = 'semantic_interpretation';"
   
   # T+30s
   sleep 30 && docker exec memory-hub-db psql -U postgres -d memory_hub -c "SELECT COUNT(*) FROM candidates WHERE evidence_source = 'semantic_interpretation';"
   
   # T+60s
   sleep 60 && docker exec memory-hub-db psql -U postgres -d memory_hub -c "SELECT COUNT(*) FROM candidates WHERE evidence_source = 'semantic_interpretation';"
   
   # T+90s
   sleep 90 && docker exec memory-hub-db psql -U postgres -d memory_hub -c "SELECT COUNT(*) FROM candidates WHERE evidence_source = 'semantic_interpretation';"
   ```
   - 如果 4 次计数完全相同 = DATABASE_STABLE = PASS
   - 如果有变化 = 继续等待

## "Memory is full" 性质判定

| 信号 | 含义 | 处理方式 |
|------|------|----------|
| Agent 报告 "Memory is full" | Agent 上下文/quota 限制 | 与 Rebuild 无关，继续检查实际状态 |
| Container OOMKilled = true | 容器被 OOM 杀死 | 需要增加内存限制或优化查询 |
| Exit Code = 137 | 进程被 SIGKILL | 可能是 OOM 或其他信号 |
| 日志显示 "Traceback" | 代码异常 | 需要修复代码或数据 |
| 日志显示 "completed successfully" | 正常完成 | PASS |

**典型误判场景**：
```
Agent: "Memory is full. I'll skip the memory update."
实际: Rebuild 已完成，只是 Agent 无法写入记忆
```

**正确做法**：
1. 忽略 Agent 的 "Memory is full" 报告
2. 立即检查 PID 状态、Exit Code、日志
3. 如果进程已终止且日志显示正常完成 = PASS
4. 不要假设 Rebuild 失败

## Workspace ID 选择 Bug（Critical）

**问题**：Rebuild 脚本使用 `workspaces[0]` 获取 workspace，但 Docker DNS 返回顺序不保证，导致选中错误的 `default-workspace`。

**根因**：
```python
# 错误代码
ws_result = await session.execute(select(Workspace))
workspaces = ws_result.scalars().all()
workspace_id = workspaces[0].id  # ❌ 依赖数据库返回顺序
```

**正确做法**：
```python
# 方案 1：硬编码（与 app.py 一致）
DEFAULT_WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

# 方案 2：按名称查询
ws_result = await session.execute(
    select(Workspace).where(Workspace.name == "user-workspace")
)
workspace_id = ws_result.scalar_one().id

# 方案 3：三阶段回退
if hardcoded_id:
    workspace_id = hardcoded_id
elif workspaces_by_name:
    workspace_id = workspaces_by_name.id
else:
    workspace_id = max(workspaces, key=lambda w: w.evidence_count).id  # 使用证据最多的 workspace
```

**证据等级**：LEVEL 3（DATABASE/RUNTIME FACT VERIFIED）

## Anti-Collapse Gate Async/Sync Bug

**问题**：`check_anti_collapse_gate` 使用同步 `session.execute()` 而非异步 `await session.execute()`。

**症状**：
```
ERROR - Failed to check Anti-Collapse Gate: 'coroutine' object has no attribute 'fetchone'
```

**根因**：
```python
# 错误代码
result = session.execute(stmt)  # ❌ 返回 coroutine
row = result.fetchone()  # ❌ coroutine 没有 fetchone

# 正确代码
result = await session.execute(stmt)  # ✅
row = result.fetchone()
```

**影响**：异常被捕获后返回 `True`（不中断），Gate 形同虚设。

**证据等级**：LEVEL 2（CODE PRESENT）

## Settings 属性名

**问题**：`settings.database_url` 不存在，正确属性是 `settings.DATABASE_URL`。

**正确代码**：
```python
from backend.shared.infrastructure.config.settings import get_settings

settings = get_settings()
db_url = settings.DATABASE_URL  # ✅ 大写
```

**证据等级**：LEVEL 2（CODE PRESENT）
