"""Memory Domain ORM models.

These SQLAlchemy ORM models map directly to the physical tables defined
in 09_Database_Physical_Design.md. Each model corresponds to one or more
tables managed by the Memory Domain repositories.

Per 09 §09.1.2 (Range Lock): These models must NOT be modified without
an ADR. Column names, types, constraints, and indexes must match the
approved physical design exactly.

Tables defined here:
- MemoryNode (memory_nodes)
- MemoryEvidence (memory_evidences)
- Evidence (evidences)
- Archive (archives)
- Tag (tags)
- TagLink (tag_links)
- Entity (entities) — D2.3
- Area (areas) — D2.3
- Workspace (workspace) — D2.3
- UserProfile (user_profiles) — D2.3
- EntityRelationship (relationships) — D2.3
- MemoryRelationship (memory_relationships) — D2.3
- Candidate (candidates) — D2.4
- Task (tasks) — D2.5
- VectorDoc (vector_documents) — D2.6

Imported by: MemoryNodeRepository, EvidenceRepository, ArchiveRepository,
TagRepository, MemoryQueryRepository, EntityRepository, RelationshipRepository,
EntityQueryRepository, CandidateRepository, TaskRepository, VectorDocRepository,
VectorQueryRepository.
NOT imported by: Service Layer, Engine Layer (boundary rule G-013).
"""

from __future__ import annotations
from datetime import datetime

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.infrastructure.database.engine import Base

# ---------------------------------------------------------------------------
# Evidence — 09.4.6
# ---------------------------------------------------------------------------


class Evidence(Base):
    """ORM model for the evidences table (09.4.6).

    Evidence is immutable — once created, never deleted or modified.
    Every MemoryNode must have at least one evidence link (No Orphan Memory).
    """

    __tablename__ = "evidences"
    __table_args__ = (
        CheckConstraint("char_length(content) > 0", name="chk_evidence_not_empty"),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    area_id: Mapped[UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="SET NULL")
    )

    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text)

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="conversation"
    )
    _meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    memory_evidences: Mapped[list[MemoryEvidence]] = relationship(
        "MemoryEvidence", back_populates="evidence", lazy="selectin"
    )

    # Indexes (declarative — actual CREATE INDEX in DDL)
    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# MemoryNode — 09.4.5
# ---------------------------------------------------------------------------


class MemoryNode(Base):
    """ORM model for the memory_nodes table (09.4.5).

    Memory hierarchy: L1=Observation, L2=Pattern, L3=Belief.
    Level 4 (State) is runtime-only, never persisted.
    Memory is immutable: no UPDATE/DELETE (correction via new node + relationship).
    """

    __tablename__ = "memory_nodes"
    __table_args__ = (
        CheckConstraint(
            "(level = 1 AND observation_type IN ("
            "'activity', 'decision', 'preference', 'fact', "
            "'goal', 'problem', 'event')) OR level != 1",
            name="chk_observation_type",
        ),
        CheckConstraint(
            "(level = 1 AND node_type = 'Observation') OR "
            "(level = 2 AND node_type = 'Pattern') OR "
            "(level = 3 AND node_type = 'Belief')",
            name="chk_level_type_consistency",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="chk_confidence_range"),
        CheckConstraint("importance >= 0.0 AND importance <= 1.0", name="chk_importance_range"),
        CheckConstraint(
            "signal_strength >= 0.0 AND signal_strength <= 1.0", name="chk_signal_strength_range"
        ),
        CheckConstraint(
            "status IN ('active', 'candidate', 'deprecated', 'superseded', 'orphaned')",
            name="chk_memory_status",
        ),
        CheckConstraint(
            "source IN ('user', 'manual', 'explicit_command', 'archive_derived', 'ai_reflect', 'import')",
            name="chk_memory_source",
        ),
        CheckConstraint(
            "generated_by IN ('user', 'manual', 'ai_reflect', 'archive', 'import')",
            name="chk_memory_generated_by",
        ),
        CheckConstraint("level IN (1, 2, 3)", name="chk_level_valid"),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    parent_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("memory_nodes.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True
    )

    level: Mapped[int] = mapped_column(Integer, nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    observation_type: Mapped[str | None] = mapped_column(String(50))

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    generated_by: Mapped[str] = mapped_column(String(50), nullable=False, default="user")

    evidence_links: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    contradict_evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    _meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    memory_evidences: Mapped[list[MemoryEvidence]] = relationship(
        "MemoryEvidence", back_populates="memory_node", lazy="selectin"
    )
    parent: Mapped[UUID] = relationship(
        "MemoryNode", remote_side=[id], lazy="select"
    )
    children: Mapped[list[MemoryNode]] = relationship(
        "MemoryNode", back_populates="parent", lazy="selectin"
    )

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# MemoryEvidence — 09.4.7
# ---------------------------------------------------------------------------


class MemoryEvidence(Base):
    """ORM model for the memory_evidences table (09.4.7).

    Junction table linking memory_nodes to evidences (many-to-many).
    Represents the evidence chain within a MemoryNode aggregate.
    """

    __tablename__ = "memory_evidences"
    __table_args__ = (
        UniqueConstraint("memory_node_id", "evidence_id", name="uk_memory_evidences"),
        CheckConstraint(
            "relationship_type IN ('supports', 'derived_from', 'contradicts', 'attenuates')",
            name="chk_relationship_type",
        ),
        CheckConstraint("contribution_weight >= 0.0 AND contribution_weight <= 1.0", name="chk_weight_range"),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    memory_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_nodes.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False
    )

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, default="supports")
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    memory_node: Mapped[MemoryNode] = relationship("MemoryNode", back_populates="memory_evidences")
    evidence: Mapped[Evidence] = relationship("Evidence", back_populates="memory_evidences")

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# Archive — 09.4.12
# ---------------------------------------------------------------------------


class Archive(Base):
    """ORM model for the archives table (09.4.12).

    Cognitive compression archives (monthly/yearly).
    Hierarchical: source_archive_id self-reference (archive-of-archive).
    """

    __tablename__ = "archives"
    __table_args__ = (
        CheckConstraint(
            "archive_type IN ('monthly', 'yearly')", name="chk_archive_type"
        ),
        CheckConstraint("period_start <= period_end", name="chk_archive_period"),
        CheckConstraint("source_count >= 0", name="chk_source_count_non_negative"),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    source_archive_id: Mapped[UUID] = mapped_column(
        ForeignKey("archives.id", ondelete="SET NULL")
    )

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    archive_type: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    parent_archive: Mapped[UUID] = relationship(
        "Archive", remote_side=[id], lazy="select"
    )
    child_archives: Mapped[list[Archive]] = relationship(
        "Archive", back_populates="parent_archive", lazy="selectin"
    )

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# Tag — 09.4.10
# ---------------------------------------------------------------------------


class Tag(Base):
    """ORM model for the tags table (09.4.10).

    Tag definitions (system/ai/user). Three-tier tag system.
    """

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uk_tags_workspace_name"),
        CheckConstraint("tag_type IN ('system', 'ai', 'user')", name="chk_tag_type"),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tag_type: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    color: Mapped[str | None] = mapped_column(String(7))

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    tag_links: Mapped[list[TagLink]] = relationship(
        "TagLink", back_populates="tag", lazy="selectin"
    )

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# TagLink — 09.4.11
# ---------------------------------------------------------------------------


class TagLink(Base):
    """ORM model for the tag_links table (09.4.11).

    Many-to-many junction between tags and targets (entity, memory_node, archive).
    """

    __tablename__ = "tag_links"
    __table_args__ = (
        UniqueConstraint("tag_id", "target_type", "target_id", name="uk_tag_links"),
        CheckConstraint(
            "target_type IN ('entity', 'memory_node', 'archive')", name="chk_target_type"
        ),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    tag: Mapped[Tag] = relationship("Tag", back_populates="tag_links")

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# Entity — 09.4.4
# ---------------------------------------------------------------------------

class Entity(Base):
    """ORM model for the entities table (09.4.4).

    Entity identity, canonical_name, aliases, type, metadata, counters.
    Hierarchical: parent_entity_id self-reference.
    Unique: (workspace_id, entity_type, canonical_name).

    Entity types: Project, Person, Organization, Tool, Technology,
    Concept, Event, Location, Object, Agent, Model, Document.
    """

    __tablename__ = "entities"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ("
            "'Project', 'Person', 'Organization', 'Tool', 'Technology',"
            "'Concept', 'Event', 'Location', 'Object', 'Agent', 'Model', 'Document'"
            ")",
            name="chk_entity_type",
        ),
        UniqueConstraint(
            "workspace_id", "entity_type", "canonical_name", name="uk_entities_type_name"
        ),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    area_id: Mapped[UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )
    parent_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL")
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="SET NULL")
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    _meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    belief_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pattern_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relationship_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships (self-referential hierarchy)
    parent: Mapped["Entity | None"] = relationship(
        "Entity",
        remote_side=[id],
        back_populates="children",
        lazy="select",
    )
    children: Mapped[list["Entity"]] = relationship(
        "Entity",
        back_populates="parent",
        lazy="selectin",
    )

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# Area — 09.4.3
# ---------------------------------------------------------------------------

class Area(Base):
    """ORM model for the areas table (09.4.3).

    Domain area classification (hierarchical via parent_area_id).
    """

    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uk_areas_workspace_name"),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    parent_area_id: Mapped[UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(7))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships (self-referential hierarchy)
    parent: Mapped["Area | None"] = relationship(
        "Area",
        remote_side=[id],
        back_populates="children",
        lazy="select",
    )
    children: Mapped[list["Area"]] = relationship(
        "Area",
        back_populates="parent",
        lazy="selectin",
    )

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# Workspace — 09.4.1
# ---------------------------------------------------------------------------

class Workspace(Base):
    """ORM model for the workspace table (09.4.1).

    Top-level container (singleton, seeded on init).
    """

    __tablename__ = "workspace"
    __table_args__ = (
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# UserProfile — 09.4.2
# ---------------------------------------------------------------------------

class UserProfile(Base):
    """ORM model for the user_profiles table (09.4.2).

    User identity and metadata.
    """

    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "external_user_id", name="uk_user_profiles_external"),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    external_user_id: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    _meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# EntityRelationship — 09.4.8
# ---------------------------------------------------------------------------

class EntityRelationship(Base):
    """ORM model for the relationships table (09.4.8).

    Entity-to-entity relationships (10 core types).
    Multiple relationships per entity pair are allowed (different types).
    No uniqueness constraint on (source_id, target_id) alone.
    """

    __tablename__ = "relationships"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ("
            "'belongs_to', 'part_of', 'uses', 'depends_on', 'related_to',"
            "'affects', 'derived_from', 'owns', 'created_by', 'about'"
            ")",
            name="chk_relationship_type",
        ),
        CheckConstraint("source_id != target_id", name="chk_no_self_relationship"),
        CheckConstraint("strength >= 0.0 AND strength <= 1.0", name="chk_strength_range"),
        UniqueConstraint(
            "source_id", "target_id", "relationship_type", name="uk_relationship_direction"
        ),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    _meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# MemoryRelationship — 09.4.14
# ---------------------------------------------------------------------------

class MemoryRelationship(Base):
    """ORM model for the memory_relationships table (09.4.14).

    MemoryNode-to-MemoryNode relationships.
    Relationship types: supports, derived_from, contradicts, attenuates.
    """

    __tablename__ = "memory_relationships"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('supports', 'derived_from', 'contradicts', 'attenuates')",
            name="chk_memory_relationship_type",
        ),
        CheckConstraint(
            "source_node_id != target_node_id", name="chk_no_self_memory_rel"
        ),
        CheckConstraint(
            "contribution_weight >= 0.0 AND contribution_weight <= 1.0",
            name="chk_memory_rel_weight_range",
        ),
        UniqueConstraint(
            "source_node_id", "target_node_id", "relationship_type",
            name="uk_memory_relationship_direction",
        ),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    source_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_nodes.id", ondelete="CASCADE"), nullable=False
    )

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    _meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# Candidate — 09.4.13
# ---------------------------------------------------------------------------


class Candidate(Base):
    """ORM model for the candidates table (09.4.13).

    Reflection work object — pattern or belief awaiting promotion
    to a formal MemoryNode. Self-contained aggregate with its own
    metadata and evidence snapshot.

    Candidate types: pattern, belief
    Status: candidate, confirmed, archived, orphaned
    Evidence-based: evidence_count >= 1, evidence_chain not empty
    Ingested by: ingestion_pipeline only
    Verified by: rule_engine / reflection_engine only
    """

    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint(
            "candidate_type IN ('pattern', 'belief')",
            name="chk_candidate_type",
        ),
        CheckConstraint(
            "evidence_count >= 1",
            name="chk_candidate_has_evidence",
        ),
        CheckConstraint(
            "evidence_strength >= 0.0 AND evidence_strength <= 1.0",
            name="chk_candidate_evidence_strength",
        ),
        CheckConstraint(
            "jsonb_array_length(evidence_chain) > 0",
            name="chk_candidate_evidence_chain_not_empty",
        ),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    area_id: Mapped[UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_type: Mapped[str] = mapped_column(String(20), nullable=False)

    evidence_source: Mapped[str] = mapped_column(String(50), nullable=False, default="observation")
    evidence_id: Mapped[UUID] = mapped_column()
    evidence_chain: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate")

    ingested_by: Mapped[str] = mapped_column(String(50), nullable=False, default="ingestion_pipeline")
    ingestion_timestamp: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    verified_at: Mapped[UUID] = mapped_column()
    verified_by: Mapped[str | None] = mapped_column(String(50))

    modified_by: Mapped[str | None] = mapped_column(String(50))
    modification_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# Task — 09.4.15
# ---------------------------------------------------------------------------


class Task(Base):
    """ORM model for the tasks table (09.4.15).

    Unified task queue for the Personal Memory Hub. All task types
    (INGESTION, REFLECTION, ACTIVATION, ARCHIVE) share this table.

    Task types: INGESTION, REFLECTION, ACTIVATION, ARCHIVE
    Status: pending, running, completed, failed, dead_letter
    Debounce: UNIQUE (workspace_id, task_type, debounce_key) WHERE status IN ('pending', 'running')
    Retry: retry_count, max_retries, exponential backoff
    Payload: JSONB (Task Runtime does not parse)

    Foreign Keys:
    - workspace_id → CASCADE
    - entity_id → SET NULL
    - area_id → SET NULL
    """

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('INGESTION', 'REFLECTION', 'ACTIVATION', 'ARCHIVE')",
            name="chk_task_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'dead_letter')",
            name="chk_task_status",
        ),
        UniqueConstraint(
            "workspace_id", "task_type", "debounce_key",
            name="uk_tasks_debounce",

        ),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL")
    )
    area_id: Mapped[UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )

    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    evidence_driven: Mapped[bool] = mapped_column(nullable=False, default=True)
    debounce_key: Mapped[str | None] = mapped_column(String(255))

    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    completed_at: Mapped[UUID] = mapped_column()

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# VectorDoc — 09.4.9
# ---------------------------------------------------------------------------


class VectorDoc(Base):
    """ORM model for the vector_documents table (09.4.9).

    Independent vector layer storing embeddings for high-value content.
    Each VectorDoc belongs to exactly one source (MemoryNode, Archive,
    or EntitySummary) via source_id + source_type.

    Source types: memory_node, archive, entity_summary
    Memory levels: 1 (Observation), 2 (Pattern), 3 (Belief), 4 (State marker)
    Importance score: 0.0–1.0
    Embedding: VECTOR(1536) stored as text (pgvector extension at DB level)

    Foreign Keys:
    - workspace_id → CASCADE
    - area_id → SET NULL
    - entity_id → SET NULL
    """

    __tablename__ = "vector_documents"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('memory_node', 'archive', 'entity_summary')",
            name="chk_vector_doc_source_type",
        ),
        CheckConstraint(
            "memory_level IN (1, 2, 3, 4)",
            name="chk_vector_doc_memory_level",
        ),
        CheckConstraint(
            "importance_score >= 0.0 AND importance_score <= 1.0",
            name="chk_vector_doc_importance_score",
        ),
        {
            
        },
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    area_id: Mapped[UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL")
    )

    memory_level: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Embedding stored as text representation (e.g., '[0.1,0.2,...]').
    # The pgvector extension is enabled at DB level via engine.py.
    embedding: Mapped[str | None] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    __mapper_args__ = {"eager_defaults": True}


__all__ = [
    "Archive",
    "Area",
    "Candidate",
    "Entity",
    "EntityRelationship",
    "Evidence",
    "MemoryEvidence",
    "MemoryNode",
    "MemoryRelationship",
    "Tag",
    "TagLink",
    "Task",
    "UserProfile",
    "VectorDoc",
    "Workspace",
]
