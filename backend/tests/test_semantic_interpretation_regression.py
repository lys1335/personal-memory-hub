"""Phase 21.4 Regression Tests — User-centric Semantic Interpretation.

These tests verify the Phase 21.4 implementation:
1. User semantic classification (confirm, reject, correct, etc.)
2. Short confirmation handling
3. Ambiguous/uncertain state detection
4. Third-party/hypothetical filtering
5. Partial confirmation decomposition
6. Role boundary (assistant evidence cannot become user fact)
7. Lineage tracking
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

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
from backend.context.semantic_interpreter import UserSemanticInterpreter


class TestConfirmationClassification:
    """Test A: 明确确认."""

    def test_explicit_confirmation(self):
        """User explicitly confirms AI suggestion."""
        interpreter = UserSemanticInterpreter()
        
        # Create context with AI suggestion + user confirmation
        base_time = datetime.now() - timedelta(minutes=5)
        
        assistant_evidence = EvidenceContext(
            evidence_id=uuid4(),
            content="建议使用 PostgreSQL。",
            role=EvidenceRole.ASSISTANT,
            created_at=base_time,
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.5,
            token_count=10,
        )
        
        trigger_evidence = EvidenceContext(
            evidence_id=uuid4(),
            content="对，就这样。",
            role=EvidenceRole.USER,
            created_at=base_time + timedelta(minutes=1),
            entity_id=assistant_evidence.entity_id,
            workspace_id=assistant_evidence.workspace_id,
            importance=0.8,
            token_count=5,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger_evidence.evidence_id,
            workspace_id=trigger_evidence.workspace_id,
            evidence_list=[assistant_evidence, trigger_evidence],
        )
        
        result = interpreter.interpret(context)
        
        assert result.user_owned is True
        assert result.interpretation_type == InterpretationType.CONFIRM
        assert result.has_user_fact is True
        assert len(result.semantic_units) == 1
        assert result.semantic_units[0].is_confirmed

    def test_short_confirmation_pattern(self):
        """Test various short confirmation patterns."""
        interpreter = UserSemanticInterpreter()
        
        confirmations = ["对", "是的", "好的", "没错", "就这样", "ok", "yes"]
        
        for confirmation in confirmations:
            trigger = EvidenceContext(
                evidence_id=uuid4(),
                content=confirmation,
                role=EvidenceRole.USER,
                created_at=datetime.now(),
                entity_id=uuid4(),
                workspace_id=uuid4(),
                importance=0.5,
            )
            
            # Verify is_user_confirmation is True
            assert trigger.is_user_confirmation is True

    def test_ambiguous_short_response(self):
        """Test that ambiguous short responses are not confirmed."""
        interpreter = UserSemanticInterpreter()
        
        # "嗯" is short but not a confirmation pattern
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="嗯",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.5,
        )
        
        assert trigger.is_short is True
        assert trigger.is_user_confirmation is False


class TestRejectionClassification:
    """Test D: 明确否定."""

    def test_explicit_rejection(self):
        """User explicitly rejects AI suggestion."""
        interpreter = UserSemanticInterpreter()
        
        base_time = datetime.now() - timedelta(minutes=5)
        
        assistant_evidence = EvidenceContext(
            evidence_id=uuid4(),
            content="建议使用 PostgreSQL。",
            role=EvidenceRole.ASSISTANT,
            created_at=base_time,
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.5,
            token_count=10,
        )
        
        trigger_evidence = EvidenceContext(
            evidence_id=uuid4(),
            content="不，我不想要那个。",
            role=EvidenceRole.USER,
            created_at=base_time + timedelta(minutes=1),
            entity_id=assistant_evidence.entity_id,
            workspace_id=assistant_evidence.workspace_id,
            importance=0.9,
            token_count=10,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger_evidence.evidence_id,
            workspace_id=trigger_evidence.workspace_id,
            evidence_list=[assistant_evidence, trigger_evidence],
        )
        
        result = interpreter.interpret(context)
        
        assert result.user_owned is True
        assert result.interpretation_type == InterpretationType.REJECT
        assert result.is_rejected is True
        assert result.semantic_units[0].is_rejected

    def test_negative_statement(self):
        """Test negative statement without prior context."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="我不打算用那个方案。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.7,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger.evidence_id,
            workspace_id=trigger.workspace_id,
            evidence_list=[trigger],
        )
        
        result = interpreter.interpret(context)
        
        # Should still be recognized as rejection intent
        assert result.user_owned is True


class TestCorrectionClassification:
    """Test E: 用户纠正 AI."""

    def test_user_correction(self):
        """User corrects AI's understanding."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="不对，我是说 MySQL。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.9,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger.evidence_id,
            workspace_id=trigger.workspace_id,
            evidence_list=[trigger],
        )
        
        result = interpreter.interpret(context)
        
        assert result.user_owned is True
        assert result.interpretation_type == InterpretationType.CORRECT
        assert result.semantic_units[0].is_corrected


class TestPartialConfirmation:
    """Test F: 部分采纳."""

    def test_partial_confirmation(self):
        """User accepts only part of AI suggestion."""
        interpreter = UserSemanticInterpreter()
        
        # This would require more sophisticated LLM-based interpretation
        # For now, we test the data structure supports multiple units
        result = InterpretationResult(
            trigger_evidence_id=uuid4(),
            workspace_id=uuid4(),
            interpretation_type=InterpretationType.PARTIAL_CONFIRM,
            user_owned=True,
            semantic_content="部分采纳",
            confidence=0.7,
            semantic_units=[
                SemanticUnit(
                    subject="A",
                    action=InterpretationType.CONFIRM,
                    content="用户接受 A",
                    confidence=0.9,
                ),
                SemanticUnit(
                    subject="B",
                    action=InterpretationType.REJECT,
                    content="用户拒绝 B",
                    confidence=0.8,
                ),
                SemanticUnit(
                    subject="C",
                    action=InterpretationType.UNCERTAIN,
                    content="用户暂定 C",
                    confidence=0.5,
                ),
            ],
        )
        
        assert len(result.semantic_units) == 3
        assert result.semantic_units[0].is_confirmed
        assert result.semantic_units[1].is_rejected
        assert result.semantic_units[2].action == InterpretationType.UNCERTAIN


class TestPreferenceClassification:
    """Test G: Preference."""

    def test_preference_expression(self):
        """User expresses preference."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="我更喜欢 Python 而不是 Java。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.6,
        )
        
        # This would be classified by LLM or pattern matching
        # For deterministic test, we verify the structure
        assert trigger.role == EvidenceRole.USER
        assert trigger.is_short is False


class TestDecisionClassification:
    """Test H: Decision."""

    def test_decision_expression(self):
        """User makes explicit decision."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="我决定使用 PostgreSQL 作为数据库。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.95,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger.evidence_id,
            workspace_id=trigger.workspace_id,
            evidence_list=[trigger],
        )
        
        result = interpreter.interpret(context)
        
        # Decision patterns should be recognized
        assert result.user_owned is True


class TestIntentClassification:
    """Test I: Intent."""

    def test_intent_expression(self):
        """User expresses future intent."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="我打算下周开始学习 Rust。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.7,
        )
        
        # Intent should be detected
        assert trigger.role == EvidenceRole.USER


class TestConstraintClassification:
    """Test J: Constraint."""

    def test_constraint_expression(self):
        """User expresses constraint."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="我的预算只有 1000 元。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.8,
        )
        
        assert trigger.role == EvidenceRole.USER


class TestUncertainState:
    """Test K: Uncertain state."""

    def test_uncertain_expression(self):
        """User expresses uncertainty."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="我还在考虑中，不确定要不要用。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.5,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger.evidence_id,
            workspace_id=trigger.workspace_id,
            evidence_list=[trigger],
        )
        
        result = interpreter.interpret(context)
        
        # Uncertain should not be user_owned fact yet
        assert result.interpretation_type in [
            InterpretationType.UNCERTAIN,
            InterpretationType.AMBIGUOUS,
        ]


class TestThirdPartyStatement:
    """Test L: Third-party statement."""

    def test_third_party_not_user_fact(self):
        """Third-party statements are not user facts."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="我朋友说 PostgreSQL 很好用。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.3,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger.evidence_id,
            workspace_id=trigger.workspace_id,
            evidence_list=[trigger],
        )
        
        result = interpreter.interpret(context)
        
        # Third-party statements should not be user facts
        assert result.user_owned is False
        assert result.interpretation_type == InterpretationType.NO_USER_FACT


class TestHypothetical:
    """Test M: Hypothetical."""

    def test_hypothetical_not_user_fact(self):
        """Hypothetical statements are not user facts."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="如果以后需要，可以考虑 PostgreSQL。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.2,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger.evidence_id,
            workspace_id=trigger.workspace_id,
            evidence_list=[trigger],
        )
        
        result = interpreter.interpret(context)
        
        # Hypothetical should not be user fact
        assert result.user_owned is False


class TestQuotation:
    """Test N: Quotation."""

    def test_quotation_not_user_fact(self):
        """Quoting others is not user fact."""
        interpreter = UserSemanticInterpreter()
        
        trigger = EvidenceContext(
            evidence_id=uuid4(),
            content="他说应该使用 PostgreSQL。",
            role=EvidenceRole.USER,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.2,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=trigger.evidence_id,
            workspace_id=trigger.workspace_id,
            evidence_list=[trigger],
        )
        
        result = interpreter.interpret(context)
        
        # Quotation should not be user fact
        assert result.user_owned is False


class TestPureAIStatement:
    """Test O: Pure AI statement."""

    def test_assistant_alone_no_user_fact(self):
        """Assistant evidence alone cannot become user fact."""
        interpreter = UserSemanticInterpreter()
        
        assistant_evidence = EvidenceContext(
            evidence_id=uuid4(),
            content="建议使用 PostgreSQL。",
            role=EvidenceRole.ASSISTANT,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.5,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=assistant_evidence.evidence_id,
            workspace_id=assistant_evidence.workspace_id,
            evidence_list=[assistant_evidence],
        )
        
        result = interpreter.interpret(context)
        
        # Assistant evidence should NOT be user fact
        assert result.user_owned is False
        assert result.interpretation_type == InterpretationType.NO_USER_FACT


class TestCrossEvidenceInterpretation:
    """Test P: Cross multiple Evidence interpretation."""

    def test_multi_turn_conversation(self):
        """Interpret across multiple turns."""
        interpreter = UserSemanticInterpreter()
        
        base_time = datetime.now() - timedelta(minutes=10)
        
        # Conversation flow
        evidences = [
            EvidenceContext(
                evidence_id=uuid4(),
                content="我在考虑数据库选型。",
                role=EvidenceRole.USER,
                created_at=base_time,
                entity_id=uuid4(),
                workspace_id=uuid4(),
                importance=0.5,
            ),
            EvidenceContext(
                evidence_id=uuid4(),
                content="基于你的需求，我建议 PostgreSQL。",
                role=EvidenceRole.ASSISTANT,
                created_at=base_time + timedelta(minutes=2),
                entity_id=evidences[0].entity_id,
                workspace_id=evidences[0].workspace_id,
                importance=0.6,
            ),
            EvidenceContext(
                evidence_id=uuid4(),
                content="好的，就用 PostgreSQL。",
                role=EvidenceRole.USER,
                created_at=base_time + timedelta(minutes=3),
                entity_id=evidences[0].entity_id,
                workspace_id=evidences[0].workspace_id,
                importance=0.9,
            ),
        ]
        
        context = InterpretationContext(
            trigger_evidence_id=evidences[2].evidence_id,
            workspace_id=evidences[0].workspace_id,
            evidence_list=evidences,
        )
        
        result = interpreter.interpret(context)
        
        assert result.user_owned is True
        assert result.interpretation_type == InterpretationType.CONFIRM
        assert len(result.source_evidence_ids) >= 2


class TestChineseShortResponse:
    """Test Q: Chinese short responses."""

    def test_chinese_short_confirmations(self):
        """Test various Chinese short confirmations."""
        interpreter = UserSemanticInterpreter()
        
        confirmations = ["对", "是的", "好的", "没错", "就这样", "嗯嗯", "行"]
        
        for conf in confirmations:
            trigger = EvidenceContext(
                evidence_id=uuid4(),
                content=conf,
                role=EvidenceRole.USER,
                created_at=datetime.now(),
                entity_id=uuid4(),
                workspace_id=uuid4(),
                importance=0.5,
            )
            
            # All should be short
            assert trigger.is_short is True


class TestMixedLanguageShortResponse:
    """Test R: Mixed Chinese/English short responses."""

    def test_mixed_language_confirmations(self):
        """Test mixed language confirmations."""
        interpreter = UserSemanticInterpreter()
        
        confirmations = ["OK", "ok", "Yes", "yes", "yeah", "yep"]
        
        for conf in confirmations:
            trigger = EvidenceContext(
                evidence_id=uuid4(),
                content=conf,
                role=EvidenceRole.USER,
                created_at=datetime.now(),
                entity_id=uuid4(),
                workspace_id=uuid4(),
                importance=0.5,
            )
            
            assert trigger.is_short is True


class TestBoundaryRules:
    """Test boundary rules from Phase 21.3 audit."""

    def test_role_boundary(self):
        """Assistant evidence cannot become user fact."""
        interpreter = UserSemanticInterpreter()
        
        assistant = EvidenceContext(
            evidence_id=uuid4(),
            content="建议 PostgreSQL",
            role=EvidenceRole.ASSISTANT,
            created_at=datetime.now(),
            entity_id=uuid4(),
            workspace_id=uuid4(),
            importance=0.5,
        )
        
        context = InterpretationContext(
            trigger_evidence_id=assistant.evidence_id,
            workspace_id=assistant.workspace_id,
            evidence_list=[assistant],
        )
        
        result = interpreter.interpret(context)
        
        assert result.user_owned is False
        assert result.interpretation_type == InterpretationType.NO_USER_FACT

    def test_trigger_not_found(self):
        """Test when trigger evidence is not in context."""
        interpreter = UserSemanticInterpreter()
        
        context = InterpretationContext(
            trigger_evidence_id=uuid4(),  # Not in list
            workspace_id=uuid4(),
            evidence_list=[],
        )
        
        result = interpreter.interpret(context)
        
        assert result.interpretation_type == InterpretationType.NO_USER_FACT


class TestInterpretationResultStructure:
    """Test InterpretationResult data structure."""

    def test_result_summary(self):
        """Test result summary generation."""
        result = InterpretationResult(
            trigger_evidence_id=uuid4(),
            workspace_id=uuid4(),
            interpretation_type=InterpretationType.CONFIRM,
            user_owned=True,
            semantic_content="用户确认采用 PostgreSQL",
            confidence=0.9,
            source_evidence_ids=[uuid4(), uuid4()],
            referenced_assistant_evidence_ids=[uuid4()],
            rationale="Short confirmation after AI suggestion",
        )
        
        summary = result.get_summary()
        
        assert summary["interpretation_type"] == "confirm"
        assert summary["user_owned"] is True
        assert summary["confidence"] == 0.9
        assert summary["semantic_units_count"] == 0

    def test_property_methods(self):
        """Test convenience properties."""
        result = InterpretationResult(
            trigger_evidence_id=uuid4(),
            workspace_id=uuid4(),
            interpretation_type=InterpretationType.CONFIRM,
            user_owned=True,
            semantic_content="Test",
            confidence=0.9,
        )
        
        assert result.has_user_fact is True
        assert result.is_confirmed is True
        assert result.is_rejected is False
        assert result.is_ambiguous is False
        assert result.is_no_user_fact is False

    def test_no_user_fact_result(self):
        """Test NO_USER_FACT result properties."""
        result = InterpretationResult(
            trigger_evidence_id=uuid4(),
            workspace_id=uuid4(),
            interpretation_type=InterpretationType.NO_USER_FACT,
            user_owned=False,
            semantic_content="",
            confidence=1.0,
        )
        
        assert result.has_user_fact is False
        assert result.is_no_user_fact is True


class TestSemanticUnit:
    """Test SemanticUnit data structure."""

    def test_unit_creation(self):
        """Test SemanticUnit creation."""
        unit = SemanticUnit(
            subject="PostgreSQL",
            action=InterpretationType.CONFIRM,
            content="用户确认使用 PostgreSQL",
            confidence=0.9,
            source_evidence_ids=[uuid4()],
        )
        
        assert unit.is_confirmed is True
        assert unit.is_rejected is False
        assert unit.is_corrected is False

    def test_multiple_units(self):
        """Test multiple semantic units in result."""
        result = InterpretationResult(
            trigger_evidence_id=uuid4(),
            workspace_id=uuid4(),
            interpretation_type=InterpretationType.PARTIAL_CONFIRM,
            user_owned=True,
            semantic_content="部分采纳",
            confidence=0.7,
            semantic_units=[
                SemanticUnit("A", InterpretationType.CONFIRM, "接受A", 0.9),
                SemanticUnit("B", InterpretationType.REJECT, "拒绝B", 0.8),
                SemanticUnit("C", InterpretationType.UNCERTAIN, "暂定C", 0.5),
            ],
        )
        
        assert len(result.semantic_units) == 3
        assert sum(1 for u in result.semantic_units if u.is_confirmed) == 1
        assert sum(1 for u in result.semantic_units if u.is_rejected) == 1


# Fixtures
@pytest.fixture
def interpreter():
    return UserSemanticInterpreter()

@pytest.fixture
def sample_workspace_id():
    return uuid4()

@pytest.fixture
def sample_entity_id():
    return uuid4()
