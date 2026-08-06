"""分批修复所有Evidences的entity_id关联"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
import re
from sqlalchemy import text
from backend.shared.infrastructure.database.engine import get_engine

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
BATCH_SIZE = 500

async def main():
    print("📊 开始分批修复evidences的entity_id关联...")
    
    engine = get_engine()
    
    # 查询所有entities
    print("📝 查询entities...")
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT id, area_id, canonical_name
            FROM entities
            WHERE workspace_id = :ws_id
        """), {"ws_id": WORKSPACE_ID})
        
        entities = result.fetchall()
        print(f"  找到 {len(entities)} 个entities")
    
    # 建立entity名称到ID的映射
    entity_map = {}
    for entity_id, area_id, canonical_name in entities:
        name_lower = canonical_name.lower()
        entity_map[name_lower] = (entity_id, area_id)
    
    # 分批处理evidences
    total_updated = 0
    offset = 0
    
    while True:
        print(f"\n📝 处理offset={offset}...")
        
        # 查询一批未关联的evidences
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT id, content
                FROM evidences
                WHERE workspace_id = :ws_id AND entity_id IS NULL
                ORDER BY created_at
                LIMIT :limit OFFSET :offset
            """), {"ws_id": WORKSPACE_ID, "limit": BATCH_SIZE, "offset": offset})
            
            evidences = result.fetchall()
        
        if not evidences:
            break
        
        batch_updated = 0
        async with engine.begin() as conn:
            for evidence_id, content in evidences:
                try:
                    # 从content中提取可能的entity名称
                    found_entities = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b', content)
                    
                    entity_id = None
                    area_id = None
                    
                    for entity_name in found_entities[:5]:
                        name_lower = entity_name.lower()
                        if name_lower in entity_map:
                            entity_id, area_id = entity_map[name_lower]
                            break
                    
                    if entity_id:
                        await conn.execute(text("""
                            UPDATE evidences
                            SET entity_id = :entity_id,
                                area_id = :area_id
                            WHERE id = :evidence_id
                        """), {
                            "entity_id": entity_id,
                            "area_id": area_id,
                            "evidence_id": evidence_id
                        })
                        batch_updated += 1
                except Exception as e:
                    print(f"  ❌ 更新失败: {e}")
                    await conn.rollback()
        
        total_updated += batch_updated
        print(f"  本批更新: {batch_updated}, 累计: {total_updated}")
        
        offset += BATCH_SIZE
        
        # 如果本批没有更新任何记录，可能已经处理完了
        if batch_updated == 0 and offset > 2000:
            break
    
    print(f"\n✅ 修复完成，共关联 {total_updated} 个evidences")
    
    # 验证
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM evidences 
            WHERE workspace_id = :ws_id AND entity_id IS NOT NULL
        """), {"ws_id": WORKSPACE_ID})
        count_with_entity = result.scalar()
        print(f"📊 有entity_id的evidences: {count_with_entity}")
        
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM evidences 
            WHERE workspace_id = :ws_id AND entity_id IS NULL
        """), {"ws_id": WORKSPACE_ID})
        count_without_entity = result.scalar()
        print(f"📊 没有entity_id的evidences: {count_without_entity}")
    
    await engine.dispose()
    
    return total_updated > 0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
