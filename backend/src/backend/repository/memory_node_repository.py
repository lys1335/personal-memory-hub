"""MemoryNodeRepository - CRUD for the MemoryNode aggregate.

Manages memory_nodes and memory_evidences tables.
MemoryNode is the aggregate root; MemoryEvidence is a child within the aggregate.

Per 10_9 §4.2 and 09 §09.4.5:
- Aggregate root: MemoryNode
- Child: MemoryEvidence (many-to-many junction with Evidence)
- Memory immutable: no UPDATE/DELETE (correction via new node + relationship)
- Three-score separation: confidence, importance, signal_strength (0.0-1.0)
- Level constraint: L1=Observation, L2=Pattern, L3=Belief
- Status: active, candidate, deprecated, superseded, orphaned
- Source: user, manual, explicit_command, archive_derived, ai_reflect
- evidence_links and contradict_evidence are JSONB arrays

Inherits from BaseRepository but overrides update() and soft_delete() to
enforce memory immutability (corrections via new node creation + relationships).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.base import BaseRepository
from backend.repository.exceptions import (
    IntegrityError as DomainIntegrityError,
)
from backend.repository.exceptions import (
    NotFoundError,
)
from backend.repository.pagination import Page


class MemoryNodeRepository(BaseRepository):
    """Repository for the MemoryNode aggregate.

    Memory nodes are IMMUTABLE: no update or delete. Corrections are made
    by creating a new node with status='superseded' pointing to the old node.
    """

    _model_class: type[Any]
    _table_name = "memory_nodes"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the memory node repository.

        Args:
            session: The SQLAlchemy async session for database operations.
        """
        super().__init__(session)
        from backend.shared.domain.memory_models import MemoryNode

        self._model_class = MemoryNode

    # ------------------------------------------------------------------
    # Immutability Enforcement - Memory cannot be updated or deleted
    # ------------------------------------------------------------------

    async def update(self, entity: Any) -> Any:
        """Memory is immutable: update is prohibited.

        Corrections must be made by creating a new node and linking via
        relationships (CORRECT/SUPERSEDES).

        Raises:
            DomainIntegrityError: Always, because memory cannot be modified.
        """
        raise DomainIntegrityError(
            entity_type="memory_node",
            constraint="Memory is immutable - use new node + relationship for corrections",
        )

    async def soft_delete(self, id: UUID) -> None:
        """Memory is immutable: soft_delete is prohibited.

        Instead, set status='deprecated' or 'superseded' via a new node
        with appropriate relationship.

        Raises:
            DomainIntegrityError: Always.
        """
        raise DomainIntegrityError(
            entity_type="memory_node",
            constraint="Memory is immutable - no DELETE allowed",
        )

    async def soft_delete_impl(self, id: UUID) -> None:
        """Memory is immutable: soft_delete_impl is prohibited.

        Raises:
            DomainIntegrityError: Always.
        """
        raise DomainIntegrityError(
            entity_type="memory_node",
            constraint="Memory is immutable - no soft delete allowed",
        )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(self, entity: Any) -> UUID:
        """Create a new memory node and persist it.

        Args:
            entity: The MemoryNode domain object to create.

        Returns:
            The UUID of the created memory node.

        Raises:
            DomainIntegrityError: If level/type consistency or constraints violated.
            IntegrityError: If a uniqueness or foreign key constraint fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            entity_id = getattr(entity, "id", None)
            if entity_id is None:
                raise DomainIntegrityError(
                    entity_type="memory_node",
                    constraint="Created memory node has no id",
                )
            return UUID(entity_id) if not isinstance(entity_id, UUID) else entity_id
        except IntegrityError as exc:
            self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    # ------------------------------------------------------------------
    # Link Evidence to MemoryNode (aggregate child operation)
    # ------------------------------------------------------------------

    async def link_evidence(
        self,
        *,
        memory_node_id: UUID,
        evidence_id: UUID,
        workspace_id: UUID,
        relationship_type: str = "supports",
        contribution_weight: float = 1.0,
    ) -> UUID:
        """Link an evidence to a memory node (aggregate child operation).

        Creates a MemoryEvidence junction record within the MemoryNode aggregate.

        Args:
            memory_node_id: The memory node UUID.
            evidence_id: The evidence UUID.
            workspace_id: Workspace scope.
            relationship_type: Type of relationship (supports, derived_from,
                contradicts, attenuates).
            contribution_weight: Weight 0.0-1.0 for this evidence link.

        Returns:
            The UUID of the created MemoryEvidence record.

        Raises:
            NotFoundError: If memory_node or evidence not found.
            DomainIntegrityError: If relationship_type or weight invalid.
        """
        from backend.shared.domain.memory_models import MemoryEvidence

        # Verify memory node exists
        mn = await self.find_by_id(memory_node_id)
        if mn is None:
            raise NotFoundError(
                entity_type="memory_node",
                entity_id=str(memory_node_id),
            )

        # Verify evidence exists — FK constraint will catch missing evidence
        # Simpler: just insert and let FK constraint handle it
        evidence_record = MemoryEvidence(
            id=UUID(int=hash((str(workspace_id), str(memory_node_id), str(evidence_id))) % (2**128)),
            workspace_id=workspace_id,
            memory_node_id=memory_node_id,
            evidence_id=evidence_id,
            relationship_type=relationship_type,
            contribution_weight=contribution_weight,
        )

        # Validate relationship_type
        valid_types = ("supports", "derived_from", "contradicts", "attenuates")
        if relationship_type not in valid_types:
            raise DomainIntegrityError(
                entity_type="memory_evidence",
                constraint=f"Invalid relationship_type: {relationship_type}. Must be one of {valid_types}",
            )

        # Validate weight
        if not (0.0 <= contribution_weight <= 1.0):
            raise DomainIntegrityError(
                entity_type="memory_evidence",
                constraint=f"contribution_weight must be 0.0-1.0, got {contribution_weight}",
            )

        try:
            self.session.add(evidence_record)
            await self.session.flush()
            return evidence_record.id  # type: ignore[return-value]
        except IntegrityError as exc:
            self.session.rollback()
            self._raise_integrity_error(exc)
            raise  # pragma: no cover

    async def unlink_evidence(
        self,
        *,
        memory_node_id: UUID,
        evidence_id: UUID,
    ) -> None:
        """Remove an evidence link from a memory node.

        Args:
            memory_node_id: The memory node UUID.
            evidence_id: The evidence UUID to unlink.

        Raises:
            NotFoundError: If the link does not exist.
        """
        from backend.shared.domain.memory_models import MemoryEvidence

        stmt = select(MemoryEvidence).where(
            MemoryEvidence.memory_node_id == memory_node_id,
            MemoryEvidence.evidence_id == evidence_id,
        )
        result = await self.session.execute(stmt)
        link = result.scalar_one_or_none()

        if link is None:
            raise NotFoundError(
                entity_type="memory_evidence",
                entity_id=f"memory_node={memory_node_id}, evidence={evidence_id}",
            )

        await self.session.delete(link)
        await self.session.flush()

    async def get_evidence_links(
        self,
        *,
        memory_node_id: UUID,
    ) -> list[Any]:
        """Get all evidence links for a memory node.

        Args:
            memory_node_id: The memory node UUID.

        Returns:
            List of MemoryEvidence records.
        """
        from backend.shared.domain.memory_models import MemoryEvidence

        stmt = select(MemoryEvidence).where(
            MemoryEvidence.memory_node_id == memory_node_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Read Operations
    # ------------------------------------------------------------------

    async def find_by_entity(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find all memory nodes for a specific entity.

        Args:
            entity_id: The entity UUID.
            workspace_id: Workspace scope.

        Returns:
            List of MemoryNode entities.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.entity_id == entity_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_level(
        self,
        *,
        level: int,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find memory nodes by level (1=Observation, 2=Pattern, 3=Belief).

        Args:
            level: Memory level (1, 2, or 3).
            workspace_id: Workspace scope.

        Returns:
            List of MemoryNode entities at the given level.
        """
        if level not in (1, 2, 3):
            raise DomainIntegrityError(
                entity_type="memory_node",
                constraint=f"Invalid level: {level}. Must be 1, 2, or 3.",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.level == level,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_status(
        self,
        *,
        status: str,
        workspace_id: UUID,
    ) -> list[Any]:
        """Find memory nodes by status.

        Args:
            status: Status (active, candidate, deprecated, superseded, orphaned).
            workspace_id: Workspace scope.

        Returns:
            List of MemoryNode entities with the given status.
        """
        valid_statuses = ("active", "candidate", "deprecated", "superseded", "orphaned")
        if status not in valid_statuses:
            raise DomainIntegrityError(
                entity_type="memory_node",
                constraint=f"Invalid status: {status}. Must be one of {valid_statuses}",
            )

        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.status == status,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_active_by_workspace(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> list[Any]:
        """Find all active memory nodes in a workspace.

        Args:
            workspace_id: Workspace scope.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Column name to order by.
            descending: Descending order flag.

        Returns:
            List of active MemoryNode entities.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
            self._model_class.status == "active",
        )

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_with_evidence_chain(
        self,
        *,
        memory_node_id: UUID,
    ) -> dict[str, Any]:
        """Find a memory node with its full evidence chain.

        Returns the memory node and all linked evidence records.

        Args:
            memory_node_id: The memory node UUID.

        Returns:
            Dict with 'node' (MemoryNode) and 'evidence_chain' (list of dicts
            containing evidence details and relationship info).

        Raises:
            NotFoundError: If the memory node does not exist.
        """
        from backend.shared.domain.memory_models import MemoryEvidence

        node = await self.find_by_id(memory_node_id)
        if node is None:
            raise NotFoundError(
                entity_type="memory_node",
                entity_id=str(memory_node_id),
            )

        # Get evidence links
        evidence_stmt = select(MemoryEvidence).where(
            MemoryEvidence.memory_node_id == memory_node_id
        )
        evidence_result = await self.session.execute(evidence_stmt)
        evidence_links = evidence_result.scalars().all()

        # Build evidence chain
        evidence_chain = []
        for link in evidence_links:
            # Fetch the actual evidence
            from backend.shared.domain.memory_models import Evidence

            ev_result = await self.session.execute(
                select(Evidence).where(Evidence.id == link.evidence_id)
            )
            evidence_record = ev_result.scalar_one_or_none()

            evidence_chain.append({
                "evidence": evidence_record,
                "relationship_type": link.relationship_type,
                "contribution_weight": link.contribution_weight,
            })

        return {
            "node": node,
            "evidence_chain": evidence_chain,
        }

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def find_page(
        self,
        *,
        workspace_id: UUID,
        level: int | None = None,
        status: str | None = None,
        entity_id: UUID | None = None,
        page_number: int = 1,
        page_size: int = 20,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> Page[Any]:
        """Find memory nodes with pagination.

        Args:
            workspace_id: Workspace scope.
            level: Optional filter by level (1, 2, 3).
            status: Optional filter by status.
            entity_id: Optional filter by entity.
            page_number: 1-based page number.
            page_size: Items per page.
            order_by: Column to order by.
            descending: Descending order.

        Returns:
            A Page object with results and metadata.
        """
        offset = (page_number - 1) * page_size
        items = await self.find_all_filtered(
            workspace_id=workspace_id,
            level=level,
            status=status,
            entity_id=entity_id,
            offset=offset,
            limit=page_size + 1,
            order_by=order_by,
            descending=descending,
        )

        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]

        return Page(
            items=items,
            total=None,
            page_number=page_number,
            page_size=page_size,
            has_next=has_next,
            has_prev=page_number > 1,
        )

    async def find_all_filtered(
        self,
        *,
        workspace_id: UUID,
        level: int | None = None,
        status: str | None = None,
        entity_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> list[Any]:
        """Find memory nodes with advanced filtering.

        Args:
            workspace_id: Workspace scope.
            level: Optional level filter.
            status: Optional status filter.
            entity_id: Optional entity filter.
            offset: Number of records to skip.
            limit: Maximum number of records.
            order_by: Column to order by.
            descending: Descending order.

        Returns:
            List of matching MemoryNode entities.
        """
        stmt = select(self._model_class).where(
            self._model_class.workspace_id == workspace_id,
        )

        if level is not None:
            stmt = stmt.where(self._model_class.level == level)
        if status is not None:
            stmt = stmt.where(self._model_class.status == status)
        if entity_id is not None:
            stmt = stmt.where(self._model_class.entity_id == entity_id)

        if order_by and hasattr(self._model_class, order_by):
            order_col = getattr(self._model_class, order_by)
            stmt = stmt.order_by(
                order_col.desc() if descending else order_col.asc()
            )

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _raise_integrity_error(self, exc: IntegrityError) -> None:
        """Map SQLAlchemy IntegrityError to domain exception.

        Args:
            exc: The SQLAlchemy IntegrityError.

        Raises:
            DomainIntegrityError: Always.
        """
        orig = exc.orig
        msg = str(orig) if orig else str(exc)

        if "unique" in msg.lower() or "duplicate" in msg.lower():
            raise DomainIntegrityError(
                entity_type="memory_node",
                constraint=msg[:200],
            )

        raise DomainIntegrityError(
            entity_type="memory_node",
            constraint=msg[:200],
        )
