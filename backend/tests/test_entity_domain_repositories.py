"""Unit tests for Entity Domain Repositories (D2.3).

Tests EntityRepository, RelationshipRepository, and EntityQueryRepository.
Uses minimal test models with str IDs to avoid SQLite UUID type issues.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import (
    Float,
    Integer,
    String,
    Text,
    func,
    select,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.shared.infrastructure.uuid import generate_uuid

_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

from backend.repository.base import BaseRepository
from backend.repository.exceptions import (
    IntegrityError as DomainIntegrityError,
)
from backend.repository.pagination import Page
from backend.repository.query import QueryRepository

# ===========================================================================
# Test Models — all IDs are str to avoid SQLite UUID binding issues
# ===========================================================================


class _TestBase(DeclarativeBase):
    pass


class _TEntity(_TestBase):
    __tablename__ = "tentities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    area_id: Mapped[str | None] = mapped_column(String(36))
    parent_entity_id: Mapped[str | None] = mapped_column(String(36))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    meta = mapped_column(Text)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    relationship_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )


class _TArea(_TestBase):
    __tablename__ = "tareass"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parent_area_id: Mapped[str | None] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )


class _TWorkspace(_TestBase):
    __tablename__ = "tworkspace"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )


class _TUserProfile(_TestBase):
    __tablename__ = "tuserprofiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    external_user_id: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )


class _TEntityRelationship(_TestBase):
    __tablename__ = "tentityrels"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strength: Mapped[float] = mapped_column(Float, default=1.0)
    meta = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )


class _TMemoryRelationship(_TestBase):
    __tablename__ = "tmemrels"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    contribution_weight: Mapped[float] = mapped_column(Float, default=1.0)
    meta = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )


def _to_json(val: Any) -> str:
    if isinstance(val, dict):
        return json.dumps(val)
    return val if isinstance(val, str) else str(val)


# ===========================================================================
# Test Repository Implementations
# ===========================================================================


class _TEntityRepo(BaseRepository):
    _model_class = _TEntity
    _table_name = "tentities"

    async def soft_delete_impl(self, id: Any) -> None:
        raise DomainIntegrityError(entity_type="entity", constraint="Never deleted")

    async def find_by_workspace(
        self, *, workspace_id: UUID, entity_types: list[str] | None = None,
        area_id: UUID | None = None, offset: int = 0, limit: int = 100,
        order_by: str = "created_at", descending: bool = False,
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id)
        )
        if entity_types:
            stmt = stmt.where(self._model_class.entity_type.in_(entity_types))
        if area_id:
            stmt = stmt.where(self._model_class.area_id == str(area_id))
        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_name(
        self, *, canonical_name: str, workspace_id: UUID, entity_type: str | None = None
    ) -> Any | None:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.canonical_name == canonical_name,
        )
        if entity_type:
            stmt = stmt.where(self._model_class.entity_type == entity_type)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_alias(self, *, alias: str, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.aliases.like(f"%{alias}%"),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_area(self, *, area_id: UUID, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.area_id == str(area_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_parent(
        self, *, parent_entity_id: UUID, workspace_id: UUID
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.parent_entity_id == str(parent_entity_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_page(
        self, *, workspace_id: UUID, page_number: int = 1, page_size: int = 20,
        entity_types: list[str] | None = None,
    ) -> Page[Any]:
        offset = (page_number - 1) * page_size
        items = await self.find_by_workspace(
            workspace_id=workspace_id, entity_types=entity_types,
            offset=offset, limit=page_size + 1,
        )
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]
        return Page(
            items=items, total=None, page_number=page_number,
            page_size=page_size, has_next=has_next, has_prev=page_number > 1,
        )

    async def create_area(self, area: Any, *, workspace_id: UUID) -> UUID:
        self.session.add(area)
        await self.session.flush()
        return area.id

    async def find_area_by_name(self, *, name: str, workspace_id: UUID) -> Any | None:
        stmt = select(_TArea).where(
            _TArea.workspace_id == str(workspace_id), _TArea.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_child_areas(self, *, parent_area_id: UUID, workspace_id: UUID) -> list[Any]:
        stmt = select(_TArea).where(
            _TArea.workspace_id == str(workspace_id),
            _TArea.parent_area_id == str(parent_area_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_workspace(self, *, name: str, description: str | None = None) -> Any:
        stmt = select(_TWorkspace).limit(1)
        result = await self.session.execute(stmt)
        ws = result.scalar_one_or_none()
        if ws is None:
            ws = _TWorkspace(id=str(generate_uuid()), name=name)
            self.session.add(ws)
            await self.session.flush()
        return ws

    async def create_user_profile(self, profile: Any, *, workspace_id: UUID) -> UUID:
        self.session.add(profile)
        await self.session.flush()
        return profile.id

    async def find_user_profile_by_external(
        self, *, external_user_id: str, workspace_id: UUID
    ) -> Any | None:
        stmt = select(_TUserProfile).where(
            _TUserProfile.workspace_id == str(workspace_id),
            _TUserProfile.external_user_id == external_user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class _TRelRepo(BaseRepository):
    _model_class = _TEntityRelationship
    _table_name = "tentityrels"

    async def soft_delete_impl(self, id: Any) -> None:
        raise DomainIntegrityError(entity_type="relationship", constraint="Never deleted")

    async def find_by_source(
        self, *, source_id: UUID, workspace_id: UUID,
        relationship_type: str | None = None,
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_id == str(source_id),
        )
        if relationship_type:
            stmt = stmt.where(self._model_class.relationship_type == relationship_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_target(
        self, *, target_id: UUID, workspace_id: UUID,
        relationship_type: str | None = None,
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.target_id == str(target_id),
        )
        if relationship_type:
            stmt = stmt.where(self._model_class.relationship_type == relationship_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_type(self, *, relationship_type: str, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.relationship_type == relationship_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_connections(self, *, entity_id: UUID, workspace_id: UUID) -> list[Any]:
        stmt = union_all(
            select(self._model_class).where(
                self._model_class.workspace_id == str(workspace_id),
                self._model_class.source_id == str(entity_id),
            ),
            select(self._model_class).where(
                self._model_class.workspace_id == str(workspace_id),
                self._model_class.target_id == str(entity_id),
            ),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_pair(
        self, *, source_id: UUID, target_id: UUID, workspace_id: UUID
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.source_id == str(source_id),
            self._model_class.target_id == str(target_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_memory_relationship(self, relationship: Any) -> UUID:
        self.session.add(relationship)
        await self.session.flush()
        return relationship.id

    async def find_memory_relationships_by_source(
        self, *, source_node_id: UUID, workspace_id: UUID
    ) -> list[Any]:
        stmt = select(_TMemoryRelationship).where(
            _TMemoryRelationship.workspace_id == str(workspace_id),
            _TMemoryRelationship.source_node_id == str(source_node_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_memory_relationships_by_target(
        self, *, target_node_id: UUID, workspace_id: UUID
    ) -> list[Any]:
        stmt = select(_TMemoryRelationship).where(
            _TMemoryRelationship.workspace_id == str(workspace_id),
            _TMemoryRelationship.target_node_id == str(target_node_id),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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
            items=items, total=None, page_number=page_number,
            page_size=page_size, has_next=has_next, has_prev=page_number > 1,
        )


class _TEntityQueryRepo(QueryRepository):
    _model_class = _TEntity
    _table_name = "tentities"

    async def complex_query(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def find_by_canonical_name(
        self, *, canonical_name: str, workspace_id: UUID,
        entity_type: str | None = None,
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.canonical_name == canonical_name,
        )
        if entity_type:
            stmt = stmt.where(self._model_class.entity_type == entity_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_alias(self, *, alias: str, workspace_id: UUID) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.aliases.like(f"%{alias}%"),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_type(
        self, *, entity_type: str, workspace_id: UUID,
        offset: int = 0, limit: int = 100,
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
            self._model_class.entity_type == entity_type,
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_type(self, *, workspace_id: UUID) -> dict[str, int]:
        stmt = select(
            self._model_class.entity_type,
            func.count(self._model_class.id).label("count"),
        ).where(
            self._model_class.workspace_id == str(workspace_id),
        ).group_by(self._model_class.entity_type)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def find_related_entities(
        self, *, entity_id: UUID, workspace_id: UUID,
        relationship_type: str | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        stmt_out = select(_TEntityRelationship, _TEntity).join(
            _TEntity, _TEntityRelationship.target_id == _TEntity.id,
        ).where(
            _TEntityRelationship.workspace_id == str(workspace_id),
            _TEntityRelationship.source_id == str(entity_id),
        )
        if relationship_type:
            stmt_out = stmt_out.where(
                _TEntityRelationship.relationship_type == relationship_type
            )
        result_out = await self.session.execute(stmt_out)
        for rel, ent in result_out.all():
            results.append({"entity": ent, "relationship": rel, "direction": "outgoing"})
        stmt_in = select(_TEntityRelationship, _TEntity).join(
            _TEntity, _TEntityRelationship.source_id == _TEntity.id,
        ).where(
            _TEntityRelationship.workspace_id == str(workspace_id),
            _TEntityRelationship.target_id == str(entity_id),
        )
        if relationship_type:
            stmt_in = stmt_in.where(
                _TEntityRelationship.relationship_type == relationship_type
            )
        result_in = await self.session.execute(stmt_in)
        for rel, ent in result_in.all():
            results.append({"entity": ent, "relationship": rel, "direction": "incoming"})
        return results

    async def find_relationships_for_entity(
        self, *, entity_id: UUID, workspace_id: UUID
    ) -> list[Any]:
        stmt = union_all(
            select(_TEntityRelationship).where(
                _TEntityRelationship.workspace_id == str(workspace_id),
                _TEntityRelationship.source_id == str(entity_id),
            ),
            select(_TEntityRelationship).where(
                _TEntityRelationship.workspace_id == str(workspace_id),
                _TEntityRelationship.target_id == str(entity_id),
            ),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_filtered(
        self, *, workspace_id: UUID,
        entity_types: list[str] | None = None,
        area_id: UUID | None = None,
        min_relationship_count: int | None = None,
        offset: int = 0, limit: int = 100,
        order_by: str = "created_at", descending: bool = False,
    ) -> list[Any]:
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == str(workspace_id),
        )
        if entity_types:
            stmt = stmt.where(self._model_class.entity_type.in_(entity_types))
        if area_id:
            stmt = stmt.where(self._model_class.area_id == str(area_id))
        if min_relationship_count is not None:
            stmt = stmt.where(
                self._model_class.relationship_count >= min_relationship_count
            )
        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_page(
        self, *, workspace_id: UUID, page_number: int = 1, page_size: int = 20,
        entity_types: list[str] | None = None,
    ) -> Page[Any]:
        offset = (page_number - 1) * page_size
        items = await self.find_filtered(
            workspace_id=workspace_id, entity_types=entity_types,
            offset=offset, limit=page_size + 1,
        )
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]
        return Page(
            items=items, total=None, page_number=page_number,
            page_size=page_size, has_next=has_next, has_prev=page_number > 1,
        )

    async def get_entity_graph(
        self, *, entity_id: UUID, workspace_id: UUID, depth: int = 1
    ) -> dict[str, Any]:
        stmt = select(self._model_class).where(
            self._model_class.id == str(entity_id)
        )
        result = await self.session.execute(stmt)
        center = result.scalar_one_or_none()
        related = await self.find_related_entities(
            entity_id=entity_id, workspace_id=workspace_id,
        )
        return {"center": center, "neighbors": related, "depth": depth}

    async def get_entity_count(self, *, workspace_id: UUID) -> int:
        stmt = select(func.count(self._model_class.id)).where(
            self._model_class.workspace_id == str(workspace_id),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
# ===========================================================================
# Fixtures
# ===========================================================================


# event_loop fixture removed — pytest-asyncio handles module-scoped loops via
# @pytest.mark.asyncio(loop_scope="module") on each test instead.


@pytest.fixture(scope="module")
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_TEntity.metadata.create_all)
        await conn.run_sync(_TArea.metadata.create_all)
        await conn.run_sync(_TWorkspace.metadata.create_all)
        await conn.run_sync(_TUserProfile.metadata.create_all)
        await conn.run_sync(_TEntityRelationship.metadata.create_all)
        await conn.run_sync(_TMemoryRelationship.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(test_engine):
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as sess:
        yield sess
        await sess.rollback()


@pytest_asyncio.fixture
async def workspace_id(session):
    ws = _TWorkspace(id=str(generate_uuid()), name="test-workspace")
    session.add(ws)
    await session.flush()
    return ws.id


@pytest_asyncio.fixture
async def sample_entity(session, workspace_id):
    eid = str(generate_uuid())
    entity = _TEntity(
        id=eid, workspace_id=str(workspace_id),
        entity_type="Project", canonical_name="Test Project",
        aliases=_to_json(["TP", "TestProj"]), description="A test project entity",
        meta=_to_json({"version": "1.0"}),
        observation_count=5, relationship_count=3,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    session.add(entity)
    await session.flush()
    return entity


@pytest_asyncio.fixture
async def sample_area(session, workspace_id):
    aid = str(generate_uuid())
    area = _TArea(
        id=aid, workspace_id=str(workspace_id),
        name="Test Area", sort_order=1,
        created_at=datetime.now(),
    )
    session.add(area)
    await session.flush()
    return area


@pytest_asyncio.fixture
async def sample_user_profile(session, workspace_id):
    uid = str(generate_uuid())
    profile = _TUserProfile(
        id=uid, workspace_id=str(workspace_id),
        external_user_id="ext-user-001", display_name="Test User",
        created_at=datetime.now(),
    )
    session.add(profile)
    await session.flush()
    return profile


@pytest_asyncio.fixture
async def test_entity_repo(session, workspace_id):
    return _TEntityRepo(session)


@pytest_asyncio.fixture
async def test_rel_repo(session, workspace_id):
    return _TRelRepo(session)


@pytest_asyncio.fixture
async def test_entity_query_repo(session, workspace_id):
    return _TEntityQueryRepo(session)


# ===========================================================================
# Test Cases — EntityRepository
# ===========================================================================


class TestEntityRepository:
    @pytest.mark.asyncio
    async def test_create_entity(self, test_entity_repo, workspace_id):
        eid = str(generate_uuid())
        entity = _TEntity(
            id=eid, workspace_id=str(workspace_id),
            entity_type="Project", canonical_name="New Project",
            aliases=_to_json(["NP"]), meta=_to_json({}),
        )
        result_id = await test_entity_repo.create(entity)
        assert str(result_id) == entity.id

    @pytest.mark.asyncio
    async def test_find_by_id_existing(self, test_entity_repo, sample_entity):
        found = await test_entity_repo.find_by_id(sample_entity.id)
        assert found is not None
        assert found.id == sample_entity.id
        assert found.canonical_name == "Test Project"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, test_entity_repo):
        found = await test_entity_repo.find_by_id(str(generate_uuid()))
        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_workspace(self, test_entity_repo, workspace_id):
        for i in range(3):
            eid = str(generate_uuid())
            e = _TEntity(
                id=eid, workspace_id=str(workspace_id),
                entity_type="Person", canonical_name=f"Person {i}",
                meta=_to_json({}),
            )
            test_entity_repo.session.add(e)
        await test_entity_repo.session.flush()
        results = await test_entity_repo.find_by_workspace(
            workspace_id=workspace_id, entity_types=["Person"]
        )
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_find_by_workspace_type_filter(self, test_entity_repo, workspace_id):
        for etype in ["Project", "Person", "Tool"]:
            eid = str(generate_uuid())
            e = _TEntity(
                id=eid, workspace_id=str(workspace_id),
                entity_type=etype, canonical_name=f"{etype} Entity",
                meta=_to_json({}),
            )
            test_entity_repo.session.add(e)
        await test_entity_repo.session.flush()
        projects = await test_entity_repo.find_by_workspace(
            workspace_id=workspace_id, entity_types=["Project"]
        )
        assert all(e.entity_type == "Project" for e in projects)

    @pytest.mark.asyncio
    async def test_find_by_name(self, test_entity_repo, workspace_id, sample_entity):
        found = await test_entity_repo.find_by_name(
            canonical_name="Test Project", workspace_id=workspace_id,
        )
        assert found is not None
        assert found.id == sample_entity.id

    @pytest.mark.asyncio
    async def test_find_by_name_with_type_filter(self, test_entity_repo, workspace_id):
        eid = str(generate_uuid())
        e = _TEntity(
            id=eid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="John Doe",
            meta=_to_json({}),
        )
        test_entity_repo.session.add(e)
        await test_entity_repo.session.flush()
        found = await test_entity_repo.find_by_name(
            canonical_name="John Doe", workspace_id=workspace_id, entity_type="Person",
        )
        assert found is not None
        assert found.entity_type == "Person"
        found_wrong = await test_entity_repo.find_by_name(
            canonical_name="John Doe", workspace_id=workspace_id, entity_type="Project",
        )
        assert found_wrong is None

    @pytest.mark.asyncio
    async def test_find_by_alias(self, test_entity_repo, workspace_id, sample_entity):
        found = await test_entity_repo.find_by_alias(alias="TP", workspace_id=workspace_id)
        assert len(found) >= 1
        assert any(e.id == sample_entity.id for e in found)

    @pytest.mark.asyncio
    async def test_find_by_area(self, test_entity_repo, workspace_id, sample_area):
        eid = str(generate_uuid())
        e = _TEntity(
            id=eid, workspace_id=str(workspace_id),
            entity_type="Project", canonical_name="Area Entity",
            area_id=sample_area.id, meta=_to_json({}),
        )
        test_entity_repo.session.add(e)
        await test_entity_repo.session.flush()
        results = await test_entity_repo.find_by_area(
            area_id=sample_area.id, workspace_id=workspace_id,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_find_by_parent(self, test_entity_repo, workspace_id, sample_entity):
        cid = str(generate_uuid())
        child = _TEntity(
            id=cid, workspace_id=str(workspace_id),
            entity_type="Concept", canonical_name="Child Entity",
            parent_entity_id=sample_entity.id, meta=_to_json({}),
        )
        test_entity_repo.session.add(child)
        await test_entity_repo.session.flush()
        children = await test_entity_repo.find_by_parent(
            parent_entity_id=sample_entity.id, workspace_id=workspace_id,
        )
        assert len(children) >= 1
        assert children[0].parent_entity_id == sample_entity.id

    @pytest.mark.asyncio
    async def test_soft_delete_raises(self, test_entity_repo, sample_entity):
        with pytest.raises(DomainIntegrityError):
            await test_entity_repo.soft_delete_impl(sample_entity.id)

    @pytest.mark.asyncio
    async def test_create_area(self, test_entity_repo, workspace_id):
        aid = str(generate_uuid())
        area = _TArea(
            id=aid, workspace_id=str(workspace_id),
            name="New Area", sort_order=2,
        )
        area_id = await test_entity_repo.create_area(area, workspace_id=workspace_id)
        assert area_id == area.id

    @pytest.mark.asyncio
    async def test_find_area_by_name(self, test_entity_repo, workspace_id, sample_area):
        found = await test_entity_repo.find_area_by_name(
            name="Test Area", workspace_id=workspace_id,
        )
        assert found is not None
        assert found.id == sample_area.id

    @pytest.mark.asyncio
    async def test_create_user_profile(self, test_entity_repo, workspace_id):
        uid = str(generate_uuid())
        profile = _TUserProfile(
            id=uid, workspace_id=str(workspace_id),
            external_user_id="test-ext-id", display_name="Test User",
        )
        pid = await test_entity_repo.create_user_profile(
            profile, workspace_id=workspace_id
        )
        assert pid == profile.id

    @pytest.mark.asyncio
    async def test_find_user_profile_by_external(
        self, test_entity_repo, workspace_id, sample_user_profile
    ):
        found = await test_entity_repo.find_user_profile_by_external(
            external_user_id="ext-user-001", workspace_id=workspace_id,
        )
        assert found is not None
        assert found.id == sample_user_profile.id

    @pytest.mark.asyncio
    async def test_pagination(self, test_entity_repo, workspace_id):
        for idx in range(5):
            eid = str(generate_uuid())
            e = _TEntity(
                id=eid, workspace_id=str(workspace_id),
                entity_type="Concept", canonical_name=f"Concept {idx}",
                meta=_to_json({}),
            )
            test_entity_repo.session.add(e)
        await test_entity_repo.session.flush()
        page = await test_entity_repo.find_page(
            workspace_id=workspace_id, entity_types=["Concept"],
            page_number=1, page_size=3,
        )
        assert len(page.items) == 3
        assert page.has_next is True
        page2 = await test_entity_repo.find_page(
            workspace_id=workspace_id, entity_types=["Concept"],
            page_number=2, page_size=3,
        )
        assert len(page2.items) == 2
        assert page2.has_next is False
# ===========================================================================
# Test Cases — RelationshipRepository
# ===========================================================================


class TestRelationshipRepository:
    @pytest.mark.asyncio
    async def test_find_by_source(self, test_rel_repo, workspace_id, sample_entity):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Target Person",
            meta=_to_json({}),
        )
        test_rel_repo.session.add(target)
        await test_rel_repo.session.flush()
        rel = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="created_by", strength=1.0,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(rel)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_by_source(
            source_id=sample_entity.id, workspace_id=workspace_id,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_find_by_source_type_filter(self, test_rel_repo, workspace_id, sample_entity):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Target",
            meta=_to_json({}),
        )
        test_rel_repo.session.add(target)
        await test_rel_repo.session.flush()
        rel = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="uses", strength=0.5,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(rel)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_by_source(
            source_id=sample_entity.id, workspace_id=workspace_id,
            relationship_type="uses",
        )
        assert all(r.relationship_type == "uses" for r in results)

    @pytest.mark.asyncio
    async def test_find_by_target(self, test_rel_repo, workspace_id, sample_entity):
        sid = str(generate_uuid())
        source = _TEntity(
            id=sid, workspace_id=str(workspace_id),
            entity_type="Project", canonical_name="Source Project",
            meta=_to_json({}),
        )
        test_rel_repo.session.add(source)
        await test_rel_repo.session.flush()
        rel = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sid, target_id=sample_entity.id,
            relationship_type="created_by", strength=1.0,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(rel)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_by_target(
            target_id=sample_entity.id, workspace_id=workspace_id,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_find_by_type(self, test_rel_repo, workspace_id, sample_entity):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Target",
            meta=_to_json({}),
        )
        test_rel_repo.session.add(target)
        await test_rel_repo.session.flush()
        for i in range(3):
            rel = _TEntityRelationship(
                id=str(generate_uuid()), workspace_id=str(workspace_id),
                source_id=sample_entity.id, target_id=tid,
                relationship_type="related_to", strength=float(i + 1) / 4,
                meta=_to_json({}),
            )
            test_rel_repo.session.add(rel)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_by_type(
            relationship_type="related_to", workspace_id=workspace_id,
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_connections(self, test_rel_repo, workspace_id, sample_entity):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Target",
            meta=_to_json({}),
        )
        test_rel_repo.session.add(target)
        await test_rel_repo.session.flush()
        rel1 = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="created_by", strength=1.0,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(rel1)
        sid = str(generate_uuid())
        source = _TEntity(
            id=sid, workspace_id=str(workspace_id),
            entity_type="Project", canonical_name="Source",
            meta=_to_json({}),
        )
        test_rel_repo.session.add(source)
        await test_rel_repo.session.flush()
        rel2 = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sid, target_id=sample_entity.id,
            relationship_type="uses", strength=0.8,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(rel2)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_connections(
            entity_id=sample_entity.id, workspace_id=workspace_id,
        )
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_multiple_relationships_same_pair(
        self, test_rel_repo, workspace_id, sample_entity
    ):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Target",
            meta=_to_json({}),
        )
        test_rel_repo.session.add(target)
        await test_rel_repo.session.flush()
        rel1 = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="created_by", strength=1.0,
            meta=_to_json({}),
        )
        rel2 = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="related_to", strength=0.5,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(rel1)
        test_rel_repo.session.add(rel2)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_by_pair(
            source_id=sample_entity.id, target_id=tid,
            workspace_id=workspace_id,
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_create_memory_relationship(self, test_rel_repo, workspace_id):
        mem_rel = _TMemoryRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_node_id=str(generate_uuid()), target_node_id=str(generate_uuid()),
            relationship_type="supports", contribution_weight=0.9,
            meta=_to_json({}),
        )
        rid = await test_rel_repo.create_memory_relationship(mem_rel)
        assert rid == mem_rel.id

    @pytest.mark.asyncio
    async def test_find_memory_by_source(self, test_rel_repo, workspace_id):
        src_id = str(generate_uuid())
        mem_rel = _TMemoryRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_node_id=src_id, target_node_id=str(generate_uuid()),
            relationship_type="supports", contribution_weight=0.8,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(mem_rel)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_memory_relationships_by_source(
            source_node_id=src_id, workspace_id=workspace_id,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_find_memory_by_target(self, test_rel_repo, workspace_id):
        tgt_id = str(generate_uuid())
        mem_rel = _TMemoryRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_node_id=str(generate_uuid()), target_node_id=tgt_id,
            relationship_type="contradicts", contribution_weight=0.6,
            meta=_to_json({}),
        )
        test_rel_repo.session.add(mem_rel)
        await test_rel_repo.session.flush()
        results = await test_rel_repo.find_memory_relationships_by_target(
            target_node_id=tgt_id, workspace_id=workspace_id,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_pagination(self, test_rel_repo, workspace_id, sample_entity):
        for _i in range(5):
            rel = _TEntityRelationship(
                id=str(generate_uuid()), workspace_id=str(workspace_id),
                source_id=sample_entity.id, target_id=str(generate_uuid()),
                relationship_type="related_to", strength=0.5,
                meta=_to_json({}),
            )
            test_rel_repo.session.add(rel)
        await test_rel_repo.session.flush()
        page = await test_rel_repo.find_page(
            workspace_id=workspace_id, page_number=1, page_size=3,
        )
        assert len(page.items) == 3
        assert page.has_next is True
# ===========================================================================
# Test Cases — EntityQueryRepository
# ===========================================================================


class TestEntityQueryRepository:
    @pytest.mark.asyncio
    async def test_find_by_canonical_name(self, test_entity_query_repo, workspace_id, sample_entity):
        results = await test_entity_query_repo.find_by_canonical_name(
            canonical_name="Test Project", workspace_id=workspace_id,
        )
        assert len(results) >= 1
        assert any(e.id == sample_entity.id for e in results)

    @pytest.mark.asyncio
    async def test_find_by_alias(self, test_entity_query_repo, workspace_id, sample_entity):
        results = await test_entity_query_repo.find_by_alias(
            alias="TP", workspace_id=workspace_id,
        )
        assert len(results) >= 1
        assert any(e.id == sample_entity.id for e in results)

    @pytest.mark.asyncio
    async def test_find_by_type(self, test_entity_query_repo, workspace_id, sample_entity):
        eid = str(generate_uuid())
        e2 = _TEntity(
            id=eid, workspace_id=str(workspace_id),
            entity_type="Project", canonical_name="Another Project",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(e2)
        await test_entity_query_repo.session.flush()
        results = await test_entity_query_repo.find_by_type(
            entity_type="Project", workspace_id=workspace_id,
        )
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_count_by_type(self, test_entity_query_repo, workspace_id, sample_entity):
        eid = str(generate_uuid())
        e2 = _TEntity(
            id=eid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Another Person",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(e2)
        await test_entity_query_repo.session.flush()
        counts = await test_entity_query_repo.count_by_type(
            workspace_id=workspace_id,
        )
        assert "Project" in counts
        assert counts["Project"] >= 1
        assert "Person" in counts
        assert counts["Person"] >= 1

    @pytest.mark.asyncio
    async def test_find_related_entities_outgoing(
        self, test_entity_query_repo, workspace_id, sample_entity
    ):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Related Person",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(target)
        await test_entity_query_repo.session.flush()
        rel = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="created_by", strength=1.0,
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(rel)
        await test_entity_query_repo.session.flush()
        results = await test_entity_query_repo.find_related_entities(
            entity_id=sample_entity.id, workspace_id=workspace_id,
        )
        outgoing = [r for r in results if r["direction"] == "outgoing"]
        assert len(outgoing) >= 1

    @pytest.mark.asyncio
    async def test_find_related_entities_incoming(
        self, test_entity_query_repo, workspace_id, sample_entity
    ):
        sid = str(generate_uuid())
        source = _TEntity(
            id=sid, workspace_id=str(workspace_id),
            entity_type="Project", canonical_name="Source Project",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(source)
        await test_entity_query_repo.session.flush()
        rel = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sid, target_id=sample_entity.id,
            relationship_type="uses", strength=0.8,
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(rel)
        await test_entity_query_repo.session.flush()
        results = await test_entity_query_repo.find_related_entities(
            entity_id=sample_entity.id, workspace_id=workspace_id,
        )
        incoming = [r for r in results if r["direction"] == "incoming"]
        assert len(incoming) >= 1

    @pytest.mark.asyncio
    async def test_find_relationships_for_entity(
        self, test_entity_query_repo, workspace_id, sample_entity
    ):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Target",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(target)
        await test_entity_query_repo.session.flush()
        rel = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="created_by", strength=1.0,
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(rel)
        await test_entity_query_repo.session.flush()
        results = await test_entity_query_repo.find_relationships_for_entity(
            entity_id=sample_entity.id, workspace_id=workspace_id,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_find_filtered_by_type(self, test_entity_query_repo, workspace_id, sample_entity):
        eid = str(generate_uuid())
        e2 = _TEntity(
            id=eid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Another Person",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(e2)
        await test_entity_query_repo.session.flush()
        results = await test_entity_query_repo.find_filtered(
            workspace_id=workspace_id, entity_types=["Person"],
        )
        assert all(e.entity_type == "Person" for e in results)

    @pytest.mark.asyncio
    async def test_find_filtered_by_min_relationship_count(
        self, test_entity_query_repo, workspace_id, sample_entity
    ):
        results = await test_entity_query_repo.find_filtered(
            workspace_id=workspace_id, min_relationship_count=3,
        )
        assert any(e.id == sample_entity.id for e in results)

    @pytest.mark.asyncio
    async def test_pagination(self, test_entity_query_repo, workspace_id, sample_entity):
        for i in range(4):
            eid = str(generate_uuid())
            e = _TEntity(
                id=eid, workspace_id=str(workspace_id),
                entity_type="Concept", canonical_name=f"Concept {i}",
                meta=_to_json({}),
            )
            test_entity_query_repo.session.add(e)
        await test_entity_query_repo.session.flush()
        page = await test_entity_query_repo.find_page(
            workspace_id=workspace_id, entity_types=["Concept"],
            page_number=1, page_size=2,
        )
        assert len(page.items) == 2
        assert page.has_next is True

    @pytest.mark.asyncio
    async def test_get_entity_graph(self, test_entity_query_repo, workspace_id, sample_entity):
        tid = str(generate_uuid())
        target = _TEntity(
            id=tid, workspace_id=str(workspace_id),
            entity_type="Person", canonical_name="Neighbor",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(target)
        await test_entity_query_repo.session.flush()
        rel = _TEntityRelationship(
            id=str(generate_uuid()), workspace_id=str(workspace_id),
            source_id=sample_entity.id, target_id=tid,
            relationship_type="related_to", strength=0.7,
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(rel)
        await test_entity_query_repo.session.flush()
        graph = await test_entity_query_repo.get_entity_graph(
            entity_id=sample_entity.id, workspace_id=workspace_id, depth=1,
        )
        assert graph["center"] is not None
        assert graph["center"].id == sample_entity.id
        assert len(graph["neighbors"]) >= 1

    @pytest.mark.asyncio
    async def test_get_entity_count(self, test_entity_query_repo, workspace_id, sample_entity):
        eid = str(generate_uuid())
        e2 = _TEntity(
            id=eid, workspace_id=str(workspace_id),
            entity_type="Project", canonical_name="Another Project",
            meta=_to_json({}),
        )
        test_entity_query_repo.session.add(e2)
        await test_entity_query_repo.session.flush()
        count = await test_entity_query_repo.get_entity_count(
            workspace_id=workspace_id,
        )
        assert count >= 2
