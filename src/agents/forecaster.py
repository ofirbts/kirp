"""
Forecaster Agent — Predicts tomorrow's load, bottlenecks, upcoming issues.
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel
from src.core.llm_router import get_llm_for_task

logger = logging.getLogger(__name__)


async def _handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Forecast load, bottlenecks, issues from events + RAG. Fetches RAG when not provided."""
    rag = context.get("rag_response")
    if not rag:
        from src.core.rag_engine import get_shared_rag_engine
        engine = await get_shared_rag_engine()
        rag = await engine.search(
            query="recent activity and load",
            tenant_id=tenant_id,
            space_id=space_id or "all",
            user_id=user_id,
            limit=10,
        )
    events = context.get("events", [])
    context_text = rag.context_text if hasattr(rag, "context_text") else str(rag)

    prompt = f"""
Predict tomorrow's load, bottlenecks, and upcoming issues from this context:

{context_text}

Forecast:
1. Tomorrow's load (low/medium/high)
2. Potential bottlenecks (what might block progress)
3. Upcoming issues (risks that might emerge)

Return JSON:
{{
  "tomorrow_load": "low|medium|high",
  "bottlenecks": [{{"description": "...", "severity": "low|medium|high"}}],
  "upcoming_issues": [{{"issue": "...", "probability": 0.0-1.0, "impact": "low|medium|high"}}]
}}
"""
    # Forecasts impact planning → treat as critical-grade reasoning.
    llm = get_llm_for_task("critical")
    response = await llm.invoke(prompt, temperature=0.5)
    import json
    try:
        forecast = json.loads(response)
        return {"ok": True, "forecast": forecast, "explanation": "forecaster_llm"}
    except:
        return {"ok": True, "forecast": {"tomorrow_load": "medium", "bottlenecks": [], "upcoming_issues": []}, "raw_response": response}


class ForecasterAgent:
    """Predicts load, bottlenecks, issues."""

    @staticmethod
    async def run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return await _handler(tenant_id, space_id, user_id, context)


forecaster_spec = AgentSpec(
    name="ForecasterAgent",
    type="forecaster",
    triggers=["daily_summary", "forecast_request"],
    tools=["rag", "llm"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Predicts tomorrow's load, bottlenecks, and upcoming issues.",
    handler=_handler,
)
