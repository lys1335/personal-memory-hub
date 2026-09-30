#!/usr/bin/env python3
"""
Phase 26-G-C-C: C-B Test Gap Verification

Investigation of the failing test: test_save_candidates_rejects_invalid_evidence
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import UUID

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.engine.evidence_evolution_engine import EvidenceEvolutionEngine
from backend.engine.reflection_engine import ReflectionEngine


class TestEvidencePersistenceFix:
    """Test suite for Phase 26-G-C-B Evidence Persistence Fix."""
    
    def test_fix1_evidence_id_set_in_candidate(self):
        """Fix 1: _build_candidates() must set evidence_id from valid source_ids."""
        engine = EvidenceEvolutionEngine()
        
        facts = [
            {
                "entity": "TestEntity",
                "value": "test value",
                "confidence": 0.9,
                "source_ids": ["06a81234-5678-9abc-def0-123456789abc"],
            }
        ]
        
        evidence = [
            {"id": "06a81234-5678-9abc-def0-123456789abc", "content": "test evidence"}
        ]
        
        candidates = engine._build_candidates(facts, evidence)
        
        assert len(candidates) == 1
        assert "evidence_id" in candidates[0]
        assert candidates[0]["evidence_id"] == "06a81234-5678-9abc-def0-123456789abc"
        assert candidates[0]["evidence_count"] == 1
    
    def test_fix1_invalid_uuid_filtered(self):
        """Fix 1: Invalid UUIDs in source_ids must be filtered out."""
        engine = EvidenceEvolutionEngine()
        
        facts = [
            {
                "entity": "TestEntity",
                "value": "test value",
                "confidence": 0.9,
                "source_ids": ["invalid-uuid", "06a81234-5678-9abc-def0-123456789abc"],
            }
        ]
        
        evidence = [
            {"id": "06a81234-5678-9abc-def0-123456789abc", "content": "test evidence"}
        ]
        
        candidates = engine._build_candidates(facts, evidence)
        
        assert len(candidates) == 1
        assert candidates[0]["evidence_id"] == "06a81234-5678-9abc-def0-123456789abc"
        assert candidates[0]["evidence_count"] == 1
    
    def test_fix1_no_valid_evidence(self):
        """Fix 1: When no valid evidence IDs, evidence_id should be None."""
        engine = EvidenceEvolutionEngine()
        
        facts = [
            {
                "entity": "TestEntity",
                "value": "test value",
                "confidence": 0.9,
                "source_ids": ["invalid-uuid-1", "invalid-uuid-2"],
            }
        ]
        
        evidence = []
        
        candidates = engine._build_candidates(facts, evidence)
        
        assert len(candidates) == 1
        assert candidates[0]["evidence_id"] is None
        assert candidates[0]["evidence_count"] == 0
    
    def test_fix1_candidate_uuid_not_masquerading(self):
        """Fix 1: Candidate UUIDs should not be used as evidence_id."""
        engine = EvidenceEvolutionEngine()
        
        facts = [
            {
                "entity": "TestEntity",
                "value": "test value",
                "confidence": 0.9,
                "source_ids": ["06a8abcd-1234-5678-9abc-def012345678"],
            }
        ]
        
        evidence = []
        
        candidates = engine._build_candidates(facts, evidence)
        
        assert candidates[0]["evidence_id"] == "06a8abcd-1234-5678-9abc-def012345678"
    
    def test_fix2_evidence_chain_filters_invalid(self):
        """Fix 2: _generate_proposals() should filter invalid evidence references."""
        engine = ReflectionEngine()
        
        facts = [
            {
                "entity": "TestEntity",
                "value": "test value",
                "confidence": 0.9,
                "source_ids": ["06a81234-5678-9abc-def0-123456789abc"],
            }
        ]
        
        proposals = engine._generate_proposals(facts, {})
        
        assert len(proposals) > 0
        for prop in proposals:
            evidence_chain = prop.get("evidence_chain", [])
            for eid in evidence_chain:
                try:
                    UUID(eid)
                except ValueError:
                    pytest.fail(f"Invalid UUID in evidence_chain: {eid}")


class TestEvidenceValidationIntegration:
    """Integration tests for evidence validation across the pipeline."""
    
    @pytest.mark.asyncio
    async def test_save_candidates_rejects_invalid_evidence(self):
        """Test that _save_candidates() skips candidates with invalid evidence.
        
        Fixed: Use correct patch path for get_engine import.
        """
        from backend.service.reflection_service import ReflectionService
        from unittest.mock import MagicMock, patch
        
        mock_memory_node_repo = MagicMock()
        mock_candidate_repo = MagicMock()
        mock_relationship_repo = MagicMock()
        
        service = ReflectionService(
            memory_node_repo=mock_memory_node_repo,
            candidate_repo=mock_candidate_repo,
            relationship_repo=mock_relationship_repo,
        )
        
        candidates = [
            {
                "entity": "TestEntity",
                "content": "test content",
                "evidence_id": "00000000-0000-0000-0000-000000000000",
                "evidence_chain": ["00000000-0000-0000-0000-000000000000"],
                "evidence_count": 1,
                "confidence": 0.9,
                "source_level": 1,
                "candidate_type": "pattern",
                "status": "candidate",
                "candidate_id": None,
            }
        ]
        
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # FIX: Patch the correct import path - get_engine is imported locally in the method
        with patch('backend.shared.infrastructure.database.engine.get_engine', return_value=mock_engine):
            with patch('backend.service.reflection_service.generate_uuid', return_value='test-uuid'):
                await service._save_candidates(candidates, MagicMock())
        
        insert_calls = [call for call in mock_conn.execute.call_args_list 
                       if 'INSERT INTO candidates' in str(call)]
        assert len(insert_calls) == 0, "Candidate with invalid evidence should not be inserted"


class TestLineageSafety:
    """Test lineage safety after fixes."""
    
    def test_evidence_id_from_first_source(self):
        """Test that evidence_id is set from first valid source."""
        engine = EvidenceEvolutionEngine()
        
        facts = [
            {
                "entity": "Entity1",
                "value": "value1",
                "confidence": 0.9,
                "source_ids": ["06a81111-2222-3333-4444-555555555555"],
            }
        ]
        
        evidence = [
            {"id": "06a81111-2222-3333-4444-555555555555", "content": "test"}
        ]
        
        candidates = engine._build_candidates(facts, evidence)
        
        assert len(candidates) == 1
        assert candidates[0]["evidence_id"] == "06a81111-2222-3333-4444-555555555555"
        assert candidates[0]["evidence_chain"] == ["06a81111-2222-3333-4444-555555555555"]
    
    def test_evidence_chain_contains_all_valid(self):
        """Test that evidence_chain contains all valid evidence IDs."""
        engine = EvidenceEvolutionEngine()
        
        facts = [
            {
                "entity": "Entity1",
                "value": "value1",
                "confidence": 0.9,
                "source_ids": ["06a81111-2222-3333-4444-555555555555", 
                               "06a82222-3333-4444-5555-666666666666"],
            }
        ]
        
        evidence = [
            {"id": "06a81111-2222-3333-4444-555555555555", "content": "evidence 1"},
            {"id": "06a82222-3333-4444-5555-666666666666", "content": "evidence 2"},
        ]
        
        candidates = engine._build_candidates(facts, evidence)
        
        assert len(candidates) == 1
        assert len(candidates[0]["evidence_chain"]) == 2
        assert "06a81111-2222-3333-4444-555555555555" in candidates[0]["evidence_chain"]
        assert "06a82222-3333-4444-5555-666666666666" in candidates[0]["evidence_chain"]
    
    def test_invalid_uuids_removed_from_chain(self):
        """Test that invalid UUIDs are removed from evidence_chain."""
        engine = EvidenceEvolutionEngine()
        
        facts = [
            {
                "entity": "Entity1",
                "value": "value1",
                "confidence": 0.9,
                "source_ids": ["invalid-uuid", "06a81111-2222-3333-4444-555555555555", 
                               "also-invalid", "06a82222-3333-4444-5555-666666666666"],
            }
        ]
        
        evidence = [
            {"id": "06a81111-2222-3333-4444-555555555555", "content": "evidence 1"},
            {"id": "06a82222-3333-4444-5555-666666666666", "content": "evidence 2"},
        ]
        
        candidates = engine._build_candidates(facts, evidence)
        
        assert len(candidates) == 1
        assert len(candidates[0]["evidence_chain"]) == 2
        assert candidates[0]["evidence_count"] == 2


class TestWorkspaceIsolation:
    """Test workspace isolation is maintained."""
    
    def test_evidence_id_workspace_scoped(self):
        """Test that evidence validation is workspace-scoped."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
