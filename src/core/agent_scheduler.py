"""
Agent Scheduler — Time-based and event-based triggers, queue agent runs, store logs in MongoDB.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# MongoDB collection: agent_logs
# Document: { agent_name, run_at (ISO), duration_ms, result_count, errors (list), tenant_id, space_id, trigger }


class AgentLogsStore:
    """Store agent run logs in MongoDB."""

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
        except Exception as e:
            logger.error("AgentLogsStore connect failed: %s", e)
            raise

    @property
    def _coll(self) -> Any:
        if self._db is None:
            raise RuntimeError("AgentLogsStore not connected; call connect() first")
        return self._db.agent_logs

    async def append(self, agent_name: str, run_at: str, duration_ms: float, result_count: int, errors: list[str], tenant_id: str, space_id: str, trigger: str) -> None:
        await self.connect()
        await self._coll.insert_one({
            "agent_name": agent_name,
            "run_at": run_at,
            "duration_ms": duration_ms,
            "result_count": result_count,
            "errors": errors,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "trigger": trigger,
        })

    async def list_(self, tenant_id: str | None = None, agent_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        await self.connect()
        q: dict[str, Any] = {}
        if tenant_id:
            q["tenant_id"] = tenant_id
        if agent_name:
            q["agent_name"] = agent_name
        cursor = self._coll.find(q).sort("run_at", -1).limit(limit)
        out = await cursor.to_list(length=limit)
        for d in out:
            if "_id" in d:
                d["_id"] = str(d["_id"])
        return out


_logs_store: AgentLogsStore | None = None


def get_agent_logs_store(mongo_uri: str | None = None) -> AgentLogsStore:
    global _logs_store
    if _logs_store is None:
        import os
        _logs_store = AgentLogsStore(mongo_uri or os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    return _logs_store


class AgentScheduler:
    """Time-based triggers (every X minutes), event-based stub. Queues runs and logs results."""

    def __init__(self, agent_framework: Any, agent_engine: Any) -> None:
        self._framework = agent_framework
        self._engine = agent_engine
        self._logs = get_agent_logs_store()
        self._interval_minutes = 15
        self._running = False

    def set_interval_minutes(self, minutes: int) -> None:
        self._interval_minutes = max(1, minutes)

    async def run_agent_and_log(
        self,
        agent_name: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
        trigger: str,
        initial_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run one agent and append log to MongoDB. initial_context is merged with trigger (e.g. rag_response)."""
        started = time.perf_counter()
        result_count = 0
        errors: list[str] = []
        context = {**(initial_context or {}), "trigger": trigger}
        try:
            result = await self._framework.run(agent_name, tenant_id, space_id, user_id, context)
            if result.get("ok"):
                result_count = len(result.get("actions", [])) + len(result.get("insights", []))
            else:
                errors.append(result.get("error", "unknown"))
        except Exception as e:
            errors.append(str(e))
            result = {"ok": False, "error": str(e)}
        duration_ms = (time.perf_counter() - started) * 1000
        run_at = datetime.now(timezone.utc).isoformat()
        await self._logs.append(agent_name, run_at, duration_ms, result_count, errors, tenant_id, space_id, trigger)
        return result

    async def time_loop(self, tenant_id: str = "default", space_id: str = "all", user_id: str = "system") -> None:
        """Background loop: every _interval_minutes run scheduled agents."""
        self._running = True
        while self._running:
            for spec in self._framework.list_all():
                if "scheduled" not in (spec.triggers or []):
                    continue
                try:
                    await self.run_agent_and_log(spec.name, tenant_id, space_id, user_id, "scheduled")
                except Exception as e:
                    logger.warning("Scheduler run %s failed: %s", spec.name, e)
            await asyncio.sleep(self._interval_minutes * 60)

    def stop(self) -> None:
        self._running = False
