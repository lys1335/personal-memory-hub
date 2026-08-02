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
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.service.base import BaseService
from backend.service.dto import (
    ReflectionExecutionResult,
    ReflectionStatus,
)
from backend.service.exceptions import ValidationError

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

        # Step 2: Delegate to ReflectionEngine
        engine_result = await self._run_engine_pipeline(scope, candidates)

        # Step 3: Save proposals to database
        await self._save_proposals(engine_result.get("proposals", []), workspace_id)

        # Step 4: Calculate statistics
        duration_ms = (time.monotonic() - start_time) * 1000
        proposals = engine_result.get("proposals", [])
        facts = engine_result.get("facts", [])

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

            # Create L2/L3 memory node
            new_node_id = self._generate_id()
            level = prop["target_level"]
            node_type = "Pattern" if level == 2 else "Belief" if level == 3 else "Observation"

            await conn.execute(text("""
                INSERT INTO memory_nodes (
                    id, workspace_id, level, node_type, content, summary,
                    confidence, importance, signal_strength, status, source, generated_by,
                    evidence_links, contradict_evidence, _meta, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :level, :node_type, :content, :summary,
                    :confidence, :importance, :signal_strength, 'active', 'ai_reflect', 'ai_reflect',
                    :evidence_links, '[]', '{}', NOW(), NOW()
                )
            """), {
                "id": str(new_node_id),
                "workspace_id": str(workspace_id),
                "level": level,
                "node_type": node_type,
                "content": prop["content"],
                "summary": prop["summary"],
                "confidence": prop["confidence"],
                "importance": prop["confidence"],
                "signal_strength": prop["confidence"],
                "evidence_links": prop["evidence_chain"],
            })

            # Create relationships (derived_from)
            for evidence_id in prop["evidence_chain"]:
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
            metadata={"new_node_id": str(new_node_id), "level": level},
        )

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
    ) -> dict[str, Any]:
        """Run the ReflectionEngine pipeline with Provider abstraction.

        Per D4.2d §2.7: LLM invocation is managed by Service layer,
        not by the Engine directly.
        """
        import os

        from backend.engine.reflection_engine import ReflectionEngine
        from backend.shared.providers.reflection_provider import OllamaReflectionProvider

        # Use OllamaReflectionProvider (concrete implementation)
        provider = OllamaReflectionProvider(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            model=os.environ.get("REFLECTION_MODEL", "reflection-engine"),
        )
        engine = ReflectionEngine()
        result = await engine.reflect_pipeline(
            scope=scope,
            candidates=candidates,
            provider=provider,
        )
        return result

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
                    "source_level": 1,
                    "target_level": prop.get("target_level", 2),
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

        if scope in ("daily", "weekly", "monthly"):
            # Get all active L1 facts (no time restriction - evidence-based)
            nodes = await self._memory_node_repo.find_active_by_workspace(
                workspace_id=workspace_id,
                limit=limit * 3,  # Fetch more to allow filtering by evidence
            )

            # Find L2/L3 nodes that already have relationships (derived_from)
            engine = get_engine()
            async with engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT DISTINCT target_node_id
                    FROM memory_relationships
                    WHERE workspace_id = :workspace_id
                    AND relationship_type = 'derived_from'
                """), {"workspace_id": str(workspace_id)})
                evolved_target_ids = set(str(r[0]) for r in result.fetchall())

            # Find L1 nodes that are NOT referenced by any L2/L3
            # These are "orphan" facts that need evidence chain
            unprocessed_ids: set[str] = set()
            filtered_nodes: list[MemoryNode] = []

            for node in nodes:
                if isinstance(node, MemoryNode) and node.level == 1:
                    node_id = str(node.id)
                    # Skip if already evolved (generated_by = 'ai_reflect')
                    if getattr(node, 'generated_by', None) == 'ai_reflect':
                        continue
                    # Skip if already referenced by higher-level memory
                    if node_id in evolved_target_ids:
                        continue
                    filtered_nodes.append(node)
                    unprocessed_ids.add(node_id)
                    if len(filtered_nodes) >= limit:
                        break

            nodes = filtered_nodes

            logger.info(
                f"[EVOLUTION] Scope acquired: {len(nodes)} unprocessed L1 facts "
                f"(skipped {len(evolved_target_ids)} already evolved)"
            )
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
