"""Historical Memory Evolution Engine — Phase 21.7.

This engine implements Historical Memory Evolution:
1. Topic status transitions (initial → active → evolved → superseded)
2. New Candidate vs Historical MemoryNode relationship detection
3. L2/L3 abstraction formation (if eligible)
4. Lineage preservation

Design constraints:
- Historical objects are IMMUTABLE (no UPDATE/DELETE)
- Evolution creates NEW objects + RELATIONSHIPS
- Phase 20/21.1-21.6 frozen design is NOT modified
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.evolution.evolution_result import (
    EvolutionResult,
    EvolutionDecision,
    RelationshipAction,
    TopicEvolutionResult,
)
from backend.repository.candidate_repository import CandidateRepository
from backend.repository.memory_node_repository import MemoryNodeRepository
from backend.repository.relationship_repository import RelationshipRepository
from backend.repository.topic_repository import TopicRepository
from backend.shared.domain.memory_models import (
    Candidate,
    MemoryNode,
    MemoryRelationship,
    Topic,
)

logger = logging.getLogger(__name__)

# Valid Topic status transitions
VALID_TRANSITIONS: dict[str, list[str]] = {
    "initial": ["active", "archived"],
    "active": ["evolved", "superseded", "archived"],
    "evolved": ["superseded", "archived"],
    "superseded": ["archived"],
    "archived": [],  # Terminal state
}


class EvolutionEngine:
    """Domain engine for Historical Memory Evolution.
    
    This engine is responsible for:
    1. Detecting relationships between new Candidates and historical MemoryNodes
    2. Managing Topic status transitions
    3. Forming L2/L3 abstractions from eligible Candidates
    """
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.candidate_repo = CandidateRepository(session)
        self.memory_repo = MemoryNodeRepository(session)
        self.relationship_repo = RelationshipRepository(session)
        self.topic_repo = TopicRepository(session)
    
    async def evolve(
        self,
        *,
        candidate_id: UUID,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        topic_ids: list[UUID] | None = None,
    ) -> EvolutionResult:
        """Execute historical memory evolution for a new Candidate.
        
        Args:
            candidate_id: The new Candidate to evolve.
            workspace_id: Workspace scope.
            entity_id: Optional entity ID.
            topic_ids: Optional list of Topic IDs.
            
        Returns:
            EvolutionResult with actions and decisions.
        """
        # Step 1: Load candidate
        candidate = await self.candidate_repo.find_by_id(candidate_id)
        if candidate is None:
            return EvolutionResult(
                candidate_id=candidate_id,
                workspace_id=workspace_id,
                rationale="Candidate not found",
            )
        
        # Step 2: Detect historical relationships
        historical_results = await self._detect_historical_relationships(
            candidate=candidate,
            workspace_id=workspace_id,
            entity_id=entity_id,
        )
        
        # Step 3: Process Topic evolution
        topic_result = None
        if topic_ids:
            topic_result = await self._evolve_topics(
                topic_ids=topic_ids,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
            )
        
        # Step 4: Make evolution decision
        decision = await self._make_evolution_decision(
            candidate=candidate,
            historical_results=historical_results,
            topic_result=topic_result,
        )
        
        # Step 5: Execute decision (create relationships, not modify existing)
        await self._execute_evolution(decision, candidate, historical_results)
        
        # Build result
        result = EvolutionResult(
            candidate_id=candidate_id,
            workspace_id=workspace_id,
            actions=historical_results,
            has_conflict=any(a.is_supersedes or a.is_contradicts for a in historical_results),
            has_supersession=any(a.is_supersedes for a in historical_results),
            has_contradiction=any(a.is_contradicts for a in historical_results),
            has_support=any(a.is_supports for a in historical_results),
            confidence=decision.weight if decision else 0.5,
            rationale=decision.reason if decision else "",
            created_at=datetime.now().isoformat(),
        )
        
        logger.info(
            "Evolution complete: candidate=%s, conflict=%s, decisions=%d",
            candidate_id,
            result.has_conflict,
            len(result.actions),
        )
        
        return result
    
    async def _detect_historical_relationships(
        self,
        *,
        candidate: Candidate,
        workspace_id: UUID,
        entity_id: UUID | None,
    ) -> list[RelationshipAction]:
        """Detect relationships between new Candidate and historical MemoryNodes.
        
        Returns:
            List of RelationshipAction to take.
        """
        actions: list[RelationshipAction] = []
        
        # Query historical MemoryNodes for same entity/workspace
        historical_nodes = await self.memory_repo.find_by_entity(
            entity_id=entity_id,
            workspace_id=workspace_id,
        ) if entity_id else []
        
        for node in historical_nodes:
            if node.status in ('superseded', 'deprecated', 'orphaned'):
                continue  # Skip already superseded nodes
            
            # Determine relationship type
            action = await self._determine_relationship(
                candidate=candidate,
                historical_node=node,
            )
            
            if action:
                actions.append(action)
        
        return actions
    
    async def _determine_relationship(
        self,
        *,
        candidate: Candidate,
        historical_node: MemoryNode,
    ) -> RelationshipAction | None:
        """Determine the relationship type between candidate and historical node.
        
        Logic:
        - If content is similar and confidence is higher → supersedes
        - If content is contradictory → contradicts
        - If content is supporting → supports
        - If content is refinement → refines
        """
        # Simple heuristic: compare semantic similarity
        # In production, this would use embedding comparison
        
        # Check for contradiction keywords
        contradiction_patterns = ["not", "no", "never", "wrong", "incorrect", "相反"]
        candidate_lower = candidate.content.lower()
        historical_lower = historical_node.content.lower()
        
        has_contradiction = any(
            p in candidate_lower for p in contradiction_patterns
        ) and any(
            p in historical_lower for p in ["决定", "使用", "选择"]
        )
        
        if has_contradiction:
            return RelationshipAction(
                action="contradicts",
                target_node_id=historical_node.id,
                reason=f"Candidate contradicts historical node: {historical_node.id}",
                weight=0.9,
            )
        
        # Check for supersession (same topic, newer evidence)
        if candidate.evidence_strength > historical_node.confidence * 0.8:
            return RelationshipAction(
                action="supersedes",
                target_node_id=historical_node.id,
                reason=f"Candidate supersedes historical node: {historical_node.id}",
                weight=0.7,
            )
        
        # Check for support
        if candidate.evidence_strength > 0.5:
            return RelationshipAction(
                action="supports",
                target_node_id=historical_node.id,
                reason=f"Candidate supports historical node: {historical_node.id}",
                weight=0.5,
            )
        
        return None
    
    async def _evolve_topics(
        self,
        *,
        topic_ids: list[UUID],
        workspace_id: UUID,
        candidate_id: UUID,
    ) -> list[TopicEvolutionResult]:
        """Evolve Topic status based on new Candidate.
        
        Rules:
        - initial → active: When first evidence supports
        - active → evolved: When refinement evidence arrives
        - evolved → superseded: When new version supersedes
        """
        results: list[TopicEvolutionResult] = []
        
        for topic_id in topic_ids:
            topic = await self.topic_repo.get_by_id(topic_id)
            if topic is None:
                continue
            
            old_status = topic.status
            new_status = await self._determine_topic_status(
                topic=topic,
                candidate_id=candidate_id,
            )
            
            if old_status != new_status and new_status in VALID_TRANSITIONS.get(old_status, []):
                # Valid transition
                topic.status = new_status
                await self.session.flush()
                
                results.append(TopicEvolutionResult(
                    topic_id=topic_id,
                    old_status=old_status,
                    new_status=new_status,
                    reason=f"New candidate {candidate_id} triggered status change",
                    triggered_by="new_candidate",
                ))
        
        return results
    
    async def _determine_topic_status(
        self,
        *,
        topic: Topic,
        candidate_id: UUID,
    ) -> str:
        """Determine new Topic status based on Candidate evidence."""
        if topic.status == "initial":
            # First candidate for this topic → active
            return "active"
        elif topic.status == "active":
            # Refinement evidence → evolved
            return "evolved"
        elif topic.status == "evolved":
            # New version from different Reconstruction → superseded
            # (Would need to check if this candidate is from a new version)
            return "evolved"  # Stay evolved until explicitly superseded
        return topic.status
    
    async def _make_evolution_decision(
        self,
        *,
        candidate: Candidate,
        historical_results: list[RelationshipAction],
        topic_result: list[TopicEvolutionResult] | None,
    ) -> EvolutionDecision:
        """Make evolution decision based on detected relationships."""
        
        has_conflict = any(a.is_supersedes or a.is_contradicts for a in historical_results)
        
        if has_conflict:
            # New evidence conflicts with history
            # Decision: Create new MemoryNode, mark old as superseded/contradicted
            return EvolutionDecision(
                decision_type="create_memory",
                reason="Conflict detected with historical memory",
                weight=0.8,
            )
        
        if not historical_results:
            # No historical relationship
            # Decision: Create new MemoryNode
            return EvolutionDecision(
                decision_type="create_memory",
                reason="No historical relationship detected",
                weight=0.5,
            )
        
        # Supports or refines
        return EvolutionDecision(
            decision_type="skip",
            reason="Candidate supports or refines existing memory",
            weight=0.3,
        )
    
    async def _execute_evolution(
        self,
        decision: EvolutionDecision,
        candidate: Candidate,
        historical_results: list[RelationshipAction],
    ) -> None:
        """Execute the evolution decision."""
        
        if not decision.should_create_memory:
            logger.info("Evolution decision: skip (no new memory creation)")
            return
        
        # Step 1: Create MemoryNode from Candidate
        memory_node = await self._create_memory_node(candidate)
        
        # Step 2: Create relationships for historical conflicts
        for action in historical_results:
            if action.is_supersedes:
                # Mark old node as superseded via relationship
                await self._create_relationship(
                    source_node_id=memory_node.id,
                    target_node_id=action.target_node_id,
                    relationship_type="supersedes",
                    weight=action.weight,
                    workspace_id=candidate.workspace_id,
                )
            elif action.is_contradicts:
                await self._create_relationship(
                    source_node_id=memory_node.id,
                    target_node_id=action.target_node_id,
                    relationship_type="contradicts",
                    weight=action.weight,
                    workspace_id=candidate.workspace_id,
                )
            elif action.is_supports:
                await self._create_relationship(
                    source_node_id=memory_node.id,
                    target_node_id=action.target_node_id,
                    relationship_type="supports",
                    weight=action.weight,
                    workspace_id=candidate.workspace_id,
                )
    
    async def _create_memory_node(self, candidate: Candidate) -> MemoryNode:
        """Create MemoryNode from Candidate.
        
        Mapping:
        - Candidate (pattern/belief) → MemoryNode (L2/L3)
        - evidence_chain → evidence_links
        - evidence_strength → confidence
        """
        # Determine level based on candidate_type
        level = 2 if candidate.candidate_type == "pattern" else 3
        node_type = "Pattern" if level == 2 else "Belief"
        
        node = MemoryNode(
            id=uuid4(),
            workspace_id=candidate.workspace_id,
            entity_id=candidate.entity_id,
            level=level,
            node_type=node_type,
            content=candidate.content,
            summary=candidate.content[:200] if len(candidate.content) > 200 else candidate.content,
            confidence=candidate.evidence_strength,
            importance=0.5,  # Default importance
            signal_strength=candidate.evidence_strength,
            status="active",
            source="ai_reflect",
            generated_by="evolution_engine",
            evidence_links=candidate.evidence_chain if candidate.evidence_chain else [],
            contradict_evidence=[],
            _meta={"candidate_id": str(candidate.id)},
        )
        
        self.session.add(node)
        await self.session.flush()
        
        logger.info("Created MemoryNode: %s from Candidate: %s", node.id, candidate.id)
        return node
    
    async def _create_relationship(
        self,
        *,
        source_node_id: UUID,
        target_node_id: UUID,
        relationship_type: str,
        weight: float,
        workspace_id: UUID,
    ) -> MemoryRelationship:
        """Create MemoryRelationship between two MemoryNodes."""
        
        rel = MemoryRelationship(
            id=uuid4(),
            workspace_id=workspace_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship_type=relationship_type,
            contribution_weight=weight,
            _meta={},
        )
        
        self.session.add(rel)
        await self.session.flush()
        
        logger.info(
            "Created relationship: %s --[%s]--> %s",
            source_node_id,
            relationship_type,
            target_node_id,
        )
        
        return rel


class TopicEvolutionService:
    """Service for Topic evolution (status transitions)."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TopicRepository(session)
    
    async def transition_status(
        self,
        *,
        topic_id: UUID,
        new_status: str,
        reason: str,
        triggered_by: str,
    ) -> TopicEvolutionResult:
        """Transition Topic status with validation.
        
        Args:
            topic_id: Topic to transition.
            new_status: Target status.
            reason: Reason for transition.
            triggered_by: Who triggered (new_candidate, user_action, auto_evolution).
            
        Returns:
            TopicEvolutionResult.
            
        Raises:
            ValueError: If transition is invalid.
        """
        topic = await self.repo.get_by_id(topic_id)
        if topic is None:
            raise ValueError(f"Topic {topic_id} not found")
        
        old_status = topic.status
        
        # Validate transition
        valid_next = VALID_TRANSITIONS.get(old_status, [])
        if new_status not in valid_next:
            raise ValueError(
                f"Invalid transition: {old_status} -> {new_status}. "
                f"Valid transitions from {old_status}: {valid_next}"
            )
        
        # Execute transition
        topic.status = new_status
        await self.session.flush()
        
        logger.info(
            "Topic %s status: %s -> %s (reason: %s)",
            topic_id,
            old_status,
            new_status,
            reason,
        )
        
        return TopicEvolutionResult(
            topic_id=topic_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            triggered_by=triggered_by,
        )
    
    async def get_valid_transitions(self, status: str) -> list[str]:
        """Get valid next statuses for a given status."""
        return VALID_TRANSITIONS.get(status, [])
