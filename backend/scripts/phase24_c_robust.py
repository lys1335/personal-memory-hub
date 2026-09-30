import asyncio, json, logging
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.service.evidence_pipeline_service import EvidencePipelineService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

def to_uuid(val):
    if isinstance(val, UUID): return val
    if hasattr(val, 'hex'): return UUID(bytes=val.bytes)
    return UUID(str(val))

async def run():
    engine = create_async_engine(DATABASE_URL)
    results = {'total': 0, 'success': 0, 'failed': 0}
    
    # Fetch all evidence IDs first
    async with engine.begin() as conn:
        result = await conn.execute(
            text('SELECT id FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC'),
            {'wid': str(WORKSPACE_ID)}
        )
        evidence_ids = [to_uuid(r[0]) for r in result.fetchall()]
        results['total'] = len(evidence_ids)
        logger.info(f'Total: {len(evidence_ids)}')
    
    # Process in batches with fresh connections
    batch_size = 100
    for batch_start in range(0, len(evidence_ids), batch_size):
        batch_end = min(batch_start + batch_size, len(evidence_ids))
        batch = evidence_ids[batch_start:batch_end]
        
        async with engine.begin() as conn:
            pipeline = EvidencePipelineService(conn)
            for ev_id in batch:
                try:
                    outcome = await pipeline.process_evidence(evidence_id=ev_id, workspace_id=WORKSPACE_ID)
                    if outcome.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    logger.error(f'Error {ev_id}: {e}')
                    results['failed'] += 1
        
        completed = batch_end
        pct = completed * 100 // len(evidence_ids)
        logger.info(f'{completed}/{len(evidence_ids)} ({pct}%) success={results["success"]}')
    
    await engine.dispose()
    
    with open('/tmp/phase24_c_result.json', 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f'Done: {results}')

asyncio.run(run())
