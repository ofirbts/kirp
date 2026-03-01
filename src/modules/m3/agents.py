"""
M3 IdentityOS — Agent specs and stub handlers.

All M3 agents are registered in KIRP's Agent Framework and invoked from pipeline stages.
ReflectionClassifierAgent calls LLM to classify reflection into pillar_scores and mood.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel

logger = logging.getLogger(__name__)

# Default pillars for classification (spec 6.1 / identity)
DEFAULT_PILLARS = ["health", "work", "family", "learning"]


async def _stub_m3_agent(
    agent_name: str,
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Stub handler: audit-only; no Memory or external calls."""
    return {
        "ok": True,
        "module": "m3",
        "agent": agent_name,
        "tenant_id": tenant_id,
        "user_id": user_id,
    }


async def _reflection_classifier_handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Classify reflection text via LLM into pillar_scores and mood.
    Returns structured result; writeback already persisted the reflection (stages run after writeback).
    """
    reflection_text = (context.get("reflection_text") or context.get("content") or "").strip()
    if not reflection_text:
        return {
            "ok": True,
            "module": "m3",
            "agent": "ReflectionClassifierAgent",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "pillar_scores": {},
            "mood": "",
        }
    try:
        from src.core.llm_router import get_llm_for_task
        llm = get_llm_for_task("bulk")
        pillars_str = ", ".join(DEFAULT_PILLARS)
        prompt = f"""Classify this daily reflection in one short JSON object only.
Use keys: "pillar_scores" (object with exactly these keys, each 0.0-1.0: {pillars_str}) and "mood" (one word or short phrase).
Reflection:
{reflection_text[:2000]}

Reply with only the JSON, no markdown."""
        response = await llm.invoke(prompt, temperature=0.2, max_tokens=300)
        text = (response or "").strip()
        # Strip markdown code block if present
        if "```" in text:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if m:
                text = m.group(1).strip()
        data = json.loads(text)
        pillar_scores = data.get("pillar_scores") or {}
        if isinstance(pillar_scores, dict):
            pillar_scores = {k: float(v) for k, v in pillar_scores.items() if isinstance(v, (int, float))}
        mood = str(data.get("mood", "") or "").strip()[:100]
        return {
            "ok": True,
            "module": "m3",
            "agent": "ReflectionClassifierAgent",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "pillar_scores": pillar_scores,
            "mood": mood,
        }
    except json.JSONDecodeError as e:
        logger.warning("ReflectionClassifierAgent JSON parse failed: %s", e)
        return {
            "ok": False,
            "module": "m3",
            "agent": "ReflectionClassifierAgent",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "error": "classification_parse_failed",
            "pillar_scores": {},
            "mood": "",
        }
    except Exception as e:
        logger.warning("ReflectionClassifierAgent failed: %s", e)
        return {
            "ok": False,
            "module": "m3",
            "agent": "ReflectionClassifierAgent",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "error": str(e),
            "pillar_scores": {},
            "mood": "",
        }


def _m3_handler(name: str):
    async def h(tenant_id: str, space_id: str, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        return await _stub_m3_agent(name, tenant_id, space_id, user_id, context)
    return h


# Spec table per architecture: IdentityIntentAgent, ReflectionClassifierAgent, IdentityVectorAgent,
# GapAnalysisAgent, MicroActionGeneratorAgent, WeeklySynthesisAgent, MonthlyEvolutionAgent, IdentityDiscriminatorAgent

identity_intent_agent_spec = AgentSpec(
    name="IdentityIntentAgent",
    type="m3_intent",
    triggers=["m3_intent", "manual"],
    tools=["schema", "memory"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Normalizes user intent (goal change, pillar focus); may emit m3.identity_intent_declared.",
    handler=_m3_handler("IdentityIntentAgent"),
)

reflection_classifier_agent_spec = AgentSpec(
    name="ReflectionClassifierAgent",
    type="m3_reflection",
    triggers=["m3_reflection", "manual"],
    tools=["memory"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Classifies raw reflection text into pillar_scores, mood, structured fields; writes reflection_entries.",
    handler=_reflection_classifier_handler,
)

identity_vector_agent_spec = AgentSpec(
    name="IdentityVectorAgent",
    type="m3_identity",
    triggers=["m3_writeback", "manual"],
    tools=["memory", "rag"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Updates identity vector and alignment score from reflections and actions; writes identity_profiles.",
    handler=_m3_handler("IdentityVectorAgent"),
)

gap_analysis_agent_spec = AgentSpec(
    name="GapAnalysisAgent",
    type="m3_gap",
    triggers=["m3_pattern", "manual"],
    tools=["memory", "schema"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Computes gap heatmap, pillar deltas, top_gaps from identity_profiles and ideal_self.",
    handler=_m3_handler("GapAnalysisAgent"),
)

micro_action_generator_agent_spec = AgentSpec(
    name="MicroActionGeneratorAgent",
    type="m3_plan",
    triggers=["m3_plan", "manual"],
    tools=["memory", "schema"],
    autonomy=AutonomyLevel.SEMI,
    tenant_scopes=[],
    description="Generates micro_actions with roi_score and due_by from gap output and context.",
    handler=_m3_handler("MicroActionGeneratorAgent"),
)

weekly_synthesis_agent_spec = AgentSpec(
    name="WeeklySynthesisAgent",
    type="m3_synthesis",
    triggers=["m3_plan", "m3_weekly", "manual"],
    tools=["memory"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Produces weekly_synthesis from week's reflection_entries and micro_actions.",
    handler=_m3_handler("WeeklySynthesisAgent"),
)

monthly_evolution_agent_spec = AgentSpec(
    name="MonthlyEvolutionAgent",
    type="m3_evolution",
    triggers=["m3_plan", "m3_monthly", "manual"],
    tools=["memory"],
    autonomy=AutonomyLevel.SEMI,
    tenant_scopes=[],
    description="Produces monthly_evolution from synthesis and identity trajectory; high entropy.",
    handler=_m3_handler("MonthlyEvolutionAgent"),
)

identity_discriminator_agent_spec = AgentSpec(
    name="IdentityDiscriminatorAgent",
    type="m3_critique",
    triggers=["m3_critique", "manual"],
    tools=["memory"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Critiques proposed plan: overload, explainability, user overload; pass/fail + reason.",
    handler=_m3_handler("IdentityDiscriminatorAgent"),
)

M3_AGENT_SPECS = [
    identity_intent_agent_spec,
    reflection_classifier_agent_spec,
    identity_vector_agent_spec,
    gap_analysis_agent_spec,
    micro_action_generator_agent_spec,
    weekly_synthesis_agent_spec,
    monthly_evolution_agent_spec,
    identity_discriminator_agent_spec,
]
