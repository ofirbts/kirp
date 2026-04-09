"""
Event Store — MongoDB-backed, event-sourced source of truth.

Flow: Ingest → Store raw in Mongo → Generate embedding → Qdrant → Metadata → Postgres
      → Publish to Kafka/Redis → Trigger agents → Governance → Execute → Emit new event.

No state mutation without event. Every decision auditable, explainable, replayable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class Sensitivity(str, Enum):
    """Tenant isolation: no cross-tenant access unless explicitly granted."""

    PRIVATE = "private"       # Owner only
    SHARED = "shared"         # Explicit permissions
    CONFIDENTIAL = "confidential"  # RBAC + ABAC + policies


@dataclass
class Event:
    """
    Canonical event model. Multi-tenant; stored in MongoDB.
    Embedding may be empty at ingest; filled before Qdrant upsert.
    Causality: parent_event_id; correlation_id for request tracing.
    """

    id: UUID
    tenant_id: str
    space_id: str
    user_id: str
    source: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sensitivity: Sensitivity = Sensitivity.PRIVATE
    event_type: str = "ingest"
    trace_id: str | None = None
    correlation_id: str | None = None
    parent_event_id: UUID | None = None
    actor: str | None = None
    version: str = "1.0"

    def to_doc(self) -> dict[str, Any]:
        """Serialize for MongoDB (datetime kept as-is for BSON)."""
        doc: dict[str, Any] = {
            "_id": str(self.id),
            "tenant_id": self.tenant_id,
            "space_id": self.space_id,
            "user_id": self.user_id,
            "source": self.source,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "timestamp": self.timestamp,
            "sensitivity": self.sensitivity.value,
            "event_type": self.event_type,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "parent_event_id": str(self.parent_event_id) if self.parent_event_id else None,
            "actor": self.actor,
            "version": self.version,
        }
        return doc

    def to_json_payload(self) -> dict[str, Any]:
        """Serialize for JSON (Kafka, HTTP). Datetime -> isoformat."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "space_id": self.space_id,
            "user_id": self.user_id,
            "source": self.source,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "sensitivity": self.sensitivity.value,
            "event_type": self.event_type,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "parent_event_id": str(self.parent_event_id) if self.parent_event_id else None,
            "actor": self.actor,
            "version": self.version,
        }

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> Event:
        """Deserialize from MongoDB."""
        ts = doc.get("timestamp")
        if ts is None or (isinstance(ts, str) and not ts):
            ts = datetime.now(timezone.utc)
        elif isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = datetime.now(timezone.utc)
        return cls(
            id=UUID(doc["_id"]),
            tenant_id=doc["tenant_id"],
            space_id=doc["space_id"],
            user_id=doc["user_id"],
            source=doc["source"],
            content=doc["content"],
            metadata=doc.get("metadata", {}),
            embedding=doc.get("embedding", []),
            timestamp=ts,
            sensitivity=Sensitivity(doc.get("sensitivity", "private")),
            event_type=doc.get("event_type", "ingest"),
            trace_id=doc.get("trace_id"),
            correlation_id=doc.get("correlation_id"),
            parent_event_id=UUID(doc["parent_event_id"]) if doc.get("parent_event_id") else None,
            actor=doc.get("actor"),
            version=doc.get("version", "1.0"),
        )


class EventStore:
    """
    MongoDB event store. Single source of truth for all events.
    """

    def __init__(self, mongo_uri: str, db_name: str = "kirp") -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._client: Any = None
        self._db: Any = None

    async def connect(self) -> None:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._client = AsyncIOMotorClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            await self._db.command("ping")
            logger.info("EventStore connected to MongoDB")
        except Exception as e:
            logger.error("EventStore connection failed: %s", e)
            raise

    async def ingest(self, event: Event) -> UUID:
        """Store raw event in Mongo. No silent mutation."""
        if self._db is None:
            await self.connect()
        await self._db.events.insert_one(event.to_doc())
        logger.info("Event stored: %s tenant=%s space=%s", event.id, event.tenant_id, event.space_id)
        return event.id

    async def get_by_id(self, event_id: UUID) -> Event | None:
        """Fetch single event by ID."""
        if self._db is None:
            await self.connect()
        doc = await self._db.events.find_one({"_id": str(event_id)})
        return Event.from_doc(doc) if doc else None

    async def find_latest_by_run_id(self, tenant_id: str, run_id: str) -> Event | None:
        """Latest event whose metadata contains this ingest `run_id` (tenant-scoped)."""
        if not tenant_id or not run_id:
            raise ValueError("tenant_id and run_id are required")
        if self._db is None:
            await self.connect()
        doc = await self._db.events.find_one(
            {"tenant_id": tenant_id, "metadata.run_id": run_id},
            sort=[("timestamp", -1)],
        )
        return Event.from_doc(doc) if doc else None

    async def find_by_external_id(
        self,
        tenant_id: str,
        source: str,
        external_id: str,
    ) -> Event | None:
        """Find an event by tenant, source, and external_id (idempotency key). Returns None if not found."""
        if self._db is None:
            await self.connect()
        doc = await self._db.events.find_one({
            "tenant_id": tenant_id,
            "source": source,
            "metadata.external_id": external_id,
        })
        return Event.from_doc(doc) if doc else None

    async def update_by_external_id(
        self,
        tenant_id: str,
        source: str,
        external_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update an existing event's content and metadata by external_id (e.g. Notion page_id).
        Used by bi-directional sync when Notion webhook reports a page change.
        Returns True if a document was updated.
        """
        if self._db is None:
            await self.connect()
        update: dict[str, Any] = {"$set": {"content": content, "timestamp": datetime.now(timezone.utc)}}
        if metadata is not None:
            update["$set"]["metadata"] = metadata
        res = await self._db.events.update_one(
            {
                "tenant_id": tenant_id,
                "source": source,
                "metadata.external_id": external_id,
            },
            update,
        )
        if res.modified_count:
            logger.info("EventStore updated by external_id: %s source=%s", external_id, source)
        return res.modified_count > 0

    async def list(
        self,
        tenant_id: str,
        space_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        since: datetime | None = None,
        allow_all_tenants: bool = False,
        agent_id: str | None = None,
        correlation_id: str | None = None,
    ) -> list[Event]:
        """
        List events with tenant/space/user scoping and optional partition (agent_id, correlation_id).
        """
        if not tenant_id or (tenant_id == "*" and not allow_all_tenants):
            if tenant_id == "*":
                raise ValueError("tenant_id='*' not allowed (multi-tenant isolation). Use allow_all_tenants=True for admin operations.")
            raise ValueError("tenant_id is required (multi-tenant isolation)")
        if self._db is None:
            await self.connect()
        q: dict[str, Any] = {}
        if tenant_id != "*":
            q["tenant_id"] = tenant_id
        if space_id:
            q["space_id"] = space_id
        if user_id:
            q["user_id"] = user_id
        if since:
            q["timestamp"] = {"$gte": since}
        if agent_id:
            q["metadata.agent_id"] = agent_id
        if correlation_id:
            q["correlation_id"] = correlation_id
        cursor = self._db.events.find(q).sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Event.from_doc(d) for d in docs]

    async def replay(self, event_id: UUID) -> dict[str, Any]:
        """Replay: fetch event and return JSON payload for re-ingest (e.g. Kafka). No mutation."""
        ev = await self.get_by_id(event_id)
        if not ev:
            raise ValueError(f"Event not found: {event_id}")
        return ev.to_json_payload()

    async def move_to_dlq(self, event_id: UUID, reason: str) -> None:
        """Move event to dead-letter queue (append to dlq_events collection)."""
        if self._db is None:
            await self.connect()
        doc = await self._db.events.find_one({"_id": str(event_id)})
        if not doc:
            raise ValueError(f"Event not found: {event_id}")
        doc["dlq_reason"] = reason
        doc["dlq_at"] = datetime.now(timezone.utc)
        await self._db.dlq_events.insert_one(doc)
        logger.info("Event %s moved to DLQ: %s", event_id, reason)

    async def list_dlq(
        self,
        tenant_id: str,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[Event]:
        """List events in DLQ (tenant-scoped)."""
        if self._db is None:
            await self.connect()
        q: dict[str, Any] = {"tenant_id": tenant_id}
        if since:
            q["dlq_at"] = {"$gte": since}
        cursor = self._db.dlq_events.find(q).sort("dlq_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Event.from_doc(d) for d in docs]

    async def retry_dlq(self, event_id: UUID) -> dict[str, Any]:
        """Return DLQ event payload for retry (caller re-ingests). Removes from DLQ on success if desired."""
        if self._db is None:
            await self.connect()
        doc = await self._db.dlq_events.find_one({"_id": str(event_id)})
        if not doc:
            raise ValueError(f"DLQ event not found: {event_id}")
        ev = Event.from_doc(doc)
        return ev.to_json_payload()

    async def delete_older_than(self, tenant_id: str, before: datetime) -> int:
        """Retention: delete events older than `before` for tenant. Returns deleted count."""
        if self._db is None:
            await self.connect()
        r = await self._db.events.delete_many({"tenant_id": tenant_id, "timestamp": {"$lt": before}})
        return r.deleted_count

    async def count_events(
        self,
        tenant_id: str | None = None,
        space_id: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """Count events, optionally filtered by tenant, space, and time."""
        if self._db is None:
            await self.connect()
        q: dict[str, Any] = {}
        if tenant_id:
            q["tenant_id"] = tenant_id
        if space_id:
            q["space_id"] = space_id
        if since:
            q["timestamp"] = {"$gte": since}
        return await self._db.events.count_documents(q)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
