"""创建高质量Candidates（包含实际evidence内容）"""
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
    print("📊 开始创建高质量Candidates...")
    
    engine = get_engine()
    
    # 查询所有有entity_id的evidences，按entity分组
    print("📝 查询evidences按entity分组...")
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT 
                e.id as entity_id,
                e.area_id,
                e.canonical_name,
                ev.id as evidence_id,
                ev.content as evidence_content
            FROM entities e
            JOIN evidences ev ON ev.entity_id = e.id AND ev.workspace_id = e.workspace_id
            WHERE e.workspace_id = :ws_id
            ORDER BY e.canonical_name, ev.created_at
            LIMIT 500
        """), {"ws_id": WORKSPACE_ID})
        
        rows = result.fetchall()
        print(f"  找到 {len(rows)} 条evidence记录")
    
    # 按entity分组
    entity_evidences = {}
    for entity_id, area_id, entity_name, evidence_id, evidence_content in rows:
        if entity_id not in entity_evidences:
            entity_evidences[entity_id] = {
                'area_id': area_id,
                'entity_name': entity_name,
                'evidences': []
            }
        if evidence_id and evidence_content:
            entity_evidences[entity_id]['evidences'].append({
                'id': str(evidence_id),
                'content': evidence_content[:500] if len(evidence_content) > 500 else evidence_content
            })
    
    print(f"  涉及 {len(entity_evidences)} 个entities")
    
    # 创建candidates
    created = 0
    
    # 先清理旧candidates
    async with engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM candidates WHERE workspace_id = :ws_id"), {"ws_id": WORKSPACE_ID})
    
    # 创建新的candidates
    async with engine.begin() as conn:
        for entity_id, data in list(entity_evidences.items())[:50]:  # 限制50个
            if not data['evidences']:
                continue
                
            try:
                candidate_id = generate_uuid_v7()
                verified_id = generate_uuid_v7()
                
                # 收集所有evidence IDs
                evidence_ids = [e['id'] for e in data['evidences'][:5]]
                
                # 构建更有意义的content，包含实际evidence内容
                content_parts = [f"实体: {data['entity_name']}"]
                for i, evidence in enumerate(data['evidences'][:5], 1):
                    content_parts.append(f"记忆{i}: {evidence['content']}")
                content = "\n".join(content_parts)
                
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
                        :evidence_strength, 'candidate', 'import',
                        NOW(), :verified_at,
                        NOW(), NOW()
                    )
                """), {
                    "id": candidate_id,
                    "ws_id": WORKSPACE_ID,
                    "entity_id": entity_id,
                    "area_id": data['area_id'],
                    "content": content,
                    "evidence_id": evidence_ids[0],
                    "evidence_chain": json.dumps(evidence_ids),
                    "evidence_count": len(evidence_ids),
                    "evidence_strength": 0.8,
                    "verified_at": verified_id,
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
        
        # 查看示例
        result = await conn.execute(text("SELECT id, content, evidence_count FROM candidates ORDER BY created_at DESC LIMIT 2"))
        rows = result.fetchall()
        print(f"\n📄 示例candidates:")
        for row in rows:
            print(f"  ID: {row[0]}")
            print(f"  Content: {row[1][:300]}...")
            print(f"  Evidence count: {row[2]}")
            print()
    
    await engine.dispose()
    
    return created > 0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
