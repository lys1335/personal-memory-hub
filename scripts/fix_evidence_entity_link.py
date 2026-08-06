"""修复Evidences的entity_id关联"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
import json
from sqlalchemy import text
from backend.shared.infrastructure.database.engine import get_engine

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

async def main():
    print("📊 开始修复evidences的entity_id关联...")
    
    engine = get_engine()
    
    # 查询所有entities
    print("📝 查询entities...")
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT e.id as entity_id, e.area_id, e.canonical_name,
                   ev.id as evidence_id
            FROM entities e
            LEFT JOIN evidences ev ON ev.workspace_id = e.workspace_id
            WHERE e.workspace_id = :ws_id
            LIMIT 500
        """), {"ws_id": WORKSPACE_ID})
        
        rows = result.fetchall()
        print(f"  找到 {len(rows)} 条记录")
    
    # 更新evidences的entity_id和area_id
    updated = 0
    async with engine.begin() as conn:
        for entity_id, area_id, entity_name, evidence_id in rows:
            if evidence_id:
                try:
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
                    updated += 1
                except Exception as e:
                    print(f"  ❌ 更新失败: {e}")
                    await conn.rollback()
    
    print(f"\n✅ 更新了 {updated} 个evidences")
    
    # 验证
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM evidences 
            WHERE workspace_id = :ws_id AND entity_id IS NOT NULL
        """), {"ws_id": WORKSPACE_ID})
        count = result.scalar()
        print(f"📊 有entity_id的evidences: {count}")
        
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM evidences 
            WHERE workspace_id = :ws_id AND entity_id IS NULL
        """), {"ws_id": WORKSPACE_ID})
        count_null = result.scalar()
        print(f"📊 没有entity_id的evidences: {count_null}")
    
    await engine.dispose()
    
    return updated > 0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
