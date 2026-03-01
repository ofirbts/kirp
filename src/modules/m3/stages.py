"""
M3 IdentityOS — Pipeline stages 2–5: context retrieval, pattern analysis, plan, critique.

Loads context from M3 memory and invokes M3 agents via the agent framework.
Per spec 4: Context Retrieval → Pattern Analysis → Plan Generation → Plan Critique.
"""

from __future__ import annotations

import logging
from typing import Any

from src.modules.m3.events import (
    EVENT_M3_DAILY_REFLECTION_SUBMITTED,
    EVENT_M3_WEEKLY_SYNTHESIS_REQUESTED,
    EVENT_M3_MONTHLY_EVOLUTION_REQUESTED,
)
from src.modules.m3.memory import get_m3_memory_store

logger = logging.getLogger(__name__)


async def _m3_context(
    tenant_id: str,
    space_id: str,
    user_id: str,
    event_type: str,
    metadata: dict[str, Any],
    content: str,
) -> dict[str, Any]:
    """Stage 2: Context Retrieval — last N reflections, identity profile, open micro_actions."""
    store = get_m3_memory_store()
    ctx: dict[str, Any] = {
        "event_type": event_type,
        "metadata": metadata,
        "content": content,
    }
    try:
        if event_type == EVENT_M3_DAILY_REFLECTION_SUBMITTED:
            reflections = await store.list_reflections(tenant_id, user_id, limit=10)
            ctx["reflections"] = [
                {
                    "id": r.id,
                    "reflection_date": r.reflection_date,
                    "reflection_text": r.reflection_text[:500],
                    "pillar_scores": r.pillar_scores,
                    "mood": r.mood,
                }
                for r in reflections
            ]
            profile = await store.get_identity_profile(tenant_id, user_id)
            ctx["identity_profile"] = (
                {"pillar_scores": profile.pillar_scores} if profile else None
            )
            open_actions = await store.list_micro_actions(
                tenant_id, user_id, status="pending", limit=20
            )
            ctx["open_micro_actions"] = [
                {"action_id": a.action_id, "title": a.title, "pillar": a.pillar, "due_by": a.due_by}
                for a in open_actions
            ]
        elif event_type == EVENT_M3_WEEKLY_SYNTHESIS_REQUESTED:
            week_start = metadata.get("week_start")
            week_end = metadata.get("week_end")
            reflections = await store.list_reflections(tenant_id, user_id, limit=50)
            if week_start or week_end:
                reflections = [
                    r for r in reflections
                    if (not week_start or r.reflection_date >= week_start)
                    and (not week_end or r.reflection_date <= week_end)
                ]
            ctx["reflections"] = [{"reflection_date": r.reflection_date, "reflection_text": r.reflection_text[:300]} for r in reflections]
            ctx["micro_actions"] = [
                {"action_id": a.action_id, "title": a.title, "status": a.status}
                for a in await store.list_micro_actions(tenant_id, user_id, limit=50)
            ]
            syntheses = await store.list_weekly_syntheses(tenant_id, user_id, limit=4)
            ctx["prior_syntheses"] = [{"week_start": s.week_start, "summary": s.summary[:200]} for s in syntheses]
        elif event_type == EVENT_M3_MONTHLY_EVOLUTION_REQUESTED:
            month = metadata.get("month")
            syntheses = await store.list_weekly_syntheses(tenant_id, user_id, limit=8)
            ctx["weekly_syntheses"] = [{"week_start": s.week_start, "summary": s.summary[:200]} for s in syntheses]
            evolutions = await store.list_monthly_evolutions(tenant_id, user_id, limit=12)
            ctx["identity_trajectory"] = [{"month": e.month, "new_goals": e.new_goals} for e in evolutions]
            profile = await store.get_identity_profile(tenant_id, user_id)
            ctx["identity_profile"] = {"pillar_scores": profile.pillar_scores} if profile else None
    except Exception as e:
        logger.warning("M3 context retrieval failed: %s", e)
    return ctx


async def run_m3_stages(
    event_type: str,
    tenant_id: str,
    space_id: str,
    user_id: str,
    metadata: dict[str, Any],
    content: str = "",
) -> None:
    """
    Run M3 pipeline stages 2–5 after store and writeback: context retrieval, then
    ReflectionClassifier (2–3), GapAnalysis (3), MicroActionGenerator (4), IdentityDiscriminator (5).
    Agents are stubs; full logic can be added later.
    """
    from src.core.agent_registry import get_agent_framework_with_all_agents

    ctx = await _m3_context(tenant_id, space_id, user_id, event_type, metadata, content)
    af = get_agent_framework_with_all_agents()

    try:
        if event_type == EVENT_M3_DAILY_REFLECTION_SUBMITTED:
            # Stage 2–3: classify reflection (pillar_scores, mood)
            spec = af.get("ReflectionClassifierAgent")
            if spec and spec.handler:
                await spec.handler(tenant_id, space_id, user_id, {**ctx, "reflection_text": content or ctx.get("metadata", {}).get("reflection_text", "")})
            # Stage 3: gap analysis
            spec = af.get("GapAnalysisAgent")
            if spec and spec.handler:
                await spec.handler(tenant_id, space_id, user_id, ctx)
            # Stage 4: optional micro-actions (Discriminator may gate)
            spec = af.get("MicroActionGeneratorAgent")
            if spec and spec.handler:
                await spec.handler(tenant_id, space_id, user_id, ctx)
            # Stage 5: critique (stub)
            spec = af.get("IdentityDiscriminatorAgent")
            if spec and spec.handler:
                await spec.handler(tenant_id, space_id, user_id, ctx)
        elif event_type == EVENT_M3_WEEKLY_SYNTHESIS_REQUESTED:
            spec = af.get("WeeklySynthesisAgent")
            if spec and spec.handler:
                await spec.handler(tenant_id, space_id, user_id, ctx)
        elif event_type == EVENT_M3_MONTHLY_EVOLUTION_REQUESTED:
            spec = af.get("MonthlyEvolutionAgent")
            if spec and spec.handler:
                await spec.handler(tenant_id, space_id, user_id, ctx)
    except Exception as e:
        logger.warning("M3 stage run failed: %s", e)
