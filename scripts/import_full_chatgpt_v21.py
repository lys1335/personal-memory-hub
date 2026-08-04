import json
import os
import uuid
import time
import re
from datetime import datetime
import psycopg2
from psycopg2 import sql

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
    conn.autocommit = False
    cur = conn.cursor()
    
    print("🗑️  清空数据库...")
    cur.execute("DELETE FROM evidences")
    cur.execute("DELETE FROM memory_nodes")
    cur.execute("DELETE FROM entities")
    cur.execute("DELETE FROM areas")
    cur.execute("DELETE FROM proposals")
    conn.commit()
    print("✅ 数据库已清空")
    
    # 预处理所有对话，收集所有消息和实体
    print("\n📝 预处理数据...")
    all_messages = []  # [(evidence_id, node_id, role, content, summary, json_file, conv_id)]
    entity_info = {}   # {entity_name: {'area_id': ..., 'entity_id': ..., 'first_conv': ...}}
    
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
            
            for msg in messages:
                evidence_id = generate_uuid_v7()
                node_id = generate_uuid_v7()
                
                content_text = msg['content']
                summary = content_text[:200] if len(content_text) > 200 else content_text
                
                all_messages.append((evidence_id, node_id, msg['role'], content_text, summary, json_file, conv_id))
                
                # 提取实体
                found = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b', content_text)
                for e in found[:10]:
                    if len(e) > 3 and e not in entity_info:
                        entity_info[e] = {'area_id': generate_uuid_v7(), 'entity_id': generate_uuid_v7(), 'first_conv': title}
            
            if (i + 1) % 100 == 0:
                print(f"  已处理 {i+1}/{len(json_files)} 文件")
                
        except Exception as e:
            print(f"  ❌ 预处理失败 {json_file}: {e}")
    
    print(f"\n✅ 预处理完成: {len(all_messages)} 条消息, {len(entity_info)} 个实体")
    
    # 批量插入证据
    print("\n💾 插入证据...")
    now = datetime.utcnow()
    for i, (evidence_id, node_id, role, content, summary, json_file, conv_id) in enumerate(all_messages):
        try:
            cur.execute("""
                INSERT INTO evidences (id, workspace_id, evidence_type, content, raw_content,
                    confidence, importance, signal_strength, source, _meta, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 0.8, 0.5, 0.6, %s, %s, %s, %s)
            """, (
                evidence_id, WORKSPACE_ID, role, content, content,
                'chatgpt',
                json.dumps({'source_file': json_file, 'conversation_id': conv_id}),
                now, now
            ))
        except Exception as e:
            print(f"  ❌ 插入证据失败: {e}")
    
    conn.commit()
    print(f"✅ 证据插入完成: {len(all_messages)} 条")
    
    # 批量插入记忆节点
    print("\n💾 插入记忆节点...")
    for evidence_id, node_id, role, content, summary, json_file, conv_id in all_messages:
        try:
            cur.execute("""
                INSERT INTO memory_nodes (id, workspace_id, level, node_type, content, summary,
                    confidence, importance, signal_strength, status, source, generated_by,
                    evidence_links, contradict_evidence, observation_type, _meta, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 0.8, 0.5, 0.6, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                node_id, WORKSPACE_ID, 1, 'Observation',
                content, summary,
                'active', 'import', 'import',
                json.dumps([evidence_id]), '[]',
                'fact',
                json.dumps({}),
                now, now
            ))
        except Exception as e:
            print(f"  ❌ 插入记忆节点失败: {e}")
    
    conn.commit()
    print(f"✅ 记忆节点插入完成: {len(all_messages)} 条")
    
    # 批量插入areas
    print("\n💾 插入Areas...")
    area_ids = set()
    for entity_name, info in entity_info.items():
        try:
            cur.execute("""
                INSERT INTO areas (id, workspace_id, name, description, sort_order, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 0, %s, %s)
            """, (info['area_id'], WORKSPACE_ID, entity_name, f'包含实体 {entity_name} 的区域', now, now))
            area_ids.add(info['area_id'])
        except psycopg2.errors.UniqueViolation:
            pass  # Area already exists
        except Exception as e:
            print(f"  ❌ 插入Area失败: {e}")
    
    conn.commit()
    print(f"✅ Areas插入完成: {len(area_ids)} 个")
    
    # 批量插入entities
    print("\n💾 插入Entities...")
    for entity_name, info in entity_info.items():
        try:
            cur.execute("""
                INSERT INTO entities (id, workspace_id, area_id, entity_type, canonical_name, description, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                info['entity_id'], WORKSPACE_ID, info['area_id'], 'Concept',
                entity_name, f'从对话中自动提取', now, now
            ))
        except psycopg2.errors.UniqueViolation:
            pass  # Entity already exists
        except Exception as e:
            print(f"  ❌ 插入Entity失败: {e}")
    
    conn.commit()
    print(f"✅ Entities插入完成: {len(entity_info)} 个")
    
    # 统计
    cur.execute("SELECT COUNT(*) FROM evidences")
    evidences_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memory_nodes")
    nodes_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entities")
    entities_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM areas")
    areas_count = cur.fetchone()[0]
    
    elapsed = time.time() - (time.time() - elapsed) if 'elapsed' in dir() else time.time() - start_time
    print(f"\n✅ 导入完成!")
    print(f"  - 总消息数: {evidences_count}")
    print(f"  - 总记忆节点: {nodes_count}")
    print(f"  - 总实体数: {entities_count}")
    print(f"  - 总区域数: {areas_count}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"\n⏱️  总耗时: {time.time() - start_time:.1f} 秒")
