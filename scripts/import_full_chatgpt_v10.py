import sys
import os
import json
import uuid
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 配置
DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/memory_hub"
EXPORT_DIR = Path(r"F:\LI_YONGSHUN\AI\ChatGPT_export\chatgpt_personal_backup_2026-08-04")

# UUIDv7 生成
def generate_uuid_v7():
    timestamp_ms = int(time.time() * 1000)
    # 48 bits timestamp
    ts_part = timestamp_ms & 0xFFFFFFFFFFFF
    # 4 bits version = 7
    # 2 bits variant
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
    
    # 连接数据库
    print("🔌 连接数据库...")
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 清空数据库
        print("🗑️  清空数据库...")
        session.execute(text("DELETE FROM evidences"))
        session.execute(text("DELETE FROM memory_nodes"))
        session.execute(text("DELETE FROM entities"))
        session.execute(text("DELETE FROM areas"))
        session.execute(text("DELETE FROM proposals"))
        session.commit()
        print("✅ 数据库已清空")
        
        # 导入对话
        print(f"\n📥 开始导入 {len(json_files)} 个对话...")
        start_time = time.time()
        
        workspace_id = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
        
        for i, json_file in enumerate(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    conv_data = json.load(f)
                
                # 获取对话标题
                title = conv_data.get('title', 'Untitled')
                conv_id = conv_data.get('conversation_id', str(generate_uuid_v7()))
                
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
                
                # 插入证据和记忆节点
                for msg in messages:
                    # Evidence
                    evidence_id = str(generate_uuid_v7())
                    session.execute(text("""
                        INSERT INTO evidences (id, workspace_id, source, evidence_type, content, created_at)
                        VALUES (:id, :workspace_id, :source, :evidence_type, :content, :created_at)
                    """), {
                        'id': evidence_id,
                        'workspace_id': workspace_id,
                        'source': 'chatgpt',
                        'evidence_type': msg['role'],
                        'content': msg['content'],
                        'created_at': datetime.utcnow()
                    })
                    
                    # Memory Node
                    node_id = str(generate_uuid_v7())
                    session.execute(text("""
                        INSERT INTO memory_nodes (id, workspace_id, level, node_type, content, summary, created_at)
                        VALUES (:id, :workspace_id, :level, :node_type, :content, :summary, :created_at)
                    """), {
                        'id': node_id,
                        'workspace_id': workspace_id,
                        'level': 1,
                        'node_type': msg['role'],
                        'content': msg['content'],
                        'summary': msg['content'][:200] if len(msg['content']) > 200 else msg['content'],
                        'created_at': datetime.utcnow()
                    })
                
                # 提取实体
                entity_pattern = r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b'
                entities_found = set()
                for msg in messages:
                    found = re.findall(entity_pattern, msg['content'])
                    for e in found[:10]:  # 每个消息最多10个实体
                        if len(e) > 3:
                            entities_found.add(e)
                
                for entity_name in list(entities_found)[:20]:
                    entity_id = str(generate_uuid_v7())
                    area_id = str(generate_uuid_v7())
                    session.execute(text("""
                        INSERT INTO entities (id, workspace_id, canonical_name, entity_type, description, area_id, created_at)
                        VALUES (:id, :workspace_id, :canonical_name, :entity_type, :description, :area_id, :created_at)
                    """), {
                        'id': entity_id,
                        'workspace_id': workspace_id,
                        'canonical_name': entity_name,
                        'entity_type': 'Concept',
                        'description': f'从对话 "{title}" 中提取',
                        'area_id': area_id,
                        'created_at': datetime.utcnow()
                    })
                    
                    session.execute(text("""
                        INSERT INTO areas (id, workspace_id, name, description, created_at)
                        VALUES (:id, :workspace_id, :name, :description, :created_at)
                    """), {
                        'id': area_id,
                        'workspace_id': workspace_id,
                        'name': entity_name,
                        'description': f'包含实体 {entity_name} 的区域',
                        'created_at': datetime.utcnow()
                    })
                
                session.commit()
                
                # 进度显示
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    eta = (len(json_files) - i - 1) / rate
                    print(f"  [{i+1}/{len(json_files)}] 已导入 {rate:.1f} 对话/秒, 预计剩余 {eta:.0f} 秒")
                
            except Exception as e:
                print(f"  ❌ 导入失败 {json_file.name}: {e}")
        
        elapsed = time.time() - start_time
        print(f"\n✅ 导入完成!")
        print(f"  - 总对话数: {len(json_files)}")
        print(f"  - 耗时: {elapsed:.1f} 秒")
        print(f"  - 平均速度: {len(json_files)/elapsed:.1f} 对话/秒")
        
        # 统计数据库记录数
        result = session.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM evidences) as evidences,
                (SELECT COUNT(*) FROM memory_nodes) as memory_nodes,
                (SELECT COUNT(*) FROM entities) as entities,
                (SELECT COUNT(*) FROM areas) as areas,
                (SELECT COUNT(*) FROM proposals) as proposals
        """))
        row = result.fetchone()
        print(f"\n📊 数据库统计:")
        print(f"  - evidences: {row[0]}")
        print(f"  - memory_nodes: {row[1]}")
        print(f"  - entities: {row[2]}")
        print(f"  - areas: {row[3]}")
        print(f"  - proposals: {row[4]}")
        
    finally:
        session.close()

if __name__ == "__main__":
    import re
    main()
