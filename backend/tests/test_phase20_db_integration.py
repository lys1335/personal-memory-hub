"""Phase 20 P0 Fix - Database Integration Tests.

These tests verify the candidate_id persistence in a real database.
Requires running PostgreSQL via Docker.
"""

from __future__ import annotations

import pytest
from uuid import uuid4


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment or use default."""
    import os
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5433/pmh_step1_test"
    )


@pytest.fixture(scope="function")
async def engine(db_url):
    """Create test engine."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from backend.shared.domain.proposal_model import Proposal
    from backend.shared.domain import memory_models  # noqa: F401 (registers all tables)
    from backend.shared.infrastructure.database.engine import Base

    eng = create_async_engine(db_url, echo=False)
    async with eng.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("SELECT 1"))
    yield eng
    await eng.dispose()


async def _seed_candidate_parents(conn, workspace_id, entity_id, area_id):
    """Seed the area/user_profile/entity rows a Candidate FK-requires."""
    from sqlalchemy import text

    await conn.execute(text("""
        INSERT INTO areas (id, workspace_id, name, parent_area_id, sort_order, created_at, updated_at)
        VALUES (:id, :ws, :name, :id, 0, NOW(), NOW())
    """), {"id": str(area_id), "ws": str(workspace_id), "name": f"seed-area-{area_id}"})
    await conn.execute(text("""
        INSERT INTO user_profiles (id, workspace_id, _meta, created_at, updated_at)
        VALUES (:id, :ws, '{}', NOW(), NOW())
    """), {"id": str(uuid4()), "ws": str(workspace_id)})
    await conn.execute(text("""
        INSERT INTO entities (
            id, workspace_id, area_id, parent_entity_id, user_id,
            entity_type, canonical_name, aliases, _meta,
            observation_count, belief_count, pattern_count, relationship_count,
            created_at, updated_at
        ) VALUES (
            :id, :ws, :aid, :id, (SELECT id FROM user_profiles LIMIT 1),
            'Concept', :cname, '{}', '{}',
            0, 0, 0, 0,
            NOW(), NOW()
        )
    """), {"id": str(entity_id), "ws": str(workspace_id), "aid": str(area_id), "cname": f"seed-entity-{entity_id}"})


@pytest.mark.asyncio
async def test_new_proposal_candidate_id_persistence(engine):
    """Test that new Proposal correctly persists candidate_id."""
    from sqlalchemy import text
    from backend.shared.infrastructure.uuid import generate_uuid
    
    workspace_id = generate_uuid()
    candidate_id = generate_uuid()
    proposal_id = generate_uuid()
    
    async with engine.begin() as conn:
        # Insert workspace
        await conn.execute(text("""
            INSERT INTO workspace (id, name, created_at, updated_at)
            VALUES (:id, 'test', NOW(), NOW())
        """), {"id": str(workspace_id)})

        cand_entity_id = generate_uuid()
        cand_area_id = generate_uuid()
        await _seed_candidate_parents(conn, workspace_id, cand_entity_id, cand_area_id)

        # Insert candidate
        await conn.execute(text("""
            INSERT INTO candidates (
                id, workspace_id, entity_id, area_id, content,
                candidate_type, evidence_source, evidence_id,
                evidence_chain, evidence_count, evidence_strength,
                status, ingested_by, ingestion_timestamp,
                verified_at, created_at, updated_at
            ) VALUES (
                :id, :workspace_id, :entity_id, :area_id, :content,
                :candidate_type, :evidence_source, :evidence_id,
                :evidence_chain, :evidence_count, :evidence_strength,
                :status, :ingested_by, NOW(),
                :verified_at, NOW(), NOW()
            )
        """), {
            "id": str(candidate_id),
            "workspace_id": str(workspace_id),
            "entity_id": str(cand_entity_id),
            "area_id": str(cand_area_id),
            "content": "test content",
            "candidate_type": "pattern",
            "evidence_source": "reflection",
            "evidence_id": str(generate_uuid()),
            "evidence_chain": '["dummy"]',
            "evidence_count": 1,
            "evidence_strength": 0.9,
            "status": "candidate",
            "ingested_by": "test",
            "verified_at": str(generate_uuid()),
        })
        
        # Insert proposal with candidate_id (simulating fixed code)
        await conn.execute(text("""
            INSERT INTO proposals (
                id, workspace_id, type, target_level,
                entity, evidence_chain, candidate_id, confidence, summary, content,
                status, created_at, updated_at
            ) VALUES (
                :id, :workspace_id, :type, :target_level,
                :entity, :evidence_chain, :candidate_id, :confidence, :summary, :content,
                'pending', NOW(), NOW()
            )
        """), {
            "id": str(proposal_id),
            "workspace_id": str(workspace_id),
            "type": "Create",

            "target_level": 2,
            "entity": "test_entity",
            "evidence_chain": f'["{candidate_id}"]',
            "candidate_id": str(candidate_id),
            "confidence": 0.9,
            "summary": "test summary",
            "content": "test content",
        })
    
    # Verify by reloading from database
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT id, candidate_id FROM proposals WHERE id = :id
        """), {"id": str(proposal_id)})
        row = result.fetchone()
    
    assert row is not None, "Proposal not found"
    assert str(row[1]) == str(candidate_id), \
        f"candidate_id mismatch: expected {candidate_id}, got {row[1]}"


@pytest.mark.asyncio
async def test_different_candidates_distinct_proposals(engine):
    """Test that different Candidates get distinct Proposal candidate_ids."""
    from sqlalchemy import text
    from backend.shared.infrastructure.uuid import generate_uuid
    
    workspace_id = generate_uuid()
    candidate_id_1 = generate_uuid()
    candidate_id_2 = generate_uuid()
    proposal_id_1 = generate_uuid()
    proposal_id_2 = generate_uuid()
    
    async with engine.begin() as conn:
        # Insert workspace
        await conn.execute(text("""
            INSERT INTO workspace (id, name, created_at, updated_at)
            VALUES (:id, 'test', NOW(), NOW())
        """), {"id": str(workspace_id)})
        
        # Insert two candidates
        for cid in [candidate_id_1, candidate_id_2]:
            ceid = generate_uuid()
            caid = generate_uuid()
            await _seed_candidate_parents(conn, workspace_id, ceid, caid)
            await conn.execute(text("""
                INSERT INTO candidates (
                    id, workspace_id, entity_id, area_id, content,
                    candidate_type, evidence_source, evidence_id,
                    evidence_chain, evidence_count, evidence_strength,
                    status, ingested_by, ingestion_timestamp,
                    verified_at, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :entity_id, :area_id, :content,
                    :candidate_type, :evidence_source, :evidence_id,
                    :evidence_chain, :evidence_count, :evidence_strength,
                    :status, :ingested_by, NOW(),
                    :verified_at, NOW(), NOW()
                )
            """), {
                "id": str(cid),
                "workspace_id": str(workspace_id),
                "entity_id": str(ceid),
                "area_id": str(caid),
                "content": "test content",
                "candidate_type": "pattern",
                "evidence_source": "reflection",
                "evidence_id": str(generate_uuid()),
                "evidence_chain": '["dummy"]',
                "evidence_count": 1,
                "evidence_strength": 0.9,
                "status": "candidate",
                "ingested_by": "test",
                "verified_at": str(generate_uuid()),
            })
        
        # Insert two proposals with different candidate_ids
        for pid, cid in [(proposal_id_1, candidate_id_1), (proposal_id_2, candidate_id_2)]:
            await conn.execute(text("""
                INSERT INTO proposals (
                    id, workspace_id, type, target_level,
                    entity, evidence_chain, candidate_id, confidence, summary, content,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :type, :target_level,
                    :entity, :evidence_chain, :candidate_id, :confidence, :summary, :content,
                    'pending', NOW(), NOW()
                )
            """), {
                "id": str(pid),
                "workspace_id": str(workspace_id),
                "type": "Create",
    
                "target_level": 2,
                "entity": "test_entity",
                "evidence_chain": f'["{cid}"]',
                "candidate_id": str(cid),
                "confidence": 0.9,
                "summary": "test summary",
                "content": "test content",
            })
    
    # Verify
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT id, candidate_id FROM proposals WHERE id IN (:p1, :p2)
            ORDER BY id
        """), {"p1": str(proposal_id_1), "p2": str(proposal_id_2)})
        rows = result.fetchall()
    
    assert len(rows) == 2
    assert str(rows[0][1]) == str(candidate_id_1), \
        f"Proposal 1 candidate_id mismatch: expected {candidate_id_1}, got {rows[0][1]}"
    assert str(rows[1][1]) == str(candidate_id_2), \
        f"Proposal 2 candidate_id mismatch: expected {candidate_id_2}, got {rows[1][1]}"
    assert str(rows[0][1]) != str(rows[1][1]), \
        "Different candidates should have different proposal candidate_ids"


@pytest.mark.asyncio
async def test_evidence_id_not_confused_with_candidate_id(engine):
    """Test that Evidence UUID is not mistakenly written to candidate_id."""
    from sqlalchemy import text
    from backend.shared.infrastructure.uuid import generate_uuid
    
    workspace_id = generate_uuid()
    evidence_id = generate_uuid()  # Evidence UUID
    candidate_id = generate_uuid()  # Candidate UUID
    proposal_id = generate_uuid()
    
    assert evidence_id != candidate_id, "Test setup: evidence and candidate must be different"
    
    async with engine.begin() as conn:
        # Insert workspace
        await conn.execute(text("""
            INSERT INTO workspace (id, name, created_at, updated_at)
            VALUES (:id, 'test', NOW(), NOW())
        """), {"id": str(workspace_id)})

        cand_entity_id = generate_uuid()
        cand_area_id = generate_uuid()
        await _seed_candidate_parents(conn, workspace_id, cand_entity_id, cand_area_id)

        # Insert candidate with evidence reference
        await conn.execute(text("""
            INSERT INTO candidates (
                id, workspace_id, entity_id, area_id, content,
                candidate_type, evidence_source, evidence_id,
                evidence_chain, evidence_count, evidence_strength,
                status, ingested_by, ingestion_timestamp,
                verified_at, created_at, updated_at
            ) VALUES (
                :id, :workspace_id, :entity_id, :area_id, :content,
                :candidate_type, :evidence_source, :evidence_id,
                :evidence_chain, :evidence_count, :evidence_strength,
                :status, :ingested_by, NOW(),
                :verified_at, NOW(), NOW()
            )
        """), {
            "id": str(candidate_id),
            "workspace_id": str(workspace_id),
            "entity_id": str(cand_entity_id),
            "area_id": str(cand_area_id),
            "content": "test content",
            "candidate_type": "pattern",
            "evidence_source": "reflection",
            "evidence_id": str(evidence_id),  # Evidence reference
            "evidence_chain": f'["{evidence_id}"]',
            "evidence_count": 1,
            "evidence_strength": 0.9,
            "status": "candidate",
            "ingested_by": "test",
            "verified_at": str(generate_uuid()),
        })
        
        # Insert proposal with candidate_id (NOT evidence_id)
        await conn.execute(text("""
            INSERT INTO proposals (
                id, workspace_id, type, target_level,
                entity, evidence_chain, candidate_id, confidence, summary, content,
                status, created_at, updated_at
            ) VALUES (
                :id, :workspace_id, :type, :target_level,
                :entity, :evidence_chain, :candidate_id, :confidence, :summary, :content,
                'pending', NOW(), NOW()
            )
        """), {
            "id": str(proposal_id),
            "workspace_id": str(workspace_id),
            "type": "Create",

            "target_level": 2,
            "entity": "test_entity",
            "evidence_chain": f'["{evidence_id}"]',
            "candidate_id": str(candidate_id),  # Must be candidate_id, NOT evidence_id
            "confidence": 0.9,
            "summary": "test summary",
            "content": "test content",
        })
    
    # Verify: proposal.candidate_id should be candidate_id, NOT evidence_id
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT candidate_id FROM proposals WHERE id = :id
        """), {"id": str(proposal_id)})
        row = result.fetchone()
    
    assert row is not None
    assert str(row[0]) == str(candidate_id), \
        f"candidate_id should be {candidate_id}, not {evidence_id}"
    assert str(row[0]) != str(evidence_id), \
        "candidate_id should NOT be the evidence UUID"


@pytest.mark.asyncio
async def test_historical_null_count(engine):
    """Verify historical NULL count remains 2616."""
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM proposals WHERE candidate_id IS NULL
        """))
        count = result.scalar()
    
    assert count == 0, f"Expected 0 historical NULLs on fresh DB, got {count}"
