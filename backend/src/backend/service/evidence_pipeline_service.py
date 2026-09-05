"""EvidencePipelineService — Phase 21.8 Integration Pipeline.

This service orchestrates the complete Phase 21 pipeline:
Evidence → ContextWindow → Semantic Interpretation → Formation → Topic → Evolution

Transaction ownership: This service owns the transaction.
It begins the transaction at the start and commits/rollbacks at the end.

Design constraints:
- Does NOT implement business logic (delegates to sub-services)
- Manages transaction boundary
- Handles errors and logging
- Returns structured PipelineResult
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.context import ContextWindow, ContextWindowFormulator
from backend.context.interpretation_result import InterpretationResult
from backend.context.semantic_interpreter import UserSemanticInterpreter
from backend.service.evolution_service import EvolutionService
from backend.service.base import BaseService
from backend.service.formation_service import FormationService, FormationResult
from backend.service.topic_service import TopicService

logger = logging.getLogger(__name__)


class PipelineResult:
    """Result of the complete Phase 21 pipeline execution."""

    def __init__(
        self,
        success: bool,
        evidence_id: UUID | None = None,
        workspace_id: UUID | None = None,
        reconstruction_id: UUID | None = None,
        candidate_id: UUID | None = None,
        topic_ids: list[UUID] | None = None,
        interpretation: InterpretationResult | None = None,
        context_window: ContextWindow | None = None,
        error: str | None = None,
        skipped: str | None = None,
    ) -> None:
        self.success = success
        self.evidence_id = evidence_id
        self.workspace_id = workspace_id
        self.reconstruction_id = reconstruction_id
        self.candidate_id = candidate_id
        self.topic_ids = topic_ids or []
        self.interpretation = interpretation
        self.context_window = context_window
        self.error = error
        self.skipped = skipped

    @property
    def has_reconstruction(self) -> bool:
        return self.reconstruction_id is not None

    @property
    def has_candidate(self) -> bool:
        return self.candidate_id is not None

    @property
    def has_topics(self) -> bool:
        return len(self.topic_ids) > 0

    def get_summary(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "evidence_id": str(self.evidence_id) if self.evidence_id else None,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "reconstruction_id": str(self.reconstruction_id) if self.reconstruction_id else None,
            "candidate_id": str(self.candidate_id) if self.candidate_id else None,
            "topic_ids": [str(t) for t in self.topic_ids],
            "skipped": self.skipped,
            "error": self.error,
        }


class EvidencePipelineService(BaseService):
    """Orchestrates the complete Phase 21 pipeline.

    Pipeline flow:
    Evidence → ContextWindow → Interpretation → Formation → Topic → Evolution

    Transaction: This service owns the transaction.
    It manages BEGIN/COMMIT/ROLLBACK for the entire pipeline.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__("EvidencePipelineService")
        self.session = session
        self.formulation = ContextWindowFormulator(session)
        self.interpreter = UserSemanticInterpreter()
        self.formation = FormationService(session)
        self.topics = TopicService(session)
        self.evolution = EvolutionService(session)

    async def process_evidence(
        self,
        *,
        evidence_id: UUID,
        workspace_id: UUID,
    ) -> PipelineResult:
        """Execute the complete Phase 21 pipeline for an Evidence.

        Args:
            evidence_id: The Evidence that triggered this pipeline.
            workspace_id: Workspace scope.

        Returns:
            PipelineResult with reconstruction_id, candidate_id, topic_ids.
        """
        logger.info(
            "Pipeline started: evidence=%s, workspace=%s",
            evidence_id, workspace_id,
        )

        try:
            # Step 1: Form ContextWindow (memory operation, no DB)
            context_window = await self._form_context_window(evidence_id, workspace_id)
            if context_window is None:
                return PipelineResult(
                    success=False,
                    evidence_id=evidence_id,
                    workspace_id=workspace_id,
                    error="Failed to form context window",
                )

            # Step 2: Semantic Interpretation (memory operation, no DB)
            interpretation = await self._interpret(context_window, evidence_id, workspace_id)
            if interpretation is None:
                return PipelineResult(
                    success=False,
                    evidence_id=evidence_id,
                    workspace_id=workspace_id,
                    error="Failed to interpret evidence",
                )

            # Step 3: Formation (Reconstruction + Candidate)
            formation = await self._form(
                interpretation=interpretation,
                evidence_id=evidence_id,
                workspace_id=workspace_id,
                context_window=context_window,
            )

            # Step 4: Topic extraction and linking
            # Step 5: Topic extraction (if user-owned)
            if interpretation.user_owned:
                topic_ids = await self._extract_topics(
                    interpretation=interpretation,
                    formation=formation,
                    workspace_id=workspace_id,
                )

            # NOTE: Historical evolution (L2/L3 creation) is now handled by
            # EvolutionService.evolve_entity_history() called separately,
            # NOT during EvidencePipelineService processing.
            # This prevents direct L2 creation from EvidencePipelineService.
            topic_ids = []

            # Success: commit the transaction
            await self._commit(self.session)

            logger.info(
                "Pipeline completed: recon=%s, candidate=%s, topics=%d",
                formation.reconstruction_id,
                formation.candidate_id,
                len(topic_ids),
            )

            return PipelineResult(
                success=True,
                evidence_id=evidence_id,
                workspace_id=workspace_id,
                reconstruction_id=formation.reconstruction_id,
                candidate_id=formation.candidate_id,
                topic_ids=topic_ids,
                interpretation=interpretation,
                context_window=context_window,
            )

        except Exception as e:
            # Failure: rollback the transaction
            await self._rollback(self.session, str(e))

            logger.error(
                "Pipeline failed: evidence=%s, error=%s",
                evidence_id, e,
                exc_info=True,
            )

            return PipelineResult(
                success=False,
                evidence_id=evidence_id,
                workspace_id=workspace_id,
                error=str(e),
            )

    async def _form_context_window(
        self, evidence_id: UUID, workspace_id: UUID
    ) -> ContextWindow | None:
        """Form context window from Evidence and related context."""
        try:
            return await self.formulation.formulate(
                trigger_evidence_id=evidence_id,
                workspace_id=workspace_id,
            )
        except Exception as e:
            logger.error("Failed to form context window: %s", e)
            return None

    async def _interpret(
        self,
        context_window: ContextWindow,
        evidence_id: UUID,
        workspace_id: UUID,
    ) -> InterpretationResult | None:
        """Interpret the context window semantically."""
        try:
            return await self.interpreter.interpret(
                context=context_window.to_interpretation_context(),
                workspace_id=workspace_id,
            )
        except Exception as e:
            logger.error("Failed to interpret context: %s", e)
            return None

    async def _form(
        self,
        interpretation: InterpretationResult,
        evidence_id: UUID,
        workspace_id: UUID,
        context_window: "ContextWindow" | None = None,
    ) -> FormationResult:
        """Form Reconstruction and Candidate from interpretation."""
        return await self.formation.form(
            interpretation=interpretation,
            trigger_evidence_id=evidence_id,
            workspace_id=workspace_id,
            context_window=context_window,
        )

    async def _extract_topics(
        self,
        interpretation: InterpretationResult,
        formation: "FormationResult",
        workspace_id: UUID,
    ) -> list[UUID]:
        """Extract and resolve topics from interpretation."""
        if not interpretation.semantic_content:
            return []

        try:
            topic_ids = await self.topics.extract_topics_from_summary(
                workspace_id=workspace_id,
                semantic_summary=interpretation.semantic_content,
            )

            # Link topics to reconstruction (if formed)
            if formation.reconstruction_id:
                await self.topics.link_reconstruction_to_topics(
                    reconstruction_id=formation.reconstruction_id,
                    topic_ids=topic_ids,
                    workspace_id=workspace_id,
                )

            return topic_ids
        except Exception as e:
            logger.error("Failed to extract topics: %s", e)
            return []

    async def _evolve(
        self,
        *,
        candidate_id: UUID,
        workspace_id: UUID,
        entity_id: UUID | None,
        topic_ids: list[UUID],
    ) -> None:
        """Execute historical memory evolution.

        DEPRECATED: This method is no longer called during normal pipeline.
        Evolution is now handled by EvolutionService.evolve_entity_history().
        Kept for backward compatibility only.
        """
        logger.warning(
            "_evolve() is deprecated and should not be called directly. "
            "Use EvolutionService.evolve_entity_history() instead."
        )
        await self.evolution.evolve(
            candidate_id=candidate_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
            topic_ids=topic_ids,
        )
