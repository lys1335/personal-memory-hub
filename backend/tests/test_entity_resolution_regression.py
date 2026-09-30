"""
Entity Resolution Regression Tests — Phase 26-B.5
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from backend.service.entity_resolution import (
    calculate_match_score,
    detect_competing_entities,
    resolve_entity_strict,
)


class TestCalculateMatchScore:
    def test_exact_phrase_match(self):
        score = calculate_match_score("Windows", "I use Windows 11 daily")
        assert score >= 0.95
    
    def test_no_match_for_winner(self):
        score = calculate_match_score("Windows", "He is the winner")
        assert score < 0.5
    
    def test_no_match_for_within(self):
        score = calculate_match_score("Windows", "within the database")
        assert score < 0.5
    
    def test_no_match_for_window(self):
        score = calculate_match_score("Windows", "window size is important")
        assert score < 0.5


class TestResolveEntityStrict:
    def test_should_match_windows(self):
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="Java"),
        ]
        result = resolve_entity_strict(
            evidence_content="I use Windows 11 for development",
            workspace_entities=entities,
            min_confidence=0.8
        )
        assert not result.is_unresolved
    
    def test_should_not_match_windows_for_winner(self):
        entities = [MagicMock(id=uuid4(), canonical_name="Windows")]
        result = resolve_entity_strict(
            evidence_content="He is the winner of the competition",
            workspace_entities=entities,
            min_confidence=0.8
        )
        assert result.is_unresolved
    
    def test_sql_not_windows(self):
        entities = [
            MagicMock(id=uuid4(), canonical_name="Windows"),
            MagicMock(id=uuid4(), canonical_name="SQL Server"),
        ]
        result = resolve_entity_strict(
            evidence_content="SELECT * FROM users WHERE id = 1",
            workspace_entities=entities,
            min_confidence=0.8
        )
        assert result.entity_id != entities[0].id or result.is_unresolved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
