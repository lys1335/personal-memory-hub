# D2 验证指南

> **阶段**: Phase D — 文档驱动实现  
> **里程碑**: D2 — 仓库层  
> **版本**: 1.0  
> **日期**: 2026-07-07  
> **状态**: 最终版  
> **作者**: 系统架构组

---

## 目录

1. [目的](#1-目的)  
2. [前置条件](#2-前置条件)  
3. [仓库准备](#3-仓库准备)  
4. [Python 环境验证](#4-python-环境验证)  
5. [依赖安装](#5-依赖安装)  
6. [Ruff 验证](#6-ruff-验证)  
7. [mypy 验证](#7-mypy-验证)  
8. [pytest 验证](#8-pytest-验证)  
9. [仓库清单验证](#9-仓库清单验证)  
10. [仓库合同验证](#10-仓库合同验证)  
11. [架构边界验证](#11-架构边界验证)  
12. [发布阻塞项验证](#12-发布阻塞项验证)  
13. [架构债务验证](#13-架构债务验证)  
14. [仓库冻结确认](#14-仓库冻结确认)  
15. [最终验收检查清单](#15-最终验收检查清单)  
16. [故障排查](#16-故障排查)

---

## 1. 目的

### 1.1 本指南验证什么

本指南验证 **D2 — 仓库层** 是否已正确实施。D2 为 Personal Memory Hub 项目建立了数据持久化层：

- **9 个 CRUD 仓库**: EntityRepository, MemoryNodeRepository, EvidenceRepository, RelationshipRepository, VectorDocRepository, ArchiveRepository, TagRepository, TaskRepository, CandidateRepository
- **3 个查询仓库**: MemoryQueryRepository, EntityQueryRepository, VectorQueryRepository
- **共享基础设施**: BaseRepository, QueryRepository, 分页, 工作区隔离, 类型工具
- **类型安全**: 所有 12 个仓库的 mypy 严格模式合规
- **测试覆盖**: 98 个测试涵盖 CRUD 操作、查询仓库、基础设施和导入边界

### 1.2 本指南不验证什么

以下项目明确 **不在** D2 验证范围内：

- **服务层** — 尚未实现服务（D3）
- **引擎层** — 尚未实现引擎/业务逻辑（D4）
- **API 端点** — 尚未实现 REST、MCP 或 CLI 适配器（D5）
- **生产部署** — CD 流水线有意推迟
- **性能基准测试** — D2 不进行负载测试
- **数据库迁移** — DDL 已定义但迁移推迟到 D3

### 1.3 验证理念

本指南面向对项目的 **不了解** 的开发者。每个命令都可直接复制粘贴。每个预期输出都已记录。如果某步骤失败，故障排查部分提供诊断和解决方法。

---

## 2. 前置条件

开始验证之前，请确保已安装以下工具。

### 2.1 操作系统

**支持的平台**:

- Windows 10/11（64 位）
- macOS 12+（Monterey 或更高版本）
- Ubuntu 20.04+ / Debian 11+ / Fedora 38+

**Windows 是本指南的默认平台。** 每个命令部分首先展示 Windows PowerShell 命令，然后是 Linux/macOS bash 等效命令。

### 2.2 Python

- **要求**: Python 3.11 或 3.12
- **最低版本**: Python 3.10（项目声明 `requires-python = ">=3.10"`）

**下载**: https://www.python.org/downloads/

**验证安装**:

**Windows (PowerShell)**:

```powershell
python --version
```

**Linux/macOS (bash)**:

```bash
python --version
```

**预期输出**:

```
Python 3.11.x
```

如果 Python 未安装或版本低于 3.10，请先安装再继续。

### 2.3 uv

- **要求**: uv 0.4.0 或更高版本
- **用途**: 快速 Python 包安装器和项目管理器

**下载**: https://docs.astral.sh/uv/getting-started/installation/

**Windows 安装** (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS 安装** (终端):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**验证安装**:

**Windows (PowerShell)**:

```powershell
uv --version
```

**Linux/macOS (bash)**:

```bash
uv --version
```

**预期输出**:

```
uv 0.x.x (xxx...)
```

### 2.4 Git

- **要求**: Git 2.40+
- **用途**: 仓库克隆

**下载**: https://git-scm.com/downloads

**验证安装**:

**Windows (PowerShell)**:

```powershell
git --version
```

**Linux/macOS (bash)**:

```bash
git --version
```

**预期输出**:

```
git version 2.x.x
```

---

## 3. 仓库准备

### 3.1 克隆仓库

**Windows (PowerShell)**:

```powershell
git clone https://github.com/lys1335/personal-memory-hub.git
cd personal-memory-hub
```

**Linux/macOS (bash)**:

```bash
git clone https://github.com/lys1335/personal-memory-hub.git
cd personal-memory-hub
```

**预期输出**:

```
Cloning into 'personal-memory-hub'...
remote: Enumerating objects: XXXX, done.
remote: Counting objects: 100% (XXX/XXX), done.
remote: Compressing objects: 100% (XXX/XXX), done.
remote: Total XXXX (delta XX), reused XXXX (delta XX), pack-reused XX
Receiving objects: 100% (XXXX/XXXX), X.XX MiB | X.XX MiB/s, done.
Resolving deltas: 100% (XX/XX), done.
```

### 3.2 验证分支

**Windows (PowerShell)**:

```powershell
git branch --show-current
```

**Linux/macOS (bash)**:

```bash
git branch --show-current
```

**预期输出**:

```
main
```

如果输出不是 `main`，切换到它：

**Windows (PowerShell)**:

```powershell
git checkout main
```

**Linux/macOS (bash)**:

```bash
git checkout main
```

### 3.3 验证仓库同步

**Windows (PowerShell)**:

```powershell
git status --short
echo "---"
git log --oneline -1
echo "---"
git rev-parse HEAD
git rev-parse '@{u}' 2>&1
```

**Linux/macOS (bash)**:

```bash
git status --short
echo "---"
git log --oneline -1
echo "---"
git rev-parse HEAD
git rev-parse '@{u}' 2>&1
```

**预期输出**:

```
(空 — 无未提交的更改)
019f6eb docs(d2-closing): Add Architecture Debt inventory for Repository Layer
019f6eb5527d21294047243387caeff43ab0cab7
019f6eb5527d21294047243387caeff43ab0cab7
```

- **工作树必须干净**（无 `git status --short` 输出）
- **本地 HEAD 必须等于远程 HEAD**（相同的提交哈希）

如果工作树不干净或 HEAD 不一致，运行：

**Windows (PowerShell)**:

```powershell
git stash
git pull --rebase
git status --short
```

**Linux/macOS (bash)**:

```bash
git stash
git pull --rebase
git status --short
```

**预期结果**: 仓库完全同步。

**如果失败**: 解决任何本地更改，然后重新运行同步检查。

---

## 4. Python 环境验证

> **工作目录**: 本节所有 `uv` 命令必须从 `backend/` 目录执行。

### 4.1 进入 Backend 目录

**Windows (PowerShell)**:

```powershell
cd backend
```

**Linux/macOS (bash)**:

```bash
cd backend
```

### 4.2 验证虚拟环境是否存在

**Windows (PowerShell)**:

```powershell
Test-Path .venv\Scripts\python.exe
```

**Linux/macOS (bash)**:

```bash
test -f .venv/bin/python && echo "exists" || echo "missing"
```

**预期输出**: `True`（Windows）或 `exists`（Linux/macOS）。

如果虚拟环境不存在，请转到第 5 节安装依赖。

---

## 5. 依赖安装

### 5.1 安装依赖

**Windows (PowerShell)**:

```powershell
uv sync --all-extras
```

**Linux/macOS (bash)**:

```bash
uv sync --all-extras
```

**预期输出**:

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
- `uuid_extensions`（用于 UUIDv7）
- `coverage`

### 5.2 验证核心包

**Windows (PowerShell)**:

```powershell
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

**Linux/macOS (bash)**:

```bash
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

**预期输出**:

```
All core packages imported successfully
SQLAlchemy: 2.0.x
Pydantic: 2.x.x
Alembic: 1.x.x
structlog: 24.x.x
aiosqlite: 0.2x.x
pytest: 8.x.x
```

**预期结果**: 所有依赖已安装且可导入。

**如果失败**: 运行 `uv cache clean && uv sync --all-extras` 重新安装。

---

## 6. Ruff 验证

### 6.1 运行代码检查

**Windows (PowerShell)**:

```powershell
uv run ruff check src/ tests/
```

**Linux/macOS (bash)**:

```bash
uv run ruff check src/ tests/
```

**预期输出**:

```
All checks passed!
```

退出码应为 `0`。

### 6.2 成功结果的特征

- 零违规报告
- 退出码 `0`
- 无警告

### 6.3 常见失败

| 症状 | 原因 | 解决方法 |
|------|------|---------|
| `F401 module imported but unused` | 未使用的导入 | 删除导入或使用它 |
| `E501 line too long` | 行超过 120 个字符 | 拆分该行 |
| `I001 import block is un-sorted` | 导入未排序 | 运行 `uv run ruff check --fix src/ tests/` |

---

## 7. mypy 验证

### 7.1 运行类型检查

**Windows (PowerShell)**:

```powershell
uv run mypy src/
```

**Linux/macOS (bash)**:

```bash
uv run mypy src/
```

**预期输出**:

```
Success: no issues found in 36 source files
```

退出码应为 `0`。

### 7.2 成功结果的特征

- `Success: no issues found in 36 source files`
- 退出码 `0`
- 无错误消息

### 7.3 mypy 严格模式配置

项目使用 mypy 严格模式，强制执行：

- `disallow_untyped_defs = true` — 所有函数必须有类型注解
- `disallow_incomplete_defs = true` — 所有类型注解必须完整
- `check_untyped_defs = true` — 类型检查器也检查未注解的函数
- `no_implicit_optional = true` — 可选类型需要显式 `| None`

### 7.4 常见失败

| 症状 | 原因 | 解决方法 |
|------|------|---------|
| `error: Missing type parameters for generic type` | 缺少泛型参数 | 为 SQLAlchemy 动态模式添加 `# type: ignore[type-arg]` |
| `error: Function is missing a return type annotation` | 缺少返回类型 | 在函数签名中添加 `-> ReturnType` |
| `error: Argument 1 has incompatible type` | 类型不匹配 | 修复类型注解或值 |

---

## 8. pytest 验证

### 8.1 运行测试

**Windows (PowerShell)**:

```powershell
uv run pytest tests/ -v
```

**Linux/macOS (bash)**:

```bash
uv run pytest tests/ -v
```

**预期输出**:

```
============================= test session starts ==============================
platform win32 -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- ...
cachedir: .pytest_cache
rootdir: .../backend
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.x.x, asyncio-1.4.0, cov-5.x.x
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 98 items

tests/test_entity_domain_repositories.py::TestEntityRepository::test_create_entity PASSED [  1%]
tests/test_entity_domain_repositories.py::TestEntityRepository::test_find_by_id_existing PASSED [  2%]
...
tests/test_smoke.py::test_pytest_works PASSED                            [100%]

============================== 98 passed in X.XXs ==============================
```

所有 98 个测试应通过。退出码应为 `0`。

### 8.2 测试套件分解

| 测试文件 | 类 | 测试数 | 目的 |
|---------|-----|--------|------|
| `test_entity_domain_repositories.py` | `TestEntityRepository` | 16 | Entity CRUD、Area、UserProfile、分页 |
| `test_entity_domain_repositories.py` | `TestRelationshipRepository` | 10 | Relationship CRUD、内存关系、分页 |
| `test_entity_domain_repositories.py` | `TestEntityQueryRepository` | 13 | 实体图查询、别名/类型过滤、分页 |
| `test_fixtures.py` | — | 3 | DI 容器、设置、测试引擎 |
| `test_memory_domain_repositories.py` | `TestEvidenceRepository` | 6 | Evidence CRUD、禁止更新/软删除 |
| `test_memory_domain_repositories.py` | `TestMemoryNodeRepository` | 9 | 内存 CRUD、证据链、分页 |
| `test_memory_domain_repositories.py` | `TestArchiveRepository` | 4 | 归档 CRUD、期间过滤、分页 |
| `test_memory_domain_repositories.py` | `TestTagRepository` | 4 | 标签 CRUD、工作区/名称过滤、分页 |
| `test_memory_domain_repositories.py` | `TestImportBoundaries` | 2 | 验证仓库中无服务/引擎导入 |
| `test_repository_infrastructure.py` | — | 29 | BaseRepository、QueryRepository、工作区隔离、分页、错误处理 |
| `test_smoke.py` | — | 1 | 基本冒烟测试 |

### 8.3 预期通过结果

- **收集 98 个测试**
- **98 个测试通过**
- **0 个测试失败**
- **0 个测试错误**
- **退出码: 0**

### 8.4 常见失败

| 症状 | 原因 | 解决方法 |
|------|------|---------|
| `ModuleNotFoundError: No module named 'backend'` | `src/` 不在 Python 路径中 | 检查 `tests/conftest.py` 将 `src/` 添加到 `sys.path` |
| `ImportError: cannot import name 'XXX'` | 缺少依赖 | 运行 `uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | 旧版 pytest-asyncio | 升级: `uv pip install --upgrade pytest-asyncio` |
| `Fixture 'XXX' not found` | conftest.py 中未定义夹具 | 检查 `tests/test_fixtures.py` 是否有该夹具 |

---

## 9. 仓库清单验证

### 9.1 验证仓库文件存在

**Windows (PowerShell)**:

```powershell
$repos = @(
    "src\backend\repository\base.py",
    "src\backend\repository\query.py",
    "src\backend\repository\pagination.py",
    "src\backend\repository\types.py",
    "src\backend\repository\workspace.py",
    "src\backend\repository\entity_repository.py",
    "src\backend\repository\entity_query_repository.py",
    "src\backend\repository\memory_node_repository.py",
    "src\backend\repository\memory_query_repository.py",
    "src\backend\repository\evidence_repository.py",
    "src\backend\repository\relationship_repository.py",
    "src\backend\repository\vector_doc_repository.py",
    "src\backend\repository\vector_query_repository.py",
    "src\backend\repository\archive_repository.py",
    "src\backend\repository\tag_repository.py",
    "src\backend\repository\task_repository.py",
    "src\backend\repository\candidate_repository.py"
)
foreach ($repo in $repos) {
    if (Test-Path $repo) { Write-Output "OK: $repo" } else { Write-Output "MISSING: $repo" }
}
```

**Linux/macOS (bash)**:

```bash
for f in \
  src/backend/repository/base.py \
  src/backend/repository/query.py \
  src/backend/repository/pagination.py \
  src/backend/repository/types.py \
  src/backend/repository/workspace.py \
  src/backend/repository/entity_repository.py \
  src/backend/repository/entity_query_repository.py \
  src/backend/repository/memory_node_repository.py \
  src/backend/repository/memory_query_repository.py \
  src/backend/repository/evidence_repository.py \
  src/backend/repository/relationship_repository.py \
  src/backend/repository/vector_doc_repository.py \
  src/backend/repository/vector_query_repository.py \
  src/backend/repository/archive_repository.py \
  src/backend/repository/tag_repository.py \
  src/backend/repository/task_repository.py \
  src/backend/repository/candidate_repository.py; do
  if [ -f "$f" ]; then echo "OK: $f"; else echo "MISSING: $f"; fi
done
```

**预期输出**: 所有 17 个文件应显示 `OK:`。

### 9.2 验证 12 个仓库实现

D2 仓库层由 **12 个仓库** 组成，分为两个类别：

#### 9.2.1 CRUD 仓库（9 个）

| # | 仓库 | 聚合 | 域 | 文件 |
|---|------|------|----|------|
| 1 | EntityRepository | Entity | Entity | `entity_repository.py` |
| 2 | MemoryNodeRepository | MemoryNode | Memory | `memory_node_repository.py` |
| 3 | EvidenceRepository | Evidence | Ingestion | `evidence_repository.py` |
| 4 | RelationshipRepository | Relationship | Entity | `relationship_repository.py` |
| 5 | VectorDocRepository | VectorDoc | Retrieval | `vector_doc_repository.py` |
| 6 | ArchiveRepository | Archive | Memory | `archive_repository.py` |
| 7 | TagRepository | Tag | Memory | `tag_repository.py` |
| 8 | TaskRepository | Task | Runtime | `task_repository.py` |
| 9 | CandidateRepository | Candidate | Reflection | `candidate_repository.py` |

#### 9.2.2 查询仓库（3 个）

| # | 仓库 | 聚合 | 域 | 文件 |
|---|------|------|----|------|
| 10 | MemoryQueryRepository | MemoryNode | Memory | `memory_query_repository.py` |
| 11 | EntityQueryRepository | Entity | Entity | `entity_query_repository.py` |
| 12 | VectorQueryRepository | Vector | Retrieval | `vector_query_repository.py` |

### 9.3 验证共享基础设施文件

| 文件 | 用途 |
|------|------|
| `base.py` | `BaseRepository[T]` — 通用 CRUD 基类，含异步操作 |
| `query.py` | `QueryRepository[T]` — 复杂查询的只读基类 |
| `pagination.py` | `OffsetPage`, `CursorPage` — 分页模型 |
| `types.py` | `get_table_columns()`, `get_primary_key_column()` — 类型工具 |
| `workspace.py` | `WorkspaceFilterMixin` — 多租户工作区隔离 |
| `exceptions.py` | `NotFoundError`, `DuplicateError`, `ReadOnlyError` — 仓库异常 |

**预期结果**: 12 个仓库存在。所有共享基础设施文件存在。

**如果失败**: 检查仓库是否从正确的分支（`main`）和提交（`019f6eb`）克隆。

---

## 10. 仓库合同验证

> **工作目录**: 项目根目录（从仓库根目录执行，非 `backend/`）。

### 10.1 验证仓库能力合规性

每个仓库的能力由其领域模型决定，而非统一的 CRUD 模板。下表基于架构文档（`10_9_Repository_Inventory.md`、`D2_Repository_Layer_Plan.md`）定义了各仓库的预期能力：

| # | 仓库 | 能力模型 | 必需方法 | 禁止方法 |
|---|-----|---------|---------|---------|
| 1 | EntityRepository | 身份（可变属性） | `create` + 查询方法 | 身份不可软删除 |
| 2 | MemoryNodeRepository | **不可变 / 追加只写** | `create` + 链接证据 | `update()`、`soft_delete()` 必须抛出异常 |
| 3 | EvidenceRepository | **不可变** | 仅 `create` | `update()`、`soft_delete()` 必须抛出异常 |
| 4 | RelationshipRepository | 不可变关系 | `create` + 查询方法 | 无 update/soft_delete |
| 5 | VectorDocRepository | 替换式（删除+重建） | `create` + 查询方法 | 无 update |
| 6 | ArchiveRepository | 不可变归档 | `create` + 查询方法 | 无 update/soft_delete |
| 7 | TagRepository | 可变标签定义 | `create` + 查询方法 | — |
| 8 | TaskRepository | 状态机 | `create` + 状态转换 | 无通用 `update()` |
| 9 | CandidateRepository | 状态机 | `create` + 状态转换 | 无通用 `update()` |
| 10 | MemoryQueryRepository | 只读查询 | 查询方法 | 任何写方法 |
| 11 | EntityQueryRepository | 只读查询 | 查询方法 | 任何写方法 |
| 12 | VectorQueryRepository | 只读查询 | 查询方法 | 任何写方法 |

**验证原则**：每个仓库按其自身能力模型验证，而非一刀切的 CRUD 模板。

#### 不可变仓库（MemoryNode、Evidence）

这些仓库继承自 `BaseRepository`，但覆写了 `update()` 和 `soft_delete()` 以抛出 `DomainIntegrityError`。这是有意为之——方法作为接口契约存在，但在运行时被禁止。

**Windows (PowerShell)**:

```powershell
# 不可变仓库：验证 update() 和 soft_delete() 抛出异常
$immutable_repos = @(
    @{ Name="memory_node_repository.py"; Label="MemoryNode" },
    @{ Name="evidence_repository.py"; Label="Evidence" }
)
foreach ($r in $immutable_repos) {
    $content = Get-Content "src\backend\repository\$($r.Name)" -Raw
    $has_update_override = $content -match "async def update\(.*\) -> .*:\s+.*raise DomainIntegrityError" -or ($content -match "async def update\(" -and $content -match "immutable")
    $has_soft_delete_override = $content -match "async def soft_delete\(.*\) -> .*:\s+.*raise DomainIntegrityError" -or ($content -match "async def soft_delete\(" -and $content -match "immutable")
    if ($has_update_override -and $has_soft_delete_override) {
        Write-Output "不可变 OK: $($r.Label) (update 已阻止, soft_delete 已阻止)"
    } else {
        Write-Output "违规: $($r.Label) (update=$has_update_override, soft_delete=$has_soft_delete_override)"
    }
}

# 其他 CRUD 仓库：验证 create 存在
$crud_repos = @(
    "entity_repository.py",
    "relationship_repository.py",
    "vector_doc_repository.py",
    "archive_repository.py",
    "tag_repository.py",
    "task_repository.py",
    "candidate_repository.py"
)
foreach ($repo in $crud_repos) {
    $content = Get-Content "src\backend\repository\$repo" -Raw
    $has_create = $content -match "async def create\("
    $status = if ($has_create) { "CREATE OK" } else { "缺少 CREATE" }
    Write-Output "${status}: $repo"
}
```

**Linux/macOS (bash)**:

```bash
# 不可变仓库：验证 update() 和 soft_delete() 抛出异常
for f in memory_node_repository evidence_repository; do
  if grep -q "async def update(" "src/backend/repository/${f}_repository.py" 2>/dev/null && \
     grep -q "immutable" "src/backend/repository/${f}_repository.py" 2>/dev/null && \
     grep -q "async def soft_delete(" "src/backend/repository/${f}_repository.py" 2>/dev/null; then
    echo "不可变 OK: ${f}_repository.py (update 已阻止, soft_delete 已阻止)"
  else
    echo "违规: ${f}_repository.py"
  fi
done

# 其他 CRUD 仓库：验证 create 存在
for f in entity_repository relationship_repository vector_doc_repository archive_repository tag_repository task_repository candidate_repository; do
  if grep -q "async def create(" "src/backend/repository/${f}_repository.py" 2>/dev/null; then
    echo "CREATE OK: ${f}_repository.py"
  else
    echo "缺少 CREATE: ${f}_repository.py"
  fi
done
```

**预期输出**:
```
不可变 OK: MemoryNode (update 已阻止, soft_delete 已阻止)
不可变 OK: Evidence (update 已阻止, soft_delete 已阻止)
CREATE OK: entity_repository.py
CREATE OK: relationship_repository.py
CREATE OK: vector_doc_repository.py
CREATE OK: archive_repository.py
CREATE OK: tag_repository.py
CREATE OK: task_repository.py
CREATE OK: candidate_repository.py
```

**预期结果**: 每个仓库实现其领域模型所需的精确操作。不可变仓库在运行时强制执行不可变性。所有仓库都实现 `create`。

**如果失败**: 检查仓库文件是否被错误修改。不可变仓库应始终对写操作尝试抛出 `DomainIntegrityError`。

### 10.2 验证查询仓库是只读的

查询仓库不应实现写操作。它们应只有只读方法：`find`、`find_page`、`count`、`get_entity_graph` 等。

**Windows (PowerShell)**:

```powershell
$query_repos = @(
    "memory_query_repository.py",
    "entity_query_repository.py",
    "vector_query_repository.py"
)
foreach ($repo in $query_repos) {
    $content = Get-Content "src\backend\repository\$repo" -Raw
    $has_write = $content -match "async def (create|update|soft_delete|delete)\("
    $status = if ($has_write) { "VIOLATION" } else { "READ-ONLY OK" }
    Write-Output "$status: $repo"
}
```

**Linux/macOS (bash)**:

```bash
for f in memory_query_repository entity_query_repository vector_query_repository; do
  if grep -q "async def \(create\|update\|soft_delete\|delete)(" "src/backend/repository/${f}_repository.py" 2>/dev/null; then
    echo "VIOLATION: ${f}_repository.py"
  else
    echo "READ-ONLY OK: ${f}_repository.py"
  fi
done
```

**预期输出**: 所有 3 个查询仓库应显示 `READ-ONLY OK`。

**预期结果**: 仓库职责符合架构。CRUD 仓库有写操作；查询仓库是只读的。

**如果失败**: 检查仓库文件是否被错误地修改。

---

## 11. 架构边界验证

### 11.1 验证仓库从不调用仓库

仓库必须独立运行。任何仓库不得导入或调用另一个仓库。

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path src\backend\repository\*_repository.py | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $other_repos = @("entity_repository", "memory_node_repository", "evidence_repository", "relationship_repository", "vector_doc_repository", "archive_repository", "tag_repository", "task_repository", "candidate_repository", "memory_query_repository", "entity_query_repository", "vector_query_repository")
    foreach ($repo in $other_repos) {
        if ($_.Name -ne "${repo}.py" -and $content -match "from backend\.repository\.${repo}") {
            Write-Output "VIOLATION: $($_.Name) imports $repo"
        }
    }
}
Write-Output "跨仓库导入检查完成"
```

**Linux/macOS (bash)**:

```bash
for f in src/backend/repository/*_repository.py; do
  basename=$(basename "$f")
  for target in entity_repository memory_node_repository evidence_repository relationship_repository vector_doc_repository archive_repository tag_repository task_repository candidate_repository memory_query_repository entity_query_repository vector_query_repository; do
    if [ "$basename" != "${target}.py" ] && grep -q "from backend\.repository\.${target}" "$f" 2>/dev/null; then
      echo "违规: $basename 导入 $target"
    fi
  done
done
echo "跨仓库导入检查完成"
```

**预期输出**: 无违规报告。

### 11.2 验证无服务依赖

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path src\backend\repository\*.py | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match "from backend\.service|import.*service") {
        Write-Output "违规: $($_.Name) 导入 service"
    }
}
Write-Output "服务依赖检查完成"
```

**Linux/macOS (bash)**:

```bash
for f in src/backend/repository/*.py; do
  if grep -q "from backend\.service\|import.*service" "$f" 2>/dev/null; then
    echo "违规: $(basename $f) 导入 service"
  fi
done
echo "服务依赖检查完成"
```

**预期输出**: 无违规报告。

### 11.3 验证无引擎依赖

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path src\backend\repository\*.py | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match "from backend\.engine|import.*engine") {
        Write-Output "违规: $($_.Name) 导入 engine"
    }
}
Write-Output "引擎依赖检查完成"
```

**Linux/macOS (bash)**:

```bash
for f in src/backend/repository/*.py; do
  if grep -q "from backend\.engine\|import.*engine" "$f" 2>/dev/null; then
    echo "违规: $(basename $f) 导入 engine"
  fi
done
echo "引擎依赖检查完成"
```

**预期输出**: 无违规报告。

### 11.4 验证无运行时引擎/会话依赖

仓库层不得直接依赖于数据库引擎。它通过依赖注入接收会话。

**Windows (PowerShell)**:

```powershell
if (Select-String -Path src\backend\repository\*.py -Pattern "get_engine|AsyncEngine" -Quiet) {
    Write-Output "违规: 发现引擎依赖"
} else {
    Write-Output "未发现引擎依赖（正确）"
}
```

**Linux/macOS (bash)**:

```bash
if grep -rq "get_engine\|AsyncEngine" src/backend/repository/ 2>/dev/null; then
  echo "违规: 发现引擎依赖"
else
  echo "未发现引擎依赖（正确）"
fi
```

**预期结果**: 仓库层边界得到维护。

**如果失败**: 任何从 `backend.service`、`backend.engine` 导入或调用 `get_engine()` 的仓库都违反架构。删除违规的导入。

---

## 12. 发布阻塞项验证

### 12.1 验证文档包含发布阻塞项

Native pgvector 支持的发布阻塞项必须在仓库清单中记录。

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Release Blocker" -Quiet) {
    Write-Output "发布阻塞项部分找到"
} else {
    Write-Output "发布阻塞项部分缺失"
}
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Native pgvector Support" -Quiet) {
    Write-Output "pgvector 描述找到"
} else {
    Write-Output "pgvector 描述缺失"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "Release Blocker" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "发布阻塞项部分找到"
else
  echo "发布阻塞项部分缺失"
fi
if grep -q "Native pgvector Support" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "pgvector 描述找到"
else
  echo "pgvector 描述缺失"
fi
```

### 12.2 验证 pgvector 文档完整性

发布阻塞项文档应包含以下内容：

| 项目 | 要求 | 位置 |
|------|------|------|
| 当前 String embedding 存储 | ✅ | `10_9_Repository_Inventory.md` §9 |
| pgvector 依赖 | ✅ | `10_9_Repository_Inventory.md` §9 |
| ORM 迁移到 `Vector(1536)` | ✅ | `10_9_Repository_Inventory.md` §9 |
| PostgreSQL vector 扩展 | ✅ | `10_9_Repository_Inventory.md` §9 |
| HNSW / IVFFlat 索引 | ✅ | `10_9_Repository_Inventory.md` §9 |
| 原生向量运算符 | ✅ | `10_9_Repository_Inventory.md` §9 |

**Windows (PowerShell)**:

```powershell
$file = "docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md"
$checks = @("embedding", "pgvector", "Vector\(1536\)", "extension", "HNSW", "IVFFlat", "cosine")
foreach ($check in $checks) {
    if (Select-String -Path $file -Pattern $check -Quiet) {
        Write-Output "找到: $check"
    } else {
        Write-Output "缺失: $check"
    }
}
```

**Linux/macOS (bash)**:

```bash
file="docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md"
for check in "embedding" "pgvector" "Vector\(1536\)" "extension" "HNSW" "IVFFlat" "cosine"; do
  if grep -qi "$check" "$file"; then
    echo "找到: $check"
  else
    echo "缺失: $check"
  fi
done
```

**预期结果**: 发布阻塞项已记录所有必需项。

**如果失败**: 将缺失的文档添加到 `10_9_Repository_Inventory.md` 第 9 节。

---

## 13. 架构债务验证

### 13.1 验证架构债务已记录

仓库合同与 BaseRepository 签名对齐的架构债务必须被记录。

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Architecture Debt" -Quiet) {
    Write-Output "架构债务部分找到"
} else {
    Write-Output "架构债务部分缺失"
}
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Repository Contract vs BaseRepository Signature Alignment" -Quiet) {
    Write-Output "债务标题找到"
} else {
    Write-Output "债务标题缺失"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "Architecture Debt" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "架构债务部分找到"
else
  echo "架构债务部分缺失"
fi
if grep -q "Repository Contract vs BaseRepository Signature Alignment" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "债务标题找到"
else
  echo "债务标题缺失"
fi
```

### 13.2 验证债务元数据

架构债务应包含以下内容：

| 字段 | 预期值 |
|------|--------|
| 状态 | Deferred（延期） |
| 优先级 | Low（低） |
| 建议里程碑 | Post-MVP Architecture Review（MVP 后架构评审） |
| 类型 | Design Debt（设计债务，非 bug） |

**Windows (PowerShell)**:

```powershell
$file = "docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md"
foreach ($term in "Deferred", "Low", "Post-MVP", "Design Debt") {
    if (Select-String -Path $file -Pattern $term -Quiet) {
        Write-Output "找到: $term"
    } else {
        Write-Output "缺失: $term"
    }
}
```

**Linux/macOS (bash)**:

```bash
file="docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md"
for term in "Deferred" "Low" "Post-MVP" "Design Debt"; do
  if grep -q "$term" "$file"; then
    echo "找到: $term"
  else
    echo "缺失: $term"
  fi
done
```

**预期结果**: 架构债务已记录正确的元数据。

**如果失败**: 将架构债务部分添加到 `10_9_Repository_Inventory.md`。

---

## 14. 仓库冻结确认

### 14.1 验证仓库层已冻结

D2.8 类型安全稳定化之后，仓库层正式冻结。变更仅限于：

**允许的**:

- Bug 修复（mypy 错误、运行时错误）
- 安全修复
- 框架兼容性更新（SQLAlchemy 版本升级）
- ADR 驱动的演进（架构决策记录）

**不允许的**:

- 仓库重新设计
- 聚合边界变更
- 仓库合同变更（方法签名、返回类型）
- 未经 ADR 批准的新增仓库

### 14.2 验证冻结已记录

仓库层冻结记录在 `D2_Repository_Layer_Plan.md`（第15节 — 关闭确认）中。这是权威记录，而非仓库清单。

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\05_Implementation\D2_Repository_Layer_Plan.md -Pattern "Closing Confirmation" -Quiet) {
    Write-Output "冻结已在 D2 Plan §15 中记录"
} else {
    Write-Output "冻结未记录"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "Closing Confirmation" docs/05_Implementation/D2_Repository_Layer_Plan.md; then
  echo "冻结已在 D2 Plan §15 中记录"
else
  echo "冻结未记录"
fi
```

### 14.3 验证 D2.8 完成

D2.8 类型安全稳定化是最终的 D2 活动。验证它已被记录。

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "D2\.8" -Quiet) {
    Write-Output "D2.8 类型安全稳定化已记录"
} else {
    Write-Output "D2.8 未记录"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "D2\.8" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "D2.8 类型安全稳定化已记录"
else
  echo "D2.8 未记录"
fi
```

**预期结果**: 仓库层正式冻结。未经 ADR 批准不得进行进一步变更。

---

## 15. 最终验收检查清单

使用此检查清单确认 D2 完成。将每项标记为完成（✓）或记录任何问题。

### 15.1 仓库同步

- [ ] 仓库克隆成功
- [ ] 分支为 `main`
- [ ] 工作树干净（无未提交的更改）
- [ ] 本地 HEAD 等于远程 HEAD（`019f6eb`）
- [ ] 无暂存或未暂存的文件

### 15.2 依赖安装

- [ ] `uv sync --all-extras` 无错误完成
- [ ] 虚拟环境 `.venv/` 存在
- [ ] 所有核心包可导入（第 4.2 节）

### 15.3 代码质量

- [ ] `ruff check src/ tests/` 报告零违规
- [ ] `mypy src/` 报告 "Success: no issues found in 36 source files"
- [ ] 所有源文件通过严格模式的类型检查

### 15.4 测试

- [ ] `pytest tests/ -v` 收集 98 个测试
- [ ] 所有 98 个测试通过
- [ ] 测试夹具（settings、container、engine）正常工作
- [ ] 测试输出无警告或错误

### 15.5 仓库清单

- [ ] 12 个仓库存在（9 个 CRUD + 3 个查询）
- [ ] 所有共享基础设施文件存在（base.py、query.py、pagination.py、types.py、workspace.py、exceptions.py）
- [ ] 仓库清单文档（`10_9_Repository_Inventory.md`）已更新

### 15.6 仓库合同

- [ ] 不可变仓库（MemoryNode、Evidence）强制执行不可变性 — `update()` 和 `soft_delete()` 抛出 `DomainIntegrityError`
- [ ] 所有其他 CRUD 仓库实现 `create`
- [ ] 所有 3 个查询仓库是只读的（无 create/update/soft_delete）
- [ ] 仓库能力符合其领域模型（见 §10.1 能力矩阵）
- [ ] 仓库职责符合架构

### 15.7 架构边界

- [ ] 无仓库导入其他仓库
- [ ] 无仓库从 `backend.service` 导入
- [ ] 无仓库从 `backend.engine` 导入
- [ ] 无仓库调用 `get_engine()` 或依赖 `AsyncEngine`

### 15.8 发布阻塞项

- [ ] 发布阻塞项部分存在于 `10_9_Repository_Inventory.md` §9
- [ ] Native pgvector 支持已记录
- [ ] String embedding 存储已注明
- [ ] pgvector 依赖已列出
- [ ] ORM 迁移到 `Vector(1536)` 已记录
- [ ] PostgreSQL vector 扩展已记录
- [ ] HNSW / IVFFlat 索引已记录
- [ ] 原生向量运算符已记录

### 15.9 架构债务

- [ ] 架构债务部分存在于 `10_9_Repository_Inventory.md` §10
- [ ] 仓库合同与 BaseRepository 签名对齐已记录
- [ ] 状态: Deferred（延期）
- [ ] 优先级: Low（低）
- [ ] 里程碑: Post-MVP Architecture Review（MVP 后架构评审）

### 15.10 仓库冻结

- [ ] 仓库层冻结记录在 `D2_Repository_Layer_Plan.md` §15
- [ ] D2.8 类型安全稳定化已记录为最终 D2 活动
- [ ] 允许的变更已列出（bug 修复、安全、框架、ADR）
- [ ] 禁止的变更已列出（重新设计、聚合边界、合同）
- [ ] 未来合同变更需通过 ADR

### 15.11 验收标准

**当以下全部条件满足时，Phase D2 视为已验证**：

1. ✅ 仓库已同步（工作树干净，HEAD 匹配远程）
2. ✅ 所有依赖无错误安装
3. ✅ `ruff check src/ tests/` 零违规通过
4. ✅ `mypy src/` 零错误通过
5. ✅ `pytest tests/ -v` 报告 98 通过，0 失败
6. ✅ 12 个仓库存在且已验证
7. ✅ 不可变仓库强制执行不可变性；其他 CRUD 仓库有 create
8. ✅ 查询仓库是只读的
9. ✅ 无跨层依赖（service、engine、runtime）
10. ✅ 发布阻塞项已记录
11. ✅ 架构债务已记录
12. ✅ 仓库冻结已在 D2 Plan §15 中确认

**如果上述任何一项失败，Phase D2 未经验证。**

---

## 16. 故障排查

### 16.1 uv sync 失败

**症状**:

```
× No solution found when resolving dependencies
```

**原因**:

- 包版本约束不兼容
- 网络问题导致包下载失败
- uv 缓存损坏

**解决方法**:

**Windows (PowerShell)**:

```powershell
uv cache clean
uv sync --all-extras
python --version  # 必须 >= 3.10
Get-Content backend\pyproject.toml -TotalCount 50
```

**Linux/macOS (bash)**:

```bash
uv cache clean
uv sync --all-extras
python --version  # 必须 >= 3.10
head -50 backend/pyproject.toml
```

### 16.2 ruff 报告错误

**症状**:

```
F401 `typing.Any` imported but unused
```

**原因**:

- 死导入
- 未排序的导入
- 行长度违规

**解决方法**:

**Windows (PowerShell)**:

```powershell
uv run ruff check --fix src/ tests/
```

**Linux/macOS (bash)**:

```bash
uv run ruff check --fix src/ tests/
```

对于剩余问题，手动编辑源文件。

### 16.3 mypy 报告错误

**症状**:

```
error: Unused "type: ignore" comment
error: Function is missing a return type annotation
```

**原因**:

- 过时的 type: ignore 注释
- 缺少类型注解
- 类型不匹配

**解决方法**:

**Windows (PowerShell)**:

```powershell
uv run mypy src/ --show-error-codes
```

**Linux/macOS (bash)**:

```bash
uv run mypy src/ --show-error-codes
```

根据需要修复类型注解。删除过时的 `type: ignore` 注释。

### 16.4 pytest 无法收集测试

**症状**:

```
collected 0 items
```

**原因**:

- 测试文件不在 `tests/` 目录中
- 测试文件未命名为 `test_*.py`
- Python 路径配置不正确

**解决方法**:

**Windows (PowerShell)**:

```powershell
Get-ChildItem tests\test_*.py
Get-ChildItem tests\conftest.py
uv run pytest tests/ --collect-only -v
```

**Linux/macOS (bash)**:

```bash
ls tests/test_*.py
ls tests/conftest.py
uv run pytest tests/ --collect-only -v
```

### 16.5 测试中的导入错误

**症状**:

```
ModuleNotFoundError: No module named 'backend'
```

**原因**:

- `src/` 不在 Python 路径中
- 工作目录不正确

**解决方法**:

**Windows (PowerShell)**:

```powershell
cd backend
Get-Content tests\conftest.py -TotalCount 15
uv run pytest tests/ -v
```

**Linux/macOS (bash)**:

```bash
cd backend
head -15 tests/conftest.py
uv run pytest tests/ -v
```

### 16.6 Git 同步问题

**症状**:

```
Your branch is behind 'origin/main' by X commits.
```

**解决方法**:

**Windows (PowerShell)**:

```powershell
git fetch origin
git reset --hard origin/main
git status --short
```

**Linux/macOS (bash)**:

```bash
git fetch origin
git reset --hard origin/main
git status --short
```

### 16.7 检测到仓库冻结违规

**症状**:

某个仓库文件被以改变合同的方式修改（方法签名、返回类型、聚合边界）。

**解决方法**:

1. 查看差异: `git diff backend/src/backend/repository/`
2. 如果是 bug 修复，则允许
3. 如果修改了合同，请还原并首先创建 ADR
4. 如果是新仓库，需要 ADR 批准

---

## 附录 A: 文件清单

### A.1 仓库源文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `src/backend/repository/__init__.py` | ~50 | 包导出 |
| `src/backend/repository/base.py` | ~340 | `BaseRepository[T]` — 通用 CRUD 基类 |
| `src/backend/repository/query.py` | ~230 | `QueryRepository[T]` — 只读基类 |
| `src/backend/repository/pagination.py` | ~100 | `OffsetPage`, `CursorPage` 模型 |
| `src/backend/repository/types.py` | ~80 | 列类型工具 |
| `src/backend/repository/workspace.py` | ~70 | 工作区过滤混合类 |
| `src/backend/repository/exceptions.py` | ~60 | 仓库异常 |
| `src/backend/repository/entity_repository.py` | ~350 | Entity CRUD |
| `src/backend/repository/memory_node_repository.py` | ~570 | MemoryNode CRUD |
| `src/backend/repository/evidence_repository.py` | ~370 | Evidence CRUD |
| `src/backend/repository/relationship_repository.py` | ~670 | Relationship CRUD |
| `src/backend/repository/vector_doc_repository.py` | ~430 | VectorDoc CRUD |
| `src/backend/repository/archive_repository.py` | ~400 | Archive CRUD |
| `src/backend/repository/tag_repository.py` | ~370 | Tag CRUD |
| `src/backend/repository/task_repository.py` | ~400 | Task CRUD |
| `src/backend/repository/candidate_repository.py` | ~350 | Candidate CRUD |
| `src/backend/repository/memory_query_repository.py` | ~380 | 内存复杂查询 |
| `src/backend/repository/entity_query_repository.py` | ~640 | 实体图查询 |
| `src/backend/repository/vector_query_repository.py` | ~470 | 向量相似性查询 |

### A.2 测试文件

| 文件 | 测试数 | 用途 |
|------|--------|------|
| `tests/test_entity_domain_repositories.py` | 39 | Entity、Relationship、EntityQueryRepository |
| `tests/test_fixtures.py` | 3 | DI 容器、设置、引擎 |
| `tests/test_memory_domain_repositories.py` | 25 | Evidence、MemoryNode、Archive、Tag、导入边界 |
| `tests/test_repository_infrastructure.py` | 29 | BaseRepository、QueryRepository、工作区隔离 |
| `tests/test_smoke.py` | 1 | 基本冒烟测试 |

### A.3 文档文件

| 文件 | 用途 |
|------|------|
| `docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md` | 仓库实现清单，含发布阻塞项和架构债务 |
| `docs/06_Guides/D2_Repository_Verification_Guide.md` | 本文档 |
| `docs/06_Guides/zh-CN/D2_Repository_Verification_Guide.md` | 中文本地化 |

---

## 附录 B: 命令快速参考

本附录中的所有命令均可直接复制粘贴。在以下每个命令注明目录下执行。

```powershell
# === 从仓库根目录 (personal-memory-hub/) ===
git clone https://github.com/lys1335/personal-memory-hub.git
cd personal-memory-hub

# === 从 backend/ 目录 ===
cd backend

# 安装依赖
uv sync --all-extras

# 运行代码检查
uv run ruff check src/ tests/

# 运行类型检查
uv run mypy src/

# 运行测试
uv run pytest tests/ -v

# 验证仓库同步
cd ..
git status --short
git log --oneline -1
git rev-parse HEAD
```

---

> **本指南是活文档。** 随着 D2 实现的演进更新它。
>
> **前一个里程碑**: D1 — 基础设施基础（已验证）
>
> **下一个里程碑**: D3 — 服务层（计划中）
