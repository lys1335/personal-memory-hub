import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.context.context_window import ContextWindow, EvidenceContext, EvidenceRole
from backend.service.formation_service import FormationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_uuid(obj):
    """Convert asyncpg UUID to Python UUID."""
    if isinstance(obj, UUID):
        return obj
    if hasattr(obj, 'hex'):
        return UUID(bytes=obj.bytes)
    return str(obj)


async def get_test_evidences(session, workspace_id: UUID, limit: int = 10):
    stmt = text("""
        SELECT id, content, evidence_type, source, workspace_id, created_at
        FROM evidences
        WHERE workspace_id = :workspace_id
          AND entity_id IS NULL
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    result = await session.execute(stmt, {
        'workspace_id': str(workspace_id),
        'limit': limit
    })
    rows = []
    for row in result.fetchall():
        rows.append({
            'id': convert_uuid(row[0]),
            'content': row[1],
            'evidence_type': row[2],
            'source': row[3],
            'workspace_id': convert_uuid(row[4]),
            'created_at': row[5],
        })
    return rows


async def build_context_window(session, evidence, related_evidence_ids: list):
    trigger = EvidenceContext(
        evidence_id=evidence['id'],
        content=evidence['content'],
        role=EvidenceRole.USER,
        created_at=evidence.get('created_at'),
        entity_id=None,
        workspace_id=evidence['workspace_id'],
        importance=1.0,
    )

    evidence_list = [trigger]

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
                workspace_id=evidence['workspace_id'],
                importance=0.8,
            ))

    return ContextWindow(
        trigger_evidence_id=trigger.evidence_id,
        workspace_id=trigger.workspace_id,
        evidence_list=evidence_list,
        token_count=sum(len(e.content) for e in evidence_list),
    )


async def test_context_resolution():
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/memory_hub"
    WORKSPACE_ID = UUID("fd0223ed-7aa2-491e-8db5-b0de71b75219")

    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    results = []

    try:
        async with SessionLocal() as session:
            evidences = await get_test_evidences(session, WORKSPACE_ID, limit=20)
            logger.info(f"Testing {len(evidences)} evidences with ContextWindow")

            formation_service = FormationService(session)

            for i, evidence in enumerate(evidences, 1):
                # Build context with this evidence + previous 2
                related_ids = [e['id'] for e in evidences[:3] if e['id'] != evidence['id']]
                context_window = await build_context_window(session, evidence, related_ids)

                entity_id, method = await formation_service._resolve_entity_from_context(
                    evidence_id=evidence['id'],
                    workspace_id=WORKSPACE_ID,
                    context_window=context_window,
                )

                results.append({
                    'index': i,
                    'evidence_id': str(evidence['id']),
                    'content_preview': evidence['content'][:80] + '...' if len(evidence['content']) > 80 else evidence['content'],
                    'predicted_entity_id': str(entity_id) if entity_id else None,
                    'method': method,
                    'context_size': len(context_window.evidence_list),
                })

                if entity_id:
                    logger.info(f"[{i}] RESOLVED: {method}")
                else:
                    logger.info(f"[{i}] UNRESOLVED: {method}")

    finally:
        await engine.dispose()

    resolved = [r for r in results if r['predicted_entity_id']]
    unresolved = [r for r in results if not r['predicted_entity_id']]

    stats = {
        'total': len(results),
        'resolved': len(resolved),
        'unresolved': len(unresolved),
        'resolution_rate': len(resolved) / len(results) * 100 if results else 0,
        'by_method': {},
        'results': results,
    }

    for r in results:
        method = r['method']
        stats['by_method'][method] = stats['by_method'].get(method, 0) + 1

    output_path = '/app/context_resolution_results.json'
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2, default=str)

    print("=" * 70)
    print("CONTEXT WINDOW ENTITY RESOLUTION TEST")
    print("=" * 70)
    print(f"Total tested: {stats['total']}")
    print(f"Resolved: {stats['resolved']} ({stats['resolution_rate']:.1f}%)")
    print(f"Unresolved: {stats['unresolved']}")
    print()
    print("By method:")
    for method, count in stats['by_method'].items():
        pct = count / stats['total'] * 100
        print(f"  {method}: {count} ({pct:.1f}%)")
    print()
    print(f"ER-1 Target: >= 90%")
    print(f"Result: {stats['resolution_rate']:.1f}%")
    print(f"Status: {'PASS' if stats['resolution_rate'] >= 90 else 'FAIL'}")
    print("=" * 70)

    return stats


if __name__ == "__main__":
    result = asyncio.run(test_context_resolution())
