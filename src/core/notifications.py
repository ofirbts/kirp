"""
Notifications — Persistent notification model and store for Activity Center.

Types: task_created, task_updated, commitment_due, commitment_overdue, reminder,
insight_generated, agent_action, sync_error, connection_issue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = (
    "task_created",
    "task_updated",
    "commitment_due",
    "commitment_overdue",
    "reminder",
    "insight_generated",
    "agent_action",
    "sync_error",
    "connection_issue",
)


@dataclass
class Notification:
    id: str
    tenant_id: str
    space_id: str
    user_id: str
    type: str
    title: str
    body: str
    entity_id: str | None
    created_at: datetime
    read: bool
    meta: dict[str, Any]

    def to_doc(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "space_id": self.space_id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "read": self.read,
            "meta": self.meta or {},
        }

    def to_json(self) -> dict[str, Any]:
        d = self.to_doc()
        d["created_at"] = self.created_at.isoformat() if self.created_at else None
        return d

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "Notification":
        ct = doc.get("created_at")
        if isinstance(ct, str):
            try:
                ct = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            except Exception:
                ct = datetime.now(timezone.utc)
        elif ct is None:
            ct = datetime.now(timezone.utc)
        return cls(
            id=doc.get("id", ""),
            tenant_id=doc.get("tenant_id", ""),
            space_id=doc.get("space_id", ""),
            user_id=doc.get("user_id", ""),
            type=doc.get("type", "reminder"),
            title=doc.get("title", ""),
            body=doc.get("body", ""),
            entity_id=doc.get("entity_id"),
            created_at=ct,
            read=bool(doc.get("read", False)),
            meta=doc.get("meta") or {},
        )


class NotificationStore:
    """MongoDB store for notifications. Collection: notifications."""

    def __init__(self, mongo_uri: str, db_name: str = "kirp") -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._client: Any = None
        self._db: Any = None

    async def connect(self) -> None:
        if self._db is not None:
            return
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._client = AsyncIOMotorClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            await self._db.command("ping")
            # Ensure common indexes for performance
            await self._db.notifications.create_index([("tenant_id", 1), ("user_id", 1), ("read", 1), ("created_at", -1)])
            logger.info("NotificationStore connected to MongoDB")
        except Exception as e:
            logger.error("NotificationStore connect failed: %s", e)
            raise

    @property
    def _coll(self) -> Any:
        if self._db is None:
            raise RuntimeError("NotificationStore not connected; call connect() first")
        return self._db.notifications

    async def create(self, notification: Notification) -> str:
        await self.connect()
        doc = notification.to_doc()
        doc["created_at"] = notification.created_at
        await self._coll.insert_one(doc)
        return notification.id

    async def list_unread(self, tenant_id: str, user_id: str, limit: int = 100) -> list[Notification]:
        await self.connect()
        cursor = self._coll.find({"tenant_id": tenant_id, "user_id": user_id, "read": False}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Notification.from_doc(d) for d in docs]

    async def list_all(self, tenant_id: str, user_id: str, limit: int = 100, type_filter: str | None = None) -> list[Notification]:
        await self.connect()
        q: dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
        if type_filter:
            q["type"] = type_filter
        cursor = self._coll.find(q).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Notification.from_doc(d) for d in docs]

    async def mark_read(self, notification_id: str) -> bool:
        await self.connect()
        from datetime import datetime, timezone
        r = await self._coll.update_one({"id": notification_id}, {"$set": {"read": True}})
        return r.modified_count > 0

    async def mark_all_read(self, tenant_id: str, user_id: str) -> int:
        await self.connect()
        r = await self._coll.update_many({"tenant_id": tenant_id, "user_id": user_id, "read": False}, {"$set": {"read": True}})
        return r.modified_count

    async def unread_count(self, tenant_id: str, user_id: str) -> int:
        await self.connect()
        return await self._coll.count_documents({"tenant_id": tenant_id, "user_id": user_id, "read": False})


_store: NotificationStore | None = None


def get_notification_store(mongo_uri: str | None = None) -> NotificationStore:
    global _store
    if _store is None:
        import os
        _store = NotificationStore(mongo_uri or os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    return _store


async def notify_user(
    tenant_id: str,
    user_id: str,
    type: str,
    title: str,
    body: str,
    space_id: str = "all",
    entity_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    """Create notification, persist, and push via WebSocket. Returns notification id."""
    n = make_notification(tenant_id, user_id, type, title, body, space_id, entity_id, meta)
    store = get_notification_store()
    await store.connect()
    await store.create(n)
    try:
        from src.api.ws_notifications import push_notification_to_user
        count = await store.unread_count(tenant_id, user_id)
        await push_notification_to_user(tenant_id, user_id, n.to_json(), count)
    except Exception as e:
        logger.warning("notify_user push failed: %s", e)
    return n.id


def make_notification(
    tenant_id: str,
    user_id: str,
    type: str,
    title: str,
    body: str,
    space_id: str = "all",
    entity_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> Notification:
    return Notification(
        id=str(uuid4()),
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        entity_id=entity_id,
        created_at=datetime.now(timezone.utc),
        read=False,
        meta=meta or {},
    )
