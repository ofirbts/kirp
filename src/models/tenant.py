"""
Tenant & Space models — Multi-tenant hierarchy.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class SpaceKind(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    TEAM = "team"
    ORG = "org"


class Tenant(Base):
    """Root organization tenant."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    extra = Column(JSON, default=dict)  # metadata reserved by SQLAlchemy
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    spaces = relationship("Space", back_populates="tenant", cascade="all, delete-orphan")


class Space(Base):
    """Tenant space: private, shared, team, or org."""

    __tablename__ = "spaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    kind = Column(String(50), nullable=False)  # SpaceKind
    name = Column(String(255), nullable=False)
    owner_id = Column(String(255), nullable=True)
    extra = Column(JSON, default=dict)  # metadata reserved by SQLAlchemy
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="spaces")
