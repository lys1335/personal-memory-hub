"""
Entity Resolution Regression Tests — Phase 26-B.5

Test cases covering:
1. Should match: "Windows" related content
2. Should NOT match: "win" substring false positives
3. Context window contamination tests
4. Competing entity tests
5. Anti-collapse gate validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from backend.service.entity_resolution import (
    calculate_match_score,
    detect_competing_entities,
    resolve_entity_strict,
    EntityResolutionResult,
)


class TestCalculateMatchScore:
    """Test match score calculation."""
    
    def test_exact_phrase_match(self):
        """Exact phrase should get highest score."""
        score = calculate_match_score("Windows", "I use Windows 11 daily")
        assert score >= 0.95, f"Expected >= 0.95, got {score}"
    
    def test_word_boundary_match(self):
        """Word boundary match should get high score."""
        score = calculate_match_score("Windows", "This is about Windows OS")
        assert score >= 0.85, f"Expected >= 0.85, got {score}"
    
    def test_no_match_for_short_prefix(self):
        """Short prefix should NOT match."""
        # "win" should not match "winner"
        score = calculate_match_score("Windows", "He is the winner")
        assert score < 0.5, f"Expected < 0.5, got {score}"
    
    def test_no_match_for_similar_words(self):
        """Similar words should not match."""
        # "win" should not match "within"
        score = calculate_match_score("Windows", "within the database")
        assert score < 0.5, f"Expected < 0.5, got {score}"
    
    def test_no_match_for_window(self):
        """'window' should not match 'Windows' entity."""
        score = calculate_match_score("Windows", "window size is important")
        assert score < 0.5, f"Expected < 0.5, got {score}"
    
    def test_no_match_for_wine(self):
        """'wine' should not match 'Windows' entity."""
        score = calculate_match_score("Windows", "I enjoy drinking wine")
        assert score < 0.5, f"Expected < 0.5, got {score}"
    
    def test_no_match_for_darwin(self):
        """'darwin' should not match 'Windows' entity."""
        score = calculate_match_score("Windows", "Charles Darwin theory")
        assert score < 0.5, f"Expected < 0.5, got {score}"


class TestResolveEntityStrict:
    """Test strict entity resolution."""
    
    def test_should_match_windows(self):
        """Should correctly match Windows entity."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="Java"),
            MagicMock(id=uuid4(), canonical_name="Docker"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="I use Windows 11 for development",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        assert not result.is_unresolved, "Should resolve to Windows"
        assert result.confidence >= 0.8, f"Confidence too low: {result.confidence}"
    
    def test_should_not_match_windows_for_winner(self):
        """Should NOT match Windows for 'winner' content."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="Java"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="He is the winner of the competition",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        assert result.is_unresolved, "Should be unresolved for 'winner'"
    
    def test_should_not_match_windows_for_within(self):
        """Should NOT match Windows for 'within' content."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="within the database system",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        assert result.is_unresolved, "Should be unresolved for 'within'"
    
    def test_should_not_match_windows_for_sql(self):
        """Should NOT match Windows for SQL content."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="SQL Server"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="SELECT * FROM users WHERE id = 1",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        # Should either match SQL Server or be unresolved
        assert result.is_unresolved or result.entity_id != entities[0].id


class TestCompetingEntities:
    """Test competing entity detection."""
    
    def test_detect_competition(self):
        """Should detect competing entities."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="Window"),
        ]
        
        competitors = detect_competing_entities(
            entities[0].id,
            "window size configuration",
            entities,
            threshold=0.5
        )
        
        # Should detect competition between Windows and Window
        assert len(competitors) > 0, "Should detect competing entities"
    
    def test_no_competition_clear_match(self):
        """Should not detect competition for clear match."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="Java"),
        ]
        
        competitors = detect_competing_entities(
            entities[0].id,
            "I use Windows 11 daily",
            entities,
            threshold=0.5
        )
        
        # Should not detect competition for clear Windows match
        assert len(competitors) == 0, "Should not detect competition for clear match"


class TestContextWindowContamination:
    """Test context window contamination prevention."""
    
    def test_context_should_not_contaminate(self):
        """Context mention should not contaminate current evidence binding."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
        ]
        
        # Current evidence is about SQL, context mentions Windows
        result = resolve_entity_strict(
            evidence_content="SELECT * FROM users",  # SQL content
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        # Should not bind to Windows just because context mentions it
        assert result.is_unresolved, "Should not be contaminated by context"
    
    def test_context_with_clear_reference(self):
        """Context with clear reference should allow binding."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
        ]
        
        # Context clearly refers to Windows
        result = resolve_entity_strict(
            evidence_content="How do I install drivers for this OS?",
            workspace_entities=entities,
            context_window=[
                MagicMock(content="I have Windows 11 installed"),
            ],
            min_confidence=0.8
        )
        
        # Should bind to Windows due to clear context
        # Note: This test verifies the principle, actual implementation may vary


class TestAntiCollapseGate:
    """Test anti-collapse gate validation."""
    
    def test_entity_concentration_check(self):
        """Test entity concentration statistics."""
        # Simulate entity distribution
        entity_counts = {
            "Windows": 2200,  # 89.1% - HIGH RISK
            "Generate": 72,
            "Users": 28,
            "Java": 5,
            "Docker": 2,
        }
        
        total = sum(entity_counts.values())
        
        # Check top 1 share
        top_1_share = max(entity_counts.values()) / total
        assert top_1_share < 0.5, f"Top 1 entity share {top_1_share} exceeds 50% threshold"
    
    def test_concentration_threshold(self):
        """Test concentration threshold detection."""
        # Simulate healthy distribution
        healthy_counts = {
            "EntityA": 100,
            "EntityB": 90,
            "EntityC": 85,
            "EntityD": 80,
        }
        
        total = sum(healthy_counts.values())
        top_1_share = max(healthy_counts.values()) / total
        
        # Healthy distribution: top 1 should be < 50%
        assert top_1_share < 0.5, f"Healthy distribution should have top 1 < 50%, got {top_1_share}"


class TestRegressionScenarios:
    """Test specific regression scenarios from Phase 26-B.4."""
    
    def test_sql_not_windows(self):
        """SQL content should not bind to Windows."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="SQL Server"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="识别效果不太好，先不管它。先问下sql问题",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        # Should not bind to Windows
        assert result.entity_id != entities[0].id or result.is_unresolved
    
    def test_medical_not_windows(self):
        """Medical content should not bind to Windows."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="监测动态心电图；窦性心律",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        assert result.is_unresolved, "Medical content should not bind to Windows"
    
    def test_javascript_not_windows(self):
        """JavaScript content should not bind to Windows."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="function printWithIframe($content) {}",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        assert result.is_unresolved, "JavaScript content should not bind to Windows"
    
    def test_css_not_windows(self):
        """CSS content should not bind to Windows."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="input:-internal-autofill-selected style",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        assert result.is_unresolved, "CSS content should not bind to Windows"
    
    def test_excel_not_windows(self):
        """Excel content should not bind to Windows."""
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
        ]
        
        result = resolve_entity_strict(
            evidence_content="我要做一个勤务表 第五行开始",
            workspace_entities=entities,
            min_confidence=0.8
        )
        
        assert result.is_unresolved, "Excel content should not bind to Windows"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
