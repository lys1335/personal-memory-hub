import json
import os
import sys

export_dir = r"F:\LI_YONGSHUN\AI\ChatGPT_export\chatgpt_personal_backup_2026-08-04"
json_files = [f for f in os.listdir(export_dir) if f.endswith('.json')]

print(f"Total JSON files: {len(json_files)}")

# Check first 5 files structure
for fname in json_files[:5]:
    filepath = os.path.join(export_dir, fname)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n=== {fname} ===")
    print(f"Top-level keys: {list(data.keys())}")
    
    # Check mapping structure
    if 'mapping' in data:
        mapping = data['mapping']
        print(f"Mapping count: {len(mapping)}")
        
        # Show first node structure
        for key in list(mapping.keys())[:2]:
            node = mapping[key]
            print(f"\nNode key: {key}")
            print(f"  Node type: {node.get('type', 'N/A') if node else 'None'}")
            if node and 'message' in node:
                msg = node['message']
                print(f"  Message keys: {list(msg.keys()) if msg else 'None'}")
                if msg:
                    print(f"    author: {msg.get('author', 'N/A')}")
                    content = msg.get('content', {})
                    print(f"    content type: {type(content).__name__}")
                    if isinstance(content, dict):
                        print(f"    content keys: {list(content.keys())}")
                        parts = content.get('parts', [])
                        if parts:
                            print(f"    parts[0]: {parts[0] if isinstance(parts[0], str) else str(parts[0])[:100]}")
                    elif isinstance(content, list):
                        print(f"    content: {str(content)[:100]}")
    
    # Check for conversation_id
    print(f"  conversation_id: {data.get('conversation_id', 'N/A')}")
    print(f"  title: {data.get('title', 'N/A')}")
