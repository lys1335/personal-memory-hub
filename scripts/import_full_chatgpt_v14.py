import json
import os
import uuid
import time
import re
from datetime import datetime
import psycopg2

EXPORT_DIR = r"F:\LI_YONGSHUN\AI\ChatGPT_export\chatgpt_personal_backup_2026-08-04"
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
DB_CONFIG = {
    'host': 'localhost',
    'database': 'memory_hub',
    'user': 'postgres',
    'password': 'postgres'
}

def generate_uuid_v7():
    timestamp_ms = int(time.time() * 1000)
    ts_part = timestamp_ms & 0xFFFFFFFFFFFF
    random_part = uuid.uuid4().int & 0xFFFFFFFFFFFF
    uuid_int = (ts_part << 48) | (0x7 << 44) | (0x2 << 42) | random_part
    return str(uuid.UUID(int=uuid_int))

def extract_messages(mapping):
    """Extract user/assistant messages from mapping"""
    messages = []
    
    for key, node in mapping.items():
        if not node:
            continue
        message = node.get('message')
        if not message:
            continue
        role = message.get('author', {}).get('role', '')
        if role not in ['user', 'assistant']:
            continue
        content = message.get('content', {})
        if not isinstance(content, dict):
            continue
        parts = content.get('parts', [])
        if not parts:
            continue
        text = ' '.join([p if isinstance(p, str) else (p.get('text', '') if isinstance(p, dict) else '') for p in parts])
        if not text:
            continue
        messages.append({'role': role, 'content': text})
    
    return messages

def main():
    print(f"📊 开始导入 {EXPORT_DIR} 数据...")
    
    json_files = sorted([f for f in os.listdir(EXPORT_DIR) if f.endswith('.json')])
    print(f"📄 找到 {len(json_files)} 个 JSON 文件")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 清空数据库
    print("🗑️  清空数据库...")
    cur.execute("DELETE FROM evidences")
    cur.execute("DELETE FROM memory_nodes")
    cur.execute("DELETE FROM entities")
    cur.execute("DELETE FROM areas")
    cur.execute("DELETE FROM proposals")
    conn.commit()
    print("✅ 数据库已清空")
    
    total_evidences = 0
    total_nodes = 0
    total_entities = 0
    total_messages = 0
    errors = []
    start_time = time.time()
    
    for i, json_file in enumerate(json_files):
        try:
            filepath = os.path.join(EXPORT_DIR, json_file)
            with open(filepath, 'r', encoding='utf-8') as f:
                conv_data = json.load(f)
            
            title = conv_data.get('title', 'Untitled')
            mapping = conv_data.get('mapping', {})
            messages = extract_messages(mapping)
            
            if not messages:
                continue
            
            now = datetime.utcnow()
            conv_id = conv_data.get('conversation_id', generate_uuid_v7())
            
            # 插入证据和记忆节点
            for msg in messages:
                evidence_id = generate_uuid_v7()
                node_id = generate_uuid_v7()
                
                content_text = msg['content']
                summary = content_text[:200] if len(content_text) > 200 else content_text
                
                cur.execute("""
                    INSERT INTO evidences (id, workspace_id, evidence_type, content, raw_content,
                        confidence, importance, signal_strength, source, _meta, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 0.8, 0.5, 0.6, %s, %s, %s, %s)
                """, (
                    evidence_id, WORKSPACE_ID, msg['role'], content_text, content_text,
                    'chatgpt',
                    json.dumps({'source_file': json_file, 'conversation_id': conv_id}),
                    now, now
                ))
                
                cur.execute("""
                    INSERT INTO memory_nodes (id, workspace_id, level, node_type, content, summary,
                        confidence, importance, signal_strength, status, source, generated_by,
                        evidence_links, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 0.8, 0.5, 0.6, %s, %s, %s, %s, %s, %s)
                """, (
                    node_id, WORKSPACE_ID, 1, msg['role'], content_text, summary,
                    'active', 'chatgpt', 'system',
                    json.dumps([evidence_id]),
                    now, now
                ))
                
                total_evidences += 1
                total_nodes += 1
                total_messages += 1
            
            # 提取实体
            entities_found = set()
            for msg in messages:
                found = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b', msg['content'])
                for e in found[:10]:
                    if len(e) > 3:
                        entities_found.add(e)
            
            for entity_name in list(entities_found)[:20]:
                entity_id = generate_uuid_v7()
                area_id = generate_uuid_v7()
                
                cur.execute("""
                    INSERT INTO areas (id, workspace_id, name, description, sort_order, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 0, %s, %s)
                """, (area_id, WORKSPACE_ID, entity_name, f'包含实体 {entity_name} 的区域', now, now))
                
                cur.execute("""
                    INSERT INTO entities (id, workspace_id, area_id, entity_type, canonical_name, description, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    entity_id, WORKSPACE_ID, area_id, 'Concept',
                    entity_name, f'从对话 "{title}" 中提取', now, now
                ))
                total_entities += 1
            
            conn.commit()
            
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                eta = (len(json_files) - i - 1) / rate
                print(f"  [{i+1}/{len(json_files)}] 已处理 {rate:.1f} 对话/秒, 预计剩余 {eta:.0f} 秒, 消息: {total_messages}")
                
        except Exception as e:
            errors.append((json_file, str(e)))
            conn.rollback()
            print(f"  ❌ 导入失败 {json_file}: {e}")
    
    elapsed = time.time() - start_time
    print(f"\n✅ 导入完成!")
    print(f"  - 总对话数: {len(json_files)}")
    print(f"  - 总消息数: {total_messages}")
    print(f"  - 总证据数: {total_evidences}")
    print(f"  - 总记忆节点: {total_nodes}")
    print(f"  - 总实体数: {total_entities}")
    print(f"  - 耗时: {elapsed:.1f} 秒")
    
    if errors:
        print(f"\n⚠️ 导入失败 {len(errors)} 个文件:")
        for f, e in errors[:5]:
            print(f"  - {f}: {e}")
    
    # 验证
    cur.execute("SELECT COUNT(*) FROM evidences")
    print(f"\n📊 数据库验证: evidences = {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM memory_nodes")
    print(f"📊 数据库验证: memory_nodes = {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM entities")
    print(f"📊 数据库验证: entities = {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM areas")
    print(f"📊 数据库验证: areas = {cur.fetchone()[0]}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
