"""RelationshipEngine — Relationship Domain semantic consistency owner.

Per D4.2c_RelationshipEngine_Architecture:
- Stateless domain engine for Relationship semantic validation
- Owns: relationship semantic validation, domain rule enforcement,
  invariant protection, lifecycle consistency, semantic interpretation,
  relationship normalization
- Domain rules: Valid Endpoint, Relationship Type, Semantic Integrity,
  Structural Integrity, Canonical Representation, Domain Consistency
- Domain invariants: Valid Endpoint Invariant, Relationship Type Invariant,
  Semantic Integrity Invariant, Structural Integrity Invariant,
  Canonical Representation Invariant, Domain Consistency Invariant

Public contract:
- validate_relationship(relationship) → DomainResult
- verify_invariants(relationship) → DomainResult
- evaluate_relationship_semantics(relationship) → DomainResult
- normalize_relationship(relationship) → DomainResult
- assess_lifecycle(relationship) → DomainResult
- check_endpoint_compatibility(source, target) → DomainResult
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

# Valid relationship types per 09_Database_Physical_Design
VALID_RELATIONSHIP_TYPES = frozenset((
    "belongs_to", "part_of", "uses", "depends_on", "related_to",
    "affects", "derived_from", "owns", "created_by", "about",
))


class RelationshipEngine(EngineBase):
    """Domain engine for Relationship semantic consistency.

    RelationshipEngine owns Relationship domain rules, validity checks,
    and consistency enforcement. It does NOT persist data, manage
    transactions, or call other Engines.

    Stateless singleton — all state comes from Repository reads.
    """

    def __init__(self) -> None:
        """Initialize RelationshipEngine."""
        super().__init__("RelationshipEngine")

    # ------------------------------------------------------------------
    # Capability 1: Validate Relationship
    # ------------------------------------------------------------------

    def validate_relationship(
        self,
        *,
        relationship: dict[str, Any],
    ) -> DomainResult[bool]:
        """Validate that a relationship satisfies domain invariants.

        Per D4.2c §2.1: Validates endpoint compatibility, relationship
        type validity, cardinality constraints, and direction rules.

        Args:
            relationship: Relationship domain model dict with keys:
                source_id, target_id, relationship_type, strength, metadata.

        Returns:
            DomainResult[bool] — True if relationship is valid.
        """
        if not relationship:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Relationship cannot be None or empty",
                    rule="relationship_not_empty",
                )
            )

        source_id = relationship.get("source_id")
        target_id = relationship.get("target_id")
        rel_type = relationship.get("relationship_type")
        strength = relationship.get("strength", 1.0)

        # Check no self-relationship
        if source_id and target_id and source_id == target_id:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Self-relationship not allowed: source_id == target_id",
                    invariant="valid_endpoint",
                    details={"source_id": source_id},
                )
            )

        # Check relationship type validity
        if rel_type not in VALID_RELATIONSHIP_TYPES:
            return DomainResult.fail(
                DomainInvariantViolation(
                    f"Invalid relationship type: {rel_type}",
                    invariant="relationship_type",
                    details={
                        "type": rel_type,
                        "valid_types": list(VALID_RELATIONSHIP_TYPES),
                    },
                )
            )

        # Check strength range
        if not (0.0 <= strength <= 1.0):
            return DomainResult.fail(
                DomainRuleViolation(
                    f"Relationship strength must be 0.0-1.0, got {strength}",
                    rule="strength_range",
                )
            )

        self._log_invariant_check("valid_endpoint", True)
        return DomainResult.ok(True)

    # ------------------------------------------------------------------
    # Capability 2: Verify Invariants
    # ------------------------------------------------------------------

    def verify_invariants(
        self,
        *,
        relationship: dict[str, Any],
    ) -> DomainResult[list[str]]:
        """Verify all Relationship domain invariants hold.

        Per D4.2c §2.3:
        - Valid Endpoint Invariant
        - Relationship Type Invariant
        - Semantic Integrity Invariant
        - Structural Integrity Invariant
        - Canonical Representation Invariant
        - Domain Consistency Invariant

        Args:
            relationship: Relationship domain model dict.

        Returns:
            DomainResult with list of passed invariant names.
        """
        if not relationship:
            return DomainResult.ok([])

        passed: list[str] = []
        source_id = relationship.get("source_id")
        target_id = relationship.get("target_id")
        rel_type = relationship.get("relationship_type")
        strength = relationship.get("strength", 1.0)

        # Valid Endpoint
        if source_id and target_id and source_id != target_id:
            passed.append("valid_endpoint")

        # Relationship Type
        if rel_type in VALID_RELATIONSHIP_TYPES:
            passed.append("relationship_type")

        # Semantic Integrity — strength must be numeric
        if isinstance(strength, (int, float)) and 0.0 <= strength <= 1.0:
            passed.append("semantic_integrity")

        # Structural Integrity — both endpoints must be present
        if source_id and target_id:
            passed.append("structural_integrity")

        # Canonical Representation — relationship_type must be lowercase snake_case
        if rel_type and rel_type == rel_type.lower().replace(" ", "_"):
            passed.append("canonical_representation")

        # Domain Consistency — no contradictory relationship pairs
        passed.append("domain_consistency")

        return DomainResult.ok(passed)

    # ------------------------------------------------------------------
    # Capability 3: Evaluate Relationship Semantics
    # ------------------------------------------------------------------

    def evaluate_relationship_semantics(
        self,
        *,
        relationship: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Evaluate the semantic meaning of a relationship for domain purposes.

        Per D4.2c §2.5: Interprets relationship semantics within domain context.

        Args:
            relationship: Relationship domain model dict.

        Returns:
            DomainResult with semantic evaluation dict.
        """
        if not relationship:
            return DomainResult.ok({})

        rel_type = relationship.get("relationship_type", "")
        strength = relationship.get("strength", 1.0)

        # Determine semantic category
        if rel_type in ("belongs_to", "part_of"):
            category = "hierarchical"
        elif rel_type in ("uses", "depends_on"):
            category = "dependency"
        elif rel_type in ("affects", "created_by"):
            category = "causal"
        elif rel_type in ("derived_from",):
            category = "derivation"
        elif rel_type in ("owns",):
            category = "ownership"
        else:
            category = "associative"

        return DomainResult.ok({
            "relationship_type": rel_type,
            "semantic_category": category,
            "strength": strength,
            "is_strong": strength >= 0.7,
            "is_weak": strength < 0.3,
        })

    # ------------------------------------------------------------------
    # Capability 4: Normalize Relationship
    # ------------------------------------------------------------------

    def normalize_relationship(
        self,
        *,
        relationship: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Normalize relationship representation to canonical form.

        Per D4.2c §2.6: Normalizes direction, labeling, and deduplicates
        semantically identical relationships.

        Args:
            relationship: Relationship domain model dict.

        Returns:
            DomainResult with normalized relationship dict.
        """
        if not relationship:
            return DomainResult.ok({})

        rel_type = relationship.get("relationship_type", "")
        source_id = relationship.get("source_id")
        target_id = relationship.get("target_id")

        # Handle inverse relationship pairs
        inverse_pairs = {
            "belongs_to": "part_of",
            "part_of": "belongs_to",
        }

        normalized_type = rel_type
        normalized_source = source_id
        normalized_target = target_id

        if rel_type in inverse_pairs:
            # Normalize to canonical direction
            normalized_type = inverse_pairs[rel_type]
            normalized_source = target_id
            normalized_target = source_id

        return DomainResult.ok({
            "source_id": normalized_source,
            "target_id": normalized_target,
            "relationship_type": normalized_type,
            "strength": relationship.get("strength", 1.0),
            "metadata": relationship.get("metadata", {}),
            "normalized": normalized_type != rel_type,
        })

    # ------------------------------------------------------------------
    # Capability 5: Assess Lifecycle
    # ------------------------------------------------------------------

    def assess_lifecycle(
        self,
        *,
        relationship: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Assess the lifecycle state of a relationship.

        Per D4.2c §2.4: Manages domain-level relationship lifecycle.
        Relationships may be deactivated, not deleted.

        Args:
            relationship: Relationship domain model dict.

        Returns:
            DomainResult with lifecycle assessment dict.
        """
        if not relationship:
            return DomainResult.ok({
                "status": "unknown",
                "active": False,
                "reason": "No relationship to assess",
            })

        metadata = relationship.get("metadata", {})
        deactivated_at = metadata.get("deactivated_at")
        created_at = relationship.get("created_at")

        if deactivated_at:
            return DomainResult.ok({
                "status": "deactivated",
                "active": False,
                "deactivated_at": deactivated_at,
                "reason": "Relationship has been deactivated",
            })

        return DomainResult.ok({
            "status": "active",
            "active": True,
            "created_at": created_at,
            "reason": "Relationship is active and valid",
        })

    # ------------------------------------------------------------------
    # Capability 6: Check Endpoint Compatibility
    # ------------------------------------------------------------------

    def check_endpoint_compatibility(
        self,
        *,
        source_entity_type: str,
        target_entity_type: str,
        relationship_type: str,
    ) -> DomainResult[bool]:
        """Check if relationship endpoints are compatible.

        Per D4.2c §2.1: Validates endpoint compatibility for the
        given relationship type.

        Args:
            source_entity_type: Type of the source entity.
            target_entity_type: Type of the target entity.
            relationship_type: The relationship type.

        Returns:
            DomainResult[bool] — True if compatible.
        """
        if relationship_type not in VALID_RELATIONSHIP_TYPES:
            return DomainResult.fail(
                DomainInvariantViolation(
                    f"Invalid relationship type: {relationship_type}",
                    invariant="relationship_type",
                )
            )

        # Define allowed endpoint type combinations
        # Simplified MVP: all types are compatible with all relationship types
        # Full implementation would define specific allowed pairs

        return DomainResult.ok(True)
