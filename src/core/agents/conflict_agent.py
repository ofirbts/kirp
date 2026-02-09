"""
ConflictAgent — Detects schedule conflicts, double-bookings, impossible deadlines.
Uses Calendar + commitments (placeholder: compares commitment due dates and overlap).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from src.core.agents.base import BaseAgent
from src.models.schema import SchemaEntity


class ConflictAgent(BaseAgent):
    name = "ConflictAgent"
    description = "Detects schedule conflicts, double-bookings, and impossible deadlines."
    triggers = ["scheduled", "manual", "new_commitment"]

    async def run(self, tenant_id: str, space_id: str, user_id: str = "system", context: dict[str, Any] | None = None) -> dict[str, Any]:
        from src.core.schema_engine import get_schema_engine

        schema = await get_schema_engine()
        nodes = await schema.list_nodes(tenant_id=tenant_id, space_id=space_id, limit=500, use_cache=False)
        commitments = [n for n in nodes if n.get("entity") == SchemaEntity.COMMITMENT.value]
        commitments = [c for c in commitments if (c.get("status") or "").lower() not in ("completed", "cancelled")]

        def parse_dt(s: str | None):
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        insights = []
        with_due = [(c, parse_dt(c.get("due_date"))) for c in commitments if c.get("due_date")]
        with_due = [(c, d) for c, d in with_due if d is not None]
        for i, (c1, d1) in enumerate(with_due):
            for c2, d2 in with_due[i + 1 : i + 5]:
                if abs((d1 - d2).total_seconds()) < 3600 and c1.get("id") != c2.get("id"):
                    insights.append({
                        "title": "Possible double-booking",
                        "body": f"'{c1.get('title')}' and '{c2.get('title')}' are due within 1 hour.",
                        "data": {"id1": c1.get("id"), "id2": c2.get("id"), "due1": c1.get("due_date"), "due2": c2.get("due_date")},
                    })
                    break

        return {"ok": True, "actions": [], "insights": insights}
