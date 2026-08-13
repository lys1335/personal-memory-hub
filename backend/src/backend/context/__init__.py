"""Context Window package — Phase 21.3 & 21.4."""

from backend.context.context_window import (
    ContextWindow,
    EvidenceContext,
    EvidenceRole,
    ContextBoundary,
    estimate_tokens,
    classify_role,
    BUDGET_DEFAULT,
    BUDGET_HARD_LIMIT,
)
from backend.context.formulator import ContextWindowFormulator
from backend.context.interpretation_result import (
    InterpretationResult,
    InterpretationContext,
    InterpretationType,
    SemanticUnit,
    SourceType,
)
from backend.context.semantic_interpreter import UserSemanticInterpreter

__all__ = [
    # Phase 21.3
    "ContextWindow",
    "EvidenceContext",
    "EvidenceRole",
    "ContextBoundary",
    "ContextWindowFormulator",
    "estimate_tokens",
    "classify_role",
    "BUDGET_DEFAULT",
    "BUDGET_HARD_LIMIT",
    # Phase 21.4
    "InterpretationResult",
    "InterpretationContext",
    "InterpretationType",
    "SemanticUnit",
    "SourceType",
    "UserSemanticInterpreter",
]
