"""
API routes for reminders: upcoming obligations and user preferences.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["reminders"])


@router.get("/reminders/upcoming")
async def list_upcoming_obligations(
    tenant_id: str = "default",
    space_id: str | None = None,
    horizon_days: int = 7,
) -> dict[str, Any]:
    """List upcoming tasks and commitments (due_date in [now, now+horizon_days])."""
    from src.core.schema_engine import get_schema_engine
    schema = await get_schema_engine()
    now = datetime.now(timezone.utc)
    due_to = now + timedelta(days=horizon_days)
    obligations = await schema.list_upcoming_obligations(
        tenant_id=tenant_id,
        space_id=space_id,
        due_from=now,
        due_to=due_to,
    )
    return {"ok": True, "obligations": obligations, "due_from": now.isoformat(), "due_to": due_to.isoformat()}


@router.get("/reminders/preferences")
async def get_reminder_preferences(
    tenant_id: str = "default",
    user_id: str = "system",
) -> dict[str, Any]:
    """Get reminder preferences for user: lead_hours, channels, quiet hours, email_to, whatsapp_to."""
    from src.core.reminder_preferences import ReminderPreferencesStore
    store = ReminderPreferencesStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    await store.connect()
    prefs = await store.get(tenant_id, user_id)
    return {"ok": True, "preferences": prefs}


@router.post("/reminders/preferences")
async def set_reminder_preferences(
    tenant_id: str = "default",
    user_id: str = "system",
    lead_hours: int | None = None,
    channels: list[str] | None = None,
    quiet_start: str | None = None,
    quiet_end: str | None = None,
    whatsapp_to: str | None = None,
    email_to: str | None = None,
) -> dict[str, Any]:
    """Set reminder preferences. Channels: whatsapp, email, notification."""
    from src.core.reminder_preferences import ReminderPreferencesStore
    store = ReminderPreferencesStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    await store.connect()
    await store.set(
        tenant_id=tenant_id,
        user_id=user_id,
        lead_hours=lead_hours,
        channels=channels,
        quiet_start=quiet_start,
        quiet_end=quiet_end,
        whatsapp_to=whatsapp_to,
        email_to=email_to,
    )
    return {"ok": True, "message": "Preferences updated"}


@router.post("/reminders/run")
async def run_reminders_now(
    tenant_id: str = "default",
    space_id: str = "all",
    user_id: str = "system",
    horizon_days: int = 7,
) -> dict[str, Any]:
    """Trigger ReminderAgent once (scheduled run is hourly)."""
    from src.core.agent_registry import get_agent_framework_with_all_agents
    af = get_agent_framework_with_all_agents()
    result = await af.run(
        "ReminderAgent",
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        context={"horizon_days": horizon_days},
    )
    return result
