"""Unit tests for Reflection Service - Entity Boundary Fix.

Tests verify:
1. Entity-level Reflection isolation
2. Workspace-level isolation
3. Unresolved candidate handling
4. Batch boundary correctness
5. No data mutation during scope acquisition
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from backend.shared.infrastructure.uuid import generate_uuid
from backend.service.reflection_service import ReflectionService

# Patch path for get_engine (imported locally inside methods)
GET_ENGINE_PATH = "backend.shared.infrastructure.database.engine.get_engine"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    """Create ReflectionService with minimal mocked dependencies."""
    mock_candidate_repo = MagicMock()
    mock_memory_node_repo = MagicMock()
    mock_relationship_repo = MagicMock()
    return ReflectionService(
        memory_node_repo=mock_memory_node_repo,
        candidate_repo=mock_candidate_repo,
        relationship_repo=mock_relationship_repo,
    )


def _make_mock_conn(rows=None):
    """Helper to create a mock async context manager for DB connection."""
    rows = rows or []
    mock_conn = MagicMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    async def mock_execute(sql, params=None):
        mock_result = MagicMock()
        mock_result.fetchall = lambda: rows
        return mock_result

    mock_conn.execute = AsyncMock(side_effect=mock_execute)
    return mock_conn


def _make_mock_engine(conn):
    """Helper to create a mock engine with begin() context manager."""
    mock_engine = MagicMock()
    mock_engine.begin = MagicMock(return_value=conn)
    return mock_engine


def _make_candidate_row(candidate_id, entity_id, content="test"):
    """Create a mock DB row for a candidate."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: [
        candidate_id,      # 0: id
        entity_id,          # 1: entity_id
        None,               # 2: area_id
        content,            # 3: content
        "pattern",          # 4: candidate_type
        "observation",      # 5: evidence_source
        candidate_id,       # 6: evidence_id
        "[]",               # 7: evidence_chain
        1,                  # 8: evidence_count
        0.9,                # 9: evidence_strength
        "candidate",        # 10: status
        1,                  # 11: source_level
    ][i]
    row.__len__ = lambda self: 12
    return row


# ---------------------------------------------------------------------------
# Test 1: Entity Isolation
# ---------------------------------------------------------------------------

class TestEntityIsolation:
    """Verify that reflect_by_entity() only processes candidates for the specified entity."""

    @pytest.mark.asyncio
    async def test_entity_scope_queries_candidates_not_memory_nodes(self, service):
        """Entity scope must query candidates table with entity_id filter."""
        workspace_id = generate_uuid()
        entity_a = generate_uuid()

        row = _make_candidate_row(str(generate_uuid()), str(entity_a))
        conn = _make_mock_conn([row])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock) as mock_pipeline:
                mock_pipeline.return_value = {"facts": [], "entities": [], "proposals": [],
                                              "execution_log": [], "evolved_candidates": []}
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_by_entity(
                            workspace_id=workspace_id,
                            entity_id=entity_a,
                        )

        # Verify query was called with entity_id filter
        call_args = conn.execute.call_args
        sql = str(call_args[0][0])
        params = call_args[1] if len(call_args) > 1 and call_args[1] else {}
        # For SQLAlchemy text(), params may be in positional args
        if not params and len(call_args[0]) > 1:
            params = call_args[0][1] or {}
        assert "entity_id" in sql, "Entity scope query must include entity_id"
        assert str(entity_a) in str(params) or str(entity_a) in sql, \
            "Query must filter by specified entity_id"

    @pytest.mark.asyncio
    async def test_entity_scope_excludes_other_entities(self, service):
        """Candidates from other entities must not be included."""
        workspace_id = generate_uuid()
        entity_a = generate_uuid()
        entity_b = generate_uuid()

        # Only entity_a's candidate is returned
        row_a = _make_candidate_row(str(generate_uuid()), str(entity_a), "Content A")
        conn = _make_mock_conn([row_a])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock) as mock_pipeline:
                mock_pipeline.return_value = {"facts": [], "entities": [], "proposals": [],
                                              "execution_log": [], "evolved_candidates": []}
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_by_entity(
                            workspace_id=workspace_id,
                            entity_id=entity_a,
                        )

        called_candidates = mock_pipeline.call_args[0][1]
        for cand in called_candidates:
            assert cand.get("entity_id") == str(entity_a), \
                f"All candidates must belong to entity_a"


# ---------------------------------------------------------------------------
# Test 2: Workspace Isolation
# ---------------------------------------------------------------------------

class TestWorkspaceIsolation:
    """Verify that Reflection is isolated by workspace_id."""

    @pytest.mark.asyncio
    async def test_workspace_filter_in_query(self, service):
        """Query must include workspace_id filter."""
        workspace_id = generate_uuid()
        entity_id = generate_uuid()

        conn = _make_mock_conn([])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock):
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_by_entity(
                            workspace_id=workspace_id,
                            entity_id=entity_id,
                        )

        params = conn.execute.call_args[1] if len(conn.execute.call_args) > 1 else {}
        if not params and len(conn.execute.call_args[0]) > 1:
            params = conn.execute.call_args[0][1] or {}
        assert params.get("workspace_id") == str(workspace_id) or \
               str(workspace_id) in str(conn.execute.call_args), \
            "Query must filter by workspace_id"


# ---------------------------------------------------------------------------
# Test 3: Unresolved Inclusion
# ---------------------------------------------------------------------------

class TestUnresolvedInclusion:
    """Verify that unresolved candidates (entity_id=NULL) are included."""

    @pytest.mark.asyncio
    async def test_unresolved_scope_queries_null_entity(self, service):
        """Unresolved scope must query candidates with NULL entity_id."""
        workspace_id = generate_uuid()

        # Create row with None entity_id
        row = _make_candidate_row(str(generate_uuid()), None, "Unresolved content")
        conn = _make_mock_conn([row])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock) as mock_pipeline:
                mock_pipeline.return_value = {"facts": [], "entities": [], "proposals": [],
                                              "execution_log": [], "evolved_candidates": []}
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_unresolved(
                            workspace_id=workspace_id,
                        )

        sql = str(conn.execute.call_args[0][0])
        assert "IS NULL" in sql, "Unresolved scope must use entity_id IS NULL condition"

    @pytest.mark.asyncio
    async def test_unresolved_candidates_included_in_results(self, service):
        """Unresolved candidates must appear in the candidates list."""
        workspace_id = generate_uuid()
        cand_id = str(generate_uuid())

        row = _make_candidate_row(cand_id, None, "Test unresolved")
        conn = _make_mock_conn([row])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock) as mock_pipeline:
                mock_pipeline.return_value = {"facts": [], "entities": [], "proposals": [],
                                              "execution_log": [], "evolved_candidates": []}
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_unresolved(
                            workspace_id=workspace_id,
                        )

        called_candidates = mock_pipeline.call_args[0][1]
        assert len(called_candidates) > 0, "Unresolved candidates must be passed to pipeline"
        for cand in called_candidates:
            assert cand.get("entity_id") is None, \
                f"Unresolved candidate must have entity_id=None, got {cand.get('entity_id')}"


# ---------------------------------------------------------------------------
# Test 4: Resolved Exclusion from Unresolved
# ---------------------------------------------------------------------------

class TestResolvedExclusion:
    """Verify that resolved candidates are NOT included in unresolved scope."""

    @pytest.mark.asyncio
    async def test_resolved_candidates_excluded_from_unresolved(self, service):
        """Candidates with entity_id set must not appear in unresolved scope."""
        workspace_id = generate_uuid()
        entity_a = generate_uuid()

        # Create a resolved candidate (entity_id is set)
        row = _make_candidate_row(str(generate_uuid()), str(entity_a), "Resolved content")
        conn = _make_mock_conn([row])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock) as mock_pipeline:
                mock_pipeline.return_value = {"facts": [], "entities": [], "proposals": [],
                                              "execution_log": [], "evolved_candidates": []}
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_unresolved(
                            workspace_id=workspace_id,
                        )

        # The query should use entity_id IS NULL, which excludes resolved candidates
        sql = str(conn.execute.call_args[0][0])
        assert "IS NULL" in sql, "Unresolved scope must filter entity_id IS NULL"

        # Pipeline should receive empty list since all candidates have entity_id set
        mock_pipeline.assert_called_once()
        called_candidates = mock_pipeline.call_args[0][1]
        # If any candidates were returned, they must have entity_id=None
        for cand in called_candidates:
            assert cand.get("entity_id") is None, \
                "Resolved candidates should not appear in unresolved scope"


# ---------------------------------------------------------------------------
# Test 5: Batch Entity Isolation
# ---------------------------------------------------------------------------

class TestBatchIsolation:
    """Verify that all batches for an entity belong to the same entity."""

    @pytest.mark.asyncio
    async def test_all_batches_same_entity(self, service):
        """When processing Entity A with >10 candidates, all batches must be Entity A."""
        workspace_id = generate_uuid()
        entity_a = generate_uuid()

        # Create 15 mock candidates for entity_a (exceeds BATCH_SIZE=10)
        rows = []
        for i in range(15):
            rows.append(_make_candidate_row(str(generate_uuid()), str(entity_a), f"Content {i}"))

        conn = _make_mock_conn(rows)
        engine = _make_mock_engine(conn)

        batch_calls = []

        async def capture_pipeline(scope, candidates, wid):
            batch_calls.append({
                "scope": scope,
                "count": len(candidates),
                "entities": set(c.get("entity_id") for c in candidates),
            })
            return {"facts": [], "entities": [], "proposals": [],
                    "execution_log": [], "evolved_candidates": []}

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", side_effect=capture_pipeline):
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_by_entity(
                            workspace_id=workspace_id,
                            entity_id=entity_a,
                        )

        # All batches must contain only entity_a candidates
        for batch_info in batch_calls:
            assert batch_info["entities"] == {str(entity_a)}, \
                f"Batch must contain only entity_a candidates, got {batch_info['entities']}"
            # Note: With 15 candidates and BATCH_SIZE=10, we get 2 batches (10+5)
            assert batch_info["count"] > 0, "Each batch should have candidates"


# ---------------------------------------------------------------------------
# Test 6: Existing Behavior Regression
# ---------------------------------------------------------------------------

class TestRegression:
    """Verify existing behavior is not broken."""

    @pytest.mark.asyncio
    async def test_daily_scope_still_works(self, service):
        """daily scope should still query candidates table without entity filter."""
        workspace_id = generate_uuid()

        row = _make_candidate_row(str(generate_uuid()), str(generate_uuid()))
        conn = _make_mock_conn([row])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock) as mock_pipeline:
                mock_pipeline.return_value = {"facts": [], "entities": [], "proposals": [],
                                              "execution_log": [], "evolved_candidates": []}
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect(
                            workspace_id=workspace_id,
                            scope="daily",
                        )

        # Verify query was made (no exception)
        # Note: reflect() may make multiple queries (scope + entity), so use assert_called()
        assert conn.execute.called

    @pytest.mark.asyncio
    async def test_ordering_preserved(self, service):
        """Results must be ordered by created_at ASC."""
        workspace_id = generate_uuid()
        entity_id = generate_uuid()

        conn = _make_mock_conn([])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock):
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_by_entity(
                            workspace_id=workspace_id,
                            entity_id=entity_id,
                        )

        sql = str(conn.execute.call_args[0][0])
        assert "ORDER BY" in sql and "created_at" in sql, \
            "Query must preserve ORDER BY created_at ASC"


# ---------------------------------------------------------------------------
# Test 7: No Data Mutation
# ---------------------------------------------------------------------------

class TestDataIntegrity:
    """Verify _acquire_scope does not mutate any data."""

    @pytest.mark.asyncio
    async def test_scope_acquisition_is_read_only(self, service):
        """_acquire_scope must only read, never write."""
        workspace_id = generate_uuid()
        entity_id = generate_uuid()

        conn = _make_mock_conn([])
        engine = _make_mock_engine(conn)

        with patch(GET_ENGINE_PATH, return_value=engine):
            with patch.object(service, "_run_engine_pipeline", new_callable=AsyncMock):
                with patch.object(service, "_save_proposals", new_callable=AsyncMock):
                    with patch.object(service, "_auto_approve_pending_proposals", new_callable=AsyncMock):
                        await service.reflect_by_entity(
                            workspace_id=workspace_id,
                            entity_id=entity_id,
                        )

        # Verify no WRITE operations were performed
        for call in conn.execute.call_args_list:
            sql = str(call[0][0]).upper()
            assert "INSERT" not in sql, "Scope acquisition must not INSERT"
            assert "UPDATE" not in sql, "Scope acquisition must not UPDATE"
            assert "DELETE" not in sql, "Scope acquisition must not DELETE"
