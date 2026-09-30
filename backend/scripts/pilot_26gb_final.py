#!/usr/bin/env python3
"""Phase 26-G-B Pilot — Direct Database Operations with Proper Constraints.

This script approves pending proposals using direct SQL with all safety checks.
No ReflectionService dependency needed.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@memory-hub-db:5432/memory_hub"
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
BATCH_SIZE = 10


async def run_pilot():
    """Execute controlled pilot approval."""
    baseline = await record_baseline()
    
    print(f"\n{'='*60}")
    print(f"  PHASE 26-G-B PILOT (v3)")
    print(f"{'='*60}\n")
    print(f"Batch Size: {BATCH_SIZE}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    pilot_proposals = await get_pilot_proposals()
    print(f"Pilot Proposals Selected: {len(pilot_proposals)}")
    
    if not pilot_proposals:
        print("\nNo suitable proposals found.")
        return False

    results = []
    approved = 0
    skipped = 0
    failed = 0

    for i, prop in enumerate(pilot_proposals, 1):
        print(f"\n[{i}/{len(pilot_proposals)}] Proposal: {prop['id'][:8]}...")
        print(f"  Level: L{prop['target_level']}, Confidence: {prop['confidence']}")

        result = await approve_single_proposal(prop)
        results.append(result)

        if result['success']:
            approved += 1
            print(f"  ✓ Approved: Node {result.get('node_id', 'N/A')[:8]}...")
        elif result['skipped']:
            skipped += 1
            print(f"  ⏭ Skipped: {result.get('reason', '')}")
        else:
            failed += 1
            print(f"  ✗ Failed: {result.get('errors', ['unknown'])[0][:50]}...")

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


async def approve_single_proposal(proposal: dict) -> dict:
    """Approve a single proposal with safety checks."""
    result = {
        'proposal_id': proposal['id'],
        'success': False,
        'skipped': False,
        'errors': [],
        'node_id': None,
    }

    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            # Safety Check 1: Verify proposal exists and is pending
            prop_check = await conn.execute(text("""
                SELECT id, status, candidate_id FROM proposals 
                WHERE id = :id AND workspace_id = :ws
            """), {"id": proposal['id'], "ws": WORKSPACE_ID})
            prop_row = prop_check.fetchone()
            if not prop_row:
                result['skipped'] = True
                result['reason'] = 'Proposal not found'
                return result
            if prop_row[1] != 'pending':
                result['skipped'] = True
                result['reason'] = f'Already processed: {prop_row[1]}'
                return result

            # Safety Check 2: Verify candidate exists
            cand_check = await conn.execute(text("""
                SELECT id, status, evidence_id, entity_id 
                FROM candidates WHERE id = :id
            """), {"id": prop_row[2]})  # candidate_id from proposal row
            cand_row = cand_check.fetchone()
            if not cand_row:
                result['errors'].append('Candidate not found')
                return result

            # Safety Check 3: Verify evidence exists
            if proposal['evidence_id']:
                ev_check = await conn.execute(text("""
                    SELECT id, content FROM evidences 
                    WHERE id = :id AND workspace_id = :ws
                """), {"id": proposal['evidence_id'], "ws": WORKSPACE_ID})
                ev_row = ev_check.fetchone()
                if not ev_row:
                    result['errors'].append(f'Evidence not found: {proposal["evidence_id"]}')
                    return result
                evidence_content = ev_row[1][:500] if ev_row[1] else ""
            else:
                evidence_content = ""

            # Safety Check 4: Check for existing memory node with same entity
            if proposal['entity_id']:
                mn_check = await conn.execute(text("""
                    SELECT id FROM memory_nodes 
                    WHERE workspace_id = :ws AND entity_id = :ent AND status = 'active'
                    LIMIT 1
                """), {"ws": WORKSPACE_ID, "ent": proposal['entity_id']})
                mn_row = mn_check.fetchone()
                if mn_row:
                    result['skipped'] = True
                    result['reason'] = f'Existing memory node: {mn_row[0][:8]}...'
                    return result

            # Execute approval
            from uuid import uuid4
            new_node_id = str(uuid4())
            level = proposal['target_level']
            node_type = "Observation" if level == 1 else "Pattern" if level == 2 else "Belief"
            
            # Build content
            entity_name = proposal['entity_id'][:8] if proposal['entity_id'] else 'Unknown'
            content = f"{entity_name}: {evidence_content[:100]}" if evidence_content else entity_name

            # Insert memory node with correct constraints
            await conn.execute(text("""
                INSERT INTO memory_nodes (
                    id, workspace_id, entity_id, level, node_type, content, summary,
                    confidence, importance, signal_strength, status, source, generated_by,
                    evidence_links, contradict_evidence, _meta, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :entity_id, :level, :node_type, :content, :summary,
                    :confidence, :importance, :signal_strength, 'active', 'ai_reflect', 'ai_reflect',
                    :evidence_links, '[]', :_meta, NOW(), NOW()
                )
            """), {
                "id": new_node_id,
                "workspace_id": WORKSPACE_ID,
                "entity_id": proposal['entity_id'],
                "level": level,
                "node_type": node_type,
                "content": content,
                "summary": content[:200],
                "confidence": proposal['confidence'],
                "importance": proposal['confidence'],
                "signal_strength": proposal['confidence'],
                "evidence_links": json.dumps([proposal['evidence_id']] if proposal['evidence_id'] else []),
                "_meta": json.dumps({
                    "pilot_marker": "phase26g_b",
                    "proposal_id": proposal['id'],
                    "approved_at": datetime.now().isoformat()
                }),
            })

            # Create memory_evidence link
            if proposal['evidence_id']:
                await conn.execute(text("""
                    INSERT INTO memory_evidences (memory_node_id, evidence_id, weight, created_at)
                    VALUES (:mn_id, :ev_id, :weight, NOW())
                    ON CONFLICT DO NOTHING
                """), {
                    "mn_id": new_node_id,
                    "ev_id": proposal['evidence_id'],
                    "weight": proposal['confidence'],
                })

            # Update proposal status
            await conn.execute(text("""
                UPDATE proposals 
                SET status = 'approved', approved_by = 'phase26g_b', approved_at = NOW()
                WHERE id = :id AND status = 'pending'
            """), {"id": proposal['id']})

            # Update candidate status
            await conn.execute(text("""
                UPDATE candidates 
                SET status = 'confirmed', updated_at = NOW()
                WHERE id = :id AND status = 'candidate'
            """), {"id": prop_row[2]})  # candidate_id from proposal row

            result['success'] = True
            result['node_id'] = new_node_id

    except Exception as e:
        result['errors'].append(str(e))
    finally:
        await engine.dispose()

    return result


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
                   COUNT(CASE WHEN evidence_links IS NOT NULL 
                            AND evidence_links != '[]'::jsonb 
                            THEN 1 END) as has_links
            FROM memory_nodes
            WHERE workspace_id = :ws 
                AND _meta->>'pilot_marker' = 'phase26g_b'
        """), {"ws": WORKSPACE_ID})
        row = result.fetchone()
    await engine.dispose()
    return row[1] == row[0] if row else False


if __name__ == "__main__":
    success = asyncio.run(run_pilot())
    sys.exit(0 if success else 1)
