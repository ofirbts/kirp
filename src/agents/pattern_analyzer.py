"""
Pattern Analyzer Agent — Detects habits, overload, procrastination, repeated themes.
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
    """Run pattern analysis over RAG context."""
    from src.core.llm_client import get_llm
    rag = context.get("rag_response")
    if not rag:
        return {"ok": False, "error": "missing_rag_context"}

    context_text = rag.context_text if hasattr(rag, "context_text") else str(rag)
    prompt = f"""
Analyze the following user activity and detect patterns:

{context_text}

Detect:
1. Habits (recurring behaviors)
2. Overload (too many tasks/commitments)
3. Procrastination (delayed actions)
4. Repeated themes (topics that come up often)

Return JSON:
{{
  "patterns": [
    {{"type": "habit|overload|procrastination|theme", "description": "...", "confidence": 0.0-1.0, "evidence": "..."}}
  ],
  "summary": "Overall pattern summary"
}}
"""
    llm = get_llm()
    response = await llm.invoke(prompt, temperature=0.3)
    import json
    try:
        data = json.loads(response)
        return {"ok": True, "patterns": data.get("patterns", []), "summary": data.get("summary"), "explanation": "pattern_analyzer_llm"}
    except:
        return {"ok": True, "patterns": [], "raw_response": response, "explanation": "pattern_analyzer_llm"}


class PatternAnalyzerAgent:
    """Pattern analysis over events / RAG context."""

    @staticmethod
    async def run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return await _handler(tenant_id, space_id, user_id, context)


pattern_analyzer_spec = AgentSpec(
    name="PatternAnalyzerAgent",
    type="analyzer",
    triggers=["ingest", "daily_summary", "pattern_analysis"],
    tools=["rag", "llm"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Detects habits, overload, procrastination, repeated themes.",
    handler=_handler,
)
