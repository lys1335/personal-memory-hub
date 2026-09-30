import asyncio, json, logging
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.service.evidence_pipeline_service import EvidencePipelineService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

def to_uuid(val):
    if isinstance(val, UUID): return val
    if hasattr(val, 'bytes'): return UUID(bytes=val.bytes)
    return UUID(str(val))

async def run():
    engine = create_async_engine(DATABASE_URL)
    
    # Get all evidence IDs
    async with engine.begin() as conn:
        result = await conn.execute(
            text('SELECT id FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC'),
            {'wid': str(WORKSPACE_ID)}
        )
        evidence_ids = [to_uuid(r[0]) for r in result.fetchall()]
    
    logger.info(f'Total: {len(evidence_ids)}')
    
    results = {'total': len(evidence_ids), 'success': 0, 'failed': 0}
    
    # Process each evidence individually with fresh connection
    for i, ev_id in enumerate(evidence_ids, 1):
        try:
            async with engine.begin() as conn:
                # Use explicit session
                from sqlalchemy.orm import Session
                async_session = async_sessionmaker(conn, expire_on_commit=False)
                session = async_session()
                
                pipeline = EvidencePipelineService(session)
                outcome = await pipeline.process_evidence(
                    evidence_id=ev_id,
                    workspace_id=WORKSPACE_ID
                )
                
                if outcome.success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                # Explicit commit
                await session.commit()
                
        except Exception as e:
            logger.error(f'Error {ev_id}: {e}')
            results['failed'] += 1
        
        if i % 100 == 0:
            logger.info(f'{i}/{len(evidence_ids)} ({i*100//len(evidence_ids)}%) success={results[success]}')
    
    await engine.dispose()
    
    with open('/tmp/phase24_c_result.json', 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f'Done: {results}')

asyncio.run(run())
