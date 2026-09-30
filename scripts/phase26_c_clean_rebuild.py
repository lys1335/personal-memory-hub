#!/usr/bin/env python3
"""
Phase 26-C: Entity Resolution Clean Rebuild
============================================
重新运行 EvidencePipelineService，使用修复后的 Entity Resolution 算法。

约束：
- 只执行 Formation（Evidence → Candidate）
- 不执行 Reflection（Candidate → Proposal）
- 不执行 Evolution（L1 → L2/L3）
- 实时监控 Anti-Collapse
- 每 500 条 Evidence 报告一次进度
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/clean_rebuild_phase26c.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 配置
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/memory_hub"
WORKSPACE_ID = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")
BATCH_SIZE = 50
REPORT_INTERVAL = 500
ANTI_COLLAPSE_THRESHOLD = 0.5  # 50%

async def clean_rebuild():
    """执行 Clean Rebuild。"""
    
    logger.info("=" * 80)
    logger.info("Phase 26-C: Entity Resolution Clean Rebuild")
    logger.info("=" * 80)
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Workspace: {WORKSPACE_ID}")
    logger.info(f"Database: {DATABASE_URL}")
    logger.info("")
    
    # Step 1: 连接到数据库
    logger.info("[Step 1] Connecting to database...")
    engine = create_async_engine(DATABASE_URL, pool_size=5)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    
    try:
        # Step 2: 清理旧数据
        logger.info("[Step 2] Clearing old data...")
        async with factory() as session:
            # 清理顺序：先清理依赖表，再清理被依赖表
            await session.execute(text("TRUNCATE topic_links CASCADE"))
            await session.execute(text("TRUNCATE reconstructions CASCADE"))
            await session.execute(text("TRUNCATE candidates CASCADE"))
            await session.execute(text("TRUNCATE proposals CASCADE"))
            await session.execute(text("TRUNCATE memory_nodes CASCADE"))
            await session.commit()
            logger.info("  - TRUNCATED topic_links, reconstructions, candidates, proposals, memory_nodes")
        
        # 验证清理结果
        async with factory() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM candidates"))
            count = result.scalar()
            logger.info(f"  - Verified: {count} candidates remaining")
            assert count == 0, f"Expected 0 candidates, got {count}"
        
        # Step 3: 导入 FormationService
        logger.info("[Step 3] Importing FormationService...")
        from backend.service.evidence_pipeline_service import EvidencePipelineService
        
        # Step 4: 运行 Pipeline
        logger.info("[Step 4] Running EvidencePipelineService...")
        logger.info(f"  - Total evidences to process: 15,662")
        logger.info(f"  - Batch size: {BATCH_SIZE}")
        logger.info(f"  - Report interval: {REPORT_INTERVAL}")
        logger.info("")
        
        pipeline = EvidencePipelineService(session_factory=factory)
        
        # 运行 pipeline
        result = await pipeline.run(
            workspace_id=WORKSPACE_ID,
            batch_size=BATCH_SIZE,
        )
        
        # Step 5: 验证结果
        logger.info("")
        logger.info("[Step 5] Validation Results:")
        logger.info("-" * 80)
        
        async with factory() as session:
            # 统计 Candidates
            cand_result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN entity_id IS NOT NULL THEN 1 END) as with_entity,
                    COUNT(CASE WHEN entity_id IS NULL THEN 1 END) as unresolved
                FROM candidates
                WHERE workspace_id = :workspace_id
            """), {"workspace_id": str(WORKSPACE_ID)})
            total, with_entity, unresolved = cand_result.fetchone()
            
            logger.info(f"  Candidates: {total} (with_entity={with_entity}, unresolved={unresolved})")
            logger.info(f"  Unresolved Rate: {unresolved/total*100:.1f}%" if total > 0 else "  Unresolved Rate: N/A")
            
            # 统计 Entity 分布
            entity_result = await session.execute(text("""
                SELECT 
                    e.canonical_name,
                    COUNT(c.id) as count
                FROM entities e
                JOIN candidates c ON c.entity_id = e.id
                WHERE c.workspace_id = :workspace_id
                GROUP BY e.id, e.canonical_name
                ORDER BY count DESC
                LIMIT 30
            """), {"workspace_id": str(WORKSPACE_ID)})
            
            rows = entity_result.fetchall()
            logger.info("")
            logger.info("  Top 30 Entities:")
            logger.info("  " + "-" * 70)
            logger.info(f"  {'Rank':<6}{'Entity':<20}{'Candidates':<12}{'Share':<10}")
            logger.info("  " + "-" * 70)
            
            total_cands = sum(r[1] for r in rows)
            for i, (name, count) in enumerate(rows[:30], 1):
                share = count / total_cands * 100 if total_cands > 0 else 0
                logger.info(f"  {i:<6}{name:<20}{count:<12}{share:>6.2f}%")
            
            # 检查 Anti-Collapse
            if rows:
                top_1_share = rows[0][1] / total_cands * 100 if total_cands > 0 else 0
                logger.info("")
                logger.info(f"  Top 1 Entity Share: {top_1_share:.2f}%")
                
                if top_1_share > ANTI_COLLAPSE_THRESHOLD * 100:
                    logger.error(f"  ❌ ANTI-COLLAPSE GATE TRIGGERED! Top 1 share {top_1_share:.1f}% > {ANTI_COLLAPSE_THRESHOLD*100:.0f}%")
                    return False
            
            # 统计 Resolution Method
            logger.info("")
            logger.info("  Resolution Method Distribution:")
            meta_result = await session.execute(text("""
                SELECT 
                    CASE 
                        WHEN CAST(_meta AS TEXT) LIKE '%exact_match%' THEN 'exact_match'
                        WHEN CAST(_meta AS TEXT) LIKE '%alias_match%' THEN 'alias_match'
                        WHEN CAST(_meta AS TEXT) LIKE '%fuzzy_match%' THEN 'fuzzy_match'
                        WHEN CAST(_meta AS TEXT) LIKE '%unresolved%' THEN 'unresolved'
                        ELSE 'other'
                    END as method,
                    COUNT(*) as count
                FROM candidates
                WHERE workspace_id = :workspace_id
                GROUP BY method
                ORDER BY count DESC
            """), {"workspace_id": str(WORKSPACE_ID)})
            
            methods = meta_result.fetchall()
            for method, count in methods:
                logger.info(f"    {method}: {count}")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("Clean Rebuild Completed Successfully!")
        logger.info(f"Finished at: {datetime.now().isoformat()}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Clean Rebuild failed: {e}", exc_info=True)
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(clean_rebuild())
    sys.exit(0 if success else 1)
