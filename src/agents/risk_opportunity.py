"""
Risk/Opportunity Agent — Detects risks, missed follow-ups, emerging opportunities.
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
    """Extract risks, missed follow-ups, opportunities from RAG + events. Fetches RAG when not provided."""
    rag = context.get("rag_response")
    if not rag:
        from src.core.rag_engine import get_shared_rag_engine
        engine = await get_shared_rag_engine()
        rag = await engine.search(
            query="recent activity risks opportunities",
            tenant_id=tenant_id,
            space_id=space_id or "all",
            user_id=user_id,
            limit=10,
        )
    context_text = rag.context_text if hasattr(rag, "context_text") else str(rag)

    prompt = f"""
Analyze this context and extract:

1. RISKS: Things that could go wrong or cause problems
2. OPPORTUNITIES: Things that could be leveraged or improved
3. MISSED FOLLOW-UPS: Actions/tasks that were mentioned but not completed

Context:
{context_text}

Return JSON:
{{
  "risks": [{{"title": "...", "severity": "low|medium|high", "confidence": 0.0-1.0, "description": "..."}}],
  "opportunities": [{{"title": "...", "impact": "low|medium|high", "confidence": 0.0-1.0, "description": "..."}}],
  "missed_follow_ups": [{{"action": "...", "original_date": "...", "urgency": "low|medium|high"}}]
}}
"""
    # Risk analysis → critical-grade provider.
    llm = get_llm_for_task("critical")
    response = await llm.invoke(prompt, temperature=0.4)
    import json
    try:
        items = json.loads(response)
        return {"ok": True, "items": items, "explanation": "risk_opportunity_llm"}
    except:
        return {"ok": True, "items": {"risks": [], "opportunities": [], "missed_follow_ups": []}, "raw_response": response}


class RiskOpportunityAgent:
    """Risks, opportunities, follow-ups."""

    @staticmethod
    async def run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return await _handler(tenant_id, space_id, user_id, context)


risk_opportunity_spec = AgentSpec(
    name="RiskOpportunityAgent",
    type="risk_opportunity",
    triggers=["ingest", "daily_summary", "risk_scan"],
    tools=["rag", "llm"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Detects risks, missed follow-ups, emerging opportunities.",
    handler=_handler,
)
