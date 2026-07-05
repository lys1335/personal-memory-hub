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

Imported by: MemoryNodeRepository, EvidenceRepository, ArchiveRepository,
TagRepository, MemoryQueryRepository.
NOT imported by: Service Layer, Engine Layer (boundary rule G-013).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    Select,
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
            "schema": "memory_hub",
        },
    )

    id: Mapped[Any] = mapped_column(primary_key=True)
    workspace_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.workspace.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.entities.id", ondelete="CASCADE"), nullable=False
    )
    area_id: Mapped[Any | None] = mapped_column(
        ForeignKey("memory_hub.areas.id", ondelete="SET NULL")
    )
    user_id: Mapped[Any | None] = mapped_column(
        ForeignKey("memory_hub.user_profiles.id", ondelete="SET NULL")
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
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    memory_evidences: Mapped[list["MemoryEvidence"]] = relationship(
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
            "(level = 1 AND observation_type IN ('activity', 'decision', 'preference', 'fact', 'goal', 'problem', 'event')) OR level != 1",
            name="chk_observation_type",
        ),
        CheckConstraint(
            "(level = 1 AND node_type = 'Observation') OR (level = 2 AND node_type = 'Pattern') OR (level = 3 AND node_type = 'Belief')",
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
            "source IN ('user', 'manual', 'explicit_command', 'archive_derived', 'ai_reflect')",
            name="chk_memory_source",
        ),
        CheckConstraint(
            "generated_by IN ('user', 'manual', 'ai_reflect', 'archive')",
            name="chk_memory_generated_by",
        ),
        CheckConstraint("level IN (1, 2, 3)", name="chk_level_valid"),
        {
            "schema": "memory_hub",
        },
    )

    id: Mapped[Any] = mapped_column(primary_key=True)
    workspace_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.workspace.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.entities.id", ondelete="CASCADE"), nullable=False
    )
    parent_node_id: Mapped[Any | None] = mapped_column(
        ForeignKey("memory_hub.memory_nodes.id", ondelete="SET NULL")
    )
    user_id: Mapped[Any | None] = mapped_column(
        ForeignKey("memory_hub.user_profiles.id", ondelete="SET NULL")
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
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    memory_evidences: Mapped[list["MemoryEvidence"]] = relationship(
        "MemoryEvidence", back_populates="memory_node", lazy="selectin"
    )
    parent: Mapped[Any | None] = relationship(
        "MemoryNode", remote_side=[id], lazy="select"
    )
    children: Mapped[list["MemoryNode"]] = relationship(
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
            "schema": "memory_hub",
        },
    )

    id: Mapped[Any] = mapped_column(primary_key=True)
    workspace_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.workspace.id", ondelete="CASCADE"), nullable=False
    )
    memory_node_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.memory_nodes.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.evidences.id", ondelete="CASCADE"), nullable=False
    )

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, default="supports")
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))

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
            "schema": "memory_hub",
        },
    )

    id: Mapped[Any] = mapped_column(primary_key=True)
    workspace_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.workspace.id", ondelete="CASCADE"), nullable=False
    )
    source_archive_id: Mapped[Any | None] = mapped_column(
        ForeignKey("memory_hub.archives.id", ondelete="SET NULL")
    )

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    archive_type: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    parent_archive: Mapped[Any | None] = relationship(
        "Archive", remote_side=[id], lazy="select"
    )
    child_archives: Mapped[list["Archive"]] = relationship(
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
            "schema": "memory_hub",
        },
    )

    id: Mapped[Any] = mapped_column(primary_key=True)
    workspace_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.workspace.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tag_type: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    color: Mapped[str | None] = mapped_column(String(7))

    created_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    tag_links: Mapped[list["TagLink"]] = relationship(
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
            "schema": "memory_hub",
        },
    )

    id: Mapped[Any] = mapped_column(primary_key=True)
    workspace_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.workspace.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[Any] = mapped_column(
        ForeignKey("memory_hub.tags.id", ondelete="CASCADE"), nullable=False
    )

    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[Any] = mapped_column(nullable=False)

    created_at: Mapped[Any] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    tag: Mapped[Tag] = relationship("Tag", back_populates="tag_links")

    __mapper_args__ = {"eager_defaults": True}


__all__ = [
    "Archive",
    "Evidence",
    "MemoryEvidence",
    "MemoryNode",
    "Tag",
    "TagLink",
]
