"""
M3 IdentityOS — Agent specs and stub handlers.

All M3 agents are registered in KIRP's Agent Framework and invoked from pipeline stages.
Stub handlers return a minimal result; full implementations will use Memory and EGE.
"""

from __future__ import annotations

from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel


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
    handler=_m3_handler("ReflectionClassifierAgent"),
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
