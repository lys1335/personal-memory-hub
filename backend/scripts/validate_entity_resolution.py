import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/memory_hub"
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"
SAMPLE_SIZE = 100

class EntityResolutionValidator:
    def __init__(self, database_url):
        self.engine = create_async_engine(database_url)

    async def fetch_sample_evidences(self):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT id, content, evidence_type, source, LENGTH(content) as content_length
                FROM evidences
                WHERE workspace_id = :workspace_id
                  AND entity_id IS NULL
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"workspace_id": WORKSPACE_ID, "limit": SAMPLE_SIZE})
            rows = result.fetchall()
            return [{
                "id": str(row[0]),
                "content": row[1],
                "evidence_type": row[2],
                "source": row[3],
                "content_length": row[4],
            } for row in rows]

    async def get_existing_entities(self):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT id, canonical_name, entity_type
                FROM entities
                WHERE workspace_id = :workspace_id
            """), {"workspace_id": WORKSPACE_ID})
            rows = result.fetchall()
            return [{
                "id": str(row[0]),
                "canonical_name": row[1],
                "entity_type": row[2],
            } for row in rows]

    def resolve_entity_simple(self, evidence, entities):
        content = evidence["content"].lower()
        for entity in entities:
            name = entity["canonical_name"].lower()
            if name in content or content in name:
                return {"entity_id": entity["id"], "method": "exact_match", "confidence": 0.95, "rationale": f"Exact match: {entity['canonical_name']}"}
        for entity in entities:
            name = entity["canonical_name"].lower()
            if len(name) >= 3 and name[:3] in content:
                return {"entity_id": entity["id"], "method": "fuzzy_match", "confidence": 0.6, "rationale": f"Prefix match: {entity['canonical_name'][:3]}"}
        return {"entity_id": None, "method": "unresolved", "confidence": 0.0, "rationale": "No match found"}

    async def validate_all(self):
        logger.info("Fetching %d sample evidences...", SAMPLE_SIZE)
        evidences = await self.fetch_sample_evidences()
        logger.info("Fetching existing entities...")
        entities = await self.get_existing_entities()
        logger.info(f"Found {len(entities)} entities")

        stats = {"total": 0, "resolved": 0, "unresolved": 0, "by_method": {"exact_match": 0, "fuzzy_match": 0, "unresolved": 0}, "samples": []}

        for evidence in evidences:
            stats["total"] += 1
            resolution = self.resolve_entity_simple(evidence, entities)
            if resolution["entity_id"]:
                stats["resolved"] += 1
                stats["by_method"][resolution["method"]] += 1
            else:
                stats["unresolved"] += 1
                stats["by_method"]["unresolved"] += 1
            stats["samples"].append({
                "evidence_id": evidence["id"],
                "content_preview": evidence["content"][:100],
                "predicted_entity_id": resolution["entity_id"],
                "method": resolution["method"],
                "confidence": resolution["confidence"],
            })

        stats["resolution_rate"] = round(stats["resolved"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
        return stats

    async def close(self):
        await self.engine.dispose()

async def main():
    validator = EntityResolutionValidator(DATABASE_URL)
    try:
        stats = await validator.validate_all()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    finally:
        await validator.close()

if __name__ == "__main__":
    asyncio.run(main())
