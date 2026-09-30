# PMH Dashboard Hang Diagnostic Report - Phase 2

## 诊断目标
确定 Memory Hub Python 进程卡在哪里，以及哪个线程/锁/任务导致 HTTP server 无法继续处理请求。

---

## 1. Python 进程完整线程栈

### 1.1 线程状态

```
总线程数: 1 (MainThread)
事件循环: <_UnixSelectorEventLoop running=False closed=False debug=False>
事件循环状态:
  - Running: False
  - Closed: False
  - Stopping: False
  - _ready count: 0
  - _scheduled count: 0
  - _default_executor: None

其他线程 (Task 7-11):
  - 状态: S (sleeping)
  - wchan: futex_wait_queue
  - 这些是 uvicorn worker 线程
```

### 1.2 关键发现

**事件循环未运行！**

```python
# 验证测试
asyncio.run(test_async()) → 成功
loop = asyncio.get_event_loop() → 失败: "There is no current event loop in thread 'MainThread'"
```

**结论**: MainThread 没有运行事件循环，uvicorn server 可能已停止或未正确启动。

### 1.3 无法获取内核栈

```
/proc/1/task/*/stack → Permission denied
```

需要 root 权限才能读取内核栈。

---

## 2. futex_wait_queue 对应的具体线程

### 2.1 主线程状态

```
State: S (sleeping)
wchan: futex_wait_queue
Threads: 6 (实际: 1 个 MainThread + 5 个 uvicorn worker)
FDSize: 64
Open FDs: 16
```

### 2.2 等待的具体对象

**无法确定**，因为：
1. 无法读取内核栈 (`/proc/1/task/*/stack` 权限不足)
2. 事件循环未运行，无法检查 asyncio Future/Task
3. faulthandler 未产生输出

**最可能的假设**:
- MainThread 在等待某个信号或事件
- 可能是在等待 uvicorn worker 线程完成
- 或者是在等待某个 threading.Event

### 2.3 已检查的同步原语

```python
# threading.Lock - 正常
lock = threading.Lock()
lock.acquire(blocking=False) → True

# asyncio.Lock - 未使用
# 事件循环未运行，无法创建 asyncio.Lock

# ThreadPoolExecutor - 无
_default_executor: None
```

**结论**: 没有明显的锁竞争，问题不在应用层锁。

---

## 3. 主 HTTP Server 状态

### 3.1 Server 框架

```
框架: FastAPI + Uvicorn
Uvicorn 版本: 0.51.0
App routes: 47
```

### 3.2 Listening Socket

```
LISTEN on 127.0.0.11:AE93 (Docker DNS)
LISTEN on 0.0.0.0:1F40 (Port 8000) - Memory Hub
```

**监听 socket 仍然存在！**

### 3.3 Accept Loop 状态

**无法直接确认**，但有以下证据：

```python
# 测试连接
serversock.connect(('127.0.0.1', 8000))
→ 失败: "[Errno 115] Operation now in progress"

# 含义:
# - EINPROGRESS (115) 表示 TCP 三次握手已发起但未完成
# - 这可能意味着:
#   1. 内核正在处理连接，但应用层无法接受
#   2. backlog 已满，新连接无法进入
#   3. 应用层的 accept() 调用被阻塞
```

### 3.4 Worker 线程状态

```
Task 7-11: State=S, wchan=futex_wait_queue
这些是 uvicorn worker 线程，都在等待请求
```

**关键问题**: 如果 worker 线程在等待请求，为什么新连接无法被接受？

**可能原因**:
1. **backlog 已满**: 377 个 CLOSE_WAIT 占用了连接队列
2. **accept() 被阻塞**: MainThread 在等待某个事件，无法调用 accept()
3. **内核层问题**: TCP 队列满，新连接无法进入

---

## 4. CLOSE_WAIT 连接分析

### 4.1 统计

```
总连接数: 383
  LISTEN: 2
  ESTABLISHED: 3
  CLOSE_WAIT: 377
  TIME_WAIT: 0
```

### 4.2 来源分析

```
CLOSE_WAIT 来源:
  - 172.19.0.1 (Docker bridge): 371 个
  - 127.0.0.1 (localhost): 6 个
```

**所有 CLOSE_WAIT 都是入站连接**（从 Host/Docker bridge 到 Container）。

### 4.3 TX/RX Queue 状态

```
TX queue (发送队列): 377 个全部为空 (00000000)
RX queue (接收队列): 377 个全部为空 (00)
```

**含义**:
- TX 空 → 应用层已发送所有数据并调用了 close()
- RX 空 → 对端已发送所有数据
- **但**: inode=0 表示这些 socket 没有被任何文件描述符引用

### 4.4 关键发现

**inode=0 的含义**:
```
所有 377 个 CLOSE_WAIT 连接的 inode 都是 0！
```

这表示：
1. 这些 socket 没有被任何文件描述符引用
2. 应用层已经调用了 close()，但 TCP 连接尚未完全关闭
3. **这是典型的连接泄漏**：应用层没有正确关闭连接

### 4.5 CLOSE_WAIT 是 Root cause 还是 Consequence？

**结论: Consequence（结果）**

证据：
1. CLOSE_WAIT 的 inode=0，表示应用层已经尝试关闭连接
2. 连接是因为超时后未正确关闭而产生的
3. 377 个 CLOSE_WAIT 是 Dashboard 轮询超时后堆积的结果
4. **不是 CLOSE_WAIT 导致卡死，而是卡死导致 CLOSE_WAIT 无法被清理**

---

## 5. Batch / Reflection 任务状态

### 5.1 最后运行时间

```
最后日志: 2026-08-10 10:55:13
[EVOLUTION] ReflectionService completed: 48 ops, 48 proposals
```

**当前时间**: 约 11:30+ (从之前的诊断)

**Batch 任务已结束约 35+ 分钟**

### 5.2 当前任务状态

```python
asyncio.all_tasks(loop) → 0 个 pending tasks
Event loop running: False
```

**没有正在运行的任务！**

### 5.3 后台任务

```
_default_executor: None
```

**没有线程池 executor！**

**结论**: 问题不是由 Batch 任务占用资源导致的。

---

## 6. Timeout 根因分析

### 6.1 证据总结

| 现象 | 状态 |
|------|------|
| Listening socket | ✅ 存在 (0.0.0.0:8000) |
| Event loop | ❌ 未运行 |
| MainThread | sleeping (futex_wait_queue) |
| Worker threads | sleeping (futex_wait_queue) |
| Pending tasks | 0 |
| Pending futures | 0 |
| CLOSE_WAIT | 377 个 (inode=0) |

### 6.2 Timeout 发生位置

**应用层 timeout，不是网络层！**

证据：
```python
# 从容器内部测试
urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)
→ 失败: "timed out"

httpx.AsyncClient(timeout=2.0).get('http://127.0.0.1:8000/health')
→ 失败: "ReadTimeout"
```

**内部请求也超时**，说明问题在应用层，不是网络层。

### 6.3 根本原因假设

**假设 1: Event Loop 未运行**

```python
# 当前状态
loop = asyncio.get_event_loop()
→ RuntimeError: "There is no current event loop in thread 'MainThread'"

# 但测试 asyncio.run() 可以工作
asyncio.run(test_async()) → success
```

**含义**: MainThread 没有运行事件循环，但 asyncio.run() 可以创建新的事件循环。

**假设 2: Uvicorn Server 已停止**

```python
# 检查 uvicorn server
server = uvicorn.Server(config)
print(f'Server should be running: {server.started}')
→ False
```

**含义**: Uvicorn server 可能已停止，但进程还在（因为 listening socket 还存在）。

**假设 3: MainThread 阻塞**

```
State: S (sleeping)
wchan: futex_wait_queue
```

**含义**: MainThread 在等待某个 futex（可能是 threading.Event 或 Condition）。

---

## 7. 最终诊断结论

### 7.1 Root Cause

**Root cause not yet proven**

但最可能的假设：

```
假设: Uvicorn server 的事件循环已停止，但进程未退出
  - MainThread 在等待某个事件（可能是 server shutdown event）
  - Worker 线程也在等待
  - Listening socket 仍然存在（因为进程未退出）
  - 但 accept() 不被调用（因为事件循环未运行）
  - 新连接无法被处理，变成 CLOSE_WAIT
  - 最终 backlog 满，所有请求超时
```

### 7.2 证据链

```
1. 事件循环未运行 (running=False)
2. MainThread 在 futex_wait_queue
3. 377 个 CLOSE_WAIT (inode=0)
4. 内部请求也超时
5. 没有 pending tasks 或 futures
6. Batch 任务已结束 35+ 分钟
```

### 7.3 需要进一步验证

1. **检查 Uvicorn server 状态**: 为什么事件循环停止但进程未退出？
2. **检查 MainThread 阻塞点**: 需要 root 权限读取内核栈
3. **检查是否有信号处理**: SIGQUIT 已发送，但未产生输出

---

## 8. 修复方向

### 8.1 立即修复

```bash
docker restart memory-hub-app
```

这将重启进程，清理所有 CLOSE_WAIT 连接。

### 8.2 长期修复

1. **添加健康检查和自动重启**: 如果事件循环停止，自动重启
2. **改进连接管理**: 确保超时后正确关闭连接
3. **添加监控**: 检测事件循环停止状态

---

## 9. 禁止事项检查

本阶段已严格遵守：
- ✅ 未修改代码
- ✅ 未重启服务
- ✅ 未修改 timeout/keep_alive
- ✅ 未修改 Ollama/Dashboard 配置
- ✅ 未修改 Docker 配置

---

**诊断完成时间**: 2026-08-10 11:30 JST
**下一步**: 等待用户指示，决定是否重启服务或继续诊断
