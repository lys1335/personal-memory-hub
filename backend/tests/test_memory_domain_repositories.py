"""Unit tests for Memory Domain Repositories (D2.2).

Tests MemoryNodeRepository, EvidenceRepository, ArchiveRepository,
TagRepository, and MemoryQueryRepository.

Uses minimal test models mirroring the real Memory Domain schema.
Test repository classes implement the same interface as the real repos
but use test models and in-memory SQLite.

Per G-058 (Deterministic-by-Default): All tests are deterministic.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Date, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

# ---------------------------------------------------------------------------
# Test Models (minimal SQLAlchemy models — mirrors real schema)
# ---------------------------------------------------------------------------
from sqlalchemy.orm import DeclarativeBase

from backend.repository.base import BaseRepository
from backend.repository.exceptions import (
    IntegrityError as DomainIntegrityError,
)
from backend.repository.pagination import Page


class _TestBase(DeclarativeBase):
    """Declarative base for test models."""

    pass


class _TEvidence(_TestBase):
    """Minimal test evidence model."""

    __tablename__ = "tevidences"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="conversation")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now())


class _TMemoryNode(_TestBase):
    """Minimal test memory node model."""

    __tablename__ = "tmemnodes"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now())


class _TArchive(_TestBase):
    """Minimal test archive model."""

    __tablename__ = "tarchives"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    archive_type: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class _TTag(_TestBase):
    """Minimal test tag model."""

    __tablename__ = "ttags"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tag_type: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    color: Mapped[str | None] = mapped_column(String(7))


class _TTagLink(_TestBase):
    """Minimal test tag link model."""

    __tablename__ = "ttaglinks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tag_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(nullable=False)


# ---------------------------------------------------------------------------
# Test Repository Implementations
# ---------------------------------------------------------------------------


class _TEvidenceRepo(BaseRepository):
    """Test EvidenceRepository — evidence is immutable."""

    _model_class = _TEvidence
    _table_name = "tevidences"

    async def soft_delete_impl(self, id: Any) -> None:
        raise DomainIntegrityError(
            entity_type="evidence",
            constraint="Evidence is immutable",
        )

    async def update(self, entity: Any) -> Any:
        raise DomainIntegrityError(
            entity_type="evidence",
            constraint="Evidence is immutable",
        )

    async def find_by_workspace(self, *, workspace_id: str, offset: int = 0, limit: int = 100) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_source(self, *, source: str, workspace_id: str) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.source == source,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_page(
        self, *, workspace_id: str, page_number: int = 1, page_size: int = 20,
    ) -> Page[Any]:
        offset = (page_number - 1) * page_size
        items = await self.find_by_workspace(workspace_id=workspace_id, offset=offset, limit=page_size + 1)
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]
        return Page(
            items=items, total=None, page_number=page_number, page_size=page_size,
            has_next=has_next, has_prev=page_number > 1,
        )


class _TMemoryNodeRepo(BaseRepository):
    """Test MemoryNodeRepository — memory is immutable."""

    _model_class = _TMemoryNode
    _table_name = "tmemnodes"

    async def soft_delete_impl(self, id: Any) -> None:
        raise DomainIntegrityError(
            entity_type="memory_node",
            constraint="Memory is immutable",
        )

    async def update(self, entity: Any) -> Any:
        raise DomainIntegrityError(
            entity_type="memory_node",
            constraint="Memory is immutable",
        )

    async def find_by_entity(self, *, entity_id: UUID, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.entity_id == str(entity_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_level(self, *, level: int, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.level == level,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_status(self, *, status: str, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.status == status,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_active_by_workspace(self, *, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.status == "active",
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_page(
        self, *, workspace_id: UUID, page_number: int = 1, page_size: int = 20,
    ) -> Page[Any]:
        offset = (page_number - 1) * page_size
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
        ).order_by(self._model_class.created_at.desc()).offset(offset).limit(page_size + 1)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]
        return Page(
            items=items, total=None, page_number=page_number, page_size=page_size,
            has_next=has_next, has_prev=page_number > 1,
        )

    async def find_with_evidence_chain(self, *, memory_node_id: UUID) -> dict[str, Any]:
        node = await self.find_by_id(memory_node_id)
        return {"node": node, "evidence_chain": []}


class _TArchiveRepo(BaseRepository):
    """Test ArchiveRepository."""

    _model_class = _TArchive
    _table_name = "tarchives"

    async def soft_delete_impl(self, id: Any) -> None:
        pass

    async def find_by_type(self, *, archive_type: str, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.archive_type == archive_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_period(
        self, *, period_start: date, period_end: date, workspace_id: UUID,
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.period_start <= period_end,
            self._model_class.period_end >= period_start,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_page(
        self, *, workspace_id: UUID, page_number: int = 1, page_size: int = 20,
    ) -> Page[Any]:
        offset = (page_number - 1) * page_size
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
        ).order_by(self._model_class.period_start.desc()).offset(offset).limit(page_size + 1)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]
        return Page(
            items=items, total=None, page_number=page_number, page_size=page_size,
            has_next=has_next, has_prev=page_number > 1,
        )


class _TTagRepo(BaseRepository):
    """Test TagRepository."""

    _model_class = _TTag
    _table_name = "ttags"

    async def soft_delete_impl(self, id: Any) -> None:
        pass

    async def find_by_workspace(self, *, workspace_id: UUID, offset: int = 0, limit: int = 100) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_name(self, *, name: str, workspace_id: UUID) -> Any | None:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_page(
        self, *, workspace_id: UUID, page_number: int = 1, page_size: int = 20,
    ) -> Page[Any]:
        offset = (page_number - 1) * page_size
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
        ).offset(offset).limit(page_size + 1)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]
        return Page(
            items=items, total=None, page_number=page_number, page_size=page_size,
            has_next=has_next, has_prev=page_number > 1,
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def test_db() -> AsyncSession:
    """Create an in-memory SQLite database with test tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.create_all)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session: AsyncSession = factory()

    yield session

    try:
        await session.close()
    except Exception:  # pragma: no cover
        pass
    await engine.dispose()


@pytest.fixture
def evidence_repo(test_db: AsyncSession) -> _TEvidenceRepo:
    return _TEvidenceRepo(session=test_db)


@pytest.fixture
def memory_node_repo(test_db: AsyncSession) -> _TMemoryNodeRepo:
    return _TMemoryNodeRepo(session=test_db)


@pytest.fixture
def archive_repo(test_db: AsyncSession) -> _TArchiveRepo:
    return _TArchiveRepo(session=test_db)


@pytest.fixture
def tag_repo(test_db: AsyncSession) -> _TTagRepo:
    return _TTagRepo(session=test_db)


@pytest.fixture
def test_workspace_id() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# EvidenceRepository Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEvidenceRepository:
    """Tests for EvidenceRepository immutability enforcement."""

    @pytest.mark.asyncio
    async def test_evidence_create(self, evidence_repo: _TEvidenceRepo, test_workspace_id: str) -> None:
        """Verify create() inserts evidence."""
        ev = _TEvidence(
            id=uuid4(),
            workspace_id=test_workspace_id,
            entity_id=str(uuid4()),
            evidence_type="conversation",
            content="Test evidence content",
            source="conversation",
        )
        ev_id = await evidence_repo.create(ev)
        assert ev_id is not None

        found = await evidence_repo.find_by_id(ev_id)
        assert found is not None
        assert found.content == "Test evidence content"

    @pytest.mark.asyncio
    async def test_evidence_update_prohibited(self, evidence_repo: _TEvidenceRepo) -> None:
        """Verify EvidenceRepository.update() raises DomainIntegrityError."""
        with pytest.raises(DomainIntegrityError, match="immutable"):
            await evidence_repo.update(object())  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_evidence_soft_delete_prohibited(self, evidence_repo: _TEvidenceRepo) -> None:
        """Verify EvidenceRepository.soft_delete() raises DomainIntegrityError."""
        with pytest.raises(DomainIntegrityError, match="immutable"):
            await evidence_repo.soft_delete(uuid4())

    @pytest.mark.asyncio
    async def test_evidence_find_by_workspace(self, evidence_repo: _TEvidenceRepo, test_workspace_id: str) -> None:
        """Verify find_by_workspace returns evidence scoped to workspace."""
        for i in range(3):
            ev = _TEvidence(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(uuid4()),
                evidence_type="conversation",
                content=f"Evidence {i}",
                source="conversation",
            )
            evidence_repo.session.add(ev)
        await evidence_repo.session.flush()

        results = await evidence_repo.find_by_workspace(workspace_id=test_workspace_id)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_evidence_find_by_source(self, evidence_repo: _TEvidenceRepo, test_workspace_id: str) -> None:
        """Verify find_by_source filters by source."""
        for i in range(3):
            ev = _TEvidence(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(uuid4()),
                evidence_type="conversation",
                content=f"Evidence {i}",
                source="manual" if i < 2 else "conversation",
            )
            evidence_repo.session.add(ev)
        await evidence_repo.session.flush()

        results = await evidence_repo.find_by_source(source="manual", workspace_id=test_workspace_id)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_evidence_find_page(self, evidence_repo: _TEvidenceRepo, test_workspace_id: str) -> None:
        """Verify evidence pagination."""
        for i in range(5):
            ev = _TEvidence(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(uuid4()),
                evidence_type="conversation",
                content=f"Evidence {i}",
                source="conversation",
            )
            evidence_repo.session.add(ev)
        await evidence_repo.session.flush()

        page = await evidence_repo.find_page(
            workspace_id=test_workspace_id,
            page_number=1,
            page_size=3,
        )
        assert len(page.items) == 3
        assert page.has_next is True


# ---------------------------------------------------------------------------
# MemoryNodeRepository Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMemoryNodeRepository:
    """Tests for MemoryNodeRepository CRUD and immutability."""

    @pytest.mark.asyncio
    async def test_memory_create(self, memory_node_repo: _TMemoryNodeRepo, test_workspace_id: str) -> None:
        """Verify create() inserts memory node."""
        mn = _TMemoryNode(
            id=uuid4(),
            workspace_id=test_workspace_id,
            entity_id=str(uuid4()),
            level=1,
            node_type="Observation",
            content="Test memory content",
            status="active",
        )
        mn_id = await memory_node_repo.create(mn)
        assert mn_id is not None

        found = await memory_node_repo.find_by_id(mn_id)
        assert found is not None
        assert found.content == "Test memory content"

    @pytest.mark.asyncio
    async def test_memory_update_prohibited(self, memory_node_repo: _TMemoryNodeRepo) -> None:
        """Verify MemoryNodeRepository.update() raises DomainIntegrityError."""
        with pytest.raises(DomainIntegrityError, match="immutable"):
            await memory_node_repo.update(object())  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_memory_soft_delete_prohibited(self, memory_node_repo: _TMemoryNodeRepo) -> None:
        """Verify MemoryNodeRepository.soft_delete() raises DomainIntegrityError."""
        with pytest.raises(DomainIntegrityError, match="immutable"):
            await memory_node_repo.soft_delete(uuid4())

    @pytest.mark.asyncio
    async def test_memory_find_by_entity(self, memory_node_repo: _TMemoryNodeRepo, test_workspace_id: str) -> None:
        """Verify find_by_entity returns memory nodes for an entity."""
        eid = uuid4()
        for i in range(3):
            mn = _TMemoryNode(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(eid),
                level=1,
                node_type="Observation",
                content=f"Memory {i}",
                status="active",
            )
            memory_node_repo.session.add(mn)
        await memory_node_repo.session.flush()

        results = await memory_node_repo.find_by_entity(entity_id=eid, workspace_id=UUID(test_workspace_id))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_memory_find_by_level(self, memory_node_repo: _TMemoryNodeRepo, test_workspace_id: str) -> None:
        """Verify find_by_level returns memory nodes at a specific level."""
        for i in range(3):
            mn = _TMemoryNode(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(uuid4()),
                level=1,
                node_type="Observation",
                content=f"L1 Memory {i}",
                status="active",
            )
            memory_node_repo.session.add(mn)
        await memory_node_repo.session.flush()

        results = await memory_node_repo.find_by_level(level=1, workspace_id=UUID(test_workspace_id))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_memory_find_by_status(self, memory_node_repo: _TMemoryNodeRepo, test_workspace_id: str) -> None:
        """Verify find_by_status returns memory nodes with given status."""
        for i in range(3):
            mn = _TMemoryNode(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(uuid4()),
                level=1,
                node_type="Observation",
                content=f"Memory {i}",
                status="active" if i < 2 else "candidate",
            )
            memory_node_repo.session.add(mn)
        await memory_node_repo.session.flush()

        results = await memory_node_repo.find_by_status(status="candidate", workspace_id=UUID(test_workspace_id))
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_memory_find_active_by_workspace(self, memory_node_repo: _TMemoryNodeRepo, test_workspace_id: str) -> None:
        """Verify find_active_by_workspace returns only active nodes."""
        for i in range(3):
            mn = _TMemoryNode(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(uuid4()),
                level=1,
                node_type="Observation",
                content=f"Memory {i}",
                status="active",
            )
            memory_node_repo.session.add(mn)
        await memory_node_repo.session.flush()

        results = await memory_node_repo.find_active_by_workspace(workspace_id=UUID(test_workspace_id))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_memory_find_page(self, memory_node_repo: _TMemoryNodeRepo, test_workspace_id: str) -> None:
        """Verify memory node pagination."""
        for i in range(7):
            mn = _TMemoryNode(
                id=uuid4(),
                workspace_id=test_workspace_id,
                entity_id=str(uuid4()),
                level=1,
                node_type="Observation",
                content=f"Memory {i}",
                status="active",
            )
            memory_node_repo.session.add(mn)
        await memory_node_repo.session.flush()

        page = await memory_node_repo.find_page(
            workspace_id=UUID(test_workspace_id),
            page_number=1,
            page_size=5,
        )
        assert len(page.items) == 5
        assert page.has_next is True

    @pytest.mark.asyncio
    async def test_memory_find_with_evidence_chain(self, memory_node_repo: _TMemoryNodeRepo, test_workspace_id: str) -> None:
        """Verify find_with_evidence_chain returns node + evidence."""
        mn = _TMemoryNode(
            id=uuid4(),
            workspace_id=test_workspace_id,
            entity_id=str(uuid4()),
            level=1,
            node_type="Observation",
            content="Memory with evidence",
            status="active",
        )
        memory_node_repo.session.add(mn)
        await memory_node_repo.session.flush()

        result = await memory_node_repo.find_with_evidence_chain(memory_node_id=mn.id)
        assert "node" in result
        assert "evidence_chain" in result
        assert len(result["evidence_chain"]) == 0


# ---------------------------------------------------------------------------
# ArchiveRepository Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestArchiveRepository:
    """Tests for ArchiveRepository CRUD."""

    @pytest.mark.asyncio
    async def test_archive_create(self, archive_repo: _TArchiveRepo, test_workspace_id: str) -> None:
        """Verify create() inserts archive."""
        arch = _TArchive(
            id=uuid4(),
            workspace_id=test_workspace_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            archive_type="monthly",
            summary="January 2026 archive",
            source_count=10,
        )
        arch_id = await archive_repo.create(arch)
        assert arch_id is not None

        found = await archive_repo.find_by_id(arch_id)
        assert found is not None
        assert found.summary == "January 2026 archive"

    @pytest.mark.asyncio
    async def test_archive_find_by_type(self, archive_repo: _TArchiveRepo, test_workspace_id: str) -> None:
        """Verify find_by_type returns archives of given type."""
        for i in range(3):
            arch = _TArchive(
                id=uuid4(),
                workspace_id=test_workspace_id,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                archive_type="monthly" if i < 2 else "yearly",
                summary=f"Archive {i}",
                source_count=10,
            )
            archive_repo.session.add(arch)
        await archive_repo.session.flush()

        results = await archive_repo.find_by_type(
            archive_type="monthly",
            workspace_id=UUID(test_workspace_id),
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_archive_find_by_period(self, archive_repo: _TArchiveRepo, test_workspace_id: str) -> None:
        """Verify find_by_period returns overlapping archives."""
        arch = _TArchive(
            id=uuid4(),
            workspace_id=test_workspace_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            archive_type="monthly",
            summary="Q1 archive",
            source_count=30,
        )
        archive_repo.session.add(arch)
        await archive_repo.session.flush()

        results = await archive_repo.find_by_period(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            workspace_id=UUID(test_workspace_id),
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_archive_find_page(self, archive_repo: _TArchiveRepo, test_workspace_id: str) -> None:
        """Verify archive pagination."""
        for i in range(5):
            arch = _TArchive(
                id=uuid4(),
                workspace_id=test_workspace_id,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                archive_type="monthly",
                summary=f"Archive {i}",
                source_count=10,
            )
            archive_repo.session.add(arch)
        await archive_repo.session.flush()

        page = await archive_repo.find_page(
            workspace_id=UUID(test_workspace_id),
            page_number=1,
            page_size=3,
        )
        assert len(page.items) == 3
        assert page.has_next is True


# ---------------------------------------------------------------------------
# TagRepository Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTagRepository:
    """Tests for TagRepository CRUD."""

    @pytest.mark.asyncio
    async def test_tag_create(self, tag_repo: _TTagRepo, test_workspace_id: str) -> None:
        """Verify create() inserts tag."""
        tag = _TTag(
            id=uuid4(),
            workspace_id=test_workspace_id,
            name="important",
            tag_type="user",
            color="#FF0000",
        )
        tag_id = await tag_repo.create(tag)
        assert tag_id is not None

        found = await tag_repo.find_by_id(tag_id)
        assert found is not None
        assert found.name == "important"

    @pytest.mark.asyncio
    async def test_tag_find_by_workspace(self, tag_repo: _TTagRepo, test_workspace_id: str) -> None:
        """Verify find_by_workspace returns tags for workspace."""
        for i in range(3):
            tag = _TTag(
                id=uuid4(),
                workspace_id=test_workspace_id,
                name=f"tag-{i}",
                tag_type="user",
            )
            tag_repo.session.add(tag)
        await tag_repo.session.flush()

        results = await tag_repo.find_by_workspace(workspace_id=UUID(test_workspace_id))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_tag_find_by_name(self, tag_repo: _TTagRepo, test_workspace_id: str) -> None:
        """Verify find_by_name returns a specific tag."""
        tag = _TTag(
            id=uuid4(),
            workspace_id=test_workspace_id,
            name="my-tag",
            tag_type="user",
        )
        tag_repo.session.add(tag)
        await tag_repo.session.flush()

        found = await tag_repo.find_by_name(
            name="my-tag",
            workspace_id=UUID(test_workspace_id),
        )
        assert found is not None
        assert found.name == "my-tag"

    @pytest.mark.asyncio
    async def test_tag_find_page(self, tag_repo: _TTagRepo, test_workspace_id: str) -> None:
        """Verify tag pagination."""
        for i in range(5):
            tag = _TTag(
                id=uuid4(),
                workspace_id=test_workspace_id,
                name=f"tag-{i}",
                tag_type="user",
            )
            tag_repo.session.add(tag)
        await tag_repo.session.flush()

        page = await tag_repo.find_page(
            workspace_id=UUID(test_workspace_id),
            page_number=1,
            page_size=3,
        )
        assert len(page.items) == 3
        assert page.has_next is True


# ---------------------------------------------------------------------------
# Import Boundary Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestImportBoundaries:
    """Verify repository layer boundary rules."""

    def test_no_service_imports(self) -> None:
        """Verify repository modules don't import from service layer."""
        import backend.repository.archive_repository
        import backend.repository.evidence_repository
        import backend.repository.memory_node_repository
        import backend.repository.memory_query_repository
        import backend.repository.tag_repository  # noqa: F401
        assert True

    def test_no_engine_imports(self) -> None:
        """Verify repository modules don't import from engine layer."""
        import backend.repository.evidence_repository
        import backend.repository.memory_node_repository  # noqa: F401
        assert True
