# Open WebUI + MemoryHub RAG 集成搭建指南

> **版本**: 1.0  
> **日期**: 2026-07-20  
> **目标**: 从零搭建 Open WebUI → MemoryHub Proxy → Ollama 的 RAG 集成环境  
> **架构原则**: MemoryHub 是唯一记忆中枢，Open WebUI 不存储任何数据

---

## 1. 架构总览

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌─────────┐
│  Open WebUI │────▶│ MemoryHub Proxy  │────▶│   Ollama     │────▶│ qwen2.5 │
│  (:3000)    │     │  (:8765)         │     │  (:11434)    │     │ :7b     │
└─────────────┘     └──────────────────┘     └──────────────┘     └─────────┘
                         │
                         ▼
                  ┌──────────────────┐
                  │  MemoryHub App   │
                  │  (:8000)         │
                  └──────────────────┘
                         │
                         ▼
                  ┌──────────────────┐
                  │ PostgreSQL DB    │
                  │  (:15432)        │
                  └──────────────────┘
```

### 数据流

1. 用户在 Open WebUI 提问
2. Open WebUI 发送 `/api/chat` 请求到代理 `memoryhub-proxy:8765`
3. 代理搜索 MemoryHub 相关记忆
4. 代理将记忆注入到请求体（preamble/system + 用户消息末尾）
5. 代理转发给 Ollama
6. Ollama 生成回答（基于记忆上下文）
7. 代理流式返回 SSE 响应给 Open WebUI

---

## 2. 组件清单

| 组件 | 端口 | 容器名 | 作用 |
|------|------|--------|------|
| Open WebUI | 3000 | open-webui | 前端界面 |
| MemoryHub Proxy | 8765 | memoryhub-proxy | RAG 注入代理 |
| MemoryHub App | 8000 | memory-hub-app | 记忆服务 API |
| PostgreSQL | 15432 | memory-hub-db | 记忆数据库 |
| Ollama | 11434 | host (本机) | 本地模型推理 |

### 网络要求

所有 Docker 容器必须连接到同一网络：`personal-memory-hub_default`

```bash
docker network create personal-memory-hub_default
```

---

## 3. 快速搭建步骤

### Step 1: 准备 MemoryHub 应用

```bash
cd F:/LI_YONGSHUN/AI/personal-memory-hub

# 构建并启动 MemoryHub
docker compose up -d db app
```

**环境变量** (`docker-compose.yml`):
```yaml
MEMORYHUB_URL: http://memory-hub-app:8000
DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/memory_hub
WORKSPACE_ID: 5266d746-d1bd-4834-9c3a-3be0f92fe0b0
```

### Step 2: 启动 Ollama

Ollama 运行在本机，不需要 Docker 容器。

```bash
# 确认 Ollama 正在运行
ollama list

# 拉取必要模型
ollama pull qwen2.5:7b
ollama pull nomic-embed-text:latest
```

### Step 3: 构建代理容器

```bash
cd F:/LI_YONGSHUN/AI

# 构建代理镜像
docker build -f Dockerfile.memoryhub-proxy -t memoryhub-proxy .

# 运行代理容器
docker run -d \
  --name memoryhub-proxy \
  --network personal-memory-hub_default \
  -p 8765:8765 \
  -e MEMORYHUB_URL=http://memory-hub-app:8000 \
  -e OLLAMA_URL=http://host.docker.internal:11434 \
  -e WORKSPACE_ID=5266d746-d1bd-4834-9c3a-3be0f92fe0b0 \
  memoryhub-proxy
```

### Step 4: 配置 Open WebUI

```bash
cd F:/LI_YONGSHUN/AI

# 创建数据目录
mkdir -p F:/LI_YONGSHUN/AI/open-webui-data

# 运行 Open WebUI
docker run -d \
  --name open-webui \
  --network personal-memory-hub_default \
  -p 3000:3000 \
  -v "F:/LI_YONGSHUN/AI/open-webui-data:/app/backend/data" \
  -e OLLAMA_BASE_URLS=http://memoryhub-proxy:8765 \
  -e OLLAMA_BASE_URL=http://memoryhub-proxy:8765 \
  -e ENABLE_SIGNUP=false \
  open-webui/open-webui:0.9.6
```

**关键配置**:
- `OLLAMA_BASE_URLS` 必须指向代理，不是直接连 Ollama
- 数据挂载路径必须是 `/app/backend/data`
- 禁用注册（`ENABLE_SIGNUP=false`），避免创建多余用户

### Step 5: 验证连通性

```bash
# 测试代理可达性
curl http://localhost:8765/api/tags

# 测试 MemoryHub API
curl http://localhost:8000/memories/search -X POST \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"5266d746-d1bd-4834-9c3a-3be0f92fe0b0","query":"NISA","limit":5}'

# 测试 Open WebUI
curl http://localhost:3000/api/v1/models
```

---

## 4. 导入数据到 MemoryHub

### 4.1 使用 Import API

```bash
# 准备导入 JSON
cat > nisa_import.json << 'EOF'
{
  "conversations": [
    {
      "title": "NISA Investment Configuration",
      "chat_msg": [
        {
          "role": "user",
          "content": "我现在的 NISA 配置中，有哪三只基金？具体比例是多少？"
        },
        {
          "role": "assistant",
          "content": "根据你之前的对话，你的 NISA 配置如下：\n\n🌍 全世界股票基金：每月 4 万日元\n🇺🇸 S&P500 指数基金：每月 4 万日元\n⚖️ バランス型（平衡型）：每月 2 万日元\n\n总计每月投入 10 万日元，年度投入 120 万日元。"
        }
      ]
    }
  ]
}
EOF

# 调用 Import API
curl -X POST http://localhost:8000/import \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "5266d746-d1bd-4834-9c3a-3be0f92fe0b0",
    "source_type": "open_webui",
    "data": "'"$(cat nisa_import.json)"'"
  }'
```

### 4.2 重要：assistant_reply 合并

**关键修复**: assistant_reply 必须合并进 `content` 字段才能被搜索命中。

在 `memory_service.py` 中：
```python
# Merge assistant_reply into content for searchability
searchable_content = content.strip()
if metadata and metadata.get("assistant_reply"):
    searchable_content += "\n\n[Assistant Reply]\n" + metadata["assistant_reply"]
```

---

## 5. RAG 注入机制

### 5.1 搜索策略

代理使用两级搜索：

1. **向量搜索** (`nomic-embed-text`)
   - 优先尝试
   - 对英文/日文效果好
   - 对中文长查询效果差

2. **关键词回退**
   - 当向量搜索返回 0 条时触发
   - 获取全部记忆后匹配关键词
   - 支持中日英混合查询

### 5.2 注入位置

```python
def inject_memories(body: dict) -> dict:
    # 1. 注入到 preamble/system（最高优先级）
    if "preamble" in body:
        body["preamble"] = context + "\n" + body["preamble"]
    elif "system" in body:
        body["system"] = context + "\n" + body["system"]
    
    # 2. 追加到用户消息末尾（强化）
    messages[-1]["content"] += context
```

### 5.3 上下文格式

```
[PERSONAL MEMORY DATABASE]
[MEMORY 1] 我的三个是每月四万四万二万的配置...
[MEMORY 2] 演练一下...
[END MEMORY DATABASE]
CRITICAL RULE: You MUST use the above personal memory database...
```

---

## 6. 调试与排查

### 6.1 查看代理日志

```bash
docker logs memoryhub-proxy --tail 50
```

**关键日志**:
```
[MemoryHub] Vector search returned 0 for '...', trying keyword fallback...
[MemoryHub] Keyword fallback returned 4 memories
[MemoryHub] Injecting 4 memories into query: ...
[MemoryHub] Context length: 5406 chars
[MemoryHub] Injected context into message 0, length: 5435
```

### 6.2 测试搜索 API

```bash
docker exec memoryhub-proxy python3 -c "
import json, urllib.request

data = json.dumps({
    'workspace_id': '5266d746-d1bd-4834-9c3a-3be0f92fe0b0',
    'query': 'NISA 配置',
    'limit': 5,
}).encode('utf-8')

req = urllib.request.Request(
    'http://memory-hub-app:8000/memories/search',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)

with urllib.request.urlopen(req) as resp:
    print(json.loads(resp.read()))
"
```

### 6.3 检查数据库

```bash
# 查看记忆数量
docker exec memory-hub-db psql -U postgres -d memory_hub -c \
  "SELECT COUNT(*) FROM memory_hub.memory_nodes;"

# 查看向量文档数量
docker exec memory-hub-db psql -U postgres -d memory_hub -c \
  "SELECT COUNT(*) FROM memory_hub.vector_documents;"

# 查看最新记忆
docker exec memory-hub-db psql -U postgres -d memory_hub -c \
  "SELECT id, LEFT(content, 200) FROM memory_hub.memory_nodes ORDER BY created_at DESC LIMIT 5;"
```

---

## 7. 已知陷阱与解决方案

### ⚠️ 陷阱 1: Host Header 导致 403

**现象**: Ollama 返回 `403 Forbidden`

**原因**: 代理转发 Open WebUI 的 Host header 给 Ollama，Ollama 拒绝

**解决**: 代理清除 Host 和 Content-Length headers
```python
clean_headers = {}
for key, value in headers.items():
    if key.lower() not in ("host", "content-length"):
        clean_headers[key] = value
```

---

### ⚠️ 陷阱 2: /api/models vs /api/tags

**现象**: Open WebUI 模型列表为空

**原因**: Open WebUI 调用 `/api/models`，但 Ollama 实际端点是 `/api/tags`

**解决**: 代理做映射
```python
def do_GET(self):
    path = self.path
    if path == "/api/models":
        path = "/api/tags"
    self._proxy_to_ollama("GET", path, self.headers, None)
```

---

### ⚠️ 陷阱 3: 流式响应问题

**现象**: Open WebUI 显示 "Server disconnected"

**原因**: 代理读取完整响应后才转发，但 Open WebUI 期望 SSE 流

**解决**: 逐块转发（4096 bytes/chunk）
```python
while True:
    chunk = resp.read(4096)
    if not chunk:
        break
    self.wfile.write(chunk)
    self.wfile.flush()
```

---

### ⚠️ 陷阱 4: 中文查询向量搜索失败

**现象**: 搜索返回 0 条记忆

**原因**: `nomic-embed-text` 对中文长查询向量匹配效果差

**解决**: 添加关键词搜索回退
```python
def search_memories(query: str, limit: int = 5) -> list[str]:
    vector_results = _vector_search(query, limit)
    if vector_results:
        return vector_results
    
    # Fallback to keyword search
    keyword_results = _keyword_search(query, limit)
    return keyword_results
```

---

### ⚠️ 陷阱 5: assistant_reply 不可搜索

**现象**: 导入后搜索不到基金配置信息

**原因**: assistant_reply 存在 metadata 中，但只有 content 字段可搜索

**解决**: 合并 assistant_reply 到 content
```python
searchable_content = content.strip()
if metadata and metadata.get("assistant_reply"):
    searchable_content += "\n\n[Assistant Reply]\n" + metadata["assistant_reply"]
```

---

### ⚠️ 陷阱 6: Open WebUI 数据库时间戳格式

**现象**: Open WebUI 容器启动后崩溃

**原因**: function/user 表时间是 BIGINT（毫秒），config 表是 DATETIME（字符串）

**解决**: 严格区分时间格式
```python
# function/user 表
"updated_at": int(time.time() * 1000),  # BIGINT 毫秒

# config 表
"updated_at": datetime.now().isoformat(),  # DATETIME 字符串
```

---

### ⚠️ 陷阱 7: Pipe Function 兼容性

**现象**: Open WebUI v0.9.6 看不到 Pipe Function

**原因**: v0.9.6 对 Pipe 加载/显示有问题

**解决**: 放弃 Pipe 方案，改用代理层注入

---

### ⚠️ 陷阱 8: Docker 网络问题

**现象**: 容器内访问其他服务失败

**原因**: Open WebUI 和 MemoryHub 在不同 Docker 网络

**解决**: 统一网络
```bash
docker network connect personal-memory-hub_default open-webui
```

---

## 8. 验证清单

### 基础设施验证

- [ ] PostgreSQL 运行中 (`:15432`)
- [ ] MemoryHub App 健康 (`:8000`)
- [ ] Ollama 模型可用 (`:11434`)
- [ ] 代理容器运行 (`:8765`)
- [ ] Open WebUI 运行 (`:3000`)

### 配置验证

- [ ] Open WebUI 配置指向代理
- [ ] 代理环境变量正确
- [ ] 数据库连接正常

### RAG 注入验证

- [ ] 搜索 API 返回记忆
- [ ] 代理日志显示注入
- [ ] Open WebUI 回答引用记忆

### 端到端测试

**测试问题 1**:
```
我现在的 NISA 配置中，有哪三只基金？具体比例是多少？每月定投金额和年度投入分别是多少？
```

**预期回答**:
- 🌍 全世界股票基金：每月 4 万日元
- 🇺🇸 S&P500 指数基金：每月 4 万日元
- ⚖️ バランス型：每月 2 万日元
- 每月总计：10 万日元
- 年度总计：120 万日元

**测试问题 2**:
```
假设美股下跌 -30% 且美元对日元贬值 -20%，我的账户从 600 万日元会跌到多少？
```

**预期回答**:
- 股票部分跌幅约 -44%
- 总账户跌幅约 -35%
- 600 万 → 390~420 万

---

## 9. 故障排除

### 问题：Open WebUI 回答不知道

**检查**:
1. 代理日志是否有注入记录
2. 搜索 API 是否返回记忆
3. Open WebUI 是否通过代理发送请求

**解决**:
```bash
# 查看代理日志
docker logs memoryhub-proxy --tail 50 | grep "Injecting"

# 测试搜索
curl http://localhost:8765/api/chat -X POST -d '{...}'
```

### 问题：模型列表空

**检查**:
```bash
curl http://localhost:8765/api/tags
```

**解决**: 确认代理映射 `/api/models` → `/api/tags`

### 问题：Server disconnected

**检查**:
```bash
docker logs memoryhub-proxy | grep "Server disconnected"
```

**解决**: 确认代理流式转发实现

---

## 10. 文件结构

```
F:/LI_YONGSHUN/AI/
├── memoryhub_proxy.py          # 代理服务器代码
├── Dockerfile.memoryhub-proxy  # 代理 Docker 构建文件
├── nisa_import_v2.json         # NISA 导入数据
└── personal-memory-hub/
    ├── backend/src/backend/
    │   ├── service/memory_service.py      # 记忆服务（含 assistant_reply 合并）
    │   ├── repository/entity_repository.py # 实体仓库（含自动创建）
    │   ├── repository/memory_query_repository.py # 查询仓库（含关键词搜索）
    │   └── ingest/adapters/open_webui.py  # Open WebUI 适配器
    └── docs/06_Integration/
        └── OpenWebUI-RAG-Integration-Guide.md  # 本文档
```

---

## 11. 总结

本集成方案的核心优势：

1. **MemoryHub 是唯一记忆中枢** — Open WebUI 不存储数据
2. **代理层 RAG 注入** — 不依赖 Open WebUI 扩展机制
3. **双级搜索** — 向量搜索 + 关键词回退，支持多语言
4. **配置型集成** — 无需修改 Open WebUI 源码

**关键经验**:
- 小模型（7B）对 RAG 上下文遵循不稳定，大模型（20B）更可靠
- 中文/日文查询需要关键词回退
- assistant_reply 必须合并进 content
- 代理注入格式要简洁明确
- Docker 网络必须统一

---

**文档版本**: 1.0  
**最后更新**: 2026-07-20  
**维护者**: Personal Memory Hub Team
