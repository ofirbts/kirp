"""
Agent Actions — Unified action model for agent outputs.

Action types: create_task, update_task, create_commitment, send_notification,
send_message, update_project, suggest_focus, suggest_reschedule.
ExecutionAgent consumes pending actions and executes them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Action types (executable or suggestions)
ACTION_CREATE_TASK = "create_task"
ACTION_UPDATE_TASK = "update_task"
ACTION_CREATE_COMMITMENT = "create_commitment"
ACTION_SEND_NOTIFICATION = "send_notification"
ACTION_SEND_MESSAGE = "send_message"
ACTION_UPDATE_PROJECT = "update_project"
ACTION_SUGGEST_FOCUS = "suggest_focus"
ACTION_SUGGEST_RESCHEDULE = "suggest_reschedule"

ACTION_TYPES = [
    ACTION_CREATE_TASK,
    ACTION_UPDATE_TASK,
    ACTION_CREATE_COMMITMENT,
    ACTION_SEND_NOTIFICATION,
    ACTION_SEND_MESSAGE,
    ACTION_UPDATE_PROJECT,
    ACTION_SUGGEST_FOCUS,
    ACTION_SUGGEST_RESCHEDULE,
]


class ActionStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def action_doc(
    agent: str,
    action_type: str,
    payload: dict[str, Any],
    tenant_id: str,
    space_id: str = "all",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Build a new action document for storage."""
    return {
        "id": str(uuid4()),
        "agent": agent,
        "type": action_type,
        "payload": payload,
        "status": ActionStatus.PENDING.value,
        "tenant_id": tenant_id,
        "space_id": space_id,
        "user_id": user_id or "system",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "executed_at": None,
        "error": None,
    }


class AgentActionsStore:
    """MongoDB store for agent actions. ExecutionAgent consumes pending actions."""

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
            # Index: status + tenant_id for efficient queries
            await self._db.agent_actions.create_index([("tenant_id", 1), ("status", 1), ("created_at", -1)])
            logger.info("AgentActionsStore connected to MongoDB")
        except Exception as e:
            logger.error("AgentActionsStore connect failed: %s", e)
            raise

    @property
    def _coll(self) -> Any:
        if self._db is None:
            raise RuntimeError("AgentActionsStore not connected; call connect() first")
        return self._db.agent_actions

    async def create(self, doc: dict[str, Any]) -> str:
        """Insert one action. Returns action id."""
        await self.connect()
        await self._coll.insert_one(doc)
        return doc["id"]

    async def create_many(self, docs: list[dict[str, Any]]) -> list[str]:
        """Insert many actions. Returns list of ids."""
        if not docs:
            return []
        await self.connect()
        await self._coll.insert_many(docs)
        return [d["id"] for d in docs]

    async def list_(
        self,
        tenant_id: str,
        status: str | None = None,
        agent: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """List actions, optionally filtered by status and agent."""
        await self.connect()
        q: dict[str, Any] = {"tenant_id": tenant_id}
        if status:
            q["status"] = status
        if agent:
            q["agent"] = agent
        cursor = self._coll.find(q).sort("created_at", -1).limit(limit)
        out = await cursor.to_list(length=limit)
        for d in out:
            if "_id" in d:
                d["_id"] = str(d["_id"])
        return out

    async def get_pending(self, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get pending actions for execution."""
        return await self.list_(tenant_id=tenant_id, status=ActionStatus.PENDING.value, limit=limit)

    async def mark_executed(self, action_id: str) -> bool:
        """Mark action as executed."""
        await self.connect()
        from datetime import datetime, timezone
        r = await self._coll.update_one(
            {"id": action_id},
            {"$set": {"status": ActionStatus.EXECUTED.value, "executed_at": datetime.now(timezone.utc).isoformat(), "error": None}},
        )
        return r.modified_count > 0

    async def mark_failed(self, action_id: str, error: str) -> bool:
        """Mark action as failed."""
        await self.connect()
        from datetime import datetime, timezone
        r = await self._coll.update_one(
            {"id": action_id},
            {"$set": {"status": ActionStatus.FAILED.value, "executed_at": datetime.now(timezone.utc).isoformat(), "error": error}},
        )
        return r.modified_count > 0


_actions_store: AgentActionsStore | None = None


def get_agent_actions_store(mongo_uri: str | None = None) -> AgentActionsStore:
    global _actions_store
    if _actions_store is None:
        import os
        _actions_store = AgentActionsStore(mongo_uri or os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    return _actions_store
