# Personal Memory Hub — 事前调查报告与实施方案

> **日期**: 2026-07-27
> **项目状态**: GitHub 覆盖后完全调查完成

---

## 一、CI 状态调查结果

### ✅ CI 流水线完全健康

| 检查项 | 工具 | 结果 |
|--------|------|------|
| 代码风格检查 | ruff v0.15.20 | ✅ All checks passed |
| 类型检查 | mypy 1.10+ | ✅ Success, no issues (69 files) |
| 单元测试 | pytest 8.4.2 | ✅ 269 tests passed (2.57s) |
| 构建打包 | uv build | ✅ wheel 创建成功 |

### CI 无错误，无需修复

代码质量优秀，静态分析和测试全部通过。如果未来需要增强 CI：
- 可添加 `uv run ruff check --fix` 自动修复格式化问题
- 可添加 `uv run coverage run -m pytest` 生成覆盖率报告
- 当前已足够稳定

---

## 二、Dashboard 显示解决方案

### 架构原理

```
浏览器 (http://localhost:5000)
    ↓ dashboard_server.py (HTTP Proxy/CORS 中间件)
├─ /api/memories → http://localhost:8000/memories (Memory Hub API)
├─ /api/ollama   → http://localhost:11434/api/ollama (Ollama LLM)
└─ 静态文件服务 ← dashboard-main.html (项目根目录)
```

### 正常运行所需条件

| 服务 | 端口 | 启动方式 | 依赖 |
|------|------|----------|------|
| PostgreSQL 数据库 | 5432 | Docker: `docker compose up -d db` | 无 |
| Memory Hub API | 8000 | `uvicorn backend.app:app --host 0.0.0.0 --port 8000` | DB + .env |
| Ollama LLM | 11434 | `ollama run qwen2.5:7b` | 无 |
| Dashboard 代理 | 5000 | `python dashboard_server.py --port 5000` | API + Ollama |

### 配置要求：必须创建 `.env` 文件

⚠️ **当前缺失**：`backend/.env` 不存在，API 无法启动！

**创建方法：**
```bash
cd F:\LI_YONGSHUN\AI\personal-memory-hub\backend
copy .env.example .env          # Windows
# 或 cp .env.example .env       # Linux/macOS
```

**.env 关键配置项（Docker 部署用）：**
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/memory_hub
APP_NAME=personal-memory-hub
APP_LOG_LEVEL=INFO
VECTOR_DIMENSION=1536
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### Dashboard 正常访问步骤

```bash
# 方法 A：使用一键启动脚本（推荐）
python hub_launcher docker

# 方法 B：手动启动各组件
# 终端 1：启动数据库
docker compose up -d db

# 终端 2：启动 API（后台运行）
cd backend && uv run python -m uvicorn app.app --host 0.0.0.0 --port 8000

# 终端 3：启动 Ollama
ollama run qwen2.5:7b

# 终端 4：启动 Dashboard
cd .. && python dashboard_server.py --port 5000 --no-browser

# 浏览器访问：http://localhost:5000
```

### 常见问题排查

| 症状 | 可能原因 | 解决方法 |
|------|----------|----------|
| 页面空白/加载失败 | API 未启动 | 先启动 `python -m uvicorn backend.app:app --port 8000` |
| 502 Bad Gateway | 后端服务不可用 | 检查 Docker 容器状态：`docker ps` |
| CORS 错误 | 直接打开 file://HTML | 务必通过 http://localhost:5000 访问 |
| 数据库连接失败 | .env 配置错误 | 确认 DATABASE_URL 正确，DB 正在运行 |
| Ollama 连接失败 | 模型未运行 | `ollama run qwen2.5:7b` |

---

## 三、一键启动功能实现

### 新增文件 1：hub_launcher.py（跨平台 Python 启动器）

**位置**: `F:\LI_YONGSHUN\AI\personal-memory-hub\hub_launcher.py`

**特性**：
- ✓ 交互式菜单选择启动模式
- ✓ 自动检测并启动 Docker Compose（DB + API）
- ✓ 健康等待机制（轮询端口 + HTTP 健康检查）
- ✓ 自动在后台启动 Dashboard
- ✓ 自动尝试打开浏览器
- ✓ Windows/macOS/Linux 跨平台支持

**使用方式**：
```bash
# 交互式菜单（推荐）
python hub_launcher.py

# Docker 模式（直接启动）
python hub_launcher.py docker

# 本地 Python 模式（需手动准备环境）
python hub_launcher.py local

# 查看帮助
python hub_launcher.py --help
```

### 新增文件 2：run_all.bat（Windows 增强版启动脚本）

**位置**: `F:\LI_YONGSHUN\AI\personal-memory-hubun_all.bat`

**改进内容**：
- ✓ 增加 API 健康检查等待循环（最多 30 秒）
- ✓ 优先使用 backend venv 的 Python 执行 Dashboard
- ✓ 错误处理更完善
- ✓ 添加自动浏览器打开尝试
- ✓ 更友好的进度提示

**使用**：双击 `run_all.bat` 或从资源管理器拖动打开。

### 方案对比

| 方案 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| `hub_launcher.py` | 跨平台、逻辑清晰、有健康检查 | 需要 Python 环境 | ✅ 首选推荐 |
| `run_all.bat` | Windows 双击即用、无需额外安装 | Windows 专属 | Windows 用户便捷启动 |
| `launch.bat` | 已有、简单 | 仅做检查不启动 | ❌ 已弃用 |

---

## 四、完整启动指南（新手友好）

### 前置依赖安装

1. **Docker Desktop** – https://www.docker.com/products/docker-desktop/
2. **Python 3.11+** – https://www.python.org/downloads/
3. **uv** – https://github.com/astral-sh/uv (已随本项目安装)
4. **Ollama** – https://ollama.com/download (`ollama run qwen2.5:7b`)

### 完整启动流程（Windows）

```cmd
:: 1. 首次设置（仅需一次）
cd F:\LI_YONGSHUN\AI\personal-memory-hubackend
copy .env.example .env

:: 2. 一键启动（从此开始只需一步）
双击 run_all.bat 
# 或 python hub_launcher.py docker

:: 3. 浏览器自动打开 http://localhost:5000
```

### 完整启动流程（Linux/macOS）

```bash
# 1. 首次设置（仅需一次）
cd ~/AI/personal-memory-hub/backend
cp .env.example .env

# 2. 一键启动
python3 hub_launcher.py docker

# 3. 浏览器打开
open http://localhost:5000  # macOS
xdg-open http://localhost:5000  # Linux
```

---

## 五、附录：项目文件结构概览

```
personal-memory-hub/
├── hub_launcher.py              ✅ 新增：统一启动器
├── run_all.bat                  ✅ 更新：增强版 Windows 启动
├── launch.bat                   已有：指引脚本（非自动启动）
├── start_hub.py                 已有：交互式 Python 启动器（分步）
├── dashboard_server.py          已有：CORS 代理服务器
├── dashboard-main.html          已有：主 Dashboard 界面
├── backend/
│   ├── src/backend/app.py       ✅ FastAPI 应用（含启动块）
│   ├── pyproject.toml          ✅ CI 配置完整
│   ├── .env.example             ⚠️ 需 copy 为 .env
│   └── .venv/                   ✅ 已创建（uv sync 后）
├── .github/workflows/ci.yml     ✅ CI 流水线（通过）
├── docker-compose.yml           ✅ Docker 编排
└── docs/                        📚 架构文档
