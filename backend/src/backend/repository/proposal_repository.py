"""Proposal Repository — CRUD operations for reflection proposals.

Per D2.x design: Repository layer owns all data access.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.domain.proposal_model import Proposal

logger = logging.getLogger(__name__)


class ProposalRepository:
    """Repository for Proposal entities.

    Per D4.2d Repository pattern: all DB access goes through here.
    """

    def __init__(self, session_factory):
        """Initialize with SQLAlchemy async session factory."""
        self._session_factory = session_factory

    async def create(self, proposal: dict[str, Any]) -> UUID:
        """Create a new proposal."""
        async with self._session_factory() as session:
            stmt = text("""
                INSERT INTO proposals (
                    id, workspace_id, type, source_level, target_level,
                    entity, evidence_chain, confidence, summary, content,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :type, :source_level, :target_level,
                    :entity, :evidence_chain, :confidence, :summary, :content,
                    :status, NOW(), NOW()
                )
                RETURNING id
            """)
            result = await session.execute(stmt, {
                "id": str(proposal["id"]),
                "workspace_id": str(proposal["workspace_id"]),
                "type": proposal.get("type", "Split"),
                "source_level": proposal.get("source_level", 1),
                "target_level": proposal.get("target_level", 2),
                "entity": proposal.get("entity", "unknown"),
                "evidence_chain": proposal.get("evidence_chain", []),
                "confidence": proposal.get("confidence", 0.5),
                "summary": proposal.get("summary", ""),
                "content": proposal.get("content", ""),
                "status": "pending",
            })
            await session.commit()
            return UUID(result.scalar())

    async def find_by_workspace(
        self,
        workspace_id: UUID,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Proposal]:
        """Find proposals by workspace, optionally filtered by status."""
        async with self._session_factory() as session:
            stmt = text("""
                SELECT id, workspace_id, type, source_level, target_level,
                       entity, evidence_chain, confidence, summary, content,
                       status, created_at, updated_at
                FROM proposals
                WHERE workspace_id = :workspace_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            if status:
                stmt = text("""
                    SELECT id, workspace_id, type, source_level, target_level,
                           entity, evidence_chain, confidence, summary, content,
                           status, created_at, updated_at
                    FROM proposals
                    WHERE workspace_id = :workspace_id
                    AND status = :status
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                result = await session.execute(stmt, {
                    "workspace_id": str(workspace_id),
                    "status": status,
                    "limit": limit,
                })
            else:
                result = await session.execute(stmt, {
                    "workspace_id": str(workspace_id),
                    "limit": limit,
                })

            rows = result.fetchall()
            proposals = []
            for row in rows:
                proposals.append(Proposal(
                    id=UUID(row[0]),
                    workspace_id=UUID(row[1]),
                    type=row[2],
                    source_level=row[3],
                    target_level=row[4],
                    entity=row[5],
                    evidence_chain=row[6],
                    confidence=row[7],
                    summary=row[8],
                    content=row[9],
                    status=row[10],
                    created_at=row[11],
                    updated_at=row[12],
                ))
            return proposals

    async def update_status(self, proposal_id: UUID, status: str) -> bool:
        """Update proposal status."""
        async with self._session_factory() as session:
            stmt = text("""
                UPDATE proposals
                SET status = :status, updated_at = NOW()
                WHERE id = :id
            """)
            result = await session.execute(stmt, {
                "id": str(proposal_id),
                "status": status,
            })
            await session.commit()
            return result.rowcount > 0

    async def clear_processed(self, workspace_id: UUID) -> int:
        """Clear processed (approved/rejected) proposals."""
        async with self._session_factory() as session:
            stmt = text("""
                DELETE FROM proposals
                WHERE workspace_id = :workspace_id
                AND status IN ('approved', 'rejected')
            """)
            result = await session.execute(stmt, {
                "workspace_id": str(workspace_id),
            })
            await session.commit()
            return result.rowcount
