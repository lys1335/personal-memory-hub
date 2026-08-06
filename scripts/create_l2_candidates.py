"""基于L2节点创建Candidates用于L2→L3演化"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
import json
from datetime import datetime
from sqlalchemy import text
from backend.shared.infrastructure.database.engine import get_engine
from backend.shared.infrastructure.uuid import generate_uuid

WORKSPACE_ID = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'

async def create_l2_candidates():
    engine = get_engine()
    async with engine.begin() as conn:
        # Query all L2 nodes
        result = await conn.execute(text("""
            SELECT id, content, evidence_links
            FROM memory_nodes
            WHERE workspace_id = :workspace_id AND level = 2
            ORDER BY created_at DESC
        """), {"workspace_id": WORKSPACE_ID})
        
        rows = result.fetchall()
        print(f"Found {len(rows)} L2 nodes")
        
        if len(rows) < 3:
            print("Need at least 3 L2 nodes to create candidates for L2→L3 evolution")
            return
        
        # Create candidates for L2→L3 evolution
        # Group nodes into batches of 3-5
        batch_size = 4
        created = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            if len(batch) < 2:
                continue
            
            candidate_id = str(generate_uuid())
            now = datetime.utcnow()
            
            # Use a dummy entity_id since L2 nodes don't have entity_id
            entity_id = str(generate_uuid())
            
            content = f"实体L2记忆组 ({len(batch)}条):\n"
            node_ids = []
            for row in batch:
                node_ids.append(str(row[0]))
                content += f"记忆: {row[1][:100] if row[1] else 'N/A'}\n"
            
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
                    'pattern', 'ai_reflect', :evidence_id,
                    :evidence_chain, :evidence_count, 0.85,
                    'pending', 'system', :ingestion_timestamp,
                    :verified_at, :created_at, :updated_at
                )
            """), {
                "id": candidate_id,
                "workspace_id": WORKSPACE_ID,
                "entity_id": entity_id,
                "area_id": None,
                "content": content,
                "candidate_type": "pattern",
                "evidence_source": "ai_reflect",
                "evidence_id": node_ids[0],
                "evidence_chain": json.dumps(node_ids),
                "evidence_count": len(node_ids),
                "ingestion_timestamp": now,
                "verified_at": str(generate_uuid()),
                "created_at": now,
                "updated_at": now,
            })
            created += 1
            print(f"  Created candidate {created} with {len(batch)} L2 nodes")
        
        print(f"\n✅ Created {created} candidates for L2→L3 evolution")

if __name__ == "__main__":
    asyncio.run(create_l2_candidates())