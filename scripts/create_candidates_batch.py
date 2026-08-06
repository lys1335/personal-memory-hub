"""批量创建 Candidates - 从所有 L1 记忆节点生成"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
import uuid
from sqlalchemy import text
from backend.shared.infrastructure.database.engine import get_engine

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
MAX_CANDIDATES = 1000

async def main():
    engine = get_engine()
    
    async with engine.begin() as conn:
        # 检查已有 candidates
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM candidates 
            WHERE workspace_id = :wid AND status IN ('candidate', 'pending')
        """), {"wid": WORKSPACE_ID})
        existing = result.scalar()
        print(f"Existing candidates: {existing}")
        
        # 检查 L1 nodes 数量
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM memory_nodes 
            WHERE workspace_id = :wid AND level = 1
        """), {"wid": WORKSPACE_ID})
        l1_count = result.scalar()
        print(f"Total L1 nodes: {l1_count}")
        
        if existing >= MAX_CANDIDATES:
            print("Already have enough candidates")
            return
        
        to_create = min(MAX_CANDIDATES - existing, l1_count)
        print(f"Creating {to_create} new candidates...")
        
        # 检查 entities 和 areas 表结构
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'entities' ORDER BY ordinal_position
        """))
        entity_cols = [r[0] for r in result.fetchall()]
        print(f"Entities columns: {entity_cols}")
        
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'areas' ORDER BY ordinal_position
        """))
        area_cols = [r[0] for r in result.fetchall()]
        print(f"Areas columns: {area_cols}")
        
        # 先获取现有的 entity 和 area ID（如果有的话）
        result = await conn.execute(text("SELECT id FROM entities LIMIT 1"))
        existing_entity = result.scalar()
        
        result = await conn.execute(text("SELECT id FROM areas LIMIT 1"))
        existing_area = result.scalar()
        
        if not existing_entity:
            # 创建一个占位 entity
            insert_params = {"id": str(uuid.uuid1()), "workspace_id": WORKSPACE_ID}
            for col in entity_cols:
                if col not in ("id", "workspace_id"):
                    insert_params[col] = "placeholder" if col.endswith("_at") else None
            await conn.execute(text(f"INSERT INTO entities ({', '.join(entity_cols)}) VALUES ({', '.join([':' + c for c in entity_cols])})"), insert_params)
            existing_entity = insert_params["id"]
            print(f"Created placeholder entity: {existing_entity}")
        
        if not existing_area:
            # 创建一个占位 area
            insert_params = {"id": str(uuid.uuid1()), "workspace_id": WORKSPACE_ID}
            for col in area_cols:
                if col not in ("id", "workspace_id"):
                    insert_params[col] = "placeholder" if col.endswith("_at") else None
            await conn.execute(text(f"INSERT INTO areas ({', '.join(area_cols)}) VALUES ({', '.join([':' + c for c in area_cols])})"), insert_params)
            existing_area = insert_params["id"]
            print(f"Created placeholder area: {existing_area}")
        
        # 获取 L1 nodes
        result = await conn.execute(text("""
            SELECT id, content
            FROM memory_nodes
            WHERE workspace_id = :wid AND level = 1
            ORDER BY created_at ASC
            LIMIT :limit
        """), {"wid": WORKSPACE_ID, "limit": to_create})
        
        rows = result.fetchall()
        
        created = 0
        errors = 0
        for row in rows:
            node_id, content = row
            if not content:
                continue
            
            content_preview = content[:1000] if len(content) > 1000 else content
            
            candidate_id = str(uuid.uuid1())
            evidence_id = str(node_id)
            verified_id = str(uuid.uuid1())
            
            try:
                await conn.execute(text("""
                    INSERT INTO candidates (
                        id, workspace_id, entity_id, area_id, content,
                        candidate_type, evidence_source, evidence_id,
                        evidence_chain, evidence_count, evidence_strength,
                        status, ingested_by, ingestion_timestamp,
                        source_level, verified_at, created_at, updated_at
                    ) VALUES (
                        :id, :workspace_id, :entity_id, :area_id, :content,
                        'pattern', 'memory_node', :evidence_id,
                        :evidence_chain, :evidence_count, 0.7,
                        'candidate', 'batch_import', NOW(),
                        1, :verified_id, NOW(), NOW()
                    )
                """), {
                    "id": candidate_id,
                    "workspace_id": WORKSPACE_ID,
                    "entity_id": existing_entity,
                    "area_id": existing_area,
                    "content": content_preview,
                    "evidence_id": evidence_id,
                    "evidence_chain": f'["{evidence_id}"]',
                    "evidence_count": 1,
                    "verified_id": verified_id,
                })
                created += 1
                
                if created % 100 == 0:
                    print(f"  Created {created}/{to_create} candidates...")
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  Error inserting candidate {candidate_id}: {e}")
        
        print(f"Created {created} new candidates ({errors} errors)")
        
        # 验证
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM candidates 
            WHERE workspace_id = :wid AND status = 'candidate'
        """), {"wid": WORKSPACE_ID})
        print(f"Total candidates: {result.scalar()}")

if __name__ == "__main__":
    asyncio.run(main())