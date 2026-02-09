"""
ReminderAgentV2 — Upgrade of ReminderAgent. Uses obligations + due dates.
Detects: upcoming deadlines, overdue items. Can emit suggest_reschedule actions.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from src.core.agents.base import BaseAgent
from src.core.agent_actions import action_doc, ACTION_SUGGEST_RESCHEDULE


class ReminderAgentV2(BaseAgent):
    name = "ReminderAgentV2"
    description = "Detects upcoming deadlines and overdue items; suggests reschedule."
    triggers = ["scheduled", "reminder", "manual"]

    async def run(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str = "system",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from src.core.schema_engine import get_schema_engine

        schema = await get_schema_engine()
        now = datetime.now(timezone.utc)
        due_to = now + timedelta(days=context.get("horizon_days", 7) if context else 7)
        obligations = await schema.list_upcoming_obligations(
            tenant_id=tenant_id, space_id=space_id or None, due_from=now, due_to=due_to, limit=200
        )

        def parse_dt(s: str | None):
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        insights = []
        actions = []
        overdue = [o for o in obligations if parse_dt(o.get("due_date")) and parse_dt(o.get("due_date")) < now]
        due_soon = [o for o in obligations if parse_dt(o.get("due_date")) and 0 < (parse_dt(o.get("due_date")) - now).total_seconds() < 48 * 3600]

        if overdue:
            insights.append({"title": "Overdue", "body": f"{len(overdue)} items overdue.", "data": {"count": len(overdue)}})
            for o in overdue[:3]:
                actions.append(action_doc(
                    self.name, ACTION_SUGGEST_RESCHEDULE,
                    {"node_id": o.get("id"), "title": o.get("title"), "current_due": o.get("due_date"), "suggested_reason": "overdue"},
                    tenant_id, space_id, user_id
                ))
            try:
                from src.core.notifications import notify_user
                for o in overdue[:5]:
                    await notify_user(tenant_id, user_id, "commitment_overdue", "Overdue", o.get("title") or "Item", space_id=space_id, entity_id=o.get("id"))
            except Exception:
                pass
            try:
                from src.core.history import record_history
                for o in overdue[:10]:
                    await record_history(tenant_id, space_id or "all", user_id, "commitment_due", "Commitment overdue", o.get("title") or "Item", source="reminder_agent", entity_id=o.get("id"))
            except Exception:
                pass
        if due_soon:
            insights.append({"title": "Due soon", "body": f"{len(due_soon)} items in the next 48 hours.", "data": {"count": len(due_soon)}})
            try:
                from src.core.notifications import notify_user
                for o in due_soon[:5]:
                    await notify_user(tenant_id, user_id, "commitment_due", "Due soon", o.get("title") or "Item", space_id=space_id, entity_id=o.get("id"))
            except Exception:
                pass
            try:
                from src.core.history import record_history
                for o in due_soon[:10]:
                    await record_history(tenant_id, space_id or "all", user_id, "commitment_due", "Commitment due soon", o.get("title") or "Item", source="reminder_agent", entity_id=o.get("id"))
            except Exception:
                pass
        if (overdue or due_soon) and (actions or insights):
            try:
                from src.core.notifications import notify_user
                await notify_user(tenant_id, user_id, "reminder", "Reminder", f"{len(overdue)} overdue, {len(due_soon)} due soon.", space_id=space_id)
            except Exception:
                pass

        return {"ok": True, "actions": actions, "insights": insights}
