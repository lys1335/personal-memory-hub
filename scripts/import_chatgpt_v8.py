"""
完整的 ChatGPT 导入脚本 - 使用 UUIDv7 并匹配实际数据库schema

流程：
1. 读取 ChatGPT 导出数据
2. 解析对话消息
3. 创建 Evidence 记录（原始内容）
4. 创建 MemoryNode 记录（Level 1 Observation）
5. 创建 memory_evidences 关联
6. 提取并创建 Entity/Area
"""

import json
import re
import sys
import uuid as uuid_module
import time
import logging
import psycopg2
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def uuid7() -> str:
    """Generate UUIDv7 (time-sorted UUID) as a string.
    
    UUIDv7 format:
    - 48 bits: Unix timestamp in milliseconds
    - 4 bits: Version (0b0111 = 7)
    - 2 bits: Variant (0b10)
    - 62 bits: Random/counter
    """
    import os
    
    # Get current timestamp in milliseconds
    ts_ms = int(time.time() * 1000)
    
    # Build 128-bit integer
    bits = 0
    
    # Timestamp (48 bits)
    bits |= (ts_ms & 0xFFFFFFFFFFFF) << 80
    
    # Version 7 (4 bits at position 76-79)
    bits |= 0x7 << 76
    
    # Random bits (62 bits)
    rand = int.from_bytes(os.urandom(8), 'big') & 0x3FFFFFFFFFFFFFFF
    bits |= rand
    
    # Format as UUID string manually
    hex_str = f'{bits:032x}'
    return f'{hex_str[0:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}'


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
    """Full ChatGPT import with Evidence chain support - matches actual DB schema."""
    
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
        from psycopg2.extras import register_uuid
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
                logger.info(f"Reached limit of {limit} messages total")
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
            # Check limit (only if limit > 0)
            if limit > 0 and count >= limit:
                logger.info(f"Reached limit of {limit} messages")
                break
            
            # Resolve message entry
            msg = self._resolve_message_entry(entry)
            if not msg:
                logger.info(f"Failed to resolve entry for {msg_id}: {list(entry.keys())[:5]}")
                continue
            
            # Only process user and assistant messages (skip system/other roles)
            if "author_role" in msg:
                role = msg.get("author_role", "")
            else:
                author = msg.get("author", {})
                role = author.get("role", "") if isinstance(author, dict) else ""
            
            # Skip non-content messages (system prompts, etc.)
            if role not in ("user", "assistant"):
                logger.info(f"Skipping message: role={role}")
                continue
            
            # Extract content
            content = self._extract_content(msg)
            
            # Skip very short messages (less than 3 chars)
            if not content or len(content.strip()) < 3:
                logger.info(f"Skipping message {msg_id}: empty or very short content")
                continue
            
            logger.info(f"Processing message {msg_id}: {content[:60]}...")
            
            try:
                # Step 1: Create Evidence (Level 1 - raw content)
                evidence_id = self._create_evidence(content, msg_id, conv_title, role)
                
                # Step 2: Create MemoryNode (Level 1 - Observation)
                node_id = self._create_memory_node(content, evidence_id)
                
                # Step 3: Create link
                self._create_evidence_link(node_id, evidence_id)
                
                # Step 4: Extract and create Entity/Area
                entity_id, area_id = self._extract_and_create_entity_area(content, area_id, role)
                
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
        
        # Fallback
        return str(msg).strip()
    
    def _create_evidence(self, content: str, msg_id: str, conv_title: str, role: str = "user") -> str:
        """Create Evidence record. Returns evidence_id as string."""
        evidence_id = uuid7()
        now = datetime.utcnow()
        
        meta = json.dumps({
            "source_type": "chatgpt",
            "source_id": msg_id,
            "conversation_title": conv_title,
            "message_role": role,
            "created_via": "import_script",
            "uuid_version": "v7"
        })
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO evidences (
                    id, workspace_id, source, evidence_type, content, raw_content,
                    confidence, importance, signal_strength, _meta, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                evidence_id, str(self.workspace_id), "chatgpt", 
                "user_input" if role == "user" else "assistant_response",
                content[:10000], content[:10000],
                0.9, 0.5, 0.5, meta, now, now
            ))
        
        self.conn.commit()
        self.stats["evidences_created"] += 1
        logger.debug(f"Created evidence: {evidence_id}")
        return evidence_id
    
    def _create_memory_node(self, content: str, evidence_id: str) -> str:
        """Create MemoryNode record. Returns node_id as string."""
        node_id = uuid7()
        now = datetime.utcnow()
        
        evidence_links = json.dumps([{
            "evidence_id": evidence_id,
            "contribution_weight": 0.8
        }])
        
        meta = json.dumps({
            "created_via": "import_script",
            "level": 1
        })
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_nodes (
                    id, workspace_id, level, node_type, content,
                    confidence, importance, signal_strength, status, source,
                    generated_by, evidence_links, contradict_evidence, _meta,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                node_id, str(self.workspace_id), 1, "Observation",
                content[:5000], 0.9, 0.5, 0.5,
                "active", "import", "import",
                evidence_links, json.dumps([]), meta,
                now, now
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
                    id, workspace_id, memory_node_id, evidence_id,
                    relationship_type, contribution_weight, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                link_id, str(self.workspace_id), node_id, evidence_id,
                "derived_from", 0.8, now
            ))
        
        self.conn.commit()
        self.stats["links_created"] += 1
    
    def _update_node_entity_area(self, node_id: str, entity_id: Optional[str], area_id: Optional[str]):
        """Update node with entity reference."""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE memory_nodes
                SET entity_id = %s, updated_at = %s
                WHERE id = %s
            """, (entity_id, datetime.utcnow(), node_id))
    
    def _extract_and_create_entity_area(self, content: str, parent_area_id: Optional[str] = None, role: str = "user") -> tuple:
        """Extract entity and area from content.
        
        Args:
            content: Message content
            parent_area_id: Parent area ID
            role: Message role (user/assistant) - affects extraction weight
        """
        entity_id = None
        area_id = parent_area_id
        
        content_lower = content.lower()
        
        # Different extraction strategies based on role
        # Assistant responses often contain more structured information
        if role == "assistant":
            # For assistant: extract from explanations and suggestions
            entity_id = self._extract_from_assistant_response(content)
        else:
            # For user: extract from questions and statements
            entity_id = self._extract_from_user_input(content)
        
        # Extract area from both (with higher weight for assistant)
        area_id = self._extract_and_create_area(content, parent_area_id, role)
        
        return entity_id, area_id
    
    def _extract_from_user_input(self, content: str) -> Optional[str]:
        """Extract entity from user input."""
        content_lower = content.lower()
        
        # Extract project names (common patterns)
        project_patterns = [
            r'项目[：:]\s*(\w+)',
            r'project[：:\s]+(\w+)',
            r'用(\w+)做',
            r'关于(\w+)的',
            r'(\w+)[项目/任务]',
        ]
        for pattern in project_patterns:
            match = re.search(pattern, content)
            if match:
                project_name = match.group(1).strip()
                if len(project_name) > 2:
                    entity_id = self._create_or_get_entity(
                        "Project", f"Project/{project_name}", f"Project mentioned by user: {project_name}"
                    )
                    if entity_id:
                        self.stats["entities_created"] += 1
                    return entity_id
        
        # Extract tool names
        tool_patterns = [
            r'(Ollama|DeepSeek|ChatGPT|Claude|GPT)[-_\s]*(\w+)?',
            r'用(\w+)[工具/模型/框架]',
            r'(\w+)[API/SDK]',
        ]
        for pattern in tool_patterns:
            match = re.search(pattern, content)
            if match:
                tool_name = match.group(1)
                entity_id = self._create_or_get_entity(
                    "Tool", f"Tool/{tool_name}", f"Tool mentioned: {tool_name}"
                )
                if entity_id:
                    self.stats["entities_created"] += 1
                return entity_id
        
        return None
    
    def _extract_from_assistant_response(self, content: str) -> Optional[str]:
        """Extract entity from assistant response (higher quality)."""
        content_lower = content.lower()
        
        # Assistant responses often contain structured information
        # Extract key concepts, entities, and topics
        
        # Look for bullet points or numbered lists
        patterns = [
            r'[•\-*]\s*(\w+[^\n]{5,50})',
            r'\d+\.\s*(\w+[^\n]{5,50})',
            r'###\s*(\w+[^\n]{5,50})',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                concept = match.group(1).strip()
                if len(concept) > 3 and len(concept) < 100:
                    entity_id = self._create_or_get_entity(
                        "Concept", f"Concept/{concept[:50]}", f"Concept from assistant: {concept[:100]}"
                    )
                    if entity_id:
                        self.stats["entities_created"] += 1
                    return entity_id
        
        # Extract technical terms
        tech_terms = [
            r'(PostgreSQL|Supabase|Docker|Kubernetes)',
            r'(React|Vue|Next\.js|Python)',
            r'(FastAPI|SQLAlchemy|Pydantic)',
        ]
        for pattern in tech_terms:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                term = match.group(1)
                entity_id = self._create_or_get_entity(
                    "Tool", f"Tool/{term}", f"Technology mentioned: {term}"
                )
                if entity_id:
                    self.stats["entities_created"] += 1
                return entity_id
        
        return None
    
    def _extract_and_create_area(self, content: str, parent_area_id: Optional[str], role: str) -> Optional[str]:
        """Extract and create area from content."""
        content_lower = content.lower()
        
        # Area keywords with weights
        area_keywords = [
            (r'ollama|deepseek|chatgpt|claude|gpt|llm|ai|模型|大模型', 'AI/LLM'),
            (r'python|javascript|react|vue|next|web|开发|编程', 'Development'),
            (r'docker|kubernetes|部署|服务器|数据库|postgresql', 'DevOps'),
            (r'投资|理财|股票|基金|nisa', 'Finance'),
            (r'生活|家庭|孩子|日本', 'Personal'),
            (r'文档|写作|翻译|日语', 'Content'),
        ]
        
        keywords = []
        for pattern, category in area_keywords:
            if re.search(pattern, content_lower):
                if category not in keywords:
                    keywords.append(category)
        
        if keywords:
            area_name = f"Personal/{keywords[0]}"
            area_id = self._create_or_get_area(area_name, f"Area for: {', '.join(keywords)}")
            if area_id:
                self.stats["areas_created"] += 1
            return area_id
        
        return parent_area_id
    
    def _create_or_get_area(self, name: str, description: str) -> Optional[str]:
        """Create or get existing area. Returns area_id as string."""
        area_id = uuid7()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO areas (id, workspace_id, parent_area_id, name, description, sort_order, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, name) DO UPDATE SET name = areas.name
                RETURNING id
            """, (
                area_id, str(self.workspace_id), None, name, description[:500], 0,
                datetime.utcnow()
            ))
            row = cur.fetchone()
            return str(row[0]) if row else None
    
    def _create_or_get_entity(self, entity_type: str, canonical_name: str, description: str) -> Optional[str]:
        """Create or get existing entity. Returns entity_id as string."""
        entity_id = uuid7()
        # Truncate canonical_name to fit VARCHAR(255)
        canonical_name = canonical_name[:250] + '...' if len(canonical_name) > 250 else canonical_name
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
            return str(row[0]) if row else None
    
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
