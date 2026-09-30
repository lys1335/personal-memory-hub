import asyncio
import json
import logging
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.service.evidence_pipeline_service import EvidencePipelineService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

def convert_uuid(obj):
    if isinstance(obj, UUID): return obj
    if hasattr(obj, 'hex'): return UUID(bytes=obj.bytes)
    return UUID(obj)

async def run():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    results = {'total': 0, 'success': 0, 'failed': 0, 'errors': []}
    try:
        async with SessionLocal() as session:
            stmt = text('SELECT id FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC')
            result = await session.execute(stmt, {'wid': str(WORKSPACE_ID)})
            evidences = [convert_uuid(r[0]) for r in result.fetchall()]
            results['total'] = len(evidences)
            logger.info(f'Total evidences: {len(evidences)}')
            pipeline = EvidencePipelineService(session)
            for i, ev_id in enumerate(evidences, 1):
                try:
                    outcome = await pipeline.process_evidence(evidence_id=ev_id, workspace_id=WORKSPACE_ID)
                    if outcome.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    results['failed'] += 1
                    if len(results['errors']) < 5:
                        results['errors'].append(str(e))
                if i % 1000 == 0:
                    logger.info(f'Processed {i}/{len(evidences)} ({i*100//len(evidences)}%)')
    finally:
        await engine.dispose()
    with open('/tmp/phase24_c_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f'Results: {results}')

asyncio.run(run())
