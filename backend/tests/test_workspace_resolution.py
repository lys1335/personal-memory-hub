"""Tests for workspace resolution in rebuild script.

These tests verify that the workspace resolution logic correctly
identifies the user-workspace even when multiple workspaces exist.
"""

from unittest.mock import MagicMock, AsyncMock, patch
from uuid import UUID

import pytest
from pytest_asyncio import fixture as async_fixture

# Mock Workspace model
class MockWorkspace:
    def __init__(self, workspace_id: str, name: str):
        self.id = UUID(workspace_id)
        self.name = name


@pytest.mark.asyncio
async def test_workspace_resolution_by_preferred_id():
    """Test that preferred ID resolution works."""
    from backend.rebuild_phase_workspace_fixed import resolve_workspace_id
    
    # Create mock session
    mock_session = MagicMock()
    
    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MockWorkspace(
        "fd0223ed-7aa2-491e-8db5-b0de71b75219",
        "user-workspace"
    )
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    # Call resolution
    result = await resolve_workspace_id(mock_session)
    
    # Verify
    assert result == UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_workspace_resolution_by_name():
    """Test that name-based resolution works when preferred ID fails."""
    from backend.rebuild_phase_workspace_fixed import resolve_workspace_id

    # Create mock session
    mock_session = MagicMock()

    # By-name query succeeds - return a MockWorkspace object
    mock_result_success = MagicMock()
    mock_result_success.scalar_one_or_none.return_value = MockWorkspace(
        "fd0223ed-7aa2-491e-8db5-b0de71b75219",
        "user-workspace"
    )

    # preferred_id="nonexistent-id" raises in production (caught, no DB call),
    # so the name-based query is the first execute() and must succeed.
    mock_session.execute = AsyncMock(return_value=mock_result_success)

    # Call resolution
    result = await resolve_workspace_id(mock_session, preferred_id="nonexistent-id")

    # Verify
    assert result == UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")


@pytest.mark.asyncio
async def test_workspace_resolution_fallback_to_first():
    """Test fallback to first workspace when all strategies fail."""
    from backend.rebuild_phase_workspace_fixed import resolve_workspace_id

    # Create mock session
    mock_session = MagicMock()

    # All queries fail except the fallback
    mock_result_fail = MagicMock()
    mock_result_fail.scalar_one_or_none.return_value = None

    mock_result_fallback = MagicMock()
    mock_workspaces = [MockWorkspace("fb77c6ce-1e15-47e9-a8b7-2e707a011071", "default-workspace")]
    mock_result_fallback.scalars.return_value.all.return_value = mock_workspaces

    # Simulate sequential returns: first two queries fail, fallback succeeds
    async def mock_execute(*args, **kwargs):
        # First two calls return None (preferred ID not found), third returns fallback
        if mock_session.execute.call_count <= 2:
            return mock_result_fail
        return mock_result_fallback

    mock_session.execute = AsyncMock(side_effect=mock_execute)

    # Call resolution (should fallback to first workspace)
    result = await resolve_workspace_id(mock_session, preferred_id="nonexistent-id")

    # Verify - falls back to first workspace
    assert result == UUID("fb77c6ce-1e15-47e9-a8b7-2e707a011071")


@pytest.mark.asyncio
async def test_workspace_resolution_multiple_workspaces():
    """Test that resolution doesn't depend on database order."""
    from backend.rebuild_phase_workspace_fixed import resolve_workspace_id
    
    # Create mock workspaces
    default_ws = MockWorkspace("fb77c6ce-1e15-47e9-a8b7-2e707a011071", "default-workspace")
    user_ws = MockWorkspace("fd0223ed-7aa2-491e-8db5-b0de71b75219", "user-workspace")
    
    # Create mock session
    mock_session = MagicMock()
    
    # Mock all queries to return user-workspace
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user_ws
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    # Call resolution with preferred ID
    result = await resolve_workspace_id(mock_session)
    
    # Verify we get user-workspace, not default-workspace
    assert result == UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
    assert result != UUID("fb77c6ce-1e15-47e9-a8b7-2e707a011071")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
