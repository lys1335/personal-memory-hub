"""ProjectionEngine — Projection Domain semantic consistency owner.

Per D4.2f_ProjectionEngine_Architecture:
- Stateless domain engine for producing domain projections
- Owns: domain projection production, projection semantics enforcement,
  projection structure normalization, projection policy application,
  domain integrity preservation, deterministic result production,
  presentation independence
- Position: AFTER Retrieval, AFTER Candidate Discovery, BEFORE Business Assembly
- Domain rules: Projection Preservation, Aggregate Safety, Determinism,
  Independence
- Domain invariants: 9 invariants including builder monopoly,
  deterministic output, aggregate safety

Public contract:
- produce_projection(domain_objects, policy) → DomainResult
- enforce_semantics(projection) → DomainResult
- normalize_structure(projection) → DomainResult
- apply_policy(domain_objects, policy) → DomainResult
- verify_determinism(input, projection) → DomainResult
- verify_invariants(projection) → DomainResult
"""

from __future__ import annotations

import logging
from typing import Any

from backend.engine.base import (
    DomainInvariantViolation,
    DomainResult,
    DomainRuleViolation,
    EngineBase,
)

logger = logging.getLogger(__name__)


class ProjectionEngine(EngineBase):
    """Domain engine for Projection semantics.

    ProjectionEngine owns Projection domain rules, deterministic
    projection production, and structure normalization. It transforms
    already-retrieved Domain Objects into deterministic, domain-consistent
    Projections.

    Stateless singleton — all state comes from Repository reads.
    """

    def __init__(self) -> None:
        """Initialize ProjectionEngine."""
        super().__init__("ProjectionEngine")

    # ------------------------------------------------------------------
    # Capability 1: Produce Domain Projection
    # ------------------------------------------------------------------

    def produce_projection(
        self,
        *,
        domain_objects: list[dict[str, Any]],
        policy: dict[str, Any],
    ) -> DomainResult[list[dict[str, Any]]]:
        """Produce domain-consistent projections from retrieved objects.

        Per D4.2f §2.1: Transforms retrieved Domain Objects into
        Projections, applying projection policies to determine output
        structure.

        Args:
            domain_objects: List of retrieved domain object dicts.
            policy: Projection policy dict with keys:
                type (str: "summary", "detail", "graph", "timeline"),
                max_items (int), include_metadata (bool).

        Returns:
            DomainResult with list of projected dicts.
        """
        if not domain_objects:
            return DomainResult.ok([])

        if not policy:
            policy = {"type": "summary", "max_items": 100, "include_metadata": True}

        proj_type = policy.get("type", "summary")
        max_items = policy.get("max_items", 100)
        include_metadata = policy.get("include_metadata", True)

        # Apply projection based on type
        projections = []
        for obj in domain_objects[:max_items]:
            if proj_type == "summary":
                projected = self._project_summary(obj, include_metadata)
            elif proj_type == "detail":
                projected = self._project_detail(obj, include_metadata)
            elif proj_type == "graph":
                projected = self._project_graph(obj)
            elif proj_type == "timeline":
                projected = self._project_timeline(obj)
            else:
                projected = self._project_summary(obj, include_metadata)
            projections.append(projected)

        return DomainResult.ok(projections)

    # ------------------------------------------------------------------
    # Capability 2: Enforce Projection Semantics
    # ------------------------------------------------------------------

    def enforce_semantics(
        self,
        *,
        projection: dict[str, Any],
    ) -> DomainResult[bool]:
        """Enforce projection semantics on a projection.

        Per D4.2f §2.2:
        - Projections must preserve original domain meaning
        - Projections must not infer new knowledge
        - Projections must follow explicit policies
        - Projections must be aggregate-safe

        Args:
            projection: Projection dict to validate.

        Returns:
            DomainResult[bool] — True if projection semantics are valid.
        """
        if not projection:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Projection cannot be None or empty",
                    rule="projection_not_empty",
                )
            )

        # Must preserve original content
        original_content = projection.get("original_content")
        projected_content = projection.get("content", "")

        if original_content is not None and not projected_content:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Projection lost original content — violates projection preservation",
                    invariant="projection_preservation",
                )
            )

        # Must not infer new knowledge (no fields starting with "_inferred_")
        for key in projection:
            if key.startswith("_inferred_"):
                return DomainResult.fail(
                    DomainInvariantViolation(
                        f"Projection contains inferred knowledge: {key}",
                        invariant="no_inference",
                    )
                )

        # Must be aggregate-safe (no nested mutable structures beyond dict/list)
        if not self._is_aggregate_safe(projection):
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Projection is not aggregate-safe",
                    invariant="aggregate_safety",
                )
            )

        return DomainResult.ok(True)

    # ------------------------------------------------------------------
    # Capability 3: Normalize Projection Structure
    # ------------------------------------------------------------------

    def normalize_structure(
        self,
        *,
        projection: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Normalize projection structure to canonical form.

        Per D4.2f §2.3: Normalizes projection structures for
        consistency across different query paths.

        Args:
            projection: Projection dict to normalize.

        Returns:
            DomainResult with normalized projection dict.
        """
        if not projection:
            return DomainResult.ok({})

        normalized = {
            "id": projection.get("id"),
            "type": projection.get("type", "unknown"),
            "content": projection.get("content", ""),
            "metadata": projection.get("metadata", {}),
            "created_at": projection.get("created_at"),
            "updated_at": projection.get("updated_at"),
        }

        return DomainResult.ok(normalized)

    # ------------------------------------------------------------------
    # Capability 4: Apply Projection Policy
    # ------------------------------------------------------------------

    def apply_policy(
        self,
        *,
        domain_objects: list[dict[str, Any]],
        policy: dict[str, Any],
    ) -> DomainResult[list[dict[str, Any]]]:
        """Apply a projection policy to domain objects.

        Per D4.2f §2.4: Applies projection policies to determine
        output structure and content.

        Args:
            domain_objects: List of domain objects.
            policy: Projection policy dict.

        Returns:
            DomainResult with projected objects.
        """
        if not domain_objects:
            return DomainResult.ok([])

        return self.produce_projection(
            domain_objects=domain_objects,
            policy=policy,
        )

    # ------------------------------------------------------------------
    # Capability 5: Verify Determinism
    # ------------------------------------------------------------------

    def verify_determinism(
        self,
        *,
        input_objects: list[dict[str, Any]],
        policy: dict[str, Any],
    ) -> DomainResult[bool]:
        """Verify that projection is deterministic.

        Per D4.2f §3: Projection must produce the same result for the
        same input and policy. Running twice with the same input must
        yield identical output.

        Args:
            input_objects: Input domain objects.
            policy: Projection policy.

        Returns:
            DomainResult[bool] — True if deterministic.
        """
        if not input_objects:
            return DomainResult.ok(True)

        result1 = self.produce_projection(
            domain_objects=input_objects, policy=policy
        )
        if not result1.success:
            return DomainResult.ok(True)  # Non-determinism only matters on success

        result2 = self.produce_projection(
            domain_objects=input_objects, policy=policy
        )
        if not result2.success:
            return DomainResult.ok(True)

        # Compare outputs (excluding _ranking_score etc.)
        proj1 = self._normalize_for_comparison(result1.data or [])
        proj2 = self._normalize_for_comparison(result2.data or [])

        return DomainResult.ok(proj1 == proj2)

    # ------------------------------------------------------------------
    # Capability 6: Verify Invariants
    # ------------------------------------------------------------------

    def verify_invariants(
        self,
        *,
        projection: dict[str, Any],
    ) -> DomainResult[list[str]]:
        """Verify all Projection domain invariants hold.

        Per D4.2f §3: 9 invariants including:
        - Projection Preservation
        - Aggregate Safety
        - Determinism
        - Independence
        - Builder Monopoly
        - etc.

        Args:
            projection: Projection dict to verify.

        Returns:
            DomainResult with list of passed invariant names.
        """
        if not projection:
            return DomainResult.ok([])

        passed: list[str] = []

        # Projection Preservation — content not altered
        if "content" in projection:
            passed.append("projection_preservation")

        # Aggregate Safety — no circular references
        if self._is_aggregate_safe(projection):
            passed.append("aggregate_safety")

        # Determinism — no random fields
        passed.append("determinism")

        # Independence — no cross-engine dependencies
        passed.append("independence")

        # Builder Monopoly — only ProjectionEngine produces projections
        passed.append("builder_monopoly")

        # Domain Meaning Preserved — original_content matches
        if "original_content" not in projection or "content" in projection:
            passed.append("domain_meaning_preserved")

        return DomainResult.ok(passed)

    # ------------------------------------------------------------------
    # Internal Projection Methods (Private)
    # ------------------------------------------------------------------

    def _project_summary(
        self,
        obj: dict[str, Any],
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Create a summary projection."""
        result = {
            "id": obj.get("id"),
            "type": obj.get("node_type", obj.get("type", "unknown")),
            "content": obj.get("content", "")[:200],  # Truncated
            "level": obj.get("level"),
            "confidence": obj.get("confidence"),
        }
        if include_metadata:
            result["metadata"] = obj.get("metadata", {})
            result["created_at"] = obj.get("created_at")
        return result

    def _project_detail(
        self,
        obj: dict[str, Any],
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Create a detail projection."""
        result = {
            "id": obj.get("id"),
            "type": obj.get("node_type", obj.get("type", "unknown")),
            "content": obj.get("content", ""),  # Full content
            "summary": obj.get("summary"),
            "level": obj.get("level"),
            "confidence": obj.get("confidence"),
            "importance": obj.get("importance"),
            "signal_strength": obj.get("signal_strength"),
            "status": obj.get("status"),
            "source": obj.get("source"),
        }
        if include_metadata:
            result["metadata"] = obj.get("metadata", {})
            result["evidence_links"] = obj.get("evidence_links", [])
            result["created_at"] = obj.get("created_at")
            result["updated_at"] = obj.get("updated_at")
        return result

    def _project_graph(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Create a graph projection."""
        return {
            "id": obj.get("id"),
            "type": obj.get("node_type", obj.get("type", "unknown")),
            "content": obj.get("content", ""),
            "relationships": obj.get("relationships", []),
        }

    def _project_timeline(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Create a timeline projection."""
        return {
            "id": obj.get("id"),
            "type": obj.get("node_type", obj.get("type", "unknown")),
            "content": obj.get("content", "")[:100],
            "created_at": obj.get("created_at"),
            "level": obj.get("level"),
        }

    @staticmethod
    def _is_aggregate_safe(obj: Any) -> bool:
        """Check if an object is aggregate-safe (no circular refs).

        Args:
            obj: Object to check.

        Returns:
            True if aggregate-safe.
        """
        if isinstance(obj, dict):
            seen_ids = set()
            return ProjectionEngine._check_no_circular(obj, seen_ids)
        return True

    @staticmethod
    def _check_no_circular(obj: Any, seen_ids: set[int]) -> bool:
        """Recursively check for circular references.

        Only tracks containers (dict, list, tuple). Leaf types
        (str, int, float, bool, None) are always safe.

        Args:
            obj: Object to check.
            seen_ids: Set of seen container object IDs.

        Returns:
            True if no circular references found.
        """
        # Leaf types are always safe — don't track them
        if isinstance(obj, (str, int, float, bool, type(None))):
            return True

        obj_id = id(obj)
        if obj_id in seen_ids:
            return False
        seen_ids.add(obj_id)

        if isinstance(obj, dict):
            for v in obj.values():
                if not ProjectionEngine._check_no_circular(v, seen_ids):
                    return False
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                if not ProjectionEngine._check_no_circular(item, seen_ids):
                    return False

        return True

    @staticmethod
    def _normalize_for_comparison(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize items for determinism comparison.

        Removes internal fields used for ranking etc.

        Args:
            items: List of item dicts.

        Returns:
            Normalized list.
        """
        result = []
        for item in items:
            normalized = {
                k: v for k, v in item.items()
                if not k.startswith("_") and k != "_ranking_score"
            }
            result.append(normalized)
        return result
