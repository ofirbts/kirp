"""
Reminder preferences — per user: lead time, channels, quiet hours.

Stored in MongoDB collection reminder_preferences.
Used by ReminderAgent to decide when and how to send reminders.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, time, timezone
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LEAD_HOURS = 24
DEFAULT_CHANNELS = ["email"]
VALID_CHANNELS = ("whatsapp", "email", "notification")


class ReminderPreferencesStore:
    """CRUD for reminder preferences per (tenant_id, user_id)."""

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
            logger.info("ReminderPreferencesStore connected")
        except Exception as e:
            logger.error("ReminderPreferencesStore connection failed: %s", e)
            raise

    def _coll(self):
        if self._db is None:
            raise RuntimeError("ReminderPreferencesStore not connected")
        return self._db.reminder_preferences

    async def get(
        self,
        tenant_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Get preferences. Returns dict: lead_hours, channels, quiet_start, quiet_end, whatsapp_to?, email_to?.
        Defaults: lead_hours=24, channels=["email"].
        """
        doc = await self._coll().find_one({"tenant_id": tenant_id, "user_id": user_id})
        if not doc:
            return {
                "lead_hours": DEFAULT_LEAD_HOURS,
                "channels": list(DEFAULT_CHANNELS),
                "quiet_start": None,
                "quiet_end": None,
                "whatsapp_to": None,
                "email_to": None,
            }
        return {
            "lead_hours": doc.get("lead_hours", DEFAULT_LEAD_HOURS),
            "channels": doc.get("channels", list(DEFAULT_CHANNELS)),
            "quiet_start": doc.get("quiet_start"),
            "quiet_end": doc.get("quiet_end"),
            "whatsapp_to": doc.get("whatsapp_to"),
            "email_to": doc.get("email_to"),
        }

    async def set(
        self,
        tenant_id: str,
        user_id: str,
        lead_hours: int | None = None,
        channels: list[str] | None = None,
        quiet_start: str | None = None,
        quiet_end: str | None = None,
        whatsapp_to: str | None = None,
        email_to: str | None = None,
    ) -> None:
        """Upsert preferences. Times as "HH:MM" (24h)."""
        update: dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
        if lead_hours is not None:
            update["lead_hours"] = lead_hours
        if channels is not None:
            update["channels"] = [c for c in channels if c in VALID_CHANNELS] or list(DEFAULT_CHANNELS)
        if quiet_start is not None:
            update["quiet_start"] = quiet_start
        if quiet_end is not None:
            update["quiet_end"] = quiet_end
        if whatsapp_to is not None:
            update["whatsapp_to"] = whatsapp_to
        if email_to is not None:
            update["email_to"] = email_to
        await self._coll().update_one(
            {"tenant_id": tenant_id, "user_id": user_id},
            {"$set": update},
            upsert=True,
        )


class ReminderSentStore:
    """Track sent reminders to avoid duplicates: (node_id, slot, channel)."""

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
            logger.error("ReminderSentStore connection failed: %s", e)
            raise

    def _coll(self):
        if self._db is None:
            raise RuntimeError("ReminderSentStore not connected")
        return self._db.reminder_sent

    async def was_sent(self, node_id: str, slot: str, channel: str) -> bool:
        """Slot = date string e.g. YYYY-MM-DD for (due_date - lead_hours)."""
        doc = await self._coll().find_one({"node_id": node_id, "slot": slot, "channel": channel})
        return doc is not None

    async def mark_sent(self, node_id: str, tenant_id: str, slot: str, channel: str) -> None:
        await self._coll().insert_one({
            "node_id": node_id,
            "tenant_id": tenant_id,
            "slot": slot,
            "channel": channel,
            "sent_at": datetime.now(timezone.utc),
        })
