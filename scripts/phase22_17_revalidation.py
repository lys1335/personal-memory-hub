"""
Phase 22.17: 100-Evidence Entity Resolution Re-Validation
Tests the FIXED ContextWindow-based entity resolution.

Usage:
    cd /app && python scripts/phase22_17_revalidation.py
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.context.context_window import ContextWindow, EvidenceContext, EvidenceRole
from backend.service.formation_service import FormationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/memory_hub"
WORKSPACE_ID = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")


def convert_uuid(obj):
    """Convert asyncpg UUID to Python UUID."""
    if isinstance(obj, UUID):
        return obj
    if hasattr(obj, 'hex'):
        return UUID(bytes=obj.bytes)
    return str(obj)


async def fetch_sample_evidences(session, limit: int = 100) -> list[dict]:
    """Fetch 100 evidences without entity_id."""
    stmt = text("""
        SELECT id, content, evidence_type, source, workspace_id, created_at
        FROM evidences
        WHERE workspace_id = :workspace_id
          AND entity_id IS NULL
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    result = await session.execute(stmt, {
        'workspace_id': str(WORKSPACE_ID),
        'limit': limit
    })
    
    evidences = []
    for row in result.fetchall():
        evidences.append({
            'id': convert_uuid(row[0]),
            'content': row[1],
            'type': row[2],
            'source': row[3],
            'workspace_id': convert_uuid(row[4]),
            'created_at': row[5],
        })
    
    return evidences


async def build_context_window(
    session, 
    trigger_evidence: dict,
    related_evidence_ids: list
) -> ContextWindow:
    """Build ContextWindow with trigger + related evidences."""
    trigger = EvidenceContext(
        evidence_id=trigger_evidence['id'],
        content=trigger_evidence['content'],
        role=EvidenceRole.USER,
        created_at=trigger_evidence['created_at'],
        entity_id=None,
        workspace_id=trigger_evidence['workspace_id'],
        importance=1.0,
    )
    
    evidence_list = [trigger]
    
    # Fetch related evidences
    if related_evidence_ids:
        ids_str = ','.join(f"'{i}'" for i in related_evidence_ids)
        stmt = text(f"SELECT id, content, role, created_at FROM evidences WHERE id IN ({ids_str})")
        related = await session.execute(stmt)
        for row in related.fetchall():
            role = EvidenceRole.ASSISTANT if row[2] == 'assistant' else EvidenceRole.USER
            evidence_list.append(EvidenceContext(
                evidence_id=convert_uuid(row[0]),
                content=row[1],
                role=role,
                created_at=row[3],
                entity_id=None,
                workspace_id=trigger_evidence['workspace_id'],
                importance=0.8,
            ))
    
    return ContextWindow(
        trigger_evidence_id=trigger.evidence_id,
        workspace_id=trigger.workspace_id,
        evidence_list=evidence_list,
        token_count=sum(len(e.content) for e in evidence_list),
    )


def classify_evidence(evidence: dict) -> str:
    """Classify evidence into categories for analysis."""
    content = evidence['content'].lower()
    length = len(evidence['content'])
    
    # Short query: < 20 chars
    if length < 20:
        return 'short_query'
    
    # Check for question patterns
    if any(q in content for q in ['什么', '怎么', '为什么', '吗？', '?']):
        if length < 30:
            return 'short_query'
    
    # Technical terms
    tech_keywords = ['jquery', 'javascript', 'sql', 'html', 'css', 'python', 'django', 'flask', 'vue', 'react']
    if any(kw in content for kw in tech_keywords):
        return 'technical_term'
    
    # Abstract concepts (new concepts not in entity database)
    abstract_keywords = ['无货源', '惠方卷', '特朗普', '中国行', '第一梯队']
    if any(kw in content for kw in abstract_keywords):
        return 'abstract_concept'
    
    # Context-dependent (references to previous discussion)
    context_patterns = ['就是这样', '找不到它', '这个', '那个', '它', '这个方案']
    if any(p in content for p in context_patterns):
        return 'context_dependent'
    
    return 'other'


async def run_validation():
    """Run full validation on 100 evidences."""
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    all_results = []
    category_stats = {
        'short_query': {'total': 0, 'resolved': 0, 'unresolved': 0, 'methods': {}},
        'context_dependent': {'total': 0, 'resolved': 0, 'unresolved': 0, 'methods': {}},
        'abstract_concept': {'total': 0, 'resolved': 0, 'unresolved': 0, 'methods': {}},
        'technical_term': {'total': 0, 'resolved': 0, 'unresolved': 0, 'methods': {}},
        'other': {'total': 0, 'resolved': 0, 'unresolved': 0, 'methods': {}},
    }
    
    try:
        async with SessionLocal() as session:
            logger.info("Fetching 100 sample evidences...")
            evidences = await fetch_sample_evidences(session, limit=100)
            logger.info(f"Got {len(evidences)} evidences")
            
            formation_service = FormationService(session)
            
            for i, evidence in enumerate(evidences, 1):
                # Classify
                category = classify_evidence(evidence)
                category_stats[category]['total'] += 1
                
                # Build context window with related evidences
                # Use previous 3 evidences as context
                related_ids = [
                    str(evidences[j]['id']) 
                    for j in range(max(0, i-4), i-1)
                    if evidences[j]['id'] != evidence['id']
                ]
                
                context_window = await build_context_window(
                    session, evidence, related_ids
                )
                
                # Run entity resolution
                entity_id, method = await formation_service._resolve_entity_from_context(
                    evidence_id=evidence['id'],
                    workspace_id=WORKSPACE_ID,
                    context_window=context_window,
                )
                
                result = {
                    'index': i,
                    'evidence_id': str(evidence['id']),
                    'category': category,
                    'content_preview': evidence['content'][:100] + '...' if len(evidence['content']) > 100 else evidence['content'],
                    'predicted_entity_id': str(entity_id) if entity_id else None,
                    'method': method,
                    'context_size': len(context_window.evidence_list),
                    'has_assistant': any(
                        e.role == EvidenceRole.ASSISTANT 
                        for e in context_window.evidence_list
                    ),
                }
                
                all_results.append(result)
                
                # Update category stats
                if entity_id:
                    category_stats[category]['resolved'] += 1
                    category_stats[category]['methods'][method] = \
                        category_stats[category]['methods'].get(method, 0) + 1
                else:
                    category_stats[category]['unresolved'] += 1
                    category_stats[category]['methods']['unresolved'] = \
                        category_stats[category]['methods'].get('unresolved', 0) + 1
                
                if i % 10 == 0:
                    logger.info(f"Processed {i}/100 evidences...")
            
            logger.info("Validation complete!")
            
    finally:
        await engine.dispose()
    
    # Calculate overall stats
    total = len(all_results)
    resolved = sum(1 for r in all_results if r['predicted_entity_id'])
    unresolved = total - resolved
    
    # Method distribution
    method_dist = {}
    for r in all_results:
        m = r['method']
        method_dist[m] = method_dist.get(m, 0) + 1
    
    stats = {
        'timestamp': datetime.now().isoformat(),
        'total': total,
        'resolved': resolved,
        'unresolved': unresolved,
        'resolution_rate': round(resolved / total * 100, 2) if total > 0 else 0,
        'by_method': method_dist,
        'by_category': category_stats,
        'results': all_results,
    }
    
    # Save results
    output_path = '/app/phase22_17_validation.json'
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    # Print summary
    print("=" * 70)
    print("PHASE 22.17: 100-EVIDENCE ENTITY RESOLUTION RE-VALIDATION")
    print("=" * 70)
    print(f"Total tested: {stats['total']}")
    print(f"Resolved: {stats['resolved']} ({stats['resolution_rate']}%)")
    print(f"Unresolved: {stats['unresolved']}")
    print()
    print("By resolution method:")
    for method, count in sorted(method_dist.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {method}: {count} ({pct:.1f}%)")
    print()
    print("By category:")
    for cat, cat_stats in category_stats.items():
        if cat_stats['total'] > 0:
            rate = cat_stats['resolved'] / cat_stats['total'] * 100
            print(f"  {cat}: {cat_stats['resolved']}/{cat_stats['total']} ({rate:.1f}%)")
    print()
    print("ER-1 Target: >= 90%")
    print(f"Result: {stats['resolution_rate']}%")
    print(f"Status: {'PASS' if stats['resolution_rate'] >= 90 else 'FAIL'}")
    print("=" * 70)
    
    return stats


if __name__ == "__main__":
    result = asyncio.run(run_validation())
