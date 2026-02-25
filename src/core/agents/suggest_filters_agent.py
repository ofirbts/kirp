"""SuggestFiltersAgent - Suggests grouping and filters for inbox/tasks."""

from __future__ import annotations

from typing import Any

from src.core.agents.base import BaseAgent


class SuggestFiltersAgent(BaseAgent):
    name = "SuggestFiltersAgent"
    description = "Suggests grouping or filters for inbox and task views."
    triggers = ["scheduled", "manual"]

    async def run(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str = "system",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from src.core.schema_engine import get_schema_engine
        from src.models.schema import SchemaEntity

        schema = await get_schema_engine()
        nodes = await schema.list_nodes(tenant_id=tenant_id, space_id=space_id, limit=500, use_cache=False)
        tasks = [n for n in nodes if n.get("entity") == SchemaEntity.TASK.value]
        sources: dict[str, int] = {}
        for n in tasks:
            src = (n.get("metadata") or n.get("extra") or {}).get("source") or "unknown"
            sources[src] = sources.get(src, 0) + 1
        suggestions = []
        if len(sources) > 2:
            suggestions.append({"type": "group_by_source", "title": "Group by source", "data": {"sources": list(sources.keys())}})
        return {"ok": True, "suggestions": suggestions}
