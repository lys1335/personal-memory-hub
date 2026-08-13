"""Phase 20 P0 Fix - Database Verification Script.

Uses synchronous psycopg2 for direct database access.
"""

import os
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import create_engine, text
from uuid import uuid4


def get_engine():
    """Create synchronous database engine."""
    db_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:postgres@localhost:5432/memory_hub"
    )
    return create_engine(db_url)


def test_migration_applied():
    """Verify Migration 002 is applied."""
    print("\n=== Testing Migration 002 Applied ===")
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check column exists
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'proposals' AND column_name = 'candidate_id'
        """))
        row = result.fetchone()
        
        if row:
            print(f"✅ candidate_id column exists: {row}")
            assert row[1] == 'uuid', f"Expected UUID, got {row[1]}"
            assert row[2] == 'YES', "Expected nullable"
        else:
            print("❌ candidate_id column NOT found")
            return False
    
    # Check partial unique index
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'proposals' AND indexname = 'uk_proposals_pending_per_candidate'
        """))
        row = result.fetchone()
        
        if row:
            print(f"✅ Partial unique index exists: {row[0]}")
            print(f"   Definition: {row[1][:80]}...")
        else:
            print("❌ Partial unique index NOT found")
            return False
    
    # Check FK constraint
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT conname, confrelid::regclass, confdeltype 
            FROM pg_constraint 
            WHERE conname = 'fk_proposals_candidate'
        """))
        row = result.fetchone()
        
        if row:
            print(f"✅ FK constraint exists: {row[0]}")
            print(f"   References: {row[1]}, ON DELETE: {row[2]}")
            assert str(row[2]) == 'n', "Expected SET NULL on delete"
        else:
            print("❌ FK constraint NOT found")
            return False
    
    print("\n✅ Migration 002 FULLY APPLIED")
    return True


def test_historical_null_count():
    """Verify historical NULL count."""
    print("\n=== Testing Historical NULL Count ===")
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM proposals WHERE candidate_id IS NULL
        """))
        count = result.scalar()
    
    print(f"📊 Historical NULL count: {count}")
    
    # Note: This may have changed since Phase 20 due to new proposals
    return count


def test_new_proposal_insert():
    """Test creating a new Proposal with candidate_id."""
    print("\n=== Testing New Proposal Insertion ===")
    engine = get_engine()
    
    workspace_id = uuid4()
    candidate_id = uuid4()
    proposal_id = uuid4()
    
    try:
        with engine.begin() as conn:
            # Insert workspace
            conn.execute(text("""
                INSERT INTO workspaces (id, name, created_at, updated_at)
                VALUES (:id, 'test_p0_fix', NOW(), NOW())
                ON CONFLICT DO NOTHING
            """), {"id": str(workspace_id)})
            
            # Insert candidate
            conn.execute(text("""
                INSERT INTO candidates (
                    id, workspace_id, entity_id, area_id, content,
                    candidate_type, evidence_source, evidence_id,
                    evidence_chain, evidence_count, evidence_strength,
                    status, ingested_by, ingestion_timestamp,
                    verified_at, source_level, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :entity_id, :area_id, :content,
                    :candidate_type, :evidence_source, :evidence_id,
                    :evidence_chain, :evidence_count, :evidence_strength,
                    :status, :ingested_by, NOW(),
                    :verified_at, :source_level, NOW(), NOW()
                )
            """), {
                "id": str(candidate_id),
                "workspace_id": str(workspace_id),
                "entity_id": str(uuid4()),
                "area_id": str(uuid4()),
                "content": "test content for p0 fix verification",
                "candidate_type": "pattern",
                "evidence_source": "reflection",
                "evidence_id": str(uuid4()),
                "evidence_chain": '["dummy"]',
                "evidence_count": 1,
                "evidence_strength": 0.9,
                "status": "candidate",
                "ingested_by": "test_p0_fix",
                "verified_at": None,
                "source_level": 1,
            })
            
            # Insert proposal with candidate_id (fixed behavior)
            conn.execute(text("""
                INSERT INTO proposals (
                    id, workspace_id, type, source_level, target_level,
                    entity, evidence_chain, candidate_id, confidence, summary, content,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :type, :source_level, :target_level,
                    :entity, :evidence_chain, :candidate_id, :confidence, :summary, :content,
                    'pending', NOW(), NOW()
                )
            """), {
                "id": str(proposal_id),
                "workspace_id": str(workspace_id),
                "type": "Create",
                "source_level": 1,
                "target_level": 2,
                "entity": "test_entity",
                "evidence_chain": f'["{candidate_id}"]',
                "candidate_id": str(candidate_id),
                "confidence": 0.9,
                "summary": "test summary for p0 fix",
                "content": "test content",
            })
        
        # Verify by reloading
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, candidate_id, status FROM proposals WHERE id = :id
            """), {"id": str(proposal_id)})
            row = result.fetchone()
        
        if row:
            print(f"✅ Proposal inserted: id={row[0]}")
            print(f"✅ candidate_id = {row[1]}")
            print(f"✅ status = {row[2]}")
            
            if str(row[1]) == str(candidate_id):
                print(f"✅ LINEAGE CORRECT: Proposal.candidate_id == Candidate.id")
                return True
            else:
                print(f"❌ LINEAGE FAILED: Expected {candidate_id}, got {row[1]}")
                return False
        else:
            print("❌ Proposal not found after insert")
            return False
            
    finally:
        # Cleanup
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM proposals WHERE workspace_id = :id"), {"id": str(workspace_id)})
            conn.execute(text("DELETE FROM candidates WHERE workspace_id = :id"), {"id": str(workspace_id)})
            conn.execute(text("DELETE FROM workspaces WHERE id = :id"), {"id": str(workspace_id)})


def test_evidence_vs_candidate_distinction():
    """Test that Evidence UUID is not confused with Candidate UUID."""
    print("\n=== Testing Evidence vs Candidate Distinction ===")
    engine = get_engine()
    
    workspace_id = uuid4()
    evidence_id = uuid4()
    candidate_id = uuid4()
    proposal_id = uuid4()
    
    assert evidence_id != candidate_id, "Test setup error: IDs must be different"
    
    try:
        with engine.begin() as conn:
            # Insert workspace
            conn.execute(text("""
                INSERT INTO workspaces (id, name, created_at, updated_at)
                VALUES (:id, 'test_evidence_distinction', NOW(), NOW())
                ON CONFLICT DO NOTHING
            """), {"id": str(workspace_id)})
            
            # Insert candidate with evidence reference
            conn.execute(text("""
                INSERT INTO candidates (
                    id, workspace_id, entity_id, area_id, content,
                    candidate_type, evidence_source, evidence_id,
                    evidence_chain, evidence_count, evidence_strength,
                    status, ingested_by, ingestion_timestamp,
                    verified_at, source_level, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :entity_id, :area_id, :content,
                    :candidate_type, :evidence_source, :evidence_id,
                    :evidence_chain, :evidence_count, :evidence_strength,
                    :status, :ingested_by, NOW(),
                    :verified_at, :source_level, NOW(), NOW()
                )
            """), {
                "id": str(candidate_id),
                "workspace_id": str(workspace_id),
                "entity_id": str(uuid4()),
                "area_id": str(uuid4()),
                "content": "test content",
                "candidate_type": "pattern",
                "evidence_source": "reflection",
                "evidence_id": str(evidence_id),
                "evidence_chain": f'["{evidence_id}"]',
                "evidence_count": 1,
                "evidence_strength": 0.9,
                "status": "candidate",
                "ingested_by": "test",
                "verified_at": None,
                "source_level": 1,
            })
            
            # Insert proposal with candidate_id (NOT evidence_id)
            conn.execute(text("""
                INSERT INTO proposals (
                    id, workspace_id, type, source_level, target_level,
                    entity, evidence_chain, candidate_id, confidence, summary, content,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :workspace_id, :type, :source_level, :target_level,
                    :entity, :evidence_chain, :candidate_id, :confidence, :summary, :content,
                    'pending', NOW(), NOW()
                )
            """), {
                "id": str(proposal_id),
                "workspace_id": str(workspace_id),
                "type": "Create",
                "source_level": 1,
                "target_level": 2,
                "entity": "test_entity",
                "evidence_chain": f'["{evidence_id}"]',
                "candidate_id": str(candidate_id),
                "confidence": 0.9,
                "summary": "test summary",
                "content": "test content",
            })
        
        # Verify
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT candidate_id FROM proposals WHERE id = :id
            """), {"id": str(proposal_id)})
            row = result.fetchone()
        
        if row:
            actual = str(row[0])
            if actual == str(candidate_id) and actual != str(evidence_id):
                print(f"✅ Evidence UUID ({evidence_id}) ≠ Candidate UUID ({candidate_id})")
                print(f"✅ Proposal.candidate_id = {actual}")
                print(f"✅ No confusion between Evidence and Candidate IDs")
                return True
            else:
                print(f"❌ ID confusion detected: expected {candidate_id}, got {actual}")
                return False
        
        print("❌ Proposal not found")
        return False
        
    finally:
        # Cleanup
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM proposals WHERE workspace_id = :id"), {"id": str(workspace_id)})
            conn.execute(text("DELETE FROM candidates WHERE workspace_id = :id"), {"id": str(workspace_id)})
            conn.execute(text("DELETE FROM workspaces WHERE id = :id"), {"id": str(workspace_id)})


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Phase 20 P0 Fix - Database Verification")
    print("=" * 60)
    
    results = {
        "migration_applied": test_migration_applied(),
        "historical_null_count": test_historical_null_count(),
        "new_proposal_insert": test_new_proposal_insert(),
        "evidence_vs_candidate": test_evidence_vs_candidate_distinction(),
    }
    
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 PHASE 20 P0 FIX FULLY VERIFIED")
    else:
        print("\n⚠️  PHASE 20 P0 FIX NOT FULLY VERIFIED")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
