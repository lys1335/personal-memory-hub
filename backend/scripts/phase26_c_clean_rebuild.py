#!/usr/bin/env python3
import asyncio, logging, sys, time
from datetime import datetime
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')
BATCH_SIZE = 50
REPORT_INTERVAL = 100
ANTI_COLLAPSE_THRESHOLD = 0.5

async def clean_rebuild():
    logger.info('='*80)
    logger.info('Phase 26-C: Entity Resolution Clean Rebuild')
    logger.info('='*80)
    logger.info(f'Started: {datetime.now().isoformat()}')
    
    engine = create_async_engine(DATABASE_URL, pool_size=5)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    
    try:
        # Step 1: Clear old data
        logger.info('[1/5] Clearing old data...')
        async with factory() as session:
            await session.execute(text('TRUNCATE topic_links CASCADE'))
            await session.execute(text('TRUNCATE reconstructions CASCADE'))
            await session.execute(text('TRUNCATE candidates CASCADE'))
            await session.execute(text('TRUNCATE proposals CASCADE'))
            await session.execute(text('TRUNCATE memory_nodes CASCADE'))
            await session.commit()
        
        async with factory() as session:
            result = await session.execute(text('SELECT COUNT(*) FROM candidates'))
            assert result.scalar() == 0
        
        # Step 2: Run pipeline
        logger.info('[2/5] Running EvidencePipelineService...')
        from backend.service.evidence_pipeline_service import EvidencePipelineService
        
        start_time = time.time()
        processed = 0
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        # Get all evidences first
        async with factory() as session:
            result = await session.execute(text('''
                SELECT id FROM evidences 
                WHERE workspace_id = :ws
                ORDER BY created_at
            '''), {'ws': str(WORKSPACE_ID)})
            evidences = [row[0] for row in result.fetchall()]
        
        logger.info(f'  Total evidences: {len(evidences)}')
        logger.info(f'  Processing...')
        logger.info('')
        
        # Process each evidence with fresh session
        for i, evid_id in enumerate(evidences):
            try:
                async with factory() as session:
                    pipeline = EvidencePipelineService(session)
                    result = await pipeline.process_evidence(
                        evidence_id=evid_id, 
                        workspace_id=WORKSPACE_ID
                    )
                    processed += 1
                    
                    if result.success and result.candidate_id:
                        success_count += 1
                    elif result.skipped:
                        skipped_count += 1
                    else:
                        error_count += 1
                        
            except Exception as e:
                error_count += 1
            
            # Progress report
            if (i + 1) % REPORT_INTERVAL == 0 or (i + 1) == len(evidences):
                elapsed = time.time() - start_time
                logger.info(f'  Progress: {i+1}/{len(evidences)} ({(i+1)/len(evidences)*100:.1f}%) - {elapsed:.1f}s')
        
        logger.info(f'')
        logger.info(f'  Summary: processed={processed}, success={success_count}, skipped={skipped_count}, errors={error_count}')
        
        # Step 3: Validate
        logger.info('[3/5] Validating results...')
        async with factory() as session:
            r1 = await session.execute(text('''
                SELECT COUNT(*), 
                       COUNT(CASE WHEN entity_id IS NOT NULL THEN 1 END),
                       COUNT(CASE WHEN entity_id IS NULL THEN 1 END)
                FROM candidates WHERE workspace_id = :ws
            '''), {'ws': str(WORKSPACE_ID)})
            total, with_entity, unresolved = r1.fetchone()
            logger.info(f'  Candidates: {total} (with_entity={with_entity}, unresolved={unresolved})')
            
            r2 = await session.execute(text('''
                SELECT e.canonical_name, COUNT(c.id) as cnt
                FROM entities e JOIN candidates c ON c.entity_id = e.id
                WHERE c.workspace_id = :ws
                GROUP BY e.id, e.canonical_name
                ORDER BY cnt DESC LIMIT 30
            '''), {'ws': str(WORKSPACE_ID)})
            rows = r2.fetchall()
            
            logger.info('')
            logger.info('  Top 30 Entities:')
            logger.info(f'  {"Rank":<6}{"Entity":<20}{"Candidates":<12}{"Share":<10}')
            logger.info('  ' + '-'*50)
            
            total_cands = sum(r[1] for r in rows)
            for i, (name, count) in enumerate(rows[:30], 1):
                share = count / total_cands * 100 if total_cands > 0 else 0
                logger.info(f'  {i:<6}{name:<20}{count:<12}{share:>6.2f}%')
            
            if rows:
                top1 = rows[0][1] / total_cands * 100
                logger.info(f'')
                logger.info(f'  Top 1 Share: {top1:.2f}%')
                if top1 > ANTI_COLLAPSE_THRESHOLD * 100:
                    logger.error(f'  ANTI-COLLAPSE GATE FAILED! {top1:.1f}% > 50%')
                    return False
            
            logger.info('')
            logger.info('  Table Stats:')
            r3 = await session.execute(text('SELECT COUNT(*) FROM reconstructions'))
            logger.info(f'    Reconstructions: {r3.scalar()}')
            r4 = await session.execute(text('SELECT COUNT(*) FROM topic_links'))
            logger.info(f'    Topic Links: {r4.scalar()}')
            r5 = await session.execute(text('SELECT COUNT(*) FROM proposals'))
            logger.info(f'    Proposals: {r5.scalar()}')
        
        logger.info('')
        logger.info('='*80)
        logger.info('Clean Rebuild Complete!')
        logger.info(f'Finished: {datetime.now().isoformat()}')
        logger.info('='*80)
        return True
        
    except Exception as e:
        logger.error(f'Failed: {e}', exc_info=True)
        return False
    finally:
        await engine.dispose()

if __name__ == '__main__':
    success = asyncio.run(clean_rebuild())
    sys.exit(0 if success else 1)
