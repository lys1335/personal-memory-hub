# D1 Verification Guide

> **Phase**: Phase D — Document-Driven Implementation  
> **Milestone**: D1 — Infrastructure Foundation  
> **Version**: 1.1  
> **Date**: 2026-07-04  
> **Status**: Final  
> **Author**: System Architecture Group

---

## Table of Contents

1. [Purpose](#1-purpose)  
2. [Prerequisites](#2-prerequisites)  
3. [Repository Preparation](#3-repository-preparation)  
4. [Python Environment Verification](#4-python-environment-verification)  
5. [Configuration Verification](#5-configuration-verification)  
6. [Build Verification](#6-build-verification)  
7. [Ruff Verification](#7-ruff-verification)  
8. [mypy Verification](#8-mypy-verification)  
9. [pytest Verification](#9-pytest-verification)  
10. [Docker Verification](#10-docker-verification)  
11. [Database Verification](#11-database-verification)  
12. [Documentation Verification](#12-documentation-verification)  
13. [Final Acceptance Checklist](#13-final-acceptance-checklist)  
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Purpose

### 1.1 What This Guide Verifies

This guide verifies that **D1 — Infrastructure Foundation** has been implemented correctly. D1 establishes the engineering baseline for the Personal Memory Hub project:

- Project directory structure with five-layer architecture
- Python package configuration via `pyproject.toml` and `uv`
- Configuration system using pydantic-settings
- Structured JSON logging via structlog
- SQLAlchemy async engine and session factory
- Alembic migration framework
- Lightweight dependency injection container
- pytest test framework with in-memory SQLite fixtures
- Docker and docker-compose for local development
- GitHub Actions CI pipeline scaffolding
- Documentation (README, setup guides)

### 1.2 What This Guide Does NOT Verify

The following are explicitly **out of scope** for D1 verification:

- **Business logic** — No Service, Engine, or Repository implementations exist yet (D2+)
- **Database schema** — No table models or migration files exist yet (D2)
- **API endpoints** — No REST, MCP, or CLI adapters exist yet (D5)
- **Production deployment** — CD pipeline is intentionally deferred
- **External integrations** — Supabase, Redis, OpenRouter are not required for D1
- **Performance benchmarks** — No load testing is performed in D1

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

### 2.4 Docker Desktop

- **Required**: Docker Desktop 4.0+ (or Docker Engine + docker-compose plugin)
- **Purpose**: Local development environment with PostgreSQL + pgvector

**Download**: https://www.docker.com/products/docker-desktop/

**Verify installation**:

**Windows (PowerShell)**:

```powershell
docker --version
docker compose version
```

**Linux/macOS (bash)**:

```bash
docker --version
docker compose version
```

**Expected output**:

```
Docker version 24.x.x, build xxxxxxx
Docker Compose version v2.x.x
```

If Docker Desktop is not installed, Docker-related verification steps (Section 10) can be skipped. The rest of D1 does not require Docker.

### 2.5 Git

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

### 3.2 Expected Directory Layout

After cloning, the repository root should contain:

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

**Verification**: Use the following command to check the structure.

> **Working directory**: Execute from the repository root (`personal-memory-hub/`).

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path backend -Recurse -File -Exclude __pycache__, .venv, .mypy_cache, .pytest_cache, .ruff_cache, dist | Select-Object -ExpandProperty FullName | Sort-Object
```

**Linux/macOS (bash)**:

```bash
find backend -type f ! -path "*/.venv/*" ! -path "*/.mypy_cache/*" ! -path "*/.pytest_cache/*" ! -path "*/.ruff_cache/*" ! -path "*/dist/*" ! -path "*/__pycache__/*" | sort
```

**Expected**: The output should list all files shown above (excluding `uv.lock` which is generated on `uv sync`, and `dist/` which is generated on `uv build`).

> **Note**: The directory tree above is a **complete representation** of committed files. It does **not** include auto-generated directories (`.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `dist/`, `__pycache__/`). These are excluded by `.gitignore`.

### 3.3 Expected Key Files

The following files must exist:

| File | Purpose |
|------|---------|
| `backend/pyproject.toml` | Project configuration, dependencies, tool settings |
| `backend/.env.example` | Environment variable template |
| `backend/src/backend/shared/infrastructure/config/settings.py` | Configuration system |
| `backend/src/backend/shared/infrastructure/logging/__init__.py` | Logging framework |
| `backend/src/backend/shared/infrastructure/database/engine.py` | SQLAlchemy engine/session |
| `backend/src/backend/shared/infrastructure/di/container.py` | DI container |
| `backend/src/backend/shared/infrastructure/database/__init__.py` | Database exports |
| `backend/alembic/env.py` | Alembic environment |
| `backend/Dockerfile` | Container build |
| `docker-compose.yml` | Local dev environment |
| `.github/workflows/ci.yml` | CI pipeline |
| `README.md` | Project overview |
| `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` | D1 planning doc |

### 3.4 Files by Category

The table below classifies every file produced by D1. Use it to understand what belongs in Git versus what is generated locally.

| Category | Examples | Should Exist in Git | Notes |
|----------|----------|---------------------|-------|
| **Source code** | `backend/src/`, `backend/tests/` | Yes | All `.py` files |
| **Configuration** | `pyproject.toml`, `alembic.ini`, `.github/workflows/ci.yml` | Yes | Tool configs and CI |
| **Lock file** | `backend/uv.lock` | Yes | **Committed** — ensures reproducible builds |
| **Environment template** | `backend/.env.example` | Yes | Template; `.env` is **not** committed |
| **Documentation** | `README.md`, `docs/` | Yes | All markdown files |
| **Container** | `backend/Dockerfile`, `docker-compose.yml` | Yes | Docker configuration |
| **Build output** | `backend/dist/` | **No** | Generated by `uv build` |
| **Virtual environment** | `.venv/` | **No** | Generated by `uv sync` |
| **Cache directories** | `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/` | **No** | Regenerated automatically |
| **Local config** | `.env`, `.env.local` | **No** | Machine-specific, contains secrets |

---

## 4. Python Environment Verification

> **Working directory**: All `uv` commands in this section must be executed from the `backend/` directory.

### 4.1 Install Dependencies

Navigate to the backend directory and install all dependencies:

**Windows (PowerShell)**:

```powershell
cd backend
uv sync --all-extras
```

**Linux/macOS (bash)**:

```bash
cd backend
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
- `psycopg2-binary` or `asyncpg`
- `coverage`

### 4.2 Verify Virtual Environment

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path .venv -Recurse -Depth 1 | Select-Object Name, Mode
```

**Linux/macOS (bash)**:

```bash
ls -la .venv/
```

**Expected**: A `.venv/` directory exists with `Scripts/` (Windows) or `bin/` (Linux/macOS) containing Python executables and installed packages.

### 4.3 Verify Package Installation

> **Note**: This section verifies that core packages are importable. For version verification, see Sections 7 and 8 which use CLI commands (`uv run ruff --version`, `uv run mypy --version`).

**Windows (PowerShell)**:

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

**Linux/macOS (bash)**:

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

### 4.4 Common Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `uv: command not found` | uv not installed or not in PATH | Reinstall uv, ensure it's in PATH |
| `No module named 'sqlalchemy'` | Dependencies not installed | Run `uv sync --all-extras` |
| `Python version mismatch` | Project requires >=3.10 | Install Python 3.10+ |
| `Could not find a version that satisfies the requirement` | Package not available for this Python version | Check package compatibility, try different Python version |

### 4.5 Recovery Steps

If verification fails:

**Windows (PowerShell)**:

```powershell
Remove-Item -Recurse -Force .venv
uv cache clean
uv sync --all-extras
```

**Linux/macOS (bash)**:

```bash
rm -rf .venv
uv cache clean
uv sync --all-extras
```

---

## 5. Configuration Verification

> **Working directory**: All commands in this section must be executed from the `backend/` directory.

### 5.1 Copy .env.example

**Windows (PowerShell)**:

```powershell
Copy-Item .env.example .env
```

**Linux/macOS (bash)**:

```bash
cp .env.example .env
```

### 5.2 Environment Variables

The `.env.example` file documents all configurable variables. Here is the complete reference:

#### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `personal-memory-hub` | Application name |
| `APP_VERSION` | `0.1.0` | Application version |
| `APP_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/memory_hub` | PostgreSQL connection string |
| `DATABASE_ECHO` | `false` | Enable SQL query logging |
| `VECTOR_DIMENSION` | `1536` | Embedding vector dimension |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | *(empty)* | Supabase project URL (for hosted PostgreSQL) |
| `SUPABASE_ANON_KEY` | *(empty)* | Supabase anonymous key |
| `REDIS_URL` | *(empty)* | Redis connection URL (V2+ placeholder) |
| `OPENROUTER_API_KEY` | *(empty)* | OpenRouter API key (deferred to D3+) |

### 5.3 Verify Configuration Loading

**Windows (PowerShell)**:

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

**Linux/macOS (bash)**:

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

**Expected output**:

```
APP_NAME: personal-memory-hub
LOG_LEVEL: INFO
DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:...
VECTOR_DIMENSION: 1536
is_supabase: False
Configuration loaded successfully
```

### 5.4 Common Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `ModuleNotFoundError: No module named 'backend'` | Working directory is not `backend/` | `cd backend` before running |
| `PydanticSettingsError: Field "XXX" is not configured` | Missing required environment variable | Check `.env` file or environment |
| `ValidationError` | Invalid value for a setting | Check variable types and formats |

---

## 6. Build Verification

> **Working directory**: All commands in this section must be executed from the `backend/` directory.

### 6.1 Build the Package

**Windows (PowerShell)**:

```powershell
uv build
```

**Linux/macOS (bash)**:

```bash
uv build
```

**Expected output**:

```
Building source distribution...
Building wheel from source distribution...
Successfully built dist\personal_memory_hub-0.1.0.tar.gz
Successfully built dist\personal_memory_hub-0.1.0-py3-none-any.whl
```

### 6.2 Verify Distribution Files

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path dist
```

**Linux/macOS (bash)**:

```bash
ls -la dist/
```

**Expected**: Two files in the `dist/` directory:

- `personal_memory_hub-0.1.0.tar.gz` (source distribution)
- `personal_memory_hub-0.1.0-py3-none-any.whl` (wheel)

### 6.3 Failure Diagnosis

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `ValueError: Error parsing field project.license` | Invalid license field | Check `pyproject.toml` license field |
| `OSError: Readme file does not exist: README.md` | Missing README.md | Create `backend/README.md` |
| `hatchling.build.build_editable failed` | Build backend error | Check `pyproject.toml` configuration |

---

## 7. Ruff Verification

> **Working directory**: All commands in this section must be executed from the `backend/` directory.

### 7.1 Run Linting

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

### 7.2 Verify Ruff Version

**Windows (PowerShell)**:

```powershell
uv run ruff --version
```

**Linux/macOS (bash)**:

```bash
uv run ruff --version
```

**Expected output**:

```
ruff 0.15.x
```

### 7.3 What a Successful Result Looks Like

- Zero violations reported
- Exit code `0`
- No warnings

### 7.4 Common Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `F401 module imported but unused` | Unused import | Remove the import or use it |
| `E501 line too long` | Line exceeds 120 characters | Split the line |
| `I001 import block is un-sorted` | Imports not sorted | Run `uv run ruff check --fix` |
| `UP035 import from collections.abc` | Using deprecated import location | Change `from typing import X` to `from collections.abc import X` |

### 7.5 Auto-Fix

If ruff reports fixable issues:

**Windows (PowerShell)**:

```powershell
uv run ruff check --fix src/ tests/
```

**Linux/macOS (bash)**:

```bash
uv run ruff check --fix src/ tests/
```

This will automatically resolve issues marked with `[*]`.

---

## 8. mypy Verification

> **Working directory**: All commands in this section must be executed from the `backend/` directory.

### 8.1 Run Type Checking

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
Success: no issues found in XX source files
```

Exit code should be `0`.

### 8.2 Verify mypy Version

**Windows (PowerShell)**:

```powershell
uv run mypy --version
```

**Linux/macOS (bash)**:

```bash
uv run mypy --version
```

**Expected output**:

```
mypy 1.x.x
```

### 8.3 Expected Behavior

- All 16 source files should pass type checking
- No undefined names
- No type mismatches
- No missing return type annotations

### 8.4 Failure Diagnosis

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `error: Name 'XXX' is not defined` | Undefined variable or import | Add the import or fix the reference |
| `error: Argument 1 to "XXX" has incompatible type` | Type mismatch | Fix the type annotation or value |
| `error: Function is missing a return type annotation` | Missing return type | Add `-> ReturnType` to the function signature |
| `note: unused section(s)` | MyPy config sections for modules not yet imported | Harmless — these modules will be imported in D2+ |

### 8.5 Strict Mode

The project uses mypy strict mode, which enforces:

- `disallow_untyped_defs = true` — All functions must have type annotations
- `disallow_incomplete_defs = true` — All type annotations must be complete
- `check_untyped_defs = true` — Typed checker also checks unannotated functions
- `no_implicit_optional = true` — Explicit `| None` required for optional types

---

## 9. pytest Verification

> **Working directory**: All commands in this section must be executed from the `backend/` directory.

### 9.1 Run Tests

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

All 4 tests should pass. Exit code should be `0`.

### 9.2 Test Descriptions

#### test_fixture_settings

**File**: `tests/test_fixtures.py`  
**Purpose**: Verifies that the `settings` fixture returns a valid `AppSettings` instance with correct defaults.

**What it checks**:

- `settings` is an instance of `AppSettings`
- `settings.APP_NAME == "personal-memory-hub"`

#### test_fixture_container

**File**: `tests/test_fixtures.py`  
**Purpose**: Verifies that the DI container resolves `AppSettings` correctly.

**What it checks**:

- `container.resolve(AppSettings)` returns an `AppSettings` instance

#### test_fixture_test_engine

**File**: `tests/test_fixtures.py`  
**Purpose**: Verifies that the test engine fixture creates a valid async SQLAlchemy engine.

**What it checks**:

- `test_engine` is not `None`
- `test_engine` has an `begin` method (async engine characteristic)

#### test_pytest_works

**File**: `tests/test_smoke.py`  
**Purpose**: Basic smoke test to verify pytest collection and execution work.

**What it checks**:

- `True` is `True` (trivial assertion — confirms test framework is operational)

### 9.3 Expected Passing Result

- **4 tests collected**
- **4 tests passed**
- **0 tests failed**
- **0 tests errored**
- **Exit code: 0**

### 9.4 Common Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `ModuleNotFoundError: No module named 'backend'` | `src/` not on Python path | Check `tests/conftest.py` adds `src/` to `sys.path` |
| `ImportError: cannot import name 'XXX'` | Missing dependency | Run `uv sync --all-extras` |
| `asyncio.Mode.AUTO not recognized` | Old pytest-asyncio version | Upgrade: `uv pip install --upgrade pytest-asyncio` |
| `Fixture 'XXX' not found` | Fixture not defined in conftest.py | Check `tests/test_fixtures.py` has the fixture |

---

## 10. Docker Verification

> **Note**: This section requires Docker Desktop to be installed and running. If Docker is not available, skip this section and note it in the checklist.

> **Working directory**: All Docker commands must be executed from the **repository root** (`personal-memory-hub/`), NOT from `backend/`.

### 10.1 Start Docker Desktop

Ensure Docker Desktop is running. Verify with:

**Windows (PowerShell)**:

```powershell
docker info
```

**Linux/macOS (bash)**:

```bash
docker info
```

**Expected output** (truncated):

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

### 10.2 Start Services

From the repository root:

**Windows (PowerShell)**:

```powershell
docker compose up -d db
```

**Linux/macOS (bash)**:

```bash
docker compose up -d db
```

**Expected output**:

```
[+] Running 2/2
 ✔ Network personal-memory-hub_default  Created
 ✔ Container memory-hub-db              Started
```

### 10.3 Verify PostgreSQL Container

**Windows (PowerShell)**:

```powershell
docker compose ps
```

**Linux/macOS (bash)**:

```bash
docker compose ps
```

**Expected output**:

```
NAME            IMAGE                    STATUS
memory-hub-db   pgvector/pgvector:pg15   Up (healthy) ...
```

The `db` service should show status `Up (healthy)`.

### 10.4 Verify pgvector Extension

Connect to the database and check pgvector:

**Windows (PowerShell)**:

```powershell
docker compose exec db psql -U postgres -d memory_hub -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

**Linux/macOS (bash)**:

```bash
docker compose exec db psql -U postgres -d memory_hub -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

**Expected output**:

```
 extname 
---------
 vector
(1 row)
```

### 10.5 Verify Network

**Windows (PowerShell)**:

```powershell
docker network ls | Select-String "memory-hub"
```

**Linux/macOS (bash)**:

```bash
docker network ls | grep memory-hub
```

**Expected**: A network named `personal-memory-hub_default` or similar exists.

### 10.6 Verify Container Logs

**Windows (PowerShell)**:

```powershell
docker compose logs db
```

**Linux/macOS (bash)**:

```bash
docker compose logs db
```

**Expected output** (truncated):

```
memory-hub-db  | PostgreSQL Database directory appears to contain a database; Skipping initialization
memory-hub-db  | 2026-07-04 10:00:00.000 UTC [1] LOG:  starting PostgreSQL 15.x on ...
memory-hub-db  | 2026-07-04 10:00:00.000 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
memory-hub-db  | 2026-07-04 10:00:00.000 UTC [1] LOG:  database system is ready to accept connections
```

### 10.7 Shutdown Procedure

**Windows (PowerShell)**:

```powershell
docker compose down
```

**Linux/macOS (bash)**:

```bash
docker compose down
```

**Expected output**:

```
[+] Running 2/2
 ✔ Container memory-hub-db  Removed
 ✔ Network personal-memory-hub_default  Removed
```

### 10.8 Failure Diagnosis

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `Cannot connect to the Docker daemon` | Docker Desktop not running | Start Docker Desktop |
| `port is already allocated` | Port 5432 in use | See Section 14.10 for port conflict resolution |
| `pgvector/pgvector:pg15 not found` | Image not pulled | Run `docker pull pgvector/pgvector:pg15` |
| `permission denied` | Docker socket permissions | Run with sudo (Linux) or check Docker Desktop settings |

---

## 11. Database Verification

> **Working directory**: All commands in this section must be executed from the `backend/` directory.

### 11.1 Verify DATABASE_URL

**Windows (PowerShell)**:

```powershell
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
s = get_settings()
print(f'DATABASE_URL: {s.DATABASE_URL}')
print(f'DATABASE_ECHO: {s.DATABASE_ECHO}')
print(f'VECTOR_DIMENSION: {s.VECTOR_DIMENSION}')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
from backend.shared.infrastructure.config.settings import get_settings
s = get_settings()
print(f'DATABASE_URL: {s.DATABASE_URL}')
print(f'DATABASE_ECHO: {s.DATABASE_ECHO}')
print(f'VECTOR_DIMENSION: {s.VECTOR_DIMENSION}')
"
```

**Expected output**:

```
DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/memory_hub
DATABASE_ECHO: False
VECTOR_DIMENSION: 1536
```

### 11.2 Verify SQLAlchemy Initialization

**Windows (PowerShell)**:

```powershell
uv run python -c "
from backend.shared.infrastructure.database.engine import Base, get_engine, get_session_factory
print(f'Base: {Base}')
print(f'Engine: {get_engine()}')
print(f'Session factory: {get_session_factory()}')
print('SQLAlchemy initialized successfully')
"
```

**Linux/macOS (bash)**:

```bash
uv run python -c "
from backend.shared.infrastructure.database.engine import Base, get_engine, get_session_factory
print(f'Base: {Base}')
print(f'Engine: {get_engine()}')
print(f'Session factory: {get_session_factory()}')
print('SQLAlchemy initialized successfully')
"
```

**Expected output**:

```
Base: <class 'backend.shared.infrastructure.database.engine.Base'>
Engine: <sqlalchemy.ext.asyncio.engine.AsyncEngine object at 0x...>
Session factory: async_sessionmaker(...)
SQLAlchemy initialized successfully
```

### 11.3 Verify Alembic Environment

> **Working directory**: `backend/`

**Windows (PowerShell)**:

```powershell
uv run alembic check
```

**Linux/macOS (bash)**:

```bash
uv run alembic check
```

**Expected behavior**:

- If PostgreSQL is running and accessible: Alembic connects and reports the current migration state
- If PostgreSQL is NOT running: Alembic reports a connection error (this is expected in D1 — no database is required for the infrastructure to be considered complete)

**Example expected output (with database)**:

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**Example expected output (without database)**:

```
ConnectionRefusedError: [WinError 1225] ...
```

or

```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionRefusedError) connection refused
```

> **Important**: The error must be a connection error (e.g., `ConnectionRefusedError`, `OperationalError`), NOT a `NoSuchModuleError` or `Can't load plugin: sqlalchemy.dialects:driver` error. If you see the latter, see Section 14.11.

This is **expected and acceptable** for D1. The Alembic environment is correctly configured; it simply cannot connect because no PostgreSQL instance is running locally.

### 11.4 Explain Expected Behaviour If No Migrations Exist

At D1 completion:

- **Zero migration files** exist in `backend/alembic/versions/`
- **Alembic history** will show an empty revision graph
- **Alembic current** will report "No migrations present"
- This is **correct** — D1 only sets up the migration framework. Actual migrations are created in D2 when domain models are defined.

Verify with:

**Windows (PowerShell)**:

```powershell
uv run alembic history
```

**Linux/macOS (bash)**:

```bash
uv run alembic history
```

**Expected output** (if database is accessible):

```
Head (revision): <none>
```

Or if no database:

```
(ConnectionRefusedError — expected, no database running)
```

---

## 12. Documentation Verification

### 12.1 Verify README

Check that `README.md` exists and contains expected sections.

**Windows (PowerShell)**:

```powershell
Get-Content README.md
```

**Linux/macOS (bash)**:

```bash
cat README.md
```

**Expected sections**:

- Project title and description
- Quick Start (prerequisites, local development, Docker)
- Project Structure
- Architecture overview
- Implementation Milestones table
- Development section (coding standards, review workflow)
- License

### 12.2 Verify Documentation Links

The README should reference:

- `docs/INDEX.md` — Architecture documentation index
- `docs/05_Implementation/` — Implementation plans

Verify links are not broken by checking that referenced files exist:

**Windows (PowerShell)**:

```powershell
if (Test-Path docs/INDEX.md) { Write-Output "INDEX.md exists" } else { Write-Output "INDEX.md MISSING" }
if (Test-Path docs/05_Implementation/README.md) { Write-Output "Implementation README exists" } else { Write-Output "MISSING" }
if (Test-Path docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md) { Write-Output "D1 Plan exists" } else { Write-Output "MISSING" }
```

**Linux/macOS (bash)**:

```bash
test -f docs/INDEX.md && echo "INDEX.md exists" || echo "INDEX.md MISSING"
test -f docs/05_Implementation/README.md && echo "Implementation README exists" || echo "MISSING"
test -f docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md && echo "D1 Plan exists" || echo "MISSING"
```

**Expected output**:

```
INDEX.md exists
Implementation README exists
D1 Plan exists
```

### 12.3 Verify Docs Structure

**Windows (PowerShell)**:

```powershell
Get-ChildItem -Path docs -Recurse -Filter "*.md" | Sort-Object FullName
```

**Linux/macOS (bash)**:

```bash
find docs -type f -name "*.md" | sort
```

**Expected**: All architecture and implementation documents listed, including:

- `docs/INDEX.md`
- `docs/05_Implementation/README.md`
- `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md`
- All Phase A, B, C documents (from previous phases)

---

## 13. Final Acceptance Checklist

Use this checklist to confirm D1 completion. Mark each item as complete (✓) or note any issues.

### 13.1 Repository

- [ ] Repository cloned successfully
- [ ] Directory structure matches expected layout
- [ ] All expected files present (see Section 3.3)
- [ ] `docs/INDEX.md` updated with Phase D section
- [ ] `docs/05_Implementation/README.md` exists
- [ ] `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` exists

### 13.2 File Classification

Refer to Section 3.4 for the classification table. Key checks:

- [ ] `backend/uv.lock` exists (lock file — must be committed)
- [ ] `backend/dist/` does **not** exist (build output — should be ignored)
- [ ] `backend/.venv/` does **not** exist (virtual env — should be ignored)
- [ ] `__pycache__/` directories do **not** exist (cache — should be ignored)

### 13.3 Python Environment

- [ ] `uv sync --all-extras` completes without errors
- [ ] Virtual environment `.venv/` exists
- [ ] All core packages importable (Section 4.3)
- [ ] `uv build` produces `.tar.gz` and `.whl` files

### 13.4 Configuration

- [ ] `.env.example` exists and is documented
- [ ] Settings module loads without errors
- [ ] All environment variables have correct defaults
- [ ] `is_supabase` property returns `False` with empty Supabase config

### 13.5 Code Quality

- [ ] `ruff check src/ tests/` reports zero violations
- [ ] `mypy src/` reports "Success: no issues found"
- [ ] All source files pass type checking in strict mode

### 13.6 Testing

- [ ] `pytest tests/ -v` collects 4 tests
- [ ] All 4 tests pass
- [ ] Test fixtures (settings, container, engine) work correctly
- [ ] No warnings or errors in test output

### 13.7 Docker (Optional — skip if Docker not available)

- [ ] `docker compose up -d db` starts PostgreSQL
- [ ] Container status is `Up (healthy)`
- [ ] pgvector extension is installed
- [ ] `docker compose down` shuts down cleanly

### 13.8 Database Infrastructure

- [ ] SQLAlchemy engine initializes
- [ ] Session factory is configured
- [ ] Declarative base `Base` is importable
- [ ] Alembic `env.py` imports correctly
- [ ] Alembic migrations directory exists (empty, as expected)

### 13.9 Documentation

- [ ] `README.md` exists with all expected sections
- [ ] `backend/README.md` exists
- [ ] `docs/05_Implementation/README.md` exists
- [ ] All documentation links resolve to existing files
- [ ] No broken references

### 13.10 Git Readiness

Verify `.gitignore` correctly excludes generated files and includes committed files:

**Windows (PowerShell)**:

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

**Linux/macOS (bash)**:

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

**Expected**: `uv.lock` should NOT be ignored; all others should be ignored.

### 13.11 Architecture Compliance

- [ ] No business logic in `service/`, `engine/`, or `repository/` directories
- [ ] All empty directories contain `__init__.py` files
- [ ] Test directories contain README placeholders
- [ ] Layer boundaries are respected (no cross-layer imports except through protocols)

---

## 14. Troubleshooting

### 14.1 uv sync Fails

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

### 14.2 ruff Reports Errors

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

### 14.3 mypy Reports Errors

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

### 14.4 pytest Fails to Collect Tests

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

### 14.5 Docker Compose Fails

**Symptoms**:

```
ERROR: Cannot connect to the Docker daemon
```

**Causes**:

- Docker Desktop not running
- Insufficient permissions
- Port conflict

**Resolution**:

**Windows (PowerShell)**:

```powershell
# Start Docker Desktop (Windows/macOS)
# Or start Docker service (Linux)
docker info

# Check for port conflicts
netstat -an | findstr 5432

# If port is in use, change it in docker-compose.yml or .env
```

**Linux/macOS (bash)**:

```bash
sudo systemctl start docker
docker info
netstat -an | grep 5432
```

### 14.6 Settings Module Fails to Load

**Symptoms**:

```
pydantic_core.ValidationError: 1 validation error for AppSettings
```

**Causes**:

- Invalid environment variable format
- Missing required variable
- Type mismatch

**Resolution**:

**Windows (PowerShell)**:

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

**Linux/macOS (bash)**:

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

### 14.7 Alembic Connection Fails

**Symptoms**:

```
ConnectionRefusedError: [WinError 1225] ...
```

or

```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionRefusedError) connection refused
```

**Causes**:

- PostgreSQL not running
- Incorrect DATABASE_URL
- Firewall blocking connection

**Resolution**:

> This is **EXPECTED** in D1 if no PostgreSQL is running. The infrastructure is correctly configured; it simply cannot connect.

**Windows (PowerShell)**:

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

**Linux/macOS (bash)**:

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

### 14.8 Import Errors in Tests

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

### 14.9 Build Fails

**Symptoms**:

```
ValueError: Error parsing field project.license
```

**Causes**:

- Invalid license field in `pyproject.toml`
- Missing README.md

**Resolution**:

**Windows (PowerShell)**:

```powershell
Select-String -Path backend\pyproject.toml -Pattern "license"
Get-ChildItem backend\README.md
```

**Linux/macOS (bash)**:

```bash
grep license backend/pyproject.toml
ls backend/README.md
```

### 14.10 Docker Port Conflict (Port 5432 Already in Use)

**Symptoms**:

```
ERROR: for db Cannot start service 'db': driver failed programming external connectivity on endpoint memory-hub-db: Bind for 0.0.0.0:5432 failed: port is already allocated
```

or

```
port is already allocated
```

**Causes**:

- Another PostgreSQL instance is running on the machine (e.g., from a different project, WSL, or a system service)
- A database management tool has an open connection

**Identify the conflicting process**:

**Windows (PowerShell)**:

```powershell
netstat -ano | findstr ":5432"
```

**Linux/macOS (bash)**:

```bash
netstat -tlnp | grep 5432
```

This will show the PID of the process using port 5432.

**Resolution Option 1 — Stop the conflicting service**:

If you no longer need the other PostgreSQL instance, stop it. On Windows, check Task Manager for `postgres.exe` or `pgAdmin`. On Linux:

```bash
sudo systemctl stop postgresql
```

**Resolution Option 2 — Use a different host port**:

If you need to keep the other PostgreSQL running, change the host port mapping in `docker-compose.yml`:

1. Open `docker-compose.yml`
2. Find the `ports` section for the `db` service
3. Change `5432:5432` to `5433:5432` (or another available port)

```yaml
services:
  db:
    ports:
      - "5433:5432"  # Host port 5433 → container port 5432
```

4. Update `.env` to reflect the new host port:

```
DB_HOST=localhost
DB_PORT=5433
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/memory_hub
```

5. Restart Docker:

```bash
docker compose down
docker compose up -d db
```

**Resolution Option 3 — Restore default configuration**:

To revert to the default port 5432 after the conflicting service has been stopped:

1. Revert `docker-compose.yml` to use `5432:5432`
2. Revert `.env` to use port 5432
3. Restart:

```bash
docker compose down
docker compose up -d db
```

### 14.11 Alembic Shows "driver://" Plugin Error

**Symptoms**:

```
sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:driver
```

**Cause**:

This error occurs when `alembic.ini` contains the placeholder `sqlalchemy.url = driver://user:pass@localhost/dbname`. The SQLAlchemy dialect parser tries to load a dialect plugin called `driver`, which does not exist.

**Resolution**:

This has been fixed in D1.1. The `alembic.ini` file now has `sqlalchemy.url =` (blank), and `alembic/env.py` populates the URL from the application Settings at runtime. If you encounter this error, ensure your `alembic.ini` line 89 reads:

```ini
sqlalchemy.url =
```

(not `driver://user:pass@localhost/dbname`)

---

## Appendix A: File Inventory

### A.1 Source Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/backend/__init__.py` | ~10 | Package marker |
| `src/backend/shared/__init__.py` | ~3 | Shared module marker |
| `src/backend/shared/domain/__init__.py` | ~5 | Domain module marker (empty in D1) |
| `src/backend/shared/infrastructure/__init__.py` | ~3 | Infrastructure module marker |
| `src/backend/shared/infrastructure/config/__init__.py` | ~8 | Config exports |
| `src/backend/shared/infrastructure/config/settings.py` | ~100 | Settings model |
| `src/backend/shared/infrastructure/database/__init__.py` | ~8 | Database exports |
| `src/backend/shared/infrastructure/database/engine.py` | ~110 | Engine, session, Base |
| `src/backend/shared/infrastructure/di/__init__.py` | ~8 | DI exports |
| `src/backend/shared/infrastructure/di/container.py` | ~100 | DI container |
| `src/backend/shared/infrastructure/logging/__init__.py` | ~55 | Logger factory |
| `src/backend/shared/protocols/__init__.py` | ~5 | Protocols marker |
| `src/backend/scripts/README.md` | ~3 | Scripts placeholder |
| `src/backend/tools/README.md` | ~3 | Tools placeholder |
| `src/backend/entry/__init__.py` | ~4 | Entry layer marker (empty) |
| `src/backend/service/__init__.py` | ~4 | Service layer marker (empty) |
| `src/backend/engine/__init__.py` | ~4 | Engine layer marker (empty) |
| `src/backend/repository/__init__.py` | ~4 | Repository layer marker (empty) |

### A.2 Test Files

| File | Lines | Purpose |
|------|-------|---------|
| `tests/conftest.py` | ~15 | Pytest path configuration |
| `tests/test_fixtures.py` | ~95 | Fixture tests (4 tests) |
| `tests/test_smoke.py` | ~10 | Smoke test |

### A.3 Configuration Files

| File | Lines | Purpose |
|------|-------|---------|
| `backend/pyproject.toml` | ~140 | Project config, dependencies, tool settings |
| `backend/.env.example` | ~50 | Environment variable template |
| `backend/alembic.ini` | ~150 | Alembic configuration |
| `backend/alembic/env.py` | ~100 | Alembic environment |
| `backend/Dockerfile` | ~50 | Multi-stage Docker build |
| `docker-compose.yml` | ~80 | Local dev services |
| `.github/workflows/ci.yml` | ~100 | CI pipeline |
| `.gitignore` | ~60 | Git ignore patterns |

### A.4 Documentation Files

| File | Lines | Purpose |
|------|-------|---------|
| `README.md` | ~140 | Project overview |
| `backend/README.md` | ~10 | Backend package overview |
| `docs/05_Implementation/README.md` | ~80 | Implementation phase overview |
| `docs/05_Implementation/D1_Infrastructure_Foundation_Plan.md` | ~400 | D1 planning document |
| `docs/INDEX.md` | ~200 | Document index (updated for D1) |
| `docs/06_Guides/D1_Verification_Guide.md` | This document | Verification guide |

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

> **This guide is a living document.** Update it as D1 implementation evolves.
> 
> **Next milestone**: D2 — Repository Layer (planned)
> 
> **Document version**: 1.1 | **Last updated**: 2026-07-04 (D1.1 Release Readiness Fix)
