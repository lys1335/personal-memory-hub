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
    DomainRuleViolation,
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
            execution_log.append(
                f"Validation FAILED: {validation_result.error.message}"
            )
            # Don't block — log warning but still return results for review
            logger.warning(
                "Reflection validation failed, returning for human review: %s",
                validation_result.error.message,
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
            source = c.get("source", "unknown")
            created = c.get("created_at", "")
            contents.append(f"[{i+1}] source={source} time={created} content={content}")

        prompt_text = "\n".join(contents)

        system_prompt = (
            "You are a Memory Evolution Fact Extractor for Personal Memory Hub.\n"
            "Analyze the following memories and extract structured facts.\n"
            "Output ONLY valid JSON with this structure:\n"
            "{\n"
            '  "facts": [{"entity": str, "relation": str, "timestamp": str, "confidence": float, "source_ids": [str]}, ...],\n'
            '  "entities": [str, ...]\n'
            "}\n"
            "Each fact should capture a new piece of knowledge about the user.\n"
            "confidence should be between 0.0 and 1.0."
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
        entity_evidence: dict[str, list[dict]] = {}
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
            evidence_chain = []
            for f in entity_facts:
                for sid in f.get("source_ids", []):
                    if sid not in evidence_chain:
                        evidence_chain.append(sid)

            proposals.append({
                "type": proposal_type,
                "target_level": target_level,
                "entity": entity,
                "evidence_chain": evidence_chain,
                "confidence": round(avg_confidence, 3),
                "summary": f"{proposal_type} memory for '{entity}' "
                           f"({len(entity_facts)} facts, confidence={avg_confidence:.2f})",
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
