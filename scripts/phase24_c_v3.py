"""
Phase 24-C v3: Fixed evidence fetching with proper ORM objects
"""
import asyncio
import json
import logging
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.shared.domain.memory_models import Evidence, Workspace
from backend.service.evidence_pipeline_service import EvidencePipelineService

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
            # Fetch all evidence ORM objects
            result = await session.execute(
                text('SELECT id, content, _meta FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC'),
                {'wid': str(WORKSPACE_ID)}
            )
            evidence_rows = result.fetchall()
            results['total'] = len(evidence_rows)
            logger.info(f'Total evidences: {len(evidence_rows)}')
            
            pipeline = EvidencePipelineService(session)
            
            for i, row in enumerate(evidence_rows, 1):
                ev_id = row[0]
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
                    results['failed'] += 1
                
                if i % 1000 == 0:
                    logger.info(f'{i}/{len(evidence_rows)} ({i*100//len(evidence_rows)}%) success={results["success"]}')
            
            await session.commit()
            
    finally:
        await engine.dispose()
    
    with open('/tmp/phase24_c_v3.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f'Final: {results}')
    return results

if __name__ == '__main__':
    asyncio.run(run())
