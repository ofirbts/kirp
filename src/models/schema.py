"""
Schema models — Tasks, projects, life areas, categories.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import Base


class SchemaEntity(str, Enum):
    TASK = "task"
    PROJECT = "project"
    LIFE_AREA = "life_area"
    CATEGORY = "category"


class SchemaNode(Base):
    """Schema entity (task, project, etc.)."""

    __tablename__ = "schema_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    space_id = Column(String(255), nullable=False, index=True)
    entity = Column(String(50), nullable=False, index=True)  # SchemaEntity
    title = Column(String(500), nullable=False)
    extra = Column(JSON, default=dict)  # metadata reserved by SQLAlchemy
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
