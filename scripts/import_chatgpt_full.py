"""
完整的 ChatGPT 导入脚本 - 支持证据链创建

流程：
1. 读取 ChatGPT 导出数据
2. 解析对话消息
3. 创建 Evidence 记录（原始内容）
4. 创建 MemoryNode 记录（摘要内容）
5. 创建 memory_evidences 关联
6. 提取并创建 Entity/Area（简化版：基于关键词）
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID
import psycopg2
import psycopg2.extras
from psycopg2.extras import register_uuid
from uuid import UUID as UUIDType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "memory_hub",
    "user": "postgres",
    "password": "postgres",
}


class ChatGPTImporter:
    """Import ChatGPT conversations with evidence chain."""

    def __init__(self, workspace_id: str):
        self.workspace_id = UUID(workspace_id)
        self.conn = None
        self.stats = {
            "conversations": 0,
            "messages": 0,
            "evidences_created": 0,
            "nodes_created": 0,
            "entities_created": 0,
            "areas_created": 0,
            "links_created": 0,
            "errors": 0,
        }

    def connect(self):
        """Connect to database."""
        self.conn = psycopg2.connect(**DATABASE_CONFIG)
        register_uuid()  # Register UUID adapter for psycopg2
        self.conn.autocommit = False

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def import_file(self, file_path: str, limit: int = 0):
        """Import ChatGPT export file."""
        logger.info(f"Importing from {file_path}")

        # Read and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, list):
            conversations = data
        elif isinstance(data, dict):
            conversations = data.get("conversations", [])
        else:
            logger.error(f"Unexpected data format: {type(data)}")
            return

        if not conversations:
            logger.warning("No conversations found in file")
            return

        self.stats["conversations"] = len(conversations)
        logger.info(f"Found {len(conversations)} conversations")

        # Process each conversation (with limit)
        message_count = 0
        for conv in conversations:
            if limit > 0 and message_count >= limit:
                logger.info(f"Reached limit of {limit} messages, stopping")
                break

            message_count = self._process_conversation(conv, limit - message_count)
            logger.info(f"Processed {message_count} messages so far")

        # Commit all changes
        self.conn.commit()
        self._log_summary()

    def _process_conversation(self, conv: dict, limit: int = 0) -> int:
        """Process a single conversation. Returns number of messages processed."""
        conv_title = conv.get("title", "Untitled")
        mapping = conv.get("mapping", {})

        logger.info(f"Processing conversation: {conv_title} ({len(mapping)} messages)")

        count = 0
        first_msg = True
        for msg_id, entry in mapping.items():
            # Check limit
            if limit > 0 and count >= limit:
                logger.info(f"Reached limit of {limit} messages")
                break

            # Handle different formats:
            # 1. Simplified: {"author_role": "user", "content_parts": [...], ...}
            # 2. Original: {"message": {"author": {"role": "user"}, "content": {...}}, ...}
            msg = self._resolve_message_entry(entry)
            if msg is None:
                if first_msg:
                    print(f"DEBUG: Entry has no message: {list(entry.keys())}")
                    first_msg = False
                continue

            # Extract role
            role = ""
            if "author_role" in msg:
                role = msg["author_role"].lower()
            elif isinstance(msg.get("author"), dict):
                role = msg["author"].get("role", "").lower()

            if first_msg:
                print(f"DEBUG: First message role={role}, keys={list(msg.keys())}")
                first_msg = False

            # Only import user messages
            if role != "user":
                if first_msg is False:  # Only print once
                    print(f"DEBUG: Skipping non-user message")
                continue

            # Extract content
            content = self._extract_content(msg)

            # Skip empty or short messages
            if not content or len(content.strip()) < 5:
                continue

            logger.info(f"Processing message {msg_id}: {content[:50]}...")

            self._import_message(msg_id, content, conv_title)
            count += 1
            self.stats["messages"] += 1

        return count

    def _resolve_message_entry(self, entry: dict) -> dict | None:
        """Resolve message entry from different formats."""
        # Handle simplified format: entry IS the message
        if "author_role" in entry:
            return entry

        # Handle original format: entry contains "message"
        if "message" in entry:
            return entry["message"]

        # Handle direct format: entry has "author"
        if "author" in entry:
            return entry

        return None

    def _extract_content(self, msg: dict) -> str:
        """Extract text content from message."""
        # Handle simplified format
        if "content_parts" in msg:
            parts = msg.get("content_parts", [])
            if isinstance(parts, list):
                return " ".join([str(p) for p in parts if isinstance(p, str)])
            return str(parts) if parts else ""

        # Handle original format
        content = msg.get("content", {})
        if isinstance(content, dict):
            parts = content.get("parts", [])
            if isinstance(parts, list):
                return " ".join([str(p) for p in parts if isinstance(p, str)])
        elif isinstance(content, str):
            return content

        return ""

    def _import_message(self, msg_id: str, content: str, conv_title: str):
        """Import a single message as Evidence + Node with evidence chain."""
        try:
            # Step 1: Create Evidence (原始记录)
            evidence_id = self._create_evidence(content, msg_id, conv_title)

            # Step 2: Create MemoryNode (摘要)
            node_id = self._create_memory_node(content, evidence_id)

            # Step 3: Link Evidence to Node
            self._create_evidence_link(node_id, evidence_id)

            # Step 4: Extract and create Entity/Area
            entity_id, area_id = self._extract_and_create_entity_area(content)

            # Step 5: Update Node with entity_id and area_id
            if entity_id or area_id:
                self._update_node_with_entity(node_id, entity_id, area_id)

            self.stats["evidences_created"] += 1
            self.stats["nodes_created"] += 1
            self.stats["links_created"] += 1
            if entity_id:
                self.stats["entities_created"] += 1
            if area_id:
                self.stats["areas_created"] += 1

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error importing message {msg_id}: {e}")

    def _create_evidence(self, content: str, msg_id: str, conv_title: str) -> str:
        """Create Evidence record. Returns evidence_id as string."""
        import uuid as uuid_module
        evidence_id = str(uuid_module.uuid4())
        now = datetime.utcnow()

        meta = json.dumps({
            "source_type": "chatgpt",
            "source_id": msg_id,
            "conversation_title": conv_title,
            "created_via": "import_script"
        })

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO evidences (
                    id, workspace_id, source_type, source_id, content, meta, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                evidence_id::uuid, str(self.workspace_id), "chatgpt",
                msg_id, content, meta, now
            ))

        self.conn.commit()
        self.stats["evidences_created"] += 1
        return evidence_id

    def _create_memory_node(self, content: str, evidence_id: str) -> str:
        """Create MemoryNode record. Returns node_id as string."""
        import uuid as uuid_module
        node_id = str(uuid_module.uuid4())
        now = datetime.utcnow()

        evidence_links = json.dumps([
            {"evidence_id": str(evidence_id), "weight": 0.8}
        ])

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_nodes (
                    id, workspace_id, entity_id, parent_node_id, user_id,
                    level, node_type, content, summary, observation_type,
                    confidence, importance, signal_strength,
                    status, source, generated_by,
                    evidence_links, contradict_evidence, _meta, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                node_id, str(self.workspace_id), None, None, None,
                1, "Observation", content, None, "fact",
                0.8, 0.5, 0.6,
                "active", "import", "import",
                evidence_links, '[]', '{}', now
            ))

        # Update evidence with node_id
        self._update_evidence_node_link(evidence_id, node_id)

        return node_id

    def _update_evidence_node_link(self, evidence_id: UUID, node_id: UUID):
        """Update evidence metadata with node_id."""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE evidences
                SET _meta = jsonb_set(_meta, '{memory_node_id}', to_jsonb(%s))
                WHERE id = %s
            """, (str(node_id), evidence_id))

    def _create_evidence_link(self, node_id: str, evidence_id: str):
        """Create memory_evidences link."""
        import uuid as uuid_module
        link_id = str(uuid_module.uuid4())
        now = datetime.utcnow()

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_evidences (
                    id, memory_node_id, evidence_id, relationship_type, created_at
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                link_id::uuid, node_id::uuid, evidence_id::uuid,
                "evidenced_by", now
            ))

        self.conn.commit()
        self.stats["links_created"] += 1

    def _extract_and_create_entity_area(self, content: str) -> tuple:
        """Extract entity and area from content."""
        entity_id = None
        area_id = None

        content_lower = content.lower()

        # Extract person names
        person_patterns = [
            (r'老婆.*?([^\s,。]+)', '老婆'),
            (r'妻子.*?([^\s,。]+)', '妻子'),
            (r'名字.*?是.*?([^\s,。]+)', '名字'),
            (r'叫.*?([^\s,。]+)', '叫'),
        ]
        for pattern, label in person_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1).strip('，。、')
                entity_key = f"Person/{name}"
                entity_id = self._create_or_get_entity("Person", entity_key, name)
                break

        # Extract areas
        area_keywords = {
            "Work": ["code", "project", "java", "rust", "开发", "代码", "项目"],
            "Family": ["wife", "husband", "child", "老婆", "孩子", "家庭"],
            "Project": ["memory hub", "pmh", "personal", "hub", "项目"],
            "Finance": ["nisa", "investment", "stock", "投资", "股票"],
            "Travel": ["travel", "paris", "tokyo", "旅行", "旅游"],
        }

        for area_name, keywords in area_keywords.items():
            if any(kw in content_lower for kw in keywords):
                area_id = self._create_or_get_area(area_name, area_name)
                break

        return entity_id, area_id

    def _create_or_get_area(self, name: str, description: str) -> str | None:
        """Create or get existing area. Returns area_id as string."""
        import uuid as uuid_module
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO areas (id, workspace_id, name, description, sort_order, created_at)
                VALUES (%s::uuid, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, name) DO UPDATE SET name = areas.name
                RETURNING id::text
            """, (
                str(uuid_module.uuid4()), str(self.workspace_id), name, description[:500], 0,
                datetime.utcnow()
            ))
            row = cur.fetchone()
            return row[0] if row else None

    def _create_or_get_entity(self, entity_type: str, canonical_name: str, description: str) -> str | None:
        """Create or get existing entity. Returns entity_id as string."""
        import uuid as uuid_module
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO entities (
                    id, workspace_id, entity_type, canonical_name, description, _meta, created_at
                )
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, entity_type, canonical_name) DO NOTHING
                RETURNING id::text
            """, (
                str(uuid_module.uuid4()), str(self.workspace_id), entity_type, canonical_name, description[:500],
                '{"auto_extracted": true}', datetime.utcnow()
            ))
            row = cur.fetchone()
            return row[0] if row else None

    def _update_node_with_entity(self, node_id: UUID, entity_id, area_id):
        """Update memory_node with entity_id and area_id."""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE memory_nodes
                SET entity_id = %s
                WHERE id = %s
            """, (str(entity_id) if entity_id else None, node_id))

    def _log_summary(self):
        """Log import summary."""
        logger.info("=" * 60)
        logger.info("Import Summary")
        logger.info("=" * 60)
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import ChatGPT conversations with evidence chain")
    parser.add_argument("file", help="Path to ChatGPT export JSON file")
    parser.add_argument("--workspace-id", default="fd0223ed-7aa2-491e-8db5-b0de71b75219",
                       help="Workspace ID")
    parser.add_argument("--limit", type=int, default=0,
                       help="Limit number of messages to import (0 = all)")
    args = parser.parse_args()

    importer = ChatGPTImporter(args.workspace_id)
    importer.connect()

    try:
        importer.import_file(args.file)
        logger.info("Import completed successfully!")
    except Exception as e:
        importer.conn.rollback()
        logger.error(f"Import failed: {e}")
        raise
    finally:
        importer.close()


if __name__ == "__main__":
    main()
