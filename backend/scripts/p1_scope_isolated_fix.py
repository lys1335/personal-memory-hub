#!/usr/bin/env python3
"""Phase 26-G-B P1 Scope Isolation Fix

This script provides a safe, scoped approval mechanism that:
1. Requires explicit proposal_id authorization
2. Validates all targets before any mutation
3. Uses single transaction for atomicity
4. Verifies exact scope after mutation
5. Rejects if ANY target is invalid

Usage:
    python scripts/p1_scope_isolated_fix.py --proposal-ids <id1,id2,...>
    
Safety guarantees:
    - 0 mutations if any validation fails
    - Exact count match required
    - Transaction rollback on any failure
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@memory-hub-db:5432/memory_hub"
WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"


class ScopeIsolationError(Exception):
    """Raised when scope isolation check fails."""
    pass


class P1ScopeIsolatedFix:
    """Safe P1 state synchronization with strict scope isolation."""
    
    def __init__(self, engine):
        self.engine = engine
        self.approved_ids = []
        
    async def preflight_check(self, authorized_ids: list[str]) -> dict:
        """Pre-flight validation before any mutation.
        
        Returns dict with:
            - requested_ids: list of authorized proposal IDs
            - existing_ids: list of IDs that exist in DB
            - eligible_ids: list of IDs that are pending and have valid evidence
            - invalid_ids: list of IDs that fail any validation
            - skip_count: number of already-processed proposals
        """
        result = {
            'requested_ids': authorized_ids,
            'existing_ids': [],
            'eligible_ids': [],
            'invalid_ids': [],
            'skip_count': 0,
        }
        
        async with self.engine.begin() as conn:
            # Check which proposals exist and their current status
            placeholders = ','.join(f':id{i}' for i in range(len(authorized_ids)))
            params = {f'id{i}': aid for i, aid in enumerate(authorized_ids)}
            
            query = f"""
                SELECT p.id, p.status, p.candidate_id, c.evidence_id
                FROM proposals p
                JOIN candidates c ON c.id = p.candidate_id AND c.workspace_id = p.workspace_id
                WHERE p.workspace_id = :workspace_id
                  AND p.id IN ({placeholders})
            """
            params['workspace_id'] = str(WORKSPACE_ID)
            
            rows = await conn.execute(text(query), params)
            proposals = rows.fetchall()
            
            for row in proposals:
                pid, status, candidate_id, evidence_id = row
            
            ...[truncated]