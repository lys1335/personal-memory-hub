import asyncio, json, logging
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.service.evidence_pipeline_service import EvidencePipelineService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

def conv_uuid(obj):
    if isinstance(obj, UUID): return obj
    if hasattr(obj, 'hex'): return UUID(bytes=obj.bytes)
    return UUID(obj)

async def run():
    engine = create_async_engine(DATABASE_URL)
    results = {'total': 0, 'success': 0, 'failed': 0}
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT id FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC'), {'wid': str(WORKSPACE_ID)})
            evidences = [conv_uuid(r[0]) for r in result.fetchall()]
            results['total'] = len(evidences)
            logger.info(f'Total: {len(evidences)}')
            pipeline = EvidencePipelineService(conn)
            for i, ev_id in enumerate(evidences, 1):
                try:
                    outcome = await pipeline.process_evidence(evidence_id=ev_id, workspace_id=WORKSPACE_ID)
                    if outcome.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    results['failed'] += 1
                if i % 1000 == 0:
                    logger.info(f'{i}/{len(evidences)} ({i*100//len(evidences)}%) success={results["success"]}')
    finally:
        await engine.dispose()
    with open('/tmp/phase24_c_final.json', 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f'Done: {results}')

asyncio.run(run())
