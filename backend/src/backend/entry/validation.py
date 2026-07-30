"""Entry Layer Validation — Contract validation for external requests.

Per D5 §6.1 Two-Layer Validation:
- Entry Layer: Contract Validation (syntax, structure, types)
- Service Layer: Domain Validation (semantics, business rules)

Entry validation does NOT verify:
- Entity existence (domain concern)
- Permission/access rights (security concern)
- Business rule compliance (domain concern)
- Data consistency (domain concern)

Per D5 §6.3: Contract validation errors are distinct from domain errors.
Error categories: CONTRACT_MISSING_FIELD, CONTRACT_INVALID_TYPE,
CONTRACT_RANGE_EXCEEDED, CONSTRUCT_STRUCTURE_INVALID,
PROTOCOL_CONSTRAINT_VIOLATION.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.entry.dto import ContractValidationError

logger = logging.getLogger(__name__)


class ContractValidator:
    """Validates external requests against published contracts.

    Stateless validator — no mutable instance state.
    """

    # Allowed entity types per 09_Database_Physical_Design
    VALID_ENTITY_TYPES = frozenset((
        "Project", "Person", "Organization", "Tool", "Technology",
        "Concept", "Event", "Location", "Object", "Agent", "Model", "Document",
    ))

    # Allowed task types per 09_Database_Physical_Design
    VALID_TASK_TYPES = frozenset(("INGESTION", "REFLECTION", "ACTIVATION", "ARCHIVE"))

    # Allowed memory levels
    VALID_MEMORY_LEVELS = frozenset((1, 2, 3))

    # Allowed observation types
    VALID_OBSERVATION_TYPES = frozenset((
        "activity", "decision", "preference", "fact", "goal", "problem", "event",
    ))

    # Max lengths
    MAX_CANONICAL_NAME_LENGTH = 255
    MAX_ENTITY_TYPE_LENGTH = 50
    MAX_CONTENT_LENGTH = 100000  # 100KB

    # Validation rules
    MIN_CONTENT_LENGTH = 1
    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0

    def __init__(self) -> None:
        """Initialize ContractValidator."""
        self._errors: list[ContractValidationError] = []

    def reset(self) -> None:
        """Reset validation state for a new request."""
        self._errors = []

    @property
    def errors(self) -> list[ContractValidationError]:
        """Return accumulated validation errors."""
        return self._errors

    @property
    def is_valid(self) -> bool:
        """Return True if no validation errors accumulated."""
        return len(self._errors) == 0

    def add_error(self, code: str, field: str, message: str) -> None:
        """Add a validation error."""
        self._errors.append(ContractValidationError(code=code, field=field, message=message))

    # ------------------------------------------------------------------
    # Memory Validation
    # ------------------------------------------------------------------

    def validate_capture_memory_request(self, data: dict[str, Any]) -> list[ContractValidationError]:
        """Validate a capture memory request against contract.

        Per D5 §6.4: Validation order — protocol parsing → contract validation.

        Args:
            data: Parsed request data dict.

        Returns:
            List of validation errors (empty if valid).
        """
        self.reset()

        # Required fields
        if "workspace_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "workspace_id", "Required field missing")
        if "content" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "content", "Required field missing")

        if not self.is_valid:
            return self.errors

        # Type checks
        if not isinstance(data.get("workspace_id"), str):
            self.add_error("CONTRACT_INVALID_TYPE", "workspace_id", "Must be a string")

        if not isinstance(data.get("content"), str):
            self.add_error("CONTRACT_INVALID_TYPE", "content", "Must be a string")
        elif len(data["content"].strip()) < self.MIN_CONTENT_LENGTH:
            self.add_error("CONTRACT_RANGE_EXCEEDED", "content", "Content cannot be empty")
        elif len(data["content"]) > self.MAX_CONTENT_LENGTH:
            self.add_error("CONTRACT_RANGE_EXCEEDED", "content", f"Content exceeds max length of {self.MAX_CONTENT_LENGTH}")

        # Optional field validations
        level = data.get("level", 1)
        if not isinstance(level, int) or level not in self.VALID_MEMORY_LEVELS:
            self.add_error("CONTRACT_INVALID_TYPE", "level", "Must be 1, 2, or 3")

        confidence = data.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)) or not (self.MIN_CONFIDENCE <= confidence <= self.MAX_CONFIDENCE):
            self.add_error("CONTRACT_RANGE_EXCEEDED", "confidence", "Must be between 0.0 and 1.0")

        importance = data.get("importance", 0.0)
        if not isinstance(importance, (int, float)) or not (self.MIN_CONFIDENCE <= importance <= self.MAX_CONFIDENCE):
            self.add_error("CONTRACT_RANGE_EXCEEDED", "importance", "Must be between 0.0 and 1.0")

        signal_strength = data.get("signal_strength", 0.0)
        if not isinstance(signal_strength, (int, float)) or not (self.MIN_CONFIDENCE <= signal_strength <= self.MAX_CONFIDENCE):
            self.add_error("CONTRACT_RANGE_EXCEEDED", "signal_strength", "Must be between 0.0 and 1.0")

        observation_type = data.get("observation_type")
        if observation_type is not None and observation_type not in self.VALID_OBSERVATION_TYPES:
            self.add_error("CONTRACT_INVALID_TYPE", "observation_type", f"Must be one of {sorted(self.VALID_OBSERVATION_TYPES)}")

        return self.errors

    # ------------------------------------------------------------------
    # Entity Validation
    # ------------------------------------------------------------------

    def validate_create_entity_request(self, data: dict[str, Any]) -> list[ContractValidationError]:
        """Validate a create entity request against contract.

        Args:
            data: Parsed request data dict.

        Returns:
            List of validation errors.
        """
        self.reset()

        if "workspace_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "workspace_id", "Required field missing")
        if "entity_type" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "entity_type", "Required field missing")
        if "canonical_name" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "canonical_name", "Required field missing")

        if not self.is_valid:
            return self.errors

        entity_type = data.get("entity_type", "")
        if not isinstance(entity_type, str):
            self.add_error("CONTRACT_INVALID_TYPE", "entity_type", "Must be a string")
        elif entity_type not in self.VALID_ENTITY_TYPES:
            self.add_error("CONTRACT_INVALID_TYPE", "entity_type", f"Must be one of {sorted(self.VALID_ENTITY_TYPES)}")

        canonical_name = data.get("canonical_name", "")
        if not isinstance(canonical_name, str):
            self.add_error("CONTRACT_INVALID_TYPE", "canonical_name", "Must be a string")
        elif len(canonical_name) > self.MAX_CANONICAL_NAME_LENGTH:
            self.add_error("CONTRACT_RANGE_EXCEEDED", "canonical_name", f"Exceeds max length of {self.MAX_CANONICAL_NAME_LENGTH}")

        return self.errors

    # ------------------------------------------------------------------
    # Query Validation
    # ------------------------------------------------------------------

    def validate_search_request(self, data: dict[str, Any]) -> list[ContractValidationError]:
        """Validate a search request against contract.

        Args:
            data: Parsed request data dict.

        Returns:
            List of validation errors.
        """
        self.reset()

        if "workspace_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "workspace_id", "Required field missing")
        if "query" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "query", "Required field missing")

        if not self.is_valid:
            return self.errors

        query = data.get("query", "")
        if not isinstance(query, str):
            self.add_error("CONTRACT_INVALID_TYPE", "query", "Query must be a string")
        # Allow empty string to mean "no filter" - do not add error for empty query

        limit = data.get("limit", 50)
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            self.add_error("CONTRACT_RANGE_EXCEEDED", "limit", "Must be between 1 and 1000")

        return self.errors

    def validate_retrieve_request(self, data: dict[str, Any]) -> list[ContractValidationError]:
        """Validate a retrieve request against contract.

        Args:
            data: Parsed request data dict.

        Returns:
            List of validation errors.
        """
        self.reset()

        if "workspace_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "workspace_id", "Required field missing")
        if "memory_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "memory_id", "Required field missing")

        return self.errors

    # ------------------------------------------------------------------
    # Reflection Validation
    # ------------------------------------------------------------------

    def validate_reflection_request(self, data: dict[str, Any]) -> list[ContractValidationError]:
        """Validate a reflection trigger request against contract.

        Args:
            data: Parsed request data dict.

        Returns:
            List of validation errors.
        """
        self.reset()

        if "workspace_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "workspace_id", "Required field missing")

        return self.errors

    # ------------------------------------------------------------------
    # Task Validation
    # ------------------------------------------------------------------

    def validate_submit_task_request(self, data: dict[str, Any]) -> list[ContractValidationError]:
        """Validate a task submission request against contract.

        Args:
            data: Parsed request data dict.

        Returns:
            List of validation errors.
        """
        self.reset()

        if "workspace_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "workspace_id", "Required field missing")
        if "task_type" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "task_type", "Required field missing")
        if "payload" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "payload", "Required field missing")

        if not self.is_valid:
            return self.errors

        task_type = data.get("task_type", "")
        if task_type not in self.VALID_TASK_TYPES:
            self.add_error("CONTRACT_INVALID_TYPE", "task_type", f"Must be one of {sorted(self.VALID_TASK_TYPES)}")

        if not isinstance(data.get("payload"), dict):
            self.add_error("CONTRACT_INVALID_TYPE", "payload", "Must be a JSON object")

        return self.errors

    # ------------------------------------------------------------------
    # Import Validation
    # ------------------------------------------------------------------

    def validate_import_request(self, data: dict[str, Any]) -> list[ContractValidationError]:
        """Validate an import request against contract.

        Per D5 §6.1: Entry Layer validates contract structure only.
        Service Layer handles domain validation of parsed items.

        Args:
            data: Parsed request data dict.

        Returns:
            List of validation errors (empty if valid).
        """
        self.reset()

        if "workspace_id" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "workspace_id", "Required field missing")
        if "source_type" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "source_type", "Required field missing")
        if "data" not in data:
            self.add_error("CONTRACT_MISSING_FIELD", "data", "Required field missing")

        if not self.is_valid:
            return self.errors

        # Validate source_type is a string
        source_type = data.get("source_type", "")
        if not isinstance(source_type, str) or not source_type.strip():
            self.add_error("CONTRACT_INVALID_TYPE", "source_type", "Must be a non-empty string")

        # Validate data is a string (will be parsed by adapter)
        data_field = data.get("data")
        if not isinstance(data_field, str):
            self.add_error("CONTRACT_INVALID_TYPE", "data", "Must be a JSON string")
        elif len(data_field) > self.MAX_CONTENT_LENGTH:
            self.add_error("CONTRACT_RANGE_EXCEEDED", "data", f"Data exceeds max length of {self.MAX_CONTENT_LENGTH}")

        return self.errors
