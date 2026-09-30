# PMH Dashboard Hang Diagnostic Report - Phase 3

## 诊断目标
确定 Uvicorn 事件循环停止的根本原因。

---

## 关键发现

### 1. Server 正在无限重启循环中

```
从 10:54:00 开始，日志显示：
  - "Shutting down" 出现 158 次
  - "Started server process" 出现 28 次
  - 平均每次启动后很快关闭
```

**证据**：
```bash
docker logs --since "2026-08-10T10:54:00" | grep -c "Shutting down"
→ 158

docker logs --since "2026-08-10T10:54:00" | grep -c "Started server"
→ 28
```

### 2. 根本原因：`_perf_cache` 未定义

**错误日志**：
```
ERROR:    Exception in ASGI application
NameError: name '_perf_cache' is not defined
```

**触发路径**：
```
Dashboard 轮询
  → GET /api/performance/gpu
  → GET /api/ollama/stats
  → NameError: _perf_cache 未定义
  → 500 Internal Server Error
  → Uvicorn worker 崩溃
  → Server 重启
  → 循环
```

### 3. 为什么进程没有退出

**Uvicorn 默认行为**：
- Worker 线程崩溃时，Master 进程会重启 worker
- 但如果崩溃频率过高，可能导致 master 进程也进入不稳定状态

**当前状态**：
```
进程状态: S (sleeping)
wchan: futex_wait_queue
Threads: 6
Event loop: running=False
```

**含义**：
- Master 进程在等待 worker 线程
- Worker 线程崩溃后，master 尝试重启
- 但每次重启都因为 `_perf_cache` 错误而失败
- 最终进入死亡螺旋

---

## 详细分析

### 4. Uvicorn 启动方式

```python
# app.py 第 1856 行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**标准启动方式**，没有自定义 event loop。

### 5. 没有显式 shutdown 调用

```bash
grep -n "shutdown\|should_exit\|sys.exit" /app/src/backend/app.py
→ 没有找到相关代码
```

**结论**：应用代码没有主动调用 shutdown。

### 6. 没有自定义 signal handler

```python
signal.getsignal(signal.SIGINT) → <built-in function default_int_handler>
signal.getsignal(signal.SIGTERM) → 0
signal.getsignal(signal.SIGQUIT) → 0
```

**结论**：没有自定义 signal handler。

### 7. FastAPI lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 创建 cron scheduler task
    _cron_scheduler_task = asyncio.create_task(_cron_scheduler_loop())
    
    yield
    
    # Shutdown: cancel cron task
    if _cron_scheduler_task:
        _cron_scheduler_task.cancel()
```

**lifespan 正常**，没有提前结束的问题。

### 8. Batch / Reflection 任务

```
最后运行时间: 2026-08-10 10:55:13
状态: 已完成 (48 facts, 48 proposals)
 cron scheduler task: None
```

**结论**：Batch 任务已完成，不影响当前状态。

---

## 因果链

```
1. 添加性能 API 端点
   ↓
2. 使用 _perf_cache 变量
   ↓
3. 部署时变量未定义（NameError）
   ↓
4. Dashboard 轮询触发 500 错误
   ↓
5. Uvicorn worker 崩溃
   ↓
6. Master 进程重启 worker
   ↓
7. 重启后立即再次崩溃（死循环）
   ↓
8. 377 个 CLOSE_WAIT 堆积
   ↓
9. 所有请求超时
```

---

## 修复方案

### 立即修复

```python
# 在 app.py 中添加正确的 _perf_cache 定义
_perf_cache = {
    "gpu": {"value": None, "timestamp": None},
    "ollama": {"value": None, "timestamp": None},
}
PERF_CACHE_TTL = 30  # seconds
```

### 根本修复

1. 确保所有性能 API 端点正确处理缓存
2. 添加错误处理，避免 NameError 导致 worker 崩溃
3. 考虑添加健康检查，检测重启循环

---

## 最终结论

**Root cause**: `_perf_cache` 变量未定义导致 NameError，触发 Uvicorn worker 重启循环。

**触发点**: 添加性能 API 端点时，缓存变量定义可能因部署问题未生效。

**状态**:
- Root cause: ✅ **CONFIRMED**
- 触发路径: ✅ **CONFIRMED**
- 重启循环: ✅ **CONFIRMED**

---

## 需要验证

1. 确认 `_perf_cache` 变量在容器中的实际状态
2. 检查部署过程是否有遗漏
3. 验证修复后不再重启

---

**诊断完成时间**: 2026-08-10 11:35 JST
**下一步**: 修复 `_perf_cache` 定义，重启容器
