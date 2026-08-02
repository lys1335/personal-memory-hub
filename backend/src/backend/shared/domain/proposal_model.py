"""
Proposal ORM model.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Double, Integer, String, Text

from backend.shared.infrastructure.database.engine import Base


class Proposal(Base):
    """Reflection proposal model."""

    __tablename__ = "proposals"

    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False)
    type = Column(String(20), nullable=False)
    source_level = Column(DateTime, default=datetime.utcnow)
    target_level = Column(Integer, nullable=False)
    entity = Column(String(255), nullable=True)
    evidence_chain = Column(Text, nullable=True)
    confidence = Column(Double, nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
