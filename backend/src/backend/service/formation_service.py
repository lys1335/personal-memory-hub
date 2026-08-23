"""Formation Service — Phase 21.5 Reconstruction → Candidate Formation.

This service implements the formation pipeline:
InterpretationResult → Reconstruction → Candidate → Lineage binding

Design constraints:
- Each Reconstruction maps to exactly one Candidate (1:1)
- Candidate is a snapshot, immutable after creation
- Reconstruction version chain via parent_reconstruction_id
- Evidence lineage preserved in Reconstruction.evidence_refs
- Workspace and entity isolation
- NO modification of historical Candidates
- NO Topic creation
- NO Historical Memory Evolution

Transaction: This service does NOT manage transactions.
It uses the session passed by the caller (EvidencePipelineService).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.context.interpretation_result import (
    InterpretationContext,
    InterpretationResult,
    InterpretationType,
    SemanticUnit,
)
from backend.repository.candidate_repository import CandidateRepository
from backend.repository.reconstruction_repository import ReconstructionRepository
from backend.repository.entity_repository import EntityRepository
from backend.repository.workspace import WorkspaceIsolationMixin
from backend.service.base import BaseService
from backend.shared.domain.memory_models import Reconstruction, Candidate

logger = logging.getLogger(__name__)


class FormationResult:
    """Result of Reconstruction → Candidate formation."""

    def __init__(
        self,
        success: bool,
        reconstruction_id: UUID | None = None,
        candidate_id: UUID | None = None,
        interpretation: InterpretationResult | None = None,
        entity_id: UUID | None = None,
        error: str | None = None,
        is_unresolved: bool = False,
        resolution_method: str | None = None,
    ) -> None:
        self.success = success
        self.reconstruction_id = reconstruction_id
        self.candidate_id = candidate_id
        self.interpretation = interpretation
        self.entity_id = entity_id
        self.error = error
        self.is_unresolved = is_unresolved
        self.resolution_method = resolution_method

    @property
    def has_reconstruction(self) -> bool:
        return self.reconstruction_id is not None

    @property
    def has_candidate(self) -> bool:
        return self.candidate_id is not None

    def get_summary(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "reconstruction_id": str(self.reconstruction_id) if self.reconstruction_id else None,
            "candidate_id": str(self.candidate_id) if self.candidate_id else None,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "is_unresolved": self.is_unresolved,
            "resolution_method": self.resolution_method,
            "error": self.error,
        }


class FormationService(BaseService):
    """Forms Reconstruction and Candidate from InterpretationResult.

    This is the Phase 21.5 core service.
    It translates semantic interpretation into persistent objects.

    Transaction: Uses the session provided by the caller.
    Does NOT commit or rollback — that is the caller's responsibility.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__("FormationService")
        self.session = session
        self.reconstruction_repo = ReconstructionRepository(session)
        self.candidate_repo = CandidateRepository(session)
        self.entity_repo = EntityRepository(session)

    async def form(
        self,
        interpretation: InterpretationResult,
        trigger_evidence_id: UUID,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        parent_reconstruction_id: UUID | None = None,
        context_window: ContextWindow | None = None,
    ) -> FormationResult:
        """Form Reconstruction and Candidate from InterpretationResult.

        Args:
            interpretation: Output from Phase 21.4 semantic interpretation.
            trigger_evidence_id: The Evidence that triggered this formation.
            workspace_id: Workspace scope.
            entity_id: Optional entity (resolved from evidence if not provided).
            parent_reconstruction_id: Optional parent for version chain.
            context_window: Optional ContextWindow with full evidence context.

        Returns:
            FormationResult with reconstruction_id and candidate_id.

        Note: This method does NOT commit or rollback.
              The caller (EvidencePipelineService) manages the transaction.
        """
        # Step 1: Check if interpretation produces user-owned fact
        if not interpretation.user_owned:
            logger.info(
                "No user-owned fact from interpretation type=%s, skipping formation",
                interpretation.interpretation_type.value,
            )
            return FormationResult(
                success=True,
                interpretation=interpretation,
                error=f"interpretation_type={interpretation.interpretation_type.value} does not produce user fact",
            )

        # Step 2: Resolve entity_id using NEW Entity Resolution algorithm ONLY
        # CRITICAL: Do NOT use Evidence.entity_id directly - it contains old buggy bindings
        # All entities must be re-resolved using the fixed algorithm
        resolution_method = None
        # Always use context-aware resolution (ignores old Evidence.entity_id)
        entity_id, resolution_method = await self._resolve_entity_from_context(
            trigger_evidence_id, workspace_id, context_window=context_window
        )

        # Step 2.5: Handle unresolved entity gracefully (don't block pipeline)
        is_unresolved = entity_id is None
        if is_unresolved:
            logger.warning(
                "Evidence %s: could not resolve entity, creating candidate without entity linkage",
                trigger_evidence_id,
            )

        # Step 3: Create Reconstruction
        reconstruction = await self._create_reconstruction(
            interpretation=interpretation,
            workspace_id=workspace_id,
            entity_id=entity_id,
            parent_reconstruction_id=parent_reconstruction_id,
            evidence_ids=interpretation.source_evidence_ids,
            is_unresolved=is_unresolved,
            resolution_method=resolution_method,
        )
        if reconstruction is None:
            return FormationResult(
                success=False,
                error="Failed to create Reconstruction",
            )

        # Step 4: Create Candidate
        candidate = await self._create_candidate(
            interpretation=interpretation,
            workspace_id=workspace_id,
            entity_id=entity_id,
            evidence_ids=interpretation.source_evidence_ids,
            is_unresolved=is_unresolved,
            resolution_method=resolution_method,
        )
        if candidate is None:
            return FormationResult(
                success=False,
                error="Failed to create Candidate",
            )

        # Step 5: Bind Reconstruction → Candidate (1:1)
        bound = await self._bind_reconstruction_to_candidate(
            reconstruction_id=reconstruction.id,
            candidate_id=candidate.id,
        )
        if not bound:
            return FormationResult(
                success=False,
                error="Failed to bind Reconstruction to Candidate",
            )

        logger.info(
            "Formation successful: recon=%s, candidate=%s, type=%s",
            reconstruction.id,
            candidate.id,
            interpretation.interpretation_type.value,
        )

        return FormationResult(
            success=True,
            reconstruction_id=reconstruction.id,
            candidate_id=candidate.id,
            interpretation=interpretation,
            entity_id=entity_id,
        )

    async def _resolve_entity(
        self, evidence_id: UUID, workspace_id: UUID
    ) -> UUID | None:
        """Resolve entity_id from trigger evidence."""
        from backend.shared.domain.memory_models import Evidence
        stmt = select(Evidence).where(
            Evidence.id == evidence_id,
            Evidence.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        evidence = result.scalar_one_or_none()
        return evidence.entity_id if evidence else None

    async def _resolve_entity_from_context(
        self, evidence_id: UUID, workspace_id: UUID,
        context_window: ContextWindow | None = None
    ) -> tuple[UUID | None, str | None]:
        """Resolve entity using context-aware strategies.

        Uses ContextWindow evidence list when available for better accuracy.
        Falls back to single evidence analysis when context_window is None.

        Returns (entity_id, method) where method indicates resolution strategy.
        Returns (None, 'unresolved') if no entity can be resolved.

        Algorithm:
        1. Calculate match score for each entity
        2. Detect competing entities
        3. Apply confidence threshold (0.8)
        4. Return unresolved if ambiguous or low confidence
        """
        from backend.shared.domain.memory_models import Evidence

        # Load workspace entities once
        workspace_entities = await self._get_workspace_entities(workspace_id)

        # Get evidence content
        evidence_content = None
        if context_window and context_window.evidence_list:
            # Use trigger evidence from context window
            for ctx_ev in context_window.evidence_list:
                if ctx_ev.evidence_id == evidence_id:
                    evidence_content = ctx_ev.content
                    break
        else:
            # Fallback: load evidence directly
            stmt = select(Evidence).where(
                Evidence.id == evidence_id,
                Evidence.workspace_id == workspace_id,
            )
            result = await self.session.execute(stmt)
            evidence = result.scalar_one_or_none()
            evidence_content = evidence.content if evidence else None

        if evidence_content is None or not evidence_content.strip():
            return None, "no_evidence"

        # Use strict resolution algorithm
        from .entity_resolution import resolve_entity_strict

        result = resolve_entity_strict(
            evidence_content=evidence_content,
            workspace_entities=workspace_entities,
            context_window=context_window.evidence_list if context_window else None,
            min_confidence=0.8  # High threshold to avoid false positives
        )

        return result.entity_id, result.method

    async def _resolve_from_context_window(
        self,
        context_window: ContextWindow,
        workspace_entities: list[Any],
    ) -> tuple[UUID | None, str | None]:
        """Resolve entity using all evidences in ContextWindow.

        REMOVED: First-match-wins logic
        ADDED: Score-based ranking with competition detection

        Algorithm:
        1. Aggregate all context evidence content
        2. Calculate match score for each entity
        3. Detect competing entities
        4. Return unresolved if ambiguous or low confidence
        """
        from backend.context.context_window import EvidenceRole

        # Aggregate context content for scoring
        context_content = " ".join([
            ev.content for ev in context_window.evidence_list
        ])

        # Use strict resolution with context
        from .entity_resolution import resolve_entity_strict

        result = resolve_entity_strict(
            evidence_content=context_content,
            workspace_entities=workspace_entities,
            context_window=context_window.evidence_list,
            min_confidence=0.8
        )

        return result.entity_id, result.method

    async def _get_workspace_entities(
        self, workspace_id: UUID
    ) -> list[Any]:
        """Get all entities for a workspace."""
        from backend.shared.domain.memory_models import Entity
        stmt = select(Entity).where(Entity.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _create_reconstruction(
        self,
        interpretation: InterpretationResult,
        workspace_id: UUID,
        entity_id: UUID,
        parent_reconstruction_id: UUID | None,
        evidence_ids: list[UUID],
        is_unresolved: bool = False,
        resolution_method: str | None = None,
    ) -> Reconstruction | None:
        """Create Reconstruction from InterpretationResult."""
        decision_type = self._map_interpretation_to_decision_type(
            interpretation.interpretation_type
        )

        meta: dict[str, Any] = {}
        if is_unresolved:
            meta["entity_resolution"] = {"method": resolution_method, "status": "unresolved"}
        elif resolution_method:
            meta["entity_resolution"] = {"method": resolution_method}

        recon = Reconstruction(
            id=uuid4(),
            workspace_id=workspace_id,
            entity_id=entity_id,
            semantic_summary=interpretation.semantic_content,
            decision_type=decision_type,
            confidence=interpretation.confidence,
            evidence_refs=[str(eid) for eid in evidence_ids],
            evidence_count=len(evidence_ids),
            parent_reconstruction_id=parent_reconstruction_id,
            status="active",
        )

        try:
            self.session.add(recon)
            await self.session.flush()
            return recon
        except Exception as e:
            logger.error("Failed to create Reconstruction: %s", e)
            return None

    async def _create_candidate(
        self,
        interpretation: InterpretationResult,
        workspace_id: UUID,
        entity_id: UUID,
        evidence_ids: list[UUID],
        is_unresolved: bool = False,
        resolution_method: str | None = None,
    ) -> Candidate | None:
        """Create Candidate from InterpretationResult."""
        area_id = await self._get_default_area_id(workspace_id)

        candidate_type = self._map_interpretation_to_candidate_type(
            interpretation.interpretation_type
        )

        evidence_strength = interpretation.confidence

        meta: dict[str, Any] = {}
        if is_unresolved:
            meta["entity_resolution"] = {"method": resolution_method, "status": "unresolved"}
        elif resolution_method:
            meta["entity_resolution"] = {"method": resolution_method}

        candidate = Candidate(
            id=uuid4(),
            workspace_id=workspace_id,
            entity_id=entity_id,
            area_id=area_id,
            content=interpretation.semantic_content,
            candidate_type=candidate_type,
            evidence_source="semantic_interpretation",
            evidence_id=evidence_ids[0] if evidence_ids else uuid4(),
            evidence_chain=[str(eid) for eid in evidence_ids],
            evidence_count=len(evidence_ids),
            evidence_strength=evidence_strength,
            status="candidate",
            ingested_by="formation_service",
            verified_at=uuid4(),
        )

        try:
            self.session.add(candidate)
            await self.session.flush()
            return candidate
        except Exception as e:
            logger.error("Failed to create Candidate: %s", e)
            return None

    async def _bind_reconstruction_to_candidate(
        self,
        reconstruction_id: UUID,
        candidate_id: UUID,
    ) -> bool:
        """Bind Reconstruction to Candidate (1:1 relationship)."""
        from backend.shared.domain.memory_models import Reconstruction as ReconModel

        stmt = select(ReconModel).where(ReconModel.id == reconstruction_id)
        result = await self.session.execute(stmt)
        recon = result.scalar_one_or_none()

        if recon is None:
            logger.error("Reconstruction %s not found for binding", reconstruction_id)
            return False

        recon.candidate_id = candidate_id
        await self.session.flush()
        return True

    async def _get_default_area_id(self, workspace_id: UUID) -> UUID:
        """Get default area_id for workspace."""
        from backend.shared.domain.memory_models import Area

        stmt = select(Area).where(Area.workspace_id == workspace_id).limit(1)
        result = await self.session.execute(stmt)
        area = result.scalar_one_or_none()

        return area.id if area else uuid4()

    def _map_interpretation_to_decision_type(
        self, interpretation_type: InterpretationType
    ) -> str | None:
        """Map InterpretationType to Reconstruction.decision_type."""
        mapping = {
            InterpretationType.CONFIRM: "confirmation",
            InterpretationType.ADOPT: "adoption",
            InterpretationType.REJECT: "rejection",
            InterpretationType.CORRECT: "correction",
            InterpretationType.PREFERENCE: "preference",
            InterpretationType.DECISION: "decision",
            InterpretationType.INTENT: "intent",
            InterpretationType.CONSTRAINT: "constraint",
            InterpretationType.PARTIAL_CONFIRM: "partial_confirmation",
            InterpretationType.UNCERTAIN: "uncertain",
        }
        return mapping.get(interpretation_type)

    def _map_interpretation_to_candidate_type(
        self, interpretation_type: InterpretationType
    ) -> str:
        """Map InterpretationType to Candidate.candidate_type."""
        if interpretation_type in (
            InterpretationType.DECISION,
            InterpretationType.INTENT,
            InterpretationType.CONSTRAINT,
        ):
            return "belief"
        return "pattern"


class FormationPipeline:
    """Orchestrates the full Formation pipeline.

    Note: This class is kept for backward compatibility.
    Use FormationService directly for new code.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.service = FormationService(session)

    async def execute(
        self,
        interpretation: InterpretationResult,
        trigger_evidence_id: UUID,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        parent_reconstruction_id: UUID | None = None,
    ) -> FormationResult:
        """Execute the formation pipeline.

        Returns:
            FormationResult with success/failure status.
        """
        return await self.service.form(
            interpretation=interpretation,
            trigger_evidence_id=trigger_evidence_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
            parent_reconstruction_id=parent_reconstruction_id,
        )
