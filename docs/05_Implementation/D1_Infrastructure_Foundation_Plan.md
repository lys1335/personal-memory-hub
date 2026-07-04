# Personal Memory Hub — D1 Infrastructure Foundation Plan

> **Version**: 1.0
> **Date**: 2026-07-04
> **Phase**: Phase D — Document-Driven Implementation
> **Stage**: D1 — Infrastructure Foundation
> **Status**: Planning (awaiting human approval)
> **Author**: System Architecture Group

---

## 1. Purpose

### 1.1 Objectives

Establish the engineering foundation required for all future implementation work in the Personal Memory Hub project. D1 creates a buildable, runnable, and testable project scaffold that:

- Provides a functional Python project with dependency management via `uv`
- Configures the database connectivity layer (PostgreSQL/Supabase + SQLAlchemy + Alembic)
- Sets up the logging framework and configuration system
- Establishes the dependency injection infrastructure
- Configures the testing framework with the testing architecture from 10_8
- Creates CI pipeline scaffolding via GitHub Actions
- Produces Docker support for local development and testing

### 1.2 Scope

D1 covers **engineering infrastructure only**:

- Project initialization and build system
- Database initialization and migration framework
- Configuration and logging systems
- Dependency injection framework
- Testing framework with fixtures infrastructure
- Docker and docker-compose for local environment
- CI/CD pipeline scaffolding
- Documentation scaffolding (README, setup guide)

### 1.3 Out of Scope

D1 explicitly excludes:

- **Business logic** — No Service, Engine, or Repository implementations
- **Domain models** — No Entity, MemoryNode, Evidence model code (only base infrastructure for ORM setup)
- **API endpoints** — No REST, MCP, CLI adapter implementations
- **Database schema** — No DDL execution or table creation (Alembic migration files are scaffolding only; actual schema from 09 is planned in D2)
- **Configuration values** — Only `.env.example` with documented keys (no actual configuration files)
- **Production deployment** — CD pipeline is deferred per 11 §8

---

## 2. Deliverables

The following outputs are expected upon D1 completion:

| # | Deliverable | Location | Description |
|---|-------------|----------|-------------|
| 1 | Project directory structure | `backend/` | Complete directory layout per 11 §5.1 |
| 2 | `pyproject.toml` | `backend/pyproject.toml` | Project metadata, dependencies, build config, tool configs |
| 3 | `uv` project initialization | `backend/.venv/` | Virtual environment managed by uv |
| 4 | Docker support | `backend/Dockerfile` | Multi-stage build for Python application |
| 5 | `docker-compose.yml` | Root `docker-compose.yml` | Local dev environment (app + PostgreSQL + pgvector) |
| 6 | `.env.example` | `backend/.env.example` | Documented environment variable template |
| 7 | SQLAlchemy initialization | `backend/src/shared/infrastructure/` | Engine factory, session factory, base model declarative base |
| 8 | Alembic initialization | `backend/alembic/` | Migration framework with environment configuration |
| 9 | Logging framework | `backend/src/shared/infrastructure/logging/` | Structured logging configuration |
| 10 | Configuration system | `backend/src/shared/infrastructure/config/` | Settings management via pydantic-settings |
| 11 | Dependency Injection framework | `backend/src/shared/infrastructure/di/` | Container/wiring infrastructure |
| 12 | Testing framework | `backend/tests/` | pytest configuration, conftest.py, base fixtures |
| 13 | GitHub Actions | `.github/workflows/ci.yml` | CI pipeline scaffolding (lint, type-check, test) |
| 14 | README updates | `README.md` | Updated with D1 completion status and setup instructions |

---

## 3. Work Breakdown

### D1.1 Project Initialization and Directory Structure

**Purpose**: Establish the canonical project layout as defined in 11 §5.1.

**Dependencies**: None.

**Expected outputs**:

```
backend/
├── src/
│   ├── entry/              # Entry Adapters (REST/MCP/CLI) — empty for D1
│   ├── service/            # Application Services — empty for D1
│   ├── engine/             # Domain Engines — empty for D1
│   ├── repository/         # Repository Layer — empty for D1
│   ├── shared/             # Common Module
│   │   ├── domain/         # Domain models (base classes only)
│   │   ├── infrastructure/ # Infrastructure: config, logging, DI, db
│   │   └── protocols/      # Abstract interfaces (Repository contracts)
│   └── __init__.py
├── tests/
│   ├── fixtures/           # Shared test fixtures per 10_8 §6.2
│   ├── scenarios/          # Test scenario data per 10_8 §6.3
│   ├── golden/             # Golden datasets per 10_8 §6.4
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── evaluation/         # Evaluation tests
│   └── conftest.py         # Base pytest configuration
├── scripts/                # Build, deploy, migration scripts
├── tools/                  # Development utilities
├── alembic/                # Alembic migration directory
├── alembic.ini              # Alembic configuration
├── pyproject.toml           # Project configuration
└── Dockerfile               # Container build
docker-compose.yml           # Local dev environment
.env.example                 # Environment template
```

**Verification**: Directory structure matches the layout above.

---

### D1.2 pyproject.toml and Dependency Management

**Purpose**: Define the Python project configuration, dependencies, and tool settings.

**Dependencies**: D1.1 (directory structure exists).

**Expected outputs**:

- `pyproject.toml` with:
  - Project metadata (name, version, description matching project vision)
  - Dependencies: `sqlalchemy>=2.0`, `pydantic>=2.0`, `pydantic-settings>=2.0`, `alembic>=1.13`, `psycopg2-binary` or `asyncpg`, `structlog` or `python-json-logger`, `pytest>=8.0`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `types-*` packages
  - Tool configurations: ruff lint settings, mypy strict mode config, pytest ini settings
  - Build system: `setuptools` or `hatchling`
  - UV workspace configuration if applicable

**Engineering decisions referenced**:
- ENG-001: Memory Hub = Infrastructure, Not Business Logic
- 11 §8: CI Strategy (ruff, mypy strict mode)
- 09 §9.2: PostgreSQL 15+ with pgvector 0.6+

**Verification**: `uv sync` succeeds. `ruff check` and `mypy --version` work.

---

### D1.3 Configuration System

**Purpose**: Provide a type-safe configuration loading mechanism.

**Dependencies**: D1.2 (dependencies available).

**Expected outputs**:

- `backend/src/shared/infrastructure/config/settings.py` — Pydantic-settings based settings model
- `backend/src/shared/infrastructure/config/__init__.py` — Settings singleton/expose
- `backend/.env.example` — Documented template with all required variables:
  - `DATABASE_URL` — PostgreSQL connection string
  - `SUPABASE_URL` (optional) — Supabase project URL
  - `SUPABASE_ANON_KEY` (optional) — Supabase anon key
  - `LOG_LEVEL` — Logging verbosity
  - `REDIS_URL` (V2+ placeholder)
  - `VECTOR_DIMENSION` — Embedding dimension (1536 per 09)
  - `UUID_VERSION` — UUID strategy (v7)
- No actual `.env` file created (gitignored)

**Engineering decisions referenced**:
- 09 §9.2.1: Technology stack (PostgreSQL, Supabase)
- ENG-015: UUIDv7 strategy

**Verification**: Settings model loads from `.env.example` values. Type hints validate field types.

---

### D1.4 Logging Framework

**Purpose**: Establish structured logging throughout the project.

**Dependencies**: D1.3 (configuration available for log level).

**Expected outputs**:

- `backend/src/shared/infrastructure/logging/__init__.py` — Logger factory
- `backend/src/shared/infrastructure/logging/config.py` — Logging configuration
- Structured JSON logging format (using `structlog` or `python-json-logger`)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Request ID injection capability (for distributed tracing per 10_7 §2.4 RequestContext)

**Verification**: Logger produces structured JSON output. Log level respects settings.

---

### D1.5 Database Infrastructure (SQLAlchemy + Alembic)

**Purpose**: Set up the ORM and migration framework. No domain models or schema yet.

**Dependencies**: D1.3 (configuration with DATABASE_URL).

**Expected outputs**:

- `backend/src/shared/infrastructure/database/engine.py` — SQLAlchemy engine/session factory
- `backend/src/shared/infrastructure/database/base.py` — Declarative base class
- `backend/src/shared/infrastructure/database/session.py` — Session management with scoped session
- `backend/alembic.ini` — Alembic configuration
- `backend/alembic/env.py` — Alembic environment with connection pooling
- `backend/alembic/versions/` — Empty versions directory with README
- `backend/alembic/script.py.mako` — Migration template

**Constraints**:
- No table models defined yet (deferred to D2)
- Engine and session factory are operational but not connected to any domain model
- Alembic `env.py` configured to import from `shared.infrastructure.database.base`
- Connection string sourced from settings

**Engineering decisions referenced**:
- 09 §9.2.1: PostgreSQL 15+, Supabase
- 09 §9.3: Naming conventions (schema: `memory_hub`)
- ENG-015: UUIDv7 for all PKs/FKs

**Verification**: `alembic current` runs without error (no migrations yet). Engine connects to test database.

---

### D1.6 Dependency Injection Framework

**Purpose**: Establish the DI infrastructure for wiring components.

**Dependencies**: D1.3 (configuration available).

**Expected outputs**:

- `backend/src/shared/infrastructure/di/container.py` — DI container/wiring
- `backend/src/shared/infrastructure/di/__init__.py` — Public exports
- Infrastructure for registering and resolving:
  - Settings (singleton)
  - Logger (singleton)
  - Database engine (singleton)
  - Database session factory (singleton)
- No domain service or engine registrations yet (deferred to D2+)

**Approach**: Use a lightweight DI mechanism (e.g., `dependency-injector` library or custom container pattern). The choice should align with ENG-001 (infrastructure, not business logic).

**Verification**: Container resolves settings, logger, engine, and session factory. Circular dependency detection works.

---

### D1.7 Testing Framework

**Purpose**: Establish the testing infrastructure per 10_8 (Testing Implementation Design).

**Dependencies**: D1.2 (pytest dependency), D1.6 (DI container available for fixtures).

**Expected outputs**:

- `backend/tests/conftest.py` — Base pytest configuration with:
  - Autouse fixtures for settings, logger, engine, session
  - In-memory SQLite test database fixture (per 10_8 §4.4: "In-memory SQLite / Testcontainers / Fixed fixtures")
  - Async test support via `pytest-asyncio`
- `backend/tests/fixtures/` — Empty directory with README explaining fixture structure per 10_8 §6.2
- `backend/tests/scenarios/` — Empty directory per 10_8 §6.3
- `backend/tests/golden/` — Empty directory per 10_8 §6.4
- `backend/pyproject.toml` — pytest configuration:
  - `asyncio_mode = "auto"`
  - Coverage thresholds
  - Test discovery patterns
  - Marker definitions (unit, integration, evaluation, slow)

**Testing principles from 10_8 applied**:
- Deterministic-by-default (D1.7 itself is deterministic)
- Mock at boundaries (database fixture uses real in-memory SQLite)
- Test structure mirrors architecture layers (unit/, integration/, evaluation/ directories)

**Verification**: `pytest --collect-only` runs. Base fixtures instantiate. In-memory SQLite creates and drops cleanly.

---

### D1.8 Docker and docker-compose

**Purpose**: Enable local development environment reproduction.

**Dependencies**: D1.2 (dependencies defined), D1.5 (database infrastructure).

**Expected outputs**:

- `backend/Dockerfile` — Multi-stage build:
  - Stage 1: Build (uv sync, dependency install)
  - Stage 2: Runtime (minimal base image, copy built dependencies)
  - Non-root user for security
- `docker-compose.yml` (root) — Local dev services:
  - `memory-hub-db`: PostgreSQL 15+ with pgvector extension
  - `memory-hub-app`: Application container
  - Named volume for database persistence
  - Health checks for database readiness
  - Environment variables from `.env.example`

**Verification**: `docker compose up -d` starts PostgreSQL with pgvector. `docker compose exec memory-hub-app python -c "..."` runs Python. Database is reachable from app container.

---

### D1.9 CI Pipeline Scaffolding

**Purpose**: Establish the CI pipeline per 11 §8 (CI Strategy).

**Dependencies**: D1.2 (tool configs), D1.7 (testing framework).

**Expected outputs**:

- `.github/workflows/ci.yml` — GitHub Actions workflow:
  - Stage 1: Static Analysis (ruff lint, mypy type-check)
  - Stage 2: Unit Tests (pytest with in-memory SQLite)
  - Trigger: push to `main`, pull_request to `main`
  - Python version matrix: 3.11, 3.12
  - Cache: uv dependency cache
  - Coverage report upload (optional, non-blocking)

**Deferred per 11 §8**:
- Integration tests (Stage 3) — requires database, deferred to D2+
- Architecture tests (Stage 4) — requires domain models, deferred to D2+
- Behavioral tests (Stage 5) — requires golden datasets, deferred to D2+
- Build verification (Stage 6) — deferred until domain models exist
- CD pipeline — intentionally deferred per 11 §8

**Verification**: CI workflow file is syntactically valid. Local `make ci` (or equivalent) reproduces the workflow stages.

---

### D1.10 Documentation Scaffolding

**Purpose**: Create documentation that reflects D1 completion.

**Dependencies**: None (parallel with other tasks).

**Expected outputs**:

- `docs/05_Implementation/README.md` — Implementation phase overview:
  - D1: Infrastructure Foundation (this document)
  - D2: Repository Layer (planned)
  - D3-D6: Subsequent milestones (referenced from 11)
  - Coding order per 11 §4
  - Review workflow per 11 §7
- `backend/README.md` — Developer setup guide:
  - Prerequisites (Python 3.11+, uv, Docker)
  - Local setup steps
  - Running tests
  - Running Alembic migrations
  - Docker quickstart
- `README.md` (root) — Updated with:
  - Phase D status (D1 in progress)
  - Development setup reference
  - Architecture documents link
- `.gitignore` — Updated with Python/uv/Docker ignore patterns

**Verification**: Setup guide steps are executable. README reflects current project status.

---

## 4. Definition of Done

D1 is complete when **all** of the following criteria are met:

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 1 | Project builds successfully | `uv build` or `python -m build` succeeds |
| 2 | Dependencies resolve | `uv sync` completes without errors |
| 3 | Linting passes | `ruff check backend/` returns zero violations |
| 4 | Type checking passes | `mypy backend/src/` passes in strict mode |
| 5 | Local startup succeeds | `python -m backend` or equivalent entry point runs without error |
| 6 | Docker startup succeeds | `docker compose up -d` starts all services |
| 7 | Database connection verified | Engine connects to PostgreSQL (via Docker) and to in-memory SQLite (for tests) |
| 8 | Migration executable | `alembic current` and `alembic history` run without error |
| 9 | Tests executable | `pytest tests/ --collect-only` discovers tests; base fixture tests pass |
| 10 | CI passes | `.github/workflows/ci.yml` validates; local reproduction of lint + test stages works |
| 11 | No business logic present | Code audit confirms zero Service, Engine, or Repository implementations |
| 12 | Documentation updated | README, setup guide, and docs/05_Implementation/README.md reflect D1 status |

---

## 5. Risks

### 5.1 Over-Engineering Infrastructure

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Creating overly complex DI, config, or logging infrastructure before domain needs are known | Keep infrastructure minimal and pragmatic. Each infrastructure component should have a clear, documented purpose aligned with approved architecture. |
| Impact | Medium | **Severity: Medium** |
| Trigger | Infrastructure code exceeds 500 lines without domain model usage | Review against ENG-001 (Memory Hub = Infrastructure, Not Business Logic) |

### 5.2 Framework Selection Paralysis

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Spending excessive time evaluating DI frameworks, logging libraries, or build tools | Use the approved technology stack from 09 §9.2 (PostgreSQL, Supabase). For tooling, prefer widely-adopted standards (SQLAlchemy, Alembic, pytest, ruff, mypy). |
| Impact | Medium | **Severity: Low** |
| Trigger | More than 2 hours spent on framework comparison | Default to industry standard; document decision as ADR if non-obvious. |

### 5.3 Database Connection Issues

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | PostgreSQL/pgvector connection configuration fails in local or CI environment | Use Docker for local PostgreSQL. Use in-memory SQLite for unit tests. Separate test and production database URLs in configuration. |
| Impact | High | **Severity: Medium** |
| Trigger | Engine connection test fails | Ensure `docker compose up -d` is run before database tests. Provide clear error messages. |

### 5.4 Alembic Configuration Complexity

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Alembic env.py configuration becomes complex when domain models are introduced later | Keep D1 Alembic setup minimal. The env.py should import from a known location (`shared.infrastructure.database.base`). Document the migration workflow for future implementers. |
| Impact | Medium | **Severity: Low** |
| Trigger | Alembic migration generation fails due to import issues | Ensure declarative base is importable before any model exists. |

### 5.5 CI/CD Alignment

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | CI pipeline stages diverge from the six-stage pipeline defined in 11 §8 | D1 implements Stages 1-2 only (Static Analysis + Unit Tests). Document remaining stages as planned but not yet implemented. |
| Impact | Low | **Severity: Low** |
| Trigger | CI workflow file omits documented stages | Add comments in CI workflow referencing 11 §8 for planned stages. |

### 5.6 Document-Driven Drift

| Aspect | Description | Mitigation |
|--------|-------------|------------|
| Risk | Infrastructure implementation diverges from architecture documents | Each infrastructure component traces back to a specific document section. Maintain cross-references in code comments. |
| Impact | High | **Severity: Medium** |
| Trigger | Infrastructure design contradicts 08, 09, or 10_1 | Review against referenced documents before committing. |

---

## 6. Documentation Updates

The following documentation should be created or updated during D1 implementation:

| # | Document | Action | Reference |
|---|----------|--------|-----------|
| 1 | `README.md` (root) | Update: Add Phase D status, development setup reference, link to docs/INDEX.md | 11 §5.1 |
| 2 | `backend/README.md` | Create: Developer setup guide with prerequisites, local setup, testing, Docker | 11 §9 |
| 3 | `docs/05_Implementation/README.md` | Create: Implementation phase overview, D1-D6 milestone mapping, coding order | 11 §4 |
| 4 | `docs/INDEX.md` | Update: Add `05_Implementation/` section, mark D1 as in-progress | INDEX.md §Current Progress |
| 5 | `.github/PULL_REQUEST_TEMPLATE.md` | Create: PR template referencing four-level review workflow (11 §7) | 11 §7 |
| 6 | `docs/07_Review/12_Architecture_Decisions.md` | Update: Add ADR for D1 infrastructure decisions (framework selections, tool choices) | 11 §10 |
| 7 | `backend/.env.example` | Create: Documented environment variable template with descriptions | 09 §9.2 |
| 8 | `docs/05_Implementation/D1_Infrastructure_Foundation_Log.md` | Create (optional): Implementation log recording decisions, issues, and resolutions | 13 §5 |

**Principle**: Documentation updates are part of D1 deliverables, not afterthoughts. Each document change should be traceable to a specific engineering decision or architectural requirement.

---

## 7. Handoff to D2 (Repository Layer)

Once D1 is complete, D2 (Repository Layer) can safely assume:

### 7.1 Infrastructure Readiness

| Item | D1 Provides | D2 Assumes |
|------|-------------|------------|
| **Project structure** | Complete `backend/` layout with empty `repository/` and `engine/` directories | Directory structure is stable and will not change |
| **Build system** | `pyproject.toml` with all dependencies, `uv` working | Dependency list is finalized for repository layer |
| **Configuration** | Settings model with `DATABASE_URL`, `LOG_LEVEL`, etc. | Configuration values are available via settings singleton |
| **Logging** | Structured logger factory | Logger is injectable and produces JSON output |
| **DI Container** | Container with settings, logger, engine, session factory resolved | Container is the mechanism for resolving repository instances |

### 7.2 Database Readiness

| Item | D1 Provides | D2 Assumes |
|------|-------------|------------|
| **SQLAlchemy** | Engine factory, session factory, declarative base | `Base` class is the import target for all model definitions |
| **Alembic** | Configured migration framework with `env.py` | Migration files go in `alembic/versions/`; `env.py` imports from `shared.infrastructure.database.base` |
| **Connection** | PostgreSQL connection string from settings | D2 uses the same connection for production; in-memory SQLite for tests |
| **Schema namespace** | Documented in 09 §9.3: `memory_hub` schema | All D2 models use `memory_hub` schema |

### 7.3 Testing Readiness

| Item | D1 Provides | D2 Assumes |
|------|-------------|------------|
| **pytest** | Configuration, base conftest, in-memory SQLite fixture | D2 extends fixtures for repository-specific test data |
| **Test directories** | `tests/unit/`, `tests/integration/`, `tests/fixtures/`, `tests/golden/` | D2 places repository tests in appropriate directories |
| **Mock strategy** | Base principles from 10_8 §4 | D2 mocks at layer boundaries (Database, LLM API); uses real in-memory SQLite |
| **Deterministic tests** | CI stage 2 configured for deterministic tests | D2 tests are deterministic (same input → same output) |

### 7.4 Architecture Boundaries

| Item | D1 Provides | D2 Assumes |
|------|-------------|------------|
| **Layer boundaries** | `shared/protocols/` for abstract repository interfaces | D2 implements interfaces from `shared/protocols/` |
| **No cross-layer violation** | Engine and Service directories are empty | D2 does not implement Engine or Service code |
| **Guideline compliance** | G-013 (Repository Is Persistence Only) documented | D2 repositories contain only CRUD + Query logic |
| **Naming conventions** | 09 §9.3 documented | D2 follows snake_case, plural table names, `memory_hub` schema |

### 7.5 What D2 Must NOT Assume

| Item | Reason |
|------|--------|
| Domain models exist | Entity, MemoryNode, Evidence models are D2 responsibility |
| Migration files exist | D2 creates first migration with actual schema from 09 |
| Service layer code exists | Service implementations are separate milestones (11 §3) |
| Engine layer code exists | Engine implementations are separate milestones (11 §3) |
| API endpoints exist | Entry layer is a later milestone (11 §3) |

---

## 8. Engineering Principles Applied

During D1 implementation, the following principles govern all decisions:

| Principle | Source | Application in D1 |
|-----------|--------|-------------------|
| **Memory Hub = Infrastructure** | ENG-001 | No business logic; pure scaffolding |
| **Document-Driven Design** | 11 §13.1 | Each component traces to a document section |
| **No Layer Skipping** | G-014 | Infrastructure does not implement domain logic |
| **Repository Is Persistence Only** | G-013 | D2 will enforce; D1 provides the foundation |
| **Deterministic-by-Default** | 10_8 §5.1 | All D1 tests are deterministic |
| **CI Over CD** | 11 §8 | CD pipeline intentionally deferred |
| **Continuous Buildability** | 11 §Engineering Principles | Main branch is buildable after every D1 task |
| **Human Decides, AI Executes** | 11 §13.2 | This plan requires human approval before coding |

---

## 9. Task Dependencies

```
D1.1 Project Structure
    ↓
D1.2 pyproject.toml ←──┐
    ↓                    │
D1.3 Configuration      │
    ↓                    │
D1.4 Logging ───────────┼──→ D1.6 DI Framework
    ↓                    │
D1.5 Database Infra ─────┘
    ↓
D1.7 Testing Framework
    ↓
D1.8 Docker + docker-compose  (parallel with D1.7)
    ↓
D1.9 CI Pipeline  (parallel with D1.8)
    ↓
D1.10 Documentation  (parallel throughout)
```

**Parallel execution opportunities**:
- D1.4 (Logging) can proceed in parallel with D1.3 (Configuration) — logging reads log level from settings
- D1.8 (Docker) can proceed in parallel with D1.7 (Testing)
- D1.9 (CI) can proceed in parallel with D1.8 (Docker)
- D1.10 (Documentation) proceeds in parallel throughout

---

## 10. Next Steps

1. **Human review** of this planning document
2. **Approval** to proceed with D1 implementation
3. **Implementation** of D1 tasks in dependency order
4. **Verification** against Definition of Done (Section 4)
5. **Handoff** to D2 (Repository Layer) upon completion

---

> **This is a planning document only.** No production code, configuration files, or placeholder implementations are created by this task.
>
> **Git rules**: No commits. No pushes. Awaiting human review and approval before any coding work begins.
