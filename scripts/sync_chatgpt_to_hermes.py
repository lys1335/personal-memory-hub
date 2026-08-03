"""
ChatGPT 数据同步到 Hermes Desktop

将导出的 ChatGPT 对话数据转换为 Hermes Desktop 的记忆格式。
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


def load_chatgpt_json(file_path: str) -> dict:
    """加载 ChatGPT 导出的 JSON 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_conversation_data(data: dict) -> dict:
    """从 ChatGPT JSON 提取对话数据"""
    title = data.get('title', 'Untitled')
    conversation_id = data.get('conversation_id', data.get('id', 'unknown'))
    mapping = data.get('mapping', {})

    # 按时间排序消息
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

    return {
        'title': title,
        'conversation_id': conversation_id,
        'messages': messages,
        'source_file': file_path
    }


def create_hermes_session(conversation: dict, project_name: str) -> dict:
    """创建 Hermes Desktop 会话格式"""
    session_id = f"chatgpt_{conversation['conversation_id']}"
    timestamp = datetime.now().isoformat()

    # 构建会话消息
    session_messages = []
    for i, msg in enumerate(conversation['messages']):
        session_messages.append({
            'id': f"msg_{i}",
            'role': msg['role'],
            'content': msg['content'],
            'timestamp': msg['timestamp']
        })

    return {
        'session_id': session_id,
        'title': f"[ChatGPT] {conversation['title']}",
        'project': project_name,
        'created_at': timestamp,
        'source': 'chatgpt_export',
        'messages': session_messages,
        'metadata': {
            'original_id': conversation['conversation_id'],
            'message_count': len(session_messages),
            'imported_at': timestamp
        }
    }


def save_hermes_session(session: dict, output_dir: Path):
    """保存 Hermes Desktop 会话"""
    # 创建项目目录
    project_dir = output_dir / session['project']
    project_dir.mkdir(parents=True, exist_ok=True)

    # 保存为 JSON 文件
    file_path = project_dir / f"{session['session_id']}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(session, f, indent=2, ensure_ascii=False)

    return file_path


def sync_chatgpt_to_hermes(export_dir: str, output_dir: Optional[str] = None):
    """主同步函数"""
    export_path = Path(export_dir)
    if output_dir is None:
        output_dir = export_path.parent / "hermes_sync"
    output_path = Path(output_dir)

    stats = {
        'files_processed': 0,
        'conversations_synced': 0,
        'messages_synced': 0,
        'errors': 0
    }

    # 遍历所有 JSON 文件
    json_files = list(export_path.rglob("*.json"))
    print(f"找到 {len(json_files)} 个 JSON 文件")

    for json_file in json_files:
        stats['files_processed'] += 1
        try:
            # 提取项目名（从路径）
            parts = json_file.parts
            project_name = "unknown"
            for i, part in enumerate(parts):
                if part in ('个人AI平台搭建', 'JP_Furigana_Project', 'extracted'):
                    if i + 1 < len(parts):
                        project_name = parts[i + 1]
                        break
                    else:
                        project_name = part
                        break

            # 如果没找到项目名，使用文件名
            if project_name == "unknown":
                project_name = json_file.stem.split('_')[0] if '_' in json_file.stem else json_file.stem

            # 加载并解析
            data = load_chatgpt_json(str(json_file))
            conversation = extract_conversation_data(data)

            # 创建 Hermes 会话
            if conversation['messages']:
                session = create_hermes_session(conversation, project_name)
                save_hermes_session(session, output_path)
                stats['conversations_synced'] += 1
                stats['messages_synced'] += len(conversation['messages'])
                print(f"  ✓ {conversation['title']} ({len(conversation['messages'])} 条消息)")
            else:
                print(f"  ⚠ 跳过空对话: {conversation['title']}")

        except Exception as e:
            stats['errors'] += 1
            print(f"  ✗ 错误: {json_file.name} - {e}")

    print(f"\n同步完成:")
    print(f"  - 处理文件: {stats['files_processed']}")
    print(f"  - 同步对话: {stats['conversations_synced']}")
    print(f"  - 同步消息: {stats['messages_synced']}")
    print(f"  - 错误: {stats['errors']}")
    print(f"\n输出目录: {output_path}")

    return stats


if __name__ == "__main__":
    export_dir = r"F:\LI_YONGSHUN\AI\ChatGPT_export\extracted"
    output_dir = r"F:\LI_YONGSHUN\AI\ChatGPT_export\hermes_sync"

    sync_chatgpt_to_hermes(export_dir, output_dir)
