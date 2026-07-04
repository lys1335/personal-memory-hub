# D1 验证指南

> **阶段**: Phase D — 基于文档的驱动式实施  
> **里程碑**: D1 — 基础设施基础  
> **版本**: 1.0  
> **日期**: 2026-07-04  
> **状态**: 最终版  
> **作者**: 系统架构组  

---

本文档为英文正式版本（Canonical Version）的简体中文本地化版本。

英文原文：

docs/06_Guides/D1_Verification_Guide.md

如中英文存在任何差异，以英文版本为准。

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
13. [最终验收清单](#13-最终验收清单)  
14. [故障排查](#14-故障排查)  

---

## 1. 目的

### 1.1 本指南验证什么

本指南用于验证 **D1 — 基础设施基础** 是否已正确实现。D1 为 Personal Memory Hub 项目建立了工程基线：

- 五层架构的项目目录结构
- 通过 `pyproject.toml` 和 `uv` 配置的 Python 包管理
- 基于 pydantic-settings 的配置系统
- 基于 structlog 的结构化 JSON 日志
- SQLAlchemy 异步引擎与会话工厂
- Alembic 迁移框架
- 轻量级依赖注入容器
- 基于内存 SQLite 固定夹具的 pytest 测试框架
- 用于本地开发的 Docker 和 docker-compose
- GitHub Actions CI 流水线脚手架
- 文档（README、安装指南）

### 1.2 本指南不验证什么

以下内容明确 **不在** D1 验证范围内：

- **业务逻辑** — Service、Engine、Repository 的实现尚不存在（D2+）
- **数据库 Schema** — 表模型或迁移文件尚不存在（D2）
- **API 端点** — REST、MCP 或 CLI 适配器尚不存在（D5）
- **生产部署** — CD 流水线有意推迟
- **外部集成** — Supabase、Redis、OpenRouter 不是 D1 的必需项
- **性能基准** — D1 不进行压力测试

### 1.3 验证理念

本指南面向 **对项目毫无了解** 的开发者设计。每条命令均可直接复制粘贴执行。每个预期结果均已记录。如果某步骤失败，故障排查章节提供了诊断方法和解决方案。

---

## 2. 前置条件

开始验证之前，请确保以下工具已安装。

### 2.1 操作系统

**支持的平台**：

- Windows 10/11（64 位）
- macOS 12+（Monterey 或更高版本）
- Ubuntu 20.04+ / Debian 11+ / Fedora 38+

**本指南默认使用 Windows 风格的路径和命令。** 如果使用 Linux/macOS，请相应调整命令（例如使用 `./` 代替 `.venv\Scripts\`，使用 `python3` 代替 `python`）。

### 2.2 Python

- **必需**：Python 3.11 或 3.12
- **最低要求**：Python 3.10（项目声明了 `requires-python = ">=3.10"`）

**下载地址**：https://www.python.org/downloads/

**验证安装**：

```bash
python --version
```

**预期输出**：

```
Python 3.11.x
```

如果未安装 Python 或版本低于 3.10，请先安装再继续。

### 2.3 uv

- **必需**：uv 0.4.0 或更高版本
- **用途**：快速 Python 包安装器和项目管理器

**下载地址**：https://docs.astral.sh/uv/getting-started/installation/

**在 Windows 上安装**（PowerShell）：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**在 Linux/macOS 上安装**（终端）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**验证安装**：

```bash
uv --version
```

**预期输出**：

```
uv 0.x.x (xxx...)
```

### 2.4 Docker Desktop

- **必需**：Docker Desktop 4.0+（或 Docker Engine + docker-compose 插件）
- **用途**：包含 PostgreSQL + pgvector 的本地开发环境

**下载地址**：https://www.docker.com/products/docker-desktop/

**验证安装**：

```bash
docker --version
docker compose version
```

**预期输出**：

```
Docker version 24.x.x, build xxxxxxx
Docker Compose version v2.x.x
```

如果未安装 Docker Desktop，可以跳过 Docker 相关验证步骤（第 10 节）。D1 其余部分不依赖 Docker。

### 2.5 Git

- **必需**：Git 2.40+
- **用途**：克隆代码仓库

**下载地址**：https://git-scm.com/downloads

**验证安装**：

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
remote: Total XXXX (delta XX), reused XXXX (delta XX), pack-reused XX
Receiving objects: 100% (XXXX/XXXX), X.XX MiB | X.XX MiB/s, done.
Resolving deltas: 100% (XX/XX), done.
```

### 3.2 预期的目录结构

克隆完成后，仓库根目录应包含以下内容：

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

**验证方法**：使用以下命令检查目录结构：

```bash
find backend -type f ! -path "*/.venv/*" ! -path "*/.mypy_cache/*" ! -path "*/.pytest_cache/*" ! -path "*/.ruff_cache/*" ! -path "*/dist/*" ! -path "*/__pycache__/*" | sort
```

**预期**：输出应列出上述所有文件（不含 `uv.lock` 和 `dist/`，这两者是生成的）。

### 3.3 预期的关键文件

以下文件必须存在：

| 文件 | 用途 |
|------|------|
| `backend/pyproject.toml` | 项目配置、依赖、工具设置 |
| `backend/.env.example` | 环境变量模板 |
| `backend/src/backend/shared/infrastructure/config/settings.py` | 配置系统 |
| `backend/src/backend/shared/infrastructure/logging/__init__.py` | 日志框架 |
| `backend/src/backend/shared/infrastructure/database/engine.py` | SQLAlchemy 引擎/会话 |
| `backend/src/backend/shared/infrastructure/di/container.py` | 依赖注入容器 |
| `backend/src/backend/shared/infrastructure/database/__init__.py` | 数据库导出模块 |
| `backend/alembic/env.py` | Alembic 环境配置 |
| `backend/Dockerfile` | 容器构建文件 |
| `docker-compose.yml` | 本地开发环境 |
| `.github/workflows/ci.yml` | CI 流水线 |
| `README.md` | 项目概览 |
| `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` | D1 计划文档 |

---

## 4. Python 环境验证

### 4.1 安装依赖

进入 backend 目录并安装所有依赖：

```bash
cd backend
uv sync --all-extras
```

**预期输出**：

```
Resolved XX packages in Xms
InstallingXX packages...
 + alembic==1.x.x
 + annotated-types==0.x.x
 + ...
 + personal-memory-hub==0.1.0 (from file:///...)
 + ...
Installed XX packages in X.XXs
```

具体包数量可能有所不同，但你应该能看到以下包：

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

```bash
ls -la .venv/
```

**预期**：存在 `.venv/` 目录，其中包含 `Scripts/`（Windows）或 `bin/`（Linux/macOS），内含 Python 可执行文件和已安装的包。

### 4.3 验证包安装

```bash
uv run python -c "
import sqlalchemy, pydantic, alembic, structlog, aiosqlite, pytest, ruff, mypy
print('All core packages imported successfully')
print(f'SQLAlchemy: {sqlalchemy.__version__}')
print(f'Pydantic: {pydantic.__version__}')
print(f'Alembic: {alembic.__version__}')
print(f'structlog: {structlog.__version__}')
print(f'aiosqlite: {aiosqlite.__version__}')
print(f'pytest: {pytest.__version__}')
print(f'ruff: {ruff.__version__}')
print(f'mypy: {mypy.__version__}')
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
ruff: 0.15.x
mypy: 1.x.x
```

### 4.4 常见问题

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `uv: command not found` | uv 未安装或未加入 PATH | 重新安装 uv，确保其位于 PATH 中 |
| `No module named 'sqlalchemy'` | 依赖未安装 | 运行 `uv sync --all-extras` |
| `Python version mismatch` | 项目要求 >=3.10 | 安装 Python 3.10+ |
| `Could not find a version that satisfies the requirement` | 该 Python 版本下无可用包 | 检查包兼容性，尝试其他 Python 版本 |

### 4.5 恢复步骤

如果验证失败：

1. 删除虚拟环境：`rm -rf .venv`
2. 清除 uv 缓存：`uv cache clean`
3. 重新安装：`uv sync --all-extras`
4. 重新执行验证

---

## 5. 配置验证

### 5.1 复制 .env.example

```bash
cp .env.example .env
```

Windows（PowerShell）环境下：

```powershell
Copy-Item .env.example .env
```

### 5.2 环境变量

`.env.example` 文件记录了所有可配置变量。以下是完整参考：

#### 必需变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | `personal-memory-hub` | 应用名称 |
| `APP_VERSION` | `0.1.0` | 应用版本 |
| `APP_LOG_LEVEL` | `INFO` | 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL） |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/memory_hub` | PostgreSQL 连接字符串 |
| `DATABASE_ECHO` | `false` | 启用 SQL 查询日志 |
| `VECTOR_DIMENSION` | `1536` | 嵌入向量维度 |

#### 可选变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SUPABASE_URL` | *（空）* | Supabase 项目 URL（用于托管 PostgreSQL） |
| `SUPABASE_ANON_KEY` | *（空）* | Supabase 匿名密钥 |
| `REDIS_URL` | *（空）* | Redis 连接 URL（V2+ 占位符） |
| `OPENROUTER_API_KEY` | *（空）* | OpenRouter API 密钥（推迟至 D3+） |

### 5.3 验证配置加载

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
| `ModuleNotFoundError: No module named 'backend'` | 工作目录不是 `backend/` | 运行前执行 `cd backend` |
| `PydanticSettingsError: Field "XXX" is not configured` | 缺少必需的环境变量 | 检查 `.env` 文件或环境变量 |
| `ValidationError` | 设置值无效 | 检查变量类型和格式 |

---

## 6. 构建验证

### 6.1 构建包

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

```bash
ls -la dist/
```

**预期**：`dist/` 目录下有两个文件：

- `personal_memory_hub-0.1.0.tar.gz`（源码发行版）
- `personal_memory_hub-0.1.0-py3-none-any.whl`（wheel）

### 6.3 故障诊断

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `ValueError: Error parsing field project.license` | license 字段无效 | 检查 `pyproject.toml` 中的 license 字段 |
| `OSError: Readme file does not exist: README.md` | 缺少 README.md | 创建 `backend/README.md` |
| `hatchling.build.build_editable failed` | 构建后端错误 | 检查 `pyproject.toml` 配置 |

---

## 7. Ruff 验证

### 7.1 运行代码检查

```bash
uv run ruff check src/ tests/
```

**预期输出**：

```
All checks passed!
```

退出码应为 `0`。

### 7.2 成功结果的特征

- 零违规
- 退出码 `0`
- 无警告

### 7.3 常见问题

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `F401 module imported but unused` | 未使用的导入 | 移除该导入或使用它 |
| `E501 line too long` | 行长度超过 120 字符 | 拆分该行 |
| `I001 import block is un-sorted` | 导入未排序 | 运行 `uv run ruff check --fix` |
| `UP035 import from collections.abc` | 使用了过时的导入位置 | 将 `from typing import X` 改为 `from collections.abc import X` |

### 7.4 自动修复

如果 ruff 报告可修复的问题：

```bash
uv run ruff check --fix src/ tests/
```

这将自动解决标记为 `[*]` 的问题。

---

## 8. mypy 验证

### 8.1 运行类型检查

```bash
uv run mypy src/
```

**预期输出**：

```
Success: no issues found in XX source files
```

退出码应为 `0`。

### 8.2 预期行为

- 全部 16 个源文件通过类型检查
- 无未定义的名称
- 无类型不匹配
- 无缺失的返回值类型注解

### 8.3 故障诊断

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `error: Name 'XXX' is not defined` | 未定义的变量或导入 | 添加导入或修正引用 |
| `error: Argument 1 to "XXX" has incompatible type` | 类型不匹配 | 修正类型注解或值 |
| `error: Function is missing a return type annotation` | 缺少返回类型 | 在函数签名中添加 `-> ReturnType` |
| `note: unused section(s)` | MyPy 配置中针对尚未导入模块的段落 | 无害 — 这些模块将在 D2+ 中被导入 |

### 8.4 严格模式

项目使用 mypy 严格模式，强制执行以下规则：

- `disallow_untyped_defs = true` — 所有函数必须有类型注解
- `disallow_incomplete_defs = true` — 所有类型注解必须完整
- `check_untyped_defs = true` — 类型检查器也检查未加注解的函数
- `no_implicit_optional = true` — 可选类型必须显式使用 `| None`

---

## 9. pytest 验证

### 9.1 运行测试

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

### 9.2 测试说明

#### test_fixture_settings

**文件**：`tests/test_fixtures.py`  
**目的**：验证 `settings` 固定夹具返回一个具有正确默认值的 `AppSettings` 实例。

**验证内容**：

- `settings` 是 `AppSettings` 的实例
- `settings.APP_NAME == "personal-memory-hub"`

#### test_fixture_container

**文件**：`tests/test_fixtures.py`  
**目的**：验证 DI 容器正确解析 `AppSettings`。

**验证内容**：

- `container.resolve(AppSettings)` 返回 `AppSettings` 实例

#### test_fixture_test_engine

**文件**：`tests/test_fixtures.py`  
**目的**：验证测试引擎固定夹具创建了有效的异步 SQLAlchemy 引擎。

**验证内容**：

- `test_engine` 不为 `None`
- `test_engine` 具有 `begin` 方法（异步引擎特征）

#### test_pytest_works

**文件**：`tests/test_smoke.py`  
**目的**：基础冒烟测试，验证 pytest 的收集和执行功能正常工作。

**验证内容**：

- `True` 等于 `True`（平凡断言 — 确认测试框架可运行）

### 9.3 预期通过结果

- **收集到 4 个测试**
- **4 个测试通过**
- **0 个测试失败**
- **0 个测试出错**
- **退出码：0**

### 9.4 常见问题

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'backend'` | `src/` 不在 Python 路径中 | 检查 `tests/conftest.py` 是否将 `src/` 添加到 `sys.path` |
| `ImportError: cannot import name 'XXX'` | 缺少依赖 | 运行 `uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | pytest-asyncio 版本过旧 | 升级：`uv pip install --upgrade pytest-asyncio` |
| `Fixture 'XXX' not found` | 固定夹具未在 conftest.py 中定义 | 检查 `tests/test_fixtures.py` 是否包含该固定夹具 |

---

## 10. Docker 验证

> **注意**：本节需要安装并运行 Docker Desktop。如果无法使用 Docker，请跳过本节并在清单中标注。

### 10.1 启动 Docker Desktop

确保 Docker Desktop 正在运行。使用以下命令验证：

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

从仓库根目录执行：

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

```bash
docker network ls | grep memory-hub
```

**预期**：存在名为 `personal-memory-hub_default` 或类似的网络。

### 10.6 验证容器日志

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
| `port is already allocated` | 端口 5432 被占用 | 在 `.env` 中更改 `DB_PORT` 或停止冲突的服务 |
| `pgvector/pgvector:pg15 not found` | 镜像未拉取 | 运行 `docker pull pgvector/pgvector:pg15` |
| `permission denied` | Docker 套接字权限不足 | 使用 sudo 运行（Linux）或检查 Docker Desktop 设置 |

---

## 11. 数据库验证

### 11.1 验证 DATABASE_URL

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

```bash
uv run alembic check
```

**预期行为**：

- 如果 PostgreSQL 正在运行且可访问：Alembic 连接并报告当前迁移状态
- 如果 PostgreSQL **未**运行：Alembic 报告连接错误（这在 D1 中是 **正常的** — 基础设施被视为完整时并不要求数据库正在运行）

**示例预期输出（有数据库）**：

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**示例预期输出（无数据库）**：

```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionDoesNotExistError) ...
```

这在 D1 中是 **预期且可接受的**。Alembic 环境已正确配置；它只是无法连接，因为本地没有运行 PostgreSQL 实例。

### 11.4 解释无迁移文件时的预期行为

在 D1 完成时：

- `backend/alembic/versions/` 中 **不存在任何迁移文件**
- **Alembic history** 将显示空的修订图谱
- **Alembic current** 将报告 "No migrations present"
- 这是 **正确的** — D1 仅搭建迁移框架。实际的迁移文件将在 D2 定义领域模型时创建

验证方式：

```bash
uv run alembic history
```

**预期输出**（如果数据库可访问）：

```
Head (revision): <none>
```

或者如果没有数据库：

```
(sqlalchemy 错误 — 预期结果，数据库未运行)
```

---

## 12. 文档验证

### 12.1 验证 README

检查 `README.md` 是否存在并包含预期的章节：

```bash
cat README.md
```

**预期章节**：

- 项目名称和描述
- 快速开始（前置条件、本地开发、Docker）
- 项目结构
- 架构概览
- 实施里程碑表格
- 开发章节（编码规范、审查流程）
- 许可证

### 12.2 验证文档链接

README 中应引用：

- `docs/INDEX.md` — 架构文档索引
- `docs/05_Implementation/` — 实施计划

通过检查引用的文件是否存在来验证链接是否有效：

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

```bash
find docs -type f -name "*.md" | sort
```

**预期**：列出所有架构和实施文档，包括：

- `docs/INDEX.md`
- `docs/05_Implementation/README.md`
- `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md`
- 所有 Phase A、B、C 文档（来自之前的阶段）

---

## 13. 最终验收清单

使用此清单确认 D1 已完成。将每项标记为已完成（✓）或记录任何问题。

### 13.1 仓库

- [ ] 仓库克隆成功
- [ ] 目录结构与预期一致
- [ ] 所有预期文件均存在（参见第 3.3 节）
- [ ] `docs/INDEX.md` 已更新，包含 Phase D 章节
- [ ] `docs/05_Implementation/README.md` 存在
- [ ] `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` 存在

### 13.2 Python 环境

- [ ] `uv sync --all-extras` 顺利完成，无错误
- [ ] 虚拟环境 `.venv/` 存在
- [ ] 所有核心包可导入（第 4.3 节）
- [ ] `uv build` 生成 `.tar.gz` 和 `.whl` 文件

### 13.3 配置

- [ ] `.env.example` 存在且已文档化
- [ ] Settings 模块加载无错误
- [ ] 所有环境变量具有正确的默认值
- [ ] `is_supabase` 属性在 Supabase 配置为空时返回 `False`

### 13.4 代码质量

- [ ] `ruff check src/ tests/` 报告零违规
- [ ] `mypy src/` 报告 "Success: no issues found"
- [ ] 所有源文件在严格模式下通过类型检查

### 13.5 测试

- [ ] `pytest tests/ -v` 收集到 4 个测试
- [ ] 全部 4 个测试通过
- [ ] 测试固定夹具（settings、container、engine）工作正常
- [ ] 测试输出中无警告或错误

### 13.6 Docker（可选 — Docker 不可用时跳过）

- [ ] `docker compose up -d db` 成功启动 PostgreSQL
- [ ] 容器状态为 `Up (healthy)`
- [ ] pgvector 扩展已安装
- [ ] `docker compose down` 干净关闭

### 13.7 数据库基础设施

- [ ] SQLAlchemy 引擎初始化成功
- [ ] 会话工厂已配置
- [ ] 声明式基类 `Base` 可导入
- [ ] Alembic `env.py` 导入正确
- [ ] Alembic 迁移目录存在（按预期为空）

### 13.8 文档

- [ ] `README.md` 存在且包含所有预期章节
- [ ] `backend/README.md` 存在
- [ ] `docs/05_Implementation/README.md` 存在
- [ ] 所有文档链接指向存在的文件
- [ ] 无断裂引用

### 13.9 架构合规性

- [ ] `service/`、`engine/`、`repository/` 目录中无业务逻辑
- [ ] 所有空目录包含 `__init__.py` 文件
- [ ] 测试目录包含 README 占位文件
- [ ] 层级边界得到遵守（除通过 protocols 外，无跨层导入）

---

## 14. 故障排查

### 14.1 uv sync 失败

**症状**：

```
× No solution found when resolving dependencies
```

**原因**：

- 包版本约束不兼容
- 网络问题导致无法下载包
- uv 缓存损坏

**解决方法**：

```bash
# 清除缓存
uv cache clean

# 重新同步
uv sync --all-extras

# 如果仍然失败，检查 Python 版本
python --version  # 必须 >= 3.10

# 检查 pyproject.toml 是否有明显语法错误
head -50 backend/pyproject.toml
```

### 14.2 ruff 报错

**症状**：

```
F401 `typing.Any` imported but unused
```

**原因**：

- 死代码导入
- 导入未排序
- 行长度违规

**解决方法**：

```bash
# 自动修复所有可解决的问题
uv run ruff check --fix src/ tests/

# 对于剩余问题，手动编辑源代码文件
```

### 14.3 mypy 报错

**症状**：

```
error: Unused "type: ignore" comment
error: Function is missing a return type annotation
```

**原因**：

- 过时的 type: ignore 注释
- 缺少类型注解
- 类型不匹配

**解决方法**：

```bash
# 使用详细输出运行 mypy 获取详情
uv run mypy src/ --show-error-codes

# 根据需要修正类型注解
# 移除过时的 type: ignore 注释
```

### 14.4 pytest 未能收集测试

**症状**：

```
collected 0 items
```

**原因**：

- 测试文件不在 `tests/` 目录中
- 测试文件未命名为 `test_*.py`
- Python 路径配置不正确

**解决方法**：

```bash
# 验证测试文件是否存在
ls tests/test_*.py

# 验证 conftest.py 是否在 tests/ 中
ls tests/conftest.py

# 使用详细收集模式运行
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

```bash
# 启动 Docker Desktop（Windows/macOS）
# 或启动 Docker 服务（Linux）
sudo systemctl start docker

# 检查 Docker 是否正在运行
docker info

# 检查端口冲突
netstat -an | grep 5432  # Linux/macOS
netstat -an | findstr 5432  # Windows

# 如果端口被占用，在 docker-compose.yml 或 .env 中更改端口
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

```bash
# 检查 .env 文件
cat .env

# 验证变量格式
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
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionRefusedError) connection refused
```

**原因**：

- PostgreSQL 未运行
- DATABASE_URL 不正确
- 防火墙阻止连接

**解决方法**：

```bash
# 在 D1 中，如果 PostgreSQL 未运行，这是预期行为
# 基础设施已正确配置；它只是无法连接

# 在不运行数据库的情况下验证配置是否正确：
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

### 14.8 测试中导入错误

**症状**：

```
ModuleNotFoundError: No module named 'backend'
```

**原因**：

- `src/` 不在 Python 路径中
- 工作目录不正确

**解决方法**：

```bash
# 确保你在 backend 目录中
cd backend

# 验证 conftest.py 将 src/ 添加到路径
head -15 tests/conftest.py

# 从 backend 目录运行
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

```bash
# 检查 pyproject.toml 中的 license 字段
grep license backend/pyproject.toml

# 应为有效的 SPDX 标识符（例如 "MIT"、"Apache-2.0"）
# 或 LICENSE 文件的路径

# 验证 backend/ 中存在 README.md
ls backend/README.md
```

---

## 附录 A：文件清单

### A.1 源文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `src/backend/__init__.py` | ~10 | 包标记文件 |
| `src/backend/shared/__init__.py` | ~3 | 共享模块标记 |
| `src/backend/shared/domain/__init__.py` | ~5 | 领域模块标记（D1 为空） |
| `src/backend/shared/infrastructure/__init__.py` | ~3 | 基础设施模块标记 |
| `src/backend/shared/infrastructure/config/__init__.py` | ~8 | 配置导出 |
| `src/backend/shared/infrastructure/config/settings.py` | ~100 | Settings 模型 |
| `src/backend/shared/infrastructure/database/__init__.py` | ~8 | 数据库导出 |
| `src/backend/shared/infrastructure/database/engine.py` | ~110 | 引擎、会话、Base |
| `src/backend/shared/infrastructure/di/__init__.py` | ~8 | DI 导出 |
| `src/backend/shared/infrastructure/di/container.py` | ~100 | DI 容器 |
| `src/backend/shared/infrastructure/logging/__init__.py` | ~55 | 日志工厂 |
| `src/backend/shared/protocols/__init__.py` | ~5 | 协议标记 |
| `src/backend/entry/__init__.py` | ~4 | 入口层标记（空） |
| `src/backend/service/__init__.py` | ~4 | 服务层标记（空） |
| `src/backend/engine/__init__.py` | ~4 | 引擎层标记（空） |
| `src/backend/repository/__init__.py` | ~4 | 仓储层标记（空） |

### A.2 测试文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `tests/conftest.py` | ~15 | pytest 路径配置 |
| `tests/test_fixtures.py` | ~95 | 固定夹具测试（4 个测试） |
| `tests/test_smoke.py` | ~10 | 冒烟测试 |

### A.3 配置文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `backend/pyproject.toml` | ~140 | 项目配置、依赖、工具设置 |
| `backend/.env.example` | ~50 | 环境变量模板 |
| `backend/alembic.ini` | ~150 | Alembic 配置 |
| `backend/alembic/env.py` | ~100 | Alembic 环境 |
| `backend/Dockerfile` | ~50 | 多阶段 Docker 构建 |
| `docker-compose.yml` | ~80 | 本地开发服务 |
| `.github/workflows/ci.yml` | ~100 | CI 流水线 |
| `.gitignore` | ~60 | Git 忽略规则 |

### A.4 文档文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `README.md` | ~140 | 项目概览 |
| `backend/README.md` | ~10 | 后端包概览 |
| `docs/05_Implementation/README.md` | ~80 | 实施阶段概览 |
| `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` | ~400 | D1 计划文档 |
| `docs/INDEX.md` | ~200 | 文档索引（已针对 D1 更新） |
| `docs/06_Guides/D1_Verification_Guide.md` | 本文档 | 验证指南 |

---

## 附录 B：命令快速参考

附录中的所有命令均可直接复制粘贴使用。除非另有说明，否则从仓库根目录执行。

```bash
# 进入 backend 目录
cd backend

# 安装依赖
uv sync --all-extras

# 运行代码检查
uv run ruff check src/ tests/

# 运行类型检查
uv run mypy src/

# 运行测试
uv run pytest tests/ -v

# 构建包
uv build

# 验证配置
uv run python -c "from backend.shared.infrastructure.config.settings import get_settings; print(get_settings().APP_NAME)"

# 验证日志
uv run python -c "from backend.shared.infrastructure.logging import configure_logging, get_logger; configure_logging(); get_logger('test').info('hello')"

# 验证数据库基础设施
uv run python -c "from backend.shared.infrastructure.database.engine import Base, get_engine; print(get_engine())"

# 验证 DI 容器
uv run python -c "from backend.shared.infrastructure.di import get_container; from backend.shared.infrastructure.config.settings import AppSettings; c=get_container(); print(c.resolve(AppSettings).APP_NAME)"

# 运行 Alembic 检查（需要运行的 PostgreSQL）
uv run alembic check

# Docker：启动数据库
docker compose up -d db

# Docker：检查状态
docker compose ps

# Docker：停止
docker compose down
```

---

> **本指南是一份持续更新的文档。** 随着 D1 实施的演进，请适时更新本文档。
>
> **下一里程碑**：D2 — 仓储层（计划中）
>
> **文档版本**：1.0 | **最后更新**：2026-07-04
