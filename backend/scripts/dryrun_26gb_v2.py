#!/usr/bin/env python3
"""Phase 26-G-B Dry-run — Corrected Evidence Chain Validation.

This script simulates the approval process for 10 proposals without
actually modifying any database state. It verifies all safety gates.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@memory-hub-db:5432/memory_hub"
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"


async def run_dry_run():
    """Execute simulated approval for 10 proposals."""
    
    # Record baseline
    baseline = await record_baseline()
    
    print(f"\n{'='*60}")
    print(f"  PHASE 26-G-B DRY-RUN (Corrected)")
    print(f"{'='*60}\n")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: SIMULATION ONLY — No database mutations")
    print()
    
    # Select 10 candidates
    candidates = await get_dryrun_candidates()
    print(f"Dry-run Candidates Selected: {len(candidates)}")
    print()
    
    if not candidates:
        print("No suitable candidates for dry-run.")
        return False
    
    results = []
    all_gates_pass = True
    
    for i, cand in enumerate(candidates, 1):
        print(f"\n[{i}/{len(candidates)}] Proposal: {cand['proposal_id'][:8]}...")
        
        result = await simulate_approval(cand, baseline)
        results.append(result)
        
        # Check gates
        gate_pass = all(result.get(gate, False) for gate in [
            'evidence_lineage', 'entity_boundary', 'workspace_isolation',
            'existing_memory_check', 'duplicate_safety', 'state_transition'
        ])
        
        if gate_pass:
            print(f"  ✓ ALL GATES PASS")
        else:
            print(f"  ✗ GATE FAIL:")
            for gate, passed in result.items():
                if gate.endswith('_gate') and not passed:
                    print(f"    - {gate}: FAIL")
            all_gates_pass = False
    
    # Verify no mutations
    after = await record_baseline()
    delta = calculate_delta(baseline, after)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  DRY-RUN SUMMARY")
    print(f"{'='*60}\n")
    print(f"Total Processed: {len(candidates)}")
    print(f"Gates Pass: {sum(1 for r in results if all(r.get(g, False) for g in ['evidence_lineage', 'entity_boundary', 'workspace_isolation']))}/{len(candidates)}")
    print()
    
    print("Database Mutations (should be 0):")
    for metric, change in delta.items():
        status = "✓" if change == 0 else "✗"
        print(f"  {status} {metric}: {change:+d}")
    print()
    
    print(f"{'='*60}")
    success = all_gates_pass and all(v == 0 for v in delta.values())
    print(f"  {'✓ DRY-RUN SUCCESSFUL' if success else '✗ DRY-RUN FAILED'}")
    print(f"{'='*60}\n")
    
    return success


async def get_dryrun_candidates():
    """Get 10 candidates for dry-run."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                p.id as proposal_id,
                p.target_level,
                p.confidence,
                c.id as candidate_id,
                c.entity_id,
                c.evidence_chain,
                c.status as candidate_status
            FROM proposals p
            JOIN candidates c ON c.id = p.candidate_id
            LEFT JOIN memory_nodes mn ON mn.workspace_id = p.workspace_id 
                AND mn.entity_id = c.entity_id 
                AND mn.status = 'active'
            WHERE p.workspace_id = :ws
                AND p.status = 'pending'
                AND c.entity_id IS NOT NULL
                AND c.evidence_chain IS NOT NULL
                AND jsonb_array_length(c.evidence_chain) > 0
                AND mn.id IS NULL
            ORDER BY p.confidence DESC, p.created_at ASC
            LIMIT 10
        """), {"ws": WORKSPACE_ID})
        
        rows = result.fetchall()
        candidates = []
        for row in rows:
            evidence_chain = row[5]
            if isinstance(evidence_chain, str):
                evidence_chain = json.loads(evidence_chain)
            candidates.append({
                'proposal_id': str(row[0]),
                'target_level': int(row[1]),
                'confidence': float(row[2]),
                'candidate_id': str(row[3]),
                'entity_id': str(row[4]) if row[4] else None,
                'evidence_chain': evidence_chain if isinstance(evidence_chain, list) else [],
                'candidate_status': row[6],
            })
    
    await engine.dispose()
    return candidates


async def simulate_approval(candidate: dict, baseline: dict) -> dict:
    """Simulate approval without database changes."""
    result = {
        'proposal_id': candidate['proposal_id'],
        'evidence_lineage_gate': False,
        'entity_boundary_gate': False,
        'workspace_isolation_gate': False,
        'existing_memory_check': False,
        'duplicate_safety_gate': False,
        'state_transition_gate': False,
    }
    
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.connect() as conn:
            # Gate 1: Evidence Lineage
            if await verify_evidence_lineage(conn, candidate):
                result['evidence_lineage_gate'] = True
                print(f"    ✓ Evidence Lineage: PASS")
            else:
                print(f"    ✗ Evidence Lineage: FAIL")
            
            # Gate 2: Entity Boundary
            if await verify_entity_boundary(conn, candidate):
                result['entity_boundary_gate'] = True
                print(f"    ✓ Entity Boundary: PASS")
            else:
                print(f"    ✗ Entity Boundary: FAIL")
            
            # Gate 3: Workspace Isolation
            if await verify_workspace_isolation(conn, candidate):
                result['workspace_isolation_gate'] = True
                print(f"    ✓ Workspace Isolation: PASS")
            else:
                print(f"    ✗ Workspace Isolation: FAIL")
            
            # Gate 4: Existing Memory Check
            if await verify_no_existing_memory(conn, candidate):
                result['existing_memory_check'] = True
                print(f"    ✓ Existing Memory Check: PASS")
            else:
                print(f"    ✗ Existing Memory Check: FAIL")
            
            # Gate 5: Duplicate Safety
            if await verify_no_duplicates(conn, candidate):
                result['duplicate_safety_gate'] = True
                print(f"    ✓ Duplicate Safety: PASS")
            else:
                print(f"    ✗ Duplicate Safety: FAIL")
            
            # Gate 6: State Transition
            if await verify_state_transition(candidate):
                result['state_transition_gate'] = True
                print(f"    ✓ State Transition: PASS")
            else:
                print(f"    ✗ State Transition: FAIL")
                
    finally:
        await engine.dispose()
    
    return result


async def verify_evidence_lineage(conn, candidate: dict) -> bool:
    """Verify evidence lineage: Candidate → Evidence chain."""
    try:
        # Check each evidence in chain exists
        for ev_id in candidate['evidence_chain']:
            if not ev_id or ev_id == '""':
                continue
            result = await conn.execute(text("""
                SELECT id FROM evidences 
                WHERE id = :id AND workspace_id = :ws
            """), {"id": ev_id, "ws": WORKSPACE_ID})
            if not result.fetchone():
                return False
        return len(candidate['evidence_chain']) > 0
    except Exception:
        return False


async def verify_entity_boundary(conn, candidate: dict) -> bool:
    """Verify entity boundary using CORRECTED rule."""
    try:
        # CORRECT: Only check candidate.entity_id IS NOT NULL
        # Evidence.entity_id can be NULL (architecture allows this)
        return candidate['entity_id'] is not None
    except Exception:
        return False


async def verify_workspace_isolation(conn, candidate: dict) -> bool:
    """Verify workspace isolation."""
    try:
        result = await conn.execute(text("""
            SELECT workspace_id FROM proposals WHERE id = :id
        """), {"id": candidate['proposal_id']})
        row = result.fetchone()
        return row and str(row[0]) == WORKSPACE_ID
    except Exception:
        return False


async def verify_no_existing_memory(conn, candidate: dict) -> bool:
    """Verify no existing active memory node for this entity."""
    try:
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM memory_nodes 
            WHERE workspace_id = :ws AND entity_id = :ent AND status = 'active'
        """), {"ws": WORKSPACE_ID, "ent": candidate['entity_id']})
        return result.scalar() == 0
    except Exception:
        return False


async def verify_no_duplicates(conn, candidate: dict) -> bool:
    """Verify no duplicate evidence references."""
    try:
        # Check if any evidence in chain is used by other pending proposals
        for ev_id in candidate['evidence_chain']:
            if not ev_id or ev_id == '""':
                continue
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM proposals p
                JOIN candidates c ON c.id = p.candidate_id
                WHERE p.workspace_id = :ws
                    AND p.status = 'pending'
                    AND p.id != :pid
                    AND :ev_id = ANY(c.evidence_chain)
            """), {"ws": WORKSPACE_ID, "pid": candidate['proposal_id'], "ev_id": ev_id})
            if result.scalar() > 0:
                return False
        return True
    except Exception:
        return False


async def verify_state_transition(candidate: dict) -> bool:
    """Verify state transition is legal."""
    try:
        # Proposal: pending → approved
        # Candidate: candidate → confirmed
        # MemoryNode: (new) → active
        return candidate['candidate_status'] == 'candidate'
    except Exception:
        return False


async def record_baseline():
    """Record current database state."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        results = {}
        for name, query in [
            ('proposals_total', "SELECT COUNT(*) FROM proposals WHERE workspace_id = :ws"),
            ('proposals_pending', "SELECT COUNT(*) FROM proposals WHERE workspace_id = :ws AND status = 'pending'"),
            ('candidates_total', "SELECT COUNT(*) FROM candidates WHERE workspace_id = :ws"),
            ('memory_nodes_total', "SELECT COUNT(*) FROM memory_nodes WHERE workspace_id = :ws"),
            ('memory_evidences_total', "SELECT COUNT(*) FROM memory_evidences"),
        ]:
            r = await conn.execute(text(query), {"ws": WORKSPACE_ID})
            results[name] = r.scalar()
    await engine.dispose()
    return results


def calculate_delta(baseline: dict, after: dict) -> dict:
    """Calculate changes."""
    return {k: after.get(k, 0) - baseline.get(k, 0) for k in baseline}


async def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("  PHASE 26-G-B DRY-RUN EXECUTION")
    print("="*60 + "\n")
    
    success = await run_dry_run()
    
    print("\n" + "="*60)
    if success:
        print("  ✓ DRY-RUN SUCCESSFUL — Ready for Pilot Authorization")
    else:
        print("  ✗ DRY-RUN FAILED — Cannot proceed to Pilot")
    print("="*60 + "\n")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
