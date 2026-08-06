"""修复所有Evidences的entity_id关联（基于内容匹配）"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
import re
import json
from sqlalchemy import text
from backend.shared.infrastructure.database.engine import get_engine

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

async def main():
    print("📊 开始修复所有evidences的entity_id关联...")
    
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
    
    # 建立entity名称到ID的映射（用于快速查找）
    entity_map = {}
    for entity_id, area_id, canonical_name in entities:
        # 标准化名称用于匹配
        name_lower = canonical_name.lower()
        entity_map[name_lower] = (entity_id, area_id)
    
    # 查询所有未关联的evidences
    print("📝 查询未关联的evidences...")
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT id, content
            FROM evidences
            WHERE workspace_id = :ws_id AND entity_id IS NULL
            LIMIT 1000
        """), {"ws_id": WORKSPACE_ID})
        
        evidences = result.fetchall()
        print(f"  找到 {len(evidences)} 个未关联的evidences")
    
    # 尝试从content中提取entity并关联
    updated = 0
    not_found = 0
    
    async with engine.begin() as conn:
        for evidence_id, content in evidences:
            try:
                # 从content中提取可能的entity名称
                # 匹配大写开头的单词（如"Python", "RustDesk"等）
                found_entities = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b', content)
                
                entity_id = None
                area_id = None
                
                # 尝试匹配
                for entity_name in found_entities[:5]:  # 最多匹配5个
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
                    updated += 1
                else:
                    not_found += 1
                    
                if updated % 100 == 0:
                    print(f"  已更新 {updated} 个evidences...")
                    
            except Exception as e:
                print(f"  ❌ 更新失败: {e}")
                await conn.rollback()
    
    print(f"\n✅ 修复完成:")
    print(f"  - 已关联: {updated}")
    print(f"  - 未找到匹配: {not_found}")
    
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
        
        # 查看关联分布
        result = await conn.execute(text("""
            SELECT e.canonical_name, COUNT(ev.id) as evidence_count
            FROM entities e
            JOIN evidences ev ON ev.entity_id = e.id
            WHERE e.workspace_id = :ws_id
            GROUP BY e.canonical_name
            ORDER BY evidence_count DESC
            LIMIT 10
        """), {"ws_id": WORKSPACE_ID})
        rows = result.fetchall()
        print(f"\n📄 Top 10 entities:")
        for row in rows:
            print(f"  {row[0]}: {row[1]} 条evidence")
    
    await engine.dispose()
    
    return updated > 0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
