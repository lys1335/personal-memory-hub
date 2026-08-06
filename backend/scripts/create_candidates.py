"""
从现有Evidence创建Candidates
用于测试ReflectionEngine
"""
import psycopg2
import uuid
import time
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'database': 'memory_hub',
    'user': 'postgres',
    'password': 'postgres'
}
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

def generate_uuid_v7():
    timestamp_ms = int(time.time() * 1000)
    ts_part = timestamp_ms & 0xFFFFFFFFFFFF
    random_part = uuid.uuid4().int & 0xFFFFFFFFFFFF
    uuid_int = (ts_part << 48) | (0x7 << 44) | (0x2 << 42) | random_part
    return str(uuid.UUID(int=uuid_int))

def main():
    print("📊 开始创建Candidates...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 清空candidates表
    print("🗑️  清空candidates表...")
    cur.execute("DELETE FROM candidates")
    conn.commit()
    
    # 查询所有entity和对应的evidence
    print("📝 从evidence创建candidates...")
    
    cur.execute("""
        SELECT 
            e.id as entity_id,
            e.area_id,
            e.canonical_name,
            en.id as evidence_id,
            en.content,
            en.evidence_type
        FROM entities e
        JOIN areas a ON e.area_id = a.id
        JOIN evidences en ON en.workspace_id = e.workspace_id
        WHERE e.workspace_id = %s
        ORDER BY e.canonical_name, en.created_at
    """, (WORKSPACE_ID,))
    
    rows = cur.fetchall()
    print(f"  找到 {len(rows)} 条evidence记录")
    
    # 按entity分组创建candidates
    entity_evidences = {}
    for entity_id, area_id, entity_name, evidence_id, content, evidence_type in rows:
        if entity_id not in entity_evidences:
            entity_evidences[entity_id] = {
                'area_id': area_id,
                'entity_name': entity_name,
                'evidences': []
            }
        entity_evidences[entity_id]['evidences'].append({
            'id': evidence_id,
            'content': content[:200],
            'type': evidence_type
        })
    
    print(f"  涉及 {len(entity_evidences)} 个entity")
    
    # 为每个entity创建candidate
    created = 0
    for entity_id, data in list(entity_evidences.items())[:100]:  # 限制100个
        try:
            candidate_id = generate_uuid_v7()
            evidence_ids = [e['id'] for e in data['evidences'][:10]]  # 最多10条evidence
            
            cur.execute("""
                INSERT INTO candidates (
                    id, workspace_id, entity_id, area_id,
                    content, candidate_type, evidence_source,
                    evidence_id, evidence_chain, evidence_count,
                    evidence_strength, status, ingested_by,
                    ingestion_timestamp, verified_at,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                candidate_id, WORKSPACE_ID, entity_id, data['area_id'],
                f"Entity: {data['entity_name']}",  # content
                'pattern',  # candidate_type (pattern or belief)
                'import',   # evidence_source
                evidence_ids[0] if evidence_ids else None,  # evidence_id
                str(evidence_ids),  # evidence_chain (JSON array string)
                len(evidence_ids),  # evidence_count
                0.8,  # evidence_strength
                'candidate',  # status
                'import',   # ingested_by
                datetime.utcnow()
            ))
            created += 1
        except Exception as e:
            print(f"  ❌ 创建candidate失败: {e}")
            conn.rollback()
    
    conn.commit()
    print(f"\n✅ 创建完成: {created} 个candidates")
    
    # 验证
    cur.execute("SELECT COUNT(*) FROM candidates WHERE workspace_id = %s", (WORKSPACE_ID,))
    count = cur.fetchone()[0]
    print(f"📊 数据库中candidates总数: {count}")
    
    cur.close()
    conn.close()
    
    return created > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
