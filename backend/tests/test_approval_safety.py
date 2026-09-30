"""
Phase 26-D Approval Safety Tests

Tests for approve_proposal() safety guarantees:
1. Idempotency - already approved/rejected proposals return early
2. Transactional integrity - all DB operations in single transaction
3. No side effects on already-processed proposals
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from uuid import UUID
from sqlalchemy import text

from backend.service.reflection_service import ReflectionService
from backend.service.dto import ReflectionExecutionResult, ReflectionStatus
from backend.service.exceptions import ValidationError


class MockRepository:
    """Mock repository for testing."""
    
    def __init__(self):
        self.data = {}
        self.calls = []
    
    async def execute(self, *args, **kwargs):
        self.calls.append(('execute', args, kwargs))
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        return mock_result


class TestApproveProposalSafety:
    """Test approve_proposal() safety guarantees."""

    @pytest.fixture
    def service(self):
        """Create ReflectionService instance with mocked dependencies."""
        memory_node_repo = MockRepository()
        candidate_repo = MockRepository()
        relationship_repo = MockRepository()
        
        service = ReflectionService(
            memory_node_repo=memory_node_repo,
            candidate_repo=candidate_repo,
            relationship_repo=relationship_repo,
        )
        service._generate_id = MagicMock(return_value=UUID("00000000-0000-0000-0000-000000000001"))
        return service

    @pytest.mark.asyncio
    async def test_approve_pending_proposal_success(self, service, monkeypatch):
        """Test 1: Normal path - pending proposal gets approved."""
        workspace_id = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
        proposal_id = UUID("06a81a90-fafd-7bc7-8000-fcb22cef6f1a")
        
        # Track all execute calls
        execute_calls = []
        
        def create_result(args_str):
            result = MagicMock()
            
            # SELECT proposal
            if "SELECT * FROM proposals" in args_str:
                result.fetchone.return_value = MagicMock(_mapping={
                    "id": str(proposal_id),
                    "workspace_id": str(workspace_id),
                    "status": "pending",
                    "entity": "Test",
                    "summary": "Test",
                    "confidence": 0.5,
                    "target_level": 1,
                    "candidate_id": "a4c2719a-7364-45fc-97be-cb330696ea84",
                    "evidence_chain": [],
                })
            # UPDATE proposal
            elif "UPDATE proposals" in args_str:
                result.fetchone.return_value = MagicMock(_mapping={"status": "approved"})
            # SELECT status verify
            elif "SELECT status FROM proposals" in args_str:
                mock_row = MagicMock()
                mock_row._mapping = {"status": "approved"}
                mock_row.__getitem__ = lambda self, key: "approved" if key == 0 else None
                result.fetchone.return_value = mock_row
            # INSERT memory_nodes
            elif "INSERT INTO memory_nodes" in args_str:
                result.fetchone.return_value = None
            # SELECT from memory_nodes
            elif "SELECT id FROM memory_nodes" in args_str:
                result.fetchone.return_value = None
            # UPDATE candidates
            elif "UPDATE candidates" in args_str:
                result.fetchone.return_value = None
            # SELECT entity_id from candidates
            elif "SELECT entity_id FROM candidates" in args_str:
                result.fetchone.return_value = MagicMock(_mapping={"entity_id": "12345678-1234-1234-1234-123456789012"})
            # SELECT evidence_id from candidates
            elif "SELECT evidence_id FROM candidates" in args_str:
                result.fetchone.return_value = MagicMock(_mapping={"evidence_id": "e1-2345-6789-abcd-ef0123456789"})
            # SELECT from evidences (validation)
            elif "SELECT 1 FROM evidences" in args_str or "FROM evidences e" in args_str:
                result.fetchone.return_value = MagicMock(_mapping={"content": "Test evidence content"})
            # INSERT INTO memory_evidences
            elif "INSERT INTO memory_evidences" in args_str:
                result.fetchone.return_value = None
            else:
                result.fetchone.return_value = None
            
            return result
        
        async def mock_execute(*args, **kwargs):
            sql_text = str(args)
            if args and hasattr(args[0], 'text'):
                sql_text = args[0].text
            execute_calls.append({'args': sql_text, 'kwargs': kwargs})
            return create_result(sql_text)
        
        # Create proper mock connection
        mock_conn = MagicMock()
        mock_conn.execute = mock_execute
        mock_conn.commit = AsyncMock()
        mock_conn.rollback = AsyncMock()
        
        # Create proper async context manager for engine.begin()
        class MockBeginCM:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    mock_conn.rollback()
                return False
        
        mock_engine = MagicMock()
        mock_engine.begin = Mock(return_value=MockBeginCM())
        
        # Patch the module
        import backend.shared.infrastructure.database.engine as engine_module
        monkeypatch.setattr(engine_module, 'get_engine', lambda: mock_engine)
        
        # Execute
        result = await service.approve_proposal(
            workspace_id=workspace_id,
            proposal_id=proposal_id,
        )
        
        # Verify
        assert result.status == ReflectionStatus.COMPLETED
        assert result.reflections_performed == 1
        assert result.metadata["new_node_id"] is not None
        assert "level" in result.metadata
        
        # Verify UPDATE had status='pending' condition
        update_calls = [c for c in execute_calls if "UPDATE proposals" in c['args']]
        assert len(update_calls) == 1
        assert "status = 'pending'" in update_calls[0]['args']
    
    @pytest.mark.asyncio
    async def test_idempotent_approved_proposal(self, service, monkeypatch):
        """Test 2: Already approved proposal returns early without side effects."""
        workspace_id = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
        proposal_id = UUID("06a81a90-fafd-7bc7-8000-fcb22cef6f1a")
        
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(_mapping={
            "id": str(proposal_id),
            "workspace_id": str(workspace_id),
            "status": "approved",  # Already approved
            "entity": "Test",
            "summary": "Test",
            "confidence": 0.5,
            "target_level": 1,
            "candidate_id": "a4c2719a-7364-45fc-97be-cb330696ea84",
            "evidence_chain": [],
        })
        mock_conn.execute.return_value = mock_result
        
        class MockBeginCM:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False
        
        mock_engine = MagicMock()
        mock_engine.begin = Mock(return_value=MockBeginCM())
        
        import backend.shared.infrastructure.database.engine as engine_module
        monkeypatch.setattr(engine_module, 'get_engine', lambda: mock_engine)
        
        result = await service.approve_proposal(
            workspace_id=workspace_id,
            proposal_id=proposal_id,
        )
        
        assert result.status == ReflectionStatus.COMPLETED
        assert result.reflections_performed == 0
        assert result.metadata["skipped"] == True
        assert result.metadata["reason"] == "already_approved"
        
        # No UPDATE should be called
        assert mock_conn.execute.call_count == 1  # Only SELECT
        for call in mock_conn.execute.call_args_list:
            assert "UPDATE" not in str(call)
    
    @pytest.mark.asyncio
    async def test_idempotent_rejected_proposal(self, service, monkeypatch):
        """Test 3: Rejected proposal returns early without side effects."""
        workspace_id = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
        proposal_id = UUID("06a81a9a-bb03-7ce6-8000-5e13fcf0e681")
        
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(_mapping={
            "id": str(proposal_id),
            "workspace_id": str(workspace_id),
            "status": "rejected",  # Already rejected
            "entity": "Test",
            "summary": "Test",
            "confidence": 0.5,
            "target_level": 1,
            "candidate_id": "a4c2719a-7364-45fc-97be-cb330696ea84",
            "evidence_chain": [],
        })
        mock_conn.execute.return_value = mock_result
        
        class MockBeginCM:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False
        
        mock_engine = MagicMock()
        mock_engine.begin = Mock(return_value=MockBeginCM())
        
        import backend.shared.infrastructure.database.engine as engine_module
        monkeypatch.setattr(engine_module, 'get_engine', lambda: mock_engine)
        
        result = await service.approve_proposal(
            workspace_id=workspace_id,
            proposal_id=proposal_id,
        )
        
        assert result.status == ReflectionStatus.COMPLETED
        assert result.reflections_performed == 0
        assert result.metadata["skipped"] == True
        assert result.metadata["reason"] == "already_rejected"
    
    @pytest.mark.asyncio
    async def test_proposal_not_found(self, service, monkeypatch):
        """Test 4: Non-existent proposal raises ValidationError."""
        workspace_id = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
        proposal_id = UUID("00000000-0000-0000-0000-000000000000")
        
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # Not found
        mock_conn.execute.return_value = mock_result
        
        class MockBeginCM:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False
        
        mock_engine = MagicMock()
        mock_engine.begin = Mock(return_value=MockBeginCM())
        
        import backend.shared.infrastructure.database.engine as engine_module
        monkeypatch.setattr(engine_module, 'get_engine', lambda: mock_engine)
        
        with pytest.raises(ValidationError) as exc_info:
            await service.approve_proposal(
                workspace_id=workspace_id,
                proposal_id=proposal_id,
            )
        
        assert str(proposal_id) in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_failure(self, service, monkeypatch):
        """Test 5: Transaction rollback on midway failure."""
        workspace_id = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
        proposal_id = UUID("06a81a90-fafd-7bc7-8000-fcb22cef6f1a")
        
        call_count = 0
        
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            result = MagicMock()
            args_str = str(args)
            
            if "SELECT * FROM proposals" in args_str:
                result.fetchone.return_value = MagicMock(_mapping={
                    "id": str(proposal_id),
                    "workspace_id": str(workspace_id),
                    "status": "pending",
                    "entity": "Test",
                    "summary": "Test",
                    "confidence": 0.5,
                    "target_level": 1,
                    "candidate_id": "a4c2719a-7364-45fc-97be-cb330696ea84",
                    "evidence_chain": [],
                })
            elif "UPDATE proposals" in args_str:
                result.fetchone.return_value = MagicMock(_mapping={"status": "approved"})
            elif "SELECT status FROM proposals" in args_str:
                if call_count == 3:
                    raise Exception("Simulated failure during verification")
                result.fetchone.return_value = MagicMock(_mapping={"status": "approved"})
            else:
                result.fetchone.return_value = None
            
            return result
        
        mock_conn = MagicMock()
        mock_conn.execute = mock_execute
        mock_conn.rollback = AsyncMock()
        
        class MockBeginCM:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    mock_conn.rollback()
                return False
        
        mock_engine = MagicMock()
        mock_engine.begin = Mock(return_value=MockBeginCM())
        
        import backend.shared.infrastructure.database.engine as engine_module
        monkeypatch.setattr(engine_module, 'get_engine', lambda: mock_engine)
        
        with pytest.raises(Exception):
            await service.approve_proposal(
                workspace_id=workspace_id,
                proposal_id=proposal_id,
            )
        
        # Verify rollback was called
        mock_conn.rollback.assert_called_once()
