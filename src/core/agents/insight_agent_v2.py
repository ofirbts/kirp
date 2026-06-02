"""
InsightAgentV2 — Deeper insights using InsightsEngine + GraphEngine.
Uses get_high_degree_nodes, get_isolated_nodes, get_life_area_distribution.
"""

from __future__ import annotations

from typing import Any

from src.core.agents.base import BaseAgent
from src.core.insights_engine import InsightsEngine
from src.core.graph_engine import GraphBuilder


class InsightAgentV2(BaseAgent):
    name = "InsightAgentV2"
    description = "Deeper insights and cross-entity reasoning from InsightsEngine and Life Graph."
    triggers = ["scheduled", "manual", "new_event"]

    async def run(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str = "system",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from src.core.schema_engine import get_schema_engine
        from src.main import get_event_store

        schema = await get_schema_engine()
        store = await get_event_store()
        insights_out: list[dict[str, Any]] = []

        engine = InsightsEngine(schema, store)
        raw_insights = await engine.compute_insights(tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=20)
        for i in raw_insights:
            insights_out.append({"title": i.title, "body": i.body, "category": i.category, "data": i.data, "confidence": i.confidence})

        try:
            builder = GraphBuilder(schema, store)
            graph = await builder.build(tenant_id=tenant_id, space_id=space_id, limit_nodes=1000)
            high = builder.get_high_degree_nodes(min_degree=3)
            if high:
                key_entities = [{"label": n.label, "type": n.type, "degree": d} for n, d in high[:10]]
                insights_out.append({"title": "Key entities in your graph", "body": f"{len(high)} nodes have many connections.", "data": {"key_entities": key_entities}})
            isolated = builder.get_isolated_nodes()
            if isolated:
                insights_out.append({"title": "Isolated nodes", "body": f"{len(isolated)} nodes have no connections.", "data": {"count": len(isolated), "sample": [n.label for n in isolated[:5]]}})
            dist = builder.get_life_area_distribution()
            if dist:
                insights_out.append({"title": "Life area distribution", "body": "Tasks/projects per life area.", "data": dist})
        except Exception as e:
            self.log_error("Graph analysis failed", exc=e)

        return {"ok": True, "actions": [], "insights": insights_out}
