"""
Pattern Analyzer Agent — Detects habits, overload, procrastination, repeated themes.
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
    """Run pattern analysis over RAG context. Fetches RAG internally when not provided."""
    rag = context.get("rag_response")
    if not rag:
        from src.core.rag_engine import get_shared_rag_engine
        engine = await get_shared_rag_engine()
        rag = await engine.search(
            query="recent activity patterns",
            tenant_id=tenant_id,
            space_id=space_id or "all",
            user_id=user_id,
            limit=10,
        )
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
    # Pattern analysis / enrichment → bulk provider.
    llm = get_llm_for_task("bulk")
    response = await llm.invoke(prompt, temperature=0.3)
    import json
    import re

    def _extract_json(text: str) -> str | None:
        """Try to parse JSON; if failed, strip markdown code blocks and retry."""
        text = (text or "").strip()
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        # Strip ```json ... ``` or ``` ... ```
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            return m.group(1).strip()
        # First { ... } or [ ... ]
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if m:
            return m.group(1)
        return None

    raw_for_fallback = response
    try:
        json_str = _extract_json(response)
        data = json.loads(json_str) if json_str else {}
    except Exception:
        data = {}

    patterns = data.get("patterns", []) or []
    summary = data.get("summary") or ""
    # Standardized shape: always expose insights for history/notifications/result_count.
    insights = [
        {
            "title": f"Pattern: {p.get('type', 'pattern')}",
            "body": p.get("description") or summary or "Pattern detected.",
            "data": p,
        }
        for p in patterns
    ]
    # Ensure at least one insight when we have a summary (so result_count > 0 and history is written).
    if not insights and summary:
        insights = [{"title": "Pattern summary", "body": summary, "data": {"summary": summary}}]
    if not insights:
        insights = [{"title": "Pattern analysis ran", "body": "No patterns detected in current context.", "data": {}}]

    return {
        "ok": True,
        "patterns": patterns,
        "summary": summary or None,
        "insights": insights,
        "actions": [],
        "raw_response": raw_for_fallback,
        "explanation": "pattern_analyzer_llm",
    }


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
