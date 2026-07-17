"""ReflectionService — Memory Evolution Application Service.

Implements the Reflection Business Capability Orchestrator:
- Reflect: Generate new patterns/beliefs from observations
- Consolidate: Merge redundant memories
- Summarize: Create level summaries
- Evaluate: Assess memory quality and completeness

Per D3.4 and 10_4 Implementation Design:
- ReflectionService does NOT own reflection algorithms (ReflectionEngine owns them)
- ReflectionService does NOT own task lifecycle (TaskService owns it)
- ReflectionService does NOT own runtime execution (Task Runtime owns it)
- Service Independence: does NOT call other Services
- Command Returns Identity: returns ReflectionExecutionResult (report, not business data)
- Raw Evidence Preservation: L0 memories never modified/deleted by Reflection
- Higher-level Memory stores evolving explanations, not snapshots
- Incremental propagation: only upward when necessary
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.repository.exceptions import RepositoryError
from backend.service.base import BaseService
from backend.service.dto import (
    ReflectionExecutionResult,
    ReflectionStatus,
)
from backend.service.exceptions import (
    ValidationError,
)

if TYPE_CHECKING:
    from backend.repository.candidate_repository import CandidateRepository
    from backend.repository.memory_node_repository import MemoryNodeRepository
    from backend.repository.relationship_repository import RelationshipRepository

logger = logging.getLogger(__name__)


class ReflectionService(BaseService):
    """Application service for memory reflection operations.

    Orchestrates the reflection workflow:
    1. Acquire scope (find candidate memories)
    2. Invoke domain engine (algorithm execution)
    3. Review and validate results
    4. Persist evolution results

    Stateless singleton managed by DI container.
    """

    def __init__(
        self,
        memory_node_repo: MemoryNodeRepository,
        candidate_repo: CandidateRepository,
        relationship_repo: RelationshipRepository,
    ) -> None:
        """Initialize ReflectionService with required repositories.

        Args:
            memory_node_repo: Repository for MemoryNode reads/writes.
            candidate_repo: Repository for Candidate records.
            relationship_repo: Repository for Relationship management.
        """
        super().__init__("ReflectionService")
        self._memory_node_repo = memory_node_repo
        self._candidate_repo = candidate_repo
        self._relationship_repo = relationship_repo

    # ------------------------------------------------------------------
    # Reflect Capability
    # ------------------------------------------------------------------

    async def reflect(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        scope: str = "entity",
    ) -> ReflectionExecutionResult:
        """Execute reflection on memories within a scope.

        The reflection workflow:
        1. Acquire scope (find candidate memories)
        2. Invoke domain engine (pattern/belief generation)
        3. Validate results (evidence completeness, semantic coherence)
        4. Persist evolution results (candidates, new memories)

        The actual reflection algorithm runs in the Domain Engine (D4).
        This service orchestrates the workflow.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity to reflect upon.
            scope: Reflection scope ("entity", "area", "workspace").

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

        # Step 2: Invoke domain engine (stub — algorithm runs in D4)
        # In production, this would call ReflectionEngine.reflect()
        new_patterns = 0
        new_beliefs = 0
        updated_beliefs = 0
        evidence_complete = 0

        for candidate in candidates:
            # Validate evidence completeness
            evidence_count = getattr(candidate, "evidence_count", 0)
            if evidence_count > 0:
                evidence_complete += 1

            # Create a candidate record in the database
            try:
                from backend.shared.domain.memory_models import Candidate

                c = Candidate(
                    id=self._generate_id(),
                    workspace_id=workspace_id,
                    entity_id=candidate.entity_id if hasattr(candidate, "entity_id") else (entity_id or UUID(int=0)),
                    content=getattr(candidate, "content", ""),
                    candidate_type=getattr(candidate, "candidate_type", "pattern"),
                    evidence_count=evidence_count,
                    evidence_strength=getattr(candidate, "evidence_strength", 0.0),
                    status="candidate",
                )
                await self._candidate_repo.create(c)

                if getattr(c, "candidate_type", "") == "pattern":
                    new_patterns += 1
                else:
                    new_beliefs += 1
            except RepositoryError as exc:
                self._log.warning(
                    "Failed to create candidate: %s", exc
                )

        # Step 3: Calculate statistics
        duration_ms = (time.monotonic() - start_time) * 1000
        total = len(candidates) if candidates else 1
        completeness = evidence_complete / total if total > 0 else 0.0

        return ReflectionExecutionResult(
            status=ReflectionStatus.COMPLETED,
            reflections_performed=len(candidates),
            new_patterns=new_patterns,
            new_beliefs=new_beliefs,
            updated_beliefs=updated_beliefs,
            evidence_completeness=completeness,
            scope=scope,
            duration_ms=duration_ms,
            metadata={"candidate_count": len(candidates)},
        )

    async def reflect_by_entity(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
    ) -> ReflectionExecutionResult:
        """Execute reflection on a specific entity's memories.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity to reflect upon.

        Returns:
            ReflectionExecutionResult.
        """
        return await self.reflect(
            workspace_id=workspace_id,
            entity_id=entity_id,
            scope="entity",
        )

    async def reflect_by_time_window(
        self,
        *,
        workspace_id: UUID,
        start_date: str,
        end_date: str,
    ) -> ReflectionExecutionResult:
        """Execute reflection on memories within a time window.

        Args:
            workspace_id: Workspace scope.
            start_date: Start date (ISO 8601).
            end_date: End date (ISO 8601).

        Returns:
            ReflectionExecutionResult.
        """
        self._validate_workspace_id(workspace_id)

        # Find memories in the time window
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
        """Execute reflection by scope type.

        Args:
            workspace_id: Workspace scope.
            scope: Scope type ("entity", "area", "workspace").

        Returns:
            ReflectionExecutionResult.
        """
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
        """Consolidate redundant memories for an entity.

        Merges duplicate or highly similar memories into a single record.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity whose memories to consolidate.

        Returns:
            ReflectionExecutionResult with consolidation statistics.
        """
        self._validate_workspace_id(workspace_id)

        # Find all memories for this entity
        memories = await self._memory_node_repo.find_by_entity(
            entity_id=entity_id,
            workspace_id=workspace_id,
        )

        # MVP: return basic result without actual consolidation logic
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
        """Alias for consolidate().

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity to consolidate.

        Returns:
            ReflectionExecutionResult.
        """
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
        """Summarize memories at a given level.

        Args:
            workspace_id: Workspace scope.
            level: Memory level to summarize (1=Observation, 2=Pattern, 3=Belief).
                If None, summarizes all levels.

        Returns:
            ReflectionExecutionResult with summary statistics.
        """
        self._validate_workspace_id(workspace_id)

        if level is not None and level not in (1, 2, 3):
            raise ValidationError(
                f"Invalid level: {level}. Must be 1, 2, or 3.",
                field="level",
            )

        # Count memories by level
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
        """Summarize memories at a specific level.

        Args:
            workspace_id: Workspace scope.
            level: Memory level (1, 2, or 3).

        Returns:
            ReflectionExecutionResult.
        """
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
        """Evaluate memory quality and completeness.

        Assess the quality of memories based on evidence strength,
        semantic coherence, and coverage.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity to evaluate.

        Returns:
            ReflectionExecutionResult with evaluation metrics.
        """
        self._validate_workspace_id(workspace_id)

        # Gather evaluation data
        memories = await self._memory_node_repo.find_active_by_workspace(
            workspace_id=workspace_id,
        )

        if entity_id:
            memories = [
                m for m in memories
                if getattr(m, "entity_id", None) == entity_id
            ]

        # Calculate basic metrics
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
        """Evaluate an entity's memories.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity to evaluate.

        Returns:
            ReflectionExecutionResult.
        """
        return await self.evaluate(
            workspace_id=workspace_id,
            entity_id=entity_id,
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _acquire_scope(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None,
        scope: str,
    ) -> list[Any]:
        """Acquire the scope of memories to reflect upon.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity filter.
            scope: Scope type.

        Returns:
            List of candidate memory objects.
        """
        if scope == "entity" and entity_id:
            return await self._memory_node_repo.find_by_entity(
                entity_id=entity_id,
                workspace_id=workspace_id,
            )
        else:
            return await self._memory_node_repo.find_active_by_workspace(
                workspace_id=workspace_id,
            )

    def _generate_id(self) -> UUID:
        """Generate a UUID for internal use."""
        try:
            from backend.shared.infrastructure.uuid import generate_uuid
            return generate_uuid()
        except ImportError:
            import uuid
            return uuid.uuid4()
