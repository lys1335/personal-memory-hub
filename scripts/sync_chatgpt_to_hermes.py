"""
ChatGPT 数据同步到 Hermes Desktop
"""
import json
import os
from pathlib import Path
from datetime import datetime

EXPORT_DIR = r"F:\LI_YONGSHUN\AI\ChatGPT_export\chatgpt_personal_backup_2026-08-04"
OUTPUT_DIR = r"F:\LI_YONGSHUN\AI\ChatGPT_export\hermes_sync"

def extract_messages(data):
    """从 ChatGPT JSON 提取消息"""
    mapping = data.get('mapping', {})
    messages = []
    for msg_id, msg_data in mapping.items():
        if not msg_data:
            continue
        message = msg_data.get('message')
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
        text = ' '.join([
            p if isinstance(p, str) 
            else (p.get('text', '') if isinstance(p, dict) else '')
            for p in parts
        ])
        if text.strip():
            messages.append({'role': role, 'content': text.strip()})
    return messages

def main():
    print(f"📊 开始同步 {EXPORT_DIR} 数据...")
    
    json_files = sorted([f for f in os.listdir(EXPORT_DIR) if f.endswith('.json')])
    print(f"📄 找到 {len(json_files)} 个 JSON 文件")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    synced = 0
    errors = 0
    
    for i, json_file in enumerate(json_files):
        try:
            filepath = os.path.join(EXPORT_DIR, json_file)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            title = data.get('title', 'Untitled')
            conv_id = data.get('conversation_id', json_file.replace('.json', ''))
            messages = extract_messages(data)
            
            if not messages:
                print(f"  ⚠️ 跳过空对话: {json_file}")
                continue
            
            # 生成Hermes Desktop格式
            hermes_format = {
                'id': conv_id,
                'title': title,
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'updated_at': datetime.utcnow().isoformat() + 'Z',
                'messages': messages
            }
            
            # 按文件路径保存到输出目录
            safe_name = json_file.replace('.json', '')
            output_path = os.path.join(OUTPUT_DIR, f"{safe_name}.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(hermes_format, f, ensure_ascii=False, indent=2)
            
            synced += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(json_files)}] 已同步 {synced} 个对话")
                
        except Exception as e:
            errors += 1
            print(f"  ❌ 错误: {json_file}: {e}")
    
    print(f"\n✅ 同步完成!")
    print(f"  - 处理文件: {len(json_files)}")
    print(f"  - 同步对话: {synced}")
    print(f"  - 错误: {errors}")
    print(f"\n📂 输出目录: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
