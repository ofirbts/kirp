"""
Scenario Orchestrator — Reads SCENARIOS.md and executes agents in sequence.

Scenarios define ordered agent lists (e.g. second_brain_daily: PatternAnalyzer → FutureObligations → Insight).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCENARIOS_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "SCENARIOS.md"


def _parse_scenarios(content: str) -> dict[str, list[str]]:
    """
    Parse SCENARIOS.md format:
    ## scenario_name
    agents:
      - AgentA
      - AgentB
    """
    scenarios: dict[str, list[str]] = {}
    current: str | None = None
    in_agents = False
    for line in content.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
            in_agents = False
            if current and current not in scenarios:
                scenarios[current] = []
        elif current and line.strip() == "agents:":
            in_agents = True
        elif current and in_agents and line.strip().startswith("- "):
            agent = line.strip()[2:].strip()
            if agent:
                scenarios[current].append(agent)
    return scenarios


def load_scenarios(path: Path | None = None) -> dict[str, list[str]]:
    """Load scenarios from SCENARIOS.md. Returns {scenario_name: [agent_names]}."""
    p = path or Path(os.getenv("KIRP_SCENARIOS_PATH", str(SCENARIOS_PATH)))
    if not p.exists():
        logger.warning("SCENARIOS.md not found at %s", p)
        return {}
    try:
        content = p.read_text(encoding="utf-8")
        return _parse_scenarios(content)
    except Exception as e:
        logger.exception("Failed to parse SCENARIOS: %s", e)
        return {}


class ScenarioOrchestrator:
    """
    Executes a scenario by running its agents in sequence.
    Passes each agent's output as context to the next.
    """

    def __init__(self) -> None:
        self._scenarios = load_scenarios()

    def list_scenarios(self) -> list[str]:
        """List available scenario names."""
        return list(self._scenarios.keys())

    def get_agents(self, scenario_name: str) -> list[str]:
        """Get ordered agent list for a scenario."""
        return list(self._scenarios.get(scenario_name, []))

    async def run(
        self,
        scenario_name: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
        initial_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run a scenario: execute each agent in sequence, chaining context.
        Returns combined context with each agent's output under step_<AgentName>.
        """
        agents = self.get_agents(scenario_name)
        if not agents:
            return {"ok": False, "error": f"Unknown or empty scenario: {scenario_name}"}

        if not tenant_id or tenant_id == "*":
            return {"ok": False, "error": "tenant_id is required (multi-tenant isolation)"}

        ctx = dict(initial_context or {})
        results: list[dict[str, Any]] = []

        for agent_name in agents:
            try:
                out = await self._run_agent(
                    agent_name=agent_name,
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id=user_id,
                    context=ctx,
                )
                ctx[f"step_{agent_name}"] = out
                ctx.update(out if isinstance(out, dict) else {})
                results.append({"agent": agent_name, "ok": True, "output": out})
            except Exception as e:
                logger.exception("Scenario agent %s failed: %s", agent_name, e)
                results.append({"agent": agent_name, "ok": False, "error": str(e)})
                ctx[f"step_{agent_name}"] = {"ok": False, "error": str(e)}

        return {
            "ok": True,
            "scenario": scenario_name,
            "results": results,
            "context": ctx,
        }

    async def _run_agent(
        self,
        agent_name: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a single agent by name. Uses AgentFramework or special-case (InsightAgent)."""
        # InsightAgent has .ask() API, not a handler
        if agent_name == "InsightAgent":
            return await self._run_insight_agent(tenant_id, space_id, context)

        # Agents that need RAG context: inject if missing
        if "rag_response" not in context and agent_name in (
            "PatternAnalyzerAgent",
            "TodayTomorrowPlannerAgent",
            "ForecasterAgent",
            "RiskOpportunityAgent",
        ):
            rag_ctx = await self._fetch_rag_context(tenant_id, space_id, user_id)
            context = {**context, "rag_response": rag_ctx}

        from src.core.agent_registry import get_agent_framework_with_all_agents

        af = get_agent_framework_with_all_agents()
        spec = af.get(agent_name)
        if not spec or not getattr(spec, "handler", None):
            raise ValueError(f"Agent not found or no handler: {agent_name}")

        return await af.run(
            agent_name=agent_name,
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            context=context,
        )

    async def _fetch_rag_context(
        self, tenant_id: str, space_id: str, user_id: str, query: str = "recent activity patterns"
    ) -> Any:
        """Fetch RAG context for scenario agents that need it."""
        from src.core.rag_engine import RAGEngine

        rag = RAGEngine(
            qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        await rag.connect()
        return await rag.search(
            query=query,
            tenant_id=tenant_id,
            space_id=space_id or None,
            user_id=user_id or None,
            limit=10,
        )

    async def _run_insight_agent(
        self,
        tenant_id: str,
        space_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run InsightAgent.ask() with query from context or default."""
        from src.core.rag_engine import RAGEngine
        from src.agents.insight import InsightAgent

        rag = RAGEngine(
            qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        await rag.connect()
        agent = InsightAgent(rag)
        query = context.get("query") or context.get("insight_query") or "Summarize my recent activity and upcoming obligations."
        answer = await agent.ask(tenant_id=tenant_id, space_id=space_id or "all", query=query)
        return {
            "ok": True,
            "answer": answer.answer,
            "sources": answer.sources,
            "needs_external_info": answer.needs_external_info,
        }


_orchestrator: ScenarioOrchestrator | None = None


def get_scenario_orchestrator() -> ScenarioOrchestrator:
    """Singleton ScenarioOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ScenarioOrchestrator()
    return _orchestrator
