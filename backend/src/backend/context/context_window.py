"""Context Window components for Phase 21.3.

Context Window is a TEMPORARY, non-persistent selection of Evidence
used to understand the Trigger Evidence before forming a Reconstruction.

Design:
- Hybrid recall: temporal + entity + reconstruction
- Budget control: default 4000 tokens, hard limit 8000
- Short confirmation expansion: extends context for brief user inputs
- Role handling: both user and assistant Evidence allowed
- Immutability: Evidence is never modified
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class EvidenceRole(Enum):
    """Evidence role classification."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ContextBoundary(Enum):
    """Context window boundary types."""
    HARD = "hard"  # Budget limit reached
    TEMPORAL = "temporal"  # Time gap exceeded
    ENTITY = "entity"  # Entity changed
    RECONSTRUCTION = "reconstruction"  # New reconstruction version


@dataclass
class EvidenceContext:
    """Evidence entry with context metadata."""

    evidence_id: UUID
    content: str
    role: EvidenceRole
    created_at: datetime
    entity_id: UUID
    workspace_id: UUID
    importance: float
    token_count: int = 0

    # Original Evidence reference
    raw_evidence: dict[str, Any] | None = None

    @property
    def is_short(self) -> bool:
        """Check if evidence is a short confirmation (<=50 chars)."""
        return len(self.content.strip()) <= 50

    @property
    def is_user_confirmation(self) -> bool:
        """Check if this looks like a user confirmation."""
        if self.role != EvidenceRole.USER:
            return False

        confirm_patterns = ["对", "是的", "好的", "没错", "就这样",
                          "ok", "okay", "yes", "yes.", "yeah"]
        content_lower = self.content.strip().lower()
        return any(pattern in content_lower for pattern in confirm_patterns)


@dataclass
class ContextWindow:
    """Context Window for Evidence selection.

    This is a temporary construct, not persisted.
    Only evidence_refs are stored in Reconstruction.
    """

    trigger_evidence_id: UUID
    workspace_id: UUID
    evidence_list: list[EvidenceContext] = field(default_factory=list)
    token_count: int = 0
    boundary: ContextBoundary | None = None
    boundary_reason: str | None = None

    # Context metadata
    recall_strategy: list[str] = field(default_factory=list)
    short_expansion_applied: bool = False
    reconstruction_recall_count: int = 0

    @property
    def is_full(self) -> bool:
        """Check if context window is at or over budget."""
        return self.token_count >= BUDGET_HARD_LIMIT

    @property
    def is_empty(self) -> bool:
        """Check if context window is empty."""
        return len(self.evidence_list) == 0

    def add_evidence(self, evidence: EvidenceContext) -> bool:
        """Add evidence to context window with budget check.

        Returns:
            True if added successfully, False if over budget.
        """
        new_token_count = self.token_count + evidence.token_count

        # Hard budget limit
        if new_token_count > BUDGET_HARD_LIMIT:
            self.boundary = ContextBoundary.HARD
            self.boundary_reason = f"Token limit exceeded ({new_token_count} > {BUDGET_HARD_LIMIT})"
            return False

        self.evidence_list.append(evidence)
        self.token_count = new_token_count
        return True

    def has_duplicate(self, evidence_id: UUID) -> bool:
        """Check if evidence is already in context."""
        return any(e.evidence_id == evidence_id for e in self.evidence_list)

    def get_evidence_ids(self) -> list[UUID]:
        """Get all evidence IDs in chronological order."""
        return [e.evidence_id for e in self.evidence_list]

    def get_summary(self) -> dict[str, Any]:
        """Get context window summary for logging."""
        return {
            "trigger_evidence_id": str(self.trigger_evidence_id),
            "evidence_count": len(self.evidence_list),
            "token_count": self.token_count,
            "boundary": self.boundary.value if self.boundary else None,
            "short_expansion_applied": self.short_expansion_applied,
            "reconstruction_recall_count": self.reconstruction_recall_count,
        }

    def to_interpretation_context(self) -> "InterpretationContext":
        """Convert ContextWindow to InterpretationContext.

        Returns:
            InterpretationContext ready for semantic interpretation.
        """
        from datetime import datetime
        from backend.context.interpretation_result import InterpretationContext

        return InterpretationContext(
            trigger_evidence_id=self.trigger_evidence_id,
            workspace_id=self.workspace_id,
            evidence_list=self.evidence_list,
            token_count=self.token_count,
            current_time=datetime.now(),
        )


# Budget constants
BUDGET_DEFAULT = 4000
BUDGET_HARD_LIMIT = 8000

# Short confirmation threshold (characters)
SHORT_CONFIRMATION_MAX_CHARS = 50

# Time windows for temporal adjacency (seconds)
TEMPORAL_WINDOW_SHORT = 300  # 5 minutes
TEMPORAL_WINDOW_MEDIUM = 1800  # 30 minutes
TEMPORAL_WINDOW_LONG = 86400  # 24 hours


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses a simple heuristic: ~4 characters per token for mixed CJK/ASCII.
    This is a deterministic approximation, not a full tokenizer.

    Args:
        text: The text to estimate.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    # Simple heuristic:
    # - CJK characters count as 1 token each
    # - ASCII words count as ~4 chars per token
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f' or '\uff00' <= c <= '\uffef')
    ascii_text = ''.join(c for c in text if not ('\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f' or '\uff00' <= c <= '\uffef'))

    # CJK: 1 char = 1 token
    # ASCII: ~4 chars = 1 token
    token_count = cjk_count + max(1, len(ascii_text) // 4)

    return token_count


def classify_role(meta: dict[str, Any]) -> EvidenceRole:
    """Classify evidence role from metadata.

    Args:
        meta: Evidence metadata dict.

    Returns:
        Classified EvidenceRole.
    """
    role = meta.get("role", "unknown").lower()

    role_map = {
        "user": EvidenceRole.USER,
        "assistant": EvidenceRole.ASSISTANT,
        "system": EvidenceRole.SYSTEM,
    }

    return role_map.get(role, EvidenceRole.UNKNOWN)


def classify_role_from_evidence_type(evidence_type: str) -> EvidenceRole:
    """Classify evidence role from evidence_type field (source of truth).

    This is the preferred method as evidence_type is the authoritative
    field for user/assistant classification.

    Args:
        evidence_type: The evidence_type value from Evidence model.

    Returns:
        Classified EvidenceRole.
    """
    role_map = {
        "user": EvidenceRole.USER,
        "assistant": EvidenceRole.ASSISTANT,
        "system": EvidenceRole.SYSTEM,
    }

    return role_map.get(evidence_type, EvidenceRole.UNKNOWN)
