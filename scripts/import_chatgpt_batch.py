"""
批量导入 ChatGPT 对话到 PMH 数据库

清空现有数据后导入新的 ChatGPT 对话。
"""

import json
import sys
import psycopg2
from pathlib import Path
from datetime import datetime
from typing import Optional

# 数据库配置
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "memory_hub",
    "user": "postgres",
    "password": "postgres"
}

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"


def clear_database():
    """清空所有表数据"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()

    tables = ['evidences', 'memory_nodes', 'entities', 'areas', 'proposals', 'memory_evidences']
    for table in tables:
        try:
            cur.execute(f"DELETE FROM {table}")
            print(f"  ✓ 清空 {table}")
        except Exception as e:
            print(f"  ⚠ {table}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ 数据库已清空")


def import_chatgpt_json(file_path: str, conn, cur) -> dict:
    """导入单个 ChatGPT JSON 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    title = data.get('title', 'Untitled')
    conversation_id = data.get('conversation_id', data.get('id', 'unknown'))
    mapping = data.get('mapping', {})

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
    evidence_ids = []
    for i, msg in enumerate(messages):
        # 创建 evidence
        evidence_type = 'user_input' if msg['role'] == 'user' else 'assistant_response'
        evidence_id = f"chatgpt_{conversation_id}_{i}"

        cur.execute(
            """
            INSERT INTO evidences (id, workspace_id, source, evidence_type, content, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                evidence_id,
                WORKSPACE_ID,
                f"chatgpt:{conversation_id}",
                evidence_type,
                msg['content'],
                datetime.fromtimestamp(msg['timestamp']) if msg['timestamp'] else datetime.now()
            )
        )
        imported += 1
        evidence_ids.append(evidence_id)

        # 每 100 条提交一次
        if imported % 100 == 0:
            conn.commit()

    # 创建 Level 1 Memory Node
    if evidence_ids:
        summary = f"[ChatGPT] {title}"
        content = "\n\n".join(msg['content'] for msg in messages[:10])  # 前 10 条消息作为内容
        cur.execute(
            """
            INSERT INTO memory_nodes (id, workspace_id, level, node_type, content, summary, confidence, importance, signal_strength, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                f"node_{conversation_id}",
                WORKSPACE_ID,
                1,
                'Observation',
                content,
                summary,
                0.9,
                0.7,
                0.8,
                datetime.now()
            )
        )

        # 创建证据关联
        for evidence_id in evidence_ids:
            try:
                cur.execute(
                    """
                    INSERT INTO memory_evidences (memory_node_id, evidence_id)
                    VALUES (%s, %s)
                    """,
                    (f"node_{conversation_id}", evidence_id)
                )
            except Exception as e:
                print(f"  ⚠ 关联证据失败: {e}")

    conn.commit()

    return {
        'title': title,
        'conversation_id': conversation_id,
        'messages_imported': imported,
        'evidence_ids': len(evidence_ids)
    }


def main():
    # 使用原始 ChatGPT 导出目录
    import_dir = sys.argv[1] if len(sys.argv) > 1 else r'F:\LI_YONGSHUN\AI\ChatGPT_export\extracted'

    import_path = Path(import_dir)
    json_files = list(import_path.rglob('*.json'))

    print(f"找到 {len(json_files)} 个 JSON 文件")
    print()

    # 清空数据库
    print("=== 清空数据库 ===")
    clear_database()
    print()

    # 连接数据库
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()

    stats = {'success': 0, 'errors': 0, 'total_messages': 0}

    for json_file in json_files:
        try:
            result = import_chatgpt_json(str(json_file), conn, cur)
            print(f"✓ {result['title']} ({result['messages_imported']} 条消息)")
            stats['success'] += 1
            stats['total_messages'] += result['messages_imported']
        except Exception as e:
            stats['errors'] += 1
            print(f"✗ {json_file.name}: {e}")

    cur.close()
    conn.close()

    print()
    print("=== 导入完成 ===")
    print(f"  - 成功: {stats['success']}")
    print(f"  - 错误: {stats['errors']}")
    print(f"  - 总消息数: {stats['total_messages']}")

    # 验证导入结果
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM evidences")
    evidence_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memory_nodes")
    node_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entities")
    entity_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM areas")
    area_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proposals")
    proposal_count = cur.fetchone()[0]
    cur.close()
    conn.close()

    print()
    print("=== 数据库状态 ===")
    print(f"  - Evidences: {evidence_count}")
    print(f"  - Memory Nodes: {node_count}")
    print(f"  - Entities: {entity_count}")
    print(f"  - Areas: {area_count}")
    print(f"  - Proposals: {proposal_count}")


if __name__ == "__main__":
    main()
