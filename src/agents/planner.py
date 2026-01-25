"""
Today/Tomorrow Planner Agent — Builds daily/weekly plans, identifies critical actions.
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel

logger = logging.getLogger(__name__)


async def _handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Build today/tomorrow plan from RAG + schema."""
    from src.core.llm_client import get_llm
    rag = context.get("rag_response")
    schema = context.get("schema_nodes", [])
    context_text = rag.context_text if hasattr(rag, "context_text") else str(rag)
    schema_text = "\n".join([f"- {n.get('title', '')}" for n in schema[:20]]) if schema else "No schema items"

    prompt = f"""
Build a daily/weekly plan from the following context:

Context:
{context_text}

Schema (tasks/projects):
{schema_text}

Create:
1. Today: 3-5 critical actions (priority: high/medium)
2. Tomorrow: 3-5 planned actions
3. Critical: Actions that must be done today

Return JSON:
{{
  "today": [{{"action": "...", "priority": "high|medium", "reason": "..."}}],
  "tomorrow": [{{"action": "...", "priority": "..."}}],
  "critical": [{{"action": "...", "urgency": "..."}}]
}}
"""
    llm = get_llm()
    response = await llm.invoke(prompt, temperature=0.4)
    import json
    try:
        plan = json.loads(response)
        return {"ok": True, "plan": plan, "explanation": "today_tomorrow_planner_llm"}
    except:
        return {"ok": True, "plan": {"today": [], "tomorrow": [], "critical": []}, "raw_response": response}


class TodayTomorrowPlannerAgent:
    """Daily/weekly planning from tasks and context."""

    @staticmethod
    async def run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return await _handler(tenant_id, space_id, user_id, context)


planner_spec = AgentSpec(
    name="TodayTomorrowPlannerAgent",
    type="planner",
    triggers=["ingest", "daily_summary", "plan_request"],
    tools=["rag", "schema", "llm"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Builds daily/weekly plans, identifies critical actions.",
    handler=_handler,
)
