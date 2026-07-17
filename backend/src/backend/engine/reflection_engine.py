"""ReflectionEngine — Reflection Domain semantic consistency owner.

Per D4.2d_ReflectionEngine_Architecture:
- Stateless domain engine for Reflection semantic validation
- Owns: reflection semantic validation, candidate evaluation,
  knowledge evolution validation, reflection consistency,
  knowledge consolidation rules, reflection domain invariants
- Domain rules: Evidence Requirement, Semantic Coherence,
  Evolution Monotonicity, Traceability Preservation, Idempotency
- Domain invariants: Evidence Requirement, Semantic Coherence,
  Evolution Monotonicity, Traceability Preservation, Idempotency

Public contract:
- validate_reflection(reflection) → DomainResult
- evaluate_candidate(candidate) → DomainResult
- validate_evolution(evolution_action) → DomainResult
- verify_invariants(reflection) → DomainResult
- assess_consolidation_feasibility(memory) → DomainResult
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


class ReflectionEngine(EngineBase):
    """Domain engine for Reflection semantic consistency.

    ReflectionEngine owns Reflection domain rules, candidate evaluation,
    and knowledge evolution validation. It does NOT persist data, manage
    transactions, or call other Engines.

    Stateless singleton — all state comes from Repository reads.
    """

    def __init__(self) -> None:
        """Initialize ReflectionEngine."""
        super().__init__("ReflectionEngine")

    # ------------------------------------------------------------------
    # Capability 1: Validate Reflection
    # ------------------------------------------------------------------

    def validate_reflection(
        self,
        *,
        reflection: dict[str, Any],
    ) -> DomainResult[bool]:
        """Validate that a reflection satisfies domain invariants.

        Per D4.2d §2.1: Validates reflection candidate is semantically
        coherent, evidence chain is complete, and evolution follows
        domain rules.

        Args:
            reflection: Reflection domain model dict with keys:
                scope, candidate_type, content, evidence_chain,
                evidence_count, evidence_strength, status.

        Returns:
            DomainResult[bool] — True if reflection is valid.
        """
        if not reflection:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Reflection cannot be None or empty",
                    rule="reflection_not_empty",
                )
            )

        # Evidence requirement: evidence_chain must not be empty
        evidence_chain = reflection.get("evidence_chain") or []
        if not evidence_chain:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Reflection has no evidence chain — violates evidence requirement",
                    invariant="evidence_requirement",
                    details={"reflection_scope": reflection.get("scope")},
                )
            )

        # Evidence count must be >= 1
        evidence_count = reflection.get("evidence_count", 0)
        if evidence_count < 1:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Evidence count is 0 — violates evidence requirement",
                    invariant="evidence_requirement",
                )
            )

        # Evidence strength must be in [0, 1]
        evidence_strength = reflection.get("evidence_strength", 0.0)
        if not (0.0 <= evidence_strength <= 1.0):
            return DomainResult.fail(
                DomainRuleViolation(
                    f"Evidence strength must be 0.0-1.0, got {evidence_strength}",
                    rule="evidence_strength_range",
                )
            )

        self._log_invariant_check("evidence_requirement", True)
        return DomainResult.ok(True)

    # ------------------------------------------------------------------
    # Capability 2: Evaluate Candidate
    # ------------------------------------------------------------------

    def evaluate_candidate(
        self,
        *,
        candidate: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Evaluate a reflection candidate for domain purposes.

        Per D4.2d §2.2: Assesses candidate semantic quality, evidence
        strength, and knowledge evolution appropriateness.

        Args:
            candidate: Candidate domain model dict with keys:
                candidate_type, content, evidence_count,
                evidence_strength, evidence_chain, status.

        Returns:
            DomainResult with evaluation dict:
                - quality_score: float (0.0-1.0)
                - promotion_eligible: bool
                - consolidation_feasible: bool
                - evaluation_notes: list[str]
        """
        if not candidate:
            return DomainResult.ok({
                "quality_score": 0.0,
                "promotion_eligible": False,
                "consolidation_feasible": False,
                "evaluation_notes": ["No candidate to evaluate"],
            })

        candidate_type = candidate.get("candidate_type", "pattern")
        evidence_count = candidate.get("evidence_count", 0)
        evidence_strength = candidate.get("evidence_strength", 0.0)
        evidence_chain = candidate.get("evidence_chain") or []
        status = candidate.get("status", "candidate")

        # Quality score: weighted combination
        quality_score = round(
            min(1.0, evidence_strength * 0.6 + min(1.0, evidence_count * 0.1) * 0.4),
            3,
        )

        # Promotion eligibility: Pattern needs ≥2 evidences, Belief needs ≥1
        promotion_eligible = False
        if (candidate_type == "pattern" and evidence_count >= 2) or (candidate_type == "belief" and evidence_count >= 1):
            promotion_eligible = True

        # Consolidation feasibility: multiple candidates of same type
        consolidation_feasible = evidence_count >= 3

        evaluation_notes = []
        if not promotion_eligible:
            evaluation_notes.append(
                f"Not promotion-eligible: {candidate_type} with {evidence_count} evidence(s)"
            )
        if quality_score < 0.5:
            evaluation_notes.append("Low quality score — may need more evidence")

        return DomainResult.ok({
            "quality_score": quality_score,
            "promotion_eligible": promotion_eligible,
            "consolidation_feasible": consolidation_feasible,
            "evaluation_notes": evaluation_notes,
        })

    # ------------------------------------------------------------------
    # Capability 3: Validate Evolution
    # ------------------------------------------------------------------

    def validate_evolution(
        self,
        *,
        evolution_action: dict[str, Any],
    ) -> DomainResult[bool]:
        """Validate that a knowledge evolution action follows domain rules.

        Per D4.2d §2.3: Validates evolution follows the Knowledge
        Evolution Model, evidence requirements are satisfied, and
        semantic integrity is preserved.

        Args:
            evolution_action: Dict with keys:
                action (str), source_level (int), target_level (int),
                evidence_chain (list), justification (str).

        Returns:
            DomainResult[bool] — True if evolution is valid.
        """
        if not evolution_action:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Evolution action cannot be None or empty",
                    rule="evolution_not_empty",
                )
            )

        action = evolution_action.get("action")
        source_level = evolution_action.get("source_level")
        target_level = evolution_action.get("target_level")
        evidence_chain = evolution_action.get("evidence_chain") or []
        justification = evolution_action.get("justification", "")

        # Evolution must be upward (monotonic): level increases
        if source_level is not None and target_level is not None:
            if target_level <= source_level:
                return DomainResult.fail(
                    DomainInvariantViolation(
                        f"Evolution is not monotonic: {source_level} → {target_level}. "
                        f"Target level must exceed source level.",
                        invariant="evolution_monotonicity",
                    )
                )

        # Evidence chain must not be empty
        if not evidence_chain:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Evolution has no evidence chain — violates evidence requirement",
                    invariant="evidence_requirement",
                )
            )

        # Justification must be non-empty
        if not justification or not str(justification).strip():
            return DomainResult.fail(
                DomainRuleViolation(
                    "Evolution justification cannot be empty",
                    rule="evolution_justification_required",
                )
            )

        self._log_invariant_check("evolution_monotonicity", True)
        return DomainResult.ok(True)

    # ------------------------------------------------------------------
    # Capability 4: Verify Invariants
    # ------------------------------------------------------------------

    def verify_invariants(
        self,
        *,
        reflection: dict[str, Any],
    ) -> DomainResult[list[str]]:
        """Verify all Reflection domain invariants hold.

        Per D4.2d §2.6:
        - Evidence Requirement
        - Semantic Coherence
        - Evolution Monotonicity
        - Traceability Preservation
        - Idempotency

        Args:
            reflection: Reflection domain model dict.

        Returns:
            DomainResult with list of passed invariant names.
        """
        if not reflection:
            return DomainResult.ok([])

        passed: list[str] = []

        # Evidence Requirement
        if reflection.get("evidence_count", 0) >= 1:
            passed.append("evidence_requirement")

        # Semantic Coherence — content must be non-empty
        content = reflection.get("content", "")
        if content and str(content).strip():
            passed.append("semantic_coherence")

        # Evolution Monotonicity — if source/target present, target > source
        source = reflection.get("source_level")
        target = reflection.get("target_level")
        if source is not None and target is not None:
            if target > source:
                passed.append("evolution_monotonicity")
        else:
            passed.append("evolution_monotonicity")  # N/A

        # Traceability — evidence_chain must not be empty
        if reflection.get("evidence_chain"):
            passed.append("traceability_preserved")

        # Idempotency — reflection has a stable scope identifier
        if reflection.get("scope"):
            passed.append("idempotency")

        return DomainResult.ok(passed)

    # ------------------------------------------------------------------
    # Capability 5: Assess Consolidation Feasibility
    # ------------------------------------------------------------------

    def assess_consolidation_feasibility(
        self,
        *,
        memories: list[dict[str, Any]],
    ) -> DomainResult[dict[str, Any]]:
        """Assess whether a group of memories can be consolidated.

        Per D4.2d §2.5: Consolidation criteria must be met, evidence
        chain preserved, and semantic content not lost.

        Args:
            memories: List of memory dicts to evaluate for consolidation.

        Returns:
            DomainResult with consolidation assessment dict.
        """
        if len(memories) < 2:
            return DomainResult.ok({
                "feasible": False,
                "reason": "Need at least 2 memories for consolidation",
                "overlap_score": 0.0,
            })

        # Calculate overlap score based on evidence sharing
        all_evidence_ids: set[str] = set()
        for mem in memories:
            for link in mem.get("evidence_links") or []:
                all_evidence_ids.add(str(link))

        total_evidence = sum(
            len(mem.get("evidence_links") or []) for mem in memories
        )
        unique_evidence = len(all_evidence_ids)
        overlap_score = round(unique_evidence / total_evidence, 3) if total_evidence > 0 else 0.0

        feasible = overlap_score >= 0.5 and len(memories) >= 2

        return DomainResult.ok({
            "feasible": feasible,
            "reason": "Memories share significant evidence" if feasible else "Insufficient evidence overlap",
            "overlap_score": overlap_score,
            "memory_count": len(memories),
            "unique_evidence_count": unique_evidence,
        })
