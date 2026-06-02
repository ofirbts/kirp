"""
Future Obligations Agent — Detects upcoming tasks and commitments (due_date in range).

Used by ReminderAgent and by UI/scheduled jobs to list what's due.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel

logger = logging.getLogger(__name__)


async def _handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    List upcoming obligations (tasks + commitments) with due_date in [now, now+horizon_days].
    """
    from src.core.schema_engine import get_schema_engine
    schema = await get_schema_engine()
    horizon_days = int(context.get("horizon_days", 7))
    due_from = datetime.now(timezone.utc)
    due_to = due_from + timedelta(days=horizon_days)
    obligations = await schema.list_upcoming_obligations(
        tenant_id=tenant_id,
        space_id=space_id or None,
        due_from=due_from,
        due_to=due_to,
        limit=200,
    )
    # Enrich with owner from metadata for reminder delivery
    for ob in obligations:
        meta = ob.get("metadata") or {}
        if isinstance(meta, dict):
            ob["owner"] = meta.get("owner") or meta.get("user_id") or user_id
        else:
            ob["owner"] = user_id
    return {
        "ok": True,
        "obligations": obligations,
        "due_from": due_from.isoformat(),
        "due_to": due_to.isoformat(),
        "count": len(obligations),
    }


future_obligations_spec = AgentSpec(
    name="FutureObligationsAgent",
    type="obligations",
    triggers=["scheduled", "reminder", "manual"],
    tools=["schema"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Detects upcoming tasks and commitments (due_date in range).",
    handler=_handler,
)
