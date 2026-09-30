# PMH Dashboard Hang Diagnostic Report

## 1. 已确认事实

### 1.1 Dashboard 调用链（已验证）

**Dashboard → Memory Hub API:**
```
checkServices() → fetch('/health') + fetch('/api/ollama/api/tags')
refreshPerfMetrics() → fetch('/api/performance/gpu') + fetch('/api/ollama/stats')
```

**Memory Hub → Ollama:**
- `/api/performance/gpu` → `urllib.request.urlopen('http://host.docker.internal:11434/api/tags', timeout=3)`
- `/api/ollama/stats` → `urllib.request.urlopen('http://host.docker.internal:11434/api/tags', timeout=3)`
- `/api/ollama/{path}` (proxy) → `httpx.AsyncClient(timeout=30.0)`

**Timeout 设置:**
| 端点 | Timeout | 客户端 |
|------|---------|--------|
| /health | 3s (AbortSignal) | Browser fetch |
| /api/ollama/api/tags | 3s (AbortSignal) | Browser fetch |
| /api/performance/gpu | 3s (urllib) | Python urllib |
| /api/ollama/stats | 3s (urllib) | Python urllib |
| /api/ollama/* (proxy) | 30s (httpx) | Python httpx |

### 1.2 Ollama 行为（已验证）

| Endpoint | 模型卸载后 | 说明 |
|----------|-----------|------|
| `/api/version` | ✅ 正常 (200) | 不需要模型 |
| `/api/ps` | ✅ 正常 (空列表) | 显示无模型运行 |
| `/api/tags` | ✅ 正常 (200, 12 models) | 列出所有模型，不需要模型在内存 |
| `/api/generate` | ⏳ 首次请求触发加载 | 需要模型加载 ~10-15s |
| `/api/chat` | ⏳ 首次请求触发加载 | 需要模型加载 |

**关键发现**: `/api/tags` 和 `/api/ps` 在模型卸载后仍然正常响应，**不需要模型在 GPU 内存中**。

### 1.3 当前系统状态

```
Port 8000 连接状态:
  CLOSE_WAIT: 373  (异常堆积)
  ESTABLISHED: 1
  LISTEN: 1

容器进程状态:
  State: S (sleeping)
  wchan: futex_wait_queue
  Threads: 6
  FDSize: 64
  Open FDs: 16

Ollama 状态:
  模型: 已卸载 (GPU 0 MiB)
  Server: 正常运行 (11434)
```

### 1.4 内部测试确认

```
从容器内部测试:
  GET http://host.docker.internal:11434/api/tags → 200 OK ✅
  GET http://host.docker.internal:11434/api/version → 200 OK ✅
  GET http://host.docker.internal:11434/api/ps → 200 OK ✅

  GET http://127.0.0.1:8000/api/performance/gpu → ReadTimeout ❌
  GET http://127.0.0.1:8000/api/ollama/stats → ReadTimeout ❌
```

**结论**: Memory Hub 容器内部访问 Ollama 正常，但访问 Memory Hub 自身 API 超时。

---

## 2. 未确认假设

### 2.1 373 个 CLOSE_WAIT 的来源

**假设**: 这些 CLOSE_WAIT 是之前 Dashboard 轮询产生的堆积，不是当前轮询产生的。

**需要验证**:
- [ ] 检查这些连接的创建时间（需要 /proc/net/tcp 的 inode 信息）
- [ ] 确认是否是浏览器刷新时产生的
- [ ] 确认是否有定时任务持续产生新连接

### 2.2 为什么 Memory Hub 自身 API 超时

**假设**: 373 个 CLOSE_WAIT 连接占用了连接队列，导致新连接无法处理。

**需要验证**:
- [ ] 检查 TCP backlog 大小
- [ ] 检查容器网络栈状态
- [ ] 确认是否有其他进程占用连接

---

## 3. CLOSE_WAIT 来源分析

### 3.1 连接方向

```
Local: 172.19.0.3:8000 (Memory Hub container)
Remote: 172.19.0.1:* (Docker bridge gateway)

所有 CLOSE_WAIT 都是:
  Container → Docker Gateway
  方向: 入站连接（从 Host 到 Container）
```

### 3.2 产生原因

**TCP CLOSE_WAIT 状态说明**:
- 本地（Memory Hub）已经调用了 `close()` 关闭了连接
- 远程（Host/Dashboard）还没有关闭连接
- 连接等待远程关闭后彻底释放

**可能来源**:
1. **Dashboard 浏览器轮询**: 每次 `fetch()` 请求超时后，浏览器侧连接未正确关闭
2. **Python urllib**: `with` 语句应该正确关闭，但如果超时可能未正确关闭
3. **Docker proxy**: Docker 端口转发代理可能保留连接

### 3.3 为什么不是 Ollama 连接

```
Port 11434 (Ollama): 无 CLOSE_WAIT 连接 ✅
Port 8000 (Memory Hub): 373 个 CLOSE_WAIT 连接 ❌
```

**结论**: CLOSE_WAIT 是 Memory Hub 的入站连接，不是 Ollama 的连接。

---

## 4. Timeout 根因分析

### 4.1 Timeout 发生位置

| 层级 | 状态 | 说明 |
|------|------|------|
| Browser fetch | 3s 超时 | AbortSignal.timeout(3000) |
| Memory Hub API | 3s 超时 | urllib.request.urlopen(timeout=3) |
| Ollama API | 不超时 | /api/tags 返回正常 |

**关键发现**: Ollama API 正常，但 Memory Hub API 超时。

### 4.2 Timeout 类型

**不是 Ollama timeout**: Ollama /api/tags 正常响应
**不是 Docker network timeout**: 容器内部可以访问 Ollama
**不是 HTTP client timeout**: Browser fetch 有 3s 超时，但 Memory Hub 本身也超时
**可能是 application-level timeout**: Memory Hub 进程无法处理新请求

### 4.3 证据

```
1. 容器进程状态: State=S (sleeping), wchan=futex_wait_queue
   → 进程在等待某个事件（可能是信号量或锁）

2. 内部 Python httpx 访问 /api/performance/gpu 也超时
   → 不是浏览器问题，是容器内部问题

3. 373 个 CLOSE_WAIT 连接
   → 连接堆积，可能占用资源
```

---

## 5. Ollama 模型卸载的角色

### 5.1 模型卸载的影响

| 操作 | 需要模型在内存？ | 模型卸载后行为 |
|------|-----------------|---------------|
| GET /api/tags | ❌ 不需要 | ✅ 正常返回 |
| GET /api/ps | ❌ 不需要 | ✅ 正常返回 |
| GET /api/version | ❌ 不需要 | ✅ 正常返回 |
| POST /api/generate | ✅ 需要 | ⏳ 首次触发加载 |
| POST /api/chat | ✅ 需要 | ⏳ 首次触发加载 |

### 5.2 模型卸载不是直接原因

**Dashboard 调用的端点**:
- `/api/performance/gpu` → 调用 `/api/tags`（不需要模型）
- `/api/ollama/stats` → 调用 `/api/tags`（不需要模型）

**实际行为**: 这些端点不需要模型在内存，应该正常响应。

### 5.3 模型卸载是间接触发条件

**因果链**:
```
1. Batch 任务运行 → 模型加载到 GPU
2. Batch 完成 → Ollama 自动卸载模型（idle 2分钟）
3. Dashboard 开始轮询 → 调用 /api/tags
4. /api/tags 正常响应
5. 但 Dashboard 刷新 → 大量并发请求
6. 连接堆积 → CLOSE_WAIT 累积
7. 最终 Memory Hub 无法处理新请求
```

**结论**: 模型卸载本身不影响 `/api/tags`，但触发条件导致 Dashboard 轮询时产生大量超时请求。

---

## 6. Memory Hub 无法刷新原因

### 6.1 当前状态

```
373 个 CLOSE_WAIT 连接
容器进程: sleeping (futex_wait_queue)
新请求: 超时
```

### 6.2 可能原因

**假设 A**: 373 个 CLOSE_WAIT 占用了连接队列
- 需要验证: TCP backlog 是否已满

**假设 B**: 容器进程卡在某个锁/信号量
- 证据: wchan=futex_wait_queue
- 需要验证: 进程在等待什么

**假设 C**: 资源泄漏（文件描述符、内存等）
- 证据: Open FDs=16（正常）, VmRSS=174MB（正常）
- 暂时排除

### 6.3 区分三种情况

| 情况 | Ollama | Dashboard | Memory Hub API | 当前状态 |
|------|--------|-----------|----------------|----------|
| A: 只有 Ollama stats 失败 | ❌ | ❌ | ✅ | ❌ 不适用 |
| B: Backend connection 耗尽 | ✅ | ❌ | ❌ | ✅ 可能 |
| C: Ollama 本身正常 | ✅ | ✅ | ✅ | ❌ 不适用 |

**当前状态**: 情况 B 最可能 —— Memory Hub backend 自身无法处理请求。

---

## 7. Batch 与 Dashboard 请求是否互相影响

### 7.1 共享资源分析

| 资源 | Batch | Dashboard | 是否共享 |
|------|-------|-----------|----------|
| HTTP client | httpx (asyncio) | Browser fetch | ❌ 不共享 |
| Connection pool | 无 | 无 | ❌ 不共享 |
| asyncio event loop | 同一进程 | 同一进程 | ✅ 共享 |
| Worker | 单进程 | 单进程 | ✅ 共享 |
| Thread | 6 threads | N/A | ✅ 可能共享 |
| Ollama client | urllib | urllib | ✅ 共享主机 |
| Semaphore | 无 | 无 | ❌ 不共享 |
| Global lock | 未知 | 未知 | ⚠️ 可能共享 |

### 7.2 可能影响路径

1. **Event loop 阻塞**: 如果 Batch 任务运行期间有大量异步操作，可能阻塞 event loop
2. **Thread 竞争**: 6 个线程可能都在处理请求，包括 Dashboard 轮询
3. **Ollama 模型加载**: Batch 任务需要模型在内存，可能影响 Dashboard 轮询

### 7.3 当前状态（Batch 未运行）

```
日志: 最后 Evolution 完成于 10:55:13
现在: 11:00+ (约 5 分钟后)
模型: 已卸载
Dashboard: 无法访问
```

**结论**: Batch 任务已完成，不影响当前状态。问题与 Batch 无关。

---

## 8. Docker 网络层分析

### 8.1 网络连接方式

```
Host (172.19.0.1)
  ↓
Docker Bridge Network (personal-memory-hub_default)
  ↓
Container (172.19.0.3:8000)
```

### 8.2 测试从 Host 访问 Ollama

```
Host → Ollama:
  GET http://localhost:11434/api/tags → 200 OK ✅
  GET http://localhost:11434/api/version → 200 OK ✅
  GET http://localhost:11434/api/ps → 200 OK ✅
```

### 8.3 Timeout 发生层

| 层级 | 测试 | 结果 |
|------|------|------|
| Host → Ollama | ✅ 正常 | 不是 Ollama 问题 |
| Container → Ollama | ✅ 正常 | 不是 Docker 网络问题 |
| Host → Memory Hub | ❌ 超时 | 问题在 Memory Hub |
| Container → Memory Hub (内部) | ❌ 超时 | 问题在 Memory Hub 应用层 |

**结论**: Timeout 发生在 Memory Hub 应用层，不是 Docker 网络层。

---

## 9. 最终诊断结论

### 9.1 已确认

1. **Dashboard 调用链**: 正确理解，调用 `/api/performance/gpu` 和 `/api/ollama/stats`
2. **Ollama API 行为**: `/api/tags` 不需要模型在内存，正常响应
3. **Timeout 位置**: Memory Hub 应用层，不是 Ollama 或 Docker 网络层
4. **CLOSE_WAIT 来源**: Memory Hub 入站连接，373 个堆积
5. **容器进程状态**: sleeping (futex_wait_queue)，无法处理新请求

### 9.2 未确认

1. **373 个 CLOSE_WAIT 的精确来源**: 需要进一步分析连接创建时间
2. **futex_wait_queue 等待的具体事件**: 需要检查进程栈
3. **为什么内部 Python 也超时**: 需要检查应用层逻辑

### 9.3 Root Cause 判断

**当前证据不足以确定根因**，但最可能的假设是：

```
Root cause not yet proven

假设: Memory Hub 应用层有连接管理问题
  - 可能是 urllib 连接未正确关闭
  - 可能是 asyncio 任务未正确清理
  - 可能是内部锁/信号量竞争

触发条件:
  - Dashboard 刷新 → 大量并发请求
  - 请求超时 → CLOSE_WAIT 堆积
  - 连接队列满 → 新请求无法处理
  - 进程阻塞 → 所有请求超时
```

### 9.4 需要进一步诊断

1. 检查 Memory Hub 应用日志，确认是否有异常
2. 检查容器内 Python 进程栈，确认 futex_wait_queue 等待什么
3. 分析 373 个 CLOSE_WAIT 的创建时间和来源
4. 确认是否有内部锁或信号量竞争

---

## 10. 修复方向（诊断完成后）

### 10.1 短期方案
- [ ] 清理 CLOSE_WAIT 连接（重启容器）
- [ ] 添加连接超时后的清理机制
- [ ] 限制最大并发连接数

### 10.2 中期方案
- [ ] 实现连接池管理
- [ ] 添加请求超时后的自动清理
- [ ] 实现 Dashboard 轮询的退避策略

### 10.3 长期方案
- [ ] 重构性能监控端点，不依赖 Ollama
- [ ] 实现 GPU 信息从系统层面读取（/proc/driver/nvidia）
- [ ] 添加连接健康检查和自动恢复

---

**诊断完成时间**: 2026-08-10 11:00 JST
**下一步**: 等待用户指示，决定修复方案
