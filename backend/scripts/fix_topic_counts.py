"""
Phase 24-E: Batch count fix for existing topic_links
Calculates correct counts from actual data and updates topics table.
"""
import asyncio
import logging
from sqlalchemy import text, update, table, column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'


async def fix_topic_counts():
    """Fix topic counts based on existing topic_links."""
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    
    async with factory() as session:
        # Get all topic_links grouped by topic_id and source_type
        result = await session.execute(text("""
            SELECT 
                topic_id,
                source_type,
                COUNT(*) as link_count
            FROM topic_links
            GROUP BY topic_id, source_type
        """))
        
        rows = result.fetchall()
        logger.info(f"Found {len(rows)} (topic_id, source_type) combinations to update")
        
        # Update each topic's count
        for topic_id, source_type, count in rows:
            if source_type == 'reconstruction':
                count_field = 'reconstruction_count'
            elif source_type == 'evidence':
                count_field = 'evidence_count'
            else:
                logger.warning(f"Unknown source_type: {source_type} for topic {topic_id}")
                continue
            
            topics_table = table('topics', column('id'), column(count_field))
            stmt = update(topics_table)\
                .where(topics_table.c.id == topic_id)\
                .values(**{count_field: count})
            
            await session.execute(stmt)
            logger.info(f"Updated topic {topic_id} ({source_type}): set {count_field} = {count}")
        
        await session.commit()
        logger.info("Topic counts fixed successfully")
    
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(fix_topic_counts())
