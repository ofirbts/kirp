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

    def to_doc(self) -> dict[str, Any]:
        """Serialize for MongoDB (datetime kept as-is for BSON)."""
        return {
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
        }

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

    async def list(
        self,
        tenant_id: str,
        space_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[Event]:
        """List events with tenant/space/user scoping. Use tenant_id='*' for all tenants."""
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
        cursor = self._db.events.find(q).sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Event.from_doc(d) for d in docs]

    async def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
