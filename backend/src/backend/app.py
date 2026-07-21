"""Personal Memory Hub - FastAPI Application

This module provides the main FastAPI application for the Personal Memory Hub.
Per D5_Entry_Layer_Architecture, this is the primary Entry Adapter for HTTP requests.
"""

import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

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
async def capture_memory(body: dict[str, Any], services: dict = Depends(get_services)):
    """POST /memories - capture a new memory."""
    adapter = RESTAdapter(services)
    try:
        response = await adapter.handle_capture_memory(body)
    except Exception as exc:
        logger.error("capture_memory error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.success:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


@app.post("/memories/search", tags=["memories"])
async def search_memory(body: dict[str, Any], services: dict = Depends(get_services)):
    """POST /memories/search - search memories."""
    adapter = RESTAdapter(services)
    try:
        response = await adapter.handle_search_memory(body)
    except Exception as exc:
        logger.error("search_memory error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.success:
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
    if response.success:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Entity Endpoints
# ------------------------------------------------------------------

@app.post("/entities", tags=["entities"])
async def create_entity(body: dict[str, Any], services: dict = Depends(get_services)):
    """POST /entities - create a new entity."""
    adapter = RESTAdapter(services)
    try:
        response = adapter.handle_create_entity(body)
    except Exception as exc:
        logger.error("create_entity error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.success:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Reflection Endpoints
# ------------------------------------------------------------------

@app.post("/reflection", tags=["reflection"])
async def trigger_reflection(body: dict[str, Any], services: dict = Depends(get_services)):
    """POST /reflection - trigger reflection."""
    adapter = RESTAdapter(services)
    try:
        response = adapter.handle_trigger_reflection(body)
    except Exception as exc:
        logger.error("trigger_reflection error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.success:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Task Endpoints
# ------------------------------------------------------------------

@app.post("/tasks", tags=["tasks"])
async def submit_task(body: dict[str, Any], services: dict = Depends(get_services)):
    """POST /tasks - submit a new task."""
    adapter = RESTAdapter(services)
    try:
        response = adapter.handle_submit_task(body)
    except Exception as exc:
        logger.error("submit_task error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.success:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


# ------------------------------------------------------------------
# Import Endpoints (Phase F)
# ------------------------------------------------------------------

@app.post("/memories/import", tags=["import"])
async def import_memories(body: dict[str, Any], services: dict = Depends(get_services)):
    """POST /memories/import - import memories from external source."""
    adapter = RESTAdapter(services)
    try:
        response = await adapter.handle_import_memories(body)
    except Exception as exc:
        logger.error("import_memories error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    if response.success:
        return asdict(response)
    raise HTTPException(status_code=422, detail=asdict(response))


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    log_level = settings.LOG_LEVEL.lower()

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        log_level=log_level,
        reload=True,
    )
