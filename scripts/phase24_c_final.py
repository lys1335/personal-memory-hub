"""
Phase 24-C: Evidence → Candidate Full Formation (Fixed)
Uses ORM to ensure proper UUID handling
"""
import asyncio
import json
import logging
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.service.evidence_pipeline_service import EvidencePipelineService
from backend.shared.domain.memory_models import Evidence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

async def run():
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    results = {'total': 0, 'success': 0, 'failed': 0}
    
    try:
        async with factory() as session:
            # Fetch all evidence IDs using ORM
            result = await session.execute(
                text('SELECT id FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC'),
                {'wid': str(WORKSPACE_ID)}
            )
            evidence_ids = [UUID(r[0]) for r in result.fetchall()]
            results['total'] = len(evidence_ids)
            logger.info(f'Total evidences: {len(evidence_ids)}')
            
            pipeline = EvidencePipelineService(session)
            
            for i, ev_id in enumerate(evidence_ids, 1):
                try:
                    outcome = await pipeline.process_evidence(
                        evidence_id=ev_id,
                        workspace_id=WORKSPACE_ID
                    )
                    if outcome.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    logger.error(f'Error {ev_id}: {e}')
                    results['failed'] += 1
                
                if i % 1000 == 0:
                    await session.commit()
                    logger.info(
                        f'{i}/{len(evidence_ids)} ({i*100//len(evidence_ids)}%) '
                        f'success={results["success"]}'
                    )
            
            await session.commit()
            logger.info('Final commit done')
            
    finally:
        await engine.dispose()
    
    with open('/tmp/phase24_c_result.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f'Final Results: {results}')
    return results

if __name__ == '__main__':
    asyncio.run(run())
