"""Personal Memory Hub - CLI Entry Point

This module provides the command-line interface for the Personal Memory Hub.
Per D5_Entry_Layer_Architecture, CLI is one of multiple Entry Adapters.
"""

import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.repository.archive_repository import ArchiveRepository
from backend.repository.evidence_repository import EvidenceRepository
from backend.repository.memory_node_repository import MemoryNodeRepository
from backend.repository.memory_query_repository import MemoryQueryRepository
from backend.repository.relationship_repository import RelationshipRepository
from backend.repository.tag_repository import TagRepository
from backend.repository.task_repository import TaskRepository
from backend.service.memory_service import MemoryService
from backend.shared.infrastructure.database.engine import get_session_factory

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the CLI."""
    logger.info("Starting Personal Memory Hub")
    
    # Create repository instances
    session_factory = get_session_factory()
    
    memory_node_repo = MemoryNodeRepository(session_factory)
    evidence_repo = EvidenceRepository(session_factory)
    relationship_repo = RelationshipRepository(session_factory)
    archive_repo = ArchiveRepository(session_factory)
    tag_repo = TagRepository(session_factory)
    task_repo = TaskRepository(session_factory)
    memory_query_repo = MemoryQueryRepository(session_factory)
    
    # Create memory service instance with all dependencies
    memory_service = MemoryService(
        memory_node_repo=memory_node_repo,
        evidence_repo=evidence_repo,
        relationship_repo=relationship_repo,
        archive_repo=archive_repo,
        tag_repo=tag_repo,
        task_repo=task_repo,
        memory_query_repo=memory_query_repo,
    )
    
    logger.info("MemoryService initialized successfully")
    print("Personal Memory Hub ready!")
    print("Use 'memory-hub --help' for available commands")


if __name__ == "__main__":
    main()
