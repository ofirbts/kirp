"""OverloadAgent — Detects workload overload, too many active projects/commitments. Uses Graph + Schema."""

from __future__ import annotations

from typing import Any

from src.core.agents.base import BaseAgent
from src.models.schema import SchemaEntity


class OverloadAgent(BaseAgent):
    name = "OverloadAgent"
    description = "Detects workload overload, too many active projects, and too many commitments."
    triggers = ["scheduled", "manual"]

    async def run(self, tenant_id: str, space_id: str, user_id: str = "system", context: dict[str, Any] | None = None) -> dict[str, Any]:
        from src.core.schema_engine import get_schema_engine
        from src.main import get_event_store
        from src.core.graph_engine import GraphBuilder

        schema = await get_schema_engine()
        store = await get_event_store()
        nodes = await schema.list_nodes(tenant_id=tenant_id, space_id=space_id, limit=1000, use_cache=False)
        tasks = [n for n in nodes if n.get("entity") == SchemaEntity.TASK.value]
        projects = [n for n in nodes if n.get("entity") == SchemaEntity.PROJECT.value]
        commitments = [n for n in nodes if n.get("entity") == SchemaEntity.COMMITMENT.value]
        active_tasks = [t for t in tasks if (t.get("status") or "").lower() != "completed"]
        active_projects = [p for p in projects if any((t.get("status") or "").lower() != "completed" for t in tasks if t.get("parent_id") == p.get("id")) or not [t for t in tasks if t.get("parent_id") == p.get("id")]]
        active_commitments = [c for c in commitments if (c.get("status") or "").lower() not in ("completed", "cancelled")]
        insights = []
        if len(active_tasks) > 30:
            insights.append({"title": "High task load", "body": f"You have {len(active_tasks)} active tasks.", "data": {"count": len(active_tasks)}})
        if len(active_projects) > 5:
            insights.append({"title": "Many active projects", "body": f"{len(active_projects)} projects in progress.", "data": {"count": len(active_projects)}})
        if len(active_commitments) > 10:
            insights.append({"title": "Many commitments", "body": f"{len(active_commitments)} active commitments.", "data": {"count": len(active_commitments)}})
        try:
            builder = GraphBuilder(schema, store)
            await builder.build(tenant_id=tenant_id, space_id=space_id, limit_nodes=1000)
            dist = builder.get_life_area_distribution()
            if dist:
                insights.append({"title": "Life area distribution", "body": "Tasks/projects per life area.", "data": dist})
        except Exception as e:
            self.log_error("Graph failed", exc=e)
        return {"ok": True, "actions": [], "insights": insights}
