"""
Connector sync log — Last sync time, status, and last 10 errors per (tenant_id, user_id, integration).

Used by Connections Hub UI for status indicators and error logs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

MAX_ERROR_LOGS = 10


class ConnectorSyncLogStore:
    """Store last sync result and last N errors per connector."""

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
            logger.info("ConnectorSyncLogStore connected")
        except Exception as e:
            logger.error("ConnectorSyncLogStore connection failed: %s", e)
            raise

    def _coll(self):
        if self._db is None:
            raise RuntimeError("ConnectorSyncLogStore not connected")
        return self._db.connector_sync_log

    async def record_sync(
        self,
        tenant_id: str,
        user_id: str,
        integration: str,
        status: str,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        """Record a sync run. status: ok | error."""
        now = datetime.now(timezone.utc)
        upd: dict[str, Any] = {
            "$set": {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "integration": integration,
                "last_sync_at": now.isoformat(),
                "last_sync_status": status,
                "last_sync_result": result or {},
            },
        }
        if error_message:
            upd["$push"] = {
                "error_log": {
                    "$each": [{"at": now.isoformat(), "message": error_message}],
                    "$position": 0,
                    "$slice": MAX_ERROR_LOGS,
                },
            }
        await self._coll().update_one(
            {"tenant_id": tenant_id, "user_id": user_id, "integration": integration},
            upd,
            upsert=True,
        )

    async def get_status(
        self,
        tenant_id: str,
        user_id: str,
        integration: str,
    ) -> dict[str, Any] | None:
        """Get last sync at, status, result, and error_log (last 10)."""
        doc = await self._coll().find_one({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "integration": integration,
        })
        if not doc:
            return None
        return {
            "last_sync_at": doc.get("last_sync_at"),
            "last_sync_status": doc.get("last_sync_status", "unknown"),
            "last_sync_result": doc.get("last_sync_result") or {},
            "error_log": doc.get("error_log") or [],
        }

    async def get_errors(
        self,
        tenant_id: str,
        user_id: str,
        integration: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get last N error log entries."""
        status = await self.get_status(tenant_id, user_id, integration)
        if not status:
            return []
        return (status.get("error_log") or [])[:limit]
