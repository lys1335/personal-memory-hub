"""
Evidence Chain Fixer - Run on host to fix existing data

This script directly connects to the PostgreSQL database and
fixes the evidence chain for existing memory nodes.
"""

import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR / "src"))

import psycopg2
import psycopg2.extras
from psycopg2.extras import register_uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Database configuration - connect to Docker PostgreSQL
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "memory_hub",
    "user": "postgres",
    "password": "postgres",
}


class EvidenceChainFixer:
    """Fix evidence chain for existing memory nodes."""

    def __init__(self, dry_run: bool = True, limit: int = 0):
        self.dry_run = dry_run
        self.limit = limit
        self.stats = {
            "total": 0,
            "processed": 0,
            "errors": 0,
            "evidences_created": 0,
            "entities_created": 0,
            "areas_created": 0,
            "nodes_updated": 0,
            "links_created": 0,
        }
        self.conn = None

    def run(self):
        """Execute the batch fix."""
        logger.info("=" * 60)
        logger.info("Evidence Chain Fixer - Batch Repair Script")
        logger.info("=" * 60)
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Limit: {self.limit or 'all'}")
        logger.info("")

        # Connect to database
        self.conn = psycopg2.connect(**DATABASE_CONFIG)
        register_uuid()  # Register UUID adapter for psycopg2
        self.conn.autocommit = False

        try:
            # Step 1: Get all memory_nodes without entity_id
            logger.info("Step 1: Loading memory nodes without entity_id...")
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, workspace_id, content, level, source, created_at
                    FROM memory_nodes
                    WHERE entity_id IS NULL
                    ORDER BY created_at ASC
                    LIMIT %s
                """, (self.limit if self.limit > 0 else None,))
                nodes = cur.fetchall()
            self.stats["total"] = len(nodes)
            logger.info(f"  Found {len(nodes)} nodes to fix")
            logger.info("")

            if not nodes:
                logger.info("No nodes to fix. Exiting.")
                return

            # Step 2: Get existing entities and areas
            logger.info("Step 2: Loading existing entities and areas...")
            with self.conn.cursor() as cur:
                cur.execute("SELECT canonical_name, id FROM entities")
                existing_entities = {row[0]: row[1] for row in cur.fetchall()}
                cur.execute("SELECT name, id FROM areas")
                existing_areas = {row[0]: row[1] for row in cur.fetchall()}
            logger.info(f"  Existing entities: {len(existing_entities)}")
            logger.info(f"  Existing areas: {len(existing_areas)}")
            logger.info("")

            # Step 3: Process each node
            logger.info("Step 3: Processing nodes...")
            logger.info("-" * 60)

            for idx, node in enumerate(nodes):
                try:
                    node_id = str(node[0])
                    workspace_id = node[1]
                    content = node[2]

                    self.stats["processed"] += 1

                    # 3.1: Create Evidence record
                    evidence_id = self._create_evidence(workspace_id, content, node_id)
                    self.stats["evidences_created"] += 1

                    # 3.2: Extract entity and area
                    entity_id, area_id = self._extract_entity_area(
                        content, workspace_id, existing_entities, existing_areas
                    )

                    # 3.3: Update memory_node
                    self._update_node(node_id, workspace_id, entity_id, area_id, evidence_id)
                    self.stats["nodes_updated"] += 1
                    if entity_id:
                        self.stats["entities_created"] += 1
                    if area_id:
                        self.stats["areas_created"] += 1

                    # 3.4: Create memory_evidences link
                    self._create_memory_evidence(workspace_id, node_id, evidence_id)
                    self.stats["links_created"] += 1

                    # Progress display
                    if (idx + 1) % 100 == 0:
                        logger.info(f"  Progress: {idx + 1}/{len(nodes)}")

                except Exception as e:
                    self.stats["errors"] += 1
                    logger.error(f"  Error processing node {node[0]}: {e}")

            logger.info("-" * 60)

            # Step 4: Output summary
            logger.info("")
            logger.info("Step 4: Summary")
            logger.info("=" * 60)
            for key, value in self.stats.items():
                logger.info(f"  {key}: {value}")
            logger.info("=" * 60)

            if self.dry_run:
                self.conn.rollback()
                logger.info("")
                logger.info("This was a DRY RUN. No changes were committed.")
                logger.info("Remove --dry-run to apply changes.")
            else:
                self.conn.commit()
                logger.info("")
                logger.info("Changes committed to database.")

        finally:
            if self.conn:
                self.conn.close()

    def _create_evidence(self, workspace_id: UUID, content: str, node_id: str) -> UUID:
        """Create an Evidence record."""
        evidence_id = UUID(int=__import__('uuid').uuid4().int)

        content_safe = content[:10000] if len(content) > 10000 else content
        meta = f'{{"memory_node_id": "{node_id}", "original_source": "chatgpt", "auto_extracted": true}}'

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO evidences (id, workspace_id, entity_id, area_id, content, evidence_type, source,
                                     confidence, importance, signal_strength, _meta, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                evidence_id, workspace_id, None, None, content_safe, "import", "chatgpt",
                0.8, 0.5, 0.6, meta, datetime.utcnow()
            ))
        return evidence_id

    def _extract_entity_area(self, content: str, workspace_id: UUID,
                             existing_entities: dict, existing_areas: dict) -> tuple:
        """Extract entity and area from content using keyword matching."""
        entity_id = None
        area_id = None

        content_lower = content.lower()

        # Extract person names (simple heuristic)
        person_patterns = [
            (r'老婆.*?([^\s,。]+)', '老婆'),
            (r'妻子.*?([^\s,。]+)', '妻子'),
            (r'名字叫([^\s,。]+)', '名字'),
            (r'叫.*?([^\s,。]+)', '叫'),
        ]
        for pattern, label in person_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1).strip('，。、')
                entity_key = f"Person/{name}"
                if entity_key not in existing_entities:
                    entity_id = self._create_entity(workspace_id, "Person", entity_key, name)
                    existing_entities[entity_key] = entity_id
                else:
                    entity_id = existing_entities[entity_key]
                break

        # Extract areas
        area_keywords = {
            "Work": ["code", "project", "java", "rust", "work", "开发", "代码", "项目", "工作"],
            "Family": ["wife", "husband", "child", "family", "老婆", "孩子", "家庭", "家"],
            "Project": ["memory hub", "pmh", "personal", "hub", "项目"],
            "Finance": ["nisa", "investment", "stock", "finance", "投资", "股票", "钱"],
            "Travel": ["travel", "paris", "tokyo", "旅行", "旅游", "住"],
        }

        for area_name, keywords in area_keywords.items():
            if any(kw in content_lower for kw in keywords):
                if area_name not in existing_areas:
                    area_id = self._create_area(workspace_id, area_name, area_name)
                    existing_areas[area_name] = area_id
                else:
                    area_id = existing_areas[area_name]
                break

        return entity_id, area_id

    def _create_entity(self, workspace_id: UUID, entity_type: str, canonical_name: str, description: str) -> UUID:
        """Create an Entity record."""
        entity_id = UUID(int=__import__('uuid').uuid4().int)

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO entities (id, workspace_id, entity_type, canonical_name, description, _meta, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, entity_type, canonical_name) DO NOTHING
            """, (
                entity_id, workspace_id, entity_type, canonical_name, description[:500],
                f'{{"auto_extracted": true, "source": "batch_fix"}}', datetime.utcnow()
            ))
        return entity_id

    def _create_area(self, workspace_id: UUID, name: str, description: str) -> UUID:
        """Create an Area record."""
        area_id = UUID(int=__import__('uuid').uuid4().int)

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO areas (id, workspace_id, name, description, sort_order, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, name) DO NOTHING
            """, (
                area_id, workspace_id, name, description[:500], 0, datetime.utcnow()
            ))
        return area_id

    def _update_node(self, node_id: str, workspace_id: UUID,
                     entity_id, area_id, evidence_id: UUID):
        """Update memory_node with entity_id and area_id."""
        # Build evidence_links JSON safely
        import json
        evidence_link = json.dumps([{"evidence_id": str(evidence_id), "weight": 0.8}])

        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE memory_nodes
                SET entity_id = %s,
                    evidence_links = %s::jsonb
                WHERE id = %s
            """, (
                str(entity_id) if entity_id else None,
                evidence_link,
                node_id,
            ))

    def _create_memory_evidence(self, workspace_id: UUID, node_id: str, evidence_id: UUID):
        """Create memory_evidences link."""
        link_id = UUID(int=__import__('uuid').uuid4().int)

        with self.conn.cursor() as cur:
            # 不使用 ON CONFLICT，因为表可能没有 UNIQUE constraint
            cur.execute("""
                INSERT INTO memory_evidences (id, workspace_id, memory_node_id, evidence_id,
                                              relationship_type, contribution_weight, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                link_id, workspace_id, node_id, evidence_id, "supports", 0.8, datetime.utcnow()
            ))
            # 检查是否已存在（通过查询）
            cur.execute("""
                SELECT 1 FROM memory_evidences
                WHERE workspace_id = %s AND memory_node_id = %s AND evidence_id = %s
                LIMIT 1
            """, (workspace_id, node_id, evidence_id))
            if cur.fetchone():
                # 已存在，删除刚插入的
                cur.execute("DELETE FROM memory_evidences WHERE id = %s", (link_id,))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix evidence chain for existing memory nodes")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of nodes to process (0 = all)")
    args = parser.parse_args()

    fixer = EvidenceChainFixer(dry_run=args.dry_run, limit=args.limit)
    fixer.run()


if __name__ == "__main__":
    main()
