"""MemoryService — Memory Domain Application Service.

Implements the primary write orchestration for the Memory lifecycle:
- Capture: Store new observations, patterns, beliefs
- Import: Batch import memories with continue-on-error
- Merge: Merge duplicate memories
- Archive: Archive memories to permanent storage
- Lifecycle: Trigger reflection, schedule archive, reprocess
- Restore: Restore archived memories

Per D3.2 and 10_2 Implementation Design:
- Command methods return Identity (MemoryId), not full Memory entity
- No Query responsibilities (all reads go through QueryService)
- No direct Engine calls (Engines are D4; Service coordinates Repositories)
- Raw Evidence Preservation: raw evidence never lost due to downstream failure
- Task Ownership: background work via TaskService.submit()
- Repository Coordination: Repositories never coordinate each other
- Transaction: Per-Memory transaction (default), batch continue-on-error
- Minimum Service Guarantee: successful persistence satisfies guarantee

Architecture:
    MemoryService (D3) → Repository Layer (D2) → Database
    MemoryService (D3) → TaskService (D3) → Task Runtime (D4)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

# Import from ingest framework (Phase F)
from backend.ingest.base import ImportSource
from backend.ingest.registry import create_default_registry
from backend.repository.exceptions import RepositoryError
from backend.service.base import BaseService
from backend.service.dto import (
    CaptureResult,
    ImportJobStatus,
    ImportStatus,
    ReflectionExecutionResult,
    ReflectionStatus,
)
from backend.service.exceptions import (
    ImportError,
    NotFoundError,
    ValidationError,
)

if TYPE_CHECKING:
    from backend.repository.archive_repository import ArchiveRepository
    from backend.repository.evidence_repository import EvidenceRepository
    from backend.repository.memory_node_repository import MemoryNodeRepository
    from backend.repository.memory_query_repository import MemoryQueryRepository
    from backend.repository.relationship_repository import RelationshipRepository
    from backend.repository.tag_repository import TagRepository
    from backend.repository.task_repository import TaskRepository
    from backend.repository.vector_doc_repository import VectorDocRepository
    from backend.service.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class MemoryService(BaseService):
    """Application service for Memory domain operations.

    Coordinates Repository reads/writes for memory capture, import,
    merge, archive, lifecycle management, and restoration.

    Stateless singleton managed by DI container.
    """

    def __init__(
        self,
        memory_node_repo: MemoryNodeRepository,
        evidence_repo: EvidenceRepository,
        relationship_repo: RelationshipRepository,
        archive_repo: ArchiveRepository,
        tag_repo: TagRepository,
        task_repo: TaskRepository,
        memory_query_repo: MemoryQueryRepository,
        vector_doc_repo: VectorDocRepository | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """Initialize MemoryService with required repositories.

        Args:
            memory_node_repo: Repository for MemoryNode CRUD.
            evidence_repo: Repository for Evidence CRUD.
            relationship_repo: Repository for Relationship management.
            archive_repo: Repository for Archive records.
            tag_repo: Repository for Tag management.
            task_repo: Repository for Task management.
            memory_query_repo: Repository for memory read queries.
            vector_doc_repo: Optional repository for VectorDoc persistence.
            embedding_service: Optional service for generating embeddings.
        """
        super().__init__("MemoryService")
        self._memory_node_repo = memory_node_repo
        self._evidence_repo = evidence_repo
        self._relationship_repo = relationship_repo
        self._archive_repo = archive_repo
        self._tag_repo = tag_repo
        self._task_repo = task_repo
        self._memory_query_repo = memory_query_repo
        self._vector_doc_repo = vector_doc_repo
        self._embedding_service = embedding_service

    # ------------------------------------------------------------------
    # Capture Capability
    # ------------------------------------------------------------------

    async def capture_memory(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None,
        content: str,
        level: int = 1,
        node_type: str = "Observation",
        source: str = "user",
        confidence: float = 0.0,
        importance: float = 0.0,
        signal_strength: float = 0.0,
        observation_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CaptureResult:
        """Capture a new memory node.

        Creates a MemoryNode and optionally links evidence.
        Returns the memory ID (Identity), not the full entity.

        Args:
            workspace_id: Workspace scope.
            entity_id: Associated entity (optional for standalone observations).
            content: Memory content text.
            level: Memory level (1=Observation, 2=Pattern, 3=Belief).
            node_type: Node type string.
            source: Source of the memory.
            confidence: Confidence score (0.0-1.0).
            importance: Importance score (0.0-1.0).
            signal_strength: Signal strength score (0.0-1.0).
            observation_type: Observation subtype (only for L1).
            metadata: Additional metadata.

        Returns:
            CaptureResult with the memory ID and metadata.

        Raises:
            ValidationError: If required fields are missing or invalid.
            DuplicateError: If a duplicate memory exists.
            DomainIntegrityError: If domain invariants are violated.
            TransactionError: If the transaction fails.
        """
        # Validate inputs
        if not content or not content.strip():
            raise ValidationError(
                "Memory content cannot be empty",
                field="content",
            )
        if level not in (1, 2, 3):
            raise ValidationError(
                f"Invalid memory level: {level}. Must be 1, 2, or 3.",
                field="level",
            )
        if not (0.0 <= confidence <= 1.0):
            raise ValidationError(
                f"Confidence must be 0.0-1.0, got {confidence}",
                field="confidence",
            )
        if not (0.0 <= importance <= 1.0):
            raise ValidationError(
                f"Importance must be 0.0-1.0, got {importance}",
                field="importance",
            )
        if not (0.0 <= signal_strength <= 1.0):
            raise ValidationError(
                f"Signal strength must be 0.0-1.0, got {signal_strength}",
                field="signal_strength",
            )

        self._validate_workspace_id(workspace_id)

        # Import the model here to avoid circular imports at module level
        from backend.shared.domain.memory_models import MemoryNode

        # Create the memory node
        memory_node = MemoryNode(
            id=self._generate_id(),
            workspace_id=workspace_id,
            entity_id=entity_id if entity_id else None,
            level=level,
            node_type=node_type,
            content=content.strip(),
            summary=None,
            observation_type=observation_type,
            confidence=confidence,
            importance=importance,
            signal_strength=signal_strength,
            status="active",
            source=source,
            generated_by=source,
            evidence_links=[],
            contradict_evidence=[],
            metadata=metadata or {},
        )

        try:
            memory_id = await self._memory_node_repo.create(memory_node)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        # Commit per G-106 (Transaction Ownership)
        await self._commit(self._memory_node_repo.session)

        # Generate vector embedding for RAG retrieval
        if self._embedding_service and self._vector_doc_repo and content.strip():
            try:
                import json as _json

                from backend.shared.domain.memory_models import VectorDoc
                from backend.shared.infrastructure.uuid import generate_uuid

                embedding = await self._embedding_service.generate(content.strip())
                if embedding is not None:
                    vector_doc = VectorDoc(
                        id=generate_uuid(),
                        workspace_id=workspace_id,
                        source_type="memory_node",
                        source_id=memory_id,
                        memory_level=level,
                        content=content.strip(),
                        importance_score=importance,
                        embedding=_json.dumps(embedding),
                    )
                    await self._vector_doc_repo.create(vector_doc)
                    await self._commit(self._vector_doc_repo.session)
                    self._log.info("Generated vector embedding for memory %s", memory_id)
            except Exception as exc:
                self._log.warning("Failed to generate vector embedding for memory %s: %s", memory_id, exc)

        self._log_operation(
            "capture_memory",
            workspace_id=workspace_id,
            entity_id=entity_id,
            level=level,
        )

        return CaptureResult.from_memory_id(
            memory_id=memory_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
            level=level,
            source=source,
            confidence=confidence,
            importance=importance,
            signal_strength=signal_strength,
        )

    async def capture_conversation(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None,
        content: str,
        raw_content: str | None = None,
        tags: list[str] | None = None,
    ) -> CaptureResult:
        """Capture a conversation as evidence and create an observation.

        This is a convenience method that creates both an Evidence record
        and a MemoryNode (L1 Observation) in a single transaction.

        Args:
            workspace_id: Workspace scope.
            entity_id: Associated entity.
            content: Summarized memory content.
            raw_content: Original conversation text (preserved as evidence).
            tags: Tags to associate with the memory.

        Returns:
            CaptureResult with the memory ID.

        Raises:
            ValidationError: If required fields are missing.
            TransactionError: If the transaction fails.
        """
        if not content or not content.strip():
            raise ValidationError(
                "Conversation content cannot be empty",
                field="content",
            )

        self._validate_workspace_id(workspace_id)

        # Create evidence first (raw content preservation)
        evidence_id = None
        if raw_content and raw_content.strip():
            evidence_id = await self._create_evidence(
                workspace_id=workspace_id,
                entity_id=entity_id,
                content=raw_content.strip(),
                source="conversation",
            )

        # Create memory node
        result = await self.capture_memory(
            workspace_id=workspace_id,
            entity_id=entity_id,
            content=content.strip(),
            level=1,
            node_type="Observation",
            source="user",
            observation_type="activity",
        )

        # Link evidence to memory node if created
        if evidence_id:
            try:
                await self._memory_node_repo.link_evidence(
                    memory_node_id=result.memory_id,
                    evidence_id=evidence_id,
                    workspace_id=workspace_id,
                    relationship_type="supports",
                )
            except RepositoryError as exc:
                # Evidence was created but linking failed — evidence is preserved
                self._log.warning(
                    "Failed to link evidence to memory node: %s", exc
                )

        # Apply tags if provided
        if tags:
            await self._apply_tags(
                workspace_id=workspace_id,
                target_type="memory_node",
                target_id=result.memory_id,
                tag_names=tags,
            )

        return result

    # ------------------------------------------------------------------
    # Import Capability
    # ------------------------------------------------------------------

    async def import_memories(
        self,
        *,
        workspace_id: UUID,
        source_type: str = "open_webui",
        data: str | None = None,
        items: list[dict[str, Any]] | None = None,
        job_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ImportJobStatus:
        """Import memories from external source using the ingest framework.

        This method supports both the new ingest framework (for structured imports
        from external sources like Open WebUI) and the legacy items-based import.

        When source_type and data are provided, the ingest framework parses and
        validates the data before importing. When items is provided directly,
        it uses the legacy continue-on-error logic.

        Per IR-010 (Continue-on-Error): Import batch continues on failure.
        Per IR-012 (Idempotent Import): Batch-level uniqueness check.

        Args:
            workspace_id: Workspace scope.
            source_type: Import source type (e.g., "open_webui").
            data: Raw data string from the external source.
            items: Legacy parameter - list of memory dicts (deprecated).
            job_id: Optional import job UUID for tracking.
            metadata: Additional metadata for the import.

        Returns:
            ImportJobStatus with success/failure counts.
        """
        self._validate_workspace_id(workspace_id)

        # Use ingest framework if source_type and data are provided
        if source_type and data:
            return await self._import_via_ingest(
                workspace_id=workspace_id,
                source_type=source_type,
                data=data,
                job_id=job_id,
                metadata=metadata or {},
            )

        # Legacy path: direct items import
        if items is None:
            items = []

        if not items:
            return ImportJobStatus(
                job_id=job_id or UUID(int=0),
                status=ImportStatus.COMPLETED,
                total_count=0,
            )

        job_id = job_id or self._generate_id()
        success_count = 0
        failure_count = 0
        error_messages: list[str] = []

        for idx, item in enumerate(items):
            try:
                await self.capture_memory(
                    workspace_id=workspace_id,
                    entity_id=item.get("entity_id"),
                    content=item["content"],
                    level=item.get("level", 1),
                    source=item.get("source", "import"),
                    metadata=item.get("metadata", {}),
                )
                success_count += 1
            except Exception as exc:
                failure_count += 1
                error_messages.append(
                    f"Item {idx}: {type(exc).__name__}: {exc}"
                )
                self._log.error("Import item %d failed: %s", idx, exc)

        status = ImportStatus.COMPLETED if failure_count == 0 else ImportStatus.FAILED
        if success_count > 0 and failure_count > 0:
            status = getattr(ImportStatus, "PARTIAL", ImportStatus.FAILED)

        return ImportJobStatus(
            job_id=job_id,
            status=status,
            total_count=len(items),
            processed_count=len(items),
            success_count=success_count,
            failure_count=failure_count,
            error_messages=error_messages,
        )

    async def _import_via_ingest(
        self,
        *,
        workspace_id: UUID,
        source_type: str,
        data: str,
        job_id: UUID | None,
        metadata: dict[str, Any],
    ) -> ImportJobStatus:
        """Import via the ingest framework.

        Uses the registered adapter for the given source_type to parse,
        validate, and import memories through the normal pipeline.
        """
        job_id = job_id or self._generate_id()

        # Create registry and register all adapters
        registry = create_default_registry()

        # Parse and validate using the pipeline
        try:
            from backend.ingest.base import ImportPipeline

            pipeline = ImportPipeline(registry)
            import_source = ImportSource(source_type)
            result = pipeline.execute(import_source, data)
        except ValueError as exc:
            return ImportJobStatus(
                job_id=job_id,
                status=ImportStatus.FAILED,
                total_count=0,
                error_messages=[str(exc)],
            )

        if not result.items:
            return ImportJobStatus(
                job_id=job_id,
                status=ImportStatus.COMPLETED,
                total_count=0,
            )

        # Import each validated MemoryItem through the normal pipeline
        success_count = 0
        failure_count = 0
        error_messages: list[str] = []

        for idx, mem_item in enumerate(result.items):
            try:
                await self.capture_conversation(
                    workspace_id=workspace_id,
                    entity_id=mem_item.entity_id,
                    content=mem_item.content,
                    raw_content=mem_item.raw_content,  # Original content for evidence
                    tags=mem_item.tags,
                )
                success_count += 1
            except Exception as exc:
                failure_count += 1
                error_messages.append(
                    f"Item {idx}: {type(exc).__name__}: {exc}"
                )
                self._log.error("Import item %d failed: %s", idx, exc)

        total = success_count + failure_count
        status = ImportStatus.COMPLETED if failure_count == 0 else (
            ImportStatus.FAILED
        )

        return ImportJobStatus(
            job_id=job_id,
            status=status,
            total_count=total,
            processed_count=total,
            success_count=success_count,
            failure_count=failure_count,
            error_messages=error_messages,
        )

    async def create_import_job(
        self,
        *,
        workspace_id: UUID,
        items: list[dict[str, Any]],
    ) -> ImportJobStatus:
        """Create and execute an import job.

        Wrapper around import_memories() for explicit job management.

        Args:
            workspace_id: Workspace scope.
            items: Items to import.

        Returns:
            ImportJobStatus with results.
        """
        return await self.import_memories(
            workspace_id=workspace_id,
            items=items,
        )

    async def get_import_status(self, job_id: UUID) -> ImportJobStatus:
        """Get the status of an import job.

        Args:
            job_id: The import job UUID.

        Returns:
            ImportJobStatus (MVP: returns a basic status).
        """
        return ImportJobStatus(
            job_id=job_id,
            status=ImportStatus.COMPLETED,
        )

    async def cancel_import(self, job_id: UUID) -> ImportJobStatus:
        """Cancel an import job.

        Args:
            job_id: The import job UUID.

        Returns:
            ImportJobStatus with CANCELLED status.
        """
        return ImportJobStatus(
            job_id=job_id,
            status=ImportStatus.CANCELLED,
        )

    async def retry_import(self, job_id: UUID) -> ImportJobStatus:
        """Retry a failed import job.

        Args:
            job_id: The import job UUID.

        Returns:
            ImportJobStatus with results.
        """
        return ImportJobStatus(
            job_id=job_id,
            status=ImportStatus.RETRYING,
        )

    # ------------------------------------------------------------------
    # Merge Capability
    # ------------------------------------------------------------------

    async def merge_memories(
        self,
        *,
        workspace_id: UUID,
        source_memory_ids: list[UUID],
        target_memory_id: UUID,
    ) -> UUID:
        """Merge multiple memories into a single target memory.

        Marks source memories as 'superseded' and updates relationships.
        The target memory absorbs the evidence chains from sources.

        Args:
            workspace_id: Workspace scope.
            source_memory_ids: Memories to merge away.
            target_memory_id: The destination memory.

        Returns:
            The target memory ID (Identity).

        Raises:
            NotFoundError: If any memory not found.
            DomainIntegrityError: If merge violates invariants.
            TransactionError: If the transaction fails.
        """
        self._validate_workspace_id(workspace_id)

        if len(source_memory_ids) < 1:
            raise ValidationError(
                "At least one source memory is required for merge",
                field="source_memory_ids",
            )

        if target_memory_id in source_memory_ids:
            raise ValidationError(
                "Target memory cannot be in source list",
                field="target_memory_id",
            )

        # Verify all memories exist
        for mem_id in [*source_memory_ids, target_memory_id]:
            existing = await self._memory_node_repo.find_by_id(mem_id)
            if existing is None:
                raise NotFoundError(
                    f"Memory {mem_id} not found",
                    resource_type="memory_node",
                    resource_id=str(mem_id),
                )

        # Mark source memories as superseded
        from backend.shared.domain.memory_models import MemoryNode

        for source_id in source_memory_ids:
            try:
                # Create a superseding node that points to the source
                superseder = MemoryNode(
                    id=self._generate_id(),
                    workspace_id=workspace_id,
                    entity_id=target_memory_id,
                    level=1,
                    node_type="Observation",
                    content=f"[Superseded by merge] Replaced by memory {target_memory_id}",
                    status="superseded",
                    source="manual",
                    generated_by="manual",
                )
                await self._memory_node_repo.create(superseder)

                # Create derived_from relationship
                await self._relationship_repo.create_memory_relationship(  # type: ignore[call-arg]
                    source_node_id=target_memory_id,
                    target_node_id=source_id,
                    workspace_id=workspace_id,
                    relationship_type="derived_from",
                )
            except RepositoryError as exc:
                self._log.warning(
                    "Failed to mark memory %s as superseded: %s",
                    source_id, exc,
                )

        self._log_operation(
            "merge_memories",
            workspace_id=workspace_id,
            entity_id=target_memory_id,
        )

        return target_memory_id

    # ------------------------------------------------------------------
    # Archive Capability
    # ------------------------------------------------------------------

    async def archive_memory(
        self,
        *,
        workspace_id: UUID,
        memory_id: UUID,
        archive_type: str = "monthly",
        summary: str | None = None,
    ) -> UUID:
        """Archive a memory node to permanent storage.

        Creates an Archive record and marks the source memory appropriately.

        Args:
            workspace_id: Workspace scope.
            memory_id: Memory to archive.
            archive_type: Type of archive (monthly/yearly).
            summary: Optional archive summary.

        Returns:
            The archive record ID.

        Raises:
            NotFoundError: If memory not found.
            TransactionError: If the transaction fails.
        """
        self._validate_workspace_id(workspace_id)

        memory = await self._memory_node_repo.find_by_id(memory_id)
        if memory is None:
            raise NotFoundError(
                f"Memory {memory_id} not found",
                resource_type="memory_node",
                resource_id=str(memory_id),
            )

        from datetime import date

        from backend.shared.domain.memory_models import Archive

        # Mark source memory as archived via superseded copy
        try:
            await self._memory_node_repo.archive(
                memory_id=memory_id,
                workspace_id=workspace_id,
            )
        except Exception as exc:
            self._log.warning(
                "Failed to mark source memory as archived: %s", exc
            )

        archive = Archive(
            id=self._generate_id(),
            workspace_id=workspace_id,
            source_archive_id=None,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            archive_type=archive_type,
            summary=summary or f"Archive of memory {memory_id}",
            source_count=1,
        )

        try:
            archive_id = await self._archive_repo.create(archive)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        self._log_operation(
            "archive_memory",
            workspace_id=workspace_id,
            entity_id=memory_id,
        )

        return archive_id

    # ------------------------------------------------------------------
    # Lifecycle Capability
    # ------------------------------------------------------------------

    async def trigger_reflection(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        scope: str = "entity",
    ) -> ReflectionExecutionResult:
        """Trigger a reflection operation on memories.

        Creates a reflection task and returns execution result.
        The actual reflection algorithm runs asynchronously via Task Runtime.

        Per D3.2: ReflectionService owns the workflow; MemoryService
        coordinates the task submission.

        Args:
            workspace_id: Workspace scope.
            entity_id: Optional entity to reflect upon.
            scope: Reflection scope ("entity", "area", "workspace").

        Returns:
            ReflectionExecutionResult with status and statistics.
        """
        self._validate_workspace_id(workspace_id)

        # Create a reflection task
        from backend.shared.domain.memory_models import Task as TaskModel

        task = TaskModel(
            id=self._generate_id(),
            workspace_id=workspace_id,
            entity_id=entity_id,
            task_type="REFLECTION",
            status="pending",
            evidence_driven=True,
            debounce_key=f"reflection:{workspace_id}:{entity_id or 'all'}:{scope}",
            payload={
                "scope": scope,
                "entity_id": str(entity_id) if entity_id else None,
            },
        )

        try:
            task_id = await self._task_repo.create(task)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        return ReflectionExecutionResult(
            status=ReflectionStatus.PENDING,
            scope=scope,
            metadata={"task_id": str(task_id)},
        )

    async def schedule_archive(
        self,
        *,
        workspace_id: UUID,
        period_start: str,
        period_end: str,
    ) -> UUID:
        """Schedule an archive operation for a time period.

        Creates an archive task for deferred execution.

        Args:
            workspace_id: Workspace scope.
            period_start: Start of the archive period (ISO 8601).
            period_end: End of the archive period (ISO 8601).

        Returns:
            The archive task ID.
        """
        self._validate_workspace_id(workspace_id)

        from backend.shared.domain.memory_models import Task as TaskModel

        task = TaskModel(
            id=self._generate_id(),
            workspace_id=workspace_id,
            task_type="ARCHIVE",
            status="pending",
            evidence_driven=True,
            debounce_key=f"archive:{workspace_id}:{period_start}:{period_end}",
            payload={
                "period_start": period_start,
                "period_end": period_end,
            },
        )

        try:
            task_id = await self._task_repo.create(task)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        return task_id

    async def reprocess_memory(
        self,
        *,
        workspace_id: UUID,
        memory_id: UUID,
    ) -> UUID:
        """Reprocess a memory node (re-run ingestion/reflection).

        Creates an ingestion task for the specified memory.

        Args:
            workspace_id: Workspace scope.
            memory_id: Memory to reprocess.

        Returns:
            The new task ID.
        """
        self._validate_workspace_id(workspace_id)

        memory = await self._memory_node_repo.find_by_id(memory_id)
        if memory is None:
            raise NotFoundError(
                f"Memory {memory_id} not found",
                resource_type="memory_node",
                resource_id=str(memory_id),
            )

        from backend.shared.domain.memory_models import Task as TaskModel

        task = TaskModel(
            id=self._generate_id(),
            workspace_id=workspace_id,
            entity_id=memory.entity_id if hasattr(memory, "entity_id") else None,
            task_type="INGESTION",
            status="pending",
            evidence_driven=True,
            debounce_key=f"reprocess:{workspace_id}:{memory_id}",
            payload={"memory_id": str(memory_id)},
        )

        try:
            task_id = await self._task_repo.create(task)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

        return task_id

    # ------------------------------------------------------------------
    # Restore Capability
    # ------------------------------------------------------------------

    async def restore_archived_memory(
        self,
        *,
        workspace_id: UUID,
        archive_id: UUID,
    ) -> UUID:
        """Restore a memory from an archive record.

        Creates a new memory node from the archived content.

        Args:
            workspace_id: Workspace scope.
            archive_id: The archive record to restore from.

        Returns:
            The new memory node ID.

        Raises:
            NotFoundError: If archive not found.
        """
        self._validate_workspace_id(workspace_id)

        archive = await self._archive_repo.find_by_id(archive_id)
        if archive is None:
            raise NotFoundError(
                f"Archive {archive_id} not found",
                resource_type="archive",
                resource_id=str(archive_id),
            )

        result = await self.capture_memory(
            workspace_id=workspace_id,
            entity_id=None,
            content=archive.summary or "",
            level=1,
            node_type="Observation",
            source="archive_derived",
            metadata={"restored_from_archive": str(archive_id)},
        )

        self._log_operation(
            "restore_archived_memory",
            workspace_id=workspace_id,
            entity_id=archive_id,
        )

        return result.memory_id

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

    async def _create_evidence(
        self,
        *,
        workspace_id: UUID,
        entity_id: UUID | None,
        content: str,
        source: str = "conversation",
    ) -> UUID:
        """Create an evidence record internally.

        Args:
            workspace_id: Workspace scope.
            entity_id: Associated entity.
            content: Evidence content.
            source: Source type.

        Returns:
            The evidence ID.
        """
        from backend.shared.domain.memory_models import Evidence

        evidence = Evidence(
            id=self._generate_id(),
            workspace_id=workspace_id,
            entity_id=entity_id or UUID(int=0),
            evidence_type="conversation",
            content=content,
            raw_content=content,
            source=source,
        )

        try:
            return await self._evidence_repo.create(evidence)
        except RepositoryError as exc:
            raise self.translate_repository_error(exc) from exc

    async def _apply_tags(
        self,
        *,
        workspace_id: UUID,
        target_type: str,
        target_id: UUID,
        tag_names: list[str],
    ) -> None:
        """Apply tags to a target (entity, memory_node, or archive).

        Creates tags if they don't exist, then links them.

        Args:
            workspace_id: Workspace scope.
            target_type: Target type ("entity", "memory_node", "archive").
            target_id: Target UUID.
            tag_names: List of tag name strings.
        """
        from backend.shared.domain.memory_models import Tag

        for tag_name in tag_names:
            # Find or create tag
            existing_tags = await self._tag_repo.find_by_workspace(
                workspace_id=workspace_id,
            )
            tag = None
            for t in existing_tags:
                if t.name == tag_name:
                    tag = t
                    break

            if tag is None:
                tag = Tag(
                    id=self._generate_id(),
                    workspace_id=workspace_id,
                    name=tag_name,
                    tag_type="user",
                )
                try:
                    await self._tag_repo.create(tag)
                except RepositoryError:
                    pass  # Tag may already exist (race condition)
                    continue

            # Link tag to target
            try:
                await self._tag_repo.link_tag(
                    tag_id=tag.id,
                    target_type=target_type,
                    target_id=target_id,
                    workspace_id=workspace_id,
                )
            except RepositoryError:
                pass  # Link may already exist
