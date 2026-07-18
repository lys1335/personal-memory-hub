# D3/D4/D5/E5 验证指南

> **阶段**: Phase D — 文档驱动实现
> **里程标记**: D3 服务层 + D4 领域引擎层 + D5 入口层 + E5 集成测试
> **版本**: 1.0
> **日期**: 2026-07-17
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
7. [pytest 验证](#7-pytest-验证)
8. [D3 服务层验证](#8-d3-服务层验证)
9. [D4 引擎层验证](#9-d4-引擎层验证)
10. [D5 入口层验证](#10-d5-入口层验证)
11. [E5 集成测试验证](#11-e5-集成测试验证)
12. [架构边界验证](#12-架构边界验证)
13. [冻结层契约验证](#13-冻结层契约验证)
14. [最终验收检查清单](#14-最终验收检查清单)
15. [故障排查](#15-故障排查)

---

> 本文档为简体中文版本。
> 如与英文版存在任何差异，以英文版为准。

## 1. 目的

### 1.1 本指南验证什么？

本指南验证 **D3 服务层 + D4 领域引擎层 + D5 入口层 + E5 集成测试** 是否已正确实施。

这些阶段建立了 Personal Memory Hub 的完整业务逻辑层：

- **D3 服务层（5 个服务）**: MemoryService、QueryService、EntityService、ReflectionService、TaskService — 共 27 个测试
- **D4 领域引擎层（6 个引擎）**: EntityEngine、MemoryEngine、RelationshipEngine、ReflectionEngine、SearchEngine、ProjectionEngine — 共 58 个测试
- **D5 入口层（REST 适配器）**: RESTAdapter、ContractValidator、9 个外部 DTO — 共 28 个测试
- **E5 集成测试**: 端到端生命周期、层边界、DTO 翻译、错误传播、依赖 DAG、冻结契约 — 共 10 个测试
- **D2 仓储层（已有代码）**: 98 个测试（作为基线，不应被破坏）

**总计**: 221 个测试，全部通过。

### 1.2 本指南不验证什么？

以下内容明确 **不在** D3/D4/D5/E5 验证范围内：

- **生产部署**: CD 流水线有意推迟
- **性能基准测试**: 本阶段不进行负载测试
- **外部集成**: Supabase、Redis、LLM Provider 等外部服务
- **MCP/CLI 适配器**: MVP 仅实现 REST 适配器（其他适配器为 V2+）
- **高级 Entity 功能**: merge/alias/relationship 的完整实现在 V2+

### 1.3 验证理念

本指南面向 **对项目没有任何先验知识** 的开发者。每条命令均可直接复制粘贴使用。每条预期输出均已记录。如果某一步骤失败，故障排查部分提供了诊断和解决方法。

---

## 2. 前置条件

开始验证之前，请确保以下工具已安装。

### 2.1 操作系统

**支持的平台**:

- Windows 10/11（64 位）
- macOS 12+（Monterey 或更高版本）
- Ubuntu 20.04+ / Debian 11+ / Fedora 38+

**Windows 是本指南的默认平台**。每个命令部分首先展示 Windows PowerShell 命令，然后是 Linux/macOS bash 等效命令。

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
(无未提交的更改)
cddb83e docs(E5): add code self-review report — A-C phase constraint verification
cddb83exxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
cddb83exxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- **工作树必须干净**（无 `git status --short` 输出）
- **本地 HEAD 必须等于远程 HEAD**（相同的提交哈希）

如果工作树不干净 / HEAD 不一致，运行：

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

> **工作目录**: 本节所有 `uv` 命令必须在 `backend/` 目录执行。

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

你应该看到以下关键包：

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

## 7. pytest 验证

### 7.1 运行全部测试

**Windows (PowerShell)**:

```powershell
uv run pytest tests/ -v --tb=no
```

**Linux/macOS (bash)**:

```bash
uv run pytest tests/ -v --tb=no
```

**预期输出**:

```
============================= test session starts ==============================
platform win32 -- Python 3.11.15, pytest-8.4.2, pluggy-1.6.0 -- ...
cachedir: .pytest_cache
rootdir: .../backend
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.x.x, asyncio-1.4.0, cov-5.x.x
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 221 items

tests/test_engine_layer.py .........................................     [ 18%]
.............                                                            [ 24%]
tests/test_entity_domain_repositories.py ...............................  [ 37%]
.......                                                                  [ 40%]
tests/test_entry_layer.py ............................                   [ 52%]
tests/test_fixtures.py ...                                               [ 54%]
tests/test_integration.py ..........                                     [ 58%]
tests/test_memory_domain_repositories.py .........................       [ 70%]
tests/test_repository_infrastructure.py ...............................  [ 83%]
tests/test_service_layer.py ...........................                  [ 95%]
tests/test_smoke.py .                                                    [100%]

======================= 221 passed in X.XXs ========================
```

**所有 221 个测试应通过**。退出码应为 `0`。

### 7.2 测试套件分解

| 测试文件 | 测试数 | 覆盖范围 |
|---------|--------|---------|
| `test_engine_layer.py` | 58 | D4 引擎层：EngineBase + 6 引擎 + 边界测试 |
| `test_entity_domain_repositories.py` | 39 | D2 仓储：Entity + Relationship + EntityQuery |
| `test_entry_layer.py` | 28 | D5 入口层：Contract Validation + DTO + REST Adapter |
| `test_fixtures.py` | 3 | D1 基础设施：DI 容器、Settings、Test Engine |
| `test_integration.py` | 10 | E5 集成测试：生命周期、边界、DTO、错误传播、DAG、契约 |
| `test_memory_domain_repositories.py` | 25 | D2 仓储：Evidence + MemoryNode + Archive + Tag |
| `test_repository_infrastructure.py` | 31 | D2 仓储：BaseRepository + QueryRepository + 边界 |
| `test_service_layer.py` | 27 | D3 服务层：BaseService + 5 服务 + DTO |
| `test_smoke.py` | 1 | 冒烟测试 |

### 7.3 预期通过结果

- **收集 221 个测试**
- **221 个测试通过**
- **0 个测试失败**
- **0 个测试错误**
- **退出码: 0**

### 7.4 常见失败

| 症状 | 原因 | 解决方法 |
|------|------|---------|
| `ModuleNotFoundError: No module named 'backend'` | `src/` 不在 Python 路径 | 检查 `tests/conftest.py` 是否将 `src/` 添加到 `sys.path` |
| `ImportError: cannot import name 'XXX'` | 缺少依赖 | 运行 `uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | 旧版 pytest-asyncio | 升级: `uv pip install --upgrade pytest-asyncio` |
| `Fixture 'XXX' not found` | conftest.py 中未定义夹具 | 检查 `tests/test_fixtures.py` 是否有该夹具 |

---

## 8. D3 服务层验证

### 8.1 验证服务文件存在

**Windows (PowerShell)**:

```powershell
$services = @(
    "src\backend\service\__init__.py",
    "src\backend\service\base.py",
    "src\backend\service\dto.py",
    "src\backend\service\exceptions.py",
    "src\backend\service\memory_service.py",
    "src\backend\service\query_service.py",
    "src\backend\service\entity_service.py",
    "src\backend\service\reflection_service.py",
    "src\backend\service\task_service.py"
)
foreach ($svc in $services) {
    if (Test-Path $svc) { Write-Output "OK: $svc" } else { Write-Output "MISSING: $svc" }
}
```

**Linux/macOS (bash)**:

```bash
for f in \
  src/backend/service/__init__.py \
  src/backend/service/base.py \
  src/backend/service/dto.py \
  src/backend/service/exceptions.py \
  src/backend/service/memory_service.py \
  src/backend/service/query_service.py \
  src/backend/service/entity_service.py \
  src/backend/service/reflection_service.py \
  src/backend/service/task_service.py; do
  if [ -f "$f" ]; then echo "OK: $f"; else echo "MISSING: $f"; fi
done
```

**预期输出**: 所有 9 个文件显示 `OK`。

### 8.2 验证服务方法签名

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.service.memory_service import MemoryService
from backend.service.query_service import QueryService
from backend.service.entity_service import EntityService
from backend.service.reflection_service import ReflectionService
from backend.service.task_service import TaskService

services = {
    'MemoryService': MemoryService,
    'QueryService': QueryService,
    'EntityService': EntityService,
    'ReflectionService': ReflectionService,
    'TaskService': TaskService,
}
expected = {
    'MemoryService': ['capture_memory', 'import_memories', 'merge_memories', 'archive_memory', 'trigger_reflection', 'schedule_archive', 'reprocess_memory', 'restore_archived_memory'],
    'QueryService': ['retrieve_by_id', 'retrieve_by_entity', 'retrieve_by_relationship', 'search_by_keyword', 'search_by_similarity', 'search_combined', 'browse_by_time_range', 'browse_by_category', 'browse_by_tag', 'project_to_summary', 'project_to_detail', 'project_to_graph', 'project_to_timeline', 'analyze_statistics', 'analyze_insights'],
    'EntityService': ['create_entity', 'resolve_entity', 'get_entity_profile', 'merge_entities', 'add_alias', 'remove_alias', 'get_aliases', 'add_relationship', 'remove_relationship', 'get_relationships', 'update_canonical_name', 'update_metadata'],
    'ReflectionService': ['reflect', 'reflect_by_entity', 'reflect_by_time_window', 'reflect_by_scope', 'consolidate', 'consolidate_by_entity', 'summarize', 'summarize_by_level', 'evaluate', 'evaluate_by_entity'],
    'TaskService': ['submit', 'get_task', 'list_tasks', 'retry_task', 'cancel_task', 'get_health'],
}
ok = True
for name, cls in services.items():
    for method in expected[name]:
        if not hasattr(cls, method):
            print(f'MISSING: {name}.{method}')
            ok = False
if ok:
    print('All D3 service methods verified OK')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.service.memory_service import MemoryService
from backend.service.query_service import QueryService
from backend.service.entity_service import EntityService
from backend.service.reflection_service import ReflectionService
from backend.service.task_service import TaskService

services = {
    'MemoryService': MemoryService,
    'QueryService': QueryService,
    'EntityService': EntityService,
    'ReflectionService': ReflectionService,
    'TaskService': TaskService,
}
expected = {
    'MemoryService': ['capture_memory', 'import_memories', 'merge_memories', 'archive_memory', 'trigger_reflection', 'schedule_archive', 'reprocess_memory', 'restore_archived_memory'],
    'QueryService': ['retrieve_by_id', 'retrieve_by_entity', 'retrieve_by_relationship', 'search_by_keyword', 'search_by_similarity', 'search_combined', 'browse_by_time_range', 'browse_by_category', 'browse_by_tag', 'project_to_summary', 'project_to_detail', 'project_to_graph', 'project_to_timeline', 'analyze_statistics', 'analyze_insights'],
    'EntityService': ['create_entity', 'resolve_entity', 'get_entity_profile', 'merge_entities', 'add_alias', 'remove_alias', 'get_aliases', 'add_relationship', 'remove_relationship', 'get_relationships', 'update_canonical_name', 'update_metadata'],
    'ReflectionService': ['reflect', 'reflect_by_entity', 'reflect_by_time_window', 'reflect_by_scope', 'consolidate', 'consolidate_by_entity', 'summarize', 'summarize_by_level', 'evaluate', 'evaluate_by_entity'],
    'TaskService': ['submit', 'get_task', 'list_tasks', 'retry_task', 'cancel_task', 'get_health'],
}
ok = True
for name, cls in services.items():
    for method in expected[name]:
        if not hasattr(cls, method):
            print(f'MISSING: {name}.{method}')
            ok = False
if ok:
    print('All D3 service methods verified OK')
"
```

**预期输出**:

```
All D3 service methods verified OK
```

### 8.3 验证服务独立性

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
modules = {
    'MemoryService': 'backend.service.memory_service',
    'QueryService': 'backend.service.query_service',
    'EntityService': 'backend.service.entity_service',
    'ReflectionService': 'backend.service.reflection_service',
    'TaskService': 'backend.service.task_service',
}
ok = True
for name, path in modules.items():
    mod = __import__(path, fromlist=[''])
    source = open(mod.__file__, encoding='utf-8').read()
    for other in modules:
        if other != name and f'from backend.service.{other.lower()}_service' in source:
            print(f'VIOLATION: {name} imports {other}')
            ok = False
if ok:
    print('Service independence: OK (no cross-service calls)')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
modules = {
    'MemoryService': 'backend.service.memory_service',
    'QueryService': 'backend.service.query_service',
    'EntityService': 'backend.service.entity_service',
    'ReflectionService': 'backend.service.reflection_service',
    'TaskService': 'backend.service.task_service',
}
ok = True
for name, path in modules.items():
    mod = __import__(path, fromlist=[''])
    source = open(mod.__file__, encoding='utf-8').read()
    for other in modules:
        if other != name and f'from backend.service.{other.lower()}_service' in source:
            print(f'VIOLATION: {name} imports {other}')
            ok = False
if ok:
    print('Service independence: OK (no cross-service calls)')
"
```

**预期输出**:

```
Service independence: OK (no cross-service calls)
```

---

## 9. D4 引擎层验证

### 9.1 验证引擎文件存在

**Windows (PowerShell)**:

```powershell
$engines = @(
    "src\backend\engine\__init__.py",
    "src\backend\engine\base.py",
    "src\backend\engine\entity_engine.py",
    "src\backend\engine\memory_engine.py",
    "src\backend\engine\relationship_engine.py",
    "src\backend\engine\reflection_engine.py",
    "src\backend\engine\search_engine.py",
    "src\backend\engine\projection_engine.py"
)
foreach ($eng in $engines) {
    if (Test-Path $eng) { Write-Output "OK: $eng" } else { Write-Output "MISSING: $eng" }
}
```

**Linux/macOS (bash)**:

```bash
for f in \
  src/backend/engine/__init__.py \
  src/backend/engine/base.py \
  src/backend/engine/entity_engine.py \
  src/backend/engine/memory_engine.py \
  src/backend/engine/relationship_engine.py \
  src/backend/engine/reflection_engine.py \
  src/backend/engine/search_engine.py \
  src/backend/engine/projection_engine.py; do
  if [ -f "$f" ]; then echo "OK: $f"; else echo "MISSING: $f"; fi
done
```

**预期输出**: 所有 8 个文件显示 `OK`。

### 9.2 验证引擎方法签名

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.engine.entity_engine import EntityEngine
from backend.engine.memory_engine import MemoryEngine
from backend.engine.relationship_engine import RelationshipEngine
from backend.engine.reflection_engine import ReflectionEngine
from backend.engine.search_engine import SearchEngine
from backend.engine.projection_engine import ProjectionEngine

engines = {
    'EntityEngine': EntityEngine,
    'MemoryEngine': MemoryEngine,
    'RelationshipEngine': RelationshipEngine,
    'ReflectionEngine': ReflectionEngine,
    'SearchEngine': SearchEngine,
    'ProjectionEngine': ProjectionEngine,
}
expected = {
    'EntityEngine': ['evaluate_entity_state', 'validate_entity', 'evaluate_evolution_decision', 'verify_domain_invariants', 'derive_domain_information', 'resolve_identity'],
    'MemoryEngine': ['evaluate_memory_semantics', 'validate_memory_evidence_chain', 'evaluate_evolution_action', 'verify_invariants', 'derive_projection_data', 'assess_archive_eligibility'],
    'RelationshipEngine': ['validate_relationship', 'verify_invariants', 'evaluate_relationship_semantics', 'normalize_relationship', 'assess_lifecycle', 'check_endpoint_compatibility'],
    'ReflectionEngine': ['validate_reflection', 'evaluate_candidate', 'validate_evolution', 'verify_invariants', 'assess_consolidation_feasibility'],
    'SearchEngine': ['interpret_intent', 'plan_discovery', 'discover_candidates', 'validate_candidate', 'rank_candidates', 'verify_invariants'],
    'ProjectionEngine': ['produce_projection', 'enforce_semantics', 'normalize_structure', 'apply_policy', 'verify_determinism', 'verify_invariants'],
}
ok = True
for name, cls in engines.items():
    for method in expected[name]:
        if not hasattr(cls, method):
            print(f'MISSING: {name}.{method}')
            ok = False
if ok:
    print('All D4 engine methods verified OK')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.engine.entity_engine import EntityEngine
from backend.engine.memory_engine import MemoryEngine
from backend.engine.relationship_engine import RelationshipEngine
from backend.engine.reflection_engine import ReflectionEngine
from backend.engine.search_engine import SearchEngine
from backend.engine.projection_engine import ProjectionEngine

engines = {
    'EntityEngine': EntityEngine,
    'MemoryEngine': MemoryEngine,
    'RelationshipEngine': RelationshipEngine,
    'ReflectionEngine': ReflectionEngine,
    'SearchEngine': SearchEngine,
    'ProjectionEngine': ProjectionEngine,
}
expected = {
    'EntityEngine': ['evaluate_entity_state', 'validate_entity', 'evaluate_evolution_decision', 'verify_domain_invariants', 'derive_domain_information', 'resolve_identity'],
    'MemoryEngine': ['evaluate_memory_semantics', 'validate_memory_evidence_chain', 'evaluate_evolution_action', 'verify_invariants', 'derive_projection_data', 'assess_archive_eligibility'],
    'RelationshipEngine': ['validate_relationship', 'verify_invariants', 'evaluate_relationship_semantics', 'normalize_relationship', 'assess_lifecycle', 'check_endpoint_compatibility'],
    'ReflectionEngine': ['validate_reflection', 'evaluate_candidate', 'validate_evolution', 'verify_invariants', 'assess_consolidation_feasibility'],
    'SearchEngine': ['interpret_intent', 'plan_discovery', 'discover_candidates', 'validate_candidate', 'rank_candidates', 'verify_invariants'],
    'ProjectionEngine': ['produce_projection', 'enforce_semantics', 'normalize_structure', 'apply_policy', 'verify_determinism', 'verify_invariants'],
}
ok = True
for name, cls in engines.items():
    for method in expected[name]:
        if not hasattr(cls, method):
            print(f'MISSING: {name}.{method}')
            ok = False
if ok:
    print('All D4 engine methods verified OK')
"
```

**预期输出**:

```
All D4 engine methods verified OK
```

### 9.3 验证引擎独立性

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
modules = {
    'EntityEngine': 'backend.engine.entity_engine',
    'MemoryEngine': 'backend.engine.memory_engine',
    'RelationshipEngine': 'backend.engine.relationship_engine',
    'ReflectionEngine': 'backend.engine.reflection_engine',
    'SearchEngine': 'backend.engine.search_engine',
    'ProjectionEngine': 'backend.engine.projection_engine',
}
ok = True
for name, path in modules.items():
    mod = __import__(path, fromlist=[''])
    source = open(mod.__file__, encoding='utf-8').read()
    for other in modules:
        if other != name and f'from backend.engine.{other.lower()}' in source:
            print(f'VIOLATION: {name} imports {other}')
            ok = False
if ok:
    print('Engine independence: OK (no cross-engine calls)')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
modules = {
    'EntityEngine': 'backend.engine.entity_engine',
    'MemoryEngine': 'backend.engine.memory_engine',
    'RelationshipEngine': 'backend.engine.relationship_engine',
    'ReflectionEngine': 'backend.engine.reflection_engine',
    'SearchEngine': 'backend.engine.search_engine',
    'ProjectionEngine': 'backend.engine.projection_engine',
}
ok = True
for name, path in modules.items():
    mod = __import__(path, fromlist=[''])
    source = open(mod.__file__, encoding='utf-8').read()
    for other in modules:
        if other != name and f'from backend.engine.{other.lower()}' in source:
            print(f'VIOLATION: {name} imports {other}')
            ok = False
if ok:
    print('Engine independence: OK (no cross-engine calls)')
"
```

**预期输出**:

```
Engine independence: OK (no cross-engine calls)
```

---

## 10. D5 入口层验证

### 10.1 验证入口层文件存在

**Windows (PowerShell)**:

```powershell
$entry_files = @(
    "src\backend\entry\__init__.py",
    "src\backend\entry\dto.py",
    "src\backend\entry\validation.py",
    "src\backend\entry\rest_adapter.py"
)
foreach ($f in $entry_files) {
    if (Test-Path $f) { Write-Output "OK: $f" } else { Write-Output "MISSING: $f" }
}
```

**Linux/macOS (bash)**:

```bash
for f in \
  src/backend/entry/__init__.py \
  src/backend/entry/dto.py \
  src/backend/entry/validation.py \
  src/backend/entry/rest_adapter.py; do
  if [ -f "$f" ]; then echo "OK: $f"; else echo "MISSING: $f"; fi
done
```

**预期输出**: 所有 4 个文件显示 `OK`。

### 10.2 验证 REST 端点

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.entry.rest_adapter import RESTAdapter

methods = ['handle_capture_memory', 'handle_search_memory', 'handle_retrieve_memory',
           'handle_create_entity', 'handle_trigger_reflection', 'handle_submit_task']
ok = True
for m in methods:
    if not hasattr(RESTAdapter, m):
        print(f'MISSING: RESTAdapter.{m}')
        ok = False
if ok:
    print('All 6 REST endpoints verified OK')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.entry.rest_adapter import RESTAdapter

methods = ['handle_capture_memory', 'handle_search_memory', 'handle_retrieve_memory',
           'handle_create_entity', 'handle_trigger_reflection', 'handle_submit_task']
ok = True
for m in methods:
    if not hasattr(RESTAdapter, m):
        print(f'MISSING: RESTAdapter.{m}')
        ok = False
if ok:
    print('All 6 REST endpoints verified OK')
"
```

**预期输出**:

```
All 6 REST endpoints verified OK
```

### 10.3 验证 Entry → Service Only

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
modules = {
    'RESTAdapter': 'backend.entry.rest_adapter',
    'ContractValidator': 'backend.entry.validation',
}
ok = True
for name, path in modules.items():
    mod = __import__(path, fromlist=[''])
    source = open(mod.__file__, encoding='utf-8').read()
    if 'from backend.engine.' in source and 'from backend.engine.base' not in source:
        print(f'VIOLATION: {name} imports engine')
        ok = False
    if 'from backend.repository.' in source:
        print(f'VIOLATION: {name} imports repository')
        ok = False
if ok:
    print('Entry layer boundary: OK (only calls service)')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
modules = {
    'RESTAdapter': 'backend.entry.rest_adapter',
    'ContractValidator': 'backend.entry.validation',
}
ok = True
for name, path in modules.items():
    mod = __import__(path, fromlist=[''])
    source = open(mod.__file__, encoding='utf-8').read()
    if 'from backend.engine.' in source and 'from backend.engine.base' not in source:
        print(f'VIOLATION: {name} imports engine')
        ok = False
    if 'from backend.repository.' in source:
        print(f'VIOLATION: {name} imports repository')
        ok = False
if ok:
    print('Entry layer boundary: OK (only calls service)')
"
```

**预期输出**:

```
Entry layer boundary: OK (only calls service)
```

---

## 11. E5 集成测试验证

### 11.1 运行集成测试

**Windows (PowerShell)**:

```powershell
uv run pytest tests/test_integration.py -v --tb=short
```

**Linux/macOS (bash)**:

```bash
uv run pytest tests/test_integration.py -v --tb=short
```

**预期输出**:

```
============================= test session starts ==============================
...
collected 10 items

tests/test_integration.py::test_full_memory_lifecycle PASSED
tests/test_integration.py::test_entry_calls_service_only PASSED
tests/test_integration.py::test_service_calls_engine_and_repository PASSED
tests/test_integration.py::test_engine_calls_repository_only PASSED
tests/test_integration.py::test_dto_translation_round_trip PASSED
tests/test_integration.py::test_error_propagation_through_layers PASSED
tests/test_integration.py::test_dependency_dag PASSED
tests/test_integration.py::test_frozen_service_contract PASSED
tests/test_integration.py::test_frozen_engine_contract PASSED
tests/test_integration.py::test_frozen_repository_contract PASSED

============================== 10 passed in X.XXs ==============================
```

**所有 10 个集成测试应通过**。

### 11.2 集成测试覆盖范围

| 测试 | 验证内容 | 预期结果 |
|------|---------|---------|
| `test_full_memory_lifecycle` | 记忆生命周期：Service → Engine → Repository | ✅ 通过 |
| `test_entry_calls_service_only` | Entry 只调 Service，不调 Engine/Repository | ✅ 通过 |
| `test_service_calls_engine_and_repository` | Service 可调用 Engine + Repository | ✅ 通过 |
| `test_engine_calls_repository_only` | Engine 只调 Repository，不调 Service/其他 Engine | ✅ 通过 |
| `test_dto_translation_round_trip` | DTO 翻译：External → Internal → Response | ✅ 通过 |
| `test_error_propagation_through_layers` | 错误传播：Engine → Service → Entry | ✅ 通过 |
| `test_dependency_dag` | 依赖 DAG 正确性 | ✅ 通过 |
| `test_frozen_service_contract` | D3 服务契约稳定性 | ✅ 通过 |
| `test_frozen_engine_contract` | D4 引擎契约稳定性 | ✅ 通过 |
| `test_frozen_repository_contract` | D2 仓储契约稳定性 | ✅ 通过 |

---

## 12. 架构边界验证

### 12.1 验证层间依赖

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')

# Check Entry -> Service only
import backend.entry.rest_adapter as entry_mod
entry_src = open(entry_mod.__file__, encoding='utf-8').read()
assert 'from backend.service.' in entry_src, 'Entry should import Service'
assert 'from backend.repository.' not in entry_src, 'Entry should NOT import Repository'
assert 'from backend.engine.' not in entry_src or 'from backend.engine.base' not in entry_src, 'Entry should NOT import Engine'
print('Entry -> Service only: OK')

# Check Service -> Engine + Repository
import backend.service.memory_service as svc_mod
svc_src = open(svc_mod.__file__, encoding='utf-8').read()
assert 'from backend.repository.' in svc_src, 'Service should import Repository'
print('Service -> Engine + Repository: OK')

# Check Engine -> Repository only
import backend.engine.entity_engine as eng_mod
eng_src = open(eng_mod.__file__, encoding='utf-8').read()
assert 'from backend.service.' not in eng_src, 'Engine should NOT import Service'
assert 'from backend.repository.' not in eng_src or 'from backend.repository.exceptions' in eng_src, 'Engine should NOT import Repository directly'
print('Engine -> Repository only (via Domain Models): OK')

# Check Repository is bottom layer
import backend.repository.memory_node_repository as repo_mod
repo_src = open(repo_mod.__file__, encoding='utf-8').read()
assert 'from backend.service.' not in repo_src, 'Repository should NOT import Service'
assert 'from backend.engine.' not in repo_src, 'Repository should NOT import Engine'
assert 'from backend.entry.' not in repo_src, 'Repository should NOT import Entry'
print('Repository -> Database only: OK')

print()
print('Dependency DAG verified:')
print('  Entry (D5) -> Service (D3) -> Engine (D4) -> Repository (D2) -> Database')
print('  No backward or sideways edges detected.')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')

# Check Entry -> Service only
import backend.entry.rest_adapter as entry_mod
entry_src = open(entry_mod.__file__, encoding='utf-8').read()
assert 'from backend.service.' in entry_src, 'Entry should import Service'
assert 'from backend.repository.' not in entry_src, 'Entry should NOT import Repository'
assert 'from backend.engine.' not in entry_src or 'from backend.engine.base' not in entry_src, 'Entry should NOT import Engine'
print('Entry -> Service only: OK')

# Check Service -> Engine + Repository
import backend.service.memory_service as svc_mod
svc_src = open(svc_mod.__file__, encoding='utf-8').read()
assert 'from backend.repository.' in svc_src, 'Service should import Repository'
print('Service -> Engine + Repository: OK')

# Check Engine -> Repository only
import backend.engine.entity_engine as eng_mod
eng_src = open(eng_mod.__file__, encoding='utf-8').read()
assert 'from backend.service.' not in eng_src, 'Engine should NOT import Service'
assert 'from backend.repository.' not in eng_src or 'from backend.repository.exceptions' in eng_src, 'Engine should NOT import Repository directly'
print('Engine -> Repository only (via Domain Models): OK')

# Check Repository is bottom layer
import backend.repository.memory_node_repository as repo_mod
repo_src = open(repo_mod.__file__, encoding='utf-8').read()
assert 'from backend.service.' not in repo_src, 'Repository should NOT import Service'
assert 'from backend.engine.' not in repo_src, 'Repository should NOT import Engine'
assert 'from backend.entry.' not in repo_src, 'Repository should NOT import Entry'
print('Repository -> Database only: OK')

print()
print('Dependency DAG verified:')
print('  Entry (D5) -> Service (D3) -> Engine (D4) -> Repository (D2) -> Database')
print('  No backward or sideways edges detected.')
"
```

**预期输出**:

```
Entry -> Service only: OK
Service -> Engine + Repository: OK
Engine -> Repository only (via Domain Models): OK
Repository -> Database only: OK

Dependency DAG verified:
  Entry (D5) -> Service (D3) -> Engine (D4) -> Repository (D2) -> Database
  No backward or sideways edges detected.
```

---

## 13. 冻结层契约验证

### 13.1 验证 D3 冻结契约

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.service.memory_service import MemoryService
from backend.service.query_service import QueryService
from backend.service.entity_service import EntityService
from backend.service.reflection_service import ReflectionService
from backend.service.task_service import TaskService

# Verify all 5 services exist
services = [MemoryService, QueryService, EntityService, ReflectionService, TaskService]
print(f'D3 Services: {len(services)} verified OK')

# Verify BaseService has transaction helpers
from backend.service.base import BaseService
assert hasattr(BaseService, '_commit'), 'BaseService should have _commit'
assert hasattr(BaseService, '_rollback'), 'BaseService should have _rollback'
print('Transaction ownership (G-106): OK')

# Verify QueryService has no write methods
assert not hasattr(QueryService, 'capture_memory'), 'QueryService should not have write methods'
print('Command/Query separation (G-037): OK')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.service.memory_service import MemoryService
from backend.service.query_service import QueryService
from backend.service.entity_service import EntityService
from backend.service.reflection_service import ReflectionService
from backend.service.task_service import TaskService

# Verify all 5 services exist
services = [MemoryService, QueryService, EntityService, ReflectionService, TaskService]
print(f'D3 Services: {len(services)} verified OK')

# Verify BaseService has transaction helpers
from backend.service.base import BaseService
assert hasattr(BaseService, '_commit'), 'BaseService should have _commit'
assert hasattr(BaseService, '_rollback'), 'BaseService should have _rollback'
print('Transaction ownership (G-106): OK')

# Verify QueryService has no write methods
assert not hasattr(QueryService, 'capture_memory'), 'QueryService should not have write methods'
print('Command/Query separation (G-037): OK')
"
```

**预期输出**:

```
D3 Services: 5 verified OK
Transaction ownership (G-106): OK
Command/Query separation (G-037): OK
```

### 13.2 验证 D4 冻结契约

**Windows (PowerShell)**:

```powershell
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.engine.base import EngineBase, DomainResult
from backend.engine.entity_engine import EntityEngine
from backend.engine.memory_engine import MemoryEngine

# Verify all 6 engines exist
from backend.engine.relationship_engine import RelationshipEngine
from backend.engine.reflection_engine import ReflectionEngine
from backend.engine.search_engine import SearchEngine
from backend.engine.projection_engine import ProjectionEngine

engines = [EntityEngine, MemoryEngine, RelationshipEngine, ReflectionEngine, SearchEngine, ProjectionEngine]
print(f'D4 Engines: {len(engines)} verified OK')

# Verify engines return DomainResult
me = MemoryEngine()
result = me.evaluate_memory_semantics(memory={'level': 1, 'node_type': 'Observation', 'content': 'test', 'confidence': 0.8, 'importance': 0.5, 'signal_strength': 0.7, 'evidence_links': ['ev-1']})
assert isinstance(result, DomainResult), 'Engine should return DomainResult'
print('Domain Result (not Protocol Result): OK')

# Verify engines are stateless
ee = EntityEngine()
assert not hasattr(ee, '__dict__') or len(ee.__dict__) == 0, 'Engine should have no mutable state'
print('Stateless Engine: OK')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from backend.engine.base import EngineBase, DomainResult
from backend.engine.entity_engine import EntityEngine
from backend.engine.memory_engine import MemoryEngine

# Verify all 6 engines exist
from backend.engine.relationship_engine import RelationshipEngine
from backend.engine.reflection_engine import ReflectionEngine
from backend.engine.search_engine import SearchEngine
from backend.engine.projection_engine import ProjectionEngine

engines = [EntityEngine, MemoryEngine, RelationshipEngine, ReflectionEngine, SearchEngine, ProjectionEngine]
print(f'D4 Engines: {len(engines)} verified OK')

# Verify engines return DomainResult
me = MemoryEngine()
result = me.evaluate_memory_semantics(memory={'level': 1, 'node_type': 'Observation', 'content': 'test', 'confidence': 0.8, 'importance': 0.5, 'signal_strength': 0.7, 'evidence_links': ['ev-1']})
assert isinstance(result, DomainResult), 'Engine should return DomainResult'
print('Domain Result (not Protocol Result): OK')

# Verify engines are stateless
ee = EntityEngine()
assert not hasattr(ee, '__dict__') or len(ee.__dict__) == 0, 'Engine should have no mutable state'
print('Stateless Engine: OK')
"
```

**预期输出**:

```
D4 Engines: 6 verified OK
Domain Result (not Protocol Result): OK
Stateless Engine: OK
```

---

## 14. 最终验收检查清单

### 14.1 检查清单

请逐项完成以下检查，每项打勾确认：

| # | 检查项 | 状态 | 备注 |
|---|--------|------|------|
| 1 | Python 3.11+ 已安装 | ☐ | |
| 2 | uv 已安装 | ☐ | |
| 3 | Git 已安装 | ☐ | |
| 4 | 仓库已克隆，分支为 `main` | ☐ | |
| 5 | 工作树干净，HEAD 与远程一致 | ☐ | |
| 6 | `cd backend` 进入后端目录 | ☐ | |
| 7 | `.venv` 虚拟环境存在 | ☐ | |
| 8 | `uv sync --all-extras` 依赖安装成功 | ☐ | |
| 9 | 核心包导入成功（SQLAlchemy, Pydantic 等） | ☐ | |
| 10 | `uv run ruff check src/ tests/` 全部通过 | ☐ | |
| 11 | `uv run pytest tests/ -v --tb=no` — 221/221 通过 | ☐ | |
| 12 | D3 服务文件全部存在（9 个） | ☐ | |
| 13 | D3 服务方法签名全部正确（5 个服务） | ☐ | |
| 14 | D3 服务独立性验证通过（无互调） | ☐ | |
| 15 | D4 引擎文件全部存在（8 个） | ☐ | |
| 16 | D4 引擎方法签名全部正确（6 个引擎） | ☐ | |
| 17 | D4 引擎独立性验证通过（无互调） | ☐ | |
| 18 | D5 入口文件全部存在（4 个） | ☐ | |
| 19 | D5 REST 端点全部存在（6 个） | ☐ | |
| 20 | D5 Entry → Service Only 验证通过 | ☐ | |
| 21 | E5 集成测试 10/10 通过 | ☐ | |
| 22 | 依赖 DAG 验证通过 | ☐ | |
| 23 | D3 冻结契约验证通过 | ☐ | |
| 24 | D4 冻结契约验证通过 | ☐ | |
| 25 | A-C 阶段约束验证通过（P1~P7） | ☐ | |

### 14.2 验收标准

**全部 25 项检查通过** → Phase E 验收通过。

**任何一项未通过** → 记录失败详情，参照第 15 节故障排查解决后重新验证。

---

## 15. 故障排查

### 15.1 常见问题

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| `ModuleNotFoundError: No module named 'backend'` | `src/` 不在 Python 路径 | 检查 `tests/conftest.py` 是否将 `src/` 添加到 `sys.path` |
| `ImportError: cannot import name 'XXX'` | 缺少依赖或未安装 | 运行 `uv cache clean && uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | 旧版 pytest-asyncio | 升级: `uv pip install --upgrade pytest-asyncio` |
| `MappedAnnotationError` | ORM 模型类型注解问题 | 确保 `Mapped[UUID]` 已替换 `Mapped[Any]`，且 `from uuid import UUID` 已添加 |
| `AttributeError: 'NoneType' object is not callable` | 方法名不匹配 | 检查 `BaseResponse.error_response` 而非 `BaseResponse.error` |
| `UnicodeDecodeError: 'gbk' codec` | 文件编码问题 | 确保使用 `encoding='utf-8'` 打开文件 |
| `pytest collection error` | 测试文件语法错误 | 检查测试文件是否有 UTF-8 编码问题 |

### 15.2 完整重置步骤

如果验证过程中出现无法解决的问题，可以尝试完整重置：

**Windows (PowerShell)**:

```powershell
cd backend
Remove-Item -Recurse -Force .venv
uv sync --all-extras
uv run pytest tests/ -v --tb=no
```

**Linux/macOS (bash)**:

```bash
cd backend
rm -rf .venv
uv sync --all-extras
uv run pytest tests/ -v --tb=no
```

### 15.3 联系支持

如果以上步骤无法解决问题，请：

1. 记录完整的错误信息和输出
2. 确认 Python 版本为 3.11 或 3.12
3. 确认 uv 版本为 0.4.0+
4. 确认 git 分支为 `main`
5. 确认 `git status --short` 输出为空

---

## 附录 A: 验证命令速查表

| 步骤 | 命令 | 预期结果 |
|------|------|---------|
| 环境 | `python --version` | `Python 3.11.x` |
| 依赖 | `uv sync --all-extras` | `Resolved XX packages` |
| 代码检查 | `uv run ruff check src/ tests/` | `All checks passed!` |
| 全部测试 | `uv run pytest tests/ -v --tb=no` | `221 passed` |
| 集成测试 | `uv run pytest tests/test_integration.py -v` | `10 passed` |
| 服务验证 | `uv run python self_review.py` | 所有服务方法 OK |
| 引擎验证 | `uv run python self_review.py` | 所有引擎方法 OK |
| 边界验证 | `uv run python self_review.py` | 依赖 DAG OK |

---

*本指南由系统架构组编写，适用于对项目没有任何先验知识的开发者。*
