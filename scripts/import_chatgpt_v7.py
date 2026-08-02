import json
import re
import sys
import uuid as uuid_module
import logging
import psycopg2
from datetime import datetime
from psycopg2.extras import register_uuid
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def uuid7() -> str:
    """Generate UUIDv7."""
    # Try to use uuid7 package
    try:
        from uuid7 import uuid7 as uuid7_lib
        return str(uuid7_lib())
    except ImportError:
        # Fallback to uuid4
        return str(uuid_module.uuid4())


# Database configuration
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "memory_hub",
    "user": "postgres",
    "password": "postgres"
}

WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"


class ChatGPTFullImporter:
    """Full ChatGPT import with Evidence chain support."""
    
    def __init__(self, workspace_id: str = WORKSPACE_ID):
        self.workspace_id = workspace_id
        self.conn = None
        self.stats = {
            "files_processed": 0,
            "conversations_processed": 0,
            "messages_processed": 0,
            "evidences_created": 0,
            "nodes_created": 0,
            "links_created": 0,
            "entities_created": 0,
            "areas_created": 0,
            "errors": 0
        }
    
    def connect(self):
        """Connect to database."""
        self.conn = psycopg2.connect(**DATABASE_CONFIG)
        register_uuid()
        self.conn.autocommit = False
        logger.info("Connected to database")
    
    def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")
    
    def import_file(self, file_path: str, limit: int = 0):
        """Import ChatGPT export file."""
        logger.info(f"Importing from {file_path}")
        
        # Read and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(data, dict):
            conversations = data.get('conversations', [data])
        else:
            conversations = data
        
        logger.info(f"Found {len(conversations)} conversations")
        
        # Process each conversation (with limit)
        message_count = 0
        for conv in conversations:
            count = self._process_conversation(conv, limit)
            message_count += count
            if limit > 0 and message_count >= limit:
                logger.info(f"Reached limit of {limit} messages")
                break
        
        self.conn.commit()
        self._print_summary()
    
    def _process_conversation(self, conv: dict, limit: int = 0) -> int:
        """Process a single conversation. Returns number of messages processed."""
        conv_title = conv.get("title", "Untitled")
        mapping = conv.get("mapping", {})
        
        logger.info(f"Processing conversation: {conv_title} ({len(mapping)} messages)")
        
        # Create area for this conversation
        area_id = self._create_or_get_area(
            f"ChatGPT: {conv_title[:50]}",
            f"ChatGPT conversation: {conv_title}"
        )
        
        # Process messages
        count = 0
        for msg_id, entry in mapping.items():
            # Check limit
            if limit > 0 and count >= limit:
                logger.info(f"Reached limit of {limit} messages")
                break

            # Resolve message entry
            msg = self._resolve_message_entry(entry)
            if not msg:
                logger.info(f"Failed to resolve entry for {msg_id}: {list(entry.keys())[:5]}")
                continue

            logger.info(f"Entry {msg_id}: keys={list(msg.keys())[:5]}, author_role={msg.get('author_role')}")

            # Only process user messages
            # Handle different formats:
            # - Simplified: msg has "author_role" field directly
            # - Original: msg has "author" dict with "role" field
            if "author_role" in msg:
                role = msg.get("author_role", "")
            else:
                author = msg.get("author", {})
                role = author.get("role", "") if isinstance(author, dict) else ""
            
            if role != "user":
                logger.info(f"Skipping non-user message: role={role}")
                continue

            logger.info(f"User message found: {msg_id[:8]}, role={role}")

            # Extract content
            content = self._extract_content(msg)

            # Debug: log skipped messages
            if not content or len(content.strip()) < 5:
                logger.info(f"Skipping message {msg_id}: empty or short content (role={role})")
            else:
                logger.info(f"Processing message {msg_id}: {content[:60]}...")
            
            try:
                # Step 1: Create Evidence
                evidence_id = self._create_evidence(content, msg_id, conv_title)
                
                # Step 2: Create MemoryNode
                node_id = self._create_memory_node(content, evidence_id)
                
                # Step 3: Create link
                self._create_evidence_link(node_id, evidence_id)
                
                # Step 4: Extract and create Entity/Area
                entity_id, area_id = self._extract_and_create_entity_area(content)
                
                # Step 5: Update node with entity/area
                self._update_node_entity_area(node_id, entity_id, area_id)
                
                count += 1
                self.stats["messages_processed"] += 1
                
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Error importing message {msg_id}: {e}")
        
        self.stats["conversations_processed"] += 1
        logger.info(f"Processed {count} messages from {conv_title}")
        
        return count
    
    def _resolve_message_entry(self, entry: dict) -> dict | None:
        """Resolve message entry from different formats."""
        # Handle simplified format: entry IS the message with flat structure
        # Keys: author_role, content_type, content_parts, create_time
        if "author_role" in entry:
            return entry
        
        # Handle original format with nested message
        if "message" in entry:
            return entry["message"]
        
        logger.debug(f"Unknown entry format: {list(entry.keys())}")
        return None
    
    def _extract_content(self, msg: dict) -> str:
        """Extract text content from message."""
        # Handle simplified format: content_parts is array of strings
        if "content_parts" in msg:
            parts = msg.get("content_parts", [])
            if isinstance(parts, list) and parts:
                # Filter text-only parts and join
                text_parts = [p for p in parts if isinstance(p, str) and p.strip()]
                return "\n".join(text_parts).strip()
            return str(parts) if parts else ""
        
        # Handle original format with nested content object
        content = msg.get("content", {})
        if isinstance(content, dict):
            parts = content.get("parts", [])
            if isinstance(parts, list):
                text_parts = []
                for part in parts:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict):
                        text = part.get("text", part.get("content", ""))
                        if text:
                            text_parts.append(str(text))
                return "\n".join(text_parts).strip()
        
        # Fallback: return the whole msg as string
        return str(msg).strip()
    
    def _create_evidence(self, content: str, msg_id: str, conv_title: str) -> str:
        """Create Evidence record. Returns evidence_id as UUIDv7 string."""
        evidence_id = uuid7()
        now = datetime.utcnow()
        
        meta = json.dumps({
            "source_type": "chatgpt",
            "source_id": msg_id,
            "conversation_title": conv_title,
            "created_via": "import_script",
            "uuid_version": "v7" if evidence_id.startswith('0') else "v4"
        })
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO evidences (
                    id, workspace_id, source_type, source_id, content, meta, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                evidence_id, str(self.workspace_id), "chatgpt",
                msg_id, content[:10000], meta, now
            ))
        
        self.conn.commit()
        self.stats["evidences_created"] += 1
        logger.debug(f"Created evidence: {evidence_id}")
        return evidence_id
    
    def _create_memory_node(self, content: str, evidence_id: str) -> str:
        """Create MemoryNode record. Returns node_id as UUIDv7 string."""
        node_id = uuid7()
        now = datetime.utcnow()
        
        evidence_links = json.dumps([{
            "evidence_id": evidence_id,
            "weight": 0.8
        }])
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_nodes (
                    id, workspace_id, type, content, meta,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                node_id, str(self.workspace_id), "extraction",
                content[:5000], evidence_links, now, now
            ))
        
        self.conn.commit()
        self.stats["nodes_created"] += 1
        logger.debug(f"Created node: {node_id}")
        return node_id
    
    def _create_evidence_link(self, node_id: str, evidence_id: str):
        """Create memory_evidences link."""
        link_id = uuid7()
        now = datetime.utcnow()
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_evidences (
                    id, memory_node_id, evidence_id, relationship_type, created_at
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                link_id, node_id, evidence_id,
                "evidenced_by", now
            ))
        
        self.conn.commit()
        self.stats["links_created"] += 1
    
    def _update_node_entity_area(self, node_id: str, entity_id: str | None, area_id: str | None):
        """Update node with entity and area references."""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE memory_nodes
                SET entity_id = %s, area_id = %s, updated_at = %s
                WHERE id = %s
            """, (entity_id, area_id, datetime.utcnow(), node_id))
    
    def _extract_and_create_entity_area(self, content: str) -> tuple:
        """Extract entity and area from content."""
        entity_id = None
        area_id = None
        
        content_lower = content.lower()
        
        # Extract person names
        person_patterns = [
            (r'老婆[^，。]+?([^，。]+?)[,。]', '老婆'),
            (r'妻子[^，。]+?([^，。]+?)[,。]', '妻子'),
            (r'名字[^是]+?([^，。]+?)[,。]', '名字'),
            (r'叫[^，。]+?([^，。]+?)[,。]', '叫'),
        ]
        for pattern, label in person_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1).strip('，。、')
                entity_key = f"Person/{name}"
                entity_id = self._create_or_get_entity(
                    "person", entity_key, f"Person mentioned: {name}"
                )
                if entity_id:
                    self.stats["entities_created"] += 1
                break
        
        # Extract keywords for area
        keywords = []
        keyword_patterns = [
            (r'ollama', 'AI/LLM'),
            (r'deepseek', 'AI/LLM'),
            (r'next\.js', 'Development'),
            (r'python', 'Development'),
            (r'web', 'Development'),
            (r'chatgpt', 'AI/LLM'),
        ]
        for pattern, category in keyword_patterns:
            if re.search(pattern, content_lower):
                if category not in keywords:
                    keywords.append(category)
        
        if keywords:
            area_name = f"Personal/{keywords[0]}"
            area_id = self._create_or_get_area(area_name, f"Area for: {', '.join(keywords)}")
            if area_id:
                self.stats["areas_created"] += 1
        
        return entity_id, area_id
    
    def _create_or_get_area(self, name: str, description: str) -> str | None:
        """Create or get existing area. Returns area_id as string."""
        area_id = uuid7()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO areas (id, workspace_id, name, description, sort_order, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, name) DO UPDATE SET name = areas.name
                RETURNING id
            """, (
                area_id, str(self.workspace_id), name, description[:500], 0,
                datetime.utcnow()
            ))
            row = cur.fetchone()
            return row[0] if row else None
    
    def _create_or_get_entity(self, entity_type: str, canonical_name: str, description: str) -> str | None:
        """Create or get existing entity. Returns entity_id as string."""
        entity_id = uuid7()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO entities (
                    id, workspace_id, entity_type, canonical_name, description, _meta, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, entity_type, canonical_name) DO NOTHING
                RETURNING id
            """, (
                entity_id, str(self.workspace_id), entity_type, canonical_name,
                description[:500], '{"auto_extracted": true}', datetime.utcnow()
            ))
            row = cur.fetchone()
            return row[0] if row else None
    
    def _print_summary(self):
        """Print import summary."""
        logger.info("=" * 50)
        logger.info("Import Summary")
        logger.info("=" * 50)
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 50)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import ChatGPT conversations with full evidence chain")
    parser.add_argument("file", help="Path to ChatGPT export JSON file")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of messages to import")
    parser.add_argument("--workspace-id", default=WORKSPACE_ID, help="Workspace ID")
    
    args = parser.parse_args()
    
    # Validate file
    if not Path(args.file).exists():
        logger.error(f"File not found: {args.file}")
        sys.exit(1)
    
    # Create importer and run
    importer = ChatGPTFullImporter(workspace_id=args.workspace_id)
    importer.connect()
    
    try:
        importer.import_file(args.file, limit=args.limit)
        logger.info("Import completed successfully")
    except Exception as e:
        logger.error(f"Import failed: {e}")
        importer.conn.rollback()
        sys.exit(1)
    finally:
        importer.disconnect()


if __name__ == "__main__":
    main()
