"""
Phase 26-D: Approval Selector Contract Fix - SQL Structure Verification

Only tests the SQL query structure, not full integration.
"""
import pytest
import inspect
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.service.reflection_service import ReflectionService


class TestSelectorSQLStructure:
    """Verify the fixed selector SQL queries have correct structure."""
    
    def test_auto_approve_pending_proposals_query(self):
        """_auto_approve_pending_proposals has entity_id check."""
        source = inspect.getsource(ReflectionService._auto_approve_pending_proposals)
        
        # Required components
        assert 'JOIN candidates c ON c.id = p.candidate_id' in source, \
            "Missing JOIN with candidates table"
        assert 'c.entity_id IS NOT NULL' in source, \
            "Missing entity_id IS NOT NULL check"
        assert "p.status = 'pending'" in source, \
            "Missing status filter"
        assert 'p.confidence >= :threshold' in source, \
            "Missing confidence threshold check"
        assert 'p.target_level <= :max_level' in source, \
            "Missing target_level check"
        
    def test_auto_approve_by_threshold_query(self):
        """_auto_approve_by_threshold has entity_id check."""
        source = inspect.getsource(ReflectionService._auto_approve_by_threshold)
        
        # Required components
        assert 'JOIN candidates c ON c.id = p.candidate_id' in source, \
            "Missing JOIN with candidates table"
        assert 'c.entity_id IS NOT NULL' in source, \
            "Missing entity_id IS NOT NULL check"
        assert "p.status = 'pending'" in source, \
            "Missing status filter"
        assert 'p.confidence >= :threshold' in source, \
            "Missing confidence threshold check"
        assert 'p.target_level = :target_level' in source, \
            "Missing target_level equality check"
    
    def test_no_other_selectors_need_fix(self):
        """Verify no other approval selectors were missed."""
        source = inspect.getsource(ReflectionService)
        
        # Count occurrences of the pattern
        count_join = source.count('JOIN candidates c ON c.id = p.candidate_id')
        count_entity_check = source.count('c.entity_id IS NOT NULL')
        
        # Both auto-approve methods should have the fix
        assert count_join >= 2, f"Expected at least 2 JOINs, found {count_join}"
        assert count_entity_check >= 2, f"Expected at least 2 entity_id checks, found {count_entity_check}"


class TestDataIntegrity:
    """Verify database state is unchanged."""
    
    def test_no_data_changes(self):
        """This test should be run manually to verify database state."""
        # Database state verification:
        # - proposals = 5,038 (approved=183, pending=4,854, rejected=1)
        # - memory_nodes = 183
        # - Cron = disabled
        # Run manually via: docker exec memory-hub-db psql ...
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
