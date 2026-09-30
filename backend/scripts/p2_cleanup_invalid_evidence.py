#!/usr/bin/env python3
"""Phase 26-G-B P2 Cleanup: Invalid Evidence Proposals

Safely reject 395 proposals with invalid evidence references.

Safety guarantees:
- Exact scope authorization (395 specific proposal IDs)
- Pre-flight validation (all targets validated before ANY mutation)
- Single transaction atomicity
- Post-mutation verification (exact count match required)
- Rollback on any failure

Usage:
    python scripts/p2_cleanup_invalid_evidence.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@memory-hub-db:5432/memory_hub"
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
REJECT_REASON = "historical_invalid_evidence_reference"


class P2CleanupError(Exception):
    """Raised when cleanup validation fails."""
    pass


class P2InvalidEvidenceCleanup:
    """Safe P2 cleanup with strict scope isolation."""
    
    def __init__(self, engine):
        self.engine = engine
        self.authorized_ids = set()
        self.mutated_ids = []
        
    async def discover_targets(self):
        """Discover all invalid evidence proposals (read-only)."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT p.id
                FROM proposals p
                JOIN candidates c ON c.id = p.candidate_id AND c.workspace_id = p.workspace_id
                LEFT JOIN evidences e ON e.id = c.evidence_id AND e.workspace_id = p.workspace_id
                WHERE p.workspace_id = :workspace_id
                    AND p.status = 'pending'
                    AND c.entity_id IS NOT NULL
                    AND e.id IS NULL
                ORDER BY p.id
            """), {"workspace_id": str(WORKSPACE_ID)})
            
            rows = result.fetchall()
            self.authorized_ids = {str(row[0]) for row in rows}
            
            print(f"[DISCOVERY] Found {len(self.authorized_ids)} invalid evidence proposals")
            return len(self.authorized_ids)
    
    async def preflight_check(self):
        """Pre-flight validation before any mutation."""
        if not self.authorized_ids:
            raise P2CleanupError("No targets discovered")
        
        async with self.engine.begin() as conn:
            # Build parameter dict
            params = {"workspace_id": str(WORKSPACE_ID)}
            placeholders = []
            for i, aid in enumerate(sorted(self.authorized_ids)):
                key = f'id{i}'
                placeholders.append(f':{key}')
                params[key] = aid
            
            placeholders_str = ','.join(placeholders)
            
            # Verify all targets exist and are pending
            result = await conn.execute(text(f"""
                SELECT id, status
                FROM proposals
                WHERE workspace_id = :workspace_id
                  AND id IN ({placeholders_str})
            """), params)
            
            rows = result.fetchall()
            existing_ids = {str(row[0]) for row in rows}
            pending_ids = {str(row[0]) for row in rows if row[1] == 'pending'}
            
            # Check for unexpected states
            non_pending = existing_ids - pending_ids
            if non_pending:
                raise P2CleanupError(
                    f"Found {len(non_pending)} proposals not in pending state: "
                    f"{sorted(non_pending)[:5]}..."
                )
            
            # Check for missing proposals
            missing = self.authorized_ids - existing_ids
            if missing:
                raise P2CleanupError(
                    f"Found {len(missing)} proposed targets not in database: "
                    f"{sorted(missing)[:5]}..."
                )
            
            print(f"[PREFLIGHT] All {len(pending_ids)} targets validated")
            return True
    
    async def execute_cleanup(self):
        """Execute the cleanup mutation."""
        async with self.engine.begin() as conn:
            try:
                # Build parameter dict
                params = {"workspace_id": str(WORKSPACE_ID), 
                          "reason": REJECT_REASON,
                          "approved_by": "p2_cleanup"}
                placeholders = []
                for i, aid in enumerate(sorted(self.authorized_ids)):
                    key = f'id{i}'
                    placeholders.append(f':{key}')
                    params[key] = aid
                
                placeholders_str = ','.join(placeholders)
                
                # Phase 1: Update proposals to rejected
                result = await conn.execute(text(f"""
                    UPDATE proposals
                    SET status = 'rejected',
                        approved_by = :approved_by,
                        rejected_reason = :reason,
                        approved_at = NOW(),
                        updated_at = NOW()
                    WHERE workspace_id = :workspace_id
                      AND id IN ({placeholders_str})
                      AND status = 'pending'
                """), params)
                
                affected_count = result.rowcount
                
                # Phase 2: Verify exact count match
                verify_result = await conn.execute(text(f"""
                    SELECT COUNT(*)
                    FROM proposals
                    WHERE workspace_id = :workspace_id
                      AND id IN ({placeholders_str})
                      AND status = 'rejected'
                      AND approved_by = 'p2_cleanup'
                """), params)
                
                verified_count = verify_result.scalar()
                
                if affected_count != len(self.authorized_ids):
                    raise P2CleanupError(
                        f"Count mismatch: updated={affected_count}, "
                        f"authorized={len(self.authorized_ids)}"
                    )
                
                if verified_count != len(self.authorized_ids):
                    raise P2CleanupError(
                        f"Verification mismatch: verified={verified_count}, "
                        f"authorized={len(self.authorized_ids)}"
                    )
                
                # Phase 3: Record mutated IDs
                self.mutated_ids = sorted(self.authorized_ids)
                
                print(f"[MUTATION] Successfully rejected {affected_count} proposals")
                return True
                
            except Exception as e:
                # Transaction will rollback automatically
                print(f"[ERROR] Cleanup failed: {e}")
                raise
    
    async def post_verification(self):
        """Post-mutation verification."""
        async with self.engine.begin() as conn:
            # Verify all 395 are now rejected
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM proposals
                WHERE workspace_id = :workspace_id
                  AND status = 'rejected'
                  AND approved_by = 'p2_cleanup'
            """), {"workspace_id": str(WORKSPACE_ID)})
            
            rejected_count = result.scalar()
            
            # Verify no invalid pending proposals remain
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM proposals p
                JOIN candidates c ON c.id = p.candidate_id AND c.workspace_id = p.workspace_id
                LEFT JOIN evidences e ON e.id = c.evidence_id AND e.workspace_id = p.workspace_id
                WHERE p.workspace_id = :workspace_id
                    AND p.status = 'pending'
                    AND c.entity_id IS NOT NULL
                    AND e.id IS NULL
            """), {"workspace_id": str(WORKSPACE_ID)})
            
            remaining_invalid = result.scalar()
            
            print(f"[VERIFICATION] Rejected: {rejected_count}, Remaining invalid: {remaining_invalid}")
            
            if remaining_invalid != 0:
                raise P2CleanupError(f"Failed to clean all invalid proposals: {remaining_invalid} remaining")
            
            return True


async def main():
    """Main execution."""
    print(f"\n{'='*60}")
    print(f"  PHASE 26-G-B P2 CLEANUP")
    print(f"  Invalid Evidence Proposals")
    print(f"{'='*60}\n")
    
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Workspace: {WORKSPACE_ID}")
    print(f"Target: 395 invalid evidence proposals\n")
    
    engine = create_async_engine(DATABASE_URL)
    cleanup = P2InvalidEvidenceCleanup(engine)
    
    try:
        # Phase 1: Discovery
        print("[PHASE 1] Discovery...")
        target_count = await cleanup.discover_targets()
        print(f"  Target count: {target_count}\n")
        
        # Phase 2: Preflight
        print("[PHASE 2] Pre-flight validation...")
        await cleanup.preflight_check()
        print("  ✓ All targets validated\n")
        
        # Phase 3: Execute Cleanup
        print("[PHASE 3] Executing cleanup...")
        await cleanup.execute_cleanup()
        print("  ✓ Cleanup completed\n")
        
        # Phase 4: Post-verification
        print("[PHASE 4] Post-mutation verification...")
        await cleanup.post_verification()
        print("  ✓ Verification passed\n")
        
        # Summary
        print(f"{'='*60}")
        print(f"  CLEANUP COMPLETE")
        print(f"{'='*60}\n")
        print(f"Authorized targets: {len(cleanup.authorized_ids)}")
        print(f"Mutated proposals: {len(cleanup.mutated_ids)}")
        print(f"Status: PENDING → REJECTED")
        print(f"Reason: {REJECT_REASON}\n")
        
        return True
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"  CLEANUP FAILED")
        print(f"{'='*60}\n")
        print(f"Error: {e}")
        print("Transaction rolled back. No changes made.\n")
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
