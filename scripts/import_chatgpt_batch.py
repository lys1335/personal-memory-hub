"""
批量导入 ChatGPT 对话到 PMH
"""
import json
import sys
import psycopg2
from pathlib import Path
from datetime import datetime

# 数据库配置
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "memory_hub",
    "user": "postgres",
    "password": "postgres"
}

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

def import_chatgpt_json(file_path: str):
    """导入单个 ChatGPT JSON 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    title = data.get('title', 'Untitled')
    conversation_id = data.get('conversation_id', data.get('id', 'unknown'))
    mapping = data.get('mapping', {})
    
    # 连接数据库
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    
    # 提取消息
    messages = []
    for msg_id, msg_data in mapping.items():
        if msg_data is None:
            continue
        message = msg_data.get('message')
        if message is None:
            continue
        author = message.get('author', {})
        if author is None:
            continue
        role = author.get('role')
        if role not in ('user', 'assistant'):
            continue
        content_obj = message.get('content', {})
        if content_obj is None:
            continue
        parts = content_obj.get('parts', [])
        if not parts:
            continue
        content = parts[0] if parts else ''
        if not content or not str(content).strip():
            continue
        timestamp = msg_data.get('create_time', 0)
        messages.append({
            'role': role,
            'content': str(content),
            'timestamp': float(timestamp) if timestamp else 0
        })
    
    # 按时间排序
    messages.sort(key=lambda x: x['timestamp'])
    
    # 导入到数据库
    imported = 0
    for msg in messages:
        # 创建 evidence
        evidence_type = 'user_input' if msg['role'] == 'user' else 'assistant_response'
        cur.execute(
            """
            INSERT INTO evidences (id, workspace_id, source, evidence_type, content, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                f"chatgpt_{conversation_id}_{imported}",
                WORKSPACE_ID,
                f"chatgpt:{conversation_id}",
                evidence_type,
                msg['content'],
                datetime.fromtimestamp(msg['timestamp']) if msg['timestamp'] else datetime.now()
            )
        )
        imported += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        'title': title,
        'conversation_id': conversation_id,
        'messages_imported': imported
    }

def main():
    import_dir = sys.argv[1] if len(sys.argv) > 1 else r'F:\LI_YONGSHUN\AI\ChatGPT_export\extracted'
    
    import_path = Path(import_dir)
    json_files = list(import_path.rglob('*.json'))
    
    print(f"找到 {len(json_files)} 个 JSON 文件")
    print()
    
    stats = {'success': 0, 'errors': 0}
    
    for json_file in json_files:
        try:
            result = import_chatgpt_json(str(json_file))
            print(f"✓ {result['title']} ({result['messages_imported']} 条消息)")
            stats['success'] += 1
        except Exception as e:
            print(f"✗ {json_file.name}: {e}")
            stats['errors'] += 1
    
    print()
    print(f"导入完成:")
    print(f"  - 成功: {stats['success']}")
    print(f"  - 错误: {stats['errors']}")

if __name__ == "__main__":
    main()
