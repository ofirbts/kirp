"""
Event & Audit models — Event-sourced audit trail.

Canonical Event model (EVENTS.md): base fields + ingest.v1 | agent_run.v1 payloads.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from src.models.base import Base


# --- Canonical Event (EVENTS.md) ---

EVENT_TYPE_INGEST = "ingest.v1"
EVENT_TYPE_AGENT_RUN = "agent_run.v1"
@dataclass
class CanonicalEvent:
    """
    Canonical event model per docs/EVENTS.md.
    Base fields (mandatory): tenant_id, space_id, user_id, source, trace_id, parent_event_id, version.
    Type-specific: ingest.v1 → content; agent_run.v1 → agent_id, input.
    """

    tenant_id: str
    space_id: str
    user_id: str
    source: str
    trace_id: str | None = None
    parent_event_id: UUID | None = None
    version: int = 1

    event_type: str = EVENT_TYPE_INGEST
    id: UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ingest.v1
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # agent_run.v1
    agent_id: str | None = None
    input: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Serialize for Kafka/HTTP (JSON-safe)."""
        payload: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "space_id": self.space_id,
            "user_id": self.user_id,
            "source": self.source,
            "trace_id": self.trace_id,
            "parent_event_id": str(self.parent_event_id) if self.parent_event_id else None,
            "version": self.version,
            "event_type": self.event_type,
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
        if self.event_type == EVENT_TYPE_INGEST:
            payload["content"] = self.content
            payload["metadata"] = self.metadata
        elif self.event_type == EVENT_TYPE_AGENT_RUN:
            payload["agent_id"] = self.agent_id
            payload["input"] = self.input
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> CanonicalEvent:
        """Deserialize from Kafka/HTTP payload. Uses values exactly as provided; no fallbacks."""
        event_type = data.get("event_type", EVENT_TYPE_INGEST)
        parent = data.get("parent_event_id")
        ev_id = data.get("id")
        ts = data.get("timestamp")
        tenant_id = data.get("tenant_id")
        space_id = data.get("space_id")
        user_id = data.get("user_id")
        if not tenant_id or tenant_id == "*":
            raise ValueError("tenant_id is required and must not be '*'")
        if not user_id:
            raise ValueError("user_id is required")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = datetime.now(timezone.utc)
        elif ts is None:
            ts = datetime.now(timezone.utc)
        return cls(
            tenant_id=tenant_id,
            space_id=space_id if space_id else "all",
            user_id=user_id,
            source=data.get("source", ""),
            trace_id=data.get("trace_id"),
            parent_event_id=UUID(parent) if isinstance(parent, str) and parent else None,
            version=int(data.get("version", 1)),
            event_type=event_type,
            id=UUID(ev_id) if ev_id else uuid.uuid4(),
            timestamp=ts,
            content=data.get("content", ""),
            metadata=data.get("metadata") or {},
            agent_id=data.get("agent_id"),
            input=data.get("input") or {},
        )


# --- SQLAlchemy models ---


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
