"""
Phase 24-E: Resume from checkpoint (evidence #217+)
Continues processing from where Phase 24-E was paused.
"""
import asyncio
import json
import logging
from datetime import datetime
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.service.evidence_pipeline_service import EvidencePipelineService
from backend.shared.domain.memory_models import Evidence

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/phase24_e_resume.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@db:5432/memory_hub'
WORKSPACE_ID = UUID('fd0223ed-7aa2-491e-8db5-b0de71b75219')
BATCH_SIZE = 50
REPORT_INTERVAL = 500


class StatsTracker:
    """Track pipeline statistics."""
    
    def __init__(self):
        self.processed = 0
        self.formation_success = 0
        self.ambiguous = 0
        self.no_user_fact = 0
        self.candidates = 0
        self.topic_links = 0
        self.transaction_failures = 0
        self.errors = []
        
    def update_from_result(self, result):
        """Update stats from PipelineResult."""
        self.processed += 1
        
        if not result.success:
            if result.skipped:
                if 'ambiguous' in result.skipped.lower():
                    self.ambiguous += 1
                elif 'no_user_fact' in result.skipped.lower():
                    self.no_user_fact += 1
            self.transaction_failures += 1
            if len(self.errors) < 50:
                self.errors.append({
                    'evidence_id': str(result.evidence_id),
                    'error': result.error or result.skipped
                })
            return
        
        if result.has_candidate:
            self.formation_success += 1
            self.candidates += 1
        
        if result.has_topics:
            self.topic_links += len(result.topic_ids)
    
    def get_summary(self):
        """Get summary dict."""
        return {
            'processed': self.processed,
            'formation_success': self.formation_success,
            'ambiguous': self.ambiguous,
            'no_user_fact': self.no_user_fact,
            'candidates': self.candidates,
            'topic_links': self.topic_links,
            'transaction_failures': self.transaction_failures,
            'candidate_rate': round(self.candidates / self.processed * 100, 2) if self.processed > 0 else 0,
        }


async def main():
    logger.info("=" * 80)
    logger.info("Phase 24-E Resume: Processing remaining evidences")
    logger.info("Workspace: %s", WORKSPACE_ID)
    logger.info("Batch size: %d", BATCH_SIZE)
    logger.info("=" * 80)
    
    engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    stats = StatsTracker()
    
    start_time = datetime.now()
    
    try:
        async with factory() as session:
            # Load all evidence IDs
            logger.info("Loading evidence IDs...")
            result = await session.execute(
                text('SELECT id FROM evidences WHERE workspace_id = :wid ORDER BY created_at ASC')
, {'wid': str(WORKSPACE_ID)})
            evidence_ids = [str(row[0]) for row in result.fetchall()]
            
            total = len(evidence_ids)
            logger.info("Total evidences: %d", total)
            
            # Skip already processed (first 216)
            checkpoint = 216
            remaining = evidence_ids[checkpoint:]
            logger.info("Checkpoint: %d, Remaining: %d", checkpoint, len(remaining))
            
            pipeline = EvidencePipelineService(session)
            
            # Process remaining in batches
            for i in range(0, len(remaining), BATCH_SIZE):
                batch = remaining[i:i+BATCH_SIZE]
                global_idx = checkpoint + i
                
                for j, ev_id in enumerate(batch):
                    try:
                        outcome = await pipeline.process_evidence(
                            evidence_id=UUID(ev_id),
                            workspace_id=WORKSPACE_ID,
                        )
                        stats.update_from_result(outcome)
                        
                    except Exception as e:
                        logger.error(f"Error processing {ev_id}: {e}")
                        stats.processed += 1
                        stats.transaction_failures += 1
                        if len(stats.errors) < 50:
                            stats.errors.append({
                                'evidence_id': ev_id,
                                'error': str(e)
                            })
                
                # Report progress
                processed = global_idx + len(batch)
                if processed % REPORT_INTERVAL == 0 or processed == total:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = processed / elapsed if elapsed > 0 else 0
                    eta = (total - processed) / rate if rate > 0 else 0
                    
                    logger.info(
                        "[%d/%d (%.1f%%)] "
                        "processed=%d success=%d amb=%d no_fact=%d "
                        "cands=%d topics=%d failures=%d eta=%ds",
                        processed, total, processed*100/total,
                        stats.processed, stats.formation_success,
                        stats.ambiguous, stats.no_user_fact,
                        stats.candidates, stats.topic_links,
                        stats.transaction_failures, int(eta)
                    )
                
                # Periodic commit
                if processed % 500 == 0:
                    try:
                        await session.commit()
                        logger.info("Checkpoint commit at %d/%d", processed, total)
                    except Exception as e:
                        logger.error(f"Checkpoint commit failed: {e}")
                        await session.rollback()
            
            # Final commit
            await session.commit()
            logger.info("Final commit completed")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        try:
            await session.rollback()
            logger.info("Rollback completed")
        except:
            pass
    finally:
        await engine.dispose()
    
    # Save stats
    elapsed = (datetime.now() - start_time).total_seconds()
    stats.summary = stats.get_summary()
    stats.summary['elapsed_seconds'] = elapsed
    stats.summary['start_time'] = start_time.isoformat()
    stats.summary['end_time'] = datetime.now().isoformat()
    
    with open('/tmp/phase24_e_resume_stats.json', 'w') as f:
        json.dump(stats.summary, f, indent=2, default=str)
    
    logger.info("=" * 80)
    logger.info("Phase 24-E Resume Complete!")
    logger.info("Summary: %s", json.dumps(stats.summary, indent=2, default=str))
    logger.info("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())
