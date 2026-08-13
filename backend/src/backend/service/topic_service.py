"""TopicService — Topic extraction and resolution service.

This service implements Phase 21.6 Topic functionality:
- Topic creation with hierarchy support
- Topic resolution (avoid duplicates)
- Topic extraction from Reconstruction semantic_summary
- Workspace isolation

Transaction: Uses the session provided by the caller.
Does NOT commit or rollback — that is the caller's responsibility.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repository.topic_repository import TopicRepository
from backend.service.base import BaseService
from backend.shared.domain.memory_models import Topic

logger = logging.getLogger(__name__)


class TopicService(BaseService):
    """Service for Topic operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__("TopicService")
        self.session = session
        self.repo = TopicRepository(session)
    
    async def create_topic(
        self,
        *,
        workspace_id: UUID,
        name: str,
        description: str | None = None,
        parent_topic_id: UUID | None = None,
        status: str = "initial",
    ) -> UUID:
        """Create a new topic with validation.
        
        Args:
            workspace_id: Workspace scope.
            name: Topic name.
            description: Optional description.
            parent_topic_id: Optional parent for hierarchy.
            status: Topic status (default: 'initial').
            
        Returns:
            UUID of created topic.
            
        Note: Does NOT commit — caller manages transaction.
        """
        topic = Topic(
            id=uuid4(),
            workspace_id=workspace_id,
            name=name,
            description=description,
            parent_topic_id=parent_topic_id,
            status=status,
        )
        
        topic_id = await self.repo.create(topic)
        logger.info("Created topic: %s, name=%s, workspace=%s", topic_id, name, workspace_id)
        return topic_id
    
    async def resolve_topic(
        self,
        *,
        workspace_id: UUID,
        name: str,
    ) -> UUID | None:
        """Resolve topic name to existing topic or create new.
        
        Implements Topic resolution strategy:
        1. Exact match
        2. Return existing or create new
        
        Args:
            workspace_id: Workspace scope.
            name: Topic name.
            
        Returns:
            UUID of resolved topic, or None if failed.
        """
        existing = await self.repo.find_by_name(
            workspace_id=workspace_id,
            name=name,
        )
        
        if existing is not None:
            logger.debug("Found existing topic: %s = %s", name, existing.id)
            return existing.id
        
        new_topic = await self.create_topic(
            workspace_id=workspace_id,
            name=name,
        )
        logger.info("Created new topic: %s = %s", name, new_topic)
        return new_topic
    
    async def extract_topics_from_summary(
        self,
        *,
        workspace_id: UUID,
        semantic_summary: str,
    ) -> list[UUID]:
        """Extract topic candidates from semantic summary.
        
        This is a simplified extraction using keyword matching.
        Complex semantic clustering is deferred.
        
        Args:
            workspace_id: Workspace scope.
            semantic_summary: Reconstruction semantic content.
            
        Returns:
            List of resolved topic UUIDs.
        """
        topics = self._extract_keywords(semantic_summary)
        
        resolved_ids = []
        for topic_name in topics:
            topic_id = await self.resolve_topic(
                workspace_id=workspace_id,
                name=topic_name,
            )
            if topic_id:
                resolved_ids.append(topic_id)
        
        return resolved_ids
    
    def _extract_keywords(self, text: str, max_keywords: int = 3) -> list[str]:
        """Extract keyword candidates from text."""
        keywords = []
        
        chinese_pattern = r'[\u4e00-\u9fff]{2,4}'
        chinese_matches = re.findall(chinese_pattern, text)
        keywords.extend(chinese_matches)
        
        english_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        english_matches = re.findall(english_pattern, text)
        keywords.extend(english_matches)
        
        tech_terms = [
            "PostgreSQL", "MySQL", "MongoDB", "Docker", "Kubernetes",
            "Python", "JavaScript", "TypeScript", "React", "Vue",
            "API", "REST", "GraphQL", "SQL", "NoSQL",
            "Memory", "Hub", "LLM", "AI", "RAG",
        ]
        for term in tech_terms:
            if term.lower() in text.lower():
                keywords.append(term)
        
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:max_keywords]
    
    async def link_reconstruction_to_topics(
        self,
        *,
        reconstruction_id: UUID,
        topic_ids: list[UUID],
        workspace_id: UUID,
    ) -> None:
        """Link a Reconstruction to multiple Topics."""
        for topic_id in topic_ids:
            await self.repo.create_link(
                topic_id=topic_id,
                source_type="reconstruction",
                source_id=reconstruction_id,
                workspace_id=workspace_id,
            )
            
            await self._increment_reconstruction_count(topic_id)
    
    async def link_candidate_to_topics(
        self,
        *,
        candidate_id: UUID,
        topic_ids: list[UUID],
        workspace_id: UUID,
    ) -> None:
        """Link a Candidate to multiple Topics."""
        for topic_id in topic_ids:
            await self.repo.create_link(
                topic_id=topic_id,
                source_type="candidate",
                source_id=candidate_id,
                workspace_id=workspace_id,
            )
            
            await self._increment_candidate_count(topic_id)
    
    async def link_entity_to_topics(
        self,
        *,
        entity_id: UUID,
        topic_ids: list[UUID],
        workspace_id: UUID,
    ) -> None:
        """Link an Entity to multiple Topics."""
        for topic_id in topic_ids:
            await self.repo.create_link(
                topic_id=topic_id,
                source_type="entity",
                source_id=entity_id,
                workspace_id=workspace_id,
            )
            
            await self._increment_entity_count(topic_id)
    
    async def _increment_reconstruction_count(self, topic_id: UUID) -> None:
        """Increment reconstruction_count on topic."""
        await self.repo.increment_count(topic_id, count_field="reconstruction_count")
    
    async def _increment_candidate_count(self, topic_id: UUID) -> None:
        """Increment candidate_count on topic."""
        await self.repo.increment_count(topic_id, count_field="candidate_count")
    
    async def _increment_entity_count(self, topic_id: UUID) -> None:
        """Increment entity_count on topic."""
        await self.repo.increment_count(topic_id, count_field="entity_count")
