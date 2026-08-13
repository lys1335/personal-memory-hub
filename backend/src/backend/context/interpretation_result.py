"""Interpretation Result — Phase 21.4 User-centric Semantic Interpretation.

This module defines the structured output of User-centric Semantic Interpretation.
It is consumed by Phase 21.5 (Reconstruction → Candidate formation).

Design:
- Pure data class, no business logic
- Tracks user ownership determination
- Supports partial confirmation (multiple semantic units)
- Includes confidence and rationale for auditability
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class InterpretationType(Enum):
    """Classification of user semantic intent."""
    
    # Positive user actions
    CONFIRM = "confirm"           # User confirms AI suggestion
    ADOPT = "adopt"              # User adopts AI proposal
    PREFERENCE = "preference"    # User expresses preference
    DECISION = "decision"        # User makes decision
    INTENT = "intent"            # User expresses future intention
    CONSTRAINT = "constraint"    # User expresses constraints/bounds
    
    # Negative user actions
    REJECT = "reject"            # User rejects AI suggestion
    CORRECT = "correct"          # User corrects AI understanding
    
    # Partial actions
    PARTIAL_CONFIRM = "partial_confirm"  # User accepts only part
    
    # Uncertain states
    UNCERTAIN = "uncertain"      # User is considering, not decided
    AMBIGUOUS = "ambiguous"      # Cannot reliably determine intent
    
    # No user fact
    NO_USER_FACT = "no_user_fact"  # Does not constitute user-owned semantic


class SourceType(Enum):
    """Evidence source type for lineage tracking."""
    TRIGGER = "trigger"          # The Evidence that triggered interpretation
    CONTEXT = "context"          # Evidence recalled from context
    HISTORICAL = "historical"    # Evidence from historical Reconstruction
    
    @classmethod
    def from_string(cls, value: str) -> SourceType:
        try:
            return cls(value)
        except ValueError:
            return cls.CONTEXT


@dataclass
class SemanticUnit:
    """A single user-owned semantic unit from partial confirmation."""
    
    subject: str                    # What the semantic is about
    action: InterpretationType      # What user did (confirm, reject, etc.)
    content: str                    # User-owned content summary
    confidence: float               # 0.0-1.0
    
    # Lineage
    source_evidence_ids: list[UUID] = field(default_factory=list)
    
    @property
    def is_confirmed(self) -> bool:
        """Check if this unit represents user confirmation/adoption."""
        return self.action in (
            InterpretationType.CONFIRM,
            InterpretationType.ADOPT,
        )
    
    @property
    def is_rejected(self) -> bool:
        """Check if this unit represents user rejection."""
        return self.action == InterpretationType.REJECT
    
    @property
    def is_corrected(self) -> bool:
        """Check if this unit represents user correction."""
        return self.action == InterpretationType.CORRECT


@dataclass
class InterpretationResult:
    """Result of User-centric Semantic Interpretation.
    
    This is the OUTPUT of Phase 21.4.
    It is consumed by Phase 21.5 for Reconstruction formation.
    
    Key invariants:
    - user_owned indicates whether this is truly user-owned
    - semantic_units allows partial confirmation decomposition
    - referenced_assistant_evidence_ids tracks AI context
    - rationale provides audit trail
    """
    
    # Input reference
    trigger_evidence_id: UUID
    workspace_id: UUID
    
    # Interpretation result
    interpretation_type: InterpretationType
    user_owned: bool
    semantic_content: str  # User-owned summary
    confidence: float  # 0.0-1.0
    
    # Lineage
    source_evidence_ids: list[UUID] = field(default_factory=list)
    referenced_assistant_evidence_ids: list[UUID] = field(default_factory=list)
    
    # Partial confirmation support
    semantic_units: list[SemanticUnit] = field(default_factory=list)
    
    # Uncertainty tracking
    uncertainty: float = field(init=False)  # Computed: 1.0 - confidence

    @property
    def computed_uncertainty(self) -> float:
        """Uncertainty is inverse of confidence."""
        return round(1.0 - self.confidence, 2)

    # Override __post_init__ to compute uncertainty
    def __post_init__(self):
        self.uncertainty = self.computed_uncertainty
    
    # Audit trail
    rationale: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_user_fact(self) -> bool:
        """Check if this interpretation produced a user-owned fact."""
        return self.user_owned and self.interpretation_type != InterpretationType.NO_USER_FACT
    
    @property
    def is_confirmed(self) -> bool:
        """Check if user confirmed something."""
        return self.interpretation_type in (
            InterpretationType.CONFIRM,
            InterpretationType.ADOPT,
        )
    
    @property
    def is_rejected(self) -> bool:
        """Check if user rejected something."""
        return self.interpretation_type == InterpretationType.REJECT
    
    @property
    def is_ambiguous(self) -> bool:
        """Check if interpretation is ambiguous."""
        return self.interpretation_type == InterpretationType.AMBIGUOUS
    
    @property
    def is_no_user_fact(self) -> bool:
        """Check if this does not constitute user fact."""
        return self.interpretation_type == InterpretationType.NO_USER_FACT
    
    def get_summary(self) -> dict[str, Any]:
        """Get interpretation summary for logging."""
        return {
            "trigger_evidence_id": str(self.trigger_evidence_id),
            "interpretation_type": self.interpretation_type.value,
            "user_owned": self.user_owned,
            "semantic_content": self.semantic_content[:100] if self.semantic_content else "",
            "confidence": self.confidence,
            "semantic_units_count": len(self.semantic_units),
            "referenced_assistant_count": len(self.referenced_assistant_evidence_ids),
        }


@dataclass
class InterpretationContext:
    """Input context for semantic interpretation.
    
    This wraps the ContextWindow from Phase 21.3 with additional metadata
    needed for interpretation.
    """
    
    # From ContextWindow
    trigger_evidence_id: UUID
    workspace_id: UUID
    evidence_list: list[Any]  # EvidenceContext from Phase 21.3
    token_count: int
    
    # Additional metadata
    current_time: datetime = field(default_factory=datetime.now)
    previous_interpretations: list[InterpretationResult] = field(default_factory=list)
    
    @property
    def trigger_evidence(self) -> Any | None:
        """Get the trigger Evidence from context."""
        for evidence in self.evidence_list:
            if evidence.evidence_id == self.trigger_evidence_id:
                return evidence
        return None
    
    @property
    def assistant_evidences(self) -> list[Any]:
        """Get all assistant Evidence in context."""
        from backend.context.context_window import EvidenceRole
        return [
            e for e in self.evidence_list
            if hasattr(e, 'role') and e.role == EvidenceRole.ASSISTANT
        ]
    
    @property
    def user_evidences(self) -> list[Any]:
        """Get all user Evidence in context."""
        from backend.context.context_window import EvidenceRole
        return [
            e for e in self.evidence_list
            if hasattr(e, 'role') and e.role == EvidenceRole.USER
        ]
