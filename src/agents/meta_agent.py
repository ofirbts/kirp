"""
Meta Agent — Orchestrates all agents.

Routes requests to optimal agents, coordinates multi-agent workflows.
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.agent_framework import AgentFramework, AgentSpec, AutonomyLevel
from src.core.llm_client import get_llm

logger = logging.getLogger(__name__)


class MetaAgent:
    """Orchestrates all agents. Routes to optimal agent(s)."""

    def __init__(self, agent_framework: AgentFramework) -> None:
        self._framework = agent_framework
        self._llm = get_llm()

    async def route(
        self,
        query: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Route query to optimal agent(s) using LLM."""
        agents = self._framework.list_all()
        agent_descriptions = "\n".join(
            f"- {a.name}: {a.description} (triggers: {', '.join(a.triggers)})"
            for a in agents
        )

        routing_prompt = f"""
You are the Meta Agent orchestrator for KIRP Enterprise.

Available agents:
{agent_descriptions}

User query: {query}

Which agent(s) should handle this? Return JSON:
{{
  "primary_agent": "AgentName",
  "secondary_agents": ["AgentName1", "AgentName2"],
  "reason": "why this routing"
}}
"""

        try:
            response = await self._llm.invoke(routing_prompt, temperature=0.3)
            import json
            routing = json.loads(response)
            primary = routing.get("primary_agent", "")
            secondary = routing.get("secondary_agents", [])

            # Run primary agent
            result: dict[str, Any] = {"routing": routing, "results": {}}
            if primary:
                agent_result = await self._framework.run(
                    primary, tenant_id=tenant_id, space_id=space_id, user_id=user_id, context=context
                )
                result["results"][primary] = agent_result

            # Run secondary agents
            for agent_name in secondary:
                if agent_name != primary:
                    agent_result = await self._framework.run(
                        agent_name, tenant_id=tenant_id, space_id=space_id, user_id=user_id, context=context
                    )
                    result["results"][agent_name] = agent_result

            return result
        except Exception as e:
            logger.exception("MetaAgent routing failed: %s", e)
            return {"ok": False, "error": str(e)}


meta_agent_spec = AgentSpec(
    name="MetaAgent",
    type="orchestrator",
    triggers=["*"],
    tools=["llm", "agent_framework"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Orchestrates all agents, routes queries to optimal agents.",
)
