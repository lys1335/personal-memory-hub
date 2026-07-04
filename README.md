# Personal Memory Hub

> **A document-driven long-term memory system for personal AI assistants.**
>
> **Phase D, Milestone D1: Infrastructure Foundation** — ✅ Complete

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) — Fast Python package installer and resolver
- [Docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/) — Optional, for local development

### Local Development

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Install dependencies
uv sync --all-extras

# 3. Run tests
uv run pytest tests/ -v

# 4. Run linting
uv run ruff check src/ tests/

# 5. Run type checking
uv run mypy src/
```

### Docker Development

```bash
# 1. Start the database
docker compose up -d db

# 2. Start the application
docker compose up -d app

# 3. Run tests inside the container
docker compose exec app uv run pytest tests/ -v

# 4. Stop all services
docker compose down
```

### Environment Variables

Copy `.env.example` to `.env` and adjust values:

```bash
cp backend/.env.example backend/.env
```

See `backend/.env.example` for all configurable options.

---

## Project Structure

```
personal-memory-hub/
├── docs/                    # Architecture & design documents
│   ├── INDEX.md             # Document index
│   ├── 01_Vision/           # Vision & goals
│   ├── 02_Data_Model/       # Data model design
│   ├── 03_Component_Model/  # Component architecture
│   ├── 04_Retrieval_Ranking/ # Implementation design (Phase B)
│   ├── 05_Implementation/   # Implementation plans (Phase D)
│   └── 07_Review/           # Review documents
├── backend/                 # Application code
│   ├── src/backend/         # Source code (5-layer architecture)
│   ├── tests/               # Test suite
│   ├── alembic/             # Database migrations
│   ├── pyproject.toml       # Project configuration
│   ├── Dockerfile           # Container build
│   └── .env.example         # Environment template
├── docker-compose.yml       # Local dev environment
├── .github/workflows/ci.yml # CI pipeline
└── .gitignore               # Git ignore rules
```

---

## Architecture

The Personal Memory Hub follows a strict five-layer architecture:

```
Entry (REST/MCP/CLI)
    ↓
Service Layer (MemoryService, QueryService, etc.)
    ↓
Engine Layer (MemoryEngine, IngestionEngine, etc.)
    ↓
Repository Layer (EntityRepository, MemoryNodeRepository, etc.)
    ↓
Database (PostgreSQL + pgvector)
```

**Principle**: Documents define architecture. Code implements documents.

See `docs/INDEX.md` for the full architecture documentation.

---

## Implementation Milestones

| Milestone | Status | Description |
|-----------|--------|-------------|
| **D1: Infrastructure Foundation** | ✅ Complete | Project setup, database, logging, DI, testing, CI |
| **D2: Repository Layer** | ⏳ Planned | Database models, repositories, migrations |
| **D3: Domain Engine** | ⏳ Planned | Stateless domain engines |
| **D4: Service Layer** | ⏳ Planned | Application services |
| **D5: Entry & API** | ⏳ Planned | REST, MCP, CLI adapters |
| **D6: Testing & Stabilization** | ⏳ Planned | Integration, evaluation, regression |

---

## Development

### Coding Standards

- **Linting**: [ruff](https://github.com/astral-sh/ruff) — `ruff check src/ tests/`
- **Type Checking**: [mypy](https://mypy.readthedocs.io/) in strict mode — `mypy src/`
- **Formatting**: ruff format — `ruff format src/ tests/`
- **Testing**: [pytest](https://docs.pytest.org/) — `pytest tests/ -v`

### Review Workflow

All implementation follows the four-level review workflow:

1. **Self Review** — Code style, unit tests, documentation, architecture alignment
2. **Architecture Review** — Layer boundaries, dependency rules, capability alignment
3. **Testing Review** — Test quality, coverage, golden datasets, regression suite
4. **Human Approval** — Design rationale, risk assessment, final sign-off

See `docs/04_Retrieval_Ranking/11_Implementation_Roadmap.md` §7 for details.

---

## License

Proprietary — All rights reserved.
