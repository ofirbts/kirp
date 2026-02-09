"""
Schema models — Tasks, projects, life areas, categories with graph relationships.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class SchemaEntity(str, Enum):
    TASK = "task"
    PROJECT = "project"
    COMMITMENT = "commitment"
    LIFE_AREA = "life_area"
    CATEGORY = "category"


# Canonical Life Areas for Second Brain (Work, Family, Health, Learning)
LIFE_AREA_NAMES = ("Work", "Family", "Health", "Learning")


class SchemaNode(Base):
    """
    Schema entity (task, project, life area, category) with graph relationships.
    
    Supports hierarchical structure:
    - LifeArea → Projects → Tasks
    - Category → Items (polymorphic)
    """

    __tablename__ = "schema_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    space_id = Column(String(255), nullable=False, index=True)
    entity = Column(String(50), nullable=False, index=True)  # SchemaEntity
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)  # Optional description
    
    # Graph relationships
    parent_id = Column(UUID(as_uuid=True), ForeignKey("schema_nodes.id"), nullable=True, index=True)
    
    # Task-specific fields
    status = Column(String(50), nullable=True)  # pending, in_progress, completed, blocked
    priority = Column(String(50), nullable=True)  # low, medium, high, critical
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra = Column(JSON, default=dict)  # Flexible metadata (tags, custom fields, etc.)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    parent = relationship("SchemaNode", remote_side=[id], backref="children")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "space_id": self.space_id,
            "entity": self.entity,
            "title": self.title,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "metadata": self.extra or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SchemaNode(id={self.id}, entity={self.entity}, title={self.title[:50]})>"
