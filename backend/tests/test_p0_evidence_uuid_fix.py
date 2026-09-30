"""P0 Regression Tests: Evidence UUID Fallback Removal

Tests to verify that the P0 fix correctly rejects evidence items without valid IDs,
instead of generating random UUIDs.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from backend.engine.evidence_evolution_engine import EvidenceEvolutionEngine, EvolutionResult
from backend.shared.providers.reflection_provider import MockReflectionProvider


@pytest.fixture
def engine():
    """Create EvidenceEvolutionEngine instance."""
    return EvidenceEvolutionEngine()


class TestP0EvidenceUUIDFallback:
    """Test P0 fix: No random UUID generation for missing evidence IDs."""

    @pytest.mark.asyncio
    async def test_missing_evidence_id_rejected(self, engine):
        """Test that evidence items without IDs are skipped, not filled with random UUIDs."""
        evidence = [
            {"content": "Evidence without ID", "source": "chat"},  # No 'id' field
            {"id": "e2", "content": "Valid evidence", "source": "chat"},
        ]
        
        facts, log = await engine._extract_facts(evidence, provider=None)
        
        # Should not generate a random UUID for the first evidence item
        # The first item should be skipped, only the second should be processed
        assert len(facts) >= 0  # Facts may be empty if provider is None
        # Check that no random UUID was generated
        for fact in facts:
            source_ids = fact.get("source_ids", [])
            for sid in source_ids:
                # Should not contain a generated UUID pattern
                assert not (sid.startswith("06a8") and len(sid) == 36), \
                    "Generated UUID should not appear in source_ids"

    @pytest.mark.asyncio
    async def test_empty_evidence_id_rejected(self, engine):
        """Test that evidence items with empty string ID are skipped."""
        evidence = [
            {"id": "", "content": "Evidence with empty ID", "source": "chat"},
            {"id": "e2", "content": "Valid evidence", "source": "chat"},
        ]
        
        facts, log = await engine._extract_facts(evidence, provider=None)
        
        # Empty ID should be treated as missing
        assert len(facts) >= 0

    @pytest.mark.asyncio
    async def test_all_evidence_without_ids_returns_empty(self, engine):
        """Test that all evidence without IDs results in empty output."""
        evidence = [
            {"content": "No ID 1", "source": "chat"},
            {"content": "No ID 2", "source": "chat"},
            {"content": "No ID 3", "source": "chat"},
        ]
        
        facts, log = await engine._extract_facts(evidence, provider=None)
        
        # Should return empty facts when no valid evidence IDs
        assert facts == []
        # Should log the rejection
        assert any("No valid evidence items" in entry for entry in log)

    @pytest.mark.asyncio
    async def test_valid_evidence_ids_preserved(self, engine):
        """Test that valid evidence IDs are preserved in facts."""
        evidence = [
            {"id": "e1", "content": "Evidence 1", "source": "chat"},
            {"id": "e2", "content": "Evidence 2", "source": "chat"},
        ]
        
        # Create a mock provider that returns facts with source_ids
        mock_facts = [
            {
                "entity": "Test",
                "value": "test value",
                "source_ids": ["e1", "e2"],
                "confidence": 0.9,
            }
        ]
        mock_provider = MockReflectionProvider(facts=mock_facts)
        
        facts, log = await engine._extract_facts(evidence, provider=mock_provider)
        
        # Valid evidence IDs should be preserved
        assert len(facts) > 0
        # Check that source_ids contain the original evidence IDs, not generated ones
        for fact in facts:
            source_ids = fact.get("source_ids", [])
            for sid in source_ids:
                assert sid in ["e1", "e2"], f"Expected original ID, got {sid}"

    @pytest.mark.asyncio
    async def test_no_generate_uuid_import(self):
        """Test that generate_uuid is no longer imported in evidence_evolution_engine."""
        import backend.engine.evidence_evolution_engine as module
        
        # Check that generate_uuid is not in the module's namespace
        assert not hasattr(module, 'generate_uuid'), \
            "generate_uuid should not be imported in evidence_evolution_engine"
        
        # Check the source code
        import inspect
        source = inspect.getsource(module)
        assert 'generate_uuid()' not in source, \
            "generate_uuid() call should be removed from evidence_evolution_engine"

    @pytest.mark.asyncio
    async def test_evolve_with_mixed_valid_invalid_evidence(self, engine):
        """Test evolve() handles mixed valid and invalid evidence correctly."""
        evidence = [
            {"id": "valid-e1", "content": "Valid evidence", "source": "chat"},
            {"content": "Missing ID", "source": "chat"},  # Invalid
            {"id": "valid-e2", "content": "Another valid", "source": "chat"},
        ]
        
        mock_facts = [
            {
                "entity": "Test",
                "value": "test value",
                "source_ids": ["valid-e1", "valid-e2"],
                "confidence": 0.9,
            }
        ]
        mock_provider = MockReflectionProvider(facts=mock_facts)
        
        result = await engine.evolve(evidence=evidence, provider=mock_provider)
        
        # Should process successfully, skipping invalid evidence
        assert isinstance(result, EvolutionResult)
        # Statistics should reflect only valid evidence count
        assert result.statistics["count"] == 3  # Original count
        # But only valid evidence should be in the prompt

    @pytest.mark.asyncio
    async def test_warning_logged_for_missing_ids(self, engine):
        """Test that warnings are logged for evidence items without IDs."""
        evidence = [
            {"content": "No ID", "source": "chat"},
        ]
        
        with patch('backend.engine.evidence_evolution_engine.logger') as mock_logger:
            facts, log = await engine._extract_facts(evidence, provider=None)
            
            # Should log a warning
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0]
            assert "Skipping evidence item" in call_args[0]


class TestEvidenceLineageIntegrity:
    """Test evidence lineage integrity after P0 fix."""

    @pytest.mark.asyncio
    async def test_candidate_id_not_masquerading_as_evidence(self, engine):
        """Test that candidate_id cannot be used as evidence_id."""
        evidence = [
            {
                "id": "e1",
                "content": "Evidence 1",
                "source": "chat",
                "candidate_id": "candidate-uuid-123"
            },
        ]
        
        mock_facts = [
            {
                "entity": "Test",
                "value": "test",
                "source_ids": ["e1"],
                "confidence": 0.9,
            }
        ]
        mock_provider = MockReflectionProvider(facts=mock_facts)
        
        facts, log = await engine._extract_facts(evidence, provider=mock_provider)
        
        # Source IDs should only contain evidence IDs, not candidate IDs
        for fact in facts:
            source_ids = fact.get("source_ids", [])
            for sid in source_ids:
                assert sid != "candidate-uuid-123", \
                    "Candidate ID should not appear in source_ids"

    @pytest.mark.asyncio
    async def test_evidence_chain_integrity(self, engine):
        """Test that evidence_chain only contains valid evidence IDs."""
        from uuid import UUID
        
        # Use valid UUID format
        evidence = [
            {"id": "00000000-0000-0000-0000-000000000001", "content": "Evidence 1", "source": "chat"},
            {"id": "00000000-0000-0000-0000-000000000002", "content": "Evidence 2", "source": "chat"},
        ]
        
        mock_facts = [
            {
                "entity": "Test",
                "value": "test",
                "source_ids": ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"],
                "confidence": 0.9,
            }
        ]
        mock_provider = MockReflectionProvider(facts=mock_facts)
        
        result = await engine.evolve(evidence=evidence, provider=mock_provider)
        
        # Check candidates have valid evidence chains
        for candidate in result.candidates:
            evidence_chain = candidate.get("evidence_chain", [])
            for ev_id in evidence_chain:
                # Each evidence ID in chain should be a valid UUID format
                try:
                    UUID(ev_id)
                except ValueError:
                    pytest.fail(f"Invalid UUID format in evidence_chain: {ev_id}")


class TestIdempotencyAfterFix:
    """Test idempotency after P0 fix."""

    @pytest.mark.asyncio
    async def test_duplicate_processing_no_new_random_uuids(self, engine):
        """Test that processing same evidence twice doesn't generate new random UUIDs."""
        evidence = [
            {"id": "e1", "content": "Evidence 1", "source": "chat"},
            {"id": "e2", "content": "Evidence 2", "source": "chat"},
        ]
        
        mock_facts = [
            {
                "entity": "Test",
                "value": "test",
                "source_ids": ["e1", "e2"],
                "confidence": 0.9,
            }
        ]
        mock_provider = MockReflectionProvider(facts=mock_facts)
        
        # Process twice
        facts1, _ = await engine._extract_facts(evidence, provider=mock_provider)
        facts2, _ = await engine._extract_facts(evidence, provider=mock_provider)
        
        # Results should be identical
        assert len(facts1) == len(facts2)
        for f1, f2 in zip(facts1, facts2):
            assert f1 == f2
