"""REST Adapter - HTTP protocol adapter for Personal Memory Hub.

Per D5_Entry_Layer_Architecture:
- Entry is a Service Adapter, not a business logic layer
- REST API is one of multiple Entry Adapters (others: MCP, CLI, SDK)
- One Operation -> One Capability mapping
- Two-Layer Validation: Entry = contract validation, Service = domain validation
- Error Translation: Domain errors -> HTTP response codes
- Protocol-agnostic: same Service Layer through multiple adapters

This module provides:
- RESTAdapter: HTTP request handler that adapts to Service Layer
- Request lifecycle: Parse -> Validate -> Translate -> Execute -> Translate -> Serialize
- Response lifecycle: Consistent structure per D5 section 5.2
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from backend.entry.dto import (
    BaseResponse,
    CaptureMemoryRequest,
    CreateEntityRequest,
    ErrorCategory,
    ImportRequest,
    RetrieveRequest,
    SearchRequest,
    SubmitTaskRequest,
    TriggerReflectionRequest,
)
from backend.entry.validation import ContractValidator
from backend.service.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class RESTAdapter:
    """HTTP REST protocol adapter for the Personal Memory Hub.

    Adapts HTTP requests to Service Layer commands and Service results
    to HTTP responses. Stateless singleton.

    Request Lifecycle (per D5 section 4.1):
    1. Protocol Parsing (adapter-specific)
    2. Contract Validation (Entry)
    3. Translation to Service Command (Entry)
    4. Service Execution (Service Layer)
    5. Domain Result Processing (Service Layer)
    6. Translation to External Response (Entry)
    7. Protocol Serialization (adapter-specific)
    """

    def __init__(self, services: dict[str, Any]) -> None:
        """Initialize REST adapter with service references.

        Args:
            services: Dict of service instances keyed by name.
                Expected keys: memory, query, entity, reflection, task.
        """
        self._services = services
        self._validator = ContractValidator()

    # ------------------------------------------------------------------
    # Memory Endpoints
    # ------------------------------------------------------------------

    def handle_capture_memory(
        self,
        body: dict[str, Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Handle POST /memories - capture a new memory."""
        request_id = str(uuid4())

        # Step 2: Contract Validation
        errors = self._validator.validate_capture_memory_request(body)
        if errors:
            return self._contract_validation_response(request_id, errors)

        # Step 3: Translation to Service Command
        request = CaptureMemoryRequest(**body)
        cmd = request.to_internal_dict()

        # Step 4: Service Execution
        try:
            result = self._services["memory"].capture_memory(**cmd)
        except ValidationError as exc:
            return self._domain_error_response(request_id, exc)
        except Exception as exc:
            return self._infrastructure_error_response(request_id, exc)

        # Step 6: Translation to External Response
        return BaseResponse.success(
            request_id=request_id,
            data={
                "memory_id": str(result.memory_id),
                "workspace_id": str(result.workspace_id),
                "entity_id": str(result.entity_id) if result.entity_id else None,
                "level": result.level,
                "source": result.source,
                "confidence": result.confidence,
                "importance": result.importance,
                "signal_strength": result.signal_strength,
                "evidence_count": result.evidence_count,
            },
        )

    async def handle_search_memory(
        self,
        body: dict[str, Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Handle POST /memories/search - search memories."""
        request_id = str(uuid4())

        errors = self._validator.validate_search_request(body)
        if errors:
            return self._contract_validation_response(request_id, errors)

        request = SearchRequest(**body)
        cmd = request.to_internal_dict()

        try:
            result = await self._services["query"].search_by_keyword(**cmd)
        except Exception as exc:
            return self._domain_error_response(request_id, exc)

        return BaseResponse.success(
            request_id=request_id,
            data={
                "items": [self._serialize_item(item) for item in result.items],
                "total": result.total,
                "page_number": result.page_number,
                "has_next": result.has_next,
            },
        )

    def handle_retrieve_memory(
        self,
        body: dict[str, Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Handle GET /memories/{id} - retrieve a memory by ID."""
        request_id = str(uuid4())

        errors = self._validator.validate_retrieve_request(body)
        if errors:
            return self._contract_validation_response(request_id, errors)

        request = RetrieveRequest(**body)
        cmd = request.to_internal_dict()

        try:
            result = self._services["query"].retrieve_by_id(**cmd)
        except NotFoundError:
            return BaseResponse.error_response(
                request_id=request_id,
                code="NOT_FOUND",
                message="Memory not found",
                category=ErrorCategory.DOMAIN_ERROR,
            )
        except Exception as exc:
            return self._domain_error_response(request_id, exc)

        return BaseResponse.success(
            request_id=request_id,
            data=self._serialize_item(result.items[0]) if result.items else {},
        )

    # ------------------------------------------------------------------
    # Entity Endpoints
    # ------------------------------------------------------------------

    def handle_create_entity(
        self,
        body: dict[str, Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Handle POST /entities - create a new entity."""
        request_id = str(uuid4())

        errors = self._validator.validate_create_entity_request(body)
        if errors:
            return self._contract_validation_response(request_id, errors)

        request = CreateEntityRequest(**body)
        cmd = request.to_internal_dict()

        try:
            entity_id = self._services["entity"].create_entity(**cmd)
        except ValidationError as exc:
            return self._domain_error_response(request_id, exc)
        except Exception as exc:
            return self._domain_error_response(request_id, exc)

        return BaseResponse.success(
            request_id=request_id,
            data={"entity_id": str(entity_id)},
        )

    # ------------------------------------------------------------------
    # Reflection Endpoints
    # ------------------------------------------------------------------

    def handle_trigger_reflection(
        self,
        body: dict[str, Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Handle POST /reflection - trigger reflection."""
        request_id = str(uuid4())

        errors = self._validator.validate_reflection_request(body)
        if errors:
            return self._contract_validation_response(request_id, errors)

        request = TriggerReflectionRequest(**body)
        cmd = request.to_internal_dict()

        try:
            result = self._services["reflection"].reflect(**cmd)
        except Exception as exc:
            return self._domain_error_response(request_id, exc)

        return BaseResponse.success(
            request_id=request_id,
            data={
                "status": result.status.value,
                "reflections_performed": result.reflections_performed,
                "new_patterns": result.new_patterns,
                "new_beliefs": result.new_beliefs,
                "scope": result.scope,
            },
        )

    # ------------------------------------------------------------------
    # Task Endpoints
    # ------------------------------------------------------------------

    def handle_submit_task(
        self,
        body: dict[str, Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Handle POST /tasks - submit a new task."""
        request_id = str(uuid4())

        errors = self._validator.validate_submit_task_request(body)
        if errors:
            return self._contract_validation_response(request_id, errors)

        request = SubmitTaskRequest(**body)
        cmd = request.to_internal_dict()

        try:
            result = self._services["task"].submit(**cmd)
        except ValidationError as exc:
            return self._domain_error_response(request_id, exc)
        except Exception as exc:
            return self._domain_error_response(request_id, exc)

        return BaseResponse.success(
            request_id=request_id,
            data={
                "task_id": str(result.task_id),
                "status": result.status.value,
            },
        )

    # ------------------------------------------------------------------
    # Import Endpoints
    # ------------------------------------------------------------------

    async def handle_import_memories(
        self,
        body: dict[str, Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Handle POST /memories/import - import memories from external source."""
        request_id = str(uuid4())

        errors = self._validator.validate_import_request(body)
        if errors:
            return self._contract_validation_response(request_id, errors)

        request = ImportRequest(**body)
        cmd = request.to_internal_dict()

        try:
            result = await self._services["memory"].import_memories(**cmd)
        except Exception as exc:
            return self._domain_error_response(request_id, exc)

        return BaseResponse.success(
            request_id=request_id,
            data={
                "job_id": str(result.job_id),
                "status": result.status.value,
                "total_count": result.total_count,
                "processed_count": result.processed_count,
                "success_count": result.success_count,
                "failure_count": result.failure_count,
                "error_messages": result.error_messages,
            },
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _contract_validation_response(
        self,
        request_id: str,
        errors: list[Any],
    ) -> BaseResponse[dict[str, Any]]:
        """Create a contract validation error response."""
        error_details = [e.to_dict() for e in errors]
        return BaseResponse.error_response(
            request_id=request_id,
            code="CONTRACT_VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": error_details},
            category=ErrorCategory.CONTRACT_VALIDATION,
        )

    def _domain_error_response(
        self,
        request_id: str,
        exc: Exception,
    ) -> BaseResponse[dict[str, Any]]:
        """Create a domain error response.

        Translates Service/Engine errors to protocol-specific format.
        """
        if isinstance(exc, NotFoundError):
            return BaseResponse.error_response(
                request_id=request_id,
                code="NOT_FOUND",
                message=str(exc),
                category=ErrorCategory.DOMAIN_ERROR,
            )
        if isinstance(exc, ValidationError):
            return BaseResponse.error_response(
                request_id=request_id,
                code="VALIDATION_ERROR",
                message=str(exc),
                category=ErrorCategory.DOMAIN_ERROR,
            )
        if isinstance(exc, DomainError):
            return BaseResponse.error_response(
                request_id=request_id,
                code=exc.error_code,
                message=exc.message,
                details=exc.details,
                category=ErrorCategory.DOMAIN_ERROR,
            )

        # Infrastructure error
        logger.error("Unhandled error: %s", exc, exc_info=True)
        return BaseResponse.error_response(
            request_id=request_id,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            category=ErrorCategory.INFRASTRUCTURE,
        )

    def _infrastructure_error_response(
        self,
        request_id: str,
        exc: Exception,
    ) -> BaseResponse[dict[str, Any]]:
        """Create an infrastructure error response."""
        return BaseResponse.error_response(
            request_id=request_id,
            code="INFRASTRUCTURE_ERROR",
            message="Service temporarily unavailable",
            category=ErrorCategory.INFRASTRUCTURE,
        )

    def _serialize_item(self, item: Any) -> dict[str, Any]:
        """Serialize a domain object to a dict for external response."""
        if isinstance(item, dict):
            return item
        result = {}
        for key in dir(item):
            if key.startswith("_"):
                continue
            try:
                val = getattr(item, key)
                if callable(val):
                    continue
                result[key] = str(val) if not isinstance(val, (str, int, float, bool, type(None))) else val
            except Exception:
                pass
        return result
