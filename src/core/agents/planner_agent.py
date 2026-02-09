"""PlannerAgent — Daily/weekly plan and priorities from tasks and commitments. Uses SchemaEngine + Graph clusters."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from src.core.agents.base import BaseAgent
from src.models.schema import SchemaEntity


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"
    description = "Produces daily plan, weekly plan, and suggested priorities from tasks and commitments."
    triggers = ["scheduled", "manual", "plan_request"]

    async def run(self, tenant_id: str, space_id: str, user_id: str = "system", context: dict[str, Any] | None = None) -> dict[str, Any]:
        from src.core.schema_engine import get_schema_engine
        from src.main import get_event_store
        from src.core.graph_engine import GraphBuilder

        schema = await get_schema_engine()
        now = datetime.now(timezone.utc)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        week_end = now + timedelta(days=7)
        nodes = await schema.list_nodes(tenant_id=tenant_id, space_id=space_id, limit=500, use_cache=False)
        obligations = await schema.list_upcoming_obligations(tenant_id=tenant_id, space_id=space_id, due_from=now, due_to=week_end, limit=100)
        tasks = [n for n in nodes if n.get("entity") == SchemaEntity.TASK.value]

        def parse_dt(s: str | None):
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        today_tasks = []
        week_tasks = []
        overdue = []
        for t in tasks:
            if (t.get("status") or "").lower() == "completed":
                continue
            due = parse_dt(t.get("due_date"))
            if not due:
                continue
            if due < now:
                overdue.append(t)
            elif due <= today_end:
                today_tasks.append(t)
            elif due <= week_end:
                week_tasks.append(t)

        clusters = []
        try:
            store = await get_event_store()
            builder = GraphBuilder(schema, store)
            await builder.build(tenant_id=tenant_id, space_id=space_id, limit_nodes=500)
            clusters = builder.get_clusters()
        except Exception:
            pass

        daily_plan = [{"title": t.get("title") or "Task", "id": t.get("id"), "due": t.get("due_date")} for t in sorted(today_tasks, key=lambda x: (parse_dt(x.get("due_date")) or now))]
        weekly_plan = [{"title": t.get("title") or "Task", "id": t.get("id"), "due": t.get("due_date")} for t in sorted(week_tasks, key=lambda x: (parse_dt(x.get("due_date")) or now))[:20]]
        priorities = []
        if overdue:
            priorities.append({"type": "overdue", "count": len(overdue), "sample": [t.get("title") for t in overdue[:3]]})
        if today_tasks:
            priorities.append({"type": "today", "count": len(today_tasks), "items": daily_plan[:5]})
        if obligations:
            priorities.append({"type": "commitments_this_week", "count": len(obligations)})

        insights = [
            {"title": "Daily plan", "body": f"{len(daily_plan)} items due today.", "data": {"items": daily_plan}},
            {"title": "Weekly plan", "body": f"{len(weekly_plan)} items this week.", "data": {"items": weekly_plan}},
            {"title": "Priorities", "body": f"Overdue: {len(overdue)}, Today: {len(today_tasks)}, Commitments: {len(obligations)}.", "data": {"priorities": priorities}},
        ]
        if clusters:
            insights.append({"title": "Task clusters", "body": f"Graph has {len(clusters)} connected clusters.", "data": {"cluster_count": len(clusters)}})
        return {"ok": True, "actions": [], "insights": insights, "daily_plan": daily_plan, "weekly_plan": weekly_plan, "priorities": priorities}
