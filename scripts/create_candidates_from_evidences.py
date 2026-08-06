"""直接从Evidences创建Candidates（不依赖entity_id）"""
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
    print("📊 开始从Evidences创建Candidates...")
    
    engine = get_engine()
    
    # 查询所有evidences（不依赖entity_id）
    print("📝 查询evidences...")
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT 
                id,
                content,
                evidence_type,
                source
            FROM evidences
            WHERE workspace_id = :ws_id
            ORDER BY created_at
            LIMIT 200
        """), {"ws_id": WORKSPACE_ID})
        
        rows = result.fetchall()
        print(f"  找到 {len(rows)} 个evidences")
    
    # 创建candidates
    created = 0
    async with engine.begin() as conn:
        for evidence_id, content, evidence_type, source in rows:
            try:
                candidate_id = generate_uuid_v7()
                entity_id = generate_uuid_v7()  # 创建临时entity_id
                
                # 截断content用于candidate
                content_preview = content[:500] if len(content) > 500 else content
                
                await conn.execute(text("""
                    INSERT INTO candidates (
                        id, workspace_id, entity_id, area_id,
                        content, candidate_type, evidence_source,
                        evidence_id, evidence_chain, evidence_count,
                        evidence_strength, status, ingested_by,
                        ingestion_timestamp, verified_at,
                        created_at, updated_at
                    ) VALUES (
                        :id, :ws_id, :entity_id, NULL,
                        :content, 'fact', :source,
                        :evidence_id, :evidence_chain, :evidence_count,
                        :evidence_strength, 'candidate', 'import',
                        NOW(), :verified_at,
                        NOW(), NOW()
                    )
                """), {
                    "id": candidate_id,
                    "ws_id": WORKSPACE_ID,
                    "entity_id": entity_id,
                    "content": content_preview,
                    "source": source or 'import',
                    "evidence_id": evidence_id,
                    "evidence_chain": json.dumps([str(evidence_id)]),
                    "evidence_count": 1,
                    "evidence_strength": 0.8,
                    "verified_at": generate_uuid_v7(),
                })
                created += 1
                if created % 20 == 0:
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
        
        # 查看一个示例
        result = await conn.execute(text("SELECT id, content, evidence_count FROM candidates ORDER BY created_at DESC LIMIT 1"))
        row = result.fetchone()
        if row:
            print(f"\n📄 示例candidate:")
            print(f"  ID: {row[0]}")
            print(f"  Content: {row[1][:200]}...")
            print(f"  Evidence count: {row[2]}")
    
    await engine.dispose()
    
    return created > 0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
