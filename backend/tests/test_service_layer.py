"""Unit tests for Service Layer (D3).

Tests BaseService, MemoryService, QueryService, EntityService,
ReflectionService, and TaskService.

Per D3.8 Service Test Suite:
- Contract testing: verify public API signatures
- Command/query testing: verify write vs read separation
- Result verification: verify return types match DTO contracts
- Error contract testing: verify exception translation
- Validation testing: verify input validation
- Exception mapping testing: verify Repository → Domain error translation
- Boundary testing: verify workspace isolation
- Determinism testing: verify stateless behavior
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

from backend.service.base import BaseService
from backend.service.dto import (
    CaptureResult,
    ImportJobStatus,
    ImportStatus,
    MergeResult,
    QueryResult,
    ReflectionExecutionResult,
    ReflectionStatus,
)
from backend.service.entity_service import EntityService
from backend.service.exceptions import (
    DomainIntegrityError,
    DuplicateError,
    NotFoundError,
    TaskNotFoundError,
    ValidationError,
)
from backend.service.memory_service import MemoryService
from backend.service.query_service import QueryService
from backend.service.reflection_service import ReflectionService
from backend.service.task_service import TaskService

# ---------------------------------------------------------------------------
# Fixtures — Mock Repositories
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_memory_node_repo():
    """Mock MemoryNodeRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_entity = AsyncMock(return_value=[])
    repo.find_by_level = AsyncMock(return_value=[])
    repo.find_active_by_workspace = AsyncMock(return_value=[])
    repo.link_evidence = AsyncMock()
    repo.find_with_evidence_chain = AsyncMock(return_value={"node": None, "evidence_chain": []})
    repo.update = AsyncMock()
    repo.soft_delete_impl = AsyncMock()
    return repo


@pytest.fixture
def mock_evidence_repo():
    """Mock EvidenceRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_by_workspace = AsyncMock(return_value=[])
    repo.find_by_memory = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_relationship_repo():
    """Mock RelationshipRepository."""
    repo = AsyncMock()
    repo.create_memory_relationship = AsyncMock()
    repo.find_by_source = AsyncMock(return_value=[])
    repo.find_by_target = AsyncMock(return_value=[])
    repo.find_connections = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_archive_repo():
    """Mock ArchiveRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_type = AsyncMock(return_value=[])
    repo.find_archived = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_tag_repo():
    """Mock TagRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_by_workspace = AsyncMock(return_value=[])
    repo.find_by_name = AsyncMock(return_value=None)
    repo.link_tag = AsyncMock()
    repo.unlink_tag = AsyncMock()
    return repo


@pytest.fixture
def mock_task_repo():
    """Mock TaskRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_workspace = AsyncMock(return_value=[])
    repo.update = AsyncMock()
    repo.find_pending = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_memory_query_repo():
    """Mock MemoryQueryRepository."""
    repo = AsyncMock()
    repo.find_related_memories = AsyncMock(return_value=[])
    repo.search_by_keyword = AsyncMock(return_value=[])
    repo.browse_by_time_range = AsyncMock(return_value=[])
    repo.browse_by_category = AsyncMock(return_value=[])
    repo.browse_by_tag = AsyncMock(return_value=[])
    repo.project_to_timeline = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_entity_repo():
    """Mock EntityRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_name = AsyncMock(return_value=None)
    repo.find_by_alias = AsyncMock(return_value=[])
    repo.find_by_workspace = AsyncMock(return_value=[])
    repo.find_by_area = AsyncMock(return_value=[])
    repo.find_page = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_entity_query_repo():
    """Mock EntityQueryRepository."""
    repo = AsyncMock()
    repo.get_entity_graph = AsyncMock(return_value={"nodes": [], "edges": []})
    repo.find_by_canonical_name = AsyncMock(return_value=None)
    repo.count_by_type = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_vector_query_repo():
    """Mock VectorQueryRepository."""
    repo = AsyncMock()
    repo.similarity_search = AsyncMock(return_value=[])
    repo.hybrid_search = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_vector_doc_repo():
    """Mock VectorDocRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_by_workspace = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_candidate_repo():
    """Mock CandidateRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=uuid4())
    repo.find_candidates_by_scope = AsyncMock(return_value=[])
    repo.update_candidate_status = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# Tests — BaseService
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_base_service_name():
    """Verify BaseService stores its name."""
    service = BaseService("TestService")
    assert service.name == "TestService"


@pytest.mark.unit
def test_base_service_workspace_validation():
    """Verify BaseService validates workspace_id."""
    service = BaseService("TestService")

    with pytest.raises(ValidationError, match="workspace_id is required"):
        service._validate_workspace_id(None)


@pytest.mark.unit
def test_base_service_error_translation_not_found():
    """Verify BaseService translates NotFoundError correctly."""
    from backend.repository.exceptions import NotFoundError as RepoNotFoundError

    service = BaseService("TestService")
    exc = RepoNotFoundError(entity_type="entity", entity_id="abc-123")
    result = service.translate_repository_error(exc)

    assert isinstance(result, NotFoundError)
    assert result.message == "entity with id 'abc-123' not found"


@pytest.mark.unit
def test_base_service_error_translation_duplicate():
    """Verify BaseService translates DuplicateError correctly."""
    from backend.repository.exceptions import DuplicateError as RepoDuplicateError

    service = BaseService("TestService")
    exc = RepoDuplicateError(entity_type="entity", constraint="uk_name")
    result = service.translate_repository_error(exc)

    assert isinstance(result, DuplicateError)


@pytest.mark.unit
def test_base_service_error_translation_unknown():
    """Verify BaseService wraps unknown errors."""
    from backend.repository.exceptions import RepositoryError

    service = BaseService("TestService")
    exc = RepositoryError("Unknown error")
    result = service.translate_repository_error(exc)

    assert isinstance(result, DomainIntegrityError)


@pytest.mark.unit
def test_base_service_domain_error_passthrough():
    """Verify BaseService passes through DomainError unchanged."""
    service = BaseService("TestService")
    domain_err = NotFoundError("Already a domain error")
    result = service.translate_domain_error(domain_err)

    assert result is domain_err


@pytest.mark.unit
def test_base_service_entry_safe_dict():
    """Verify DomainError.to_entry_safe_dict produces safe output."""
    err = NotFoundError("Entity not found", resource_type="entity")
    safe = err.to_entry_safe_dict()

    assert "code" in safe
    assert "message" in safe
    assert "details" in safe
    assert safe["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Tests — MemoryService
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_service_capture(
    mock_memory_node_repo, mock_evidence_repo,
    mock_relationship_repo, mock_archive_repo,
    mock_tag_repo, mock_task_repo, mock_memory_query_repo,
):
    """Verify MemoryService.capture_memory creates a memory node.

    Note: MemoryNode is imported inside capture_memory(), so we patch
    the import at the source module level.
    """
    service = MemoryService(
        memory_node_repo=mock_memory_node_repo,
        evidence_repo=mock_evidence_repo,
        relationship_repo=mock_relationship_repo,
        archive_repo=mock_archive_repo,
        tag_repo=mock_tag_repo,
        task_repo=mock_task_repo,
        memory_query_repo=mock_memory_query_repo,
    )

    workspace_id = uuid4()
    entity_id = uuid4()
    mock_mem_id = uuid4()
    mock_memory_node_repo.create = AsyncMock(return_value=mock_mem_id)

    mock_node = Mock()
    mock_node.id = mock_mem_id
    mock_node.workspace_id = workspace_id
    mock_node.entity_id = entity_id
    mock_node.level = 1
    mock_node.node_type = "Observation"
    mock_node.content = "test content"
    mock_node.confidence = 0.8
    mock_node.importance = 0.5
    mock_node.signal_strength = 0.9
    mock_node.status = "active"
    mock_node.source = "user"
    mock_node.generated_by = "user"
    mock_node.evidence_links = []
    mock_node.contradict_evidence = []
    mock_node.metadata = {}

    with patch("backend.shared.domain.memory_models.MemoryNode", return_value=mock_node):
        result = await service.capture_memory(
            workspace_id=workspace_id,
            entity_id=entity_id,
            content="test content",
            level=1,
            confidence=0.8,
            importance=0.5,
            signal_strength=0.9,
        )

    assert isinstance(result, CaptureResult)
    assert result.memory_id == mock_mem_id
    assert result.workspace_id == workspace_id
    assert result.entity_id == entity_id
    assert result.level == 1
    assert result.source == "user"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_service_capture_empty_content(
    mock_memory_node_repo, mock_evidence_repo,
    mock_relationship_repo, mock_archive_repo,
    mock_tag_repo, mock_task_repo, mock_memory_query_repo,
):
    """Verify MemoryService rejects empty content."""
    service = MemoryService(
        memory_node_repo=mock_memory_node_repo,
        evidence_repo=mock_evidence_repo,
        relationship_repo=mock_relationship_repo,
        archive_repo=mock_archive_repo,
        tag_repo=mock_tag_repo,
        task_repo=mock_task_repo,
        memory_query_repo=mock_memory_query_repo,
    )

    with pytest.raises(ValidationError, match="content"):
        await service.capture_memory(
            workspace_id=uuid4(),
            entity_id=uuid4(),
            content="",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_service_capture_invalid_level(
    mock_memory_node_repo, mock_evidence_repo,
    mock_relationship_repo, mock_archive_repo,
    mock_tag_repo, mock_task_repo, mock_memory_query_repo,
):
    """Verify MemoryService rejects invalid level."""
    service = MemoryService(
        memory_node_repo=mock_memory_node_repo,
        evidence_repo=mock_evidence_repo,
        relationship_repo=mock_relationship_repo,
        archive_repo=mock_archive_repo,
        tag_repo=mock_tag_repo,
        task_repo=mock_task_repo,
        memory_query_repo=mock_memory_query_repo,
    )

    with pytest.raises(ValidationError, match="level"):
        await service.capture_memory(
            workspace_id=uuid4(),
            entity_id=uuid4(),
            content="test",
            level=99,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_service_import_empty(
    mock_memory_node_repo, mock_evidence_repo,
    mock_relationship_repo, mock_archive_repo,
    mock_tag_repo, mock_task_repo, mock_memory_query_repo,
):
    """Verify MemoryService.import_memories handles empty items."""
    service = MemoryService(
        memory_node_repo=mock_memory_node_repo,
        evidence_repo=mock_evidence_repo,
        relationship_repo=mock_relationship_repo,
        archive_repo=mock_archive_repo,
        tag_repo=mock_tag_repo,
        task_repo=mock_task_repo,
        memory_query_repo=mock_memory_query_repo,
    )

    result = await service.import_memories(
        workspace_id=uuid4(),
        items=[],
    )

    assert result.status == ImportStatus.COMPLETED
    assert result.total_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_service_import_success(
    mock_memory_node_repo, mock_evidence_repo,
    mock_relationship_repo, mock_archive_repo,
    mock_tag_repo, mock_task_repo, mock_memory_query_repo,
):
    """Verify MemoryService.import_memories succeeds when all items pass."""
    service = MemoryService(
        memory_node_repo=mock_memory_node_repo,
        evidence_repo=mock_evidence_repo,
        relationship_repo=mock_relationship_repo,
        archive_repo=mock_archive_repo,
        tag_repo=mock_tag_repo,
        task_repo=mock_task_repo,
        memory_query_repo=mock_memory_query_repo,
    )

    # Patch capture_memory to succeed
    async def fake_capture(*args, **kwargs):
        return CaptureResult.from_memory_id(
            memory_id=uuid4(),
            workspace_id=kwargs.get("workspace_id", uuid4()),
        )

    with patch.object(service, "capture_memory", side_effect=fake_capture):
        result = await service.import_memories(
            workspace_id=uuid4(),
            items=[
                {"content": "good1"},
                {"content": "good2"},
            ],
        )

    assert result.success_count == 2
    assert result.failure_count == 0
    assert result.total_count == 2


# ---------------------------------------------------------------------------
# Tests — QueryService
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_service_retrieve_not_found(
    mock_memory_node_repo, mock_memory_query_repo,
    mock_entity_repo, mock_entity_query_repo,
    mock_vector_query_repo, mock_vector_doc_repo,
):
    """Verify QueryService raises NotFoundError for missing memory."""
    service = QueryService(
        memory_node_repo=mock_memory_node_repo,
        memory_query_repo=mock_memory_query_repo,
        entity_repo=mock_entity_repo,
        entity_query_repo=mock_entity_query_repo,
        vector_query_repo=mock_vector_query_repo,
        vector_doc_repo=mock_vector_doc_repo,
    )

    mock_memory_node_repo.find_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.retrieve_by_id(
            workspace_id=uuid4(),
            memory_id=uuid4(),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_service_retrieve_by_id(
    mock_memory_node_repo, mock_memory_query_repo,
    mock_entity_repo, mock_entity_query_repo,
    mock_vector_query_repo, mock_vector_doc_repo,
):
    """Verify QueryService retrieves a memory by ID."""
    service = QueryService(
        memory_node_repo=mock_memory_node_repo,
        memory_query_repo=mock_memory_query_repo,
        entity_repo=mock_entity_repo,
        entity_query_repo=mock_entity_query_repo,
        vector_query_repo=mock_vector_query_repo,
        vector_doc_repo=mock_vector_doc_repo,
    )

    mock_mem = Mock()
    mock_mem.id = uuid4()
    mock_mem.content = "test"
    mock_memory_node_repo.find_by_id = AsyncMock(return_value=mock_mem)

    result = await service.retrieve_by_id(
        workspace_id=uuid4(),
        memory_id=mock_mem.id,
    )

    assert isinstance(result, QueryResult)
    assert len(result.items) == 1
    assert result.items[0] is mock_mem


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_service_search_empty_query(
    mock_memory_node_repo, mock_memory_query_repo,
    mock_entity_repo, mock_entity_query_repo,
    mock_vector_query_repo, mock_vector_doc_repo,
):
    """Verify QueryService rejects empty search query."""
    service = QueryService(
        memory_node_repo=mock_memory_node_repo,
        memory_query_repo=mock_memory_query_repo,
        entity_repo=mock_entity_repo,
        entity_query_repo=mock_entity_query_repo,
        vector_query_repo=mock_vector_query_repo,
        vector_doc_repo=mock_vector_doc_repo,
    )

    with pytest.raises(ValidationError, match="query"):
        await service.search_by_keyword(
            workspace_id=uuid4(),
            query="",
        )


# ---------------------------------------------------------------------------
# Tests — EntityService
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_entity_service_create_missing_name(
    mock_entity_repo, mock_relationship_repo,
):
    """Verify EntityService rejects empty canonical_name."""
    service = EntityService(
        entity_repo=mock_entity_repo,
        relationship_repo=mock_relationship_repo,
    )

    with pytest.raises(ValidationError, match="canonical_name"):
        await service.create_entity(
            workspace_id=uuid4(),
            entity_type="Project",
            canonical_name="",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_entity_service_resolve_missing_params(
    mock_entity_repo, mock_relationship_repo,
):
    """Verify EntityService requires entity_id or canonical_name."""
    service = EntityService(
        entity_repo=mock_entity_repo,
        relationship_repo=mock_relationship_repo,
    )

    with pytest.raises(ValidationError, match="entity_id"):
        await service.resolve_entity(
            workspace_id=uuid4(),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_entity_service_resolve_not_found(
    mock_entity_repo, mock_relationship_repo,
):
    """Verify EntityService.resolve_entity returns None for missing entity."""
    service = EntityService(
        entity_repo=mock_entity_repo,
        relationship_repo=mock_relationship_repo,
    )

    mock_entity_repo.find_by_id = AsyncMock(return_value=None)

    result = await service.resolve_entity(
        workspace_id=uuid4(),
        entity_id=uuid4(),
    )

    assert result is None


# ---------------------------------------------------------------------------
# Tests — ReflectionService
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reflection_service_no_candidates(
    mock_memory_node_repo, mock_candidate_repo, mock_relationship_repo,
):
    """Verify ReflectionService returns early when no candidates exist."""
    service = ReflectionService(
        memory_node_repo=mock_memory_node_repo,
        candidate_repo=mock_candidate_repo,
        relationship_repo=mock_relationship_repo,
    )

    mock_memory_node_repo.find_active_by_workspace = AsyncMock(return_value=[])

    result = await service.reflect(
        workspace_id=uuid4(),
        scope="workspace",
    )

    assert result.status == ReflectionStatus.COMPLETED
    assert result.reflections_performed == 0


# ---------------------------------------------------------------------------
# Tests — TaskService
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_service_submit_invalid_type(
    mock_task_repo,
):
    """Verify TaskService rejects invalid task_type."""
    service = TaskService(task_repo=mock_task_repo)

    with pytest.raises(ValidationError, match="task_type"):
        await service.submit(
            workspace_id=uuid4(),
            task_type="INVALID_TYPE",
            payload={},
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_service_get_not_found(
    mock_task_repo,
):
    """Verify TaskService raises NotFoundError for missing task."""
    service = TaskService(task_repo=mock_task_repo)

    mock_task_repo.find_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaskNotFoundError):
        await service.get_task(
            workspace_id=uuid4(),
            task_id=uuid4(),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_service_cancel_completed(
    mock_task_repo,
):
    """Verify TaskService rejects cancelling a completed task."""
    from backend.service.exceptions import TaskCancellationError

    service = TaskService(task_repo=mock_task_repo)

    mock_task = Mock()
    mock_task.id = uuid4()
    mock_task.status = "completed"
    mock_task.task_type = "INGESTION"
    mock_task.created_at = "2026-01-01T00:00:00Z"
    mock_task.updated_at = "2026-01-01T00:00:00Z"
    mock_task.completed_at = "2026-01-01T00:00:00Z"
    mock_task.retry_count = 0
    mock_task.max_retries = 3

    mock_task_repo.find_by_id = AsyncMock(return_value=mock_task)

    with pytest.raises(TaskCancellationError):
        await service.cancel_task(
            workspace_id=uuid4(),
            task_id=uuid4(),
        )


# ---------------------------------------------------------------------------
# Tests — DTO Models
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_capture_result_creation():
    """Verify CaptureResult can be created from factory method."""
    mid = uuid4()
    wsid = uuid4()
    eid = uuid4()

    result = CaptureResult.from_memory_id(
        memory_id=mid,
        workspace_id=wsid,
        entity_id=eid,
        level=1,
        source="user",
        confidence=0.9,
        importance=0.5,
        signal_strength=0.8,
        evidence_count=3,
    )

    assert result.memory_id == mid
    assert result.workspace_id == wsid
    assert result.entity_id == eid
    assert result.level == 1
    assert result.confidence == 0.9
    assert result.evidence_count == 3


@pytest.mark.unit
def test_query_result_from_page():
    """Verify QueryResult can be created from a Page."""
    from backend.repository.pagination import Page

    page = Page(
        items=["a", "b"],
        page_number=1,
        page_size=2,
        has_next=True,
    )

    qr = QueryResult.from_page(page, query_id="q-123")

    assert len(qr.items) == 2
    assert qr.query_id == "q-123"
    assert qr.has_next is True


@pytest.mark.unit
def test_reflection_execution_result():
    """Verify ReflectionExecutionResult fields."""
    result = ReflectionExecutionResult(
        status=ReflectionStatus.COMPLETED,
        reflections_performed=5,
        new_patterns=2,
        new_beliefs=1,
        evidence_completeness=0.8,
        scope="workspace",
        duration_ms=150.5,
    )

    assert result.status == ReflectionStatus.COMPLETED
    assert result.new_patterns == 2
    assert result.evidence_completeness == 0.8


@pytest.mark.unit
def test_import_job_status():
    """Verify ImportJobStatus fields."""
    job_id = uuid4()
    status = ImportJobStatus(
        job_id=job_id,
        status=ImportStatus.RUNNING,
        total_count=100,
        processed_count=50,
        success_count=48,
        failure_count=2,
    )

    assert status.job_id == job_id
    assert status.success_count + status.failure_count == status.processed_count


@pytest.mark.unit
def test_merge_result():
    """Verify MergeResult fields."""
    result = MergeResult(
        target_entity_id=uuid4(),
        source_entity_ids=[uuid4(), uuid4()],
        relationships_migrated=10,
        aliases_consolidated=3,
        memories_referenced=0,
    )

    assert len(result.source_entity_ids) == 2
    assert result.relationships_migrated == 10
