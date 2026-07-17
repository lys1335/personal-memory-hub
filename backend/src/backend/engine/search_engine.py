"""SearchEngine — Discovery Domain semantic consistency owner.

Per D4.2e_SearchEngine_Architecture:
- Stateless domain engine for Search intent interpretation and
  candidate discovery
- Owns: search intent interpretation, discovery planning, candidate
  discovery, candidate validation, candidate filtering, candidate
  ranking policy, discovery domain consistency
- NOT a Query Engine — discovers Candidates, does NOT retrieve data
- Domain rules: Discovery ≠ Retrieval, Candidate-Centric Discovery
- Domain invariants: 8 invariants including discovery scope,
  candidate validation, ranking consistency

Public contract:
- interpret_intent(query) → DomainResult
- plan_discovery(query, scope) → DomainResult
- discover_candidates(query, scope) → DomainResult
- validate_candidate(candidate) → DomainResult
- rank_candidates(candidates) → DomainResult
- verify_invariants(discovery) → DomainResult
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


class SearchEngine(EngineBase):
    """Domain engine for Discovery semantics.

    SearchEngine owns Discovery semantics, candidate validation, and
    ranking policy. It discovers Candidates within defined Scope.
    It does NOT perform retrieval, SQL generation, vector search,
    or DTO assembly.

    Stateless singleton — all state comes from Repository reads.
    """

    def __init__(self) -> None:
        """Initialize SearchEngine."""
        super().__init__("SearchEngine")

    # ------------------------------------------------------------------
    # Capability 1: Interpret Search Intent
    # ------------------------------------------------------------------

    def interpret_intent(
        self,
        *,
        query: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Interpret search intent for domain purposes.

        Per D4.2e §2.1: Extracts semantic meaning, determines discovery
        scope, identifies candidate types, and establishes ranking
        priorities.

        Args:
            query: Query dict with keys:
                text (str), scope (str), filters (dict),
                ranking_preference (str).

        Returns:
            DomainResult with interpreted intent dict.
        """
        if not query:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Query cannot be None or empty",
                    rule="query_not_empty",
                )
            )

        text = query.get("text", "")
        scope = query.get("scope", "workspace")
        filters = query.get("filters") or {}
        ranking_pref = query.get("ranking_preference", "relevance")

        # Determine candidate types from query text
        candidate_types = self._infer_candidate_types(text)

        # Determine ranking approach
        ranking_approach = ranking_pref if ranking_pref in (
            "relevance", "recency", "importance", "confidence"
        ) else "relevance"

        return DomainResult.ok({
            "intent": "search",
            "scope": scope,
            "candidate_types": candidate_types,
            "ranking_approach": ranking_approach,
            "filter_count": len(filters),
            "has_text_query": bool(text and text.strip()),
        })

    # ------------------------------------------------------------------
    # Capability 2: Plan Discovery
    # ------------------------------------------------------------------

    def plan_discovery(
        self,
        *,
        query: dict[str, Any],
        scope: dict[str, Any],
    ) -> DomainResult[dict[str, Any]]:
        """Plan discovery strategy.

        Per D4.2e §2.2: Defines discovery boundaries, selects applicable
        discovery policies, establishes candidate validation criteria,
        and determines ranking approach.

        Args:
            query: Query dict (from interpret_intent).
            scope: Scope dict with keys: workspace_id, entity_id,
                level (int), status (str).

        Returns:
            DomainResult with discovery plan dict.
        """
        if not query or not scope:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Query and scope are required for discovery planning",
                    rule="discovery_requires_scope",
                )
            )

        intent = self.interpret_intent(query=query)
        if not intent.success:
            return DomainResult.fail(intent.error)

        intent_data = intent.data
        scope_level = scope.get("level")

        # Adjust discovery strategy based on scope
        strategy = "broad"
        if scope_level is not None:
            strategy = "targeted"
        if scope.get("entity_id"):
            strategy = "entity_specific"

        return DomainResult.ok({
            "strategy": strategy,
            "scope_level": scope_level,
            "candidate_types": intent_data.get("candidate_types", []),
            "ranking_approach": intent_data.get("ranking_approach", "relevance"),
            "validation_criteria": self._get_validation_criteria(strategy),
        })

    # ------------------------------------------------------------------
    # Capability 3: Discover Candidates
    # ------------------------------------------------------------------

    def discover_candidates(
        self,
        *,
        plan: dict[str, Any],
        available_items: list[dict[str, Any]],
    ) -> DomainResult[list[dict[str, Any]]]:
        """Discover candidates within defined scope.

        Per D4.2e §2.3: Discovers Candidates based on the discovery plan.
        Does NOT retrieve data — only identifies candidate scope.

        Args:
            plan: Discovery plan from plan_discovery().
            available_items: List of available domain items to discover from.

        Returns:
            DomainResult with list of discovered candidate dicts.
        """
        if not plan:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Discovery plan is required",
                    rule="discovery_plan_required",
                )
            )

        strategy = plan.get("strategy", "broad")
        candidate_types = plan.get("candidate_types", [])
        validation_criteria = plan.get("validation_criteria", {})

        # Filter available items based on strategy
        candidates = []
        for item in available_items:
            item_type = item.get("node_type", item.get("candidate_type", ""))
            if candidate_types and item_type not in candidate_types:
                continue
            # Apply validation criteria
            if self._passes_validation(item, validation_criteria):
                candidates.append(item)

        return DomainResult.ok(candidates)

    # ------------------------------------------------------------------
    # Capability 4: Validate Candidate
    # ------------------------------------------------------------------

    def validate_candidate(
        self,
        *,
        candidate: dict[str, Any],
    ) -> DomainResult[bool]:
        """Validate a candidate against discovery criteria.

        Per D4.2e §2.4: Validates candidate meets domain rules for
        inclusion in discovery results.

        Args:
            candidate: Candidate domain model dict.

        Returns:
            DomainResult[bool] — True if candidate is valid.
        """
        if not candidate:
            return DomainResult.fail(
                DomainRuleViolation(
                    "Candidate cannot be None or empty",
                    rule="candidate_not_empty",
                )
            )

        # Must have content
        content = candidate.get("content", "")
        if not content or not str(content).strip():
            return DomainResult.fail(
                DomainRuleViolation(
                    "Candidate content cannot be empty",
                    rule="candidate_content_required",
                )
            )

        # Must have a valid level
        level = candidate.get("level")
        if level not in (1, 2, 3):
            return DomainResult.fail(
                DomainInvariantViolation(
                    f"Invalid candidate level: {level}",
                    invariant="candidate_valid_level",
                )
            )

        # Must have evidence
        evidence_links = candidate.get("evidence_links") or []
        if not evidence_links:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Candidate has no evidence — violates evidence requirement",
                    invariant="candidate_evidence_required",
                )
            )

        return DomainResult.ok(True)

    # ------------------------------------------------------------------
    # Capability 5: Rank Candidates
    # ------------------------------------------------------------------

    def rank_candidates(
        self,
        *,
        candidates: list[dict[str, Any]],
        ranking_approach: str = "relevance",
    ) -> DomainResult[list[dict[str, Any]]]:
        """Rank discovered candidates.

        Per D4.2e §2.6: Applies ranking policy to order candidates.
        Ranking is deterministic and stateless.

        Args:
            candidates: List of candidate dicts.
            ranking_approach: Ranking strategy
                ("relevance", "recency", "importance", "confidence").

        Returns:
            DomainResult with ranked list of candidates.
        """
        if not candidates:
            return DomainResult.ok([])

        scored = []
        for c in candidates:
            score = self._calculate_ranking_score(c, ranking_approach)
            scored.append({**c, "_ranking_score": score})

        # Sort descending by score
        scored.sort(key=lambda x: x.get("_ranking_score", 0.0), reverse=True)

        return DomainResult.ok(scored)

    # ------------------------------------------------------------------
    # Capability 6: Verify Invariants
    # ------------------------------------------------------------------

    def verify_invariants(
        self,
        *,
        discovery: dict[str, Any],
    ) -> DomainResult[list[str]]:
        """Verify all Search domain invariants hold.

        Per D4.2e §3: 8 invariants including:
        - Discovery ≠ Retrieval
        - Candidate-Centric Discovery
        - Scope-Bounded Discovery
        - Deterministic Ranking
        - etc.

        Args:
            discovery: Discovery dict from plan_discovery().

        Returns:
            DomainResult with list of passed invariant names.
        """
        if not discovery:
            return DomainResult.ok([])

        passed: list[str] = []

        # Discovery ≠ Retrieval — discovery should not contain raw DB results
        if "raw_sql" not in discovery:
            passed.append("discovery_not_retrieval")

        # Candidate-Centric — discovery should produce candidates, not DTOs
        if "candidates" in discovery or "strategy" in discovery:
            passed.append("candidate_centric")

        # Scope-Bounded — discovery has a defined scope
        if "scope" in discovery:
            passed.append("scope_bounded")

        # Deterministic — ranking approach is specified
        if "ranking_approach" in discovery:
            passed.append("deterministic_ranking")

        return DomainResult.ok(passed)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _infer_candidate_types(self, text: str) -> list[str]:
        """Infer candidate types from query text.

        MVP: returns default types. Full implementation would use
        NLP to extract semantic types.

        Args:
            text: Query text.

        Returns:
            List of candidate type strings.
        """
        if not text or not text.strip():
            return []
        # Default: all types are candidates
        return ["Observation", "Pattern", "Belief"]

    def _get_validation_criteria(self, strategy: str) -> dict[str, Any]:
        """Get validation criteria based on discovery strategy.

        Args:
            strategy: Discovery strategy name.

        Returns:
            Validation criteria dict.
        """
        if strategy == "entity_specific":
            return {"min_evidence": 1, "min_confidence": 0.0}
        elif strategy == "targeted":
            return {"min_evidence": 1, "min_confidence": 0.3}
        else:
            return {"min_evidence": 0, "min_confidence": 0.0}

    def _passes_validation(
        self,
        item: dict[str, Any],
        criteria: dict[str, Any],
    ) -> bool:
        """Check if an item passes validation criteria.

        Args:
            item: Item to validate.
            criteria: Validation criteria dict.

        Returns:
            True if item passes.
        """
        evidence_count = len(item.get("evidence_links") or [])
        min_evidence = criteria.get("min_evidence", 0)
        if evidence_count < min_evidence:
            return False

        confidence = item.get("confidence", 0.0)
        min_confidence = criteria.get("min_confidence", 0.0)
        if confidence < min_confidence:
            return False

        return True

    def _calculate_ranking_score(
        self,
        candidate: dict[str, Any],
        approach: str,
    ) -> float:
        """Calculate ranking score for a candidate.

        Args:
            candidate: Candidate dict.
            approach: Ranking approach name.

        Returns:
            Score (higher = better).
        """
        confidence = candidate.get("confidence", 0.0)
        importance = candidate.get("importance", 0.0)
        signal = candidate.get("signal_strength", 0.0)
        evidence_count = len(candidate.get("evidence_links") or [])

        if approach == "relevance":
            return round(0.4 * confidence + 0.3 * importance + 0.3 * signal, 3)
        elif approach == "importance":
            return round(importance * 0.6 + signal * 0.4, 3)
        elif approach == "confidence":
            return round(confidence * 0.7 + signal * 0.3, 3)
        else:  # recency — use created_at if available
            return round(confidence * 0.5 + importance * 0.3 + signal * 0.2, 3)
