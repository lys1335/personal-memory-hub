# D2 Verification Guide

> **Phase**: Phase D — Document-Driven Implementation  
> **Milestone**: D2 — Repository Layer  
> **Version**: 1.0  
> **Date**: 2026-07-07  
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
7. [mypy Verification](#7-mypy-verification)  
8. [pytest Verification](#8-pytest-verification)  
9. [Repository Inventory Verification](#9-repository-inventory-verification)  
10. [Repository Contract Verification](#10-repository-contract-verification)  
11. [Architecture Boundary Verification](#11-architecture-boundary-verification)  
12. [Release Blocker Verification](#12-release-blocker-verification)  
13. [Architecture Debt Verification](#13-architecture-debt-verification)  
14. [Repository Freeze Confirmation](#14-repository-freeze-confirmation)  
15. [Final Acceptance Checklist](#15-final-acceptance-checklist)  
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Purpose

### 1.1 What This Guide Verifies

This guide verifies that **D2 — Repository Layer** has been implemented correctly. D2 establishes the data persistence layer for the Personal Memory Hub project:

- **9 CRUD Repositories**: EntityRepository, MemoryNodeRepository, EvidenceRepository, RelationshipRepository, VectorDocRepository, ArchiveRepository, TagRepository, TaskRepository, CandidateRepository
- **3 Query Repositories**: MemoryQueryRepository, EntityQueryRepository, VectorQueryRepository
- **Shared Infrastructure**: BaseRepository, QueryRepository, pagination, workspace isolation, type utilities
- **Type Safety**: Full mypy strict mode compliance across all 12 repositories
- **Test Coverage**: 98 tests covering CRUD operations, query repositories, infrastructure, and import boundaries

### 1.2 What This Guide Does NOT Verify

The following are explicitly **out of scope** for D2 verification:

- **Service Layer** — No service implementations exist yet (D3)
- **Engine Layer** — No engine/business logic implementations exist yet (D4)
- **API Endpoints** — No REST, MCP, or CLI adapters exist yet (D5)
- **Production deployment** — CD pipeline is intentionally deferred
- **Performance benchmarks** — No load testing is performed in D2
- **Database migrations** — DDL is defined but migrations are deferred to D3

### 1.3 Verification Philosophy

This guide is designed for a developer with **no prior knowledge** of the project. Every command is copy-and-paste ready. Every expected output is documented. If a step fails, the Troubleshooting section provides diagnosis and resolution.

---

## 2. Prerequisites

Before beginning verification, ensure the following tools are installed.

### 2.1 Operating System

**Supported**:

- Windows 10/11 (64-bit)
- macOS 12+ (Monterey or later)
- Ubuntu 20.04+ / Debian 11+ / Fedora 38+

**Windows is the default platform for this guide.** Every command section presents the Windows PowerShell command first, followed by the Linux/macOS bash equivalent.

### 2.2 Python

- **Required**: Python 3.11 or 3.12
- **Minimum**: Python 3.10 (project declares `requires-python = ">=3.10"`)

**Download**: https://www.python.org/downloads/

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

If Python is not installed or the version is below 3.10, install it before proceeding.

### 2.3 uv

- **Required**: uv 0.4.0 or later
- **Purpose**: Fast Python package installer and project manager

**Download**: https://docs.astral.sh/uv/getting-started/installation/

**Install on Windows** (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Install on Linux/macOS** (terminal):

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

- **Required**: Git 2.40+
- **Purpose**: Repository cloning

**Download**: https://git-scm.com/downloads

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

If the output is not `main`, switch to it:

**Windows (PowerShell)**:

```powershell
git checkout main
```

**Linux/macOS (bash)**:

```bash
git checkout main
```

### 3.3 Verify Repository Synchronization

**Windows (PowerShell)**:

```powershell
git status --short
echo "---"
git log --oneline -1
echo "---"
git rev-parse HEAD
git rev-parse @{u} 2>&1
```

**Linux/macOS (bash)**:

```bash
git status --short
echo "---"
git log --oneline -1
echo "---"
git rev-parse HEAD
git rev-parse @{u} 2>&1
```

**Expected output**:

```
(empty — no uncommitted changes)
019f6eb docs(d2-closing): Add Architecture Debt inventory for Repository Layer
019f6eb5527d21294047243387caeff43ab0cab7
019f6eb5527d21294047243387caeff43ab0cab7
```

- **Working tree must be clean** (no `git status --short` output)
- **Local HEAD must equal remote HEAD** (same commit hash)

If the working tree is not clean or HEADs differ, run:

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

**Expected Result**: Repository fully synchronized.

**If Failed**: Resolve any local changes, then re-run the synchronization check.

---

## 4. Python Environment Verification

> **Working directory**: All `uv` commands in this section must be executed from the `backend/` directory.

### 4.1 Navigate to Backend

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

**Expected output**: `True` (Windows) or `exists` (Linux/macOS).

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

The exact package count may vary, but you should see:

- `personal-memory-hub==0.1.0` (the project itself)
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
- `uuid_extensions` (for UUIDv7)
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

**Expected Result**: All dependencies installed and importable.

**If Failed**: Run `uv cache clean && uv sync --all-extras` to reinstall.

---

## 6. Ruff Verification

### 6.1 Run Linting

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

### 6.2 What a Successful Result Looks Like

- Zero violations reported
- Exit code `0`
- No warnings

### 6.3 Common Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `F401 module imported but unused` | Unused import | Remove the import or use it |
| `E501 line too long` | Line exceeds 120 characters | Split the line |
| `I001 import block is un-sorted` | Imports not sorted | Run `uv run ruff check --fix src/ tests/` |

---

## 7. mypy Verification

### 7.1 Run Type Checking

**Windows (PowerShell)**:

```powershell
uv run mypy src/
```

**Linux/macOS (bash)**:

```bash
uv run mypy src/
```

**Expected output**:

```
Success: no issues found in 36 source files
```

Exit code should be `0`.

### 7.2 What a Successful Result Looks Like

- `Success: no issues found in 36 source files`
- Exit code `0`
- No error messages

### 7.3 mypy Strict Mode Configuration

The project uses mypy strict mode, which enforces:

- `disallow_untyped_defs = true` — All functions must have type annotations
- `disallow_incomplete_defs = true` — All type annotations must be complete
- `check_untyped_defs = true` — Typed checker also checks unannotated functions
- `no_implicit_optional = true` — Explicit `| None` required for optional types

### 7.4 Common Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `error: Missing type parameters for generic type` | Missing generic args | Add `# type: ignore[type-arg]` for SQLAlchemy dynamic patterns |
| `error: Function is missing a return type annotation` | Missing return type | Add `-> ReturnType` to the function signature |
| `error: Argument 1 has incompatible type` | Type mismatch | Fix the type annotation or value |

---

## 8. pytest Verification

### 8.1 Run Tests

**Windows (PowerShell)**:

```powershell
uv run pytest tests/ -v
```

**Linux/macOS (bash)**:

```bash
uv run pytest tests/ -v
```

**Expected output**:

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

All 98 tests should pass. Exit code should be `0`.

### 8.2 Test Suite Breakdown

| Test File | Class | Tests | Purpose |
|-----------|-------|-------|---------|
| `test_entity_domain_repositories.py` | `TestEntityRepository` | 16 | Entity CRUD, Area, UserProfile, pagination |
| `test_entity_domain_repositories.py` | `TestRelationshipRepository` | 10 | Relationship CRUD, memory relationships, pagination |
| `test_entity_domain_repositories.py` | `TestEntityQueryRepository` | 13 | Entity graph queries, alias/type filtering, pagination |
| `test_fixtures.py` | — | 3 | DI container, settings, test engine fixtures |
| `test_memory_domain_repositories.py` | `TestEvidenceRepository` | 6 | Evidence CRUD, update/soft-delete prohibited |
| `test_memory_domain_repositories.py` | `TestMemoryNodeRepository` | 9 | Memory CRUD, evidence chain, pagination |
| `test_memory_domain_repositories.py` | `TestArchiveRepository` | 4 | Archive CRUD, period filtering, pagination |
| `test_memory_domain_repositories.py` | `TestTagRepository` | 4 | Tag CRUD, workspace/name filtering, pagination |
| `test_memory_domain_repositories.py` | `TestImportBoundaries` | 2 | Verify no service/engine imports in repository |
| `test_repository_infrastructure.py` | — | 29 | BaseRepository, QueryRepository, workspace isolation, pagination, error handling |
| `test_smoke.py` | — | 1 | Basic smoke test |

### 8.3 Expected Passing Result

- **98 tests collected**
- **98 tests passed**
- **0 tests failed**
- **0 tests errored**
- **Exit code: 0**

### 8.4 Common Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `ModuleNotFoundError: No module named 'backend'` | `src/` not on Python path | Check `tests/conftest.py` adds `src/` to `sys.path` |
| `ImportError: cannot import name 'XXX'` | Missing dependency | Run `uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | Old pytest-asyncio version | Upgrade: `uv pip install --upgrade pytest-asyncio` |
| `Fixture 'XXX' not found` | Fixture not defined in conftest.py | Check `tests/test_fixtures.py` has the fixture |

---

## 9. Repository Inventory Verification

### 9.1 Verify Repository Files Exist

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

**Expected output**: All 17 files should show `OK:`.

### 9.2 Verify 12 Repository Implementations

The D2 Repository Layer consists of **12 repositories** organized into two categories:

#### 9.2.1 CRUD Repositories (9)

| # | Repository | Aggregate | Domain | File |
|---|-----------|-----------|--------|------|
| 1 | EntityRepository | Entity | Entity | `entity_repository.py` |
| 2 | MemoryNodeRepository | MemoryNode | Memory | `memory_node_repository.py` |
| 3 | EvidenceRepository | Evidence | Ingestion | `evidence_repository.py` |
| 4 | RelationshipRepository | Relationship | Entity | `relationship_repository.py` |
| 5 | VectorDocRepository | VectorDoc | Retrieval | `vector_doc_repository.py` |
| 6 | ArchiveRepository | Archive | Memory | `archive_repository.py` |
| 7 | TagRepository | Tag | Memory | `tag_repository.py` |
| 8 | TaskRepository | Task | Runtime | `task_repository.py` |
| 9 | CandidateRepository | Candidate | Reflection | `candidate_repository.py` |

#### 9.2.2 Query Repositories (3)

| # | Repository | Aggregate | Domain | File |
|---|-----------|-----------|--------|------|
| 10 | MemoryQueryRepository | MemoryNode | Memory | `memory_query_repository.py` |
| 11 | EntityQueryRepository | Entity | Entity | `entity_query_repository.py` |
| 12 | VectorQueryRepository | Vector | Retrieval | `vector_query_repository.py` |

### 9.3 Verify Shared Infrastructure Files

| File | Purpose |
|------|---------|
| `base.py` | `BaseRepository[T]` — Generic CRUD base with async operations |
| `query.py` | `QueryRepository[T]` — Read-only base for complex queries |
| `pagination.py` | `OffsetPage`, `CursorPage` — Pagination models |
| `types.py` | `get_table_columns()`, `get_primary_key_column()` — Type utilities |
| `workspace.py` | `WorkspaceFilterMixin` — Multi-tenant workspace isolation |
| `exceptions.py` | `NotFoundError`, `DuplicateError`, `ReadOnlyError` — Repository exceptions |

**Expected Result**: 12 repositories present. All shared infrastructure files present.

**If Failed**: Check that the repository was cloned from the correct branch (`main`) and commit (`019f6eb`).

---

## 10. Repository Contract Verification

### 10.1 Verify CRUD Repositories Have Write Operations

Each CRUD repository should implement write operations: `create`, `update`, `soft_delete`, and `delete`.

**Windows (PowerShell)**:

```powershell
$crud_repos = @(
    "entity_repository.py",
    "memory_node_repository.py",
    "evidence_repository.py",
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
    $has_update = $content -match "async def update\("
    $has_soft_delete = $content -match "async def soft_delete\("
    $status = if ($has_create -and $has_update -and $has_soft_delete) { "CRUD OK" } else { "INCOMPLETE" }
    Write-Output "$status: $repo (create=$has_create, update=$has_update, soft_delete=$has_soft_delete)"
}
```

**Linux/macOS (bash)**:

```bash
for f in entity_repository memory_node_repository evidence_repository relationship_repository vector_doc_repository archive_repository tag_repository task_repository candidate_repository; do
  content=$(grep -c "async def create\|async def update\|async def soft_delete" "src/backend/repository/${f}_repository.py" 2>/dev/null || echo 0)
  echo "${content}/3 methods found: ${f}_repository.py"
done
```

**Expected output**: Each CRUD repository should show 3/3 methods found.

### 10.2 Verify Query Repositories Are Read-Only

Query repositories should NOT implement write operations. They should only have read-only methods: `find`, `find_page`, `count`, `get_entity_graph`, etc.

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

**Expected output**: All 3 query repositories should show `READ-ONLY OK`.

**Expected Result**: Repository responsibilities match architecture. CRUD repos have write operations; Query repos are read-only.

**If Failed**: Check that the repository files have not been modified incorrectly.

---

## 11. Architecture Boundary Verification

### 11.1 Verify Repository Never Calls Repository

Repositories must operate independently. No repository should import or call another repository.

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
Write-Output "Cross-repository import check complete"
```

**Linux/macOS (bash)**:

```bash
for f in src/backend/repository/*_repository.py; do
  basename=$(basename "$f")
  for target in entity_repository memory_node_repository evidence_repository relationship_repository vector_doc_repository archive_repository tag_repository task_repository candidate_repository memory_query_repository entity_query_repository vector_query_repository; do
    if [ "$basename" != "${target}.py" ] && grep -q "from backend\.repository\.${target}" "$f" 2>/dev/null; then
      echo "VIOLATION: $basename imports $target"
    fi
  done
done
echo "Cross-repository import check complete"
```

**Expected output**: No violations reported.

### 11.2 Verify No Service Dependency

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path src\backend\repository\*.py | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match "from backend\.service|import.*service") {
        Write-Output "VIOLATION: $($_.Name) imports service"
    }
}
Write-Output "Service dependency check complete"
```

**Linux/macOS (bash)**:

```bash
for f in src/backend/repository/*.py; do
  if grep -q "from backend\.service\|import.*service" "$f" 2>/dev/null; then
    echo "VIOLATION: $(basename $f) imports service"
  fi
done
echo "Service dependency check complete"
```

**Expected output**: No violations reported.

### 11.3 Verify No Engine Dependency

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path src\backend\repository\*.py | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match "from backend\.engine|import.*engine") {
        Write-Output "VIOLATION: $($_.Name) imports engine"
    }
}
Write-Output "Engine dependency check complete"
```

**Linux/macOS (bash)**:

```bash
for f in src/backend/repository/*.py; do
  if grep -q "from backend\.engine\|import.*engine" "$f" 2>/dev/null; then
    echo "VIOLATION: $(basename $f) imports engine"
  fi
done
echo "Engine dependency check complete"
```

**Expected output**: No violations reported.

### 11.4 Verify No Runtime Dependency on Engine/Session

The repository layer must not directly depend on the database engine. It receives sessions via dependency injection.

**Windows (PowerShell)**:

```powershell
if (Select-String -Path src\backend\repository\*.py -Pattern "get_engine|AsyncEngine" -Quiet) {
    Write-Output "VIOLATION: Engine dependency found"
} else {
    Write-Output "No engine dependency found (correct)"
}
```

**Linux/macOS (bash)**:

```bash
if grep -rq "get_engine\|AsyncEngine" src/backend/repository/ 2>/dev/null; then
  echo "VIOLATION: Engine dependency found"
else
  echo "No engine dependency found (correct)"
fi
```

**Expected Result**: Repository Layer boundaries preserved.

**If Failed**: Any repository importing from `backend.service`, `backend.engine`, or calling `get_engine()` violates the architecture. Remove the offending import.

---

## 12. Release Blocker Verification

### 12.1 Verify Documentation Contains Release Blocker

The Release Blocker for Native pgvector Support must be documented in the Repository Inventory.

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Release Blocker" -Quiet) {
    Write-Output "Release Blocker section found"
} else {
    Write-Output "Release Blocker section MISSING"
}
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Native pgvector Support" -Quiet) {
    Write-Output "pgvector description found"
} else {
    Write-Output "pgvector description MISSING"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "Release Blocker" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "Release Blocker section found"
else
  echo "Release Blocker section MISSING"
fi
if grep -q "Native pgvector Support" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "pgvector description found"
else
  echo "pgvector description MISSING"
fi
```

### 12.2 Verify pgvector Documentation Completeness

The Release Blocker documentation should include:

| Item | Required | Location |
|------|----------|----------|
| Current String embedding storage | ✅ | `10_9_Repository_Inventory.md` §9 |
| pgvector dependency | ✅ | `10_9_Repository_Inventory.md` §9 |
| ORM migration to `Vector(1536)` | ✅ | `10_9_Repository_Inventory.md` §9 |
| PostgreSQL vector extension | ✅ | `10_9_Repository_Inventory.md` §9 |
| HNSW / IVFFlat indexes | ✅ | `10_9_Repository_Inventory.md` §9 |
| Native vector operators | ✅ | `10_9_Repository_Inventory.md` §9 |

**Windows (PowerShell)**:

```powershell
$file = "docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md"
$checks = @("String.*embedding", "pgvector", "Vector\(1536\)", "vector extension", "HNSW", "IVFFlat", "cosine distance")
foreach ($check in $checks) {
    if (Select-String -Path $file -Pattern $check -Quiet) {
        Write-Output "FOUND: $check"
    } else {
        Write-Output "MISSING: $check"
    }
}
```

**Linux/macOS (bash)**:

```bash
file="docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md"
for check in "embedding" "pgvector" "Vector\(1536\)" "extension" "HNSW" "IVFFlat" "cosine"; do
  if grep -qi "$check" "$file"; then
    echo "FOUND: $check"
  else
    echo "MISSING: $check"
  fi
done
```

**Expected Result**: Release blocker documented with all required items.

**If Failed**: Add the missing documentation to `10_9_Repository_Inventory.md` Section 9.

---

## 13. Architecture Debt Verification

### 13.1 Verify Architecture Debt Is Documented

The Architecture Debt for Repository Contract vs BaseRepository Signature Alignment must be documented.

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Architecture Debt" -Quiet) {
    Write-Output "Architecture Debt section found"
} else {
    Write-Output "Architecture Debt section MISSING"
}
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Repository Contract vs BaseRepository Signature Alignment" -Quiet) {
    Write-Output "Debt title found"
} else {
    Write-Output "Debt title MISSING"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "Architecture Debt" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "Architecture Debt section found"
else
  echo "Architecture Debt section MISSING"
fi
if grep -q "Repository Contract vs BaseRepository Signature Alignment" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "Debt title found"
else
  echo "Debt title MISSING"
fi
```

### 13.2 Verify Debt Metadata

The Architecture Debt should include:

| Field | Expected Value |
|-------|---------------|
| Status | Deferred |
| Priority | Low |
| Suggested Milestone | Post-MVP Architecture Review |
| Type | Design Debt (not a bug) |

**Windows (PowerShell)**:

```powershell
$file = "docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md"
foreach ($term in "Deferred", "Low", "Post-MVP", "Design Debt") {
    if (Select-String -Path $file -Pattern $term -Quiet) {
        Write-Output "FOUND: $term"
    } else {
        Write-Output "MISSING: $term"
    }
}
```

**Linux/macOS (bash)**:

```bash
file="docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md"
for term in "Deferred" "Low" "Post-MVP" "Design Debt"; do
  if grep -q "$term" "$file"; then
    echo "FOUND: $term"
  else
    echo "MISSING: $term"
  fi
done
```

**Expected Result**: Architecture debt documented with correct metadata.

**If Failed**: Add the Architecture Debt section to `10_9_Repository_Inventory.md`.

---

## 14. Repository Freeze Confirmation

### 14.1 Verify Repository Layer Is Frozen

The Repository Layer is officially frozen after D2.8 Type Safety Stabilization. Changes are restricted to:

**Allowed**:

- Bug fixes (mypy errors, runtime errors)
- Security fixes
- Framework compatibility updates (SQLAlchemy version bumps)
- ADR-driven evolution (Architecture Decision Records)

**Not Allowed**:

- Repository redesign
- Aggregate boundary changes
- Repository contract changes (method signatures, return types)
- Adding new repositories without ADR approval

### 14.2 Verify Freeze Is Documented

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "Frozen" -Quiet) {
    Write-Output "Repository freeze documented"
} else {
    Write-Output "Repository freeze NOT documented"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "Frozen" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "Repository freeze documented"
else
  echo "Repository freeze NOT documented"
fi
```

### 14.3 Verify D2.8 Completion

D2.8 Type Safety Stabilization is the final D2 activity. Verify it is documented.

**Windows (PowerShell)**:

```powershell
if (Select-String -Path docs\04_Retrieval_Ranking\10_9_Repository_Inventory.md -Pattern "D2\.8" -Quiet) {
    Write-Output "D2.8 Type Safety Stabilization documented"
} else {
    Write-Output "D2.8 NOT documented"
}
```

**Linux/macOS (bash)**:

```bash
if grep -q "D2\.8" docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md; then
  echo "D2.8 Type Safety Stabilization documented"
else
  echo "D2.8 NOT documented"
fi
```

**Expected Result**: Repository Layer is officially frozen. No further changes allowed without ADR.

---

## 15. Final Acceptance Checklist

Use this checklist to confirm D2 completion. Mark each item as complete (✓) or note any issues.

### 15.1 Repository Synchronization

- [ ] Repository cloned successfully
- [ ] Branch is `main`
- [ ] Working tree is clean (no uncommitted changes)
- [ ] Local HEAD equals remote HEAD (`019f6eb`)
- [ ] No staged or unstaged files

### 15.2 Dependency Installation

- [ ] `uv sync --all-extras` completes without errors
- [ ] Virtual environment `.venv/` exists
- [ ] All core packages importable (Section 4.2)

### 15.3 Code Quality

- [ ] `ruff check src/ tests/` reports zero violations
- [ ] `mypy src/` reports "Success: no issues found in 36 source files"
- [ ] All source files pass type checking in strict mode

### 15.4 Testing

- [ ] `pytest tests/ -v` collects 98 tests
- [ ] All 98 tests pass
- [ ] Test fixtures (settings, container, engine) work correctly
- [ ] No warnings or errors in test output

### 15.5 Repository Inventory

- [ ] 12 repositories present (9 CRUD + 3 Query)
- [ ] All shared infrastructure files present (base.py, query.py, pagination.py, types.py, workspace.py, exceptions.py)
- [ ] Repository Inventory document (`10_9_Repository_Inventory.md`) is up to date

### 15.6 Repository Contracts

- [ ] All 9 CRUD repositories have write operations (create, update, soft_delete)
- [ ] All 3 Query repositories are read-only (no create/update/soft_delete)
- [ ] Repository responsibilities match architecture

### 15.7 Architecture Boundaries

- [ ] No repository imports another repository
- [ ] No repository imports from `backend.service`
- [ ] No repository imports from `backend.engine`
- [ ] No repository calls `get_engine()` or depends on `AsyncEngine`

### 15.8 Release Blocker

- [ ] Release Blocker section exists in `10_9_Repository_Inventory.md` §9
- [ ] Native pgvector Support documented
- [ ] String embedding storage noted
- [ ] pgvector dependency listed
- [ ] ORM migration to `Vector(1536)` documented
- [ ] PostgreSQL vector extension documented
- [ ] HNSW / IVFFlat indexes documented
- [ ] Native vector operators documented

### 15.9 Architecture Debt

- [ ] Architecture Debt section exists in `10_9_Repository_Inventory.md` §10
- [ ] Repository Contract vs BaseRepository Signature Alignment documented
- [ ] Status: Deferred
- [ ] Priority: Low
- [ ] Milestone: Post-MVP Architecture Review

### 15.10 Repository Freeze

- [ ] Repository Layer freeze documented
- [ ] D2.8 Type Safety Stabilization documented as final D2 activity
- [ ] Allowed changes listed (bug fixes, security, framework, ADR)
- [ ] Prohibited changes listed (redesign, aggregate boundaries, contracts)

### 15.11 Acceptance Criteria

**Phase D2 is considered VERIFIED when ALL of the following are true**:

1. ✅ Repository is synchronized (clean working tree, HEAD matches remote)
2. ✅ All dependencies install without errors
3. ✅ `ruff check src/ tests/` passes with zero violations
4. ✅ `mypy src/` passes with zero errors
5. ✅ `pytest tests/ -v` reports 98 passed, 0 failed
6. ✅ 12 repositories present and verified
7. ✅ CRUD repos have write operations; Query repos are read-only
8. ✅ No cross-layer dependencies (service, engine, runtime)
9. ✅ Release Blocker documented
10. ✅ Architecture Debt documented
11. ✅ Repository Freeze confirmed

**If any item above fails, Phase D2 is NOT verified.**

---

## 16. Troubleshooting

### 16.1 uv sync Fails

**Symptoms**:

```
× No solution found when resolving dependencies
```

**Causes**:

- Package version constraints are incompatible
- Network issues preventing package download
- Corrupted uv cache

**Resolution**:

**Windows (PowerShell)**:

```powershell
uv cache clean
uv sync --all-extras
python --version  # Must be >= 3.10
Get-Content backend\pyproject.toml -TotalCount 50
```

**Linux/macOS (bash)**:

```bash
uv cache clean
uv sync --all-extras
python --version  # Must be >= 3.10
head -50 backend/pyproject.toml
```

### 16.2 ruff Reports Errors

**Symptoms**:

```
F401 `typing.Any` imported but unused
```

**Causes**:

- Dead imports
- Unsorted imports
- Line length violations

**Resolution**:

**Windows (PowerShell)**:

```powershell
uv run ruff check --fix src/ tests/
```

**Linux/macOS (bash)**:

```bash
uv run ruff check --fix src/ tests/
```

For remaining issues, manually edit the source files.

### 16.3 mypy Reports Errors

**Symptoms**:

```
error: Unused "type: ignore" comment
error: Function is missing a return type annotation
```

**Causes**:

- Stale type ignore comments
- Missing type annotations
- Type mismatches

**Resolution**:

**Windows (PowerShell)**:

```powershell
uv run mypy src/ --show-error-codes
```

**Linux/macOS (bash)**:

```bash
uv run mypy src/ --show-error-codes
```

Fix type annotations as needed. Remove obsolete `type: ignore` comments.

### 16.4 pytest Fails to Collect Tests

**Symptoms**:

```
collected 0 items
```

**Causes**:

- Test files not in `tests/` directory
- Test files not named `test_*.py`
- Python path not configured correctly

**Resolution**:

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

### 16.5 Import Errors in Tests

**Symptoms**:

```
ModuleNotFoundError: No module named 'backend'
```

**Causes**:

- `src/` not on Python path
- Working directory is incorrect

**Resolution**:

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

### 16.6 Git Synchronization Issues

**Symptoms**:

```
Your branch is behind 'origin/main' by X commits.
```

**Resolution**:

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

### 16.7 Repository Freeze Violations Detected

**Symptoms**:

A repository file has been modified in a way that changes the contract (method signatures, return types, aggregate boundaries).

**Resolution**:

1. Check the diff: `git diff backend/src/backend/repository/`
2. If the change is a bug fix, it is allowed
3. If the change modifies the contract, revert it and create an ADR first
4. If the change is a new repository, it requires ADR approval

---

## Appendix A: File Inventory

### A.1 Repository Source Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/backend/repository/__init__.py` | ~50 | Package exports |
| `src/backend/repository/base.py` | ~340 | `BaseRepository[T]` — Generic CRUD base |
| `src/backend/repository/query.py` | ~230 | `QueryRepository[T]` — Read-only base |
| `src/backend/repository/pagination.py` | ~100 | `OffsetPage`, `CursorPage` models |
| `src/backend/repository/types.py` | ~80 | Column type utilities |
| `src/backend/repository/workspace.py` | ~70 | Workspace filter mixin |
| `src/backend/repository/exceptions.py` | ~60 | Repository exceptions |
| `src/backend/repository/entity_repository.py` | ~350 | Entity CRUD |
| `src/backend/repository/memory_node_repository.py` | ~570 | MemoryNode CRUD |
| `src/backend/repository/evidence_repository.py` | ~370 | Evidence CRUD |
| `src/backend/repository/relationship_repository.py` | ~670 | Relationship CRUD |
| `src/backend/repository/vector_doc_repository.py` | ~430 | VectorDoc CRUD |
| `src/backend/repository/archive_repository.py` | ~400 | Archive CRUD |
| `src/backend/repository/tag_repository.py` | ~370 | Tag CRUD |
| `src/backend/repository/task_repository.py` | ~400 | Task CRUD |
| `src/backend/repository/candidate_repository.py` | ~350 | Candidate CRUD |
| `src/backend/repository/memory_query_repository.py` | ~380 | Memory complex queries |
| `src/backend/repository/entity_query_repository.py` | ~640 | Entity graph queries |
| `src/backend/repository/vector_query_repository.py` | ~470 | Vector similarity queries |

### A.2 Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `tests/test_entity_domain_repositories.py` | 39 | Entity, Relationship, EntityQueryRepository |
| `tests/test_fixtures.py` | 3 | DI container, settings, engine |
| `tests/test_memory_domain_repositories.py` | 25 | Evidence, MemoryNode, Archive, Tag, import boundaries |
| `tests/test_repository_infrastructure.py` | 29 | BaseRepository, QueryRepository, workspace isolation |
| `tests/test_smoke.py` | 1 | Basic smoke test |

### A.3 Documentation Files

| File | Purpose |
|------|---------|
| `docs/04_Retrieval_Ranking/10_9_Repository_Inventory.md` | Repository implementation inventory with Release Blocker and Architecture Debt |
| `docs/06_Guides/D2_Repository_Verification_Guide.md` | This document |
| `docs/06_Guides/zh-CN/D2_Repository_Verification_Guide.md` | Chinese localization |

---

## Appendix B: Command Quick Reference

All commands in this appendix are copy-and-paste ready. Execute from the directory noted below each command.

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

# Run type checking
uv run mypy src/

# Run tests
uv run pytest tests/ -v

# Verify repository synchronization
cd ..
git status --short
git log --oneline -1
git rev-parse HEAD
```

---

> **This guide is a living document.** Update it as D2 implementation evolves.
>
> **Previous milestone**: D1 — Infrastructure Foundation (verified)
>
> **Next milestone**: D3 — Service Layer (planned)
