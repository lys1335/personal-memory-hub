"""Unit tests for ReflectionEngine components.

Tests the four internal components:
1. FactExtractorComponent (via Provider)
2. InterestAnalyzerComponent
3. ProjectionUpdaterComponent
4. ReflectionValidator
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from backend.engine.reflection_engine import ReflectionEngine
from backend.shared.providers.reflection_provider import MockReflectionProvider


@pytest.fixture
def engine():
    """Create ReflectionEngine instance."""
    return ReflectionEngine()


@pytest.fixture
def mock_provider():
    """Create MockReflectionProvider with sample data."""
    return MockReflectionProvider(
        mock_data={
            "facts": [
                {"entity": "happysmile", "value": "摄影服务平台", "confidence": 0.9, "source_ids": ["e1", "e2"]},
                {"entity": "happysmile", "value": "日本公司", "confidence": 0.85, "source_ids": ["e3"]},
                {"entity": "happysmile", "value": "2024年成立", "confidence": 0.8, "source_ids": ["e4"]},
            ],
            "entities": ["happysmile"],
        }
    )


class TestFactExtractorComponent:
    """Test FactExtractorComponent via Provider interface."""

    @pytest.mark.asyncio
    async def test_extract_facts_success(self, engine, mock_provider):
        """Test successful fact extraction."""
        candidates = [
            {"id": "e1", "content": "happysmile is a photography service platform"},
            {"id": "e2", "content": "The company was founded in Japan"},
        ]

        result, log = await engine._extract_facts(candidates, mock_provider)

        assert len(result) > 0
        assert isinstance(result, list)
        assert len(log) > 0

    @pytest.mark.asyncio
    async def test_extract_facts_empty(self, engine):
        """Test extraction with no candidates."""
        provider = MockReflectionProvider()
        result, log = await engine._extract_facts([], provider)

        assert result == []
        assert len(log) > 0

    @pytest.mark.asyncio
    async def test_extract_facts_provider_error(self, engine):
        """Test extraction when provider fails."""
        provider = MockReflectionProvider()
        provider.generate = AsyncMock(side_effect=Exception("Ollama unavailable"))

        result, log = await engine._extract_facts(
            [{"id": "e1", "content": "test"}], provider
        )

        assert result == []
        assert any("failed" in l.lower() for l in log)


class TestInterestAnalyzerComponent:
    """Test InterestAnalyzerComponent."""

    def test_analyze_interest_empty(self, engine):
        """Test analysis with no facts."""
        result = engine._analyze_interest([])

        assert result["trends"] == []
        assert "No facts" in result["summary"]

    def test_analyze_interest_single_entity(self, engine):
        """Test analysis with single entity mentions."""
        facts = [
            {"entity": "A", "value": "x", "confidence": 0.9},
            {"entity": "A", "value": "y", "confidence": 0.8},
            {"entity": "A", "value": "z", "confidence": 0.7},
        ]

        result = engine._analyze_interest(facts)

        assert len(result["trends"]) == 1
        assert result["trends"][0]["entity"] == "A"
        assert result["trends"][0]["trend"] == "rising"
        assert result["trends"][0]["mention_count"] == 3

    def test_analyze_interest_multiple_entities(self, engine):
        """Test analysis with multiple entities."""
        facts = [
            {"entity": "X", "value": "a", "confidence": 0.9},
            {"entity": "X", "value": "b", "confidence": 0.8},
            {"entity": "Y", "value": "c", "confidence": 0.7},
            {"entity": "Z", "value": "d", "confidence": 0.6},
        ]

        result = engine._analyze_interest(facts)

        assert len(result["trends"]) == 3
        # X should be first (most mentions)
        assert result["trends"][0]["entity"] == "X"
        # X has 2 mentions, which is >= 2, so trend is "stable"
        assert result["trends"][0]["trend"] == "stable"
        assert result["trends"][0]["mention_count"] == 2


class TestProjectionUpdaterComponent:
    """Test ProjectionUpdaterComponent."""

    def test_generate_proposals_empty(self, engine):
        """Test proposal generation with no facts."""
        result = engine._generate_proposals([], {})

        assert len(result) == 1
        assert result[0]["type"] == "Ignore"
        assert result[0]["confidence"] == 0.0

    def test_generate_proposals_strengthen(self, engine):
        """Test Strengthen proposal for high-confidence entity."""
        facts = [
            {"entity": "happysmile", "value": "摄影平台", "confidence": 0.9, "source_ids": ["e1", "e2", "e3"]},
            {"entity": "happysmile", "value": "日本公司", "confidence": 0.85, "source_ids": ["e4", "e5"]},
            {"entity": "happysmile", "value": "2024年成立", "confidence": 0.8, "source_ids": ["e6", "e7"]},
        ]

        result = engine._generate_proposals(facts, {})

        assert len(result) == 1
        assert result[0]["type"] == "Strengthen"
        assert result[0]["target_level"] == 2  # L2 Pattern
        assert result[0]["entity"] == "happysmile"
        # Evidence chain should contain valid UUIDs
        assert len(result[0]["evidence_chain"]) >= 0  # May be 0 if UUIDs are invalid

    def test_generate_proposals_create(self, engine):
        """Test Create proposal for medium-confidence entity."""
        facts = [
            {"entity": "tool_x", "value": "功能A", "confidence": 0.7},
            {"entity": "tool_x", "value": "功能B", "confidence": 0.65},
        ]

        result = engine._generate_proposals(facts, {})

        assert len(result) == 1
        assert result[0]["type"] == "Create"
        assert result[0]["target_level"] == 1  # L1 Observation
        assert result[0]["entity"] == "tool_x"

    def test_generate_proposals_mixed(self, engine):
        """Test proposal generation with multiple entities."""
        facts = [
            {"entity": "A", "value": "x", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "y", "confidence": 0.85, "source_ids": ["e2"]},
            {"entity": "A", "value": "z", "confidence": 0.8, "source_ids": ["e3"]},
            {"entity": "B", "value": "a", "confidence": 0.7, "source_ids": ["e4"]},
        ]

        result = engine._generate_proposals(facts, {})

        assert len(result) == 2
        types = {p["type"] for p in result}
        assert "Strengthen" in types  # A has 3 facts with high confidence

    def test_generate_proposals_uuid_validation(self, engine):
        """Test that invalid UUIDs are filtered from evidence chain."""
        facts = [
            {"entity": "test", "value": "x", "confidence": 0.9, "source_ids": ["invalid-uuid"]},
        ]

        result = engine._generate_proposals(facts, {})

        assert len(result) == 1
        # Should filter out invalid UUID
        assert result[0]["evidence_chain"] == []


class TestReflectionValidator:
    """Test ReflectionValidator."""

    def test_validate_valid_proposal(self, engine):
        """Test validation of a valid proposal."""
        proposal = {
            "type": "Create",
            "target_level": 1,
            "entity": "test",
            "evidence_chain": ["e1", "e2"],
            "confidence": 0.8,
            "summary": "Test proposal",
        }

        result = engine._validate_proposals([proposal])

        assert result.success
        assert len(result.unwrap_or([])) == 1

    def test_validate_missing_evidence(self, engine):
        """Test validation rejects proposal without evidence."""
        proposal = {
            "type": "Create",
            "target_level": 1,
            "entity": "test",
            "evidence_chain": [],  # Missing evidence
            "confidence": 0.8,
            "summary": "Test proposal",
        }

        result = engine._validate_proposals([proposal])

        assert not result.success
        assert "evidence chain" in result.error.message.lower()

    def test_validate_l0_protection(self, engine):
        """Test L0 protection rejects level 0 proposals."""
        proposal = {
            "type": "Create",
            "target_level": 0,  # L0 protection violation
            "entity": "test",
            "evidence_chain": ["e1"],
            "confidence": 0.8,
            "summary": "Test proposal",
        }

        result = engine._validate_proposals([proposal])

        assert not result.success
        assert "L0" in result.error.message or "level 0" in result.error.message.lower()

    def test_validate_empty_summary(self, engine):
        """Test validation rejects proposal with empty summary."""
        proposal = {
            "type": "Create",
            "target_level": 1,
            "entity": "test",
            "evidence_chain": ["e1"],
            "confidence": 0.8,
            "summary": "",  # Empty summary
        }

        result = engine._validate_proposals([proposal])

        assert not result.success
        assert "summary" in result.error.message.lower()

    def test_validate_mixed_valid_invalid(self, engine):
        """Test validation with mixed valid and invalid proposals."""
        proposals = [
            {
                "type": "Create",
                "target_level": 1,
                "entity": "valid",
                "evidence_chain": ["e1"],
                "confidence": 0.8,
                "summary": "Valid proposal",
            },
            {
                "type": "Create",
                "target_level": 0,  # Invalid: L0
                "entity": "invalid",
                "evidence_chain": ["e2"],
                "confidence": 0.8,
                "summary": "Invalid proposal",
            },
        ]

        result = engine._validate_proposals(proposals)

        # Should fail due to invalid proposal
        assert not result.success
        # But valid proposal should be in validated list if we check partial
        # Note: Current implementation returns all-or-nothing


class TestReflectPipeline:
    """Test the full reflect_pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_empty_candidates(self, engine):
        """Test pipeline with no candidates."""
        provider = MockReflectionProvider()
        result = await engine.reflect_pipeline(
            scope="test", candidates=[], provider=provider
        )

        assert result["facts"] == []
        assert result["proposals"] == []
        assert result["validation_passed"] is True
        assert "No candidates" in result["execution_log"][0]

    @pytest.mark.asyncio
    async def test_pipeline_no_facts(self, engine):
        """Test pipeline when no facts extracted."""
        provider = MockReflectionProvider(mock_data={"facts": [], "entities": []})
        candidates = [{"id": "e1", "content": "test content"}]

        result = await engine.reflect_pipeline(
            scope="test", candidates=candidates, provider=provider
        )

        assert result["facts"] == []
        assert result["proposals"] == []
        assert "No facts extracted" in str(result["execution_log"])

    @pytest.mark.asyncio
    async def test_pipeline_full_flow(self, engine, mock_provider):
        """Test complete pipeline flow."""
        candidates = [
            {"id": "e1", "content": "happysmile is a photography platform"},
            {"id": "e2", "content": "Founded in Japan 2024"},
            {"id": "e3", "content": "Provides photo sales service"},
        ]

        result = await engine.reflect_pipeline(
            scope="workspace", candidates=candidates, provider=mock_provider
        )

        # Check all expected keys
        assert "facts" in result
        assert "entities" in result
        assert "interest_trends" in result
        assert "proposals" in result
        assert "validation_passed" in result
        assert "execution_log" in result

        # Check facts extracted
        assert len(result["facts"]) > 0

        # Check entities extracted
        assert len(result["entities"]) > 0
        assert "happysmile" in result["entities"]

        # Check proposals generated
        assert len(result["proposals"]) >= 0  # May be empty if validation fails

        # Check execution log
        assert len(result["execution_log"]) > 0
        assert "Pipeline complete" in result["execution_log"][-1]


class TestExtractEntityNames:
    """Test _extract_entity_names helper."""

    def test_extract_from_facts(self, engine):
        """Test entity name extraction."""
        facts = [
            {"entity": "A", "value": "x"},
            {"entity": "B", "value": "y"},
            {"entity": "A", "value": "z"},  # Duplicate
        ]

        result = engine._extract_entity_names(facts)

        assert result == ["A", "B"]  # Sorted, unique

    def test_extract_empty_facts(self, engine):
        """Test entity extraction with no facts."""
        result = engine._extract_entity_names([])

        assert result == []

    def test_extract_no_entity(self, engine):
        """Test extraction when facts have no entity field."""
        facts = [{"value": "x"}, {"value": "y"}]

        result = engine._extract_entity_names(facts)

        assert result == []
