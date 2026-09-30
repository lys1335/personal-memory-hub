#!/usr/bin/env python3
"""Phase 26-G-B Pilot — Using Existing Approval Method.

This script uses the existing ReflectionService.approve_proposal() method
to ensure all safety checks and constraints are properly applied.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@memory-hub-db:5432/memory_hub"
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
BATCH_SIZE = 10


async def run_pilot():
    """Execute controlled pilot approval."""
    from backend.service.reflection_service import ReflectionService

    baseline = await record_baseline()
    
    print(f"\n{'='*60}")
    print(f"  PHASE 26-G-B PILOT (v2)")
    print(f"{'='*60}\n")
    print(f"Using existing ReflectionService.approve_proposal()")
    print(f"Batch Size: {BATCH_SIZE}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Get pilot proposals
    pilot_proposals = await get_pilot_proposals()
    print(f"Pilot Proposals Selected: {len(pilot_proposals)}")
    
    if not pilot_proposals:
        print("\nNo suitable proposals found.")
        return False

    # Create service instance
    service = ReflectionService()
    
    results = []
    approved = 0
    skipped = 0
    failed = 0

    for i, prop in enumerate(pilot_proposals, 1):
        print(f"\n[{i}/{len(pilot_proposals)}] Proposal: {prop['id'][:8]}...")
        print(f"  Level: L{prop['target_level']}, Confidence: {prop['confidence']}")

        try:
            result = await service.approve_proposal(
                workspace_id=UUID(WORKSPACE_ID),
                proposal_id=UUID(prop['id']),
            )
            
            if result.metadata.get('skipped'):
                skipped += 1
                print(f"  ⏭ Skipped: {result.metadata.get('reason', '')}")
            else:
                approved += 1
                print(f"  ✓ Approved: Node {result.metadata.get('new_node_id', 'N/A')[:8]}...")
                
        except Exception as e:
            failed += 1
            print(f"  ✗ Failed: {str(e)[:50]}...")
        
        results.append({
            'proposal_id': prop['id'],
            'success': not result.metadata.get('skipped') if hasattr(result, 'metadata') else False,
            'error': str(e) if 'e' in dir() else None,
        })

    # Record after state
    after = await record_baseline()
    delta = calculate_delta(baseline, after)

    # Summary
    print(f"\n{'='*60}")
    print(f"  PILOT SUMMARY")
    print(f"{'='*60}\n")
    print(f"Total: {len(pilot_proposals)}")
    print(f"Approved: {approved}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print()
    
    print("Database Changes:")
    for metric, change in delta.items():
        if change != 0:
            print(f"  {metric}: {change:+d}")
    print()

    # Verification
    if approved > 0:
        lineage_ok = await verify_lineage()
        print(f"Evidence Lineage: {'✓ PASS' if lineage_ok else '✗ FAIL'}")
    
    print(f"\n{'='*60}")
    success = failed == 0
    print(f"  {'✓ PILOT SUCCESSFUL' if success else '✗ PILOT FAILED'}")
    print(f"{'='*60}\n")

    return success


async def get_pilot_proposals():
    """Get pilot proposals with safety criteria."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT p.id, p.target_level, p.confidence, c.evidence_id, c.entity_id
            FROM proposals p
            JOIN candidates c ON c.id = p.candidate_id
            WHERE p.workspace_id = :ws AND p.status = 'pending'
                AND c.evidence_id IS NOT NULL
                AND EXISTS (SELECT 1 FROM evidences e WHERE e.id = c.evidence_id AND e.workspace_id = :ws)
                AND NOT EXISTS (
                    SELECT 1 FROM memory_nodes mn 
                    WHERE mn.workspace_id = :ws AND mn.entity_id = c.entity_id AND mn.status = 'active'
                )
            ORDER BY p.confidence DESC, p.created_at ASC
            LIMIT :limit
        """), {"ws": WORKSPACE_ID, "limit": BATCH_SIZE})

        rows = result.fetchall()
        proposals = []
        for row in rows:
            proposals.append({
                'id': str(row[0]),
                'target_level': int(row[1]),
                'confidence': float(row[2]),
                'evidence_id': str(row[3]) if row[3] else None,
                'entity_id': str(row[4]) if row[4] else None,
            })

    await engine.dispose()
    return proposals


async def record_baseline():
    """Record database state."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        results = {}
        for name, query in [
            ('proposals_total', "SELECT COUNT(*) FROM proposals WHERE workspace_id = :ws"),
            ('proposals_pending', "SELECT COUNT(*) FROM proposals WHERE workspace_id = :ws AND status = 'pending'"),
            ('proposals_approved', "SELECT COUNT(*) FROM proposals WHERE workspace_id = :ws AND status = 'approved'"),
            ('memory_nodes_total', "SELECT COUNT(*) FROM memory_nodes WHERE workspace_id = :ws"),
            ('memory_nodes_active', "SELECT COUNT(*) FROM memory_nodes WHERE workspace_id = :ws AND status = 'active'"),
            ('memory_evidences_total', "SELECT COUNT(*) FROM memory_evidences"),
        ]:
            r = await conn.execute(text(query), {"ws": WORKSPACE_ID})
            results[name] = r.scalar()
    await engine.dispose()
    return results


def calculate_delta(baseline, after):
    """Calculate changes."""
    return {k: after.get(k, 0) - baseline.get(k, 0) for k in baseline}


async def verify_lineage():
    """Verify evidence lineage for recent nodes."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN evidence_links IS NOT NULL AND evidence_links != '[]'::jsonb THEN 1 END) as has_links
            FROM memory_nodes
            WHERE workspace_id = :ws AND created_at > NOW() - INTERVAL '5 minutes'
        """), {"ws": WORKSPACE_ID})
        row = result.fetchone()
    await engine.dispose()
    return row[1] == row[0] if row else False


if __name__ == "__main__":
    success = asyncio.run(run_pilot())
    sys.exit(0 if success else 1)
