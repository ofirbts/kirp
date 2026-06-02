"""
Reminder Agent — Schedules and delivers reminders for upcoming obligations.

Uses FutureObligationsAgent (or list_upcoming_obligations), user preferences (lead time, channels),
and delivers via WhatsApp, Email, or in-app Notification. Tracks sent reminders to avoid duplicates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel

logger = logging.getLogger(__name__)


def _parse_due(due_str: str | None) -> datetime | None:
    if not due_str:
        return None
    try:
        return datetime.fromisoformat(due_str.replace("Z", "+00:00"))
    except Exception:
        return None


async def _deliver_reminder(
    channel: str,
    to_identifier: str | None,
    title: str,
    due_str: str,
    tenant_id: str,
    user_id: str,
    node_id: str,
) -> bool:
    """Send reminder via channel. to_identifier: email address or phone. Returns True if sent."""
    body = f"Reminder: {title}\nDue: {due_str}"
    if channel == "email" and to_identifier:
        from src.integrations.email import EmailIntegration
        email = EmailIntegration()
        r = await email.send(to=to_identifier, subject=f"Reminder: {title}", body=body, user_id=user_id)
        return r.get("ok") is True
    if channel == "whatsapp" and to_identifier:
        from src.integrations.whatsapp import WhatsAppIntegration
        wa = WhatsAppIntegration()
        wa.connect()
        r = await wa.send_message(to=to_identifier, text=body, user_id=user_id)
        return r.get("ok") is True
    if channel == "notification":
        # Store as event so UI can show in-app notifications
        try:
            from src.main import get_event_store
            from src.core.event_store import Event
            from uuid import uuid4
            store = await get_event_store()
            ev = Event(
                id=uuid4(),
                tenant_id=tenant_id,
                space_id="all",
                user_id=user_id,
                source="reminder_agent",
                content=body,
                metadata={"node_id": node_id, "due": due_str, "title": title},
                event_type="reminder",
            )
            await store.ingest(ev)
            return True
        except Exception as e:
            logger.warning("Notification (event) ingest failed: %s", e)
            return False
    return False


async def _handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    List upcoming obligations, apply user reminder preferences, and send reminders
    for obligations whose reminder time (due - lead_hours) has passed. Tracks sent to avoid duplicates.
    """
    import os
    from src.core.schema_engine import get_schema_engine
    from src.core.reminder_preferences import ReminderPreferencesStore, ReminderSentStore

    schema = await get_schema_engine()
    prefs_store = ReminderPreferencesStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    sent_store = ReminderSentStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    await prefs_store.connect()
    await sent_store.connect()

    now = datetime.now(timezone.utc)
    due_to = now + timedelta(days=context.get("horizon_days", 7))
    obligations = await schema.list_upcoming_obligations(
        tenant_id=tenant_id,
        space_id=space_id or None,
        due_from=now,
        due_to=due_to,
        limit=200,
    )

    sent_count = 0
    skipped = 0
    errors: list[str] = []

    for ob in obligations:
        node_id = ob.get("id")
        due_str = ob.get("due_date")
        due_dt = _parse_due(due_str)
        if not node_id or not due_dt:
            continue
        owner = (ob.get("metadata") or {}).get("owner") or (ob.get("metadata") or {}).get("user_id") or user_id
        prefs = await prefs_store.get(tenant_id, owner)
        lead_hours = prefs.get("lead_hours", 24)
        channels = prefs.get("channels", ["email"])
        reminder_at = due_dt - timedelta(hours=lead_hours)
        if now < reminder_at:
            continue
        slot = reminder_at.date().isoformat()
        title = ob.get("title", "Obligation")

        # Optional: skip if current time is in user's quiet window (e.g. 22:00–07:00)
        quiet_start = prefs.get("quiet_start")
        quiet_end = prefs.get("quiet_end")
        if quiet_start and quiet_end:
            try:
                from datetime import time as dt_time
                qs = [int(x) for x in quiet_start.split(":")[:2]]
                qe = [int(x) for x in quiet_end.split(":")[:2]]
                t_now = now.time()
                t_quiet_s = dt_time(qs[0], qs[1] if len(qs) > 1 else 0)
                t_quiet_e = dt_time(qe[0], qe[1] if len(qe) > 1 else 0)
                if t_quiet_s < t_quiet_e and t_quiet_s <= t_now <= t_quiet_e:
                    continue
                if t_quiet_s > t_quiet_e and (t_now >= t_quiet_s or t_now <= t_quiet_e):
                    continue
            except Exception:
                pass

        for ch in channels:
            if ch not in ("whatsapp", "email", "notification"):
                continue
            if await sent_store.was_sent(node_id, slot, ch):
                skipped += 1
                continue
            to_id = prefs.get("whatsapp_to") if ch == "whatsapp" else prefs.get("email_to") if ch == "email" else None
            if ch != "notification" and not to_id:
                errors.append(f"{node_id}: no {ch} address for user {owner}")
                continue
            try:
                ok = await _deliver_reminder(ch, to_id, title, due_str or "", tenant_id, owner, node_id)
                if ok:
                    await sent_store.mark_sent(node_id, tenant_id, slot, ch)
                    sent_count += 1
            except Exception as e:
                errors.append(f"{node_id}:{ch}: {e}")

    return {
        "ok": True,
        "reminders_sent": sent_count,
        "skipped_already_sent": skipped,
        "obligations_checked": len(obligations),
        "errors": errors[:20],
    }


reminder_agent_spec = AgentSpec(
    name="ReminderAgent",
    type="reminder",
    triggers=["scheduled", "reminder", "manual"],
    tools=["schema", "whatsapp", "email", "event_store"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Schedules and delivers reminders for upcoming tasks/commitments via WhatsApp, Email, or Notification.",
    handler=_handler,
)
