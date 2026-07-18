# D3/D4/D5/E5 Verification Guide

> **Phase**: Phase D — Document-Driven Implementation
> **Milestones**: D3 Service Layer + D4 Domain Engine Layer + D5 Entry Layer + E5 Integration Tests
> **Version**: 1.0
> **Date**: 2026-07-17
> **Status**: Final
> **Author**: System Architecture Group

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Prerequisites](#2-prerequisites)
3. [Repository Preparation](#3-repository-preparation)
4. [Python Environment Verification](#4-python-environment-verification)
5. [Dependency Installation](#5-dependency-installation)
6. [Ruff Verification](#6-ruff-verification)
7. [pytest Verification](#7-pytest-verification)
8. [D3 Service Layer Verification](#8-d3-service-layer-verification)
9. [D4 Engine Layer Verification](#9-d4-engine-layer-verification)
10. [D5 Entry Layer Verification](#10-d5-entry-layer-verification)
11. [E5 Integration Test Verification](#11-e5-integration-test-verification)
12. [Architecture Boundary Verification](#12-architecture-boundary-verification)
13. [Frozen Layer Contract Verification](#13-frozen-layer-contract-verification)
14. [Final Acceptance Checklist](#14-final-acceptance-checklist)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Purpose

### 1.1 What This Guide Verifies

This guide verifies that **D3 Service Layer + D4 Domain Engine Layer + D5 Entry Layer + E5 Integration Tests** have been implemented correctly.

These phases establish the complete business logic layer for the Personal Memory Hub project:

- **D3 Service Layer (5 services)**: MemoryService, QueryService, EntityService, ReflectionService, TaskService — 27 tests total
- **D4 Domain Engine Layer (6 engines)**: EntityEngine, MemoryEngine, RelationshipEngine, ReflectionEngine, SearchEngine, ProjectionEngine — 58 tests total
- **D5 Entry Layer (REST Adapter)**: RESTAdapter, ContractValidator, 9 external DTOs — 28 tests total
- **E5 Integration Tests**: end-to-end lifecycle, layer boundaries, DTO translation, error propagation, dependency DAG, frozen contracts — 10 tests total
- **D2 Repository Layer (existing code)**: 98 tests (as baseline, should not be broken)

**Total**: 221 tests, all passing.

### 1.2 What This Guide Does NOT Verify

The following are explicitly **out of scope** for D3/D4/D5/E5 verification:

- **Production deployment**: CD 
- **Performance benchmarking**: 
- **External integrations**: SupabaseRedisLLM Provider 
- **MCP/CLI Adapters**: MVP  REST  V2+
- **Advanced Entity features**: merge/alias/relationship  V2+

### 1.3 Verification Philosophy

This guide is intended for developers with **no prior knowledge** of the project. Every command can be copied and pasted directly. Every expected output is documented. If any step fails, the troubleshooting section provides diagnosis and resolution steps.

---

## 2. Prerequisites

Before starting verification, ensure the following tools are installed.

### 2.1 Operating System

**Supported platforms**:

- Windows 10/1164 
- macOS 12+Monterey 
- Ubuntu 20.04+ / Debian 11+ / Fedora 38+

**Windows ** Windows PowerShell  Linux/macOS bash 

### 2.2 Python

- ****: Python 3.11  3.12
- ****: Python 3.10 `requires-python = ">=3.10"`

****: https://www.python.org/downloads/

**Verify installation**:

**Windows (PowerShell)**:

```powershell
python --version
```

**Linux/macOS (bash)**:

```bash
python --version
```

**Expected output**:

```
Python 3.11.x
```

If Python is not installed or the version is below 3.10, install it first before continuing.

### 2.3 uv

- ****: uv 0.4.0 
- ****:  Python 

****: https://docs.astral.sh/uv/getting-started/installation/

**Windows ** (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS ** ():

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verify installation**:

**Windows (PowerShell)**:

```powershell
uv --version
```

**Linux/macOS (bash)**:

```bash
uv --version
```

**Expected output**:

```
uv 0.x.x (xxx...)
```

### 2.4 Git

- ****: Git 2.40+
- ****: 

****: https://git-scm.com/downloads

**Verify installation**:

**Windows (PowerShell)**:

```powershell
git --version
```

**Linux/macOS (bash)**:

```bash
git --version
```

**Expected output**:

```
git version 2.x.x
```

---

## 3. Repository Preparation

### 3.1 Clone Repository

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

**Expected output**:

```
Cloning into 'personal-memory-hub'...
remote: Enumerating objects: XXXX, done.
remote: Counting objects: 100% (XXX/XXX), done.
remote: Compressing objects: 100% (XXX/XXX), done.
remote: Total XXXX (delta XX), reused XXXX (delta XX), pack-reused XX
Receiving objects: 100% (XXXX/XXXX), X.XX MiB | X.XX MiB/s, done.
Resolving deltas: 100% (XX/XX), done.
```

### 3.2 Verify Branch

**Windows (PowerShell)**:

```powershell
git branch --show-current
```

**Linux/macOS (bash)**:

```bash
git branch --show-current
```

**Expected output**:

```
main
```

If the output is not `main`, switch to it

**Windows (PowerShell)**:

```powershell
git checkout main
```

**Linux/macOS (bash)**:

```bash
git checkout main
```

### 3.3 Verify Repository Sync

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

**Expected output**:

```
(No uncommitted changes)
cddb83e docs(E5): add code self-review report — A-C phase constraint verification
cddb83exxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
cddb83exxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- **** `git status --short` 
- ** HEAD  HEAD**

If working tree is dirty / HEAD inconsistent, run

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

****: 

****: 

---

## 4. Python Environment Verification

> ****:  `uv`  `backend/` 

### 4.1 Enter Backend Directory

**Windows (PowerShell)**:

```powershell
cd backend
```

**Linux/macOS (bash)**:

```bash
cd backend
```

### 4.2 Verify Virtual Environment Exists

**Windows (PowerShell)**:

```powershell
Test-Path .venv\Scripts\python.exe
```

**Linux/macOS (bash)**:

```bash
test -f .venv/bin/python && echo "exists" || echo "missing"
```

**Expected output**: `True`Windows `exists`Linux/macOS

If the virtual environment does not exist, proceed to Section 5 to install dependencies.

---

## 5. Dependency Installation

### 5.1 Install Dependencies

**Windows (PowerShell)**:

```powershell
uv sync --all-extras
```

**Linux/macOS (bash)**:

```bash
uv sync --all-extras
```

**Expected output**:

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

You should see the following key packages

- `personal-memory-hub==0.1.0`
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
- `uuid_extensions` UUIDv7
- `coverage`

### 5.2 Verify Core Packages

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

**Expected output**:

```
All core packages imported successfully
SQLAlchemy: 2.0.x
Pydantic: 2.x.x
Alembic: 1.x.x
structlog: 24.x.x
aiosqlite: 0.2x.x
pytest: 8.x.x
```

****: 

****:  `uv cache clean && uv sync --all-extras` 

---

## 6. Ruff Verification

### 6.1 Run Code Check

**Windows (PowerShell)**:

```powershell
uv run ruff check src/ tests/
```

**Linux/macOS (bash)**:

```bash
uv run ruff check src/ tests/
```

**Expected output**:

```
All checks passed!
```

Exit code should be `0`.

### 6.2 Characteristics of Successful Results

- Zero violation reports
- Exit code `0`
- No warnings

### 6.3 Common Failures

|  |  |  |
|------|------|---------|
| `F401 module imported but unused` | Unused import |  |
| `E501 line too long` | Line exceeds 120 characters |  |
| `I001 import block is un-sorted` | Imports not sorted |  `uv run ruff check --fix src/ tests/` |

---

## 7. pytest Verification

### 7.1 Run All Tests

**Windows (PowerShell)**:

```powershell
uv run pytest tests/ -v --tb=no
```

**Linux/macOS (bash)**:

```bash
uv run pytest tests/ -v --tb=no
```

**Expected output**:

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

** 221 **Exit code should be `0`.

### 7.2 Test Suite Breakdown

|  |  |  |
|---------|--------|---------|
| `test_engine_layer.py` | 58 | D4 Engine Layer: EngineBase + 6 engines + boundary tests |
| `test_entity_domain_repositories.py` | 39 | D2 Repository: Entity + Relationship + EntityQuery |
| `test_entry_layer.py` | 28 | D5 Entry Layer: Contract Validation + DTO + REST Adapter |
| `test_fixtures.py` | 3 | D1 Infrastructure: DI Container, Settings, Test Engine |
| `test_integration.py` | 10 | E5 Integration TestsDTODAG |
| `test_memory_domain_repositories.py` | 25 | D2 Repository: Evidence + MemoryNode + Archive + Tag |
| `test_repository_infrastructure.py` | 31 | D2 Repository: BaseRepository + QueryRepository + boundaries |
| `test_service_layer.py` | 27 | D3 Service Layer: BaseService + 5 services + DTOs |
| `test_smoke.py` | 1 | Smoke test |

### 7.3 Expected Passing Results

- **Collect 221 tests**
- **221 tests passed**
- **0 tests failed**
- **0 test errors**
- **Exit code: 0**

### 7.4 Common Failures

|  |  |  |
|------|------|---------|
| `ModuleNotFoundError: No module named 'backend'` | `src/`  Python  |  `tests/conftest.py`  `src/`  `sys.path` |
| `ImportError: cannot import name 'XXX'` | Missing dependency |  `uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | Outdated pytest-asyncio | : `uv pip install --upgrade pytest-asyncio` |
| `Fixture 'XXX' not found` | conftest.py  |  `tests/test_fixtures.py`  |

---

## 8. D3 

### 8.1 

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

**Expected output**:  9  `OK`

### 8.2 

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

**Expected output**:

```
All D3 service methods verified OK
```

### 8.3 

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

**Expected output**:

```
Service independence: OK (no cross-service calls)
```

---

## 9. D4 

### 9.1 

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

**Expected output**:  8  `OK`

### 9.2 

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

**Expected output**:

```
All D4 engine methods verified OK
```

### 9.3 

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

**Expected output**:

```
Engine independence: OK (no cross-engine calls)
```

---

## 10. D5 

### 10.1 

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

**Expected output**:  4  `OK`

### 10.2  REST 

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

**Expected output**:

```
All 6 REST endpoints verified OK
```

### 10.3  Entry → Service Only

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

**Expected output**:

```
Entry layer boundary: OK (only calls service)
```

---

## 11. E5 Integration Tests

### 11.1 

**Windows (PowerShell)**:

```powershell
uv run pytest tests/test_integration.py -v --tb=short
```

**Linux/macOS (bash)**:

```bash
uv run pytest tests/test_integration.py -v --tb=short
```

**Expected output**:

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

** 10 **

### 11.2 

|  |  |  |
|------|---------|---------|
| `test_full_memory_lifecycle` | Service → Engine → Repository | ✅  |
| `test_entry_calls_service_only` | Entry  Service Engine/Repository | ✅  |
| `test_service_calls_engine_and_repository` | Service  Engine + Repository | ✅  |
| `test_engine_calls_repository_only` | Engine  Repository Service/ Engine | ✅  |
| `test_dto_translation_round_trip` | DTO External → Internal → Response | ✅  |
| `test_error_propagation_through_layers` | Engine → Service → Entry | ✅  |
| `test_dependency_dag` |  DAG  | ✅  |
| `test_frozen_service_contract` | D3  | ✅  |
| `test_frozen_engine_contract` | D4  | ✅  |
| `test_frozen_repository_contract` | D2  | ✅  |

---

## 12. 

### 12.1 

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

**Expected output**:

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

## 13. 

### 13.1  D3 

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

**Expected output**:

```
D3 Services: 5 verified OK
Transaction ownership (G-106): OK
Command/Query separation (G-037): OK
```

### 13.2  D4 

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

**Expected output**:

```
D4 Engines: 6 verified OK
Domain Result (not Protocol Result): OK
Stateless Engine: OK
```

---

## 14. 

### 14.1 

| # |  |  |  |
|---|--------|------|------|
| 1 | Python 3.11+  | ☐ | |
| 2 | uv  | ☐ | |
| 3 | Git  | ☐ | |
| 4 |  `main` | ☐ | |
| 5 | HEAD  | ☐ | |
| 6 | `cd backend`  | ☐ | |
| 7 | `.venv`  | ☐ | |
| 8 | `uv sync --all-extras`  | ☐ | |
| 9 | SQLAlchemy, Pydantic  | ☐ | |
| 10 | `uv run ruff check src/ tests/`  | ☐ | |
| 11 | `uv run pytest tests/ -v --tb=no` — 221/221  | ☐ | |
| 12 | D3 9  | ☐ | |
| 13 | D3 5  | ☐ | |
| 14 | D3  | ☐ | |
| 15 | D4 8  | ☐ | |
| 16 | D4 6  | ☐ | |
| 17 | D4  | ☐ | |
| 18 | D5 4  | ☐ | |
| 19 | D5 REST 6  | ☐ | |
| 20 | D5 Entry → Service Only  | ☐ | |
| 21 | E5 Integration Tests 10/10  | ☐ | |
| 22 |  DAG  | ☐ | |
| 23 | D3  | ☐ | |
| 24 | D4  | ☐ | |
| 25 | A-C P1~P7 | ☐ | |

### 14.2 

** 25 ** → Phase E 

**** →  15 

---

## 15. 

### 15.1 

|  |  |  |
|------|------|---------|
| `ModuleNotFoundError: No module named 'backend'` | `src/`  Python  |  `tests/conftest.py`  `src/`  `sys.path` |
| `ImportError: cannot import name 'XXX'` | Missing dependency |  `uv cache clean && uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | Outdated pytest-asyncio | : `uv pip install --upgrade pytest-asyncio` |
| `MappedAnnotationError` | ORM  |  `Mapped[UUID]`  `Mapped[Any]` `from uuid import UUID`  |
| `AttributeError: 'NoneType' object is not callable` |  |  `BaseResponse.error_response`  `BaseResponse.error` |
| `UnicodeDecodeError: 'gbk' codec` |  |  `encoding='utf-8'`  |
| `pytest collection error` |  |  UTF-8  |

### 15.2 

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

### 15.3 

1. 
2.  Python  3.11  3.12
3.  uv  0.4.0+
4.  git  `main`
5.  `git status --short` 

---

##  A: 

|  |  |  |
|------|------|---------|
|  | `python --version` | `Python 3.11.x` |
|  | `uv sync --all-extras` | `Resolved XX packages` |
|  | `uv run ruff check src/ tests/` | `All checks passed!` |
|  | `uv run pytest tests/ -v --tb=no` | `221 passed` |
|  | `uv run pytest tests/test_integration.py -v` | `10 passed` |
|  | `uv run python self_review.py` |  OK |
|  | `uv run python self_review.py` |  OK |
|  | `uv run python self_review.py` |  DAG OK |

---

**
