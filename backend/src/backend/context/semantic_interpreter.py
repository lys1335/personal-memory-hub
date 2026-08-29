"""User-centric Semantic Interpreter — Phase 21.4.

This module implements User-centric Semantic Interpretation.
It takes a ContextWindow from Phase 21.3 and determines:
1. Whether user has expressed user-owned semantic
2. What type of semantic (confirm, reject, decide, etc.)
3. The user-owned content summary

Design:
- Deterministic rules first, LLM fallback for complex cases
- Strict boundary: does NOT create Candidate/Reconstruction/Topic
- Outputs InterpretationResult for Phase 21.5 consumption
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from backend.context.context_window import (
    ContextWindow,
    EvidenceContext,
    EvidenceRole,
)
from backend.context.interpretation_result import (
    InterpretationContext,
    InterpretationResult,
    InterpretationType,
    SemanticUnit,
)

logger = logging.getLogger(__name__)


class UserSemanticInterpreter:
    """Interprets user semantic intent from ContextWindow.
    
    This is Phase 21.4's core component.
    It determines whether user has expressed user-owned semantic
    and classifies the interpretation type.
    
    Rules:
    1. role=user is required for user_owned=True
    2. Short confirmations need preceding context
    3. AI statements alone cannot become User Fact
    4. Partial confirmations are decomposed into SemanticUnits
    """
    
    # Confirmation patterns (deterministic)
    CONFIRM_PATTERNS = [
        "对", "是的", "好的", "没错", "就这样", "就这",
        "同意", "认可", "接受", "采纳", "采用",
        "ok", "okay", "yes", "yeah", "yep",
    ]
    
    # Rejection patterns
    REJECT_PATTERNS = [
        "不", "不对", "不是", "错", "否定", "拒绝",
        "不要", "不需要", "不行", "不好",
        "no", "nope", "never",
    ]
    
    # Correction patterns
    CORRECT_PATTERNS = [
        "不对", "错了", "不是", "修正", "纠正",
        "应该是", "其实是", "实际上是",
    ]
    
    # Uncertain patterns
    UNCERTAIN_PATTERNS = [
        "考虑", "想想", "待定", "犹豫", "也许", "可能",
        "暂时", "目前", "现在", "以后",
        "maybe", "perhaps", "consider",
    ]
    
    # Hypothetical patterns
    HYPOTHETICAL_PATTERNS = [
        "如果", "假如", "假设", "万一",
        "要是", "假使", "倘若",
        "if", "suppose", "assuming",
    ]
    
    # Third-party patterns
    THIRD_PARTY_PATTERNS = [
        "朋友", "同事", "他们说", "别人",
        "有人", "据说", "听说",
    ]
    
    def __init__(
        self,
        use_llm: bool = False,
        llm_provider: Any = None,
    ) -> None:
        """Initialize the interpreter.
        
        Args:
            use_llm: Whether to use LLM for complex cases.
            llm_provider: LLM provider instance (if use_llm=True).
        """
        self._use_llm = use_llm
        self._llm_provider = llm_provider
    
    async def interpret(
        self,
        context: InterpretationContext,
        workspace_id: UUID | None = None,
    ) -> InterpretationResult:
        """Interpret user semantic from context.

        Args:
            context: InterpretationContext wrapping ContextWindow.
            workspace_id: Optional workspace id to attach to the result.

        Returns:
            InterpretationResult with user-owned semantic classification.
        """
        trigger = context.trigger_evidence

        if trigger is None:
            result = self._create_no_user_fact(
                context, "Trigger evidence not found"
            )
        # Step 1: Role check - must be user
        elif trigger.role != EvidenceRole.USER:
            result = self._create_no_user_fact(
                context,
                f"Trigger is {trigger.role.value}, not user"
            )
        # Step 2: Check if short confirmation needing expansion
        elif trigger.is_short and trigger.is_user_confirmation:
            result = await self._interpret_short_confirmation(context, trigger)
        # Step 3: Direct interpretation of user message
        else:
            result = await self._interpret_direct(context, trigger)

        if workspace_id is not None:
            result.workspace_id = workspace_id

        return result
    
    async def _interpret_short_confirmation(
        self,
        context: InterpretationContext,
        trigger: EvidenceContext,
    ) -> InterpretationResult:
        """Interpret short confirmation like '对，就这样'."""
        # Find preceding assistant evidence
        assistant_evidences = [
            e for e in context.evidence_list
            if e.role == EvidenceRole.ASSISTANT
            and e.created_at < trigger.created_at
        ]
        
        if not assistant_evidences:
            # No context to confirm - ambiguous
            return self._create_ambiguous(
                context, "Short confirmation without preceding context"
            )
        
        # Get the most recent assistant evidence
        latest_assistant = max(assistant_evidences, key=lambda e: e.created_at)
        
        # Extract semantic content from assistant evidence
        assistant_content = latest_assistant.content
        
        # Determine interpretation type
        if trigger.is_user_confirmation:
            # User confirmed AI suggestion
            return InterpretationResult(
                trigger_evidence_id=context.trigger_evidence_id,
                workspace_id=context.workspace_id,
                interpretation_type=InterpretationType.CONFIRM,
                user_owned=True,
                semantic_content=f"用户确认采用: {assistant_content[:100]}",
                confidence=0.85,
                source_evidence_ids=[trigger.evidence_id, latest_assistant.evidence_id],
                referenced_assistant_evidence_ids=[latest_assistant.evidence_id],
                semantic_units=[
                    SemanticUnit(
                        subject=assistant_content[:50],
                        action=InterpretationType.CONFIRM,
                        content=f"用户确认: {assistant_content[:100]}",
                        confidence=0.85,
                        source_evidence_ids=[trigger.evidence_id, latest_assistant.evidence_id],
                    )
                ],
                rationale=f"Short confirmation '{trigger.content}' follows assistant suggestion",
            )
        
        return self._create_ambiguous(
            context,
            f"Short message '{trigger.content}' without clear confirmation pattern"
        )
    
    async def _interpret_direct(
        self,
        context: InterpretationContext,
        trigger: EvidenceContext,
    ) -> InterpretationResult:
        """Interpret direct user message."""
        content = trigger.content.strip()
        
        # Check for rejection
        if self._matches_pattern(content, self.REJECT_PATTERNS):
            return self._interpret_rejection(context, trigger, content)
        
        # Check for correction
        if self._matches_pattern(content, self.CORRECT_PATTERNS):
            return self._interpret_correction(context, trigger, content)
        
        # Check for uncertain
        if self._matches_pattern(content, self.UNCERTAIN_PATTERNS):
            return self._interpret_uncertain(context, trigger, content)
        
        # Check for hypothetical
        if self._matches_pattern(content, self.HYPOTHETICAL_PATTERNS):
            return self._create_no_user_fact(
                context, "Hypothetical statement, not user-owned fact"
            )
        
        # Check for third-party
        if self._matches_pattern(content, self.THIRD_PARTY_PATTERNS):
            return self._create_no_user_fact(
                context, "Third-party statement, not user-owned fact"
            )
        
        # Check for explicit decision/adopt
        if self._matches_pattern(content, ["决定", "采用", "选择", "使用", "安装", "配置"]):
            return self._interpret_decision(context, trigger, content)
        
        # For longer messages, try LLM if available
        if self._use_llm and self._llm_provider:
            return await self._interpret_with_llm(context, trigger)
        
        # Default: ambiguous for longer unconstrained messages
        return self._create_ambiguous(
            context,
            f"Long message without clear semantic marker: {content[:50]}"
        )
    
    def _interpret_rejection(
        self,
        context: InterpretationContext,
        trigger: EvidenceContext,
        content: str,
    ) -> InterpretationResult:
        """Interpret user rejection."""
        # Find what was rejected (previous assistant evidence)
        assistant_evidences = [
            e for e in context.evidence_list
            if e.role == EvidenceRole.ASSISTANT
            and e.created_at < trigger.created_at
        ]
        
        rejected_content = "未知建议"
        if assistant_evidences:
            latest = max(assistant_evidences, key=lambda e: e.created_at)
            rejected_content = latest.content[:100]
        
        return InterpretationResult(
            trigger_evidence_id=context.trigger_evidence_id,
            workspace_id=context.workspace_id,
            interpretation_type=InterpretationType.REJECT,
            user_owned=True,
            semantic_content=f"用户否定: {rejected_content}。用户说: {content[:100]}",
            confidence=0.9,
            source_evidence_ids=[trigger.evidence_id],
            semantic_units=[
                SemanticUnit(
                    subject=rejected_content[:50],
                    action=InterpretationType.REJECT,
                    content=f"用户否定: {rejected_content}",
                    confidence=0.9,
                    source_evidence_ids=[trigger.evidence_id],
                )
            ],
            rationale="User explicitly rejected using rejection patterns",
        )
    
    def _interpret_correction(
        self,
        context: InterpretationContext,
        trigger: EvidenceContext,
        content: str,
    ) -> InterpretationResult:
        """Interpret user correction."""
        return InterpretationResult(
            trigger_evidence_id=context.trigger_evidence_id,
            workspace_id=context.workspace_id,
            interpretation_type=InterpretationType.CORRECT,
            user_owned=True,
            semantic_content=f"用户纠正: {content[:100]}",
            confidence=0.95,
            source_evidence_ids=[trigger.evidence_id],
            semantic_units=[
                SemanticUnit(
                    subject="correction",
                    action=InterpretationType.CORRECT,
                    content=f"用户纠正: {content[:100]}",
                    confidence=0.95,
                    source_evidence_ids=[trigger.evidence_id],
                )
            ],
            rationale="User explicitly correcting with correction patterns",
        )
    
    def _interpret_uncertain(
        self,
        context: InterpretationContext,
        trigger: EvidenceContext,
        content: str,
    ) -> InterpretationResult:
        """Interpret uncertain user state."""
        return InterpretationResult(
            trigger_evidence_id=context.trigger_evidence_id,
            workspace_id=context.workspace_id,
            interpretation_type=InterpretationType.UNCERTAIN,
            user_owned=False,
            semantic_content=f"用户处于不确定状态: {content[:100]}",
            confidence=0.7,
            source_evidence_ids=[trigger.evidence_id],
            rationale="User expressed uncertainty",
        )
    
    def _interpret_decision(
        self,
        context: InterpretationContext,
        trigger: EvidenceContext,
        content: str,
    ) -> InterpretationResult:
        """Interpret user decision."""
        return InterpretationResult(
            trigger_evidence_id=context.trigger_evidence_id,
            workspace_id=context.workspace_id,
            interpretation_type=InterpretationType.DECISION,
            user_owned=True,
            semantic_content=f"用户决定: {content[:100]}",
            confidence=0.9,
            source_evidence_ids=[trigger.evidence_id],
            semantic_units=[
                SemanticUnit(
                    subject=content[:50],
                    action=InterpretationType.DECISION,
                    content=f"用户决定: {content[:100]}",
                    confidence=0.9,
                    source_evidence_ids=[trigger.evidence_id],
                )
            ],
            rationale="User expressed decision using decision patterns",
        )
    
    async def _interpret_with_llm(
        self,
        context: InterpretationContext,
        trigger: EvidenceContext,
    ) -> InterpretationResult:
        """Use LLM for complex semantic interpretation."""
        # Build prompt from context
        context_text = "\n".join([
            f"[{e.role.value}] {e.content}"
            for e in context.evidence_list
        ])
        
        prompt = f"""Analyze the following conversation and determine if the user has expressed a user-owned semantic fact.

Conversation:
{context_text}

User's latest message: {trigger.content}

Output JSON with:
- interpretation_type: confirm|adopt|reject|correct|preference|decision|intent|uncertain|ambiguous|no_user_fact
- user_owned: true|false
- semantic_content: summary of user-owned fact
- confidence: 0.0-1.0
- rationale: why this interpretation

Rules:
- Only user messages can become user-owned facts
- AI suggestions alone do not become user facts
- Short responses like "嗯" without context are ambiguous
- Hypothetical statements are not user facts
"""
        
        try:
            result = await self._llm_provider.generate(prompt)
            # Parse JSON result
            import json
            data = json.loads(result)
            
            return InterpretationResult(
                trigger_evidence_id=context.trigger_evidence_id,
                workspace_id=context.workspace_id,
                interpretation_type=InterpretationType(data.get("interpretation_type", "ambiguous")),
                user_owned=data.get("user_owned", False),
                semantic_content=data.get("semantic_content", ""),
                confidence=data.get("confidence", 0.5),
                source_evidence_ids=[trigger.evidence_id],
                rationale=data.get("rationale", ""),
            )
        except Exception as e:
            logger.error("LLM interpretation failed: %s", e)
            return self._create_ambiguous(context, f"LLM failed: {e}")
    
    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    
    def _matches_pattern(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any pattern."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in patterns)
    
    def _create_no_user_fact(
        self, context: InterpretationContext, reason: str
    ) -> InterpretationResult:
        """Create NO_USER_FACT result."""
        return InterpretationResult(
            trigger_evidence_id=context.trigger_evidence_id,
            workspace_id=context.workspace_id,
            interpretation_type=InterpretationType.NO_USER_FACT,
            user_owned=False,
            semantic_content="",
            confidence=1.0,
            source_evidence_ids=[],
            rationale=reason,
        )
    
    def _create_ambiguous(
        self, context: InterpretationContext, reason: str
    ) -> InterpretationResult:
        """Create AMBIGUOUS result."""
        return InterpretationResult(
            trigger_evidence_id=context.trigger_evidence_id,
            workspace_id=context.workspace_id,
            interpretation_type=InterpretationType.AMBIGUOUS,
            user_owned=False,
            semantic_content="",
            confidence=0.3,
            source_evidence_ids=[],
            rationale=reason,
        )
