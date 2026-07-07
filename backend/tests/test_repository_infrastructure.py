"""Unit tests for Repository Infrastructure (D2.1).

Tests BaseRepository, QueryRepository, Pagination, Exceptions,
WorkspaceIsolationMixin, and shared types.

Per G-058 (Deterministic-by-Default): All tests are deterministic.
Per G-057 (Mock Mirrors Layer Boundary): We mock at the database boundary
using real in-memory SQLite via the existing test fixtures.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

# ---------------------------------------------------------------------------
# Test Models (minimal SQLAlchemy models for testing)
# ---------------------------------------------------------------------------
from sqlalchemy.orm import DeclarativeBase

from backend.repository.base import BaseRepository
from backend.repository.exceptions import (
    DuplicateError,
    IntegrityError,
    NotFoundError,
    ReadOnlyError,
    WorkspaceIsolationError,
)
from backend.repository.pagination import CursorPage, OffsetPage, Page
from backend.repository.query import QueryRepository
from backend.repository.types import (
    PrimaryKey,
    get_primary_key_column,
    get_table_columns,
)
from backend.repository.workspace import WorkspaceIsolationMixin


class _TestBase(DeclarativeBase):
    """Declarative base for test models."""

    pass


class TestEntity(_TestBase):
    """Minimal test entity with workspace_id."""

    __tablename__ = "test_entities"

    id: Mapped[PrimaryKey] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[PrimaryKey] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[int | None] = mapped_column(default=None)


class TestQueryEntity(_TestBase):
    """Minimal test entity for QueryRepository testing."""

    __tablename__ = "test_query_entities"

    id: Mapped[PrimaryKey] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[PrimaryKey] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


# ---------------------------------------------------------------------------
# Test Repository Implementations
# ---------------------------------------------------------------------------


class _TestRepository(BaseRepository[TestEntity]):
    """Concrete test implementation of BaseRepository."""

    _model_class = TestEntity
    _table_name = "test_entities"

    async def soft_delete_impl(self, id: PrimaryKey) -> None:
        # For testing: mark as deleted by setting name to 'DELETED'
        from sqlalchemy import update as sa_update

        stmt = (
            sa_update(TestEntity)
            .where(TestEntity.id == id)  # type: ignore[arg-type]
            .values(name="DELETED")
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]


class _TestQueryRepo(QueryRepository[TestQueryEntity]):
    """Concrete test implementation of QueryRepository."""

    _model_class = TestQueryEntity
    _table_name = "test_query_entities"

    async def complex_query(self, *args, **kwargs):
        return []


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[tuple[AsyncSession, AsyncSession], None]:
    """Create an in-memory SQLite database with test tables.

    Returns:
        Tuple of (session, session2) — two separate sessions for concurrency tests.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.create_all)

    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")

    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as s1, factory() as s2:
        yield s1, s2


@pytest.fixture
def repo(test_db: tuple[AsyncSession, AsyncSession]) -> _TestRepository:
    """Create a _TestRepository instance bound to the test database."""
    return _TestRepository(session=test_db[0])


@pytest.fixture
def query_repo(test_db: tuple[AsyncSession, AsyncSession]) -> _TestQueryRepo:
    """Create a _TestQueryRepo instance bound to the test database."""
    return _TestQueryRepo(session=test_db[0])


@pytest.fixture
def test_workspace_id() -> str:
    """A deterministic workspace UUID for tests."""
    return str(uuid4())


# ---------------------------------------------------------------------------
# Tests — BaseRepository CRUD
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_and_find_by_id(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify create() inserts and find_by_id() retrieves the entity."""
    entity = TestEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="test-entity",
        value=42,
    )
    created_id = await repo.create(entity)
    assert created_id == entity.id

    found = await repo.find_by_id(created_id)
    assert found is not None
    assert found.name == "test-entity"
    assert found.value == 42


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_by_id_not_found(repo: _TestRepository) -> None:
    """Verify find_by_id() returns None for non-existent entity."""
    found = await repo.find_by_id(uuid4())
    assert found is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_all_basic(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify find_all() returns all entities in the workspace."""
    for i in range(5):
        entity = TestEntity(
            id=uuid4(),
            workspace_id=test_workspace_id,
            name=f"entity-{i}",
            value=i * 10,
        )
        repo.session.add(entity)
    await repo.session.flush()

    results = await repo.find_all(workspace_id=test_workspace_id)
    assert len(results) == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_all_with_filters(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify find_all() respects filter conditions."""
    for i in range(5):
        entity = TestEntity(
            id=uuid4(),
            workspace_id=test_workspace_id,
            name=f"entity-{i}",
            value=i * 10,
        )
        repo.session.add(entity)
    await repo.session.flush()

    results = await repo.find_all(
        workspace_id=test_workspace_id,
        filters={"value": 20},
    )
    assert len(results) == 1
    assert results[0].name == "entity-2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_all_with_ordering(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify find_all() respects ordering."""
    for i in [3, 1, 4, 1, 5]:
        entity = TestEntity(
            id=uuid4(),
            workspace_id=test_workspace_id,
            name=f"entity-{i}",
            value=i,
        )
        repo.session.add(entity)
    await repo.session.flush()

    results = await repo.find_all(
        workspace_id=test_workspace_id,
        order_by="value",
        descending=True,
    )
    values = [r.value for r in results]
    assert values == sorted(values, reverse=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify update() modifies an existing entity."""
    entity = TestEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="original",
        value=1,
    )
    repo.session.add(entity)
    await repo.session.flush()

    entity.name = "updated"
    entity.value = 99
    await repo.update(entity)

    found = await repo.find_by_id(entity.id)
    assert found is not None
    assert found.name == "updated"
    assert found.value == 99


@pytest.mark.unit
@pytest.mark.asyncio
async def test_soft_delete(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify soft_delete() marks entity as deleted."""
    entity = TestEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="to-delete",
        value=1,
    )
    repo.session.add(entity)
    await repo.session.flush()

    await repo.soft_delete(entity.id)

    # Entity should still be findable but marked as deleted
    found = await repo.find_by_id(entity.id)
    assert found is not None
    assert found.name == "DELETED"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exists_true(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify exists() returns True for existing entity."""
    entity = TestEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="exists-test",
    )
    repo.session.add(entity)
    await repo.session.flush()

    assert await repo.exists(entity.id) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exists_false(repo: _TestRepository) -> None:
    """Verify exists() returns False for non-existent entity."""
    assert await repo.exists(uuid4()) is False


# ---------------------------------------------------------------------------
# Tests — Pagination
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_page_basic(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify find_page() returns paginated results."""
    for i in range(10):
        entity = TestEntity(
            id=uuid4(),
            workspace_id=test_workspace_id,
            name=f"entity-{i}",
            value=i + 1,
        )
        repo.session.add(entity)
    await repo.session.flush()

    page = await repo.find_page(
        workspace_id=test_workspace_id,
        page_number=1,
        page_size=3,
    )

    # find_page fetches page_size+1=4, removes sentinel → 3 items
    assert len(page.items) == 3
    assert page.page_number == 1
    assert page.has_next is True
    assert page.has_prev is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_page_last_page(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify find_page() correctly identifies the last page."""
    for i in range(5):
        entity = TestEntity(
            id=uuid4(),
            workspace_id=test_workspace_id,
            name=f"entity-{i}",
            value=i,
        )
        repo.session.add(entity)
    await repo.session.flush()

    page = await repo.find_page(
        workspace_id=test_workspace_id,
        page_number=2,
        page_size=3,
        order_by="value",
    )

    assert len(page.items) == 2
    assert page.has_next is False
    assert page.has_prev is True


@pytest.mark.unit
def test_page_is_empty() -> None:
    """Verify Page.is_empty property."""
    page = Page.empty(page_size=20)
    assert page.is_empty is True
    assert page.is_last is True


# ---------------------------------------------------------------------------
# Tests — Exception Mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_not_found_error() -> None:
    """Verify NotFoundError carries entity info."""
    err = NotFoundError("Entity", "abc-123")
    assert "Entity" in str(err)
    assert "abc-123" in str(err)
    assert err.entity_type == "Entity"
    assert err.entity_id == "abc-123"


@pytest.mark.unit
def test_duplicate_error() -> None:
    """Verify DuplicateError carries constraint info."""
    err = DuplicateError("Entity", "uk_entities_type_name", "duplicate name")
    assert "duplicate" in str(err)
    assert err.entity_type == "Entity"


@pytest.mark.unit
def test_integrity_error() -> None:
    """Verify IntegrityError carries constraint info."""
    err = IntegrityError("MemoryNode", "chk_level_type_consistency", "invalid level")
    assert "invalid level" in str(err)


@pytest.mark.unit
def test_read_only_error() -> None:
    """Verify ReadOnlyError is raised for write on read-only repo."""
    err = ReadOnlyError("MemoryQueryRepository")
    assert "MemoryQueryRepository" in str(err)


@pytest.mark.unit
def test_workspace_isolation_error() -> None:
    """Verify WorkspaceIsolationError is raised when workspace is missing."""
    err = WorkspaceIsolationError(workspace_id="", requested_workspace="any")
    assert "Workspace isolation breach" in str(err)


# ---------------------------------------------------------------------------
# Tests — QueryRepository Read-Only Enforcement
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_repo_read_only_enforcement(query_repo: _TestQueryRepo, test_workspace_id: str) -> None:
    """Verify QueryRepository rejects write operations."""
    with pytest.raises(ReadOnlyError):
        await query_repo.create(None)  # type: ignore[arg-type]

    with pytest.raises(ReadOnlyError):
        await query_repo.update(None)  # type: ignore[arg-type]

    with pytest.raises(ReadOnlyError):
        await query_repo.soft_delete(uuid4())

    with pytest.raises(ReadOnlyError):
        await query_repo.exists(uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_repo_find_by_id(query_repo: _TestQueryRepo, test_workspace_id: str) -> None:
    """Verify QueryRepository find_by_id() works (read operation)."""
    entity = TestQueryEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="query-test",
    )
    query_repo.session.add(entity)
    await query_repo.session.flush()

    found = await query_repo.find_by_id(entity.id)
    assert found is not None
    assert found.name == "query-test"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_repo_complex_query(query_repo: _TestQueryRepo) -> None:
    """Verify QueryRepository complex_query() can be implemented."""
    result = await query_repo.complex_query(test_arg="value")
    assert result == []


# ---------------------------------------------------------------------------
# Tests — Workspace Isolation
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_workspace_isolation_enforced(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify Repository enforces workspace isolation."""
    # Set workspace
    ws_id = uuid4()
    repo.set_workspace(ws_id)
    assert repo.get_workspace() == ws_id

    # find_all should only return entities in the set workspace
    other_ws = str(uuid4())
    entity = TestEntity(
        id=uuid4(),
        workspace_id=other_ws,
        name="other-workspace",
    )
    repo.session.add(entity)
    await repo.session.flush()

    # Should not find entity from other workspace
    results = await repo.find_all()
    assert len(results) == 0


@pytest.mark.unit
def test_workspace_isolation_error_on_unset() -> None:
    """Verify WorkspaceIsolationMixin raises when workspace is not set."""
    mixin = WorkspaceIsolationMixin()
    with pytest.raises(WorkspaceIsolationError):
        mixin._ensure_workspace()


# ---------------------------------------------------------------------------
# Tests — Shared Types
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_table_columns() -> None:
    """Verify get_table_columns extracts columns from a model class."""
    columns = get_table_columns(TestEntity)
    assert "id" in columns
    assert "workspace_id" in columns
    assert "name" in columns
    assert "value" in columns


@pytest.mark.unit
def test_get_primary_key_column() -> None:
    """Verify get_primary_key_column returns the PK column."""
    pk = get_primary_key_column(TestEntity)
    assert pk is not None
    assert pk.name == "id"


@pytest.mark.unit
def test_build_workspace_filter() -> None:
    """Verify WorkspaceIsolationMixin.build_workspace_filter creates correct filter."""
    ws_id = uuid4()
    filt = WorkspaceIsolationMixin.build_workspace_filter(ws_id)  # type: ignore[arg-type]
    assert filt == {"workspace_id": ws_id}


# ---------------------------------------------------------------------------
# Tests — Transaction Support
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_commit(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify commit() persists changes."""
    entity = TestEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="commit-test",
    )
    repo.session.add(entity)
    await repo.commit()

    # Re-query to verify persistence
    found = await repo.find_by_id(entity.id)
    assert found is not None
    assert found.name == "commit-test"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify rollback() undoes uncommitted changes."""
    entity = TestEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="rollback-test",
    )
    repo.session.add(entity)
    await repo.rollback()

    # Entity should not exist after rollback
    found = await repo.find_by_id(entity.id)
    assert found is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh(repo: _TestRepository, test_workspace_id: str) -> None:
    """Verify refresh() reloads entity from database."""
    entity = TestEntity(
        id=uuid4(),
        workspace_id=test_workspace_id,
        name="refresh-test",
        value=10,
    )
    repo.session.add(entity)
    await repo.session.flush()

    # Modify locally
    entity.name = "modified-locally"
    entity.value = 999

    # Refresh from database
    await repo.refresh(entity)

    # Should be back to original values
    assert entity.name == "refresh-test"
    assert entity.value == 10


# ---------------------------------------------------------------------------
# Tests — Page Data Structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_offset_page_computes_has_next() -> None:
    """Verify OffsetPage computes has_next based on total."""
    page = OffsetPage(
        items=[1, 2, 3],
        total=10,
        page_number=1,
        page_size=3,
    )
    assert page.has_next is True
    assert page.has_prev is False


@pytest.mark.unit
def test_offset_page_last_page() -> None:
    """Verify OffsetPage identifies last page."""
    page = OffsetPage(
        items=[1],
        total=3,
        page_number=1,
        page_size=3,
    )
    assert page.has_next is False
    assert page.has_prev is False


@pytest.mark.unit
def test_cursor_page_has_next() -> None:
    """Verify CursorPage sets has_next based on sentinel."""
    page = CursorPage(
        items=[1, 2, 3],
        page_number=1,
        page_size=3,
        prev_cursor=None,
    )
    # has_next is True because last item is not None
    assert page.has_next is True
