"""
Agent Framework — Registry, triggers, autonomy levels.

AgentSpec: name, type, triggers, tools, autonomy, tenant_scopes.
Flow: Event → RAG → Agent Decision → Governance → Execution → Event.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

from src.core.agent_validation import normalize_agent_output
from src.observability.metrics import MetricsCollector

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
    # Orchestration hints
    max_retries: int = 0
    backoff_seconds: float = 0.0
    timeout_seconds: float = 0.0


class AgentFramework:
    """
    Agent registry and dispatch. Triggers agents from events.
    """

    def __init__(self) -> None:
        self._registry: dict[str, AgentSpec] = {}
        self._metrics = MetricsCollector("kirp_agents")

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

        if not spec.handler:
            logger.info("Agent %s has no handler; returning no-op result", spec.name)
            return {"ok": True, "message": f"Agent {agent_name} (no handler)"}

        max_retries = spec.max_retries or 0
        backoff = float(spec.backoff_seconds or 0.0)
        timeout = float(spec.timeout_seconds or 0.0)

        attempt = 0
        last_error: Exception | None = None

        while True:
            attempt += 1
            started = time.perf_counter()
            try:
                if timeout > 0:
                    result = await asyncio.wait_for(
                        spec.handler(
                            tenant_id=tenant_id,
                            space_id=space_id,
                            user_id=user_id,
                            context=context,
                        ),
                        timeout=timeout,
                    )
                else:
                    result = await spec.handler(
                        tenant_id=tenant_id,
                        space_id=space_id,
                        user_id=user_id,
                        context=context,
                    )

                # Validate and normalize output
                result = normalize_agent_output(agent_name, result)

                latency = time.perf_counter() - started
                self._metrics.inc(
                    "runs_total",
                    labels={
                        "agent": agent_name,
                        "tenant_id": tenant_id,
                        "space_id": space_id,
                        "status": "success",
                    },
                )
                self._metrics.observe(
                    "latency_seconds",
                    latency,
                    labels={"agent": agent_name, "tenant_id": tenant_id, "space_id": space_id},
                )
                return result
            except Exception as e:
                last_error = e
                latency = time.perf_counter() - started
                logger.warning(
                    "Agent %s failed on attempt %d/%d for tenant=%s space=%s: %s",
                    agent_name,
                    attempt,
                    max_retries + 1,
                    tenant_id,
                    space_id,
                    e,
                )
                self._metrics.inc(
                    "runs_total",
                    labels={
                        "agent": agent_name,
                        "tenant_id": tenant_id,
                        "space_id": space_id,
                        "status": "error",
                    },
                )
                self._metrics.observe(
                    "latency_seconds",
                    latency,
                    labels={"agent": agent_name, "tenant_id": tenant_id, "space_id": space_id},
                )
                if attempt > max_retries:
                    logger.error("Agent %s exhausted retries: %s", agent_name, e)
                    return {"ok": False, "error": str(e)}
                if backoff > 0:
                    sleep_for = backoff * (2 ** (attempt - 1))
                    await asyncio.sleep(sleep_for)
