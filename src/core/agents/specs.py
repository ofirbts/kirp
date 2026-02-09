"""AgentSpec entries for Phase 5 agents (Planner, InsightV2, ReminderV2, Execution, Overload, Conflict)."""

from __future__ import annotations

from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel
from src.core.agent_actions import get_agent_actions_store, action_doc


async def _run_base_agent(agent_name: str, tenant_id: str, space_id: str, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
    from src.core.agents.planner_agent import PlannerAgent
    from src.core.agents.insight_agent_v2 import InsightAgentV2
    from src.core.agents.reminder_agent_v2 import ReminderAgentV2
    from src.core.agents.execution_agent import ExecutionAgent
    from src.core.agents.overload_agent import OverloadAgent
    from src.core.agents.conflict_agent import ConflictAgent

    agents = {
        "PlannerAgent": PlannerAgent(),
        "InsightAgentV2": InsightAgentV2(),
        "ReminderAgentV2": ReminderAgentV2(),
        "ExecutionAgent": ExecutionAgent(),
        "OverloadAgent": OverloadAgent(),
        "ConflictAgent": ConflictAgent(),
    }
    agent = agents.get(agent_name)
    if not agent:
        return {"ok": False, "error": f"Unknown agent: {agent_name}"}
    result = await agent.run(tenant_id=tenant_id, space_id=space_id, user_id=user_id, context=context)
    actions = result.get("actions", [])
    if actions:
        store = get_agent_actions_store()
        await store.connect()
        docs = []
        for a in actions:
            if isinstance(a, dict) and a.get("id") and a.get("type"):
                docs.append(a)
            elif isinstance(a, dict):
                docs.append(action_doc(a.get("agent", agent_name), a.get("type", ""), a.get("payload", {}), tenant_id, space_id, user_id))
        if docs:
            await store.create_many(docs)
    return result


def _handler(agent_name: str):
    async def h(tenant_id: str, space_id: str, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        return await _run_base_agent(agent_name, tenant_id, space_id, user_id, context)
    return h


planner_agent_spec = AgentSpec(
    name="PlannerAgent",
    type="planner",
    triggers=["scheduled", "manual", "plan_request"],
    tools=["schema", "graph"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Produces daily plan, weekly plan, and suggested priorities from tasks and commitments.",
    handler=_handler("PlannerAgent"),
)

insight_agent_v2_spec = AgentSpec(
    name="InsightAgentV2",
    type="insight",
    triggers=["scheduled", "manual", "new_event"],
    tools=["insights_engine", "graph"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Deeper insights and cross-entity reasoning from InsightsEngine and Life Graph.",
    handler=_handler("InsightAgentV2"),
)

reminder_agent_v2_spec = AgentSpec(
    name="ReminderAgentV2",
    type="reminder",
    triggers=["scheduled", "reminder", "manual"],
    tools=["schema"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Detects upcoming deadlines and overdue items; suggests reschedule.",
    handler=_handler("ReminderAgentV2"),
)

execution_agent_spec = AgentSpec(
    name="ExecutionAgent",
    type="execution",
    triggers=["scheduled", "manual", "after_agent"],
    tools=["agent_actions", "schema", "execution_engine"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Executes queued actions: create_task, update_task, send_notification, send_message.",
    handler=_handler("ExecutionAgent"),
)

overload_agent_spec = AgentSpec(
    name="OverloadAgent",
    type="overload",
    triggers=["scheduled", "manual"],
    tools=["schema", "graph"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Detects workload overload, too many active projects, and too many commitments.",
    handler=_handler("OverloadAgent"),
)

conflict_agent_spec = AgentSpec(
    name="ConflictAgent",
    type="conflict",
    triggers=["scheduled", "manual", "new_commitment"],
    tools=["schema"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Detects schedule conflicts, double-bookings, and impossible deadlines.",
    handler=_handler("ConflictAgent"),
)

PHASE5_AGENT_SPECS = [
    planner_agent_spec,
    insight_agent_v2_spec,
    reminder_agent_v2_spec,
    execution_agent_spec,
    overload_agent_spec,
    conflict_agent_spec,
]
