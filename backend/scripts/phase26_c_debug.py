import asyncio, logging
from datetime import datetime
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

async def debug():
    engine = create_async_engine(DATABASE_URL, pool_size=2)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    
    try:
        from backend.service.evidence_pipeline_service import EvidencePipelineService
        
        async with factory() as session:
            # Get first evidence
            result = await session.execute(text('''
                SELECT id, content FROM evidences 
                WHERE workspace_id = :ws LIMIT 1
            '''), {'ws': str(WORKSPACE_ID)})
            row = result.fetchone()
            evid_id, content = row
            logger.info(f'Testing evidence: {evid_id}')
            logger.info(f'Content preview: {content[:100] if content else None}')
            
            pipeline = EvidencePipelineService(session)
            
            try:
                result = await pipeline.process_evidence(evid_id, WORKSPACE_ID)
                logger.info(f'Result: success={result.success}, candidate={result.candidate_id}')
                if result.error:
                    logger.info(f'Error: {result.error}')
            except Exception as e:
                logger.error(f'Exception: {e}', exc_info=True)
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(debug())
