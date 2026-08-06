import sys
import os
import json
import uuid
import time
import re
from pathlib import Path
from datetime import datetime

# 配置
DB_URL = "postgresql://postgres:postgres@localhost:5432/memory_hub"
EXPORT_DIR = Path(r"F:\LI_YONGSHUN\AI\ChatGPT_export\chatgpt_personal_backup_2026-08-04")
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

# UUIDv7 生成
def generate_uuid_v7():
    timestamp_ms = int(time.time() * 1000)
    ts_part = timestamp_ms & 0xFFFFFFFFFFFF
    random_part = uuid.uuid4().int & 0xFFFFFFFFFFFF
    uuid_int = (ts_part << 48) | (0x7 << 44) | (0x2 << 42) | random_part
    return uuid.UUID(int=uuid_int)

def main():
    print(f"📊 开始导入 {EXPORT_DIR.name} 数据...")
    print(f"📁 导出目录: {EXPORT_DIR}")
    
    # 获取所有 JSON 文件
    json_files = list(EXPORT_DIR.glob("*.json"))
    print(f"📄 找到 {len(json_files)} 个 JSON 文件")
    
    if len(json_files) == 0:
        print("❌ 没有找到 JSON 文件")
        return
    
    # 导入对话
    print(f"\n📥 开始导入 {len(json_files)} 个对话...")
    start_time = time.time()
    
    total_evidences = 0
    total_nodes = 0
    total_entities = 0
    
    for i, json_file in enumerate(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                conv_data = json.load(f)
            
            # 获取对话标题
            title = conv_data.get('title', 'Untitled')
            
            # 提取消息
            mapping = conv_data.get('mapping', {})
            messages = []
            
            # 找根节点
            root_id = None
            for key in mapping:
                node = mapping[key]
                if node and not node.get('parent'):
                    root_id = key
                    break
            
            if not root_id:
                root_id = list(mapping.keys())[0] if mapping else None
            
            # 遍历消息
            visited = set()
            def traverse(node_id):
                if not node_id or node_id in visited:
                    return
                visited.add(node_id)
                
                node = mapping.get(node_id)
                if not node:
                    return
                
                message = node.get('message')
                if not message:
                    return
                
                role = message.get('author', {}).get('role', '')
                if role not in ['user', 'assistant']:
                    return
                
                content = message.get('content', {})
                parts = content.get('parts', [])
                if not parts:
                    return
                
                text = ' '.join([p if isinstance(p, str) else p.get('text', '') for p in parts])
                if not text:
                    return
                
                messages.append({
                    'role': role,
                    'content': text
                })
                
                child_id = node.get('child')
                if child_id:
                    traverse(child_id)
            
            if root_id:
                traverse(root_id)
            
            # 使用 psycopg2 直接插入
            import psycopg2
            conn = psycopg2.connect(DB_URL.replace('postgresql://', 'postgres://'))
            cur = conn.cursor()
            
            # 插入证据和记忆节点
            for msg in messages:
                evidence_id = str(generate_uuid_v7())
                node_id = str(generate_uuid_v7())
                
                cur.execute("""
                    INSERT INTO evidences (id, workspace_id, source, evidence_type, content, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (evidence_id, WORKSPACE_ID, 'chatgpt', msg['role'], msg['content'], datetime.utcnow()))
                
                cur.execute("""
                    INSERT INTO memory_nodes (id, workspace_id, level, node_type, content, summary, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (node_id, WORKSPACE_ID, 1, msg['role'], msg['content'], 
                      msg['content'][:200] if len(msg['content']) > 200 else msg['content'],
                      datetime.utcnow()))
                
                total_evidences += 1
                total_nodes += 1
            
            # 提取实体
            entity_pattern = r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b'
            entities_found = set()
            for msg in messages:
                found = re.findall(entity_pattern, msg['content'])
                for e in found[:10]:
                    if len(e) > 3:
                        entities_found.add(e)
            
            for entity_name in list(entities_found)[:20]:
                entity_id = str(generate_uuid_v7())
                area_id = str(generate_uuid_v7())
                
                cur.execute("""
                    INSERT INTO entities (id, workspace_id, canonical_name, entity_type, description, area_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (entity_id, WORKSPACE_ID, entity_name, 'Concept', 
                      f'从对话 "{title}" 中提取', area_id, datetime.utcnow()))
                
                cur.execute("""
                    INSERT INTO areas (id, workspace_id, name, description, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (area_id, WORKSPACE_ID, entity_name, 
                      f'包含实体 {entity_name} 的区域', datetime.utcnow()))
                
                total_entities += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            # 进度显示
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                eta = (len(json_files) - i - 1) / rate
                print(f"  [{i+1}/{len(json_files)}] {rate:.1f} 对话/秒, 预计剩余 {eta:.0f} 秒")
            
        except Exception as e:
            print(f"  ❌ 导入失败 {json_file.name}: {e}")
    
    elapsed = time.time() - start_time
    print(f"\n✅ 导入完成!")
    print(f"  - 总对话数: {len(json_files)}")
    print(f"  - 总证据数: {total_evidences}")
    print(f"  - 总记忆节点: {total_nodes}")
    print(f"  - 总实体数: {total_entities}")
    print(f"  - 耗时: {elapsed:.1f} 秒")
    print(f"  - 平均速度: {len(json_files)/elapsed:.1f} 对话/秒")

if __name__ == "__main__":
    main()
