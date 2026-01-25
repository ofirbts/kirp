"""
Event & Audit models — Event-sourced audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from src.models.base import Base


class Sensitivity(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    CONFIDENTIAL = "confidential"


class EventModel(Base):
    """Event metadata in PostgreSQL (full event in MongoDB)."""

    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    space_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    source = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    sensitivity = Column(String(50), nullable=False)
    trace_id = Column(String(255), nullable=True, index=True)
    extra = Column(JSON, default=dict)  # metadata reserved by SQLAlchemy
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    embedding = Column(ARRAY(Float), nullable=True)  # Vector for search
    risk_score = Column(Float, nullable=True)
    requires_approval = Column(Boolean, default=False)
    approved = Column(Boolean, nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Governance audit trail."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=False)
    resource_id = Column(String(255), nullable=True)
    result = Column(String(50), nullable=False)  # allowed, denied, approved, rejected
    policy_id = Column(String(255), nullable=True)
    risk_score = Column(Float, nullable=True)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
