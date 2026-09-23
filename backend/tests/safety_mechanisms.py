"""
Phase 26-G-C-D: Cron Safety Mechanisms Implementation

This module adds pre-flight, in-flight, and post-flight safety checks
to the Cron execution pipeline to prevent invalid data generation.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import text

logger = logging.getLogger(__name__)


class CronSafetyValidator:
    """Validates Cron execution safety before, during, and after execution."""

    # Thresholds (configurable via environment)
    MAX_INVALID_LINEAGE_PER_RUN = int(os.environ.get('PMH_MAX_INVALID_LINEAGE', '5'))
    MAX_MUTATIONS_PER_BATCH = int(os.environ.get('PMH_MAX_MUTATIONS_PER_BATCH', '100'))
    CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get('PMH_CB_THRESHOLD', '3'))

    def __init__(self, engine: Optional[Any] = None):
        self.engine = engine
        self.failure_counter = 0
        self.audit_log: List[Dict[str, Any]] = []

    async def pre_flight_check(
        self,
        workspace_id: UUID,
        task_id: str,
    ) -> Tuple[bool, str]:
        """
        Pre-flight validation before Cron execution.
        
        Returns:
            (is_valid, reason)
        """
        # Check engine first
        if not self.engine:
            return False, "No database engine available"

        async with self.engine.begin() as conn:
            # 1. Validate workspace exists
            ws_check = await conn.execute(text("""
                SELECT COUNT(*) FROM workspaces WHERE id = :id LIMIT 1
            """), {"id": str(workspace_id)})
            if ws_check.scalar() == 0:
                return False, f"Workspace {workspace_id} not found"

            # 2. Check AUTO_APPROVE status (must be disabled)
            auto_approve = os.environ.get('AUTO_APPROVE', 'false').lower()
            if auto_approve == 'true':
                return False, "AUTO_APPROVE is enabled - safety violation"

            # 3. Check for existing invalid evidence references
            invalid_count = await conn.execute(text("""
                SELECT COUNT(*)
                FROM proposals p
                JOIN candidates c ON c.id = p.candidate_id 
                    AND c.workspace_id = p.workspace_id
                LEFT JOIN evidences e ON e.id = c.evidence_id 
                    AND e.workspace_id = p.workspace_id
                WHERE p.workspace_id = :workspace_id
                  AND p.status = 'pending'
                  AND c.entity_id IS NOT NULL
                  AND e.id IS NULL
            """), {"workspace_id": str(workspace_id)})
            
            invalid_pending = invalid_count.scalar() or 0
            
            # Log warning if invalid count exceeds threshold
            if invalid_pending > self.MAX_INVALID_LINEAGE_PER_RUN:
                logger.warning(
                    f"[SAFETY] High invalid lineage count: {invalid_pending} "
                    f"(threshold: {self.MAX_INVALID_LINEAGE_PER_RUN})"
                )

            # 4. Verify entity boundary integrity
            orphaned_count = await conn.execute(text("""
                SELECT COUNT(*)
                FROM candidates c
                WHERE c.workspace_id = :workspace_id
                  AND c.entity_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM entities e 
                      WHERE e.id = c.entity_id 
                        AND e.workspace_id = c.workspace_id
                  )
            """), {"workspace_id": str(workspace_id)})
            
            if orphaned_count.scalar() > 0:
                logger.warning(
                    f"[SAFETY] Found {orphaned_count.scalar()} orphaned candidates"
                )

        # Record audit entry
        audit_entry = {
            "type": "pre_flight",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "workspace_id": str(workspace_id),
            "invalid_pending": invalid_pending,
            "auto_approve_enabled": auto_approve == 'true',
            "status": "passed",
        }
        self.audit_log.append(audit_entry)
        logger.info(f"[SAFETY] Pre-flight check passed for task {task_id}")

        return True, "All checks passed"

    async def validate_batch_safety(
        self,
        workspace_id: UUID,
        batch_candidates: List[Dict[str, Any]],
        batch_id: int,
    ) -> Tuple[bool, str]:
        """
        Validate batch before execution.
        
        Returns:
            (is_valid, reason)
        """
        if len(batch_candidates) > self.MAX_MUTATIONS_PER_BATCH:
            return False, f"Batch size {len(batch_candidates)} exceeds limit {self.MAX_MUTATIONS_PER_BATCH}"

        # If no engine, cannot validate evidence existence
        if not self.engine:
            return True, "Engine not available, skipping evidence validation"

        valid_ids = []
        invalid_ids = []

        async with self.engine.begin() as conn:
            for candidate in batch_candidates:
                evidence_id = candidate.get("evidence_id")
                if not evidence_id:
                    invalid_ids.append({"id": candidate.get("id"), "reason": "missing_evidence_id"})
                    continue

                check = await conn.execute(text("""
                    SELECT 1 FROM evidences 
                    WHERE id = :eid AND workspace_id = :wid LIMIT 1
                """), {"eid": str(evidence_id), "wid": str(workspace_id)})

                if check.fetchone():
                    valid_ids.append(candidate)
                else:
                    invalid_ids.append({
                        "id": candidate.get("id"),
                        "evidence_id": evidence_id,
                        "reason": "evidence_not_found"
                    })

        if invalid_ids:
            logger.warning(
                f"[SAFETY] Batch {batch_id}: {len(invalid_ids)} invalid candidates "
                f"out of {len(batch_candidates)}"
            )
            return False, f"{len(invalid_ids)} invalid candidates found"

        return True, f"All {len(valid_ids)} candidates valid"

    async def validate_post_flight(
        self,
        workspace_id: UUID,
        expected_proposal_ids: Set[str],
        expected_candidate_ids: Set[str],
        actual_proposal_ids: Set[str],
        actual_candidate_ids: Set[str],
        run_id: str,
    ) -> Tuple[bool, str]:
        """
        Validate execution results after batch completion.
        
        Returns:
            (is_valid, reason)
        """
        issues = []

        # Check expected vs actual proposals
        missing_proposals = expected_proposal_ids - actual_proposal_ids
        extra_proposals = actual_proposal_ids - expected_proposal_ids
        
        if missing_proposals:
            issues.append(f"{len(missing_proposals)} expected proposals not created")
        if extra_proposals:
            issues.append(f"{len(extra_proposals)} unexpected proposals created")

        # Validate candidate evidence lineage if engine available
        if self.engine:
            async with self.engine.begin() as conn:
                for candidate_id in actual_candidate_ids:
                    check = await conn.execute(text("""
                        SELECT c.evidence_id, e.id
                        FROM candidates c
                        LEFT JOIN evidences e ON e.id = c.evidence_id AND e.workspace_id = c.workspace_id
                        WHERE c.id = :cid AND c.workspace_id = :wid
                    """), {"cid": candidate_id, "wid": str(workspace_id)})
                    
                    row = check.fetchone()
                    if row and row[0]:  # evidence_id exists
                        if not row[1]:  # but corresponding evidence not found
                            issues.append(f"Candidate {candidate_id} has invalid evidence reference")

        if issues:
            return False, "; ".join(issues)
        return True, "All post-flight checks passed"

    async def record_failure(self, reason: str, run_id: str) -> bool:
        """Record a safety failure and check circuit breaker.
        
        Returns True if circuit breaker triggered.
        """
        self.failure_counter += 1
        logger.error(f"[SAFETY] Failure #{self.failure_counter}: {reason}")
        
        audit_entry = {
            "type": "failure",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "failure_count": self.failure_counter,
            "reason": reason,
        }
        self.audit_log.append(audit_entry)

        if self.failure_counter >= self.CIRCUIT_BREAKER_THRESHOLD:
            logger.critical(
                f"[SAFETY] Circuit breaker triggered! "
                f"Consecutive failures: {self.failure_counter}"
            )
            return True  # Signal to disable cron
        return False

    async def reset_failure_counter(self) -> None:
        """Reset failure counter on successful run."""
        if self.failure_counter > 0:
            logger.info(f"[SAFETY] Resetting failure counter ({self.failure_counter} -> 0)")
            self.failure_counter = 0
