"""
Meta Agent — Orchestrates all agents.

Routes requests to optimal agents with decision trees, scoring, and multi-agent coordination.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.core.agent_framework import AgentFramework, AgentSpec, AutonomyLevel
from src.core.llm_router import get_llm_for_task

logger = logging.getLogger(__name__)


class MetaAgent:
    """
    Orchestrates all agents with intelligent routing.
    Uses decision trees, agent scoring, and LLM-based routing.
    """

    def __init__(self, agent_framework: AgentFramework) -> None:
        self._framework = agent_framework
        # Orchestrator uses critical-grade provider (high reliability).
        self._llm = get_llm_for_task("critical")
        self._agent_scores: dict[str, float] = {}  # Agent name -> success score (0-1)

    def _score_agent(self, agent_name: str, success: bool) -> None:
        """Update agent success score (exponential moving average)."""
        current_score = self._agent_scores.get(agent_name, 0.5)
        alpha = 0.1  # Learning rate
        new_score = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_score
        self._agent_scores[agent_name] = new_score

    def _decision_tree_routing(self, query: str, agents: list[AgentSpec]) -> list[str]:
        """
        Simple decision tree for common patterns.
        Returns list of candidate agent names.
        """
        query_lower = query.lower()
        candidates = []
        
        # Pattern matching
        if any(word in query_lower for word in ["plan", "today", "tomorrow", "schedule", "action"]):
            candidates.append("TodayTomorrowPlannerAgent")
        
        if any(word in query_lower for word in ["risk", "opportunity", "follow", "missed"]):
            candidates.append("RiskOpportunityAgent")
        
        if any(word in query_lower for word in ["forecast", "predict", "bottleneck", "load"]):
            candidates.append("ForecasterAgent")
        
        if any(word in query_lower for word in ["pattern", "habit", "recurring", "trend"]):
            candidates.append("PatternAnalyzerAgent")
        
        if any(word in query_lower for word in ["task", "project", "schema", "structure"]):
            candidates.append("SchemaStructureAgent")
        
        if any(word in query_lower for word in ["view", "kanban", "timeline", "calendar", "mindmap"]):
            candidates.append("PresentationAgent")
        
        if any(word in query_lower for word in ["improve", "learn", "optimize", "better"]):
            candidates.append("SelfImprovementAgent")
        
        return candidates

    async def route(
        self,
        query: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Route query to optimal agent(s) using decision trees + LLM + scoring.
        Enforces multi-tenant isolation.
        """
        # Enforce multi-tenant isolation
        if not tenant_id or tenant_id == "*":
            return {"ok": False, "error": "tenant_id is required (multi-tenant isolation)"}
        
        agents = self._framework.list_all()
        
        # Step 1: Decision tree routing (fast path)
        decision_tree_candidates = self._decision_tree_routing(query, agents)
        
        # Step 2: Score agents by historical performance
        scored_agents = []
        for agent in agents:
            score = self._agent_scores.get(agent.name, 0.5)
            if agent.name in decision_tree_candidates:
                score += 0.2  # Boost decision tree matches
            scored_agents.append((agent.name, score, agent))
        
        # Sort by score
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Step 3: LLM-based routing for final decision
        agent_descriptions = "\n".join(
            f"- {a.name}: {a.description} (triggers: {', '.join(a.triggers)}, score: {self._agent_scores.get(a.name, 0.5):.2f})"
            for a in agents
        )

        routing_prompt = f"""
You are the Meta Agent orchestrator for KIRP Enterprise.

Available agents (with historical scores):
{agent_descriptions}

User query: {query}

Decision tree candidates: {', '.join(decision_tree_candidates) if decision_tree_candidates else 'none'}

Which agent(s) should handle this? Consider:
1. Agent capabilities and triggers
2. Historical success scores
3. Query intent and keywords

Return JSON:
{{
  "primary_agent": "AgentName",
  "secondary_agents": ["AgentName1", "AgentName2"],
  "reason": "why this routing",
  "confidence": 0.0-1.0
}}
"""

        try:
            response = await self._llm.invoke(routing_prompt, temperature=0.3, max_tokens=500)
            
            # Parse JSON
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            routing = json.loads(response_text)
            primary = routing.get("primary_agent", "")
            secondary = routing.get("secondary_agents", [])
            confidence = routing.get("confidence", 0.5)

            # Run primary agent
            result: dict[str, Any] = {
                "ok": True,
                "routing": routing,
                "results": {},
                "confidence": confidence,
            }
            
            if primary:
                try:
                    agent_result = await self._framework.run(
                        primary, tenant_id=tenant_id, space_id=space_id, user_id=user_id, context=context
                    )
                    result["results"][primary] = agent_result
                    # Update score based on success
                    self._score_agent(primary, agent_result.get("ok", False))
                except Exception as e:
                    logger.error("Primary agent %s failed: %s", primary, e)
                    result["results"][primary] = {"ok": False, "error": str(e)}
                    self._score_agent(primary, False)

            # Run secondary agents (if confidence is high enough)
            if confidence >= 0.6:
                for agent_name in secondary[:2]:  # Limit to 2 secondary agents
                    if agent_name != primary:
                        try:
                            agent_result = await self._framework.run(
                                agent_name, tenant_id=tenant_id, space_id=space_id, user_id=user_id, context=context
                            )
                            result["results"][agent_name] = agent_result
                            self._score_agent(agent_name, agent_result.get("ok", False))
                        except Exception as e:
                            logger.warning("Secondary agent %s failed: %s", agent_name, e)
                            result["results"][agent_name] = {"ok": False, "error": str(e)}
                            self._score_agent(agent_name, False)

            return result
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM routing response: %s", e)
            # Fallback to decision tree
            if decision_tree_candidates:
                primary = decision_tree_candidates[0]
                agent_result = await self._framework.run(
                    primary, tenant_id=tenant_id, space_id=space_id, user_id=user_id, context=context
                )
                return {
                    "ok": True,
                    "routing": {"primary_agent": primary, "reason": "decision_tree_fallback"},
                    "results": {primary: agent_result},
                    "confidence": 0.5,
                }
            return {"ok": False, "error": "Routing failed: invalid LLM response"}
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
