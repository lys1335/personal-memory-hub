"""
Phase 24-C: Evidence → Candidate Full Formation
Processes all 15,662 evidences through the pipeline.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.service.evidence_pipeline_service import EvidencePipelineService
from backend.context.context_window import ContextWindowFormulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')

async def run():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'errors': [],
        'start_time': datetime.now().isoformat(),
    }
    
    try:
        async with SessionLocal() as session:
            # Get all evidences
            stmt = text('SELECT id, content, evidence_type, source, workspace_id, created_at FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC')
            result = await session.execute(stmt, {'wid': str(WORKSPACE_ID)})
            evidences = result.fetchall()
            
            results['total'] = len(evidences)
            logger.info(f'Total evidences to process: {len(evidences)}')
            
            pipeline = EvidencePipelineService(session)
            formulator = ContextWindowFormulator(session)
            
            for i, ev in enumerate(evidences, 1):
                evidence_id = UUID(ev[0])
                workspace_id = UUID(ev[4])
                
                try:
                    # Step 1: Form context window
                    ctx = await formulator.formulate(
                        trigger_evidence_id=evidence_id,
                        workspace_id=workspace_id,
                    )
                    
                    # Step 2: Process through pipeline
                    outcome = await pipeline.process_evidence(
                        evidence_id=evidence_id,
                        workspace_id=workspace_id,
                    )
                    
                    if outcome.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        if len(results['errors']) < 10:
                            results['errors'].append({
                                'evidence_id': str(evidence_id),
                                'error': str(outcome.error) if hasattr(outcome, 'error') else 'Unknown error'
                            })
                
                except Exception as e:
                    results['failed'] += 1
                    if len(results['errors']) < 10:
                        results['errors'].append({
                            'evidence_id': str(evidence_id),
                            'error': str(e)
                        })
                
                # Progress reporting
                if i % 1000 == 0:
                    logger.info(f'Processed {i}/{len(evidences)} ({i*100//len(evidences)}%)')
                    
            results['end_time'] = datetime.now().isoformat()
            
    finally:
        await engine.dispose()
    
    # Save results
    with open('/tmp/phase24_c_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f'Results saved to /tmp/phase24_c_results.json')
    logger.info(f'Success: {results["success"]}, Failed: {results["failed"]}')
    
    return results

if __name__ == '__main__':
    asyncio.run(run())
