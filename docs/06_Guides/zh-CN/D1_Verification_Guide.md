# D1 验证指南

> **阶段**: Phase D — 文档驱动实现  
> **里程碑**: D1 — 基础设施基础  
> **版本**: 1.1  
> **日期**: 2026-07-04  
> **状态**: 最终版  
> **作者**: 系统架构组

---

## 目录

1. [目的](#1-目的)  
2. [前置条件](#2-前置条件)  
3. [仓库准备](#3-仓库准备)  
4. [Python 环境验证](#4-python-环境验证)  
5. [配置验证](#5-配置验证)  
6. [构建验证](#6-构建验证)  
7. [Ruff 验证](#7-ruff-验证)  
8. [mypy 验证](#8-mypy-验证)  
9. [pytest 验证](#9-pytest-验证)  
10. [Docker 验证](#10-docker-验证)  
11. [数据库验证](#11-数据库验证)  
12. [文档验证](#12-文档验证)  
13. [最终验收检查清单](#13-最终验收检查清单)  
14. [故障排查](#14-故障排查)

---

> 本文档为英文正式版本（Canonical Version）的简体中文本地化版本。
> 
> 英文原文：
> 
> docs/06_Guides/D1_Verification_Guide.md
> 
> 如中英文存在任何差异，以英文版本为准。

## 1. 目的

### 1.1 本指南验证什么

本指南验证 **D1 — 基础设施基础** 是否已正确实施。D1 为 Personal Memory Hub 项目建立了工程基线：

- 采用五层架构的项目目录结构
- 通过 `pyproject.toml` 和 `uv` 进行 Python 包配置
- 使用 pydantic-settings 的配置系统
- 通过 structlog 实现的结构化 JSON 日志
- SQLAlchemy 异步引擎和会话工厂
- Alembic 迁移框架
- 轻量级依赖注入容器
- 使用内存 SQLite 夹具的 pytest 测试框架
- 用于本地开发的 Docker 和 docker-compose
- GitHub Actions CI 流水线脚手架
- 文档（README、安装指南）

### 1.2 本指南不验证什么

以下内容明确 **不在** D1 验证范围内：

- **业务逻辑** — Service、Engine 或 Repository 的实现尚不存在（D2+）
- **数据库模式** — 表模型或迁移文件尚不存在（D2）
- **API 端点** — REST、MCP 或 CLI 适配器尚不存在（D5）
- **生产部署** — CD 流水线有意推迟
- **外部集成** — Supabase、Redis、OpenRouter 在 D1 中不需要
- **性能基准** — D1 不进行负载测试

### 1.3 验证理念

本指南面向 **对项目没有任何先验知识** 的开发人员设计。每条命令均可直接复制粘贴使用。每条预期输出均已记录。如果某一步骤失败，故障排查部分提供了诊断和解决方法。

---

## 2. 前置条件

开始验证之前，请确保以下工具已安装。

### 2.1 操作系统

**支持的平台**：

- Windows 10/11（64 位）
- macOS 12+（Monterey 或更高版本）
- Ubuntu 20.04+ / Debian 11+ / Fedora 38+

**Windows 是本指南的默认平台**。每个命令部分首先展示 Windows PowerShell 命令，然后是 Linux/macOS bash 等效命令。

### 2.2 Python

- **必需**: Python 3.11 或 3.12
- **最低要求**: Python 3.10（项目声明 `requires-python = ">=3.10"`）

**下载**: https://www.python.org/downloads/

**验证安装**：

**Windows (PowerShell)**：

```powershell
python --version
```

**Linux/macOS (bash)**：

```bash
python --version
```

**预期输出**：

```
Python 3.11.x
```

如果未安装 Python 或版本低于 3.10，请在继续之前安装。

### 2.3 uv

- **必需**: uv 0.4.0 或更高版本
- **用途**: 快速 Python 包安装器和项目管理器

**下载**: https://docs.astral.sh/uv/getting-started/installation/

**在 Windows 上安装**（PowerShell）：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**在 Linux/macOS 上安装**（终端）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**验证安装**：

**Windows (PowerShell)**：

```powershell
uv --version
```

**Linux/macOS (bash)**：

```bash
uv --version
```

**预期输出**：

```
uv 0.x.x (xxx...)
```

### 2.4 Docker Desktop

- **必需**: Docker Desktop 4.0+（或 Docker Engine + docker-compose 插件）
- **用途**: 带有 PostgreSQL + pgvector 的本地开发环境

**下载**: https://www.docker.com/products/docker-desktop/

**验证安装**：

**Windows (PowerShell)**：

```powershell
docker --version
docker compose version
```

**Linux/macOS (bash)**：

```bash
docker --version
docker compose version
```

**预期输出**：

```
Docker version 24.x.x, build xxxxxxx
Docker Compose version v2.x.x
```

如果未安装 Docker Desktop，可以跳过 Docker 相关验证步骤（第 10 节）。D1 的其余部分不需要 Docker。

### 2.5 Git

- **必需**: Git 2.40+
- **用途**: 仓库克隆

**下载**: https://git-scm.com/downloads

**验证安装**：

**Windows (PowerShell)**：

```powershell
git --version
```

**Linux/macOS (bash)**：

```bash
git --version
```

**预期输出**：

```
git version 2.x.x
```

---

## 3. 仓库准备

### 3.1 克隆仓库

**Windows (PowerShell)**：

```powershell
git clone https://github.com/lys1335/personal-memory-hub.git
cd personal-memory-hub
```

**Linux/macOS (bash)**：

```bash
git clone https://github.com/lys1335/personal-memory-hub.git
cd personal-memory-hub
```

**预期输出**：

```
Cloning into 'personal-memory-hub'...
remote: Enumerating objects: XXXX, done.
remote: Counting objects: 100% (XXX/XXX), done.
remote: Compressing objects: 100% (XXX/XXX), done.
remote: total XXXX (delta XX), reused XXXX (delta XX), pack-reused XX
Receiving objects: 100% (XXXX/XXXX), X.XX MiB | X.XX MiB/s, done.
Resolving deltas: 100% (XX/XX), done.
```

### 3.2 预期的目录布局

克隆后，仓库根目录应包含以下内容：

```
personal-memory-hub/
├── .gitignore
├── README.md
├── docker-compose.yml
├── docs/
│   ├── INDEX.md
│   └── 05_Implementation/
│       ├── README.md
│       └── D1_Infrastructure_Foundation_Plan.md
└── backend/
    ├── .env.example
    ├── alembic.ini
    ├── Dockerfile
    ├── pyproject.toml
    ├── README.md
    ├── uv.lock
    ├── alembic/
    │   ├── env.py
    │   ├── README
    │   ├── script.py.mako
    │   └── versions/
    │       └── README.md
    ├── scripts/
    │   └── README.md
    ├── src/
    │   └── backend/
    │       ├── __init__.py
    │       ├── engine/
    │       │   └── __init__.py
    │       ├── entry/
    │       │   └── __init__.py
    │       ├── repository/
    │       │   └── __init__.py
    │       ├── scripts/
    │       │   └── README.md
    │       ├── service/
    │       │   └── __init__.py
    │       ├── shared/
    │       │   ├── __init__.py
    │       │   ├── domain/
    │       │   │   └── __init__.py
    │       │   ├── infrastructure/
    │       │   │   ├── __init__.py
    │       │   │   ├── config/
    │       │   │   │   ├── __init__.py
    │       │   │   │   └── settings.py
    │       │   │   ├── database/
    │       │   │   │   ├── __init__.py
    │       │   │   │   └── engine.py
    │       │   │   ├── di/
    │       │   │   │   ├── __init__.py
    │       │   │   │   └── container.py
    │       │   │   └── logging/
    │       │   │       └── __init__.py
    │       │   └── protocols/
    │       │       └── __init__.py
    │       └── tools/
    │           └── README.md
    ├── tests/
    │   ├── conftest.py
    │   ├── test_fixtures.py
    │   ├── test_smoke.py
    │   ├── evaluation/
    │   │   └── README.md
    │   ├── fixtures/
    │   │   └── README.md
    │   ├── golden/
    │   │   └── README.md
    │   ├── integration/
    │   │   └── README.md
    │   ├── scenarios/
    │   │   └── README.md
    │   └── unit/
    │       └── README.md
    └── tools/
        └── README.md
```

**验证**: 使用以下命令检查结构。

> **工作目录**: 从仓库根目录（`personal-memory-hub/`）执行。

**Windows (PowerShell)**：

```powershell
Get-ChildItem -Path backend -Recurse -File -Exclude __pycache__, .venv, .mypy_cache, .pytest_cache, .ruff_cache, dist | Select-Object -ExpandProperty FullName | Sort-Object
```

**Linux/macOS (bash)**：

```bash
find backend -type f ! -path "*/.venv/*" ! -path "*/.mypy_cache/*" ! -path "*/.pytest_cache/*" ! -path "*/.ruff_cache/*" ! -path "*/dist/*" ! -path "*/__pycache__/*" | sort
```

**预期**: 输出应列出上述所有文件（不包括 `uv.lock`，它在 `uv sync` 时生成；以及 `dist/`，它在 `uv build` 时生成）。

> **注意**: 上面的目录树是已提交文件的 **完整表示**。它 **不包含** 自动生成的目录（`.venv/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`dist/`、`__pycache__/`）。这些已由 `.gitignore` 排除。

### 3.3 预期的关键文件

以下文件必须存在：

| 文件 | 用途 |
|------|------|
| `backend/pyproject.toml` | 项目配置、依赖项、工具设置 |
| `backend/.env.example` | 环境变量模板 |
| `backend/src/backend/shared/infrastructure/config/settings.py` | 配置系统 |
| `backend/src/backend/shared/infrastructure/logging/__init__.py` | 日志框架 |
| `backend/src/backend/shared/infrastructure/database/engine.py` | SQLAlchemy 引擎/会话 |
| `backend/src/backend/shared/infrastructure/di/container.py` | DI 容器 |
| `backend/src/backend/shared/infrastructure/database/__init__.py` | 数据库导出 |
| `backend/alembic/env.py` | Alembic 环境 |
| `backend/Dockerfile` | 容器构建 |
| `docker-compose.yml` | 本地开发环境 |
| `.github/workflows/ci.yml` | CI 流水线 |
| `README.md` | 项目概述 |
| `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` | D1 规划文档 |

### 3.4 按分类的文件

下表对 D1 产生的每个文件进行了分类。用它来理解哪些属于 Git，哪些是在本地生成的。

| 类别 | 示例 | 应在 Git 中存在 | 说明 |
|------|------|----------------|------|
| **源代码** | `backend/src/`、`backend/tests/` | 是 | 所有 `.py` 文件 |
| **配置文件** | `pyproject.toml`、`alembic.ini`、`.github/workflows/ci.yml` | 是 | 工具配置和 CI |
| **锁定文件** | `backend/uv.lock` | 是 | **已提交** — 确保可复现的构建 |
| **环境模板** | `backend/.env.example` | 是 | 模板；`.env` **未提交** |
| **文档** | `README.md`、`docs/` | 是 | 所有 markdown 文件 |
| **容器** | `backend/Dockerfile`、`docker-compose.yml` | 是 | Docker 配置 |
| **构建输出** | `backend/dist/` | **否** | 由 `uv build` 生成 |
| **虚拟环境** | `.venv/` | **否** | 由 `uv sync` 生成 |
| **缓存目录** | `__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/` | **否** | 自动重新生成 |
| **本地配置** | `.env`、`.env.local` | **否** | 特定于机器，包含密钥 |

---

## 4. Python 环境验证

> **工作目录**: 本节中的所有 `uv` 命令必须从 `backend/` 目录执行。

### 4.1 安装依赖项

导航到 backend 目录并安装所有依赖项：

**Windows (PowerShell)**：

```powershell
cd backend
uv sync --all-extras
```

**Linux/macOS (bash)**：

```bash
cd backend
uv sync --all-extras
```

**预期输出**：

```
Resolved XX packages in Xms
Installing XX packages...
 + alembic==1.x.x
 + annotated-types==0.x.x
 + ...
 + personal-memory-hub==0.1.0 (from file:///...)
 + ...
Installed XX packages in X.XXs
```

确切的包数量可能有所不同，但你应该看到：

- `personal-memory-hub==0.1.0`（项目本身）
- `sqlalchemy>=2.0`
- `pydantic>=2.0`
- `pydantic-settings>=2.0`
- `alembic>=1.13`
- `structlog>=24.0`
- `aiosqlite>=0.20`
- `pytest>=8.0`
- `pytest-asyncio>=0.23`
- `pytest-cov>=5.0`
- `ruff>=0.4`
- `mypy>=1.10`
- `psycopg2-binary` 或 `asyncpg`
- `coverage`

### 4.2 验证虚拟环境

**Windows (PowerShell)**：

```powershell
Get-ChildItem -Path .venv -Recurse -Depth 1 | Select-Object Name, Mode
```

**Linux/macOS (bash)**：

```bash
ls -la .venv/
```

**预期**: 存在 `.venv/` 目录，其中包含 `Scripts/`（Windows）或 `bin/`（Linux/macOS），内含 Python 可执行文件和已安装的包。

### 4.3 验证包安装

> **注意**: 本节验证核心包是否可导入。如需版本验证，请参阅第 7 节和第 8 节（使用 CLI 命令 `uv run ruff --version`、`uv run mypy --version`）。

**Windows (PowerShell)**：

```powershell
cd backend
uv run python -c "
import sqlalchemy, pydantic, alembic, structlog, aiosqlite, pytest
print('All core packages imported successfully')
print(f'SQLAlchemy: {sqlalchemy.__version__}')
print(f'Pydantic: {pydantic.__version__}')
print(f'Alembic: {alembic.__version__}')
print(f'structlog: {structlog.__version__}')
print(f'aiosqlite: {aiosqlite.__version__}')
print(f'pytest: {pytest.__version__}')
"
```

**Linux/macOS (bash)**：

```bash
cd backend
uv run python -c "
import sqlalchemy, pydantic, alembic, structlog, aiosqlite, pytest
print('All core packages imported successfully')
print(f'SQLAlchemy: {sqlalchemy.__version__}')
print(f'Pydantic: {pydantic.__version__}')
print(f'Alembic: {alembic.__version__}')
print(f'structlog: {structlog.__version__}')
print(f'aiosqlite: {aiosqlite.__version__}')
print(f'pytest: {pytest.__version__}')
"
```

**预期输出**：

```
All core packages imported successfully
SQLAlchemy: 2.0.x
Pydantic: 2.x.x
Alembic: 1.x.x
structlog: 24.x.x
aiosqlite: 0.2x.x
pytest: 8.x.x
```

### 4.4 常见问题

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `uv: command not found` | uv 未安装或不在 PATH 中 | 重新安装 uv，确保其在 PATH 中 |
| `No module named 'sqlalchemy'` | 未安装依赖项 | 运行 `uv sync --all-extras` |
| `Python version mismatch` | 项目要求 >=3.10 | 安装 Python 3.10+ |
| `Could not find a version that satisfies the requirement` | 该 Python 版本没有可用的包 | 检查包兼容性，尝试不同的 Python 版本 |

### 4.5 恢复步骤

如果验证失败：

**Windows (PowerShell)**：

```powershell
Remove-Item -Recurse -Force .venv
uv cache clean
uv sync --all-extras
```

**Linux/macOS (bash)**：

```bash
rm -rf .venv
uv cache clean
uv sync --all-extras
```

---

## 5. 配置验证

> **工作目录**: 本节中的所有命令必须从 `backend/` 目录执行。

### 5.1 复制 .env.example

**Windows (PowerShell)**：

```powershell
Copy-Item .env.example .env
```

**Linux/macOS (bash)**：

```bash
cp .env.example .env
```

### 5.2 环境变量

`.env.example` 文件记录了所有可配置变量。以下是完整参考：

#### 必需变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `APP_NAME` | `personal-memory-hub` | 应用程序名称 |
| `APP_VERSION` | `0.1.0` | 应用程序版本 |
| `APP_LOG_LEVEL` | `INFO` | 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL） |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/memory_hub` | PostgreSQL 连接字符串 |
| `DATABASE_ECHO` | `false` | 启用 SQL 查询日志 |
| `VECTOR_DIMENSION` | `1536` | 嵌入向量维度 |

#### 可选变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `SUPABASE_URL` | *（空）* | Supabase 项目 URL（用于托管 PostgreSQL） |
| `SUPABASE_ANON_KEY` | *（空）* | Supabase 匿名密钥 |
| `REDIS_URL` | *（空）* | Redis 连接 URL（V2+ 占位符） |
| `OPENROUTER_API_KEY` | *（空）* | OpenRouter API 密钥（推迟到 D3+） |

### 5.3 验证配置加载

**Windows (PowerShell)**：

```powershell
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
s = get_settings()
print(f'APP_NAME: {s.APP_NAME}')
print(f'LOG_LEVEL: {s.LOG_LEVEL}')
print(f'DATABASE_URL: {s.DATABASE_URL[:50]}...')
print(f'VECTOR_DIMENSION: {s.VECTOR_DIMENSION}')
print(f'is_supabase: {s.is_supabase}')
print('Configuration loaded successfully')
"
```

**Linux/macOS (bash)**：

```bash
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
s = get_settings()
print(f'APP_NAME: {s.APP_NAME}')
print(f'LOG_LEVEL: {s.LOG_LEVEL}')
print(f'DATABASE_URL: {s.DATABASE_URL[:50]}...')
print(f'VECTOR_DIMENSION: {s.VECTOR_DIMENSION}')
print(f'is_supabase: {s.is_supabase}')
print('Configuration loaded successfully')
"
```

**预期输出**：

```
APP_NAME: personal-memory-hub
LOG_LEVEL: INFO
DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:...
VECTOR_DIMENSION: 1536
is_supabase: False
Configuration loaded successfully
```

### 5.4 常见问题

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'backend'` | 工作目录不是 `backend/` | 运行前 `cd backend` |
| `PydanticSettingsError: Field "XXX" is not configured` | 缺少必需的环境变量 | 检查 `.env` 文件或环境变量 |
| `ValidationError` | 设置的值无效 | 检查变量类型和格式 |

---

## 6. 构建验证

> **工作目录**: 本节中的所有命令必须从 `backend/` 目录执行。

### 6.1 构建包

**Windows (PowerShell)**：

```powershell
uv build
```

**Linux/macOS (bash)**：

```bash
uv build
```

**预期输出**：

```
Building source distribution...
Building wheel from source distribution...
Successfully built dist\personal_memory_hub-0.1.0.tar.gz
Successfully built dist\personal_memory_hub-0.1.0-py3-none-any.whl
```

### 6.2 验证分发文件

**Windows (PowerShell)**：

```powershell
Get-ChildItem -Path dist
```

**Linux/macOS (bash)**：

```bash
ls -la dist/
```

**预期**: `dist/` 目录中有两个文件：

- `personal_memory_hub-0.1.0.tar.gz`（源分发）
- `personal_memory_hub-0.1.0-py3-none-any.whl`（wheel）

### 6.3 故障诊断

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `ValueError: Error parsing field project.license` | 无效的 license 字段 | 检查 `pyproject.toml` 中的 license 字段 |
| `OSError: Readme file does not exist: README.md` | 缺少 README.md | 创建 `backend/README.md` |
| `hatchling.build.build_editable failed` | 构建后端错误 | 检查 `pyproject.toml` 配置 |

---

## 7. Ruff 验证

> **工作目录**: 本节中的所有命令必须从 `backend/` 目录执行。

### 7.1 运行代码检查

**Windows (PowerShell)**：

```powershell
uv run ruff check src/ tests/
```

**Linux/macOS (bash)**：

```bash
uv run ruff check src/ tests/
```

**预期输出**：

```
All checks passed!
```

退出码应为 `0`。

### 7.2 验证 Ruff 版本

**Windows (PowerShell)**：

```powershell
uv run ruff --version
```

**Linux/macOS (bash)**：

```bash
uv run ruff --version
```

**预期输出**：

```
ruff 0.15.x
```

### 7.3 成功结果的样子

- 零违规报告
- 退出码 `0`
- 无警告

### 7.4 常见问题

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `F401 module imported but unused` | 未使用的导入 | 删除导入或使用它 |
| `E501 line too long` | 行超过 120 个字符 | 拆分该行 |
| `I001 import block is un-sorted` | 导入未排序 | 运行 `uv run ruff check --fix` |
| `UP035 import from collections.abc` | 使用了弃用的导入位置 | 将 `from typing import X` 改为 `from collections.abc import X` |

### 7.5 自动修复

如果 ruff 报告可修复的问题：

**Windows (PowerShell)**：

```powershell
uv run ruff check --fix src/ tests/
```

**Linux/macOS (bash)**：

```bash
uv run ruff check --fix src/ tests/
```

这将自动解决标记有 `[*]` 的问题。

---

## 8. mypy 验证

> **工作目录**: 本节中的所有命令必须从 `backend/` 目录执行。

### 8.1 运行类型检查

**Windows (PowerShell)**：

```powershell
uv run mypy src/
```

**Linux/macOS (bash)**：

```bash
uv run mypy src/
```

**预期输出**：

```
Success: no issues found in XX source files
```

退出码应为 `0`。

### 8.2 验证 mypy 版本

**Windows (PowerShell)**：

```powershell
uv run mypy --version
```

**Linux/macOS (bash)**：

```bash
uv run mypy --version
```

**预期输出**：

```
mypy 1.x.x
```

### 8.3 预期行为

- 全部 16 个源文件应通过类型检查
- 无未定义的变量
- 无类型不匹配
- 无缺失的返回类型注解

### 8.4 故障诊断

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `error: Name 'XXX' is not defined` | 未定义的变量或导入 | 添加导入或修复引用 |
| `error: Argument 1 to "XXX" has incompatible type` | 类型不匹配 | 修复类型注解或值 |
| `error: Function is missing a return type annotation` | 缺少返回类型 | 在函数签名中添加 `-> ReturnType` |
| `note: unused section(s)` | MyPy 配置中包含尚未导入的模块 | 无害 — 这些模块将在 D2+ 中导入 |

### 8.5 严格模式

项目使用 mypy 严格模式，其强制要求：

- `disallow_untyped_defs = true` — 所有函数必须有类型注解
- `disallow_incomplete_defs = true` — 所有类型注解必须完整
- `check_untyped_defs = true` — 类型检查器也检查未标注的函数
- `no_implicit_optional = true` — 可选类型需要显式 `| None`

---

## 9. pytest 验证

> **工作目录**: 本节中的所有命令必须从 `backend/` 目录执行。

### 9.1 运行测试

**Windows (PowerShell)**：

```powershell
uv run pytest tests/ -v
```

**Linux/macOS (bash)**：

```bash
uv run pytest tests/ -v
```

**预期输出**：

```
============================= test session starts ==============================
platform win32 -- Python 3.11.15, pytest-8.x.x, pluggy-1.x.x -- ...
cachedir: .pytest_cache
rootdir: .../backend
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.x.x, asyncio-0.26.x, cov-5.x.x
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 4 items

tests/test_fixtures.py::test_fixture_settings PASSED                     [ 25%]
tests/test_fixtures.py::test_fixture_container PASSED                    [ 50%]
tests/test_fixtures.py::test_fixture_test_engine PASSED                  [ 75%]
tests/test_smoke.py::test_pytest_works PASSED                            [100%]

============================== 4 passed in X.XXs ===============================
```

全部 4 个测试应通过。退出码应为 `0`。

### 9.2 测试描述

#### test_fixture_settings

**文件**: `tests/test_fixtures.py`  
**目的**: 验证 `settings` 夹具返回一个具有正确默认值的有效 `AppSettings` 实例。

**检查内容**：

- `settings` 是 `AppSettings` 的实例
- `settings.APP_NAME == "personal-memory-hub"`

#### test_fixture_container

**文件**: `tests/test_fixtures.py`  
**目的**: 验证 DI 容器正确解析 `AppSettings`。

**检查内容**：

- `container.resolve(AppSettings)` 返回一个 `AppSettings` 实例

#### test_fixture_test_engine

**文件**: `tests/test_fixtures.py`  
**目的**: 验证测试引擎夹具创建了有效的异步 SQLAlchemy 引擎。

**检查内容**：

- `test_engine` 不为 `None`
- `test_engine` 具有 `begin` 方法（异步引擎的特征）

#### test_pytest_works

**文件**: `tests/test_smoke.py`  
**目的**: 基本的冒烟测试，验证 pytest 的收集和执行正常工作。

**检查内容**：

- `True` 为 `True`（简单的断言 — 确认测试框架可用）

### 9.3 预期通过结果

- **收集了 4 个测试**
- **4 个测试通过**
- **0 个测试失败**
- **0 个测试出错**
- **退出码: 0**

### 9.4 常见问题

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'backend'` | `src/` 不在 Python 路径中 | 检查 `tests/conftest.py` 是否将 `src/` 添加到 `sys.path` |
| `ImportError: cannot import name 'XXX'` | 缺少依赖项 | 运行 `uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | 旧版本的 pytest-asyncio | 升级: `uv pip install --upgrade pytest-asyncio` |
| `Fixture 'XXX' not found` | conftest.py 中未定义夹具 | 检查 `tests/test_fixtures.py` 是否有该夹具 |

---

## 10. Docker 验证

> **注意**: 本节需要已安装并正在运行 Docker Desktop。如果无法使用 Docker，请跳过本节并在检查清单中注明。

> **工作目录**: 所有 Docker 命令必须从 **仓库根目录**（`personal-memory-hub/`）执行，而非 `backend/`。

### 10.1 启动 Docker Desktop

确保 Docker Desktop 正在运行。使用以下命令验证：

**Windows (PowerShell)**：

```powershell
docker info
```

**Linux/macOS (bash)**：

```bash
docker info
```

**预期输出**（截断）：

```
Client:
 Version:    24.x.x
Context:    desktop-linux
...

Server:
 Containers: 0
  Running: 0
  Paused: 0
  Stopped: 0
 Images: 0
 Server Version: 24.x.x
 Storage Driver: overlay2
...
```

### 10.2 启动服务

从仓库根目录：

**Windows (PowerShell)**：

```powershell
docker compose up -d db
```

**Linux/macOS (bash)**：

```bash
docker compose up -d db
```

**预期输出**：

```
[+] Running 2/2
 ✔ Network personal-memory-hub_default  Created
 ✔ Container memory-hub-db              Started
```

### 10.3 验证 PostgreSQL 容器

**Windows (PowerShell)**：

```powershell
docker compose ps
```

**Linux/macOS (bash)**：

```bash
docker compose ps
```

**预期输出**：

```
NAME            IMAGE                    STATUS
memory-hub-db   pgvector/pgvector:pg15   Up (healthy) ...
```

`db` 服务的状态应显示为 `Up (healthy)`。

### 10.4 验证 pgvector 扩展

连接到数据库并检查 pgvector：

**Windows (PowerShell)**：

```powershell
docker compose exec db psql -U postgres -d memory_hub -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

**Linux/macOS (bash)**：

```bash
docker compose exec db psql -U postgres -d memory_hub -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

**预期输出**：

```
 extname 
---------
 vector
(1 row)
```

### 10.5 验证网络

**Windows (PowerShell)**：

```powershell
docker network ls | Select-String "memory-hub"
```

**Linux/macOS (bash)**：

```bash
docker network ls | grep memory-hub
```

**预期**: 存在名为 `personal-memory-hub_default` 或类似的网络。

### 10.6 验证容器日志

**Windows (PowerShell)**：

```powershell
docker compose logs db
```

**Linux/macOS (bash)**：

```bash
docker compose logs db
```

**预期输出**（截断）：

```
memory-hub-db  | PostgreSQL Database directory appears to contain a database; Skipping initialization
memory-hub-db  | 2026-07-04 10:00:00.000 UTC [1] LOG:  starting PostgreSQL 15.x on ...
memory-hub-db  | 2026-07-04 10:00:00.000 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
memory-hub-db  | 2026-07-04 10:00:00.000 UTC [1] LOG:  database system is ready to accept connections
```

### 10.7 关闭流程

**Windows (PowerShell)**：

```powershell
docker compose down
```

**Linux/macOS (bash)**：

```bash
docker compose down
```

**预期输出**：

```
[+] Running 2/2
 ✔ Container memory-hub-db  Removed
 ✔ Network personal-memory-hub_default  Removed
```

### 10.8 故障诊断

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `Cannot connect to the Docker daemon` | Docker Desktop 未运行 | 启动 Docker Desktop |
| `port is already allocated` | 端口 5432 被占用 | 参见第 14.10 节的端口冲突解决方法 |
| `pgvector/pgvector:pg15 not found` | 镜像未拉取 | 运行 `docker pull pgvector/pgvector:pg15` |
| `permission denied` | Docker socket 权限 | 使用 sudo 运行（Linux）或检查 Docker Desktop 设置 |

---

## 11. 数据库验证

> **工作目录**: 本节中的所有命令必须从 `backend/` 目录执行。

### 11.1 验证 DATABASE_URL

**Windows (PowerShell)**：

```powershell
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
s = get_settings()
print(f'DATABASE_URL: {s.DATABASE_URL}')
print(f'DATABASE_ECHO: {s.DATABASE_ECHO}')
print(f'VECTOR_DIMENSION: {s.VECTOR_DIMENSION}')
"
```

**Linux/macOS (bash)**：

```bash
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
s = get_settings()
print(f'DATABASE_URL: {s.DATABASE_URL}')
print(f'DATABASE_ECHO: {s.DATABASE_ECHO}')
print(f'VECTOR_DIMENSION: {s.VECTOR_DIMENSION}')
"
```

**预期输出**：

```
DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/memory_hub
DATABASE_ECHO: False
VECTOR_DIMENSION: 1536
```

### 11.2 验证 SQLAlchemy 初始化

**Windows (PowerShell)**：

```powershell
uv run python -c "
from backend.shared.infrastructure.database.engine import Base, get_engine, get_session_factory
print(f'Base: {Base}')
print(f'Engine: {get_engine()}')
print(f'Session factory: {get_session_factory()}')
print('SQLAlchemy initialized successfully')
"
```

**Linux/macOS (bash)**：

```bash
uv run python -c "
from backend.shared.infrastructure.database.engine import Base, get_engine, get_session_factory
print(f'Base: {Base}')
print(f'Engine: {get_engine()}')
print(f'Session factory: {get_session_factory()}')
print('SQLAlchemy initialized successfully')
"
```

**预期输出**：

```
Base: <class 'backend.shared.infrastructure.database.engine.Base'>
Engine: <sqlalchemy.ext.asyncio.engine.AsyncEngine object at 0x...>
Session factory: async_sessionmaker(...)
SQLAlchemy initialized successfully
```

### 11.3 验证 Alembic 环境

> **工作目录**: `backend/`

**Windows (PowerShell)**：

```powershell
uv run alembic check
```

**Linux/macOS (bash)**：

```bash
uv run alembic check
```

**预期行为**：

- 如果 PostgreSQL 正在运行且可访问：Alembic 连接并报告当前迁移状态
- 如果 PostgreSQL **未运行**：Alembic 报告连接错误（这在 D1 中是预期的 — 基础设施完成不需要数据库）

**带数据库的预期输出示例**：

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**不带数据库的预期输出示例**：

```
ConnectionRefusedError: [WinError 1225] ...
```

或

```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionRefusedError) connection refused
```

> **重要**: 错误必须是连接错误（例如 `ConnectionRefusedError`、`OperationalError`），而不是 `NoSuchModuleError` 或 `Can't load plugin: sqlalchemy.dialects:driver` 错误。如果遇到后者，请参阅第 14.11 节。

这是 **预期且可接受的** D1 行为。Alembic 环境已正确配置；只是由于本地没有运行 PostgreSQL 实例而无法连接。

### 11.4 解释无迁移时的预期行为

在 D1 完成时：

- `backend/alembic/versions/` 中 **不存在** 任何迁移文件
- **Alembic history** 将显示空的修订图
- **Alembic current** 将报告 "No migrations present"
- 这是 **正确的** — D1 仅设置迁移框架。实际的迁移文件将在 D2 中定义域模型时创建

验证方式：

**Windows (PowerShell)**：

```powershell
uv run alembic history
```

**Linux/macOS (bash)**：

```bash
uv run alembic history
```

**预期输出**（如果数据库可访问）：

```
Head (revision): <none>
```

或如果没有数据库：

```
(ConnectionRefusedError — 预期，没有运行数据库)
```

---

## 12. 文档验证

### 12.1 验证 README

检查 `README.md` 是否存在并包含预期的章节。

**Windows (PowerShell)**：

```powershell
Get-Content README.md
```

**Linux/macOS (bash)**：

```bash
cat README.md
```

**预期章节**：

- 项目标题和描述
- 快速入门（前置条件、本地开发、Docker）
- 项目结构
- 架构概述
- 实现里程碑表格
- 开发部分（编码标准、审查流程）
- 许可证

### 12.2 验证文档链接

README 应引用：

- `docs/INDEX.md` — 架构文档索引
- `docs/05_Implementation/` — 实现计划

通过检查引用的文件是否存在来验证链接是否完好：

**Windows (PowerShell)**：

```powershell
if (Test-Path docs/INDEX.md) { Write-Output "INDEX.md exists" } else { Write-Output "INDEX.md MISSING" }
if (Test-Path docs/05_Implementation/README.md) { Write-Output "Implementation README exists" } else { Write-Output "MISSING" }
if (Test-Path docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md) { Write-Output "D1 Plan exists" } else { Write-Output "MISSING" }
```

**Linux/macOS (bash)**：

```bash
test -f docs/INDEX.md && echo "INDEX.md exists" || echo "INDEX.md MISSING"
test -f docs/05_Implementation/README.md && echo "Implementation README exists" || echo "MISSING"
test -f docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md && echo "D1 Plan exists" || echo "MISSING"
```

**预期输出**：

```
INDEX.md exists
Implementation README exists
D1 Plan exists
```

### 12.3 验证文档结构

**Windows (PowerShell)**：

```powershell
Get-ChildItem -Path docs -Recurse -Filter "*.md" | Sort-Object FullName
```

**Linux/macOS (bash)**：

```bash
find docs -type f -name "*.md" | sort
```

**预期**: 列出所有架构和实现文档，包括：

- `docs/INDEX.md`
- `docs/05_Implementation/README.md`
- `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md`
- 所有阶段 A、B、C 的文档（来自之前的阶段）

---

## 13. 最终验收检查清单

使用此检查清单确认 D1 完成。将每项标记为已完成（✓）或注明任何问题。

### 13.1 仓库

- [ ] 仓库克隆成功
- [ ] 目录结构与预期一致
- [ ] 所有预期文件存在（见第 3.3 节）
- [ ] `docs/INDEX.md` 已更新，包含 Phase D 部分
- [ ] `docs/05_Implementation/README.md` 存在
- [ ] `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` 存在

### 13.2 文件分类

参考第 3.4 节的分类表格。关键检查：

- [ ] `backend/uv.lock` 存在（锁定文件 — 必须提交）
- [ ] `backend/dist/` **不存在**（构建输出 — 应被忽略）
- [ ] `backend/.venv/` **不存在**（虚拟环境 — 应被忽略）
- [ ] `__pycache__/` 目录 **不存在**（缓存 — 应被忽略）

### 13.3 Python 环境

- [ ] `uv sync --all-extras` 顺利完成，无错误
- [ ] 虚拟环境 `.venv/` 存在
- [ ] 所有核心包可导入（第 4.3 节）
- [ ] `uv build` 生成 `.tar.gz` 和 `.whl` 文件

### 13.4 配置

- [ ] `.env.example` 存在且有文档说明
- [ ] Settings 模块加载无误
- [ ] 所有环境变量具有正确的默认值
- [ ] `is_supabase` 属性在 Supabase 配置为空时返回 `False`

### 13.5 代码质量

- [ ] `ruff check src/ tests/` 报告零违规
- [ ] `mypy src/` 报告 "Success: no issues found"
- [ ] 所有源文件在严格模式下通过类型检查

### 13.6 测试

- [ ] `pytest tests/ -v` 收集了 4 个测试
- [ ] 全部 4 个测试通过
- [ ] 测试夹具（settings、container、engine）工作正常
- [ ] 测试输出中无警告或错误

### 13.7 Docker（可选 — 如无 Docker 则跳过）

- [ ] `docker compose up -d db` 成功启动 PostgreSQL
- [ ] 容器状态为 `Up (healthy)`
- [ ] pgvector 扩展已安装
- [ ] `docker compose down` 干净关闭

### 13.8 数据库基础设施

- [ ] SQLAlchemy 引擎初始化成功
- [ ] 会话工厂已配置
- [ ] 声明式基类 `Base` 可导入
- [ ] Alembic `env.py` 导入正常
- [ ] Alembic 迁移目录存在（预期为空）

### 13.9 文档

- [ ] `README.md` 存在且包含所有预期章节
- [ ] `backend/README.md` 存在
- [ ] `docs/05_Implementation/README.md` 存在
- [ ] 所有文档链接指向存在的文件
- [ ] 无损坏的引用

### 13.10 Git 就绪性

验证 `.gitignore` 正确排除了生成的文件并包含了已提交的文件：

**Windows (PowerShell)**：

```powershell
# Check that uv.lock is NOT ignored
if (-not (git check-ignore -q backend/uv.lock 2>$null)) { Write-Output "uv.lock is tracked (correct)" } else { Write-Output "uv.lock is ignored (wrong)" }

# Check that dist/ IS ignored
if (git check-ignore -q backend/dist/ 2>$null) { Write-Output "dist/ is ignored (correct)" } else { Write-Output "dist/ is tracked (wrong)" }

# Check that .venv/ IS ignored
if (git check-ignore -q backend/.venv/ 2>$null) { Write-Output ".venv/ is ignored (correct)" } else { Write-Output ".venv/ is tracked (wrong)" }

# Check that __pycache__/ IS ignored
if (git check-ignore -q backend/src/backend/__pycache__/ 2>$null) { Write-Output "__pycache__/ is ignored (correct)" } else { Write-Output "__pycache__/ is tracked (wrong)" }

# Check that .env IS ignored
if (git check-ignore -q backend/.env 2>$null) { Write-Output ".env is ignored (correct)" } else { Write-Output ".env is tracked (wrong)" }
```

**Linux/macOS (bash)**：

```bash
# Check that uv.lock is NOT ignored
git check-ignore -v backend/uv.lock 2>&1 || echo "uv.lock is tracked (correct)"

# Check that dist/ IS ignored
git check-ignore -v backend/dist/ 2>&1 && echo "dist/ is ignored (correct)" || echo "dist/ is tracked (wrong)"

# Check that .venv/ IS ignored
git check-ignore -v backend/.venv/ 2>&1 && echo ".venv/ is ignored (correct)" || echo ".venv/ is tracked (wrong)"

# Check that __pycache__/ IS ignored
git check-ignore -v backend/src/backend/__pycache__/ 2>&1 && echo "__pycache__/ is ignored (correct)" || echo "__pycache__/ is tracked (wrong)"

# Check that .env IS ignored
git check-ignore -v backend/.env 2>&1 && echo ".env is ignored (correct)" || echo ".env is tracked (wrong)"
```

**预期**: `uv.lock` 应 **不被** 忽略；其他都应被忽略。

### 13.11 架构合规性

- [ ] `service/`、`engine/` 或 `repository/` 目录中无业务逻辑
- [ ] 所有空目录都包含 `__init__.py` 文件
- [ ] 测试目录包含 README 占位符
- [ ] 尊重层级边界（跨层导入仅通过协议进行）

---

## 14. 故障排查

### 14.1 uv sync 失败

**症状**：

```
× No solution found when resolving dependencies
```

**原因**：

- 包版本约束不兼容
- 网络连接问题导致包下载失败
- uv 缓存损坏

**解决方法**：

**Windows (PowerShell)**：

```powershell
uv cache clean
uv sync --all-extras
python --version  # Must be >= 3.10
Get-Content backend\pyproject.toml -TotalCount 50
```

**Linux/macOS (bash)**：

```bash
uv cache clean
uv sync --all-extras
python --version  # Must be >= 3.10
head -50 backend/pyproject.toml
```

### 14.2 ruff 报错

**症状**：

```
F401 `typing.Any` imported but unused
```

**原因**：

- 死代码导入
- 未排序的导入
- 行长度违规

**解决方法**：

**Windows (PowerShell)**：

```powershell
uv run ruff check --fix src/ tests/
```

**Linux/macOS (bash)**：

```bash
uv run ruff check --fix src/ tests/
```

对于剩余问题，手动编辑源文件。

### 14.3 mypy 报错

**症状**：

```
error: Unused "type: ignore" comment
error: Function is missing a return type annotation
```

**原因**：

- 过期的 type ignore 注释
- 缺少类型注解
- 类型不匹配

**解决方法**：

**Windows (PowerShell)**：

```powershell
uv run mypy src/ --show-error-codes
```

**Linux/macOS (bash)**：

```bash
uv run mypy src/ --show-error-codes
```

根据需要修复类型注解。移除过时的 `type: ignore` 注释。

### 14.4 pytest 无法收集测试

**症状**：

```
collected 0 items
```

**原因**：

- 测试文件不在 `tests/` 目录中
- 测试文件未命名为 `test_*.py`
- Python 路径配置不正确

**解决方法**：

**Windows (PowerShell)**：

```powershell
Get-ChildItem tests\test_*.py
Get-ChildItem tests\conftest.py
uv run pytest tests/ --collect-only -v
```

**Linux/macOS (bash)**：

```bash
ls tests/test_*.py
ls tests/conftest.py
uv run pytest tests/ --collect-only -v
```

### 14.5 Docker Compose 失败

**症状**：

```
ERROR: Cannot connect to the Docker daemon
```

**原因**：

- Docker Desktop 未运行
- 权限不足
- 端口冲突

**解决方法**：

**Windows (PowerShell)**：

```powershell
# Start Docker Desktop (Windows/macOS)
# Or start Docker service (Linux)
docker info

# Check for port conflicts
netstat -an | findstr 5432

# If port is in use, change it in docker-compose.yml or .env
```

**Linux/macOS (bash)**：

```bash
sudo systemctl start docker
docker info
netstat -an | grep 5432
```

### 14.6 Settings 模块加载失败

**症状**：

```
pydantic_core.ValidationError: 1 validation error for AppSettings
```

**原因**：

- 环境变量格式无效
- 缺少必需变量
- 类型不匹配

**解决方法**：

**Windows (PowerShell)**：

```powershell
Get-Content .env
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
try:
    s = get_settings()
    print('OK')
except Exception as e:
    print(f'Error: {e}')
"
```

**Linux/macOS (bash)**：

```bash
cat .env
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
try:
    s = get_settings()
    print('OK')
except Exception as e:
    print(f'Error: {e}')
"
```

### 14.7 Alembic 连接失败

**症状**：

```
ConnectionRefusedError: [WinError 1225] ...
```

或

```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionRefusedError) connection refused
```

**原因**：

- PostgreSQL 未运行
- DATABASE_URL 不正确
- 防火墙阻止连接

**解决方法**：

> 如果未运行 PostgreSQL，这在 D1 中是 **预期的**。基础设施已正确配置；只是无法连接。

**Windows (PowerShell)**：

```powershell
# To verify the configuration is correct (without a running database):
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
from backend.shared.infrastructure.database.engine import get_engine
s = get_settings()
print(f'DATABASE_URL configured: {s.DATABASE_URL[:50]}...')
engine = get_engine()
print(f'Engine created: {type(engine).__name__}')
print('Configuration is correct — connection failure is expected without running database')
"
```

**Linux/macOS (bash)**：

```bash
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
from backend.shared.infrastructure.database.engine import get_engine
s = get_settings()
print(f'DATABASE_URL configured: {s.DATABASE_URL[:50]}...')
engine = get_engine()
print(f'Engine created: {type(engine).__name__}')
print('Configuration is correct — connection failure is expected without running database')
"
```

### 14.8 测试中的导入错误

**症状**：

```
ModuleNotFoundError: No module named 'backend'
```

**原因**：

- `src/` 不在 Python 路径中
- 工作目录不正确

**解决方法**：

**Windows (PowerShell)**：

```powershell
cd backend
Get-Content tests\conftest.py -TotalCount 15
uv run pytest tests/ -v
```

**Linux/macOS (bash)**：

```bash
cd backend
head -15 tests/conftest.py
uv run pytest tests/ -v
```

### 14.9 构建失败

**症状**：

```
ValueError: Error parsing field project.license
```

**原因**：

- `pyproject.toml` 中 license 字段无效
- 缺少 README.md

**解决方法**：

**Windows (PowerShell)**：

```powershell
Select-String -Path backend\pyproject.toml -Pattern "license"
Get-ChildItem backend\README.md
```

**Linux/macOS (bash)**：

```bash
grep license backend/pyproject.toml
ls backend/README.md
```

### 14.10 Docker 端口冲突（端口 5432 已被占用）

**症状**：

```
ERROR: for db Cannot start service 'db': driver failed programming external connectivity on endpoint memory-hub-db: Bind for 0.0.0.0:5432 failed: port is already allocated
```

或

```
port is already allocated
```

**原因**：

- 另一台 PostgreSQL 实例正在机器上运行（例如来自不同项目、WSL 或系统服务）
- 数据库管理工具有打开的连接

**识别冲突进程**：

**Windows (PowerShell)**：

```powershell
netstat -ano | findstr ":5432"
```

**Linux/macOS (bash)**：

```bash
netstat -tlnp | grep 5432
```

这将显示使用端口 5432 的进程的 PID。

**解决方法 1 — 停止冲突的服务**：

如果你不再需要另一个 PostgreSQL 实例，请停止它。在 Windows 上，检查任务管理器中的 `postgres.exe` 或 `pgAdmin`。在 Linux 上：

```bash
sudo systemctl stop postgresql
```

**解决方法 2 — 使用不同的主机端口**：

如果需要保留另一个 PostgreSQL 运行，更改 `docker-compose.yml` 中的主机端口映射：

1. 打开 `docker-compose.yml`
2. 找到 `db` 服务的 `ports` 部分
3. 将 `5432:5432` 更改为 `5433:5432`（或其他可用端口）

```yaml
services:
  db:
    ports:
      - "5433:5432"  # Host port 5433 → container port 5432
```

4. 更新 `.env` 以反映新的主机端口：

```
DB_HOST=localhost
DB_PORT=5433
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/memory_hub
```

5. 重启 Docker：

```bash
docker compose down
docker compose up -d db
```

**解决方法 3 — 恢复默认配置**：

在冲突服务已停止后，恢复到默认的 5432 端口：

1. 将 `docker-compose.yml` 恢复为使用 `5432:5432`
2. 将 `.env` 恢复为使用端口 5432
3. 重启：

```bash
docker compose down
docker compose up -d db
```

### 14.11 Alembic 显示 "driver://" 插件错误

**症状**：

```
sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:driver
```

**原因**：

此错误发生在 `alembic.ini` 包含占位符 `sqlalchemy.url = driver://user:pass@localhost/dbname` 时。SQLAlchemy 方言解析器试图加载一个名为 `driver` 的方言插件，但该插件不存在。

**解决方法**：

这已在 D1.1 中修复。`alembic.ini` 文件现在具有 `sqlalchemy.url =`（空白），`alembic/env.py` 在运行时从应用 Settings 填充 URL。如果遇到此错误，请确保你的 `alembic.ini` 第 89 行读取：

```ini
sqlalchemy.url =
```

（而不是 `driver://user:pass@localhost/dbname`）

---

## 附录 A：文件清单

### A.1 源文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `src/backend/__init__.py` | ~10 | 包标记 |
| `src/backend/shared/__init__.py` | ~3 | 共享模块标记 |
| `src/backend/shared/domain/__init__.py` | ~5 | 领域模块标记（D1 为空） |
| `src/backend/shared/infrastructure/__init__.py` | ~3 | 基础设施模块标记 |
| `src/backend/shared/infrastructure/config/__init__.py` | ~8 | 配置导出 |
| `src/backend/shared/infrastructure/config/settings.py` | ~100 | 设置模型 |
| `src/backend/shared/infrastructure/database/__init__.py` | ~8 | 数据库导出 |
| `src/backend/shared/infrastructure/database/engine.py` | ~110 | 引擎、会话、Base |
| `src/backend/shared/infrastructure/di/__init__.py` | ~8 | DI 导出 |
| `src/backend/shared/infrastructure/di/container.py` | ~100 | DI 容器 |
| `src/backend/shared/infrastructure/logging/__init__.py` | ~55 | 日志工厂 |
| `src/backend/protocols/__init__.py` | ~5 | 协议标记 |
| `src/backend/scripts/README.md` | ~3 | 脚本占位符 |
| `src/backend/tools/README.md` | ~3 | 工具占位符 |
| `src/backend/entry/__init__.py` | ~4 | 入口层标记（空） |
| `src/backend/service/__init__.py` | ~4 | 服务层标记（空） |
| `src/backend/engine/__init__.py` | ~4 | 引擎层标记（空） |
| `src/backend/repository/__init__.py` | ~4 | 仓储层标记（空） |

### A.2 测试文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `tests/conftest.py` | ~15 | Pytest 路径配置 |
| `tests/test_fixtures.py` | ~95 | 夹具测试（4 个测试） |
| `tests/test_smoke.py` | ~10 | 冒烟测试 |

### A.3 配置文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `backend/pyproject.toml` | ~140 | 项目配置、依赖项、工具设置 |
| `backend/.env.example` | ~50 | 环境变量模板 |
| `backend/alembic.ini` | ~150 | Alembic 配置 |
| `backend/alembic/env.py` | ~100 | Alembic 环境 |
| `backend/Dockerfile` | ~50 | 多阶段 Docker 构建 |
| `docker-compose.yml` | ~80 | 本地开发服务 |
| `.github/workflows/ci.yml` | ~100 | CI 流水线 |
| `.gitignore` | ~60 | Git 忽略模式 |

### A.4 文档文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `README.md` | ~140 | 项目概述 |
| `backend/README.md` | ~10 | 后端包概述 |
| `docs/05_Implementation/README.md` | ~80 | 实现阶段概述 |
| `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` | ~400 | D1 规划文档 |
| `docs/INDEX.md` | ~200 | 文档索引（已为 D1 更新） |
| `docs/06_Guides/D1_Verification_Guide.md` | 本文档 | 验证指南 |

---

## 附录 B：命令快速参考

本附录中的所有命令均可直接复制粘贴使用。从每个命令下方注明的路径执行。

```powershell
# === From repository root (personal-memory-hub/) ===
git clone https://github.com/lys1335/personal-memory-hub.git
cd personal-memory-hub

# === From backend/ directory ===
cd backend

# Install dependencies
uv sync --all-extras

# Run linting
uv run ruff check src/ tests/

# Verify ruff version
uv run ruff --version

# Run type checking
uv run mypy src/

# Verify mypy version
uv run mypy --version

# Run tests
uv run pytest tests/ -v

# Build package
uv build

# Verify settings
uv run python -c "from backend.shared.infrastructure.config.settings import get_settings; print(get_settings().APP_NAME)"

# Verify logging
uv run python -c "from backend.shared.infrastructure.logging import configure_logging, get_logger; configure_logging(); get_logger('test').info('hello')"

# Verify database infrastructure
uv run python -c "from backend.shared.infrastructure.database.engine import Base, get_engine; print(get_engine())"

# Verify DI container
uv run python -c "from backend.shared.infrastructure.di import get_container; from backend.shared.infrastructure.config.settings import AppSettings; c=get_container(); print(c.resolve(AppSettings).APP_NAME)"

# Run Alembic check (requires running PostgreSQL)
uv run alembic check

# === From repository root (personal-memory-hub/) ===
# Docker: start database
docker compose up -d db

# Docker: check status
docker compose ps

# Docker: stop
docker compose down
```

---

> **本指南是动态文档。** 随着 D1 实施的演进，请更新此文档。
> 
> **下一个里程碑**: D2 — 仓储层（计划中）
> 
> **文档版本**: 1.1 | **最后更新**: 2026-07-04（D1.1 发布就绪修复）
