"""Context Window formation logic for Phase 21.3.

This module implements the Context Window formation algorithm:
1. Recall trigger Evidence
2. Expand to related Evidence (temporal + entity)
3. Handle short confirmations
4. Recall historical Reconstructions
5. Apply budget control
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.context.context_window import (
    ContextWindow,
    EvidenceContext,
    EvidenceRole,
    ContextBoundary,
    classify_role,
    classify_role_from_evidence_type,
    estimate_tokens,
    BUDGET_DEFAULT,
    BUDGET_HARD_LIMIT,
    SHORT_CONFIRMATION_MAX_CHARS,
    TEMPORAL_WINDOW_SHORT,
    TEMPORAL_WINDOW_MEDIUM,
    TEMPORAL_WINDOW_LONG,
)
from backend.shared.domain.memory_models import Evidence, Reconstruction


class ContextWindowFormulator:
    """Formulates Context Windows for Evidence analysis.
    
    The Context Window is TEMPORARY and not persisted.
    It is used to select relevant Evidence before forming a Reconstruction.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize the context window formulator.
        
        Args:
            session: Database session.
        """
        self.session = session
    
    async def formulate(
        self,
        trigger_evidence_id: UUID,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        budget: int = BUDGET_DEFAULT,
        include_reconstruction_recall: bool = True,
    ) -> ContextWindow:
        """Formulate a Context Window for the trigger Evidence.
        
        Args:
            trigger_evidence_id: The Evidence that triggered this context formation.
            workspace_id: Workspace scope.
            entity_id: Optional entity filter.
            budget: Token budget (default 4000, hard limit 8000).
            include_reconstruction_recall: Whether to include historical Reconstructions.
            
        Returns:
            Formulated Context Window.
        """
        context = ContextWindow(
            trigger_evidence_id=trigger_evidence_id,
            workspace_id=workspace_id,
        )
        
        # Step 1: Get trigger Evidence
        trigger = await self._get_trigger_evidence(trigger_evidence_id, workspace_id)
        if trigger is None:
            context.boundary = ContextBoundary.HARD
            context.boundary_reason = "Trigger evidence not found"
            return context
        
        # Add trigger Evidence
        trigger_context = self._evidence_to_context(trigger)
        if not context.add_evidence(trigger_context):
            return context
        
        # Step 2: Check if short confirmation needs expansion
        if trigger_context.is_user_confirmation and trigger_context.is_short:
            context = await self._expand_short_confirmation(
                context, trigger_context, workspace_id, entity_id
            )
        
        # Step 3: Temporal + entity recall
        context = await self._recall_temporal_context(
            context, trigger_context, workspace_id, entity_id
        )
        
        # Step 4: Reconstruction recall
        if include_reconstruction_recall:
            context = await self._recall_reconstructions(
                context, workspace_id, entity_id
            )
        
        # Step 5: Apply budget
        context = await self._apply_budget(context, budget)
        
        return context
    
    async def _get_trigger_evidence(
        self, evidence_id: UUID, workspace_id: UUID
    ) -> Evidence | None:
        """Get the trigger Evidence."""
        stmt = select(Evidence).where(
            Evidence.id == evidence_id,
            Evidence.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def _evidence_to_context(self, evidence: Evidence) -> EvidenceContext:
        """Convert Evidence to EvidenceContext."""
        # Use evidence_type as source of truth, fallback to _meta['role']
        role = classify_role_from_evidence_type(evidence.evidence_type)
        if role == EvidenceRole.UNKNOWN:
            role = classify_role(evidence._meta)
        content = evidence.content or ""
        token_count = estimate_tokens(content)
        
        return EvidenceContext(
            evidence_id=evidence.id,
            content=content,
            role=role,
            created_at=evidence.created_at,
            entity_id=evidence.entity_id,
            workspace_id=evidence.workspace_id,
            importance=evidence.importance,
            token_count=token_count,
            raw_evidence={
                "id": str(evidence.id),
                "type": evidence.evidence_type,
                "source": evidence.source,
            },
        )
    
    async def _expand_short_confirmation(
        self,
        context: ContextWindow,
        trigger: EvidenceContext,
        workspace_id: UUID,
        entity_id: UUID | None,
    ) -> ContextWindow:
        """Expand context for short user confirmations.
        
        When user sends a short confirmation like "对，就这样",
        we need to look backward to find the preceding AI suggestion.
        """
        # Find recent Evidence from same entity/workspace
        stmt = select(Evidence).where(
            Evidence.workspace_id == workspace_id,
            Evidence.created_at < trigger.created_at,
        )
        
        if entity_id:
            stmt = stmt.where(Evidence.entity_id == entity_id)
        
        stmt = stmt.order_by(Evidence.created_at.desc()).limit(10)
        result = await self.session.execute(stmt)
        recent_evidences = result.scalars().all()
        
        # Look backward for related Evidence
        for evidence in recent_evidences:
            if context.has_duplicate(evidence.id):
                continue
            
            # Check temporal proximity (within 30 minutes)
            time_diff = (trigger.created_at - evidence.created_at).total_seconds()
            if time_diff > TEMPORAL_WINDOW_SHORT:
                continue
            
            evidence_context = self._evidence_to_context(evidence)
            
            # Prefer assistant Evidence before user confirmation
            if evidence_context.role == EvidenceRole.ASSISTANT:
                if context.add_evidence(evidence_context):
                    context.recall_strategy.append("short_confirmation_expansion")
                    context.short_expansion_applied = True
            elif evidence_context.role == EvidenceRole.USER:
                # Add user Evidence that's temporally close
                if context.add_evidence(evidence_context):
                    context.recall_strategy.append("temporal_user_evidence")
        
        return context
    
    async def _recall_temporal_context(
        self,
        context: ContextWindow,
        trigger: EvidenceContext,
        workspace_id: UUID,
        entity_id: UUID | None,
    ) -> ContextWindow:
        """Recall Evidence within temporal and entity proximity."""
        # Get Evidence within temporal window
        time_window = TEMPORAL_WINDOW_MEDIUM
        stmt = select(Evidence).where(
            Evidence.workspace_id == workspace_id,
            Evidence.created_at >= trigger.created_at - __import__('datetime').timedelta(seconds=time_window),
            Evidence.created_at <= trigger.created_at,
        )
        
        if entity_id:
            stmt = stmt.where(Evidence.entity_id == entity_id)
        
        stmt = stmt.order_by(Evidence.created_at.asc())
        result = await self.session.execute(stmt)
        evidences = result.scalars().all()
        
        for evidence in evidences:
            if context.has_duplicate(evidence.id):
                continue
            
            evidence_context = self._evidence_to_context(evidence)
            
            # Prioritize by role and importance
            if evidence_context.role in (EvidenceRole.USER, EvidenceRole.ASSISTANT):
                if context.add_evidence(evidence_context):
                    context.recall_strategy.append("temporal_recall")
        
        return context
    
    async def _recall_reconstructions(
        self,
        context: ContextWindow,
        workspace_id: UUID,
        entity_id: UUID | None,
    ) -> ContextWindow:
        """Recall historical Reconstruction summaries for context."""
        stmt = select(Reconstruction).where(
            Reconstruction.workspace_id == workspace_id,
            Reconstruction.status.in_(["active", "updated"]),
        )
        
        if entity_id:
            stmt = stmt.where(Reconstruction.entity_id == entity_id)
        
        stmt = stmt.order_by(Reconstruction.created_at.desc()).limit(5)
        result = await self.session.execute(stmt)
        reconstructions = result.scalars().all()
        
        for recon in reconstructions:
            # Add reconstruction summary as synthetic evidence
            summary_content = f"[Reconstruction] {recon.semantic_summary}"
            token_count = estimate_tokens(summary_content)
            
            if context.token_count + token_count > BUDGET_HARD_LIMIT:
                break
            
            synthetic = EvidenceContext(
                evidence_id=recon.id,  # Use reconstruction ID as marker
                content=summary_content,
                role=EvidenceRole.SYSTEM,
                created_at=recon.created_at,
                entity_id=recon.entity_id,
                workspace_id=recon.workspace_id,
                importance=recon.confidence,
                token_count=token_count,
                raw_evidence={
                    "type": "reconstruction_summary",
                    "reconstruction_id": str(recon.id),
                },
            )
            
            if context.add_evidence(synthetic):
                context.reconstruction_recall_count += 1
                context.recall_strategy.append("reconstruction_recall")
        
        return context
    
    async def _apply_budget(
        self, context: ContextWindow, budget: int
    ) -> ContextWindow:
        """Apply budget control to context window.
        
        If over budget, trim from the oldest Evidence.
        """
        if context.token_count <= budget:
            return context
        
        # Trim oldest Evidence first (keeping trigger Evidence)
        trigger_id = context.trigger_evidence_id
        trimmed = []
        
        for evidence in reversed(context.evidence_list):
            if evidence.evidence_id == trigger_id:
                trimmed.insert(0, evidence)
                continue
            
            if context.token_count - evidence.token_count <= budget:
                context.token_count -= evidence.token_count
                context.boundary = ContextBoundary.HARD
                context.boundary_reason = f"Trimmed to budget ({budget} tokens)"
            else:
                trimmed.append(evidence)
        
        context.evidence_list = list(reversed(trimmed))
        return context
