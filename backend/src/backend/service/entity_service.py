"""EntityService — Identity Management Application Service.

Implements entity lifecycle and relationship management:
- Identity Management: create, resolve, get profile
- Merge: merge duplicate entities (MVP: basic create/resolve only)
- Alias: add/remove/get aliases (MVP: basic operations)
- Relationship: add/remove/get relationships
- Profile Update: update canonical name, metadata

Per D3.5 and 10_5 Implementation Design:
- MVP scope: create_entity(), resolve_entity() only
- Advanced capabilities (merge, alias, relationships) are V2+
- Entity identity is stable (EntityID never changes)
- Entity is never soft-deleted
- No Memory management (belongs to MemoryService)
- No Reflection generation (belongs to ReflectionService)
- No Query Projection (belongs to QueryService)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from backend.repository.exceptions import RepositoryError
from backend.service.base import BaseService
from backend.service.dto import EntityProfile, MergeResult
from backend.service.exceptions import (
    NotFoundError,
    ValidationError,
)

if TYPE_CHECKING:
    from backend.repository.entity_repository import EntityRepository
    from backend.repository.relationship_repository import RelationshipRepository

logger = logging.getLogger(__name__)


class EntityService(BaseService):
    """Application service for Entity domain operations.

    Coordinates Repository operations for entity identity management.

    Stateless singleton managed by DI container.
    """

    def __init__(
        self,
        entity_repo: EntityRepository,
        relationship_repo: RelationshipRepository,
    ) -> None:
        """Initialize EntityService with required repositories.

        Args:
            entity_repo: Repository for Entity CRUD.
            relationship_repo: Repository for Relationship management.
        """
        super().__init__("EntityService")
        self._entity_repo = entity_repo
        self._relationship_repo = relationship_repo

    # ------------------------------------------------------------------
    # Identity Management Capability (MVP)
    # ------------------------------------------------------------------

    async def create_entity(
        self,
        *,
        workspace_id: UUID,
        entity_type: str,
        canonical_name: str,
        area_id: UUID | None = None,
        parent_entity_id: UUID | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        aliases: list[str] | None = None,
    ) -> UUID:
        """Create a new entity.

        Returns the entity ID (Identity), not the full entity.

        Args:
            workspace_id: Workspace scope.
            entity_type: Entity type (Project, Person, etc.).
            canonical_name: Canonical (primary) name.
            area_id: Optional area ID.
            parent_entity_id: Optional parent entity.
            description: Optional description.
            metadata: Optional metadata dict.
            aliases: Optional list of alias names.

        Returns:
            The entity UUID.

        Raises:
            ValidationError: If required fields are missing or invalid.
            DuplicateError: If entity with same type+name exists.
        """
        self._validate_workspace_id(workspace_id)

        if not entity_type or not entity_type.strip():
            raise ValidationError(
                "entity_type is required",
                field="entity_type",
            )
        if not canonical_name or not canonical_name.strip():
            raise ValidationError(
                "canonical_name is required",
                field="canonical_name",
            )

        # Import model here to avoid circular imports
        from backend.shared.domain.memory_models import Entity

        entity = Entity(
            id=self._generate_id(),
            workspace_id=workspace_id,
            area_id=area_id,
            parent_entity_id=parent_entity_id,
            entity_type=entity_type.strip(),
            canonical_name=canonical_name.strip(),
            aliases=aliases or [],
            description=description,
            metadata=metadata or {},
        )

        try:
            entity_id = await self._entity_repo.create(entity)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        self._log_operation(
            "create_entity",
            workspace_id=workspace_id,
            entity_id=entity_id,
        )

        return entity_id

    async def resolve_entity(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        canonical_name: str | None = None,
        entity_type: str | None = None,
    ) -> EntityProfile | None:
        """Resolve an entity by ID or name.

        Returns an EntityProfile (read-only view), not the ORM model.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity UUID.
            canonical_name: Optional canonical name lookup.
            entity_type: Optional entity type filter.

        Returns:
            EntityProfile if found, None otherwise.

        Raises:
            ValidationError: If neither entity_id nor canonical_name provided.
        """
        self._validate_workspace_id(workspace_id)

        if entity_id is None and not canonical_name:
            raise ValidationError(
                "Either entity_id or canonical_name must be provided",
                field="entity_id",
            )

        # Import model here

        entity = None

        if entity_id:
            entity = await self._entity_repo.find_by_id(entity_id)
        elif canonical_name:
            entity = await self._entity_repo.find_by_name(
                canonical_name=canonical_name,
                workspace_id=workspace_id,
                entity_type=entity_type,
            )

        if entity is None:
            return None

        # Build EntityProfile from ORM model
        return EntityProfile(
            entity_id=entity.id,
            workspace_id=entity.workspace_id,
            entity_type=entity.entity_type,
            canonical_name=entity.canonical_name,
            aliases=list(entity.aliases) if hasattr(entity, "aliases") else [],
            description=getattr(entity, "description", None),
            metadata=getattr(entity, "metadata", {}) or {},
            observation_count=getattr(entity, "observation_count", 0),
            pattern_count=getattr(entity, "pattern_count", 0),
            belief_count=getattr(entity, "belief_count", 0),
            relationship_count=getattr(entity, "relationship_count", 0),
            created_at=str(getattr(entity, "created_at", "")),
            updated_at=str(getattr(entity, "updated_at", "")),
        )

    async def get_entity_profile(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
    ) -> EntityProfile:
        """Get a detailed entity profile.

        Convenience wrapper around resolve_entity() that raises NotFoundError.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.

        Returns:
            EntityProfile.

        Raises:
            NotFoundError: If entity not found.
        """
        self._validate_workspace_id(workspace_id)

        profile = await self.resolve_entity(
            workspace_id=workspace_id,
            entity_id=entity_id,
        )

        if profile is None:
            raise NotFoundError(
                f"Entity {entity_id} not found",
                resource_type="entity",
                resource_id=str(entity_id),
            )

        return profile

    # ------------------------------------------------------------------
    # Merge Capability (MVP: stub, full implementation V2+)
    # ------------------------------------------------------------------

    async def merge_entities(
        self,
        *,
        workspace_id: UUID,
        source_entity_ids: list[UUID],
        target_entity_id: UUID,
    ) -> MergeResult:
        """Merge multiple entities into one.

        MVP STUB: Returns a basic MergeResult without actual merge logic.
        Full implementation is V2+ (requires relationship migration,
        alias consolidation, memory reference updates).

        Args:
            workspace_id: Workspace scope.
            source_entity_ids: Entities to merge away.
            target_entity_id: Surviving entity.

        Returns:
            MergeResult with merge statistics.
        """
        self._validate_workspace_id(workspace_id)

        # Verify target exists
        target = await self._entity_repo.find_by_id(target_entity_id)
        if target is None:
            raise NotFoundError(
                f"Entity {target_entity_id} not found",
                resource_type="entity",
                resource_id=str(target_entity_id),
            )

        return MergeResult(
            target_entity_id=target_entity_id,
            source_entity_ids=source_entity_ids,
            relationships_migrated=0,
            aliases_consolidated=0,
            memories_referenced=0,
        )

    async def get_merge_status(
        self,
        *,
        workspace_id: UUID,
        merge_id: UUID,
    ) -> str:
        """Get the status of a merge operation.

        MVP STUB: Always returns "completed".

        Args:
            workspace_id: Workspace scope.
            merge_id: Merge operation ID.

        Returns:
            Status string.
        """
        return "completed"

    # ------------------------------------------------------------------
    # Alias Capability (MVP: stub, full implementation V2+)
    # ------------------------------------------------------------------

    async def add_alias(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
        alias: str,
    ) -> bool:
        """Add an alias to an entity.

        MVP STUB: Returns True without actual modification.
        Full implementation updates entity.aliases array.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.
            alias: Alias name to add.

        Returns:
            True if alias was added.
        """
        self._validate_workspace_id(workspace_id)

        if not alias or not alias.strip():
            raise ValidationError(
                "Alias cannot be empty",
                field="alias",
            )

        return True

    async def remove_alias(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
        alias: str,
    ) -> bool:
        """Remove an alias from an entity.

        MVP STUB: Returns True without actual modification.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.
            alias: Alias name to remove.

        Returns:
            True if alias was removed.
        """
        self._validate_workspace_id(workspace_id)
        return True

    async def get_aliases(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
    ) -> list[str]:
        """Get all aliases for an entity.

        MVP STUB: Returns empty list.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.

        Returns:
            List of alias strings.
        """
        self._validate_workspace_id(workspace_id)
        return []

    # ------------------------------------------------------------------
    # Relationship Capability (MVP: stub, full implementation V2+)
    # ------------------------------------------------------------------

    async def add_relationship(
        self,
        *,
        workspace_id: UUID,
        source_id: UUID,
        target_id: UUID,
        relationship_type: str,
    ) -> UUID:
        """Add a relationship between two entities.

        MVP STUB: Returns a generated ID without persisting.
        Full implementation creates a Relationship record.

        Args:
            workspace_id: Workspace scope.
            source_id: Source entity UUID.
            target_id: Target entity UUID.
            relationship_type: Type of relationship.

        Returns:
            The relationship UUID.
        """
        self._validate_workspace_id(workspace_id)

        if not relationship_type or not relationship_type.strip():
            raise ValidationError(
                "relationship_type is required",
                field="relationship_type",
            )

        return self._generate_id()

    async def remove_relationship(
        self,
        *,
        workspace_id: UUID,
        relationship_id: UUID,
    ) -> bool:
        """Remove a relationship.

        MVP STUB: Returns True without actual removal.

        Args:
            workspace_id: Workspace scope.
            relationship_id: The relationship UUID.

        Returns:
            True if removed.
        """
        self._validate_workspace_id(workspace_id)
        return True

    async def get_relationships(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
        relationship_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get relationships for an entity.

        MVP STUB: Returns empty list.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.
            relationship_type: Optional type filter.

        Returns:
            List of relationship dicts.
        """
        self._validate_workspace_id(workspace_id)
        return []

    # ------------------------------------------------------------------
    # Profile Update Capability
    # ------------------------------------------------------------------

    async def update_canonical_name(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
        new_name: str,
    ) -> UUID:
        """Update an entity's canonical name.

        MVP STUB: Returns the entity ID without modification.
        Full implementation updates entity.canonical_name.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.
            new_name: New canonical name.

        Returns:
            The entity UUID.
        """
        self._validate_workspace_id(workspace_id)

        if not new_name or not new_name.strip():
            raise ValidationError(
                "New canonical name cannot be empty",
                field="canonical_name",
            )

        return entity_id

    async def update_metadata(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID,
        metadata: dict[str, Any],
    ) -> UUID:
        """Update an entity's metadata.

        MVP STUB: Returns the entity ID without modification.

        Args:
            workspace_id: Workspace scope.
            entity_id: The entity UUID.
            metadata: New metadata dict (merged with existing).

        Returns:
            The entity UUID.
        """
        self._validate_workspace_id(workspace_id)
        return entity_id

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _generate_id(self) -> UUID:
        """Generate a UUID for internal use."""
        try:
            from backend.shared.infrastructure.uuid import generate_uuid
            return generate_uuid()
        except ImportError:
            import uuid
            return generate_uuid()
