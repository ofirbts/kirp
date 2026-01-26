"""
Agent Framework — Registry, triggers, autonomy levels.

AgentSpec: name, type, triggers, tools, autonomy, tenant_scopes.
Flow: Event → RAG → Agent Decision → Governance → Execution → Event.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class AutonomyLevel(str, Enum):
    """Governance: optionally require human approval."""

    FULL = "full"           # No approval required
    SEMI = "semi"           # High-risk actions need approval
    HUMAN_IN_LOOP = "human_in_loop"  # All actions need approval


@dataclass
class AgentSpec:
    """Registry entry for a built-in or plugin agent."""

    name: str
    type: str
    triggers: list[str]
    tools: list[str]
    autonomy: AutonomyLevel
    tenant_scopes: list[str]
    description: str = ""
    handler: Callable[..., Awaitable[dict[str, Any]]] | None = None


class AgentFramework:
    """
    Agent registry and dispatch. Triggers agents from events.
    """

    def __init__(self) -> None:
        self._registry: dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> None:
        """Register an agent."""
        self._registry[spec.name] = spec
        logger.info("Agent registered: %s triggers=%s", spec.name, spec.triggers)

    def get(self, name: str) -> AgentSpec | None:
        """Get agent by name."""
        return self._registry.get(name)

    def list_by_trigger(self, trigger: str) -> list[AgentSpec]:
        """List agents that react to a given trigger."""
        return [s for s in self._registry.values() if trigger in s.triggers]

    def list_all(self) -> list[AgentSpec]:
        """List all registered agents."""
        return list(self._registry.values())

    async def run(
        self,
        agent_name: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run an agent by name. Delegates to handler if registered.
        Validates output against JSON schema.
        """
        # Enforce multi-tenant isolation
        if not tenant_id or tenant_id == "*":
            return {"ok": False, "error": "tenant_id is required (multi-tenant isolation)"}
        
        spec = self.get(agent_name)
        if not spec:
            return {"ok": False, "error": f"Agent not found: {agent_name}"}
        if spec.tenant_scopes and tenant_id not in spec.tenant_scopes:
            return {"ok": False, "error": f"Agent {agent_name} not in scope for tenant {tenant_id}"}
        if spec.handler:
            try:
                result = await spec.handler(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id=user_id,
                    context=context,
                )
                
                # Validate and normalize output
                from src.core.agent_validation import normalize_agent_output
                result = normalize_agent_output(agent_name, result)
                
                return result
            except Exception as e:
                logger.exception("Agent %s failed: %s", agent_name, e)
                return {"ok": False, "error": str(e)}
        return {"ok": True, "message": f"Agent {agent_name} (no handler)"}
