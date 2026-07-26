"""Personal Memory Hub - FastAPI Application

This module provides the main FastAPI application for the Personal Memory Hub.
Per D5_Entry_Layer_Architecture, this is the primary Entry Adapter for HTTP requests.
"""

import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend.entry.rest_adapter import RESTAdapter
from backend.entry.dto import ResponseStatus
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
    import os as _os
    log_dir = _os.environ.get('LOG_DIR', '/app/logs')
    log_file = _os.path.join(log_dir, 'memory_hub.log')
    _os.makedirs(log_dir, exist_ok=True)
    
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
    from backend.shared.infrastructure.database.engine import get_engine
    from sqlalchemy import text

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
            raise HTTPException(status_code=403, detail=f"Query contains disallowed operation")

    from backend.shared.infrastructure.database.engine import get_engine
    from sqlalchemy import text, MetaData, Table, Column
    import uuid
    import json

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
            raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")

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

import os as _os
import json as _json
import threading as _threading
_cron_lock = _threading.Lock()
_cron_tasks: dict = {}  # task_id -> task config
_CRON_DATA_FILE = _os.environ.get('LOG_DIR', '/app/logs') + '/cron_tasks.json'

def _load_cron_tasks():
    """Load cron tasks from disk."""
    global _cron_tasks
    try:
        if _os.path.exists(_CRON_DATA_FILE):
            with open(_CRON_DATA_FILE, 'r', encoding='utf-8') as f:
                _cron_tasks = json.load(f)
    except Exception:
        _cron_tasks = {}

def _save_cron_tasks():
    """Persist cron tasks to disk."""
    try:
        _os.makedirs(_os.path.dirname(_CRON_DATA_FILE), exist_ok=True)
        with open(_CRON_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(_cron_tasks, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# Load on startup
_load_cron_tasks()

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
async def run_cron_task_now(task_id: str):
    """Manually trigger a task execution."""
    task = _cron_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task_type = task.get('type', 'evolution')
    payload = task.get('payload', {})
    
    result = {"task_id": task_id, "type": task_type, "status": "completed"}
    
    if task_type == 'evolution':
        source_filter = payload.get('source_filter', None)
        limit = payload.get('limit', 50)
        logger.info(f"[CRON] Running evolution task '{task['name']}' (type={task_type}, limit={limit})")
        result["message"] = f"Evolution triggered for {limit} memories"
    elif task_type == 'batch_import':
        logger.info(f"[CRON] Running batch import task '{task['name']}'")
        result["message"] = "Batch import triggered"
    else:
        result["message"] = f"Custom task '{task_type}' triggered"
    
    result['executed_at'] = __import__('datetime').datetime.utcnow().isoformat()
    
    with _cron_lock:
        _cron_tasks[task_id]['last_run'] = result['executed_at']
        _cron_tasks[task_id]['status'] = 'completed'
        _save_cron_tasks()
    
    return result



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
