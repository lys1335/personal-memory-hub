"""Evolution Result — Phase 21.7 Historical Memory Evolution.

This module defines the structured output of Historical Memory Evolution.
It captures the relationship between new Candidates and historical MemoryNodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class RelationshipAction:
    """Action to take based on historical relationship detection."""
    
    action: str  # 'supersedes', 'contradicts', 'supports', 'refines'
    target_node_id: UUID
    reason: str
    weight: float = 1.0
    
    @property
    def is_supersedes(self) -> bool:
        return self.action == 'supersedes'
    
    @property
    def is_contradicts(self) -> bool:
        return self.action == 'contradicts'
    
    @property
    def is_supports(self) -> bool:
        return self.action == 'supports'
    
    @property
    def is_refines(self) -> bool:
        return self.action == 'refines'


@dataclass
class EvolutionResult:
    """Result of Historical Memory Evolution.
    
    This captures:
    1. Whether new Candidate conflicts with historical Memory
    2. What action to take (supersede, contradict, support, refine)
    3. Lineage tracking
    """
    
    candidate_id: UUID
    workspace_id: UUID
    entity_id: UUID | None = None
    
    # Evolution actions detected
    actions: list[RelationshipAction] = field(default_factory=list)
    
    # Summary
    has_conflict: bool = False
    has_supersession: bool = False
    has_contradiction: bool = False
    has_support: bool = False
    has_refinement: bool = False
    
    # Metadata
    confidence: float = 0.0
    rationale: str = ""
    created_at: str = ""
    
    @property
    def needs_action(self) -> bool:
        """Whether any evolution action is needed."""
        return len(self.actions) > 0
    
    @property
    def is_consistent(self) -> bool:
        """Whether new Candidate is consistent with history."""
        return not self.has_conflict and not self.has_contradiction
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of evolution result."""
        return {
            "candidate_id": str(self.candidate_id),
            "workspace_id": str(self.workspace_id),
            "has_conflict": self.has_conflict,
            "has_supersession": self.has_supersession,
            "has_contradiction": self.has_contradiction,
            "actions_count": len(self.actions),
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


@dataclass
class EvolutionDecision:
    """Decision made during evolution process."""
    
    decision_type: str  # 'create_memory', 'mark_superseded', 'mark_contradicted', 'skip'
    target_node_id: UUID | None = None
    new_node_id: UUID | None = None
    reason: str = ""
    weight: float = 0.5
    
    @property
    def should_create_memory(self) -> bool:
        return self.decision_type == 'create_memory'
    
    @property
    def should_supersede(self) -> bool:
        return self.decision_type == 'mark_superseded'
    
    @property
    def should_contradict(self) -> bool:
        return self.decision_type == 'mark_contradicted'


@dataclass
class TopicEvolutionResult:
    """Result of Topic evolution (status transition)."""
    
    topic_id: UUID
    old_status: str
    new_status: str
    reason: str
    triggered_by: str  # 'new_candidate', 'user_action', 'auto_evolution'
    
    @property
    def is_active(self) -> bool:
        return self.new_status == 'active'
    
    @property
    def is_superseded(self) -> bool:
        return self.new_status == 'superseded'
