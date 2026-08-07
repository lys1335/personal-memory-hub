"""Unit tests for EvidenceEvolutionEngine.

Per D4.2g and ADR-EvidenceEvolution-Split:
- Tests Information Extraction logic
- Tests rule-based pattern discovery
- Tests candidate building
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from backend.engine.evidence_evolution_engine import EvidenceEvolutionEngine, EvolutionResult
from backend.shared.providers.reflection_provider import MockReflectionProvider


@pytest.fixture
def engine():
    """Create EvidenceEvolutionEngine instance."""
    return EvidenceEvolutionEngine()


@pytest.fixture
def mock_evidence():
    """Create sample evidence list."""
    return [
        {"id": "e1", "content": "HappySmile is a photography platform", "source": "chat", "metadata": {}},
        {"id": "e2", "content": "HappySmile was founded in 2024", "source": "chat", "metadata": {}},
        {"id": "e3", "content": "HappySmile is a Japanese company", "source": "chat", "metadata": {}},
        {"id": "e4", "content": "Apple Pay supports contactless payment", "source": "chat", "metadata": {}},
        {"id": "e5", "content": "Apple Pay works on iPhone", "source": "chat", "metadata": {}},
    ]


@pytest.fixture
def mock_provider():
    """Create MockReflectionProvider with sample facts."""
    return MockReflectionProvider(
        mock_data={
            "facts": [
                {
                    "entity": "HappySmile",
                    "value": "photography platform",
                    "source_ids": ["e1", "e2", "e3"],
                    "confidence": 0.9,
                },
                {
                    "entity": "Apple Pay",
                    "value": "contactless payment",
                    "source_ids": ["e4", "e5"],
                    "confidence": 0.85,
                },
            ],
            "entities": ["HappySmile", "Apple Pay"],
        }
    )


class TestEvidenceEvolutionEngineInit:
    """Test EvidenceEvolutionEngine initialization."""

    def test_init(self, engine):
        """Test engine initialization."""
        assert engine.name == "EvidenceEvolutionEngine"


class TestEvolveMethod:
    """Test EvidenceEvolutionEngine.evolve() method."""

    @pytest.mark.asyncio
    async def test_evolve_empty_evidence(self, engine):
        """Test evolve with empty evidence list."""
        result = await engine.evolve(evidence=[], provider=None)

        assert isinstance(result, EvolutionResult)
        assert result.candidates == []
        assert result.entities == []
        assert len(result.execution_log) > 0
        assert result.statistics["count"] == 0

    @pytest.mark.asyncio
    async def test_evolve_with_mock_data(self, engine, mock_evidence, mock_provider):
        """Test evolve with sample evidence and mock provider."""
        result = await engine.evolve(evidence=mock_evidence, provider=mock_provider)

        assert isinstance(result, EvolutionResult)
        assert len(result.candidates) > 0
        assert len(result.entities) > 0
        assert len(result.execution_log) > 0
        assert result.statistics["count"] == len(mock_evidence)

        # Verify candidate structure
        candidate = result.candidates[0]
        assert "entity" in candidate
        assert "content" in candidate
        assert "evidence_chain" in candidate
        assert "source_level" in candidate

    @pytest.mark.asyncio
    async def test_evolve_provider_error(self, engine, mock_evidence):
        """Test evolve when provider raises an exception."""
        async def failing_generate(*args, **kwargs):
            raise RuntimeError("Provider error")

        class FailingProvider:
            generate = failing_generate

        result = await engine.evolve(evidence=mock_evidence, provider=FailingProvider())

        assert isinstance(result, EvolutionResult)
        assert result.candidates == []
        # Error message should be in execution_log
        assert any("failed" in entry.lower() or "error" in entry.lower() for entry in result.execution_log)


class TestExtractFacts:
    """Test _extract_facts() method."""

    @pytest.mark.asyncio
    async def test_extract_facts_success(self, engine, mock_provider):
        """Test successful fact extraction."""
        evidence = [{"id": "e1", "content": "Test content", "source": "chat"}]
        facts, log = await engine._extract_facts(evidence, mock_provider)

        assert len(facts) == 2
        assert facts[0]["entity"] == "HappySmile"
        assert facts[0]["confidence"] == 0.9
        assert len(log) > 0

    @pytest.mark.asyncio
    async def test_extract_facts_empty(self, engine):
        """Test extraction with empty evidence."""
        # Use a provider that returns empty facts
        class EmptyProvider:
            async def generate(self, prompt, context):
                return {"facts": [], "entities": []}

        facts, log = await engine._extract_facts([], EmptyProvider())

        assert facts == []
        assert len(log) > 0


class TestDiscoverPatterns:
    """Test _discover_patterns() method."""

    def test_discover_patterns_recurring(self, engine):
        """Test pattern discovery for recurring entities."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
            {"entity": "B", "value": "v3", "confidence": 0.8, "source_ids": ["e3"]},
        ]

        patterns = engine._discover_patterns(facts)

        assert len(patterns) == 1
        assert patterns[0]["entity"] == "A"
        assert patterns[0]["pattern_type"] == "recurring"
        assert patterns[0]["mention_count"] == 2

    def test_discover_patterns_no_recurring(self, engine):
        """Test pattern discovery with no recurring entities."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "B", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
            {"entity": "C", "value": "v3", "confidence": 0.8, "source_ids": ["e3"]},
        ]

        patterns = engine._discover_patterns(facts)

        assert len(patterns) == 0


class TestAggregateEvidence:
    """Test _aggregate_evidence() method."""

    def test_aggregate_evidence_groups(self, engine):
        """Test evidence aggregation by entity."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
            {"entity": "B", "value": "v3", "confidence": 0.8, "source_ids": ["e3"]},
        ]

        aggregated = engine._aggregate_evidence(facts)

        assert "A" in aggregated
        assert "B" in aggregated
        assert aggregated["A"]["fact_count"] == 2
        assert aggregated["B"]["fact_count"] == 1
        assert len(aggregated["A"]["source_ids"]) == 2

    def test_aggregate_evidence_empty(self, engine):
        """Test aggregation with empty facts."""
        aggregated = engine._aggregate_evidence([])
        assert aggregated == {}


class TestEstimateConfidence:
    """Test _estimate_confidence() method."""

    def test_estimate_confidence_average(self, engine):
        """Test confidence estimation as average."""
        facts = [
            {"entity": "A", "confidence": 0.9},
            {"entity": "A", "confidence": 0.8},
            {"entity": "A", "confidence": 0.7},
        ]

        confidence = engine._estimate_confidence(facts)
        assert confidence == pytest.approx(0.8)

    def test_estimate_confidence_empty(self, engine):
        """Test confidence estimation with empty facts."""
        confidence = engine._estimate_confidence([])
        assert confidence == 0.0


class TestBuildCandidates:
    """Test _build_candidates() method."""

    def test_build_candidates_from_facts(self, engine):
        """Test candidate building from extracted facts."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1", "e2"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e3"]},
            {"entity": "B", "value": "v3", "confidence": 0.8, "source_ids": ["e4"]},
        ]
        evidence = [
            {"id": "e1", "content": "c1"},
            {"id": "e2", "content": "c2"},
            {"id": "e3", "content": "c3"},
            {"id": "e4", "content": "c4"},
        ]

        candidates = engine._build_candidates(facts, evidence)

        assert len(candidates) == 2
        assert candidates[0]["entity"] == "A"
        assert candidates[0]["source_level"] == 1
        assert candidates[0]["candidate_type"] == "pattern"
        assert candidates[0]["status"] == "candidate"
        assert len(candidates[0]["evidence_chain"]) == 3

    def test_build_candidates_empty(self, engine):
        """Test candidate building with empty facts."""
        candidates = engine._build_candidates([], [])
        assert candidates == []


class TestExtractEntityNames:
    """Test _extract_entity_names() method."""

    def test_extract_entities(self, engine):
        """Test entity name extraction."""
        facts = [
            {"entity": "B", "value": "v1", "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "source_ids": ["e2"]},
            {"entity": "C", "value": "v3", "source_ids": ["e3"]},
            {"entity": "A", "value": "v4", "source_ids": ["e4"]},
        ]

        entities = engine._extract_entity_names(facts)

        assert entities == ["A", "B", "C"]

    def test_extract_entities_empty(self, engine):
        """Test entity extraction with empty facts."""
        entities = engine._extract_entity_names([])
        assert entities == []


class TestEvolutionResult:
    """Test EvolutionResult dataclass."""

    def test_default_values(self):
        """Test default values for EvolutionResult."""
        result = EvolutionResult()

        assert result.candidates == []
        assert result.entities == []
        assert result.execution_log == []
        assert result.statistics == {}

    def test_custom_values(self):
        """Test custom values for EvolutionResult."""
        result = EvolutionResult(
            candidates=[{"entity": "test"}],
            entities=["test"],
            execution_log=["log"],
            statistics={"count": 1},
        )

        assert len(result.candidates) == 1
        assert result.entities == ["test"]
        assert result.execution_log == ["log"]
        assert result.statistics["count"] == 1
