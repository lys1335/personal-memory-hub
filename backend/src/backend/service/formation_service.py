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
    ) -> None:
        self.success = success
        self.reconstruction_id = reconstruction_id
        self.candidate_id = candidate_id
        self.interpretation = interpretation
        self.entity_id = entity_id
        self.error = error
    
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
    ) -> FormationResult:
        """Form Reconstruction and Candidate from InterpretationResult.
        
        Args:
            interpretation: Output from Phase 21.4 semantic interpretation.
            trigger_evidence_id: The Evidence that triggered this formation.
            workspace_id: Workspace scope.
            entity_id: Optional entity (resolved from evidence if not provided).
            parent_reconstruction_id: Optional parent for version chain.
            
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
        
        # Step 2: Resolve entity_id if not provided
        if entity_id is None:
            entity_id = await self._resolve_entity(trigger_evidence_id, workspace_id)
            if entity_id is None:
                return FormationResult(
                    success=False,
                    error="Could not resolve entity_id from trigger evidence",
                )
        
        # Step 3: Create Reconstruction
        reconstruction = await self._create_reconstruction(
            interpretation=interpretation,
            workspace_id=workspace_id,
            entity_id=entity_id,
            parent_reconstruction_id=parent_reconstruction_id,
            evidence_ids=interpretation.source_evidence_ids,
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
    
    async def _create_reconstruction(
        self,
        interpretation: InterpretationResult,
        workspace_id: UUID,
        entity_id: UUID,
        parent_reconstruction_id: UUID | None,
        evidence_ids: list[UUID],
    ) -> Reconstruction | None:
        """Create Reconstruction from InterpretationResult."""
        decision_type = self._map_interpretation_to_decision_type(
            interpretation.interpretation_type
        )
        
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
    ) -> Candidate | None:
        """Create Candidate from InterpretationResult."""
        area_id = await self._get_default_area_id(workspace_id)
        
        candidate_type = self._map_interpretation_to_candidate_type(
            interpretation.interpretation_type
        )
        
        evidence_strength = interpretation.confidence
        
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
