"""EvidenceEvolutionEngine — Information Extraction Domain Engine.

Per D4.2g_EvidenceEvolutionEngine_Architecture and ADR-EvidenceEvolution-Split:
- Responsible for: Information Extraction (Evidence → Candidate)
- NOT responsible for: Reasoning, Proposal generation, Memory creation
- Stateless domain engine for Entity Extraction, Pattern Discovery,
  Evidence Aggregation, Evidence Chain Construction, Confidence Estimation
- LLM calls go through ReflectionProvider interface
- No cross-Engine calls, no direct database access
- Service layer owns orchestration

Migration Status (2026-08-05):
- Phase 1: Skeleton created (commit 0cac852)
- Phase 2: Extraction logic migrated from ReflectionEngine (this commit)
- Phase 3: Rule-based components to be added in subsequent commits
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.engine.base import EngineBase

logger = logging.getLogger(__name__)


@dataclass
class EvolutionResult:
    """Result of EvidenceEvolutionEngine.evolve() call.

    Per D4.2g §3.2:
    - candidates: List of candidate dicts ready for ReflectionEngine
    - entities: List of extracted entity names
    - execution_log: Processing log for debugging
    - statistics: count, confidence_distribution, etc.
    """

    candidates: list[dict[str, Any]] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    execution_log: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


class EvidenceEvolutionEngine(EngineBase):
    """Domain engine for Evidence → Candidate evolution (Information Extraction).

    Public contract per D4.2g:
    - evolve(*, evidence, provider) → EvolutionResult
    - extract_entities(content: str) → list[dict] (implemented)
    - discover_patterns(evidence_list: list[dict]) → list[dict] (stub)
    - aggregate_evidence(evidence_list: list[dict]) → dict (stub)
    - estimate_confidence(evidence_list: list[dict]) → float (stub)

    Current Implementation:
    - evolve() delegates to _extract_facts() for LLM-based extraction
    - Rules-based components (discover_patterns, etc.) to be added
    """

    def __init__(self) -> None:
        super().__init__("EvidenceEvolutionEngine")

    async def evolve(
        self,
        *,
        evidence: list[dict[str, Any]],
        provider: Any,  # ReflectionProvider type
    ) -> EvolutionResult:
        """Execute evidence evolution pipeline.

        Per D4.2g §3.1:
        - Input: List of evidence dicts with content, source, metadata
        - Output: EvolutionResult with candidates, entities, execution_log, statistics

        Pipeline:
        1. Extract entities and facts via LLM
        2. Discover patterns (rule-based, future)
        3. Aggregate evidence (rule-based, future)
        4. Estimate confidence (rule-based, future)
        5. Build candidates
        """
        if not evidence:
            logger.info("evolve: no evidence provided")
            return EvolutionResult(
                candidates=[],
                entities=[],
                execution_log=["No evidence to process"],
                statistics={"count": 0},
            )

        execution_log = [
            f"EvidenceEvolutionEngine.evolve() called with {len(evidence)} evidence items",
        ]

        # Step 1: LLM-based extraction
        facts, fact_log = await self._extract_facts(evidence, provider)
        execution_log.extend(fact_log)

        if not facts:
            execution_log.append("No facts extracted — returning empty result")
            return EvolutionResult(
                candidates=[],
                entities=[],
                execution_log=execution_log,
                statistics={"count": 0, "extracted": 0},
            )

        # Step 2: Rule-based pattern discovery (future implementation)
        patterns = self._discover_patterns(facts)
        execution_log.append(f"Discovered {len(patterns)} patterns")

        # Step 3: Rule-based evidence aggregation (future implementation)
        aggregated = self._aggregate_evidence(facts)
        execution_log.append(f"Aggregated into {len(aggregated)} groups")

        # Step 4: Rule-based confidence estimation (future implementation)
        confidence = self._estimate_confidence(facts)
        execution_log.append(f"Estimated confidence: {confidence:.3f}")

        # Step 5: Build candidates from extracted facts
        candidates = self._build_candidates(facts, evidence)
        entities = self._extract_entity_names(facts)

        execution_log.append(f"Built {len(candidates)} candidates from {len(facts)} facts")

        return EvolutionResult(
            candidates=candidates,
            entities=entities,
            execution_log=execution_log,
            statistics={
                "count": len(evidence),
                "extracted": len(facts),
                "patterns": len(patterns),
                "aggregated_groups": len(aggregated),
                "confidence": round(confidence, 3),
            },
        )

    # ------------------------------------------------------------------
    # LLM-based Extraction (migrated from ReflectionEngine)
    # ------------------------------------------------------------------

    async def _extract_facts(
        self,
        evidence: list[dict[str, Any]],
        provider: Any,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Extract structured facts from evidence items.

        Per D4.2g §7.2: Uses LLM via Provider interface.
        Migrated from ReflectionEngine._extract_facts().

        Args:
            evidence: List of evidence dicts with content, source, metadata
            provider: LLM provider for inference

        Returns:
            Tuple of (facts list, execution log)
        """
        log: list[str] = []

        # Build prompt from evidence content
        contents = []
        for i, e in enumerate(evidence):
            content = e.get("content", "")
            # Truncate very long content to avoid token limit
            content = content[:500] if len(content) > 500 else content
            evidence_id = e.get("id", f"evidence_{i+1}")
            contents.append(f"[{i+1}] ID:{evidence_id} | {content}")

        evidence_ids = [e.get("id", f"evidence_{i+1}") for i, e in enumerate(evidence)]

        # Extraction prompt per D4.2g §7.2
        system_prompt = (
            "你是一个信息提取专家。请从以下证据中提取结构化事实。\n"
            "要求：\n"
            "1. 只输出有效的JSON，不要有任何解释或Markdown\n"
            "2. JSON必须以{开头，以}结尾\n"
            "3. 不要包含```json```或```标记\n\n"
            '输出格式：{"facts":[{"entity":"实体名","value":"值","source_ids":["id"],"confidence":0.9}],"entities":[]}\n\n'
            f"Evidence IDs: {evidence_ids}\n\nEvidence Items:\n" + "\n".join(contents)
        )

        try:
            result = await provider.generate(system_prompt, {"evidence": evidence})
            facts = result.get("facts", [])
            log.append(f"LLM extracted {len(facts)} facts from {len(evidence)} evidence items")
            return facts, log
        except Exception as e:
            log.append(f"Fact extraction failed: {e}")
            logger.error("EvidenceEvolution fact extraction error: %s", e, exc_info=True)
            return [], log

    # ------------------------------------------------------------------
    # Rule-based Components (stub implementations)
    # ------------------------------------------------------------------

    def _discover_patterns(
        self, facts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Discover patterns across evidence items.

        Per D4.2g §4.2:
        - Semantic clustering of similar evidence
        - Frequency analysis of entity mentions
        - Cross-entity pattern identification
        - Pure rule-based algorithm (no LLM)

        TODO: Implement actual clustering logic
        """
        # Count entity occurrences
        entity_counts: dict[str, int] = {}
        for fact in facts:
            entity = fact.get("entity", "")
            if entity:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1

        # Simple pattern: entities mentioned multiple times
        patterns = []
        for entity, count in entity_counts.items():
            if count >= 2:
                patterns.append({
                    "entity": entity,
                    "pattern_type": "recurring",
                    "mention_count": count,
                    "confidence": min(0.9, 0.5 + count * 0.1),
                })

        return patterns

    def _aggregate_evidence(
        self, facts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Aggregate evidence for candidate formation.

        Per D4.2g §4.3:
        - Group evidence by entity/topic
        - Calculate aggregate confidence
        - Build evidence chains
        - Detect evidence conflicts
        - Pure rule-based algorithm (no LLM)

        TODO: Implement actual aggregation logic
        """
        # Group facts by entity
        grouped: dict[str, list[dict[str, Any]]] = {}
        for fact in facts:
            entity = fact.get("entity", "unknown")
            if entity not in grouped:
                grouped[entity] = []
            grouped[entity].append(fact)

        # Calculate aggregate metrics per group
        aggregated = {}
        for entity, entity_facts in grouped.items():
            avg_confidence = sum(
                f.get("confidence", 0.5) for f in entity_facts
            ) / len(entity_facts)

            # Collect all source IDs
            source_ids = []
            for f in entity_facts:
                source_ids.extend(f.get("source_ids", []))

            aggregated[entity] = {
                "entity": entity,
                "fact_count": len(entity_facts),
                "avg_confidence": round(avg_confidence, 3),
                "source_ids": list(set(source_ids)),  # Deduplicate
                "evidence_chain": source_ids,
            }

        return aggregated

    def _estimate_confidence(
        self, facts: list[dict[str, Any]]
    ) -> float:
        """Estimate confidence for evidence group.

        Per D4.2g §4.5:
        - Aggregate per-evidence confidence
        - Apply aggregation formula (weighted average)
        - Record confidence distribution
        - Pure rule-based algorithm (no LLM)
        """
        if not facts:
            return 0.0

        confidences = [f.get("confidence", 0.5) for f in facts]
        return sum(confidences) / len(confidences)

    def _build_candidates(
        self,
        facts: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build Candidate dicts from extracted facts.

        Per D4.2g §3.3:
        Each candidate represents a structured piece of information
        ready for ReflectionEngine processing.
        """
        candidates = []

        # Group facts by entity
        entity_facts: dict[str, list[dict[str, Any]]] = {}
        for fact in facts:
            entity = fact.get("entity", "unknown")
            if entity not in entity_facts:
                entity_facts[entity] = []
            entity_facts[entity].append(fact)

        # Build one candidate per entity group
        for entity, entity_facts_list in entity_facts.items():
            # Get source evidence IDs
            source_ids = []
            for f in entity_facts_list:
                source_ids.extend(f.get("source_ids", []))
            source_ids = list(set(source_ids))

            # Calculate aggregate confidence
            avg_confidence = sum(
                f.get("confidence", 0.5) for f in entity_facts_list
            ) / len(entity_facts_list)

            # Build candidate content
            values = [f.get("value", "") for f in entity_facts_list if f.get("value")]
            content = f"{entity}: {', '.join(values[:3])}" if values else entity

            candidate = {
                "entity": entity,
                "content": content,
                "evidence_chain": source_ids[:10],  # Limit chain length
                "evidence_count": len(source_ids),
                "confidence": round(avg_confidence, 3),
                "source_level": 1,  # Default for Evidence input
                "candidate_type": "pattern",
                "status": "candidate",
            }

            candidates.append(candidate)

        return candidates

    def _extract_entity_names(
        self, facts: list[dict[str, Any]]
    ) -> list[str]:
        """Extract unique entity names from facts.

        Per D4.2g §3.3:
        Returns list of distinct entity names found in facts.
        """
        entities = set()
        for fact in facts:
            entity = fact.get("entity", "")
            if entity:
                entities.add(entity)
        return sorted(entities)
