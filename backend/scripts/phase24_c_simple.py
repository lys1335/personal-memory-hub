import asyncio, json, logging, sys
from uuid import UUID
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import create_async_engine
from backend.service.evidence_pipeline_service import EvidencePipelineService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    # Enable autocommit for DML
    @event.listens_for(engine.sync_engine, connect)
    def set_autocommit(dbapi_conn, connection_record):
        pass
    
    results = {'total': 0, 'success': 0, 'failed': 0}
    
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT id FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC'), {'wid': str(WORKSPACE_ID)})
        evidence_ids = [r[0] for r in result.fetchall()]
        results['total'] = len(evidence_ids)
        logger.info(f'Total: {len(evidence_ids)}')
        
        await conn.commit()  # Explicit commit after query
        
        # Create session for writes
        from sqlalchemy.ext.asyncio import async_sessionmaker
        factory = async_sessionmaker(engine, expire_on_commit=False)
        
        async with factory() as session:
            pipeline = EvidencePipelineService(session)
            
            for i, ev_id in enumerate(evidence_ids, 1):
                try:
                    outcome = await pipeline.process_evidence(evidence_id=ev_id, workspace_id=WORKSPACE_ID)
                    if outcome.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    logger.error(f'Error {ev_id}: {e}')
                    results['failed'] += 1
                
                if i % 500 == 0:
                    await session.commit()
                    logger.info(f'{i}/{len(evidence_ids)} ({i*100//len(evidence_ids)}%) success={results[success]}')
            
            await session.commit()
            logger.info(f'Final commit done')
    
    await engine.dispose()
    
    with open('/tmp/phase24_c_simple.json', 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f'Done: {results}')
    return results

asyncio.run(run())
