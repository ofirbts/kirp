"""
SpaceMembership — User membership in spaces with optional role.

Used for visibility: private / shared / tenant / space.
tenant_id and space_id are strings (e.g. "default", "all", or UUID as string) to align with API/events.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSON

from src.models.base import Base


class SpaceMembership(Base):
    """User membership in a space (tenant_id + space_id) with optional role."""

    __tablename__ = "space_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    space_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    role = Column(String(100), nullable=True)  # e.g. owner, member, viewer
    extra = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("tenant_id", "space_id", "user_id", name="uq_space_membership_tenant_space_user"),
        Index("ix_space_memberships_tenant_user", "tenant_id", "user_id"),
    )
