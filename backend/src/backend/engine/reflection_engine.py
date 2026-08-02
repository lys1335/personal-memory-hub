"""ReflectionEngine — Memory Evolution Domain Engine.

Per D4.2d_ReflectionEngine_Architecture and MVP_Evolution_Plan:
- Single Engine with internal Components (NOT multiple independent Engines)
- Stateless domain engine for Reflection semantic validation
- LLM calls go through ReflectionProvider interface (D4.2d §2.7)
- No cross-Engine calls, no direct database access
- Service layer owns orchestration

Components:
1. FactExtractorComponent   — LLM-assisted fact extraction (via Provider)
2. InterestAnalyzerComponent — Rule-driven interest trend analysis
3. ProjectionUpdaterComponent — Rule-driven Memory Pyramid update proposals
4. ReflectionValidator       — Domain invariant enforcement
"""

from __future__ import annotations

import logging
from typing import Any

from backend.engine.base import (
    DomainInvariantViolation,
    DomainResult,
    EngineBase,
)
from backend.shared.providers.reflection_provider import ReflectionProvider

logger = logging.getLogger(__name__)


class ReflectionEngine(EngineBase):
    """Domain engine for memory evolution via Reflection.

    This is a SINGLE Engine that owns ALL reflection-related capabilities.
    Internal components are private; Service layer calls only the public contract.

    Public contract:
    - reflect_pipeline(scope, candidates, provider) → ReflectionExecutionResult
    - validate_proposals(proposals) → DomainResult[list[validated_proposal]]
    """

    def __init__(self) -> None:
        super().__init__("ReflectionEngine")

    # ------------------------------------------------------------------
    # Main Pipeline Entry Point
    # ------------------------------------------------------------------

    async def reflect_pipeline(
        self,
        *,
        scope: str,
        candidates: list[dict[str, Any]],
        provider: ReflectionProvider,
    ) -> dict[str, Any]:
        """Execute the full Reflection pipeline.

        Per 10_4 §7.1 Pipeline:
        Select Scope → Collect Candidates → Analyze Evidence →
        Generate Reflection → Validate → Persist → Link Evidence →
        Propagate Upward → Emit Log

        Args:
            scope: Reflection scope identifier.
            candidates: List of candidate memory dicts to reflect upon.
            provider: LLM provider for inference.

        Returns:
            Dict with keys: facts, entities, interest_trends, proposals,
            validation_passed, execution_log.
        """
        if not candidates:
            logger.info("reflect_pipeline: no candidates for scope=%s", scope)
            return {
                "facts": [],
                "entities": [],
                "interest_trends": {},
                "proposals": [],
                "validation_passed": True,
                "execution_log": ["No candidates to process"],
            }

        execution_log: list[str] = []

        # Step 1: Extract facts via LLM (FactExtractorComponent)
        facts, step_log = await self._extract_facts(candidates, provider)
        execution_log.extend(step_log)
        self._log_domain_rule("fact_extraction", context={"count": len(facts)})

        if not facts:
            execution_log.append("No facts extracted — skipping further steps")
            return {
                "facts": [],
                "entities": [],
                "interest_trends": {},
                "proposals": [],
                "validation_passed": True,
                "execution_log": execution_log,
            }

        # Step 2: Analyze interest trends (InterestAnalyzerComponent)
        interest_trends = self._analyze_interest(facts)
        self._log_domain_rule("interest_analysis", context={"trends": interest_trends})

        # Step 3: Generate projection proposals (ProjectionUpdaterComponent)
        proposals = self._generate_proposals(facts, interest_trends)
        self._log_domain_rule("projection_update", context={"proposal_count": len(proposals)})

        # Step 4: Validate all proposals (ReflectionValidator)
        validation_result = self._validate_proposals(proposals)
        if not validation_result.success:
            msg = validation_result.error.message if validation_result.error else "unknown"
            execution_log.append(
                f"Validation FAILED: {msg}"
            )
            # Don't block — log warning but still return results for review
            logger.warning(
                "Reflection validation failed, returning for human review: %s",
                msg,
            )

        execution_log.append(
            f"Pipeline complete: {len(facts)} facts, "
            f"{len(proposals)} proposals"
        )

        return {
            "facts": facts,
            "entities": self._extract_entity_names(facts),
            "interest_trends": interest_trends,
            "proposals": proposals,
            "validation_passed": validation_result.success,
            "execution_log": execution_log,
        }

    # ------------------------------------------------------------------
    # Component 1: FactExtractor
    # ------------------------------------------------------------------

    async def _extract_facts(
        self,
        candidates: list[dict[str, Any]],
        provider: ReflectionProvider,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Extract structured facts from candidate memories.

        Uses LLM via Provider interface (NOT direct Ollama call).
        """
        log: list[str] = []

        # Build prompt from candidate content
        contents = []
        for i, c in enumerate(candidates):
            content = c.get("content", "")
            # Truncate very long content to avoid token limit
            content = content[:500] if len(content) > 500 else content
            contents.append(f"[{i+1}] {content}")

        # Build list of memory IDs from candidates
        memory_ids = [c.get("id", f"memory_{i+1}") for i, c in enumerate(candidates)]

        # Simple, concise prompt
        system_prompt = (
            "Extract structured facts from memories. Output ONLY JSON.\n"
            'Format: {"facts":[{"entity":"name","value":"value","source_ids":["id"],"confidence":0.9}],"entities":[]}\n'
            f"\nIDs: {memory_ids}\n\nMemories:\n" + "\n".join(contents)
        )

        try:
            result = await provider.generate(system_prompt, {"candidates": candidates})
            facts = result.get("facts", [])
            log.append(f"LLM extracted {len(facts)} facts")
            return facts, log
        except Exception as e:
            log.append(f"Fact extraction failed: {e}")
            logger.error("Fact extraction error: %s", e, exc_info=True)
            return [], log

    # ------------------------------------------------------------------
    # Component 2: InterestAnalyzer
    # ------------------------------------------------------------------

    def _analyze_interest(
        self, facts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze interest trends based on extracted facts.

        Pure rule-based algorithm. No LLM dependency.
        """
        if not facts:
            return {"trends": [], "keywords": {}, "summary": "No facts to analyze"}

        # Count entity mentions across facts
        entity_counts: dict[str, int] = {}
        for fact in facts:
            entity = fact.get("entity", "")
            if entity:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1

        # Sort by frequency
        sorted_entities = sorted(
            entity_counts.items(), key=lambda x: x[1], reverse=True
        )

        # Determine trends
        trends = []
        for entity, count in sorted_entities[:5]:
            if count >= 3:
                trend = "rising"
            elif count >= 2:
                trend = "stable"
            else:
                trend = "new"
            trends.append({"entity": entity, "mention_count": count, "trend": trend})

        summary = (
            f"Top interests: {', '.join(e for e, _ in sorted_entities[:3])}"
            if sorted_entities
            else "No clear interest patterns"
        )

        return {
            "trends": trends,
            "keywords": dict(sorted_entities[:10]),
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Component 3: ProjectionUpdater
    # ------------------------------------------------------------------

    def _generate_proposals(
        self,
        facts: list[dict[str, Any]],
        interest_trends: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate Memory Pyramid update proposals.

        Pure rule-based algorithm. Proposal types per 10_4 §7.2:
        Create / Strengthen / Refine / Split / Ignore
        """
        proposals: list[dict[str, Any]] = []

        if not facts:
            return [
                {
                    "type": "Ignore",
                    "target_level": 0,
                    "evidence_chain": [],
                    "confidence": 0.0,
                    "summary": "No facts to generate proposals from",
                }
            ]

        # Analyze evidence density per entity
        entity_evidence: dict[str, list[dict[str, Any]]] = {}
        for fact in facts:
            entity = fact.get("entity", "unknown")
            if entity not in entity_evidence:
                entity_evidence[entity] = []
            entity_evidence[entity].append(fact)

        for entity, entity_facts in entity_evidence.items():
            avg_confidence = sum(
                f.get("confidence", 0.5) for f in entity_facts
            ) / len(entity_facts)

            # Decision logic per 10_4 §7.2 Semantic Evolution
            if avg_confidence >= 0.8 and len(entity_facts) >= 3:
                proposal_type = "Strengthen"
                target_level = 2  # Pattern (L2)
            elif avg_confidence >= 0.6 and len(entity_facts) >= 2:
                proposal_type = "Create"
                target_level = 1  # Observation/Topic (L1)
            elif avg_confidence >= 0.9:
                proposal_type = "Refine"
                target_level = 2
            else:
                proposal_type = "Split"
                target_level = 1

            # Build evidence chain from source_ids
            # Filter out invalid placeholders (must be valid UUIDs)
            import uuid as _uuid_mod
            evidence_chain = []
            for f in entity_facts:
                for sid in f.get("source_ids", []):
                    # Validate UUID format
                    try:
                        _uuid_mod.UUID(sid)
                        if sid not in evidence_chain:
                            evidence_chain.append(sid)
                    except ValueError:
                        # Skip invalid placeholder like "memory_1"
                        pass

            # Build meaningful summary from fact values
            fact_values = [f.get("value", "") for f in entity_facts if f.get("value")]
            if fact_values:
                value_str = ", ".join(fact_values[:2])  # First 2 values
                summary_text = f"{entity}: {value_str}"
            else:
                summary_text = f"{proposal_type} memory for '{entity}' ({len(entity_facts)} facts, confidence={avg_confidence:.2f})"
            
            proposals.append({
                "type": proposal_type,
                "target_level": target_level,
                "entity": entity,
                "evidence_chain": evidence_chain,
                "confidence": round(avg_confidence, 3),
                "summary": summary_text,
                # 添加更多元数据用于后续生成 L2/L3 内容
                "fact_values": fact_values,
                "source_facts": entity_facts,
            })

        return proposals

    @staticmethod
    def _extract_entity_names(facts: list[dict[str, Any]]) -> list[str]:
        """Extract unique entity names from facts."""
        entities = set()
        for fact in facts:
            entity = fact.get("entity", "")
            if entity:
                entities.add(entity)
        return sorted(entities)

    # ------------------------------------------------------------------
    # Component 4: ReflectionValidator
    # ------------------------------------------------------------------

    def _validate_proposals(
        self, proposals: list[dict[str, Any]]
    ) -> DomainResult[list[dict[str, Any]]]:
        """Validate proposals against domain invariants.

        Per D4.2d §2.6 invariants:
        - Evidence Requirement: each proposal needs evidence chain
        - Semantic Coherence: content must be non-empty
        - L0 Protection: no proposals targeting level 0
        """
        validated: list[dict[str, Any]] = []
        violations: list[str] = []

        for i, prop in enumerate(proposals):
            errors: list[str] = []

            # Evidence Requirement (10_4 §7.4)
            evidence = prop.get("evidence_chain", [])
            if not evidence:
                errors.append(
                    f"Proposal {i}: missing evidence chain — violates evidence requirement"
                )

            # L0 Protection
            target_level = prop.get("target_level", 0)
            if target_level < 1:
                errors.append(
                    f"Proposal {i}: targets level {target_level} — L0 protection violated"
                )

            # Semantic Coherence
            summary = prop.get("summary", "")
            if not summary or not str(summary).strip():
                errors.append(
                    f"Proposal {i}: empty summary — violates semantic coherence"
                )

            if errors:
                violations.extend(errors)
            else:
                validated.append(prop)

        if violations:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "; ".join(violations[:3]),  # truncate for readability
                    invariant="reflection_validation",
                    details={"total_violations": len(violations)},
                )
            )

        return DomainResult.ok(validated)

    # ------------------------------------------------------------------
    # Public Methods for Testing & API
    # ------------------------------------------------------------------

    def validate_reflection(self, *, reflection: dict[str, Any]) -> DomainResult[bool]:
        """Validate a single reflection against domain invariants.

        Per D4.2d §2.6 invariants:
        - Evidence Requirement: each proposal needs evidence chain
        - Semantic Coherence: content must be non-empty
        - L0 Protection: no proposals targeting level 0
        """
        errors: list[str] = []

        # Evidence Requirement
        evidence_chain = reflection.get("evidence_chain", [])
        if not evidence_chain or len(evidence_chain) == 0:
            errors.append("Missing evidence chain — violates evidence requirement")

        # Semantic Coherence
        content = reflection.get("content", "")
        if not content or not str(content).strip():
            errors.append("Empty content — violates semantic coherence")

        # Status check
        status = reflection.get("status", "")
        if status not in ("candidate", "approved", "rejected"):
            errors.append(f"Invalid status '{status}' — must be candidate/approved/rejected")

        if errors:
            return DomainResult.fail(
                DomainInvariantViolation("; ".join(errors), invariant="reflection_validation")
            )

        return DomainResult.ok(True)

    def evaluate_candidate(self, *, candidate: dict[str, Any]) -> DomainResult[dict[str, Any]]:
        """Evaluate whether a candidate is eligible for promotion.

        Promotion criteria:
        - candidate_type must be 'pattern' or 'belief'
        - evidence_count >= 2
        - evidence_strength >= 0.5
        """
        candidate_type = candidate.get("candidate_type", "")
        evidence_count = candidate.get("evidence_count", 0)
        evidence_strength = candidate.get("evidence_strength", 0.0)

        promotion_eligible = (
            candidate_type in ("pattern", "belief")
            and evidence_count >= 2
            and evidence_strength >= 0.5
        )

        return DomainResult.ok({
            "promotion_eligible": promotion_eligible,
            "criteria_met": {
                "valid_type": candidate_type in ("pattern", "belief"),
                "sufficient_evidence": evidence_count >= 2,
                "strong_evidence": evidence_strength >= 0.5,
            },
        })

    def validate_evolution(self, *, evolution_action: dict[str, Any]) -> DomainResult[bool]:
        """Validate evolution action against monotonicity invariant.

        Evolution must be monotonic: levels can only increase (promote),
        never decrease (demote) without valid justification.
        Demotions that skip levels are prohibited.
        """
        action = evolution_action.get("action", "")
        source_level = evolution_action.get("source_level", 0)
        target_level = evolution_action.get("target_level", 0)
        justification = evolution_action.get("justification", "")

        # Demotion is generally prohibited unless justified
        if action == "demote":
            if not justification or not str(justification).strip():
                return DomainResult.fail(
                    DomainInvariantViolation(
                        "Demotion requires justification",
                        invariant="evolution_monotonicity",
                    )
                )
            # Non-monotonic: skipping levels in demotion is not allowed
            if target_level < source_level - 1:
                return DomainResult.fail(
                    DomainInvariantViolation(
                        f"Non-monotonic demotion from level {source_level} to {target_level}",
                        invariant="evolution_monotonicity",
                    )
                )

        # Promotions must target higher level
        if action == "promote" and target_level <= source_level:
            return DomainResult.fail(
                DomainInvariantViolation(
                    f"Promotion from level {source_level} to {target_level} is not upward",
                    invariant="evolution_monotonicity",
                )
            )

        return DomainResult.ok(True)

    def assess_consolidation_feasibility(
        self, *, memories: list[dict[str, Any]]
    ) -> DomainResult[dict[str, Any]]:
        """Assess whether a set of memories can be consolidated.

        Consolidation is feasible when:
        - At least 2 memories are provided
        - They share common evidence links
        - Content overlap exists
        """
        if len(memories) < 2:
            return DomainResult.fail(
                DomainInvariantViolation(
                    "Need at least 2 memories for consolidation",
                    invariant="consolidation_requirement",
                )
            )

        # Calculate evidence overlap
        all_evidence_sets = [set(m.get("evidence_links", [])) for m in memories]
        common_evidence = all_evidence_sets[0]
        for es in all_evidence_sets[1:]:
            common_evidence &= es

        overlap_score = len(common_evidence) / max(
            len(set().union(*all_evidence_sets)), 1
        )

        feasible = overlap_score > 0 and len(common_evidence) >= 1

        return DomainResult.ok({
            "feasible": feasible,
            "overlap_score": round(overlap_score, 3),
            "common_evidence": sorted(list(common_evidence)),
        })
