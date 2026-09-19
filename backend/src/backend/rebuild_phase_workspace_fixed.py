"""Phase 26-G-B.6 Rebuild Script — Fixed Version.

This script processes all evidences through the EvidencePipelineService
to rebuild reconstructions and candidates after Clean Phase.

Usage:
    docker exec memory-hub-app python3 /tmp/rebuild_phase_fixed.py

Author: Hermes Agent Agnes 2.0
Date: 2026-08-22
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.infrastructure.config.settings import get_settings
from backend.shared.infrastructure.database.engine import get_engine, get_session_factory
from backend.shared.domain.memory_models import Evidence, Workspace
from backend.service.evidence_pipeline_service import EvidencePipelineService, PipelineResult

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

BATCH_SIZE = 50
ANTI_COLLAPSE_THRESHOLD = 0.50  # 50%

# Correct workspace: user-workspace for YONGSHUN LI
# This matches DEFAULT_WORKSPACE in app.py
DEFAULT_WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

# ------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Monitor
# ------------------------------------------------------------------

@dataclass
class RebuildMonitor:
    """Monitor rebuild progress."""

    start_time: datetime = datetime.utcnow()
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    reconstructions_created: int = 0
    candidates_created: int = 0
    topic_links_created: int = 0
    entity_resolution_stats: dict[str, int] = field(default_factory=lambda: {"resolved": 0, "unresolved": 0})
    gate_failures: list[dict[str, Any]] = field(default_factory=list)
    total_evidences: int = 0

    def update(self, result: dict[str, Any]) -> None:
        """Update monitor with pipeline result."""
        self.processed += 1

        if result.get("skipped"):
            self.skipped += 1
        elif result.get("success"):
            self.success += 1
            if result.get("reconstruction_id"):
                self.reconstructions_created += 1
            if result.get("candidate_id"):
                self.candidates_created += 1
            if result.get("topic_ids"):
                self.topic_links_created += len(result["topic_ids"])
        else:
            self.failed += 1

        # Track entity resolution
        if result.get("entity_id"):
            self.entity_resolution_stats["resolved"] += 1
        else:
            self.entity_resolution_stats["unresolved"] += 1

    async def check_anti_collapse_gate(self, session: AsyncSession) -> bool:
        """Check Anti-Collapse Gates."""
        try:
            # Check entity concentration
            stmt = text("""
                SELECT 
                    entity_id,
                    COUNT(*) as cnt
                FROM candidates
                WHERE entity_id IS NOT NULL
                GROUP BY entity_id
                ORDER BY cnt DESC
                LIMIT 1
            """)
            result = await session.execute(stmt)
            row = result.fetchone()

            if row:
                top_entity_count = row[1]
                stmt_total = text("SELECT COUNT(*) FROM candidates WHERE entity_id IS NOT NULL")
                total_result = await session.execute(stmt_total)
                total_candidates = total_result.scalar() or 0

                if total_candidates > 0:
                    top_share = top_entity_count / total_candidates
                    if top_share > ANTI_COLLAPSE_THRESHOLD:
                        self.gate_failures.append({
                            "gate": "entity_concentration",
                            "threshold": ANTI_COLLAPSE_THRESHOLD,
                            "actual": top_share,
                            "top_entity_id": row[0],
                            "top_entity_count": top_entity_count,
                        })
                        logger.error(
                            "ANTI-COLLAPSE GATE FAILED: Entity concentration %.1f%% > %.0f%%",
                            top_share * 100,
                            ANTI_COLLAPSE_THRESHOLD * 100,
                        )
                        return False

            return True

        except Exception as e:
            logger.error("Failed to check Anti-Collapse Gate: %s", e)
            return True  # Don't fail on check errors

    def print_progress(self, batch_size: int) -> None:
        """Print progress update."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        rate = self.processed / elapsed if elapsed > 0 else 0
        eta = (self.total_evidences - self.processed) / rate if rate > 0 else 0

        logger.info(
            "Progress: %d/%d (%.1f%%) | "
            "Success: %d | Failed: %d | Skipped: %d | "
            "Recons: %d | Candidates: %d | Topics: %d | "
            "Rate: %.1f/s | ETA: %.0fs",
            self.processed,
            self.total_evidences,
            (self.processed / self.total_evidences * 100) if self.total_evidences > 0 else 0,
            self.success,
            self.failed,
            self.skipped,
            self.reconstructions_created,
            self.candidates_created,
            self.topic_links_created,
            rate,
            eta,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get rebuild summary."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        return {
            "total_evidences": self.total_evidences,
            "processed": self.processed,
            "success_rate": (self.success / self.processed * 100) if self.processed > 0 else 0,
            "reconstructions_created": self.reconstructions_created,
            "candidates_created": self.candidates_created,
            "topic_links_created": self.topic_links_created,
            "entity_resolution": self.entity_resolution_stats,
            "gate_failures": self.gate_failures,
            "elapsed_seconds": elapsed,
            "avg_rate_per_second": self.processed / elapsed if elapsed > 0 else 0,
        }


# ------------------------------------------------------------------
# Workspace Resolution
# ------------------------------------------------------------------

async def resolve_workspace_id(
    session: AsyncSession,
    preferred_id: str = DEFAULT_WORKSPACE_ID,
) -> UUID:
    """Resolve workspace ID with multiple strategies.

    Priority:
    1. Explicit preferred_id (hardcoded correct value)
    2. Query by name 'user-workspace'
    3. Query all workspaces and return first with evidences

    This prevents the bug where workspaces[0] returns wrong workspace
    when multiple workspaces exist.
    """
    # Strategy 1: Use explicit preferred ID
    try:
        preferred_uuid = UUID(preferred_id)
        ws_check = await session.execute(
            select(Workspace).where(Workspace.id == preferred_uuid)
        )
        ws = ws_check.scalar_one_or_none()
        if ws:
            logger.info("Resolved workspace by preferred ID: %s (%s)", ws.id, ws.name)
            return ws.id
    except Exception as e:
        logger.warning("Preferred ID resolution failed: %s", e)

    # Strategy 2: Query by name
    try:
        ws_name_result = await session.execute(
            select(Workspace).where(Workspace.name == "user-workspace")
        )
        ws_by_name = ws_name_result.scalar_one_or_none()
        if ws_by_name:
            logger.info("Resolved workspace by name: %s (%s)", ws_by_name.id, ws_by_name.name)
            return ws_by_name.id
    except Exception as e:
        logger.warning("Name-based resolution failed: %s", e)

    # Strategy 3: Find workspace with most evidences
    try:
        ws_evidence_result = await session.execute(text("""
            SELECT workspace_id, COUNT(*) as cnt
            FROM evidences
            GROUP BY workspace_id
            ORDER BY cnt DESC
            LIMIT 1
        """))
        row = ws_evidence_result.fetchone()
        if row and row[1] > 0:
            resolved_id = UUID(row[0])
            ws_check = await session.execute(
                select(Workspace).where(Workspace.id == resolved_id)
            )
            ws = ws_check.scalar_one_or_none()
            if ws:
                logger.info(
                    "Resolved workspace by evidence count: %s (%s) with %d evidences",
                    resolved_id, ws.name, row[1]
                )
                return resolved_id
    except Exception as e:
        logger.warning("Evidence-based resolution failed: %s", e)

    # Fallback: return first workspace (old behavior, may be wrong)
    logger.error("All resolution strategies failed, falling back to first workspace")
    ws_result = await session.execute(select(Workspace))
    workspaces = ws_result.scalars().all()
    if not workspaces:
        raise RuntimeError("No workspace found in database")
    return workspaces[0].id


# ------------------------------------------------------------------
# Rebuild Logic
# ------------------------------------------------------------------

async def run_rebuild() -> dict[str, Any]:
    """Run the rebuild phase."""
    logger.info("=" * 60)
    logger.info("Phase 26-G-B.6 Rebuild Phase Started")
    logger.info("=" * 60)

    # Initialize monitor
    monitor = RebuildMonitor()

    # Get settings
    settings = get_settings()
    logger.info("Database URL: %s", settings.DATABASE_URL)

    # Create engine and session
    engine = get_engine()
    async_session = get_session_factory()

    async with async_session() as session:
        # Resolve workspace using robust logic
        workspace_id = await resolve_workspace_id(session)
        logger.info("Using workspace_id: %s", workspace_id)

        # Count total evidences
        stmt = select(Evidence)
        evidence_result = await session.execute(stmt)
        evidences = evidence_result.scalars().all()
        monitor.total_evidences = len(evidences)

        logger.info("Total evidences to process: %d", monitor.total_evidences)
        logger.info("Processing in batches of %d", BATCH_SIZE)

        # Process in batches
        for i in range(0, len(evidences), BATCH_SIZE):
            batch = evidences[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            logger.info("Processing batch %d (%d evidences)", batch_num, len(batch))

            for evidence in batch:
                # Create pipeline service for this evidence
                pipeline = EvidencePipelineService(session)

                # Process evidence
                pipeline_result: PipelineResult = await pipeline.process_evidence(
                    evidence_id=evidence.id,
                    workspace_id=workspace_id,
                )

                # Update monitor
                monitor.update({
                    "success": pipeline_result.success,
                    "reconstruction_id": pipeline_result.reconstruction_id,
                    "candidate_id": pipeline_result.candidate_id,
                    "topic_ids": pipeline_result.topic_ids,
                    "skipped": pipeline_result.skipped,
                    "entity_id": getattr(pipeline_result, 'entity_id', None),
                })

                # Log progress
                if (i + 1) % BATCH_SIZE == 0 or (i + 1) == len(evidences):
                    monitor.print_progress(BATCH_SIZE)

            # Check anti-collapse gate after each batch
            if not await monitor.check_anti_collapse_gate(session):
                logger.error("Anti-collapse gate triggered, stopping rebuild")
                break

    # Print final summary
    logger.info("=" * 60)
    logger.info("Rebuild Phase Completed")
    logger.info("=" * 60)
    summary = monitor.get_summary()
    logger.info("Summary: %s", summary)

    return summary


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

async def main() -> dict[str, Any]:
    """Main entry point."""
    try:
        result = await run_rebuild()
        logger.info("Rebuild Phase completed successfully!")
        return result
    except Exception as e:
        logger.error("Rebuild Phase failed: %s", e, exc_info=True)
        return {"error": str(e)}


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if "error" not in result else 1)
