"""从现有Entities创建Candidates"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
import uuid
import time
import json
from datetime import datetime
from sqlalchemy import text
from backend.shared.infrastructure.database.engine import get_engine

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

def generate_uuid_v7():
    timestamp_ms = int(time.time() * 1000)
    ts_part = timestamp_ms & 0xFFFFFFFFFFFF
    random_part = uuid.uuid4().int & 0xFFFFFFFFFFFF
    uuid_int = (ts_part << 48) | (0x7 << 44) | (0x2 << 42) | random_part
    return str(uuid.UUID(int=uuid_int))

async def main():
    print("📊 开始创建Candidates...")
    
    engine = get_engine()
    
    # 查询所有entity和对应的evidence
    print("📝 查询entities和evidences...")
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT 
                e.id as entity_id,
                e.area_id,
                e.canonical_name,
                ev.id as evidence_id
            FROM entities e
            JOIN evidences ev ON ev.workspace_id = e.workspace_id AND ev.entity_id = e.id
            WHERE e.workspace_id = :ws_id
            ORDER BY e.canonical_name, ev.created_at
            LIMIT 500
        """), {"ws_id": WORKSPACE_ID})
        
        rows = result.fetchall()
        print(f"  找到 {len(rows)} 条evidence记录")
    
    # 按entity分组
    entity_evidences = {}
    for entity_id, area_id, entity_name, evidence_id in rows:
        if entity_id not in entity_evidences:
            entity_evidences[entity_id] = {
                'area_id': area_id,
                'entity_name': entity_name,
                'evidence_ids': []
            }
        entity_evidences[entity_id]['evidence_ids'].append(str(evidence_id))
    
    print(f"  涉及 {len(entity_evidences)} 个entity")
    
    # 创建candidates
    created = 0
    async with engine.begin() as conn:
        for entity_id, data in list(entity_evidences.items())[:100]:  # 限制100个
            try:
                candidate_id = generate_uuid_v7()
                evidence_ids = data['evidence_ids'][:5]  # 最多5条evidence
                
                await conn.execute(text("""
                    INSERT INTO candidates (
                        id, workspace_id, entity_id, area_id,
                        content, candidate_type, evidence_source,
                        evidence_id, evidence_chain, evidence_count,
                        evidence_strength, status, ingested_by,
                        ingestion_timestamp, verified_at,
                        created_at, updated_at
                    ) VALUES (
                        :id, :ws_id, :entity_id, :area_id,
                        :content, 'pattern', 'import',
                        :evidence_id, :evidence_chain, :evidence_count,
                        0.8, 'candidate', 'import',
                        NOW(), NOW(),
                        NOW(), NOW()
                    )
                """), {
                    "id": candidate_id,
                    "ws_id": WORKSPACE_ID,
                    "entity_id": entity_id,
                    "area_id": data['area_id'],
                    "content": f"Entity: {data['entity_name']}",
                    "evidence_id": evidence_ids[0] if evidence_ids else None,
                    "evidence_chain": json.dumps(evidence_ids),
                    "evidence_count": len(evidence_ids),
                })
                created += 1
                if created % 10 == 0:
                    print(f"  已创建 {created} 个candidates...")
            except Exception as e:
                print(f"  ❌ 创建candidate失败: {e}")
                await conn.rollback()
    
    print(f"\n✅ 创建完成: {created} 个candidates")
    
    # 验证
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM candidates WHERE workspace_id = :ws_id"), {"ws_id": WORKSPACE_ID})
        count = result.scalar()
        print(f"📊 数据库中candidates总数: {count}")
    
    await engine.dispose()
    
    return created > 0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
