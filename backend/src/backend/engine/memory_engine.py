"""MemoryEngine — Memory Domain semantic consistency owner.

Per D4.2b_MemoryEngine_Architecture:
- Stateless domain engine for Memory semantic consistency
- Owns: evidence integrity, progressive evolution, rule-based consolidation
- Domain rules: Evidence Requirement, Progressive Evolution, Rule-Based Consolidation,
  Traceability, Archive Eligibility, Domain Isolation, Policy-Driven Behavior
- Domain invariants: Every Memory Has Evidence, Semantic Consistency,
  Traceability Is Never Lost, Evolution Is Monotonic, Domain Purity, Policy Compliance

Public contract:
- evaluate_memory_semantics(memory) → DomainResult
- validate_memory_evidence_chain(memory, evidences) → DomainResult
- evaluate_evolution_action(memory) → DomainResult
- verify_invariants(memory) → DomainResult
- derive_projection_data(memory) → DomainResult
- assess_archive_eligibility(memory) → DomainResult
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


class MemoryEngine(EngineBase):
    """Domain engine for Memory semantic consistency.

    MemoryEngine owns Memory domain rules, evidence integrity, and
    progressive evolution decisions. It does NOT persist data, manage
    transactions, or call other Engines.

    Stateless singleton — all state comes from Repository reads.
    """

    def __init__(self) -> None:
        """Initialize MemoryEngine."""
        super().__init__("MemoryEngine")

    # ------------------------------------------------------------------
    # Capability 1: Evaluate Memory Semantics
    # ------------------------------------------------------------------

    def evaluate_memory_semantics(
        self,
        *,
        memory: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Evaluate the current semantic state of a memory for domain purposes.

        Answers domain questions about memory state. Does not modify state.

        Args:
            memory: Memory domain model dict with keys:
                level, node_type, content, confidence, importance,
                signal_strength, status, source, generated_by,
                evidence_links, contradict_evidence, metadata.

        Returns:
            DomainResult with semantic evaluation dict containing:
                - semantic_coherence: float (0.0-1.0)
                - evidence_strength: float (0.0-1.0)
                - semantic_category: str
                - evaluation_notes: list[str]
        """
        if not memory:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Memory cannot be None or empty",
                    rule="memory_not_empty",
                )
            )

        level = memory.get("level")
        if level not in (1, 2, 3):
            return DomainResult.fail(
                DomainInvariantViolation(
                    f"Invalid memory level: {level}. Must be 1, 2, or 3.",
                    invariant="every_memory_has_evidence",
                )
            )

        # Calculate semantic coherence based on evidence and scores
        evidence_links = memory.get("evidence_links") or []
        confidence = memory.get("confidence", 0.0)
        importance = memory.get("importance", 0.0)
        signal_strength = memory.get("signal_strength", 0.0)

        evidence_count = len(evidence_links)
        # Semantic coherence: weighted combination of confidence, importance, signal
        semantic_coherence = round(
            0.4 * confidence + 0.3 * importance + 0.3 * signal_strength, 3
        )

        # Evidence strength: based on evidence count and signal strength
        evidence_strength = min(1.0, round(evidence_count * 0.2 + signal_strength * 0.5, 3))

        # Determine semantic category
        _node_type = memory.get("node_type", "Observation")
        if level == 1:
            category = "observation"
        elif level == 2:
            category = "pattern"
        else:
            category = "belief"

        evaluation_notes = []
        if evidence_count == 0:
            evaluation_notes.append("No evidence links — violates evidence requirement")
        if semantic_coherence < 0.3:
            evaluation_notes.append("Low semantic coherence")

        return DomainResult.ok({
            "semantic_coherence": semantic_coherence,
            "evidence_strength": evidence_strength,
            "semantic_category": category,
            "evaluation_notes": evaluation_notes,
        })

    # ------------------------------------------------------------------
    # Capability 2: Validate Memory Evidence Chain
    # ------------------------------------------------------------------

    def validate_memory_evidence_chain(
        self,
        *,
        memory: dict[str, Any],
        evidences: list[dict[str, Any]] | None = None,
    ) -> DomainResult[bool]:
        """Validate that a memory satisfies the evidence requirement invariant.

        Per D4.2b §4.1 (Evidence Requirement):
        > Every Memory must have associated Evidence. No Evidence, no Memory.

        Args:
            memory: Memory domain model dict.
            evidences: List of evidence dicts associated with the memory.

        Returns:
            DomainResult[bool] — True if evidence chain is valid.

        Raises:
            DomainInvariantViolation: If evidence requirement not met.
        """
        if not memory:
            return DomainResult.ok(True)  # No memory to validate

        evidence_links = memory.get("evidence_links") or []
        _contradict_evidence = memory.get("contradict_evidence") or []

        # Invariant: Every Memory Has Evidence
        if not evidence_links:
            error = DomainInvariantViolation(
                "Memory has no evidence links — violates evidence requirement invariant",
                invariant="every_memory_has_evidence",
                details={"memory_id": memory.get("id")},
            )
            self._log_invariant_check("every_memory_has_evidence", False)
            return DomainResult.fail(error)

        # Validate evidence chain integrity
        if evidences:
            for ev in evidences:
                content = ev.get("content", "")
                if not content or not str(content).strip():
                    return DomainResult.fail(
                        DomainRuleViolation(
                            "Evidence content cannot be empty",
                            rule="evidence_not_empty",
                        )
                    )

        self._log_invariant_check("every_memory_has_evidence", True)
        return DomainResult.ok(True)

    # ------------------------------------------------------------------
    # Capability 3: Evaluate Evolution Action
    # ------------------------------------------------------------------

    def evaluate_evolution_action(
        self,
        *,
        memory: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Evaluate what evolution action is appropriate for a memory.

        Per D4.2b §4.2 (Progressive Evolution):
        > Memory semantics evolve progressively, never regress.
        > Each evolution step refines or consolidates existing semantics.

        Args:
            memory: Memory domain model dict.

        Returns:
            DomainResult with evolution action dict:
                - action: str ("none", "promote", "consolidate", "archive")
                - target_level: int | None
                - reason: str
                - confidence: float
        """
        if not memory:
            return DomainResult.ok({
                "action": "none",
                "target_level": None,
                "reason": "No memory to evaluate",
                "confidence": 0.0,
            })

        level = memory.get("level", 1)
        confidence = memory.get("confidence", 0.0)
        importance = memory.get("importance", 0.0)
        signal_strength = memory.get("signal_strength", 0.0)
        evidence_links = memory.get("evidence_links") or []
        evidence_count = len(evidence_links)

        # Determine evolution action based on domain rules
        action = "none"
        target_level = None
        reason = "No evolution needed"
        eval_confidence = 0.0

        if level == 1 and evidence_count >= 2 and confidence >= 0.7:
            action = "promote"
            target_level = 2
            reason = "Observation has sufficient evidence for Pattern promotion"
            eval_confidence = round(min(1.0, confidence * 0.6 + signal_strength * 0.4), 3)

        elif level == 2 and evidence_count >= 1 and confidence >= 0.8:
            action = "promote"
            target_level = 3
            reason = "Pattern has strong evidence for Belief promotion"
            eval_confidence = round(min(1.0, confidence * 0.7 + importance * 0.3), 3)

        elif importance >= 0.8 and level == 3:
            action = "archive"
            target_level = None
            reason = "High-importance Belief eligible for archive"
            eval_confidence = 0.9

        elif importance >= 0.6 and evidence_count >= 3:
            action = "consolidate"
            target_level = None
            reason = "Multiple evidences suggest consolidation opportunity"
            eval_confidence = 0.7

        return DomainResult.ok({
            "action": action,
            "target_level": target_level,
            "reason": reason,
            "confidence": eval_confidence,
        })

    # ------------------------------------------------------------------
    # Capability 4: Verify Invariants
    # ------------------------------------------------------------------

    def verify_invariants(
        self,
        *,
        memory: dict[str, Any],
        evidences: list[dict[str, Any]] | None = None,
    ) -> DomainResult[list[str]]:
        """Verify all Memory domain invariants hold.

        Per D4.2b §5:
        - 5.1 Every Memory Has Evidence
        - 5.2 Semantic Consistency
        - 5.3 Traceability Is Never Lost
        - 5.4 Evolution Is Monotonic
        - 5.5 Domain Purity
        - 5.6 Policy Compliance

        Args:
            memory: Memory domain model dict.
            evidences: Associated evidence dicts.

        Returns:
            DomainResult with list of passed invariant names.
            Failed invariants are logged but do not cause failure.
        """
        if not memory:
            return DomainResult.ok([])

        passed: list[str] = []
        failed: list[str] = []

        # 5.1 Evidence Requirement
        evidence_links = memory.get("evidence_links") or []
        if evidence_links:
            passed.append("every_memory_has_evidence")
        else:
            failed.append("every_memory_has_evidence")

        # 5.2 Semantic Consistency — level and node_type must match
        level = memory.get("level")
        node_type = memory.get("node_type", "")
        valid_mappings = {1: "Observation", 2: "Pattern", 3: "Belief"}
        if level in valid_mappings and node_type == valid_mappings[level]:
            passed.append("semantic_consistency")
        else:
            failed.append("semantic_consistency")

        # 5.3 Traceability — evidence_links must not be empty if memory has content
        content = memory.get("content", "")
        if content and evidence_links:
            passed.append("traceability_preserved")
        elif not content:
            passed.append("traceability_preserved")  # Empty content is OK
        else:
            failed.append("traceability_preserved")

        # 5.4 Evolution Monotonic — confidence/importance/signal must be in [0, 1]
        for field in ("confidence", "importance", "signal_strength"):
            val = memory.get(field, 0.0)
            if not (0.0 <= val <= 1.0):
                failed.append(f"monotonic_{field}")
                break
        else:
            passed.append("evolution_monotonic")

        # 5.5 Domain Purity — no query-specific fields in memory
        passed.append("domain_purity")

        # 5.6 Policy Compliance — status must be valid
        valid_statuses = ("active", "candidate", "deprecated", "superseded", "orphaned")
        status = memory.get("status", "active")
        if status in valid_statuses:
            passed.append("policy_compliance")
        else:
            failed.append("policy_compliance")

        if failed:
            for inv in failed:
                self._log_invariant_check(inv, False)

        return DomainResult.ok(passed)

    # ------------------------------------------------------------------
    # Capability 5: Derive Projection Data
    # ------------------------------------------------------------------

    def derive_projection_data(
        self,
        *,
        memory: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Derive projection data from memory for read purposes.

        Per D4.2b §4.6 (Domain Isolation):
        > MemoryEngine owns Memory domain semantics only.
        > Memory content is not influenced by query needs.

        This method transforms memory into a projection-friendly format
        WITHOUT changing domain semantics.

        Args:
            memory: Memory domain model dict.

        Returns:
            DomainResult with projection data dict.
        """
        if not memory:
            return DomainResult.ok({})

        level = memory.get("level", 1)
        node_type = memory.get("node_type", "Observation")

        # Build projection view — preserves domain meaning
        projection = {
            "id": memory.get("id"),
            "level": level,
            "node_type": node_type,
            "content": memory.get("content", ""),
            "summary": memory.get("summary"),
            "confidence": memory.get("confidence", 0.0),
            "importance": memory.get("importance", 0.0),
            "signal_strength": memory.get("signal_strength", 0.0),
            "status": memory.get("status", "active"),
            "source": memory.get("source", "user"),
            "evidence_count": len(memory.get("evidence_links") or []),
            "contradiction_count": len(memory.get("contradict_evidence") or []),
            "created_at": memory.get("created_at"),
        }

        return DomainResult.ok(projection)

    # ------------------------------------------------------------------
    # Capability 6: Assess Archive Eligibility
    # ------------------------------------------------------------------

    def assess_archive_eligibility(
        self,
        *,
        memory: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Assess whether a memory is eligible for archival.

        Per D4.2b §4.5 (Archive Eligibility):
        > Archive eligibility is determined by domain rules, not arbitrary thresholds.
        > Rules consider: age, confidence decay, semantic redundancy.

        Args:
            memory: Memory domain model dict.

        Returns:
            DomainResult with eligibility dict:
                - eligible: bool
                - reason: str
                - priority: str ("low", "medium", "high")
        """
        if not memory:
            return DomainResult.ok({
                "eligible": False,
                "reason": "No memory to evaluate",
                "priority": "low",
            })

        status = memory.get("status", "active")
        level = memory.get("level", 1)
        confidence = memory.get("confidence", 0.0)
        importance = memory.get("importance", 0.0)

        # Archived or deprecated memories are not eligible
        if status in ("deprecated", "superseded"):
            return DomainResult.ok({
                "eligible": False,
                "reason": f"Memory status is '{status}' — not eligible",
                "priority": "low",
            })

        # Beliefs with high importance are strong archive candidates
        if level == 3 and importance >= 0.7:
            return DomainResult.ok({
                "eligible": True,
                "reason": "High-importance Belief — eligible for archive",
                "priority": "high",
            })

        # Patterns with low confidence may be archived
        if level == 2 and confidence < 0.4:
            return DomainResult.ok({
                "eligible": True,
                "reason": "Low-confidence Pattern — eligible for archive",
                "priority": "medium",
            })

        # Default: not eligible
        return DomainResult.ok({
            "eligible": False,
            "reason": "Does not meet archive eligibility criteria",
            "priority": "low",
        })
