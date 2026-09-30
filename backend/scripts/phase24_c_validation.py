"""
Phase 24-C: Small-scale Pipeline Validation (100 evidences)
Tests role fix before full rebuild
"""
import asyncio
import json
import logging
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.service.evidence_pipeline_service import EvidencePipelineService
from backend.context.context_window import EvidenceRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')


def to_uuid(value):
    """Convert UUID value to Python UUID."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


async def main():
    logger.info("Starting Phase 24-C validation (100 evidences)...")
    
    engine = create_async_engine(DATABASE_URL)
    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'ambiguous': 0,
        'user_evidences': 0,
        'assistant_evidences': 0,
        'context_window_roles': {'user': 0, 'assistant': 0, 'unknown': 0},
    }
    
    async with engine.begin() as conn:
        # Get first 100 evidences
        result = await conn.execute(text('''
            SELECT id, evidence_type, content 
            FROM evidences
            WHERE workspace_id = :wid
            ORDER BY created_at DESC
            LIMIT 100
        '''), {'wid': str(WORKSPACE_ID)})
        
        evidences = []
        for row in result.fetchall():
            ev_id = to_uuid(row[0])
            ev_type = row[1]
            content = row[2]
            if ev_id:
                evidences.append({
                    'id': ev_id,
                    'type': ev_type,
                    'content': content[:50] if content else '',
                })
                if ev_type == 'user':
                    stats['user_evidences'] += 1
                elif ev_type == 'assistant':
                    stats['assistant_evidences'] += 1
        
        stats['total'] = len(evidences)
        logger.info(f"Loaded {stats['total']} evidences (user={stats['user_evidences']}, assistant={stats['assistant_evidences']})")
    
    # Test each evidence
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        for i, ev in enumerate(evidences[:100], 1):
            try:
                service = EvidencePipelineService(session)
                result = await service.process_evidence(
                    evidence_id=ev['id'],
                    workspace_id=WORKSPACE_ID,
                )
                
                stats['total'] += 1
                if result.success:
                    stats['success'] += 1
                    if result.has_candidate:
                        logger.info(f"[{i}] ✓ Candidate created for {str(ev['id'])[:36]}...")
                elif result.skipped:
                    stats['skipped'] += 1
                    if 'ambiguous' in result.skipped.lower():
                        stats['ambiguous'] += 1
                else:
                    stats['failed'] += 1
                    logger.warning(f"[{i}] ✗ Failed: {result.error}")
                    
            except Exception as e:
                stats['failed'] += 1
                logger.error(f"[{i}] Error: {e}")
    
    await engine.dispose()
    
    # Save stats
    with open('/tmp/pipeline_validation_stats.json', 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    logger.info("=" * 60)
    logger.info("VALIDATION RESULTS:")
    logger.info(f"  Total processed: {stats['total']}")
    logger.info(f"  Success: {stats['success']}")
    logger.info(f"  Skipped: {stats['skipped']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"  AMBIGUOUS: {stats['ambiguous']}")
    logger.info(f"  Evidence types: user={stats['user_evidences']}, assistant={stats['assistant_evidences']}")
    logger.info("=" * 60)
    
    print(json.dumps(stats, indent=2, default=str))


if __name__ == '__main__':
    asyncio.run(main())
