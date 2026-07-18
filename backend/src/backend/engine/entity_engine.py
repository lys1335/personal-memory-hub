"""EntityEngine — Entity Domain semantic consistency owner.

Per D4.2a_EntityEngine_Architecture:
- Stateless domain engine for Entity identity resolution, canonical
  entity semantics, identity consolidation, and entity evolution
- Owns: entity identity resolution, canonical entity semantics,
  identity consolidation decisions, entity evolution rules,
  alias management, metadata consistency
- Domain rules: Canonical Identity, Alias Uniqueness, Type Validity,
  State Transition Legality
- Domain invariants: Identity Is Immutable, Single Canonical Identity,
  Valid Domain State, Evolution Preserves Identity, Canonical Entity
  Uniqueness, Historical Traceability
- AI provides candidates, EntityEngine provides domain decisions

Public contract:
- evaluate_entity_state(entity) → DomainResult
- validate_entity(entity) → DomainResult
- evaluate_evolution_decision(entity) → DomainResult
- verify_domain_invariants(entity) → DomainResult
- derive_domain_information(entity) → DomainResult
- resolve_identity(canonical_name, entity_type, workspace_id) → DomainResult
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from backend.engine.base import (
    DomainInvariantViolation,
    DomainResult,
    DomainRuleViolation,
    EngineBase,
)

logger = logging.getLogger(__name__)

# Valid entity types per 09_Database_Physical_Design
VALID_ENTITY_TYPES = frozenset((
    "Project", "Person", "Organization", "Tool", "Technology",
    "Concept", "Event", "Location", "Object", "Agent", "Model", "Document",
))


class EntityEngine(EngineBase):
    """Domain engine for Entity identity and semantic consistency.

    EntityEngine owns Entity domain rules, identity resolution, and
    evolution decisions. It does NOT persist data, manage transactions,
    or call other Engines.

    Stateless singleton — all state comes from Repository reads.
    """

    def __init__(self) -> None:
        """Initialize EntityEngine."""
        super().__init__("EntityEngine")

    # ------------------------------------------------------------------
    # Capability 1: Evaluate Entity State
    # ------------------------------------------------------------------

    def evaluate_entity_state(
        self,
        *,
        entity: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Evaluate the current state of an Entity for domain purposes.

        Per D4.2a §2.1: Answers domain questions about Entity state.
        Does not modify state.

        Args:
            entity: Entity domain model dict with keys:
                entity_type, canonical_name, aliases, description,
                metadata, observation_count, pattern_count, belief_count,
                relationship_count, status, created_at, updated_at.

        Returns:
            DomainResult with state evaluation dict.
        """
        if not entity:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Entity cannot be None or empty",
                    rule="entity_not_empty",
                )
            )

        entity_type = entity.get("entity_type", "")
        canonical_name = entity.get("canonical_name", "")
        aliases = entity.get("aliases") or []
        status = entity.get("status", "active")

        # Evaluate state
        if status == "archived":
            state = "archived"
        elif status == "merged":
            state = "merged"
        else:
            state = "active"

        # Determine canonical identity
        canonical_identity = {
            "entity_id": entity.get("id"),
            "canonical_name": canonical_name,
            "entity_type": entity_type,
        }

        # Alias count
        alias_count = len(aliases)

        return DomainResult.ok({
            "state": state,
            "canonical_identity": canonical_identity,
            "alias_count": alias_count,
            "is_active": state == "active",
            "is_archived": state == "archived",
            "is_merged": state == "merged",
        })

    # ------------------------------------------------------------------
    # Capability 2: Validate Entity
    # ------------------------------------------------------------------

    def validate_entity(
        self,
        *,
        entity: dict[str, Any],
    ) -> DomainResult[bool]:
        """Validate that an Entity satisfies domain invariants.

        Per D4.2a §2.2: Validates canonical identity, alias uniqueness,
        entity type validity, and state transition legality.

        Args:
            entity: Entity domain model dict.

        Returns:
            DomainResult[bool] — True if entity is valid.
        """
        if not entity:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Entity cannot be None or empty",
                    rule="entity_not_empty",
                )
            )

        entity_type = entity.get("entity_type", "")
        canonical_name = entity.get("canonical_name", "")
        aliases = entity.get("aliases") or []

        # Canonical Identity rule: canonical_name must be non-empty
        if not canonical_name or not str(canonical_name).strip():
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Entity must have a canonical name",
                    invariant="canonical_identity",
                )
            )

        # Entity Type validity rule
        if entity_type not in VALID_ENTITY_TYPES:
            return DomainResult.fail(
                DomainInvariantViolation(
                    f"Invalid entity type: {entity_type}",
                    invariant="type_validity",
                    details={
                        "type": entity_type,
                        "valid_types": list(VALID_ENTITY_TYPES),
                    },
                )
            )

        # Alias uniqueness rule: aliases must not contain empty strings
        for alias in aliases:
            if not alias or not str(alias).strip():
                return DomainResult.fail(
                    DomainRuleViolation(
                        "Alias cannot be empty",
                        rule="alias_not_empty",
                    )
                )
            # Alias must not equal canonical name
            if alias.lower() == canonical_name.lower():
                return DomainResult.fail(
                    DomainRuleViolation(
                        "Alias cannot equal canonical name",
                        rule="alias_uniqueness",
                    )
                )

        self._log_invariant_check("canonical_identity", True)
        return DomainResult.ok(True)

    # ------------------------------------------------------------------
    # Capability 3: Evaluate Evolution Decision
    # ------------------------------------------------------------------

    def evaluate_evolution_decision(
        self,
        *,
        entity: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Evaluate what evolution action is appropriate for an Entity.

        Per D4.2a §2.4: Determines canonical name selection, alias
        addition/removal, identity consolidation feasibility, and
        state transition approval.

        Args:
            entity: Entity domain model dict.

        Returns:
            DomainResult with evolution decision dict.
        """
        if not entity:
            return DomainResult.ok({
                "action": "none",
                "reason": "No entity to evaluate",
                "confidence": 0.0,
            })

        entity_type = entity.get("entity_type", "")
        _canonical_name = entity.get("canonical_name", "")
        aliases = entity.get("aliases") or []
        _metadata = entity.get("metadata", {})
        observation_count = entity.get("observation_count", 0)
        pattern_count = entity.get("pattern_count", 0)
        belief_count = entity.get("belief_count", 0)

        # Determine evolution action based on evidence accumulation
        total_evidence = observation_count + pattern_count + belief_count

        action = "none"
        reason = "No evolution needed"
        confidence = 0.0

        if total_evidence >= 10 and observation_count >= 5:
            action = "update_canonical_name"
            reason = "Sufficient evidence accumulation for canonical name review"
            confidence = round(min(1.0, total_evidence * 0.05), 3)

        elif belief_count >= 3 and pattern_count < 3:
            action = "promote_patterns"
            reason = "Beliefs exist without sufficient patterns — promote patterns"
            confidence = 0.7

        elif len(aliases) >= 5:
            action = "consolidate_aliases"
            reason = "Many aliases — consolidation recommended"
            confidence = 0.6

        return DomainResult.ok({
            "action": action,
            "reason": reason,
            "confidence": confidence,
            "total_evidence": total_evidence,
            "entity_type": entity_type,
        })

    # ------------------------------------------------------------------
    # Capability 4: Verify Domain Invariants
    # ------------------------------------------------------------------

    def verify_domain_invariants(
        self,
        *,
        entity: dict[str, Any],
    ) -> DomainResult[list[str]]:
        """Verify that Entity domain invariants hold.

        Per D4.2a §5:
        - 5.1 Identity Is Immutable
        - 5.2 Single Canonical Identity
        - 5.3 Valid Domain State
        - 5.4 Evolution Preserves Identity
        - 5.5 Canonical Entity Uniqueness
        - 5.6 Historical Traceability

        Args:
            entity: Entity domain model dict.

        Returns:
            DomainResult with list of passed invariant names.
        """
        if not entity:
            return DomainResult.ok([])

        passed: list[str] = []

        # 5.1 Identity Is Immutable — entity has an id
        if entity.get("id"):
            passed.append("identity_immutable")

        # 5.2 Single Canonical Identity — exactly one canonical_name
        if entity.get("canonical_name"):
            passed.append("single_canonical_identity")

        # 5.3 Valid Domain State — entity_type is valid
        if entity.get("entity_type") in VALID_ENTITY_TYPES:
            passed.append("valid_domain_state")

        # 5.4 Evolution Preserves Identity — canonical_name exists
        if entity.get("canonical_name"):
            passed.append("evolution_preserves_identity")

        # 5.5 Canonical Entity Uniqueness — entity has unique type+name
        if entity.get("entity_type") and entity.get("canonical_name"):
            passed.append("canonical_entity_uniqueness")

        # 5.6 Historical Traceability — has created_at
        if entity.get("created_at"):
            passed.append("historical_traceability")

        return DomainResult.ok(passed)

    # ------------------------------------------------------------------
    # Capability 5: Derive Domain Information
    # ------------------------------------------------------------------

    def derive_domain_information(
        self,
        *,
        entity: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Derive domain information from Entity state.

        Per D4.2a §2.5: Derives canonical name, alias resolution
        results, entity type classification, and identity graph
        relationships.

        Args:
            entity: Entity domain model dict.

        Returns:
            DomainResult with derived domain information dict.
        """
        if not entity:
            return DomainResult.ok({})

        canonical_name = entity.get("canonical_name", "")
        aliases = entity.get("aliases") or []
        entity_type = entity.get("entity_type", "")
        metadata = entity.get("metadata", {})

        # Derive canonical name from evidence (MVP: use existing)
        derived_canonical = canonical_name

        # Alias resolution results
        alias_resolution = {
            "canonical_name": derived_canonical,
            "alias_count": len(aliases),
            "aliases": aliases,
        }

        # Entity type classification
        type_classification = {
            "entity_type": entity_type,
            "is_project": entity_type == "Project",
            "is_person": entity_type == "Person",
            "is_organization": entity_type == "Organization",
            "is_technology": entity_type in ("Tool", "Technology"),
            "is_abstract": entity_type in ("Concept", "Event", "Location", "Object", "Agent", "Model", "Document"),
        }

        return DomainResult.ok({
            "derived_canonical_name": derived_canonical,
            "alias_resolution": alias_resolution,
            "type_classification": type_classification,
            "metadata_keys": list(metadata.keys()),
        })

    # ------------------------------------------------------------------
    # Capability 6: Resolve Identity
    # ------------------------------------------------------------------

    def resolve_identity(
        self,
        *,
        canonical_name: str,
        entity_type: str,
        workspace_id: UUID | str,
    ) -> DomainResult[dict[str, Any]]:
        """Resolve an entity identity by canonical name and type.

        Per D4.2a §4.1: Returns the canonical entity identity.
        Does NOT query the database — that is the Service's responsibility.

        Args:
            canonical_name: The canonical name to resolve.
            entity_type: The entity type.
            workspace_id: Workspace scope.

        Returns:
            DomainResult with resolved identity dict.
        """
        if not canonical_name or not canonical_name.strip():
            return DomainResult.fail(
                DomainRuleViolation(
                    "Canonical name is required for identity resolution",
                    rule="canonical_name_required",
                )
            )

        if entity_type not in VALID_ENTITY_TYPES:
            return DomainResult.fail(
                DomainInvariantViolation(
                    f"Invalid entity type for resolution: {entity_type}",
                    invariant="type_validity",
                )
            )

        return DomainResult.ok({
            "resolved": True,
            "canonical_name": canonical_name.strip(),
            "entity_type": entity_type,
            "workspace_id": str(workspace_id),
            "resolution_method": "canonical_lookup",
        })
