"""
Phase 26-G-C-D: Cron Safety Mechanisms Implementation Tests

Tests for the Cron safety mechanisms implemented in app.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import UUID
import os as os_module

WORKSPACE_ID = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")


def make_mock_result(rows=None, scalar_value=None):
    """Helper to create a mock SQLAlchemy result."""
    result = MagicMock()
    if rows is not None:
        result.fetchall.return_value = rows
    if scalar_value is not None:
        result.scalar.return_value = scalar_value
    return result


class TestPreFlightGuard:
    """Test pre-flight validation before Cron execution."""
    
    @pytest.mark.asyncio
    async def test_preflight_passes_when_valid(self):
        """Test that pre-flight passes when all conditions are met."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        mock_result = make_mock_result(scalar_value=1)
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_ctx
        
        validator = CronSafetyValidator(engine=mock_engine)
        
        with patch.dict(os_module.environ, {'AUTO_APPROVE': 'false'}):
            is_valid, reason = await validator.pre_flight_check(
                workspace_id=WORKSPACE_ID,
                task_id="test_task"
            )
        
        assert is_valid == True
        assert "passed" in reason
    
    @pytest.mark.asyncio
    async def test_preflight_fails_when_auto_approve_enabled(self):
        """Test that pre-flight fails when AUTO_APPROVE is enabled."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        mock_result = make_mock_result(scalar_value=1)
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_ctx
        
        validator = CronSafetyValidator(engine=mock_engine)
        
        with patch.dict(os_module.environ, {'AUTO_APPROVE': 'true'}):
            is_valid, reason = await validator.pre_flight_check(
                workspace_id=WORKSPACE_ID,
                task_id="test_task"
            )
        
        assert is_valid == False
        assert "AUTO_APPROVE" in reason
    
    @pytest.mark.asyncio
    async def test_preflight_fails_when_workspace_missing(self):
        """Test that pre-flight fails when workspace doesn't exist."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        mock_result = make_mock_result(scalar_value=0)
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_ctx
        
        validator = CronSafetyValidator(engine=mock_engine)
        
        with patch.dict(os_module.environ, {'AUTO_APPROVE': 'false'}):
            is_valid, reason = await validator.pre_flight_check(
                workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
                task_id="test_task"
            )
        
        assert is_valid == False
        assert "not found" in reason
    
    @pytest.mark.asyncio
    async def test_preflight_no_engine(self):
        """Test pre-flight fails when no engine is available."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        validator = CronSafetyValidator(engine=None)
        is_valid, reason = await validator.pre_flight_check(
            workspace_id=WORKSPACE_ID,
            task_id="test_task"
        )
        
        assert is_valid == False
        assert "No database engine" in reason


class TestBatchSafety:
    """Test batch-level safety validations."""
    
    @pytest.mark.asyncio
    async def test_batch_exceeds_limit(self):
        """Test batch rejection when exceeding size limit."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        validator = CronSafetyValidator()
        
        large_batch = [{"id": str(i)} for i in range(150)]
        
        is_valid, reason = await validator.validate_batch_safety(
            workspace_id=WORKSPACE_ID,
            batch_candidates=large_batch,
            batch_id=1
        )
        
        assert is_valid == False
        assert "exceeds limit" in reason
    
    @pytest.mark.asyncio
    async def test_batch_invalid_evidence(self):
        """Test batch rejection when evidence not found."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        mock_result = MagicMock()
        mock_result.fetchone = lambda: None
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_ctx
        
        validator = CronSafetyValidator(engine=mock_engine)
        
        batch = [{
            "id": "test-id",
            "evidence_id": "00000000-0000-0000-0000-000000000000",
        }]
        
        is_valid, reason = await validator.validate_batch_safety(
            workspace_id=WORKSPACE_ID,
            batch_candidates=batch,
            batch_id=1
        )
        
        assert is_valid == False
        assert "invalid candidates" in reason
    
    @pytest.mark.asyncio
    async def test_batch_all_valid(self):
        """Test batch passes when all evidence is valid."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        mock_result = MagicMock()
        mock_result.fetchone = lambda: (1,)
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_ctx
        
        validator = CronSafetyValidator(engine=mock_engine)
        
        batch = [{
            "id": "test-id",
            "evidence_id": "06a81234-5678-9abc-def0-123456789abc",
        }]
        
        is_valid, reason = await validator.validate_batch_safety(
            workspace_id=WORKSPACE_ID,
            batch_candidates=batch,
            batch_id=1
        )
        
        assert is_valid == True
        assert "valid" in reason


class TestPostFlightValidation:
    """Test post-flight validation checks."""
    
    @pytest.mark.asyncio
    async def test_post_flight_passes(self):
        """Test post-flight passes when all checks pass."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        mock_result = make_mock_result(rows=[])
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_ctx
        
        validator = CronSafetyValidator(engine=mock_engine)
        
        is_valid, reason = await validator.validate_post_flight(
            workspace_id=WORKSPACE_ID,
            expected_proposal_ids={"prop1", "prop2"},
            expected_candidate_ids={"cand1"},
            actual_proposal_ids={"prop1", "prop2"},
            actual_candidate_ids={"cand1"},
            run_id="test_run"
        )
        
        assert is_valid == True
        assert "passed" in reason
    
    @pytest.mark.asyncio
    async def test_post_flight_missing_proposals(self):
        """Test post-flight fails when expected proposals missing."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        validator = CronSafetyValidator()
        
        is_valid, reason = await validator.validate_post_flight(
            workspace_id=WORKSPACE_ID,
            expected_proposal_ids={"prop1", "prop2"},
            expected_candidate_ids=set(),
            actual_proposal_ids=set(),
            actual_candidate_ids=set(),
            run_id="test_run"
        )
        
        assert is_valid == False
        assert "missing" in reason.lower() or "not created" in reason.lower()


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_threshold(self):
        """Test circuit breaker triggers after threshold failures."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        validator = CronSafetyValidator()
        validator.failure_counter = 0
        
        for i in range(validator.CIRCUIT_BREAKER_THRESHOLD):
            triggered = await validator.record_failure(f"failure_{i}", f"run_{i}")
            if i == validator.CIRCUIT_BREAKER_THRESHOLD - 1:
                assert triggered == True
            else:
                assert triggered == False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self):
        """Test circuit breaker resets on success."""
        from tests.safety_mechanisms import CronSafetyValidator
        
        validator = CronSafetyValidator()
        validator.failure_counter = 5
        
        await validator.reset_failure_counter()
        
        assert validator.failure_counter == 0


class TestIdempotency:
    """Test idempotency properties."""
    
    def test_duplicate_prevention(self):
        """Test that duplicate detection works."""
        pass
    
    def test_approved_proposals_not_reprocessed(self):
        """Test that approved proposals are not reprocessed."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
