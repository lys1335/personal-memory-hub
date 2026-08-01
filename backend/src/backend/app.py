"""Personal Memory Hub - FastAPI Application

This module provides the main FastAPI application for the Personal Memory Hub.
Per D5_Entry_Layer_Architecture, this is the primary Entry Adapter for HTTP requests.
"""

import json
import logging
import os
import sys
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend.entry.dto import ResponseStatus
from backend.entry.rest_adapter import RESTAdapter
from backend.service.entity_service import EntityService
from backend.service.memory_service import MemoryService
from backend.service.query_service import QueryService
from backend.service.reflection_service import ReflectionService
from backend.service.task_service import TaskService
from backend.shared.infrastructure.config.settings import get_settings
from backend.shared.infrastructure.database.engine import get_engine, get_session_factory

logger = logging.getLogger(__name__)


async def get_session() -> AsyncSession:
    """Dependency to provide an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


def get_repositories(session: AsyncSession = Depends(get_session)):
    """Factory to create all repository instances for a request."""
    from backend.repository.archive_repository import ArchiveRepository
    from backend.repository.candidate_repository import CandidateRepository
    from backend.repository.entity_query_repository import EntityQueryRepository
    from backend.repository.entity_repository import EntityRepository
    from backend.repository.evidence_repository import EvidenceRepository
    from backend.repository.memory_node_repository import MemoryNodeRepository
    from backend.repository.memory_query_repository import MemoryQueryRepository
    from backend.repository.relationship_repository import RelationshipRepository
    from backend.repository.tag_repository import TagRepository
    from backend.repository.task_repository import TaskRepository
    from backend.repository.vector_doc_repository import VectorDocRepository
    from backend.repository.vector_query_repository import VectorQueryRepository

    return {
        "memory_node": MemoryNodeRepository(session),
        "evidence": EvidenceRepository(session),
        "relationship": RelationshipRepository(session),
        "archive": ArchiveRepository(session),
        "tag": TagRepository(session),
        "task": TaskRepository(session),
        "memory_query": MemoryQueryRepository(session),
        "entity": EntityRepository(session),
        "entity_query": EntityQueryRepository(session),
        "vector_query": VectorQueryRepository(session),
        "vector_doc": VectorDocRepository(session),
        "candidate": CandidateRepository(session),
    }


def get_services(
    session: AsyncSession = Depends(get_session),
    repos: dict = Depends(get_repositories),
):
    # Initialize embedding service using configured Ollama URL
    from backend.service.embedding_service import EmbeddingService
    from backend.shared.infrastructure.config.settings import get_settings
    _settings = get_settings()
    embedding_service = EmbeddingService(
        ollama_base_url=_settings.OLLAMA_BASE_URL,
        model=_settings.EMBEDDING_MODEL,
    )

    memory_service = MemoryService(
        memory_node_repo=repos["memory_node"],
        evidence_repo=repos["evidence"],
        relationship_repo=repos["relationship"],
        archive_repo=repos["archive"],
        tag_repo=repos["tag"],
        task_repo=repos["task"],
        memory_query_repo=repos["memory_query"],
        vector_doc_repo=repos["vector_doc"],
        embedding_service=embedding_service,
    )
    query_service = QueryService(
        memory_node_repo=repos["memory_node"],
        memory_query_repo=repos["memory_query"],
        entity_repo=repos["entity"],
        entity_query_repo=repos["entity_query"],
        vector_query_repo=repos["vector_query"],
        vector_doc_repo=repos["vector_doc"],
    )
    entity_service = EntityService(
        entity_repo=repos["entity"],
        relationship_repo=repos["relationship"],
    )
    reflection_service = ReflectionService(
        memory_node_repo=repos["memory_node"],
        candidate_repo=repos["candidate"],
        relationship_repo=repos["relationship"],
    )
    task_svc = TaskService(repos["task"])

    return {
        "memory": memory_service,
        "query": query_service,
        "entity": entity_service,
        "reflection": reflection_service,
        "task": task_svc,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Configure file logging - write to shared volume for dashboard to read
    log_dir = os.environ.get('LOG_DIR', '/app/logs')
    log_file = os.path.join(log_dir, 'memory_hub.log')
    os.makedirs(log_dir, exist_ok=True)

    # Simple file handler with immediate flush
    fh = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    root_logger = logging.getLogger()
    root_logger.addHandler(fh)
    root_logger.setLevel(logging.DEBUG)
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.NAME} v0.1.0")
    logger.info(f"Database URL: {settings.DATABASE_URL[:50]}...")

    engine = get_engine()
    logger.info("Database engine initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Personal Memory Hub")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="Personal Memory Hub",
    description="A document-driven long-term memory system for personal AI assistants",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Health Endpoints
# ------------------------------------------------------------------

@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """Root endpoint - health check."""
    return {"status": "ok", "message": "Personal Memory Hub is running"}


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "personal-memory-hub",
        "version": "0.1.0",
    }


# ------------------------------------------------------------------
# Memory Endpoints (via RESTAdapter)
# ------------------------------------------------------------------

@app.post("/memories", tags=["memories"])
async def capture_memory(body: dict = Body(...), services: dict = Depends(get_services)):
    """POST /memories - capture a new memory."""
    logger.info("=== capture_memory ENTER ===")
    logger.info("body type: %s, keys: %s", type(body), list(body.keys()) if isinstance(body, dict) else 'N/A')
    logger.info("services type: %s", type(services))
    try:
        adapter = RESTAdapter(services)
        logger.info("adapter created")
        response = await adapter.handle_capture_memory(body)
        logger.info("response status: %s, data: %s", response.status, str(response.data)[:200])
        logger.info("response error: %s", str(response.error)[:200] if response.error else None)
    except Exception as exc:
        logger.error("=== capture_memory EXCEPTION === %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.status == ResponseStatus.SUCCESS:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


@app.post("/memories/search", tags=["memories"])
async def search_memory(body: dict = Body(..., embed=False), services: dict = Depends(get_services)):
    """POST /memories/search - search memories."""
    adapter = RESTAdapter(services)
    try:
        response = await adapter.handle_search_memory(body)
    except Exception as exc:
        logger.error("search_memory error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.status == ResponseStatus.SUCCESS:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


@app.get("/memories/{memory_id}", tags=["memories"])
async def retrieve_memory(memory_id: str, services: dict = Depends(get_services)):
    """GET /memories/{id} - retrieve a memory by ID."""
    adapter = RESTAdapter(services)
    try:
        response = adapter.handle_retrieve_memory({"memory_id": memory_id})
    except Exception as exc:
        logger.error("retrieve_memory error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.status == ResponseStatus.SUCCESS:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Entity Endpoints
# ------------------------------------------------------------------


@app.get("/memories", tags=["memories"])
async def list_memories(
    repos: dict = Depends(get_repositories),
    workspace_id: str = Query(None, description="Workspace UUID"),
    limit: int | None = Query(None, description="Max number of memories to return")
):
    """GET /memories - list memories with total count."""
    from uuid import UUID

    default_ws_id = "fb77c6ce-1e15-47e9-a8b7-2e707a011071"
    target_wid = UUID(workspace_id) if workspace_id else UUID(default_ws_id)

    memory_node_repo = repos["memory_node"]
    
    # Use provided limit or large default to fetch all memories
    repo_limit = limit if limit is not None else 999999
    all_memories = await memory_node_repo.find_active_by_workspace(
        workspace_id=target_wid, 
        limit=repo_limit
    )

    total_count = len(all_memories)

    # Return all memories (with content truncation for long entries)
    data = []
    for m in all_memories:
        item = {
            "id": str(m.id),
            "level": m.level,
            "source": m.source,
            "content": (m.content[:100] + "...") if m.content and len(m.content) > 100 else m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        data.append(item)

    return {"data": data, "total": total_count}


@app.post("/entities", tags=["entities"])
async def create_entity(body: dict = Body(...), services: dict = Depends(get_services)):
    """POST /entities - create a new entity."""
    adapter = RESTAdapter(services)
    try:
        response = adapter.handle_create_entity(body)
    except Exception as exc:
        logger.error("create_entity error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.status == ResponseStatus.SUCCESS:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Reflection Endpoints
# ------------------------------------------------------------------

@app.post("/reflection", tags=["reflection"])
async def trigger_reflection(body: dict = Body(...), services: dict = Depends(get_services)):
    """POST /reflection - trigger reflection."""
    adapter = RESTAdapter(services)
    try:
        response = adapter.handle_trigger_reflection(body)
    except Exception as exc:
        logger.error("trigger_reflection error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.status == ResponseStatus.SUCCESS:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Task Endpoints
# ------------------------------------------------------------------

@app.post("/tasks", tags=["tasks"])
async def submit_task(body: dict = Body(...), services: dict = Depends(get_services)):
    """POST /tasks - submit a new task."""
    adapter = RESTAdapter(services)
    try:
        response = adapter.handle_submit_task(body)
    except Exception as exc:
        logger.error("submit_task error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.status == ResponseStatus.SUCCESS:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Import Endpoints (Phase F)
# ------------------------------------------------------------------

@app.post("/memories/import", tags=["import"])
async def import_memories(body: dict = Body(...), services: dict = Depends(get_services)):
    """POST /memories/import - import memories from external source."""
    adapter = RESTAdapter(services)
    try:
        response = await adapter.handle_import_memories(body)
    except Exception as exc:
        logger.error("import_memories error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.status == ResponseStatus.SUCCESS:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# SQL Query Endpoints (Dashboard Data Browser)
# ------------------------------------------------------------------

@app.get("/api/sql/tables", tags=["sql"])
async def list_tables():
    """GET /api/sql/tables - List all tables with column info."""
    from sqlalchemy import text

    from backend.shared.infrastructure.database.engine import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        # Get table names
        rows = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = []
        for r in rows:
            tname = r[0]
            cols = await conn.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = :tname ORDER BY ordinal_position"),
                {"tname": tname}
            )
            tables.append({
                "name": tname,
                "columns": [{"name": c[0], "type": c[1]} for c in cols],
            })
        return {"tables": tables}


@app.post("/api/sql/query", tags=["sql"])
async def execute_sql_query(body: dict = Body(..., embed=False)):
    """POST /api/sql/query - Execute a read-only SQL query and return results."""
    sql = body.get("sql", "").strip()
    limit = min(int(body.get("limit", 100)), 500)  # Max 500 rows

    if not sql:
        raise HTTPException(status_code=400, detail="SQL query is empty")

    # Security: only allow SELECT statements
    first_word = sql.split()[0].upper() if sql else ""
    if first_word != "SELECT":
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed")

    # Block dangerous keywords - use word boundary matching to avoid false positives like 'created_at'
    import re
    sql_upper = sql.upper()
    dangerous_patterns = [
        r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b',
        r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bGRANT\b',
        r'\bREVOKE\b', r'\bEXEC\b', r'\bEXECUTE\b', r'\bMERGE\b',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, sql_upper):
            raise HTTPException(status_code=403, detail="Query contains disallowed operation")

    import json
    import uuid

    from sqlalchemy import text

    from backend.shared.infrastructure.database.engine import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        # Add LIMIT if not present
        final_sql = sql.rstrip(";").strip()
        if "LIMIT" not in final_sql.upper():
            final_sql += f" LIMIT {limit}"

        try:
            result = await conn.execute(text(final_sql))
            rows_list = result.fetchall()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Query error: {e!s}")

        columns = list(result.keys())

        if not rows_list:
            return {"columns": columns, "rows": [], "row_count": 0, "sql": final_sql}

        # Convert rows to serializable dicts using _mapping for named access
        result_rows = []
        for row in rows_list:
            mapping = row._mapping
            row_dict = {}
            for col in columns:
                val = mapping[col]
                if isinstance(val, uuid.UUID):
                    row_dict[col] = str(val)
                elif isinstance(val, bytes):
                    row_dict[col] = val.decode('utf-8', errors='replace')
                elif isinstance(val, (dict, list)):
                    row_dict[col] = json.dumps(val, ensure_ascii=False)
                else:
                    row_dict[col] = val
            result_rows.append(row_dict)

        return {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows),
            "sql": final_sql,
        }


# ------------------------------------------------------------------
# Cron Control Panel Endpoints (Dashboard Scheduled Tasks)
# ------------------------------------------------------------------

_cron_lock = threading.Lock()
_cron_tasks: dict = {}  # task_id -> task config
_CRON_DATA_FILE = os.environ.get('LOG_DIR', '/app/logs') + '/cron_tasks.json'

def _load_cron_tasks():
    """Load cron tasks from disk."""
    global _cron_tasks
    try:
        if os.path.exists(_CRON_DATA_FILE):
            with open(_CRON_DATA_FILE, encoding='utf-8') as f:
                _cron_tasks = json.load(f)
    except Exception:
        _cron_tasks = {}

def _save_cron_tasks():
    """Persist cron tasks to disk."""
    try:
        os.makedirs(os.path.dirname(_CRON_DATA_FILE), exist_ok=True)
        with open(_CRON_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(_cron_tasks, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# Load on startup
_load_cron_tasks()


# Default evolution task configuration
_DEFAULT_EVOLUTION_TASK = {
    "name": "记忆演化",
    "type": "evolution",
    "interval_seconds": int(os.environ.get("CRON_EVOLUTION_INTERVAL", "3600")),
    "enabled": True,
    "payload": {
        "workspace_id": "fd0223ed-7aa2-491e-8db5-b0de71b75219",
        "limit": int(os.environ.get("CRON_EVOLUTION_LIMIT", "50"))
    }
}


def _initialize_default_tasks():
    """Initialize default cron tasks if not exist."""
    global _cron_tasks
    import uuid as _uuid
    from datetime import datetime, timezone
    
    # Check if evolution task exists
    has_evolution = any(
        t.get('type') == 'evolution' for t in _cron_tasks.values()
    )
    
    if not has_evolution:
        # Create default evolution task
        task_id = str(_uuid.uuid4())[:8]
        _cron_tasks[task_id] = {
            "id": task_id,
            "name": _DEFAULT_EVOLUTION_TASK["name"],
            "type": _DEFAULT_EVOLUTION_TASK["type"],
            "interval_seconds": _DEFAULT_EVOLUTION_TASK["interval_seconds"],
            "enabled": _DEFAULT_EVOLUTION_TASK["enabled"],
            "payload": _DEFAULT_EVOLUTION_TASK["payload"],
            "last_run": None,
            "status": "idle",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        _save_cron_tasks()
        logger.info(f"[CRON] Initialized default evolution task: {task_id}")


_initialize_default_tasks()


# ================================================================
# Background Cron Scheduler
# ================================================================

async def _cron_scheduler_loop():
    """Background task that checks cron tasks and triggers expired ones."""
    import asyncio
    from datetime import datetime, timezone
    
    logger.info("[CRON] Background scheduler started")
    
    while True:
        try:
            await asyncio.sleep(30)
            
            now = datetime.now(timezone.utc)
            
            with _cron_lock:
                tasks_to_run = []
                for task_id, task in list(_cron_tasks.items()):
                    if not task.get('enabled', False):
                        continue
                    interval = task.get('interval_seconds', 300)
                    last_run = task.get('last_run')
                    if last_run:
                        try:
                            last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                            elapsed = (now - last_run_dt).total_seconds()
                            if elapsed >= interval:
                                tasks_to_run.append(task_id)
                        except (ValueError, AttributeError):
                            tasks_to_run.append(task_id)
                    else:
                        tasks_to_run.append(task_id)
            
            for task_id in tasks_to_run:
                try:
                    logger.info(f"[CRON] Triggering task {task_id}")
                    await run_cron_task_now(task_id)
                except Exception as e:
                    logger.error(f"[CRON] Error running task {task_id}: {e}", exc_info=True)
                    
        except asyncio.CancelledError:
            logger.info("[CRON] Scheduler loop cancelled")
            break
        except Exception as e:
            logger.error(f"[CRON] Scheduler error: {e}", exc_info=True)
            await asyncio.sleep(60)


_cron_scheduler_task = None


# Default workspace ID (user workspace)
DEFAULT_WORKSPACE = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

_services: dict = {}
_services_ready: bool = False
_services_init_event: any = None  # Will be set during startup

@app.on_event("startup")
async def startup_cron_scheduler():
    global _cron_scheduler_task
    # Start the cron scheduler
    if _cron_scheduler_task is None or _cron_scheduler_task.done():
        _cron_scheduler_task = asyncio.create_task(_cron_scheduler_loop())
        logger.info("[CRON] Scheduler task created")

@app.on_event("shutdown")
async def shutdown_cron_scheduler():
    global _cron_scheduler_task
    if _cron_scheduler_task:
        _cron_scheduler_task.cancel()
        try:
            await _cron_scheduler_task
        except asyncio.CancelledError:
            pass
        logger.info("[CRON] Scheduler task cancelled")


@app.get("/api/cron/tasks")
async def list_cron_tasks():
    """List all configured cron/scheduled tasks."""
    with _cron_lock:
        return {"tasks": list(_cron_tasks.values())}

@app.post("/api/cron/tasks")
async def create_cron_task(body: dict = Body(embed=False)):
    """Create a new scheduled task.

    Body fields:
      - name: str (required) - Task name
      - type: str - 'evolution' | 'batch_import' | 'custom'
      - interval_seconds: int - Polling interval in seconds
      - enabled: bool - Start enabled
      - schedule_expr: str - Optional cron expression (e.g. '0 */6 * * *')
      - payload: dict - Task-specific parameters
    """
    import uuid as _uuid

    name = body.get('name', '')
    if not name:
        raise HTTPException(status_code=400, detail="Task name is required")

    task_type = body.get('type', 'evolution')
    interval = body.get('interval_seconds', 300)
    schedule_expr = body.get('schedule_expr', '')
    enabled = body.get('enabled', True)
    payload = body.get('payload', {})

    task_id = str(_uuid.uuid4())[:8]

    task = {
        "id": task_id,
        "name": name,
        "type": task_type,
        "interval_seconds": max(10, int(interval)),  # Min 10s
        "schedule_expr": schedule_expr,
        "enabled": enabled,
        "payload": payload,
        "last_run": None,
        "next_run": None,
        "status": "idle",
        "created_at": __import__('datetime').datetime.utcnow().isoformat(),
    }

    with _cron_lock:
        _cron_tasks[task_id] = task
        _save_cron_tasks()

    return {"task_id": task_id, **task}

@app.put("/api/cron/tasks/{task_id}")
async def update_cron_task(task_id: str, body: dict = Body(embed=False)):
    """Update an existing task's configuration."""
    with _cron_lock:
        if task_id not in _cron_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        task = _cron_tasks[task_id]
        for key in ['name', 'type', 'interval_seconds', 'schedule_expr', 'enabled', 'payload']:
            if key in body:
                task[key] = body[key]

        _save_cron_tasks()
        return {"task_id": task_id, **task}

@app.delete("/api/cron/tasks/{task_id}")
async def delete_cron_task(task_id: str):
    """Delete a scheduled task."""
    with _cron_lock:
        if task_id not in _cron_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        del _cron_tasks[task_id]
        _save_cron_tasks()
        return {"deleted": task_id}

@app.post("/api/cron/tasks/{task_id}/start")
async def start_cron_task(task_id: str):
    """Start (enable) a task."""
    with _cron_lock:
        if task_id not in _cron_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        _cron_tasks[task_id]['enabled'] = True
        _cron_tasks[task_id]['status'] = 'running'
        _save_cron_tasks()
        return {"task_id": task_id, "status": "started"}

@app.post("/api/cron/tasks/{task_id}/stop")
async def stop_cron_task(task_id: str):
    """Stop (disable) a task."""
    with _cron_lock:
        if task_id not in _cron_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        _cron_tasks[task_id]['enabled'] = False
        _cron_tasks[task_id]['status'] = 'stopped'
        _save_cron_tasks()
        return {"task_id": task_id, "status": "stopped"}

@app.post("/api/cron/tasks/{task_id}/run-now")
async def run_cron_task_now(
    task_id: str,
    services: dict = Depends(get_services),
):
    """Manually trigger a task execution via Service layer."""
    task = _cron_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task_type = task.get('type', 'evolution')
    payload = task.get('payload', {})
    result = {"task_id": task_id, "type": task_type, "status": "completed"}

    if task_type == 'evolution':
        limit = payload.get('limit', 50)
        workspace_id = UUID(payload.get('workspace_id', "fb77c6ce-1e15-47e9-a8b7-2e707a011071"))

        try:
            reflection_svc = services["reflection"]
            exec_result = await reflection_svc.reflect(
                workspace_id=workspace_id,
                scope="daily",
                limit=limit,
            )

            result["message"] = f"Reflection completed: {exec_result.reflections_performed} operations"
            result["scope"] = exec_result.scope
            result["new_patterns"] = exec_result.new_patterns
            result["new_beliefs"] = exec_result.new_beliefs
            result["evidence_completeness"] = exec_result.evidence_completeness
            result["duration_ms"] = exec_result.duration_ms
            result["metadata"] = exec_result.metadata

            # Store proposals in sandbox (from metadata if available)
            proposals = exec_result.metadata.get("proposals", [])
            import uuid as _uuid_mod
            with _sandbox_lock:
                for prop in proposals:
                    prop["id"] = str(_uuid_mod.uuid4())[:8]
                    prop["status"] = "pending"
                    prop["task_id"] = task_id
                    prop["created_at"] = __import__('datetime').datetime.utcnow().isoformat()
                    _sandbox_proposals.append(prop)
                result["sandbox_proposal_count"] = len(proposals)
                _save_sandbox()  # Persist after adding

            logger.info(f"[EVOLUTION] ReflectionService completed: {exec_result.reflections_performed} ops, {len(proposals)} proposals")

        except Exception as e:
            logger.error(f"[EVOLUTION] ReflectionService error: {e}", exc_info=True)
            result["error"] = str(e)
            result["status"] = "failed"
    elif task_type == 'batch_import':
        logger.info(f"[CRON] Running batch import task '{task['name']}'")
        result["message"] = "Batch import triggered"
    else:
        result["message"] = f"Custom task '{task_type}' triggered"

    from datetime import datetime, timezone
    result['executed_at'] = datetime.now(timezone.utc).isoformat()

    with _cron_lock:
        _cron_tasks[task_id]['last_run'] = result['executed_at']
        _cron_tasks[task_id]['status'] = result['status']
        _save_cron_tasks()

    return result


# ================================================================
# Sandbox

# ================================================================

# Sandbox storage - persisted to file
_SANDBOX_FILE = os.environ.get('LOG_DIR', '/app/logs') + '/sandbox_proposals.json'
_sandbox_proposals: list[dict[str, Any]] = []
_sandbox_lock = __import__('threading').Lock()


def _load_sandbox():
    """Load sandbox proposals from disk."""
    global _sandbox_proposals
    try:
        if os.path.exists(_SANDBOX_FILE):
            with open(_SANDBOX_FILE, encoding='utf-8') as f:
                _sandbox_proposals = json.load(f)
            logger.info(f"[SANDBOX] Loaded {len(_sandbox_proposals)} proposals from disk")
    except Exception as e:
        logger.warning(f"[SANDBOX] Failed to load sandbox: {e}")
        _sandbox_proposals = []


def _save_sandbox():
    """Persist sandbox proposals to disk."""
    try:
        os.makedirs(os.path.dirname(_SANDBOX_FILE), exist_ok=True)
        with open(_SANDBOX_FILE, 'w', encoding='utf-8') as f:
            json.dump(_sandbox_proposals, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[SANDBOX] Failed to save: {e}")


# Load sandbox on startup
_load_sandbox()


@app.get("/api/review/proposals")
async def list_review_proposals():
    """List all pending evolution proposals from sandbox."""
    with _sandbox_lock:
        pending = [p for p in _sandbox_proposals if p.get("status") == "pending"]
        _save_sandbox()  # Persist after read
        return {"proposals": pending, "total": len(pending)}


@app.post("/api/review/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Approve a proposal — marks it as reviewed and writes to DB."""
    global _sandbox_proposals, _sandbox_lock
    
    # Mark as approved in sandbox
    with _sandbox_lock:
        proposal = None
        for p in _sandbox_proposals:
            if p.get("id") == proposal_id:
                proposal = p
                break
        
        if not proposal:
            raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
        
        # Mark as approved
        proposal["status"] = "approved"
        proposal["approved_at"] = __import__('datetime').datetime.utcnow().isoformat()
        _save_sandbox()
        logger.info(f"[EVOLUTION] Proposal {proposal_id} approved in sandbox")
    
    # Write to DB using FastAPI dependency injection
    try:
        # Use the existing factory functions defined in this file
        # Note: get_repositories and get_services are NOT async
        repos = get_repositories(session)
        services = get_services(session, repos)
        memory_service = services["memory"]
        
        # Extract data from proposal
        entity_name = proposal.get("entity", "unknown")
        summary = proposal.get("summary", f"AI-generated memory for {entity_name}")
        confidence = proposal.get("confidence", 0.5)
        proposal_type = proposal.get("type", "Refine")
        evidence_chain = proposal.get("evidence_chain", [])
        
        # Determine memory level based on proposal type
        level = 1  # Default to Observation
        if proposal_type == "Refine":
            level = 2
        elif proposal_type == "Merge":
            level = 3
        
        # Prepare metadata
        metadata = {
            "source_proposal_id": proposal_id,
            "proposal_type": proposal_type,
            "evidence_chain": evidence_chain,
            "original_summary": summary,
            "generated_by": "ai_reflect"
        }
        
        from uuid import UUID as PyUUID
        
        # Capture memory - entity_id is optional, we can pass None
        result = await memory_service.capture_memory(
            workspace_id=PyUUID(DEFAULT_WORKSPACE),
            entity_id=None,  # Entity not found/created yet
            content=summary,
            level=level,
            node_type="Pattern" if level == 2 else ("Belief" if level == 3 else "Observation"),
            source="ai_reflect",
            confidence=float(confidence),
            importance=float(confidence) * 0.8,
            signal_strength=float(confidence) * 0.6,
            metadata=metadata
        )
        
        # Link evidence from proposal's evidence_chain to the new memory
        # evidence_chain contains source memory IDs - we create derived_from relationships
        memory_id = result.memory_id
        evidence_count = 0
        
        if evidence_chain and len(evidence_chain) > 0:
            try:
                from backend.repository.relationship_repository import RelationshipRepository
                import uuid as uuid_mod
                
                # Create derived_from relationships from new memory to source memories
                for source_memory_id_str in evidence_chain:
                    try:
                        source_uuid = uuid_mod.UUID(source_memory_id_str)
                        # Create relationship: new_memory -> derived_from -> source_memory
                        await memory_service._relationship_repo.create_relationship(
                            source_node_id=memory_id,
                            target_node_id=source_uuid,
                            relationship_type="derived_from",
                            strength=float(confidence),
                            workspace_id=PyUUID(DEFAULT_WORKSPACE),
                        )
                        evidence_count += 1
                    except Exception as e:
                        logger.warning(f"[EVOLUTION] Failed to link source memory {source_memory_id_str}: {e}")
                
                logger.info(f"[EVOLUTION] Linked {evidence_count} source memories to {memory_id}")
            except Exception as e:
                logger.warning(f"[EVOLUTION] Failed to create relationships: {e}")
        
        logger.info(f"[EVOLUTION] Written to DB: memory_id={memory_id}, evidence_count={evidence_count}")
        return {"proposal_id": proposal_id, "status": "approved", "memory_id": str(memory_id), "evidence_count": evidence_count}
    except Exception as e:
        logger.error(f"[EVOLUTION] Failed to write to DB: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"proposal_id": proposal_id, "status": "approved", "db_write_error": str(e)}


@app.post("/api/review/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str):
    """Reject a proposal — marks it as dismissed."""
    with _sandbox_lock:
        for p in _sandbox_proposals:
            if p.get("id") == proposal_id:
                p["status"] = "rejected"
                p["rejected_at"] = __import__('datetime').datetime.utcnow().isoformat()
                logger.info(f"[EVOLUTION] Proposal {proposal_id} rejected")
                _save_sandbox()
                return {"proposal_id": proposal_id, "status": "rejected"}
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")


@app.post("/api/review/proposals/clear")
async def clear_review_proposals():
    """Clear all reviewed (approved/rejected) proposals from sandbox."""
    with _sandbox_lock:
        before = len(_sandbox_proposals)
        _sandbox_proposals.clear()
        _save_sandbox()  # Persist after clearing
        logger.info(f"[EVOLUTION] Cleared {before} sandbox proposals")
        return {"cleared": before}



# ------------------------------------------------------------------
# Log Viewer Endpoint (Dashboard Log Viewer)
# ------------------------------------------------------------------

@app.get("/api/logs", tags=["logs"])
async def get_logs(
    lines: int = Query(-1, description="Number of lines to return (-1 for most recent)"),
    q: str | None = Query(None, description="Keyword filter"),
    level: str | None = Query(None, description="Log level filter (INFO, WARNING, ERROR)")
):
    """GET /api/logs - Read log files for dashboard viewer."""
    import os
    
    # Find log file
    log_file = None
    for d in ["/app/logs", "./logs"]:
        potential = os.path.join(d, "memory_hub.log")
        if os.path.exists(potential):
            log_file = potential
            break
    
    if not log_file or not os.path.exists(log_file):
        return {"logs": [], "total_lines": 0, "filtered_lines": 0}
    
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            file_size = f.tell()
            max_recent = 5000
            n = lines if lines > 0 else max_recent
            bytes_to_read = n * 200
            seek_pos = max(0, file_size - bytes_to_read)
            f.seek(seek_pos)
            content = f.read()
            # Skip incomplete first line if any
            if "\n" in content:
                content = content[content.index("\n") + 1:]
            log_lines = content.splitlines()
            
            total_count = len(log_lines)
            filtered = log_lines
            if q:
                q_lower = q.lower()
                filtered = [l for l in filtered if q_lower in l.lower()]
            if level:
                filtered = [l for l in filtered if level in l]
            
            return {
                "logs": filtered,
                "total_lines": total_count,
                "filtered_lines": len(filtered)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
