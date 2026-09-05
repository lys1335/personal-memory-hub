"""Historical Memory Evolution Service — Phase 21.7.

This service implements Historical Memory Evolution:
1. Topic status transitions (initial → active → evolved → superseded)
2. New Candidate vs Historical MemoryNode relationship detection
3. L2/L3 abstraction formation (if eligible)
4. Lineage preservation

Transaction: Uses the session provided by the caller.
Does NOT commit or rollback — that is the caller's responsibility.

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

from backend.shared.domain.evolution_result import (
    EvolutionResult,
    EvolutionDecision,
    RelationshipAction,
    TopicEvolutionResult,
)
from backend.repository.candidate_repository import CandidateRepository
from backend.repository.memory_node_repository import MemoryNodeRepository
from backend.repository.relationship_repository import RelationshipRepository
from backend.repository.topic_repository import TopicRepository
from backend.service.base import BaseService
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


class EvolutionService(BaseService):
    """Domain service for Historical Memory Evolution.
    
    This service is responsible for:
    1. Detecting relationships between new Candidates and historical MemoryNodes
    2. Managing Topic status transitions
    3. Forming L2/L3 abstractions from eligible Candidates
    
    Transaction: Uses the session provided by the caller.
    Does NOT commit or rollback — that is the caller's responsibility.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__("EvolutionService")
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
            
        Note: Does NOT commit — caller manages transaction.
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
        """Detect relationships between new Candidate and historical MemoryNodes."""
        actions: list[RelationshipAction] = []
        
        historical_nodes = await self.memory_repo.find_by_entity(
            entity_id=entity_id,
            workspace_id=workspace_id,
        ) if entity_id else []
        
        for node in historical_nodes:
            if node.status in ('superseded', 'deprecated', 'orphaned'):
                continue
            
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
        """Determine the relationship type between candidate and historical node."""
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
        
        if candidate.evidence_strength > historical_node.confidence * 0.8:
            return RelationshipAction(
                action="supersedes",
                target_node_id=historical_node.id,
                reason=f"Candidate supersedes historical node: {historical_node.id}",
                weight=0.7,
            )
        
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
        """Evolve Topic status based on new Candidate."""
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
            return "active"
        elif topic.status == "active":
            return "evolved"
        elif topic.status == "evolved":
            return "evolved"
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
            return EvolutionDecision(
                action="create_with_conflict",
                reason="Historical conflict detected",
                weight=0.8,
            )
        
        if any(a.is_supports for a in historical_results):
            return EvolutionDecision(
                decision_type='create_with_support',
                reason="Historical support detected",
                weight=0.6,
            )

        return EvolutionDecision(
            decision_type='create',
            reason="No historical relationships detected",
            weight=0.5,
        )
    
    async def _execute_evolution(
        self,
        decision: EvolutionDecision,
        candidate: Candidate,
        historical_results: list[RelationshipAction],
    ) -> None:
        """Execute evolution decision — create new MemoryNode and Relationships."""
        
        # Create new MemoryNode from Candidate
        memory_node = await self._create_memory_node(candidate)
        
        if memory_node is None:
            logger.error("Failed to create MemoryNode for candidate %s", candidate.id)
            return
        
        # Create relationships
        for action in historical_results:
            await self._create_relationship(
                source_node_id=memory_node.id,
                target_node_id=action.target_node_id,
                relationship_type=action.action,
            )
    
    async def _create_memory_node(
        self,
        candidate: Candidate,
    ) -> MemoryNode | None:
        """Create a new MemoryNode from Candidate."""
        from backend.shared.domain.memory_models import Area
        
        # Determine level based on candidate_type
        level = 2 if candidate.candidate_type == "pattern" else 3
        node_type = "Pattern" if level == 2 else "Belief"
        
        # Get area_id
        stmt = select(Area).where(Area.id == candidate.area_id).limit(1)
        result = await self.session.execute(stmt)
        area = result.scalar_one_or_none()
        
        node = MemoryNode(
            id=uuid4(),
            workspace_id=candidate.workspace_id,
            entity_id=candidate.entity_id,
            level=level,
            node_type=node_type,
            content=candidate.content,
            confidence=candidate.evidence_strength,
            status="active",
            source="evolution_service",
            metadata={
                "candidate_id": str(candidate.id),
                "evidence_ids": candidate.evidence_chain,
                "formed_at": datetime.now().isoformat(),
            },
        )
        
        try:
            self.session.add(node)
            await self.session.flush()
            return node
        except Exception as e:
            logger.error("Failed to create MemoryNode: %s", e)
            return None
    
    async def _create_relationship(
        self,
        *,
        source_node_id: UUID,
        target_node_id: UUID,
        relationship_type: str,
    ) -> bool:
        """Create a MemoryRelationship between two MemoryNodes."""
        from backend.shared.domain.memory_models import MemoryRelationship as RelModel
        
        rel = MemoryRelationship(
            id=uuid4(),
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship_type=relationship_type,
            confidence=0.7,
            created_at=datetime.now(),
        )
        
        try:
            self.session.add(rel)
            await self.session.flush()
            return True
        except Exception as e:
            logger.error("Failed to create relationship: %s", e)
            return False

    async def evolve_entity_history(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        min_l1_count: int = 3,
        min_avg_confidence: float = 0.8,
    ) -> list[dict]:
        """Evolve historical L1 MemoryNodes into L2 Patterns / L3 Beliefs.

        This method is called AFTER ReflectionService has created L1 nodes.
        It aggregates L1 nodes by entity and creates higher-level abstractions
        when threshold criteria are met.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional specific entity to evolve. If None, evolves all entities.
            min_l1_count: Minimum number of L1 nodes required (default: 3).
            min_avg_confidence: Minimum average confidence required (default: 0.8).

        Returns:
            List of evolution results with entity_id, level, node_id, rationale.
        """
        from backend.shared.domain.memory_models import MemoryNode as NodeModel

        results = []

        # Query L1 nodes grouped by entity
        query = text("""
            SELECT entity_id, COUNT(*) as l1_count, AVG(confidence) as avg_confidence
            FROM memory_nodes
            WHERE workspace_id = :workspace_id
              AND level = 1
              AND status = 'active'
              AND (:entity_id IS NULL OR entity_id = :entity_id)
            GROUP BY entity_id
            HAVING COUNT(*) >= :min_l1_count
               AND AVG(confidence) >= :min_avg_confidence
        """)

        result = await self.session.execute(query, {
            "workspace_id": str(workspace_id),
            "entity_id": str(entity_id) if entity_id else None,
            "min_l1_count": min_l1_count,
            "min_avg_confidence": min_avg_confidence,
        })

        entities_to_evolve = result.fetchall()

        for row in entities_to_evolve:
            ev_entity_id = row[0]
            l1_count = row[1]
            avg_confidence = float(row[2])

            # Get representative L1 nodes for this entity
            l1_query = text("""
                SELECT id, content, confidence
                FROM memory_nodes
                WHERE workspace_id = :workspace_id
                  AND entity_id = :entity_id
                  AND level = 1
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 10
            """)

            l1_result = await self.session.execute(l1_query, {
                "workspace_id": str(workspace_id),
                "entity_id": str(ev_entity_id),
            })
            l1_nodes = l1_result.fetchall()

            # Create L2 Pattern
            l2_node_id = uuid4()
            content_parts = [str(node[1])[:200] for node in l1_nodes if node[1]]
            aggregated_content = "; ".join(content_parts[:3]) if content_parts else f"Pattern for entity {ev_entity_id}"

            await self.session.execute(text("""
                INSERT INTO memory_nodes (
                    id, workspace_id, entity_id, level, node_type, content, summary,
                    confidence, importance, signal_strength, status, source, generated_by,
                    evidence_links, contradict_evidence, _meta, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :entity_id, 2, 'Pattern', :content, :summary,
                    :confidence, :importance, :signal_strength, 'active', 'evolution_service', 'evolution_service',
                    :evidence_links, '[]', '{}', NOW(), NOW()
                )
            """), {
                "id": str(l2_node_id),
                "workspace_id": str(workspace_id),
                "entity_id": str(ev_entity_id),
                "content": aggregated_content[:1000],
                "summary": f"Pattern: {l1_count} L1 observations aggregated",
                "confidence": avg_confidence,
                "importance": avg_confidence,
                "signal_strength": avg_confidence,
                "evidence_links": json.dumps([str(node[0]) for node in l1_nodes[:5]]),
            })

            # Create relationships from L2 to L1 nodes
            for l1_node in l1_nodes[:5]:
                await self.session.execute(text("""
                    INSERT INTO memory_relationships (
                        id, source_node_id, target_node_id, relationship_type,
                        confidence, created_at, updated_at
                    ) VALUES (
                        :rel_id, :source_id, :target_id, 'supports', :confidence, NOW(), NOW()
                    )
                """), {
                    "rel_id": str(uuid4()),
                    "source_id": str(l2_node_id),
                    "target_id": str(l1_node[0]),
                    "confidence": avg_confidence,
                })

            results.append({
                "entity_id": str(ev_entity_id),
                "level": 2,
                "node_id": str(l2_node_id),
                "l1_count": l1_count,
                "avg_confidence": round(avg_confidence, 3),
                "rationale": f"Created Pattern from {l1_count} L1 nodes with avg confidence {avg_confidence:.2f}",
            })

            logger.info(
                "Entity %s evolved to L2 Pattern: %d L1 nodes, avg_conf=%.3f",
                ev_entity_id, l1_count, avg_confidence,
            )

        return results
