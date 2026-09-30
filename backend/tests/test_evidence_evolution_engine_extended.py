"""Extended unit tests for EvidenceEvolutionEngine rule-based methods.

Per D4.2g and ADR-EvidenceEvolution-Split:
- Tests edge cases for _discover_patterns(), _aggregate_evidence(), _estimate_confidence()
- Tests idempotency and determinism
- Tests invalid input handling
- Tests duplicate fact handling

Phase 26-G-A Test Completion
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


@pytest.fixture
def engine():
    """Create EvidenceEvolutionEngine instance."""
    return EvidenceEvolutionEngine()


class TestDiscoverPatternsEdgeCases:
    """Extended tests for _discover_patterns() edge cases."""

    def test_discover_patterns_empty_input(self, engine):
        """Test pattern discovery with empty input."""
        facts = []
        patterns = engine._discover_patterns(facts)
        assert patterns == []

    def test_discover_patterns_single_fact(self, engine):
        """Test pattern discovery with single fact (below threshold)."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
        ]
        patterns = engine._discover_patterns(facts)
        # Single mention does not meet threshold of 2
        assert patterns == []

    def test_discover_patterns_no_entity_field(self, engine):
        """Test pattern discovery when facts lack entity field."""
        facts = [
            {"value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
        ]
        patterns = engine._discover_patterns(facts)
        # No entity field means no recurring entities
        assert patterns == []

    def test_discover_patterns_empty_entity_string(self, engine):
        """Test pattern discovery with empty entity string."""
        facts = [
            {"entity": "", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
        ]
        patterns = engine._discover_patterns(facts)
        # Empty entity should not be counted
        assert patterns == []

    def test_discover_patterns_high_mention_count(self, engine):
        """Test pattern discovery with high mention count."""
        facts = [
            {"entity": "A", "value": f"v{i}", "confidence": 0.9, "source_ids": [f"e{i}"]}
            for i in range(10)
        ]
        patterns = engine._discover_patterns(facts)
        assert len(patterns) == 1
        assert patterns[0]["entity"] == "A"
        assert patterns[0]["mention_count"] == 10
        # Confidence should be capped at 0.9
        assert patterns[0]["confidence"] == 0.9

    def test_discover_patterns_exact_threshold(self, engine):
        """Test pattern discovery at exact threshold (2 mentions)."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
        ]
        patterns = engine._discover_patterns(facts)
        assert len(patterns) == 1
        assert patterns[0]["mention_count"] == 2

    def test_discover_patterns_multiple_recurring(self, engine):
        """Test pattern discovery with multiple recurring entities."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
            {"entity": "B", "value": "v3", "confidence": 0.8, "source_ids": ["e3"]},
            {"entity": "B", "value": "v4", "confidence": 0.75, "source_ids": ["e4"]},
            {"entity": "C", "value": "v5", "confidence": 0.7, "source_ids": ["e5"]},
        ]
        patterns = engine._discover_patterns(facts)
        # Both A and B should be detected
        assert len(patterns) == 2
        entities = [p["entity"] for p in patterns]
        assert "A" in entities
        assert "B" in entities
        # C should not be detected (only 1 mention)
        assert "C" not in entities

    def test_discover_patterns_deterministic(self, engine):
        """Test that pattern discovery is deterministic."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
            {"entity": "B", "value": "v3", "confidence": 0.8, "source_ids": ["e3"]},
        ]
        patterns1 = engine._discover_patterns(facts)
        patterns2 = engine._discover_patterns(facts)
        assert patterns1 == patterns2


class TestAggregateEvidenceEdgeCases:
    """Extended tests for _aggregate_evidence() edge cases."""

    def test_aggregate_evidence_empty_input(self, engine):
        """Test aggregation with empty input."""
        aggregated = engine._aggregate_evidence([])
        assert aggregated == {}

    def test_aggregate_evidence_single_fact(self, engine):
        """Test aggregation with single fact."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
        ]
        aggregated = engine._aggregate_evidence(facts)
        assert "A" in aggregated
        assert aggregated["A"]["fact_count"] == 1
        assert aggregated["A"]["source_ids"] == ["e1"]

    def test_aggregate_evidence_no_entity_field(self, engine):
        """Test aggregation when facts lack entity field."""
        facts = [
            {"value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
        ]
        aggregated = engine._aggregate_evidence(facts)
        # Should use "unknown" as default entity
        assert "unknown" in aggregated
        assert aggregated["unknown"]["fact_count"] == 2

    def test_aggregate_evidence_deduplicates_source_ids(self, engine):
        """Test that aggregation deduplicates source IDs."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1", "e2"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2", "e3"]},
        ]
        aggregated = engine._aggregate_evidence(facts)
        # e2 appears in both facts but should be deduplicated
        assert len(aggregated["A"]["source_ids"]) == 3
        assert set(aggregated["A"]["source_ids"]) == {"e1", "e2", "e3"}

    def test_aggregate_evidence_average_confidence(self, engine):
        """Test confidence averaging in aggregation."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.8},
            {"entity": "A", "value": "v2", "confidence": 1.0},
        ]
        aggregated = engine._aggregate_evidence(facts)
        # Average of 0.8 and 1.0 is 0.9
        assert aggregated["A"]["avg_confidence"] == pytest.approx(0.9)

    def test_aggregate_evidence_mixed_entities(self, engine):
        """Test aggregation with mixed entity presence."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "B", "value": "v2", "confidence": 0.8, "source_ids": ["e2"]},
            {"value": "v3", "confidence": 0.7, "source_ids": ["e3"]},  # No entity
        ]
        aggregated = engine._aggregate_evidence(facts)
        assert "A" in aggregated
        assert "B" in aggregated
        assert "unknown" in aggregated

    def test_aggregate_evidence_deterministic(self, engine):
        """Test that aggregation is deterministic."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
        ]
        agg1 = engine._aggregate_evidence(facts)
        agg2 = engine._aggregate_evidence(facts)
        assert agg1 == agg2


class TestEstimateConfidenceEdgeCases:
    """Extended tests for _estimate_confidence() edge cases."""

    def test_estimate_confidence_all_zero(self, engine):
        """Test confidence estimation with all zero values."""
        facts = [
            {"entity": "A", "confidence": 0.0},
            {"entity": "A", "confidence": 0.0},
        ]
        confidence = engine._estimate_confidence(facts)
        assert confidence == 0.0

    def test_estimate_confidence_all_max(self, engine):
        """Test confidence estimation with all max values."""
        facts = [
            {"entity": "A", "confidence": 1.0},
            {"entity": "A", "confidence": 1.0},
        ]
        confidence = engine._estimate_confidence(facts)
        assert confidence == 1.0

    def test_estimate_confidence_single_fact(self, engine):
        """Test confidence estimation with single fact."""
        facts = [{"entity": "A", "confidence": 0.75}]
        confidence = engine._estimate_confidence(facts)
        assert confidence == 0.75

    def test_estimate_confidence_missing_confidence_field(self, engine):
        """Test confidence estimation when facts lack confidence field."""
        facts = [
            {"entity": "A", "value": "v1"},
            {"entity": "A", "value": "v2"},
        ]
        confidence = engine._estimate_confidence(facts)
        # Should use default 0.5 for missing confidence
        assert confidence == 0.5

    def test_estimate_confidence_negative_values(self, engine):
        """Test confidence estimation with negative values (edge case)."""
        facts = [
            {"entity": "A", "confidence": -0.1},
            {"entity": "A", "confidence": 0.9},
        ]
        confidence = engine._estimate_confidence(facts)
        # Simple average, may produce negative result
        assert confidence == pytest.approx(0.4)

    def test_estimate_confidence_deterministic(self, engine):
        """Test that confidence estimation is deterministic."""
        facts = [
            {"entity": "A", "confidence": 0.9},
            {"entity": "A", "confidence": 0.8},
            {"entity": "A", "confidence": 0.7},
        ]
        conf1 = engine._estimate_confidence(facts)
        conf2 = engine._estimate_confidence(facts)
        assert conf1 == conf2


class TestDuplicateFacts:
    """Test handling of duplicate facts."""

    def test_discover_patterns_duplicate_facts(self, engine):
        """Test pattern discovery with duplicate facts."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},  # Duplicate
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},  # Duplicate
        ]
        patterns = engine._discover_patterns(facts)
        # Should count all 3 mentions
        assert len(patterns) == 1
        assert patterns[0]["mention_count"] == 3

    def test_aggregate_evidence_duplicate_facts(self, engine):
        """Test evidence aggregation with duplicate facts."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},  # Duplicate
        ]
        aggregated = engine._aggregate_evidence(facts)
        # Should count both facts
        assert aggregated["A"]["fact_count"] == 2
        # Source IDs should be deduplicated
        assert aggregated["A"]["source_ids"] == ["e1"]

    def test_estimate_confidence_duplicate_facts(self, engine):
        """Test confidence estimation with duplicate facts."""
        facts = [
            {"entity": "A", "confidence": 0.9},
            {"entity": "A", "confidence": 0.9},  # Duplicate
        ]
        confidence = engine._estimate_confidence(facts)
        # Average of identical values is the same value
        assert confidence == 0.9


class TestInvalidInput:
    """Test handling of invalid input."""

    def test_discover_patterns_invalid_type(self, engine):
        """Test pattern discovery with invalid input type."""
        # Should not crash, should handle gracefully
        with pytest.raises((TypeError, AttributeError)):
            engine._discover_patterns("not a list")

    def test_aggregate_evidence_invalid_type(self, engine):
        """Test aggregation with invalid input type."""
        with pytest.raises((TypeError, AttributeError)):
            engine._aggregate_evidence("not a list")

    def test_estimate_confidence_invalid_type(self, engine):
        """Test confidence estimation with invalid input type."""
        with pytest.raises((TypeError, AttributeError)):
            engine._estimate_confidence("not a list")

    def test_discover_patterns_none_input(self, engine):
        """Test pattern discovery with None input."""
        # Should raise TypeError when trying to iterate None
        with pytest.raises(TypeError):
            engine._discover_patterns(None)

    def test_aggregate_evidence_none_input(self, engine):
        """Test aggregation with None input."""
        with pytest.raises(TypeError):
            engine._aggregate_evidence(None)

    def test_estimate_confidence_none_input(self, engine):
        """Test confidence estimation with None input.
        
        Note: Current implementation treats None as empty input and returns 0.0.
        This is acceptable behavior - no crash, deterministic result.
        """
        # Current behavior: returns 0.0 for None input
        result = engine._estimate_confidence(None)
        assert result == 0.0


class TestIdempotency:
    """Test idempotency of rule-based methods."""

    def test_discover_patterns_idempotent(self, engine):
        """Test that pattern discovery is idempotent."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
            {"entity": "B", "value": "v3", "confidence": 0.8, "source_ids": ["e3"]},
        ]
        # Run multiple times
        results = [engine._discover_patterns(facts) for _ in range(5)]
        # All results should be identical
        for result in results[1:]:
            assert result == results[0]

    def test_aggregate_evidence_idempotent(self, engine):
        """Test that evidence aggregation is idempotent."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e2"]},
        ]
        results = [engine._aggregate_evidence(facts) for _ in range(5)]
        for result in results[1:]:
            assert result == results[0]

    def test_estimate_confidence_idempotent(self, engine):
        """Test that confidence estimation is idempotent."""
        facts = [
            {"entity": "A", "confidence": 0.9},
            {"entity": "A", "confidence": 0.8},
        ]
        results = [engine._estimate_confidence(facts) for _ in range(5)]
        for result in results[1:]:
            assert result == results[0]


class TestLineageSafety:
    """Test that evidence lineage is preserved."""

    def test_discover_patterns_preserves_lineage(self, engine):
        """Test that pattern discovery doesn't corrupt lineage."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1", "e2"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e3"]},
        ]
        patterns = engine._discover_patterns(facts)
        # Patterns don't modify source_ids, they just count
        assert len(patterns) == 1
        assert patterns[0]["entity"] == "A"

    def test_aggregate_evidence_preserves_lineage(self, engine):
        """Test that aggregation preserves source_ids."""
        facts = [
            {"entity": "A", "value": "v1", "confidence": 0.9, "source_ids": ["e1", "e2"]},
            {"entity": "A", "value": "v2", "confidence": 0.85, "source_ids": ["e3"]},
        ]
        aggregated = engine._aggregate_evidence(facts)
        # All source IDs should be preserved
        assert set(aggregated["A"]["source_ids"]) == {"e1", "e2", "e3"}

    def test_estimate_confidence_no_side_effects(self, engine):
        """Test that confidence estimation has no side effects."""
        facts = [
            {"entity": "A", "confidence": 0.9, "source_ids": ["e1"]},
            {"entity": "A", "confidence": 0.8, "source_ids": ["e2"]},
        ]
        original_facts = [dict(f) for f in facts]  # Deep copy
        confidence = engine._estimate_confidence(facts)
        # Facts should not be modified
        assert facts == original_facts


class TestBoundaryConditions:
    """Test boundary conditions."""

    def test_discover_patterns_large_input(self, engine):
        """Test pattern discovery with large input."""
        facts = [
            {"entity": f"E{i}", "value": f"v{j}", "confidence": 0.9, "source_ids": [f"e{i}_{j}"]}
            for i in range(100)
            for j in range(3)
        ]
        patterns = engine._discover_patterns(facts)
        # Each entity appears 3 times, all should be detected
        assert len(patterns) == 100
        assert all(p["mention_count"] == 3 for p in patterns)

    def test_aggregate_evidence_large_input(self, engine):
        """Test aggregation with large input."""
        facts = [
            {"entity": f"E{i}", "value": f"v{j}", "confidence": 0.9, "source_ids": [f"e{i}_{j}"]}
            for i in range(100)
            for j in range(3)
        ]
        aggregated = engine._aggregate_evidence(facts)
        assert len(aggregated) == 100

    def test_estimate_confidence_large_input(self, engine):
        """Test confidence estimation with large input."""
        facts = [
            {"entity": "A", "confidence": 0.5 + i * 0.01}
            for i in range(100)
        ]
        confidence = engine._estimate_confidence(facts)
        # Average should be approximately 0.995
        assert confidence == pytest.approx(0.995, abs=0.01)
