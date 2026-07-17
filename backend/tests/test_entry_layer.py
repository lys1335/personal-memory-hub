"""Unit tests for Entry Layer (D5).

Tests REST adapter, contract validation, DTO translation, and error handling.

Per D5 architecture:
- Entry is a Service Adapter (not business logic layer)
- Two-Layer Validation: Entry = contract validation, Service = domain validation
- DTO Strategy: External DTOs (Entry) <-> Internal DTOs (Service) <-> Domain Models
- Error Translation: Domain errors -> protocol-specific error responses
- One Operation -> One Capability mapping

Test Categories:
- Contract Validation Tests: syntax, structure, types
- DTO Translation Tests: external -> internal -> external round-trip
- Error Translation Tests: domain errors -> HTTP responses
- REST Adapter Tests: request lifecycle, response structure
- Boundary Tests: Entry -> Service only, no Engine/Repository calls
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

from backend.entry.dto import (
    BaseResponse,
    CaptureMemoryRequest,
    ContractValidationError,
    CreateEntityRequest,
    ErrorCategory,
    ResponseStatus,
    SearchRequest,
)
from backend.entry.rest_adapter import RESTAdapter
from backend.entry.validation import ContractValidator
from backend.service.dto import (
    CaptureResult,
    QueryResult,
    ReflectionExecutionResult,
    ReflectionStatus,
    TaskStatus,
    TaskSubmissionResult,
)
from backend.service.exceptions import NotFoundError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_services():
    """Mock services dict for REST adapter."""
    services = {
        "memory": MagicMock(),
        "query": MagicMock(),
        "entity": MagicMock(),
        "reflection": MagicMock(),
        "task": MagicMock(),
    }
    return services


@pytest.fixture
def rest_adapter(mock_services):
    """REST adapter with mocked services."""
    return RESTAdapter(services=mock_services)


@pytest.fixture
def validator():
    """Contract validator instance."""
    return ContractValidator()


# ---------------------------------------------------------------------------
# Tests - Contract Validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validator_capture_memory_valid(validator):
    """Verify valid capture memory request passes validation."""
    data = {
        "workspace_id": str(uuid4()),
        "content": "Test memory content",
        "level": 1,
        "confidence": 0.8,
        "importance": 0.5,
        "signal_strength": 0.7,
    }
    errors = validator.validate_capture_memory_request(data)
    assert len(errors) == 0


@pytest.mark.unit
def test_validator_capture_memory_missing_workspace(validator):
    """Verify capture memory validation catches missing workspace_id."""
    data = {"content": "Test content"}
    errors = validator.validate_capture_memory_request(data)
    assert any(e.field == "workspace_id" for e in errors)


@pytest.mark.unit
def test_validator_capture_memory_missing_content(validator):
    """Verify capture memory validation catches missing content."""
    data = {"workspace_id": str(uuid4())}
    errors = validator.validate_capture_memory_request(data)
    assert any(e.field == "content" for e in errors)


@pytest.mark.unit
def test_validator_capture_memory_empty_content(validator):
    """Verify capture memory validation catches empty content."""
    data = {"workspace_id": str(uuid4()), "content": ""}
    errors = validator.validate_capture_memory_request(data)
    assert any(e.code == "CONTRACT_RANGE_EXCEEDED" for e in errors)


@pytest.mark.unit
def test_validator_capture_memory_invalid_level(validator):
    """Verify capture memory validation catches invalid level."""
    data = {"workspace_id": str(uuid4()), "content": "test", "level": 99}
    errors = validator.validate_capture_memory_request(data)
    assert any(e.field == "level" for e in errors)


@pytest.mark.unit
def test_validator_capture_memory_invalid_confidence(validator):
    """Verify capture memory validation catches out-of-range confidence."""
    data = {"workspace_id": str(uuid4()), "content": "test", "confidence": 1.5}
    errors = validator.validate_capture_memory_request(data)
    assert any(e.field == "confidence" for e in errors)


@pytest.mark.unit
def test_validator_capture_memory_invalid_observation_type(validator):
    """Verify capture memory validation catches invalid observation_type."""
    data = {
        "workspace_id": str(uuid4()),
        "content": "test",
        "observation_type": "invalid_type",
    }
    errors = validator.validate_capture_memory_request(data)
    assert any(e.field == "observation_type" for e in errors)


@pytest.mark.unit
def test_validator_create_entity_valid(validator):
    """Verify valid create entity request passes validation."""
    data = {
        "workspace_id": str(uuid4()),
        "entity_type": "Project",
        "canonical_name": "Test Project",
    }
    errors = validator.validate_create_entity_request(data)
    assert len(errors) == 0


@pytest.mark.unit
def test_validator_create_entity_invalid_type(validator):
    """Verify create entity validation catches invalid entity_type."""
    data = {
        "workspace_id": str(uuid4()),
        "entity_type": "InvalidType",
        "canonical_name": "Test",
    }
    errors = validator.validate_create_entity_request(data)
    assert any(e.field == "entity_type" for e in errors)


@pytest.mark.unit
def test_validator_search_valid(validator):
    """Verify valid search request passes validation."""
    data = {"workspace_id": str(uuid4()), "query": "test"}
    errors = validator.validate_search_request(data)
    assert len(errors) == 0


@pytest.mark.unit
def test_validator_search_empty_query(validator):
    """Verify search validation catches empty query."""
    data = {"workspace_id": str(uuid4()), "query": ""}
    errors = validator.validate_search_request(data)
    assert any(e.field == "query" for e in errors)


@pytest.mark.unit
def test_validator_submit_task_valid(validator):
    """Verify valid task submission passes validation."""
    data = {
        "workspace_id": str(uuid4()),
        "task_type": "REFLECTION",
        "payload": {"scope": "workspace"},
    }
    errors = validator.validate_submit_task_request(data)
    assert len(errors) == 0


@pytest.mark.unit
def test_validator_submit_task_invalid_type(validator):
    """Verify task validation catches invalid task_type."""
    data = {
        "workspace_id": str(uuid4()),
        "task_type": "INVALID",
        "payload": {},
    }
    errors = validator.validate_submit_task_request(data)
    assert any(e.field == "task_type" for e in errors)


# ---------------------------------------------------------------------------
# Tests - DTO Translation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_capture_memory_request_to_internal():
    """Verify CaptureMemoryRequest translates to internal dict."""
    req = CaptureMemoryRequest(
        workspace_id=str(uuid4()),
        content="Test content",
        level=1,
        confidence=0.8,
    )
    internal = req.to_internal_dict()

    assert isinstance(internal["workspace_id"], UUID)
    assert internal["content"] == "Test content"
    assert internal["level"] == 1
    assert internal["confidence"] == 0.8


@pytest.mark.unit
def test_create_entity_request_to_internal():
    """Verify CreateEntityRequest translates to internal dict."""
    req = CreateEntityRequest(
        workspace_id=str(uuid4()),
        entity_type="Project",
        canonical_name="Test",
        area_id=str(uuid4()),
    )
    internal = req.to_internal_dict()

    assert isinstance(internal["workspace_id"], UUID)
    assert isinstance(internal["area_id"], UUID)
    assert internal["entity_type"] == "Project"


@pytest.mark.unit
def test_search_request_to_internal():
    """Verify SearchRequest translates to internal dict."""
    req = SearchRequest(
        workspace_id=str(uuid4()),
        query="test",
        limit=25,
    )
    internal = req.to_internal_dict()

    assert isinstance(internal["workspace_id"], UUID)
    assert internal["limit"] == 25


# ---------------------------------------------------------------------------
# Tests - BaseResponse
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_base_response_success():
    """Verify BaseResponse.success creates correct response."""
    resp = BaseResponse.success(
        request_id="req-123",
        data={"key": "value"},
    )
    assert resp.status == ResponseStatus.SUCCESS
    assert resp.request_id == "req-123"
    assert resp.data == {"key": "value"}
    assert resp.error is None


@pytest.mark.unit
def test_base_response_error():
    """Verify BaseResponse.error_response creates correct response."""
    resp = BaseResponse.error_response(
        request_id="req-456",
        code="NOT_FOUND",
        message="Entity not found",
        category=ErrorCategory.DOMAIN_ERROR,
    )
    assert resp.status == ResponseStatus.ERROR
    assert resp.error["code"] == "NOT_FOUND"
    assert resp.error["category"] == "DOMAIN_ERROR"
    assert resp.data is None


@pytest.mark.unit
def test_contract_validation_error_to_dict():
    """Verify ContractValidationError serializes correctly."""
    err = ContractValidationError(
        code="CONTRACT_MISSING_FIELD",
        field="workspace_id",
        message="Required field missing",
    )
    d = err.to_dict()
    assert d["code"] == "CONTRACT_MISSING_FIELD"
    assert d["field"] == "workspace_id"


# ---------------------------------------------------------------------------
# Tests - REST Adapter
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rest_capture_memory_success(rest_adapter, mock_services):
    """Verify REST adapter captures memory successfully."""
    mock_result = CaptureResult.from_memory_id(
        memory_id=uuid4(),
        workspace_id=uuid4(),
        entity_id=uuid4(),
        level=1,
        source="user",
        confidence=0.8,
        importance=0.5,
        signal_strength=0.7,
        evidence_count=2,
    )
    mock_services["memory"].capture_memory = MagicMock(return_value=mock_result)

    body = {
        "workspace_id": str(uuid4()),
        "content": "Test memory",
        "level": 1,
        "confidence": 0.8,
        "importance": 0.5,
        "signal_strength": 0.7,
    }

    result = rest_adapter.handle_capture_memory(body)

    assert result.status == ResponseStatus.SUCCESS
    assert result.data is not None
    assert "memory_id" in result.data


@pytest.mark.unit
def test_rest_capture_memory_contract_validation(rest_adapter, mock_services):
    """Verify REST adapter returns contract validation error."""
    body = {}  # Missing all required fields

    result = rest_adapter.handle_capture_memory(body)

    assert result.status == ResponseStatus.ERROR
    assert result.error["code"] == "CONTRACT_VALIDATION_ERROR"
    assert result.error["category"] == "CONTRACT_VALIDATION"


@pytest.mark.unit
def test_rest_search_success(rest_adapter, mock_services):
    """Verify REST adapter searches memories successfully."""
    mock_result = QueryResult(
        items=[{"id": "test", "content": "test"}],
        total=1,
        page_number=1,
        has_next=False,
    )
    mock_services["query"].search_by_keyword = MagicMock(return_value=mock_result)

    body = {
        "workspace_id": str(uuid4()),
        "query": "test",
        "limit": 50,
    }

    result = rest_adapter.handle_search_memory(body)

    assert result.status == ResponseStatus.SUCCESS
    assert result.data is not None
    assert "items" in result.data


@pytest.mark.unit
def test_rest_create_entity_success(rest_adapter, mock_services):
    """Verify REST adapter creates entity successfully."""
    entity_id = uuid4()
    mock_services["entity"].create_entity = MagicMock(return_value=entity_id)

    body = {
        "workspace_id": str(uuid4()),
        "entity_type": "Project",
        "canonical_name": "Test Project",
    }

    result = rest_adapter.handle_create_entity(body)

    assert result.status == ResponseStatus.SUCCESS
    assert result.data["entity_id"] == str(entity_id)


@pytest.mark.unit
def test_rest_trigger_reflection_success(rest_adapter, mock_services):
    """Verify REST adapter triggers reflection successfully."""
    mock_result = ReflectionExecutionResult(
        status=ReflectionStatus.COMPLETED,
        reflections_performed=5,
        new_patterns=2,
        new_beliefs=1,
        scope="workspace",
    )
    mock_services["reflection"].reflect = MagicMock(return_value=mock_result)

    body = {
        "workspace_id": str(uuid4()),
        "scope": "workspace",
    }

    result = rest_adapter.handle_trigger_reflection(body)

    assert result.status == ResponseStatus.SUCCESS
    assert result.data["status"] == "completed"
    assert result.data["reflections_performed"] == 5


@pytest.mark.unit
def test_rest_submit_task_success(rest_adapter, mock_services):
    """Verify REST adapter submits task successfully."""
    mock_result = TaskSubmissionResult(
        task_id=uuid4(),
        status=TaskStatus.PENDING,
    )
    mock_services["task"].submit = MagicMock(return_value=mock_result)

    body = {
        "workspace_id": str(uuid4()),
        "task_type": "REFLECTION",
        "payload": {"scope": "workspace"},
    }

    result = rest_adapter.handle_submit_task(body)

    assert result.status == ResponseStatus.SUCCESS
    assert result.data["task_id"] is not None


@pytest.mark.unit
def test_rest_error_translation_not_found(rest_adapter, mock_services):
    """Verify REST adapter translates NotFoundError correctly."""
    mock_services["query"].retrieve_by_id = MagicMock(
        side_effect=NotFoundError("Memory not found", resource_type="memory_node")
    )

    body = {
        "workspace_id": str(uuid4()),
        "memory_id": str(uuid4()),
    }

    result = rest_adapter.handle_retrieve_memory(body)

    assert result.status == ResponseStatus.ERROR
    assert result.error["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Tests - Entry Layer Boundary
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rest_adapter_no_engine_imports():
    """Verify REST adapter doesn't import from engine layer."""
    import backend.entry.dto
    import backend.entry.rest_adapter
    import backend.entry.validation

    for mod in (backend.entry.rest_adapter, backend.entry.validation, backend.entry.dto):
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if obj and hasattr(obj, "__module__"):
                assert not obj.__module__.startswith("backend.engine"), \
                    f"{obj.__module__}.{name} imports from engine layer"


@pytest.mark.unit
def test_rest_adapter_no_repository_imports():
    """Verify REST adapter doesn't import from repository layer."""
    import backend.entry.dto
    import backend.entry.rest_adapter
    import backend.entry.validation

    for mod in (backend.entry.rest_adapter, backend.entry.validation, backend.entry.dto):
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if obj and hasattr(obj, "__module__"):
                assert not obj.__module__.startswith("backend.repository"), \
                    f"{obj.__module__}.{name} imports from repository layer"
