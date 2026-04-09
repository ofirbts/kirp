"""
History 2.0 — Human-readable timeline entries (life activity, not raw event log).

Types: email_received, whatsapp_message, slack_message, task_created, task_completed,
commitment_created, commitment_due, project_updated, agent_insight, agent_action,
notion_sync, calendar_event, system.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

HISTORY_TYPES = (
    "email_received",
    "whatsapp_message",
    "slack_message",
    "task_created",
    "task_completed",
    "task_updated",
    "commitment_created",
    "commitment_due",
    "project_updated",
    "agent_insight",
    "agent_action",
    "notion_sync",
    "calendar_event",
    "system",
)


@dataclass
class HistoryEntry:
    id: str
    tenant_id: str
    space_id: str
    user_id: str
    type: str
    title: str
    body: str
    entity_id: str | None
    source: str
    created_at: datetime
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
            "source": self.source,
            "created_at": self.created_at,
            "meta": self.meta or {},
        }

    def to_json(self) -> dict[str, Any]:
        d = self.to_doc()
        d["created_at"] = self.created_at.isoformat() if self.created_at else None
        return d

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "HistoryEntry":
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
            type=doc.get("type", "system"),
            title=doc.get("title", ""),
            body=doc.get("body", ""),
            entity_id=doc.get("entity_id"),
            source=doc.get("source", "api"),
            created_at=ct,
            meta=doc.get("meta") or {},
        )


class HistoryStore:
    """MongoDB store for history entries. Collection: history."""

    def __init__(
        self,
        mongo_uri: str,
        db_name: str = "kirp",
        *,
        connect_max_attempts: int = 5,
        connect_base_delay_sec: float = 0.5,
        server_selection_timeout_ms: int = 5000,
    ) -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._connect_max_attempts = max(1, connect_max_attempts)
        self._connect_base_delay_sec = connect_base_delay_sec
        self._server_selection_timeout_ms = server_selection_timeout_ms
        self._client: Any = None
        self._db: Any = None

    async def health_check(self) -> bool:
        """Return True if MongoDB responds to ping."""
        if self._db is None:
            return False
        try:
            await self._db.command("ping")
            return True
        except Exception as e:
            logger.warning("HistoryStore health_check failed: %s", e)
            return False

    async def connect(self) -> None:
        if self._db is not None:
            if await self.health_check():
                return
            self._reset_connection()

        last_err: Exception | None = None
        for attempt in range(1, self._connect_max_attempts + 1):
            try:
                from motor.motor_asyncio import AsyncIOMotorClient

                self._client = AsyncIOMotorClient(
                    self._mongo_uri,
                    serverSelectionTimeoutMS=self._server_selection_timeout_ms,
                )
                self._db = self._client[self._db_name]
                await self._db.command("ping")
                await self._db.history.create_index(
                    [("tenant_id", 1), ("user_id", 1), ("created_at", -1)]
                )
                logger.info("HistoryStore connected to MongoDB (attempt %s)", attempt)
                return
            except Exception as e:
                last_err = e
                self._reset_connection()
                logger.warning(
                    "HistoryStore connect attempt %s/%s failed: %s",
                    attempt,
                    self._connect_max_attempts,
                    e,
                )
                if attempt < self._connect_max_attempts:
                    await asyncio.sleep(self._connect_base_delay_sec * attempt)
        logger.error("HistoryStore connect exhausted retries: %s", last_err)
        if last_err is not None:
            raise last_err
        raise RuntimeError("HistoryStore connect failed with no exception detail")

    def _reset_connection(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._db = None

    @property
    def _coll(self) -> Any:
        if self._db is None:
            raise RuntimeError("HistoryStore not connected; call connect() first")
        return self._db.history

    async def record(self, entry: HistoryEntry) -> str:
        await self.connect()
        doc = entry.to_doc()
        doc["created_at"] = entry.created_at
        await self._coll.insert_one(doc)
        return entry.id

    async def list_(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 100,
        type_filter: str | None = None,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
    ) -> list[HistoryEntry]:
        await self.connect()
        q: dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
        if type_filter:
            q["type"] = type_filter
        if from_ts is not None:
            q.setdefault("created_at", {})["$gte"] = from_ts
        if to_ts is not None:
            q.setdefault("created_at", {})["$lt"] = to_ts
        cursor = self._coll.find(q).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [HistoryEntry.from_doc(d) for d in docs]

    async def list_by_date_range(
        self,
        tenant_id: str,
        user_id: str,
        from_ts: datetime,
        to_ts: datetime,
        limit: int = 500,
    ) -> list[HistoryEntry]:
        return await self.list_(tenant_id, user_id, limit=limit, from_ts=from_ts, to_ts=to_ts)

    async def list_by_type(
        self,
        tenant_id: str,
        user_id: str,
        type_: str,
        limit: int = 100,
    ) -> list[HistoryEntry]:
        return await self.list_(tenant_id, user_id, limit=limit, type_filter=type_)


_store: HistoryStore | None = None


def get_history_store(mongo_uri: str | None = None) -> HistoryStore:
    global _store
    if _store is None:
        import os
        _store = HistoryStore(mongo_uri or os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    return _store


def make_history_entry(
    tenant_id: str,
    space_id: str,
    user_id: str,
    type_: str,
    title: str,
    body: str,
    source: str = "api",
    entity_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> HistoryEntry:
    return HistoryEntry(
        id=str(uuid4()),
        tenant_id=tenant_id,
        space_id=space_id or "all",
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        entity_id=entity_id,
        source=source,
        created_at=datetime.now(timezone.utc),
        meta=meta or {},
    )


async def record_history(
    tenant_id: str,
    space_id: str,
    user_id: str,
    type_: str,
    title: str,
    body: str,
    source: str = "api",
    entity_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    """Create and persist a history entry. Returns entry id."""
    entry = make_history_entry(
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        type_=type_,
        title=title,
        body=body,
        source=source,
        entity_id=entity_id,
        meta=meta,
    )
    store = get_history_store()
    await store.connect()
    return await store.record(entry)
