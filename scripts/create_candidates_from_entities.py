"""从Entities创建Candidates（不依赖evidences）"""
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
    print("📊 开始从Entities创建Candidates...")
    
    engine = get_engine()
    
    # 查询所有entities
    print("📝 查询entities...")
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT id, area_id, canonical_name
            FROM entities
            WHERE workspace_id = :ws_id
            LIMIT 100
        """), {"ws_id": WORKSPACE_ID})
        
        rows = result.fetchall()
        print(f"  找到 {len(rows)} 个entities")
    
    # 创建candidates
    created = 0
    for entity_id, area_id, entity_name in rows:
        try:
            candidate_id = generate_uuid_v7()
            verified_id = generate_uuid_v7()
            
            async with engine.begin() as conn:
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
                        NOW(), :verified_at,
                        NOW(), NOW()
                    )
                """), {
                    "id": candidate_id,
                    "ws_id": WORKSPACE_ID,
                    "entity_id": entity_id,
                    "area_id": area_id,
                    "content": f"Entity: {entity_name}",
                    "evidence_id": entity_id,
                    "evidence_chain": json.dumps([str(entity_id)]),
                    "evidence_count": 1,
                    "verified_at": verified_id,
                })
            created += 1
            if created % 10 == 0:
                print(f"  已创建 {created} 个candidates...")
        except Exception as e:
            print(f"  ❌ 创建candidate失败: {e}")
    
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
