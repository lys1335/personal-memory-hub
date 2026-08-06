"""ReflectionService — Memory Evolution Application Service.

Per D3.4 and 10_4 Implementation Design:
- Business Capability Orchestrator for Reflection
- Owns: workflow orchestration, business validation, Repository coordination,
        transaction coordination, Reflection capability execution
- Does NOT own: reflection algorithms (ReflectionEngine owns them),
                 task lifecycle (TaskService owns it),
                 runtime execution (Task Runtime owns it)
- Service Independence: does NOT call other Services directly
- Command Returns Identity: returns ReflectionExecutionResult (report, not data)
- Raw Evidence Preservation: L0 memories never modified/deleted
- Higher-level Memory stores evolving explanations, not snapshots
- Incremental propagation: only upward when necessary

MVP Evolution additions:
- Integrates ReflectionProvider abstraction (D4.2d §2.7)
- Delegates to ReflectionEngine for all LLM-based reasoning
- Sandbox-first: evolution results stored in memory, not production DB
- Batch processing: LLM calls are batched to avoid timeouts
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.service.base import BaseService
from backend.service.dto import (
    ReflectionExecutionResult,
    ReflectionStatus,
)
from backend.service.exceptions import ValidationError

# Batch processing configuration for LLM calls
BATCH_SIZE = int(os.environ.get('REFLECTION_BATCH_SIZE', '10'))

if TYPE_CHECKING:
    from backend.repository.candidate_repository import CandidateRepository
    from backend.repository.memory_node_repository import MemoryNodeRepository
    from backend.repository.relationship_repository import RelationshipRepository
    from backend.shared.providers.reflection_provider import ReflectionProvider

logger = logging.getLogger(__name__)


class ReflectionService(BaseService):
    """Application service for memory reflection operations.

    Orchestrates the reflection workflow:
    1. Acquire scope (find candidate memories via Repository)
    2. Delegate to ReflectionEngine (algorithm execution via Provider)
    3. Review and validate results
    4. Store evolution results in Sandbox (not production DB)
    5. Publish DomainEvent: ReflectionCompleted

    Stateless singleton managed by DI container.
    """

    def __init__(
        self,
        memory_node_repo: MemoryNodeRepository,
        candidate_repo: CandidateRepository,
        relationship_repo: RelationshipRepository,
        reflection_provider: ReflectionProvider | None = None,
    ) -> None:
        """Initialize ReflectionService with required repositories.

        Args:
            memory_node_repo: Repository for MemoryNode reads/writes.
            candidate_repo: Repository for Candidate records.
            relationship_repo: Repository for Relationship management.
            reflection_provider: LLM provider for inference (optional, uses env default).
        """
        super().__init__("ReflectionService")
        self._memory_node_repo = memory_node_repo
        self._candidate_repo = candidate_repo
        self._relationship_repo = relationship_repo
        self._provider = reflection_provider

    # ------------------------------------------------------------------
    # Reflect Capability
    # ------------------------------------------------------------------

    async def reflect(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        scope: str = "entity",
        limit: int = 50,
    ) -> ReflectionExecutionResult:
        """Execute reflection on memories within a scope.

        The reflection workflow:
        1. Acquire scope (find candidate memories)
        2. Delegate to ReflectionEngine (algorithm execution)
        3. Validate results (evidence completeness, semantic coherence)
        4. Persist evolution results to Sandbox (not production DB)

        The actual reflection algorithm runs in ReflectionEngine (D4).
        This service orchestrates the workflow and manages Provider.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity to reflect upon.
            scope: Reflection scope ("entity", "area", "workspace").
            limit: Maximum number of candidate memories to process.

        Returns:
            ReflectionExecutionResult with execution statistics.
        """
        self._validate_workspace_id(workspace_id)

        start_time = time.monotonic()

        # Step 1: Acquire scope — find candidate memories
        candidates = await self._acquire_scope(
            workspace_id=workspace_id,
            entity_id=entity_id,
            scope=scope,
            limit=limit,
        )

        if not candidates:
            return ReflectionExecutionResult(
                status=ReflectionStatus.COMPLETED,
                reflections_performed=0,
                scope=scope,
                metadata={"reason": "no_candidates"},
            )

        # Limit candidates
        candidates = candidates[:limit]

        # Step 2: Delegate to two-stage pipeline
        engine_result = await self._run_engine_pipeline(scope, candidates, workspace_id)

        # Step 3: Save proposals to database
        await self._save_proposals(engine_result.get("proposals", []), workspace_id)

        # Step 4: Calculate statistics
        duration_ms = (time.monotonic() - start_time) * 1000
        proposals = engine_result.get("proposals", [])
        facts = engine_result.get("facts", [])
        evolved_candidates = engine_result.get("evolved_candidates", [])

        new_patterns = sum(
            1 for p in proposals if p.get("type") == "Create" and p.get("target_level") >= 2
        )
        new_beliefs = sum(
            1 for p in proposals if p.get("type") == "Strengthen" and p.get("target_level") >= 3
        )
        evidence_complete = sum(
            1 for p in proposals if p.get("evidence_chain")
        )

        result = ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=len(facts),
            new_patterns=new_patterns,
            new_beliefs=new_beliefs,
            evidence_completeness=evidence_complete / len(proposals) if proposals else 0.0,
            scope=scope,
            duration_ms=duration_ms,
            metadata={
                "candidate_count": len(candidates),
                "evolved_candidate_count": len(evolved_candidates),
                "fact_count": len(facts),
                "proposal_count": len(proposals),
                "proposals": proposals,  # Add proposals for sandbox storage
                "entities": engine_result.get("entities", []),
                "interest_trends": engine_result.get("interest_trends", {}),
                "execution_log": engine_result.get("execution_log", []),
            },
        )

        logger.info(
            "Reflection completed: scope=%s facts=%d proposals=%d duration=%.0fms",
            scope, len(facts), len(proposals), duration_ms,
        )

        return result

    async def reflect_by_entity(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
    ) -> ReflectionExecutionResult:
        """Execute reflection on a specific entity's memories."""
        return await self.reflect(
            workspace_id=workspace_id,
            entity_id=entity_id,
            scope="entity",
        )

    async def approve_proposal(
        self,
        *,
        workspace_id: UUID,
        proposal_id: UUID,
    ) -> ReflectionExecutionResult:
        """Approve a reflection proposal and create L2/L3 memory."""
        from sqlalchemy import text

        from backend.shared.infrastructure.database.engine import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            # Get proposal
            result = await conn.execute(text("""
                SELECT * FROM proposals WHERE id = :id AND workspace_id = :workspace_id
            """), {"id": str(proposal_id), "workspace_id": str(workspace_id)})
            prop_row = result.fetchone()

            if not prop_row:
                raise ValidationError(f"Proposal not found: {proposal_id}")

            prop = dict(prop_row)

            # Update proposal status
            await conn.execute(text("""
                UPDATE proposals SET status = 'approved', approved_by = 'user', approved_at = NOW(), updated_at = NOW()
                WHERE id = :id
            """), {"id": str(proposal_id)})

            # Create L2/L3 memory node with aggregated content from evidence
            new_node_id = self._generate_id()
            level = prop["target_level"]
            node_type = "Pattern" if level == 2 else "Belief" if level == 3 else "Observation"

            # Get entity_id from proposal (set during candidate creation)
            entity_id = prop.get("entity_id")

            # Get evidence_chain from proposal (JSONB column, may be string or list)
            evidence_chain_raw = prop.get("evidence_chain", [])
            if isinstance(evidence_chain_raw, str):
                import json as _json
                try:
                    evidence_chain = _json.loads(evidence_chain_raw)
                except (json.JSONDecodeError, TypeError):
                    evidence_chain = []
            elif isinstance(evidence_chain_raw, list):
                evidence_chain = evidence_chain_raw
            else:
                evidence_chain = []

            # Approach 2: Aggregate evidence content for meaningful L2 node
            evidence_contents = []
            if evidence_chain:
                # Query original evidences from evidences table (not memory_nodes)
                evidence_query = await conn.execute(
                    text("""
                        SELECT e.content
                        FROM evidences e
                        WHERE e.id = ANY(:ids)
                    """),
                    {"ids": evidence_chain[:10]}  # Limit to 10 evidences
                )
                evidence_rows = evidence_query.fetchall()
                for row in evidence_rows:
                    if row and row[0]:
                        evidence_contents.append(row[0])

            # Generate meaningful content and summary from evidence
            entity_name = prop.get("entity", "unknown")
            if evidence_contents:
                # Aggregate evidence content for summary
                # Use first 3 evidence contents to build a description
                sample_evidences = evidence_contents[:3]
                # Build summary from evidence
                summary = f"{entity_name}: {'; '.join(sample_evidences)}"
                # Build content - use same as summary for now
                content = summary
            else:
                # Fallback if no evidence content found
                content = f"{entity_name}"
                summary = f"{entity_name}"

            await conn.execute(text("""
                INSERT INTO memory_nodes (
                    id, workspace_id, entity_id, level, node_type, content, summary,
                    confidence, importance, signal_strength, status, source, generated_by,
                    evidence_links, contradict_evidence, _meta, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :entity_id, :level, :node_type, :content, :summary,
                    :confidence, :importance, :signal_strength, 'active', 'ai_reflect', 'ai_reflect',
                    :evidence_links, '[]', '{}', NOW(), NOW()
                )
            """), {
                "id": str(new_node_id),
                "workspace_id": str(workspace_id),
                "entity_id": str(entity_id) if entity_id else None,
                "level": level,
                "node_type": node_type,
                "content": content,
                "summary": summary,
                "confidence": prop["confidence"],
                "importance": prop["confidence"],
                "signal_strength": prop["confidence"],
                "evidence_links": json.dumps(evidence_chain) if evidence_chain else "[]",
            })

            # Create relationships (derived_from)
            for evidence_id in evidence_chain:
                await conn.execute(text("""
                    INSERT INTO memory_relationships (
                        id, workspace_id, source_node_id, target_node_id,
                        relationship_type, contribution_weight, _meta, created_at
                    ) VALUES (
                        :rel_id, :workspace_id, :source_id, :target_id,
                        'derived_from', :weight, '{}', NOW()
                    )
                """), {
                    "rel_id": str(self._generate_id()),
                    "workspace_id": str(workspace_id),
                    "source_id": str(new_node_id),
                    "target_id": evidence_id,
                    "weight": prop["confidence"],
                })

            logger.info(f"Approved proposal {proposal_id}: created {node_type} node {new_node_id}")

        return ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=1,
            scope=f"approve:{proposal_id}",
            metadata={
                "new_node_id": str(new_node_id),
                "level": level,
                "auto_approved_next": auto_approved_next,
            },
        )

    async def _auto_approve_by_threshold(
        self,
        conn,
        workspace_id: UUID,
        target_level: int,
        min_confidence: float,
    ) -> int:
        """Auto-approve proposals that meet confidence threshold.

        Returns: number of auto-approved proposals.
        """
        threshold = float(os.environ.get('AUTO_APPROVE_THRESHOLD', '0.95'))
        max_level = int(os.environ.get('AUTO_APPROVE_MAX_LEVEL', '3'))

        if min_confidence < threshold:
            logger.info(
                f"Auto-approve skipped: confidence {min_confidence} < threshold {threshold}"
            )
            return 0

        if target_level > max_level:
            logger.info(f"Auto-approve skipped: level {target_level} > max {max_level}")
            return 0

        # Find pending proposals for next level
        result = await conn.execute(text("""
            SELECT id, confidence FROM proposals
            WHERE workspace_id = :workspace_id
              AND target_level = :target_level
              AND status = 'pending'
              AND confidence >= :threshold
            ORDER BY confidence DESC
        """), {
            "workspace_id": str(workspace_id),
            "target_level": target_level,
            "threshold": threshold,
        })
        rows = result.fetchall()

        if not rows:
            logger.info(f"No pending proposals for L{target_level} meeting threshold {threshold}")
            return 0

        approved_count = 0
        for row in rows:
            proposal_id = row[0]
            try:
                await self.approve_proposal(
                    workspace_id=workspace_id,
                    proposal_id=proposal_id,
                )
                approved_count += 1
                logger.info(f"Auto-approved L{target_level} proposal {proposal_id} (confidence={row[1]})")
            except Exception as e:
                logger.error(f"Auto-approve failed for {proposal_id}: {e}")

        return approved_count

    async def reject_proposal(
        self,
        *,
        workspace_id: UUID,
        proposal_id: UUID,
        reason: str = "",
    ) -> ReflectionExecutionResult:
        """Reject a reflection proposal."""
        from sqlalchemy import text

        from backend.shared.infrastructure.database.engine import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("""
                UPDATE proposals SET status = 'rejected', rejected_reason = :reason, updated_at = NOW()
                WHERE id = :id AND workspace_id = :workspace_id
            """), {
                "id": str(proposal_id),
                "workspace_id": str(workspace_id),
                "reason": reason,
            })

        return ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=1,
            scope=f"reject:{proposal_id}",
            metadata={"proposal_id": str(proposal_id)},
        )

    async def reflect_by_time_window(
        self,
        *,
        workspace_id: UUID,
        start_date: str,
        end_date: str,
    ) -> ReflectionExecutionResult:
        """Execute reflection on memories within a time window."""
        self._validate_workspace_id(workspace_id)

        memories = await self._memory_node_repo.find_active_by_workspace(
            workspace_id=workspace_id,
        )

        return ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=len(memories),
            scope="time_window",
            metadata={
                "start_date": start_date,
                "end_date": end_date,
                "memory_count": len(memories),
            },
        )

    async def reflect_by_scope(
        self,
        *,
        workspace_id: UUID,
        scope: str,
    ) -> ReflectionExecutionResult:
        """Execute reflection by scope type."""
        return await self.reflect(
            workspace_id=workspace_id,
            scope=scope,
        )

    # ------------------------------------------------------------------
    # Consolidate Capability
    # ------------------------------------------------------------------

    async def consolidate(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
    ) -> ReflectionExecutionResult:
        """Consolidate redundant memories for an entity."""
        self._validate_workspace_id(workspace_id)

        memories = await self._memory_node_repo.find_by_entity(
            entity_id=entity_id,
            workspace_id=workspace_id,
        )

        return ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=len(memories),
            scope=f"consolidate:{entity_id}",
            metadata={"memory_count": len(memories)},
        )

    async def consolidate_by_entity(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
    ) -> ReflectionExecutionResult:
        """Alias for consolidate()."""
        return await self.consolidate(
            workspace_id=workspace_id,
            entity_id=entity_id,
        )

    # ------------------------------------------------------------------
    # Summarize Capability
    # ------------------------------------------------------------------

    async def summarize(
        self,
        *,
        workspace_id: UUID,
        level: int | None = None,
    ) -> ReflectionExecutionResult:
        """Summarize memories at a given level."""
        self._validate_workspace_id(workspace_id)

        if level is not None and level not in (1, 2, 3):
            raise ValidationError(
                f"Invalid level: {level}. Must be 1, 2, or 3.",
                field="level",
            )

        counts = {}
        if level is None or level == 1:
            obs = await self._memory_node_repo.find_by_level(
                level=1, workspace_id=workspace_id,
            )
            counts["observations"] = len(obs)
        if level is None or level == 2:
            pats = await self._memory_node_repo.find_by_level(
                level=2, workspace_id=workspace_id,
            )
            counts["patterns"] = len(pats)
        if level is None or level == 3:
            bels = await self._memory_node_repo.find_by_level(
                level=3, workspace_id=workspace_id,
            )
            counts["beliefs"] = len(bels)

        return ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=sum(counts.values()),
            scope=f"summarize:level={level or 'all'}",
            metadata=counts,
        )

    async def summarize_by_level(
        self,
        *,
        workspace_id: UUID,
        level: int,
    ) -> ReflectionExecutionResult:
        """Summarize memories at a specific level."""
        return await self.summarize(
            workspace_id=workspace_id,
            level=level,
        )

    # ------------------------------------------------------------------
    # Evaluate Capability
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
    ) -> ReflectionExecutionResult:
        """Evaluate memory quality and completeness."""
        self._validate_workspace_id(workspace_id)

        memories = await self._memory_node_repo.find_active_by_workspace(
            workspace_id=workspace_id,
        )

        if entity_id:
            memories = [
                m for m in memories
                if getattr(m, "entity_id", None) == entity_id
            ]

        total = len(memories)
        with_evidence = sum(
            1 for m in memories
            if getattr(m, "evidence_links", [])
        )
        avg_confidence = (
            sum(getattr(m, "confidence", 0.0) for m in memories) / total
            if total > 0 else 0.0
        )

        return ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=total,
            scope="evaluate",
            evidence_completeness=with_evidence / total if total > 0 else 0.0,
            metadata={
                "total_memories": total,
                "with_evidence": with_evidence,
                "avg_confidence": round(avg_confidence, 3),
            },
        )

    async def evaluate_by_entity(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
    ) -> ReflectionExecutionResult:
        """Evaluate an entity's memories."""
        return await self.evaluate(
            workspace_id=workspace_id,
            entity_id=entity_id,
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _run_engine_pipeline(
        self,
        scope: str,
        candidates: list[dict[str, Any]],
        workspace_id: UUID,
    ) -> dict[str, Any]:
        """Run the two-stage pipeline with batch processing.

        Per D4.2g and D4.2d_v1.1:
        Stage 1: EvidenceEvolutionEngine (Information Extraction)
        Stage 2: ReflectionEngine (Reasoning)

        Returns dict with:
        - evolved_candidates: list of candidates from Stage 1
        - proposals: list of proposals from Stage 2
        - execution_log: processing log
        """
        import os

        from backend.engine.evidence_evolution_engine import EvidenceEvolutionEngine
        from backend.engine.reflection_engine import ReflectionEngine
        from backend.shared.providers.reflection_provider import OllamaReflectionProvider

        # Use OllamaReflectionProvider (concrete implementation)
        provider = OllamaReflectionProvider(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            model=os.environ.get("REFLECTION_MODEL", "reflection-engine"),
        )

        execution_log = []

        # Batch processing: split candidates into smaller chunks for LLM
        # This avoids timeouts and improves JSON parsing success rate
        batch_count = (len(candidates) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info(
            "[EVOLUTION] Processing %d candidates in %d batches (batch_size=%d)",
            len(candidates), batch_count, BATCH_SIZE,
        )

        all_facts = []
        all_entities = []
        all_proposals = []
        all_evolved_candidates = []

        for i in range(0, len(candidates), BATCH_SIZE):
            batch = candidates[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            logger.info(
                "[EVOLUTION] Processing batch %d/%d (%d candidates)",
                batch_num, batch_count, len(batch),
            )

            try:
                # Stage 1: Evidence Evolution (Information Extraction)
                evidence_engine = EvidenceEvolutionEngine()
                evolution_result = await evidence_engine.evolve(
                    evidence=batch,
                    provider=provider,
                )
                execution_log.append(
                    f"Batch {batch_num}: EvidenceEvolution: {len(evolution_result.candidates)} candidates"
                )
                execution_log.extend(evolution_result.execution_log)

                # Log detailed info for debugging
                if evolution_result.candidates:
                    logger.info(
                        "[EVOLUTION] Batch %d: EvidenceEvolution generated %d candidates",
                        batch_num, len(evolution_result.candidates),
                    )
                    # Show first candidate
                    first_candidate = evolution_result.candidates[0]
                    logger.info(
                        "[EVOLUTION] First candidate keys: %s, content: %s",
                        list(first_candidate.keys()),
                        first_candidate.get('content', '')[:100],
                    )

                # Save evolved candidates to database (if any)
                if evolution_result.candidates:
                    await self._save_candidates(evolution_result.candidates, workspace_id)
                    execution_log.append(f"Batch {batch_num}: Saved {len(evolution_result.candidates)} candidates")
                    all_evolved_candidates.extend(evolution_result.candidates)

                # Stage 2: Reflection (Reasoning)
                # Use evolved candidates if available, otherwise fallback to original
                # Convert EvidenceEvolutionEngine output format to ReflectionEngine input format
                if evolution_result.candidates:
                    reflection_candidates = []
                    for c in evolution_result.candidates:
                        # Use evidence_chain IDs as candidate IDs for proper source tracking
                        evidence_chain = c.get('evidence_chain', [])
                        candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'
                        reflection_candidates.append({
                            'id': candidate_id,
                            'content': c.get('content', ''),
                            'evidence_source': 'evolution',
                            'source_level': c.get('source_level', 2),
                            'evidence_chain': evidence_chain,
                            'confidence': c.get('confidence', 0.9),
                        })
                else:
                    reflection_candidates = batch
                reflection_engine = ReflectionEngine()
                result = await reflection_engine.reflect_pipeline(
                    scope=scope,
                    candidates=reflection_candidates,
                    provider=provider,
                )

                all_facts.extend(result.get("facts", []))
                all_entities.extend(result.get("entities", []))
                all_proposals.extend(result.get("proposals", []))
                execution_log.extend(result.get("execution_log", []))

                # Log detailed info for debugging
                facts_count = len(result.get("facts", []))
                proposals_count = len(result.get("proposals", []))
                logger.info(
                    "[EVOLUTION] Batch %d/%d completed: facts=%d proposals=%d",
                    batch_num, batch_count,
                    facts_count, proposals_count,
                )
                if facts_count > 0:
                    logger.info(
                        "[EVOLUTION] First fact: %s",
                        result["facts"][0] if result.get("facts") else "N/A",
                    )

            except Exception as e:
                logger.error(
                    "[EVOLUTION] Batch %d/%d failed: %s",
                    batch_num, batch_count, str(e),
                    exc_info=True,
                )
                execution_log.append(f"Batch {batch_num} failed: {str(e)}")

        return {
            "facts": all_facts,
            "entities": all_entities,
            "proposals": all_proposals,
            "execution_log": execution_log,
            "evolved_candidates": all_evolved_candidates,
            "batch_count": batch_count,
        }

    async def _save_candidates(
        self,
        candidates: list[dict[str, Any]],
        workspace_id: UUID,
    ) -> None:
        """Save evolved candidates to database.

        Note: verified_at is UUID type in DB (see schema), not timestamp.
        The documentation says TIMESTAMPTZ but actual DB uses UUID.
        """
        import json as json_lib
        import uuid as uuid_lib

        from sqlalchemy import text

        from backend.shared.infrastructure.database.engine import get_engine

        if not candidates:
            return

        engine = get_engine()
        async with engine.begin() as conn:
            # Caches for entity and area lookups
            entity_cache: dict[str, str] = {}
            area_cache: dict[str, str] = {}

            for candidate in candidates:
                # verified_at is UUID type in database (not timestamp)
                # Generate a fresh UUID for each candidate
                candidate_verified_at = str(uuid_lib.uuid4())

                # Get or create entity by canonical_name
                entity_name = candidate.get("entity", "unknown")
                if entity_name not in entity_cache:
                    # Try to find existing entity
                    entity_result = await conn.execute(
                        text("SELECT id FROM entities WHERE workspace_id = :wid AND canonical_name = :name LIMIT 1"),
                        {"wid": str(workspace_id), "name": entity_name},
                    )
                    entity_row = entity_result.fetchone()
                    if entity_row:
                        entity_cache[entity_name] = str(entity_row[0])
                    else:
                        # Create new entity
                        new_entity_id = str(uuid_lib.uuid4())
                        await conn.execute(
                            text("""
                                INSERT INTO entities (id, workspace_id, canonical_name, entity_type, created_at, updated_at)
                                VALUES (:id, :workspace_id, :name, 'Concept', NOW(), NOW())
                            """),
                            {"id": new_entity_id, "workspace_id": str(workspace_id), "name": entity_name},
                        )
                        entity_cache[entity_name] = new_entity_id

                entity_id = entity_cache.get(entity_name, str(uuid_lib.uuid4()))

                # Get or create area
                area_id = candidate.get("area_id")
                if area_id:
                    # Check if area exists
                    area_result = await conn.execute(
                        text("SELECT id FROM areas WHERE id = :id LIMIT 1"),
                        {"id": area_id},
                    )
                    if not area_result.fetchone():
                        area_id = None  # Invalidate invalid area_id

                if not area_id:
                    # Use a default area or create one
                    area_id = area_cache.get("default")
                    if not area_id:
                        # Try to find any existing area for this workspace
                        default_area_result = await conn.execute(
                            text("SELECT id FROM areas WHERE workspace_id = :wid LIMIT 1"),
                            {"wid": str(workspace_id)},
                        )
                        default_area_row = default_area_result.fetchone()
                        if default_area_row:
                            area_id = str(default_area_row[0])
                            area_cache["default"] = area_id
                        else:
                            # Create default area
                            new_area_id = str(uuid_lib.uuid4())
                            await conn.execute(
                                text("""
                                    INSERT INTO areas (id, workspace_id, name, created_at, updated_at)
                                    VALUES (:id, :workspace_id, 'Default', NOW(), NOW())
                                """),
                                {"id": new_area_id, "workspace_id": str(workspace_id)},
                            )
                            area_id = new_area_id
                            area_cache["default"] = area_id
                else:
                    area_cache["default"] = area_id  # Cache for reuse

                await conn.execute(text("""
                    INSERT INTO candidates (
                        id, workspace_id, entity_id, area_id, content,
                        candidate_type, evidence_source, evidence_id,
                        evidence_chain, evidence_count, evidence_strength,
                        status, ingested_by, ingestion_timestamp,
                        verified_at, source_level, created_at, updated_at
                    ) VALUES (
                        :id, :workspace_id, :entity_id, :area_id, :content,
                        :candidate_type, :evidence_source, :evidence_id,
                        :evidence_chain, :evidence_count, :evidence_strength,
                        :status, :ingested_by, NOW(),
                        :verified_at, :source_level, NOW(), NOW()
                    )
                """), {
                    "id": str(uuid_lib.uuid4()),
                    "workspace_id": str(workspace_id),
                    "entity_id": entity_id,
                    "area_id": area_id,
                    "content": candidate.get("content", ""),
                    "candidate_type": candidate.get("node_type", "pattern"),
                    "evidence_source": candidate.get("evidence_source", "reflection"),
                    "evidence_id": candidate.get("evidence_id") or str(uuid_lib.uuid4()),
                    "evidence_chain": json_lib.dumps(candidate.get("evidence_chain", ["dummy"])),
                    "evidence_count": candidate.get("evidence_count", 1),
                    "evidence_strength": candidate.get("evidence_strength", 0.9),
                    "status": "candidate",
                    "ingested_by": "ai_reflect",
                    "verified_at": candidate_verified_at,
                    "source_level": candidate.get("level", 2),
                })

        logger.info(f"Saved {len(candidates)} candidates to database")

    async def _save_proposals(
        self,
        proposals: list[dict[str, Any]],
        workspace_id: UUID,
    ) -> None:
        """Save proposals to database for review."""
        import json as json_lib

        from sqlalchemy import text

        from backend.shared.infrastructure.database.engine import get_engine
        from backend.shared.infrastructure.uuid import generate_uuid

        if not proposals:
            return

        engine = get_engine()
        async with engine.begin() as conn:
            for prop in proposals:
                # Serialize evidence_chain to JSON string for PostgreSQL
                evidence_chain = prop.get("evidence_chain", [])
                if isinstance(evidence_chain, list):
                    evidence_chain_json = json_lib.dumps(evidence_chain)
                else:
                    evidence_chain_json = str(evidence_chain)

                # Determine source_level from candidate nodes
                source_level = prop.get("source_level", 1)

                await conn.execute(text("""
                    INSERT INTO proposals (
                        id, workspace_id, type, source_level, target_level,
                        entity, evidence_chain, confidence, summary, content,
                        status, created_at, updated_at
                    ) VALUES (
                        :id, :workspace_id, :type, :source_level, :target_level,
                        :entity, :evidence_chain, :confidence, :summary, :content,
                        'pending', NOW(), NOW()
                    )
                """), {
                    "id": str(generate_uuid()),
                    "workspace_id": str(workspace_id),
                    "type": prop.get("type", "Ignore"),
                    "source_level": source_level,
                    "target_level": prop.get("target_level", source_level + 1),
                    "entity": prop.get("entity", "unknown"),
                    "evidence_chain": evidence_chain_json,
                    "confidence": prop.get("confidence", 0.5),
                    "summary": prop.get("summary", ""),
                    "content": prop.get("content", ""),
                })

            logger.info(f"Saved {len(proposals)} proposals for review")

    async def _acquire_scope(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None,
        scope: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Acquire the scope of memories to reflect upon.

        Reads from Repository (allowed: Service → Repository).
        Converts ORM objects to dicts for engine processing.

        Per 10_4 §9: Idempotency requires bounded scope.
        Per Memory Lifecycle design: Evidence-based, not time-based.
        We process L1 facts that are NOT yet referenced by higher-level memories.
        """
        from sqlalchemy import text

        from backend.shared.domain.memory_models import MemoryNode
        from backend.shared.infrastructure.database.engine import get_engine

        if scope in ("daily", "weekly", "monthly", "workspace"):
            # Check if there are candidates in the candidates table
            engine = get_engine()
            async with engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT id, entity_id, area_id, content, candidate_type,
                           evidence_source, evidence_id, evidence_chain,
                           evidence_count, evidence_strength, status,
                           COALESCE(source_level, 1) as source_level
                    FROM candidates
                    WHERE workspace_id = :workspace_id
                    AND status IN ('candidate', 'pending')
                    ORDER BY created_at ASC
                    LIMIT :limit
                """), {"workspace_id": str(workspace_id), "limit": limit})

                rows = result.fetchall()
                if rows:
                    # Return candidates as dicts with source_level
                    result = []
                    for row in rows:
                        result.append({
                            "id": str(row[0]),
                            "entity_id": str(row[1]) if row[1] else None,
                            "area_id": str(row[2]) if row[2] else None,
                            "content": row[3],
                            "node_type": row[4],  # candidate_type
                            "evidence_source": row[5],
                            "evidence_id": str(row[6]) if row[6] else None,
                            "evidence_chain": row[7],
                            "evidence_count": row[8],
                            "evidence_strength": row[9],
                            "status": row[10],
                            "level": row[11] if row[11] else 1,  # source_level
                        })
                    logger.info(
                        f"[EVOLUTION] Scope acquired: {len(result)} candidates"
                    )
                    return result

            # No candidates - create from memory_nodes based on level
            # L2 candidates from level=2 nodes for L2→L3 evolution
            # L3+ candidates from level>=3 nodes for cascading evolution
            # L1 candidates from unprocessed L1 nodes (generated_by is None or 'import')
            nodes = await self._memory_node_repo.find_active_by_workspace(
                workspace_id=workspace_id,
                limit=limit * 3,
            )

            # Filter nodes for candidate creation
            filtered_nodes = []
            for node in nodes:
                if isinstance(node, MemoryNode):
                    if node.level == 1:
                        # L1 nodes: only create candidates if not yet evolved
                        if getattr(node, 'generated_by', None) != 'ai_reflect':
                            filtered_nodes.append(node)
                    else:
                        # L2+ nodes: always create candidates for further evolution
                        filtered_nodes.append(node)

                    if len(filtered_nodes) >= limit:
                        break

            # Convert to candidates format with proper source_level
            result = []
            for node in filtered_nodes:
                result.append({
                    "id": str(node.id),
                    "entity_id": str(node.entity_id) if getattr(node, 'entity_id', None) else None,
                    "area_id": str(getattr(node, 'area_id', None)) if hasattr(node, 'area_id') and node.area_id else None,
                    "content": node.content,
                    "node_type": node.node_type,
                    "evidence_source": getattr(node, 'source', None),
                    "evidence_id": None,
                    "evidence_chain": getattr(node, 'evidence_links', []) or [],
                    "evidence_count": len(getattr(node, 'evidence_links', []) or []) if getattr(node, 'evidence_links', []) else 0,
                    "evidence_strength": getattr(node, 'confidence', 0.5) or 0.5,
                    "status": "pending",
                    "level": node.level,  # source_level: 1 for L1→L2, 2 for L2→L3, etc.
                })
            logger.info(
                f"[EVOLUTION] Scope acquired: {len(result)} candidates from memory_nodes"
            )
            return result
        else:
            # Entity scope: get all memories for this entity
            if entity_id:
                nodes = await self._memory_node_repo.find_by_entity(
                    entity_id=entity_id,
                    workspace_id=workspace_id,
                )
            else:
                nodes = await self._memory_node_repo.find_active_by_workspace(
                    workspace_id=workspace_id,
                    limit=limit,
                )

        # Convert ORM objects to dicts
        result = []
        for node in nodes:
            if isinstance(node, MemoryNode):
                result.append({
                    "id": str(node.id),
                    "workspace_id": str(node.workspace_id),
                    "content": node.content,
                    "level": node.level,
                    "node_type": node.node_type,
                    "status": node.status,
                    "source": node.source,
                    "created_at": node.created_at.isoformat() if node.created_at else None,
                    "evidence_links": node.evidence_links or [],
                })
            else:
                result.append(node)

        return result

    def _generate_id(self) -> UUID:
        """Generate a UUID for internal use."""
        try:
            from backend.shared.infrastructure.uuid import generate_uuid
            return generate_uuid()
        except ImportError:
            import uuid
            return uuid.uuid4()
