"""
Pending executions — Optional approval workflow for autonomous actions.

Commands submitted with require_approval=True are stored here until approved/rejected.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PendingExecutionsStore:
    """MongoDB collection pending_executions: list, add, get, approve, reject."""

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
        except Exception as e:
            logger.error("PendingExecutionsStore connection failed: %s", e)
            raise

    def _coll(self):
        if self._db is None:
            raise RuntimeError("PendingExecutionsStore not connected")
        return self._db.pending_executions

    async def add(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        command_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Insert pending command. Returns pending_id."""
        from uuid import uuid4
        pending_id = str(uuid4())
        await self._coll().insert_one({
            "_id": pending_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "space_id": space_id,
            "command_type": command_type,
            "payload": payload,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        })
        return pending_id

    async def get(self, pending_id: str) -> dict[str, Any] | None:
        doc = await self._coll().find_one({"_id": pending_id})
        if not doc:
            return None
        return {
            "id": doc["_id"],
            "tenant_id": doc["tenant_id"],
            "user_id": doc["user_id"],
            "space_id": doc["space_id"],
            "command_type": doc["command_type"],
            "payload": doc["payload"],
            "status": doc["status"],
            "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
        }

    async def list_pending(self, tenant_id: str, user_id: str | None = None) -> list[dict[str, Any]]:
        q: dict[str, Any] = {"tenant_id": tenant_id, "status": "pending"}
        if user_id:
            q["user_id"] = user_id
        cursor = self._coll().find(q).sort("created_at", -1).limit(100)
        docs = await cursor.to_list(length=100)
        return [
            {
                "id": d["_id"],
                "tenant_id": d["tenant_id"],
                "user_id": d["user_id"],
                "space_id": d["space_id"],
                "command_type": d["command_type"],
                "payload": d["payload"],
                "created_at": d["created_at"].isoformat() if d.get("created_at") else None,
            }
            for d in docs
        ]

    async def set_status(self, pending_id: str, status: str, executed_result: dict[str, Any] | None = None) -> bool:
        """Set status to approved, rejected, or executed. Returns True if updated."""
        update: dict[str, Any] = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if executed_result is not None:
            update["executed_result"] = executed_result
        r = await self._coll().update_one({"_id": pending_id}, {"$set": update})
        return r.modified_count > 0
