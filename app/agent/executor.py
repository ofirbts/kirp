# app/agent/executor.py
from typing import Dict, Any


class ExecutorAgent:
    """
    Executor that takes a plan and delegates to the core Agent.

    This makes it easy to later plug in different execution backends or
    add new actions while keeping the Agent's core logic reusable.
    """

    async def execute(self, plan: Dict[str, Any], agent) -> Dict[str, Any]:
        action = plan.get("action")

        if action == "answer":
            query = plan.get("query", "")
            return await agent._execute_query(query)

        # Future actions (e.g. "search_only", "update_memory") can go here.
        return {
            "answer": "Unsupported action in plan.",
            "sources": [],
            "suggestions": [],
            "agent_mode": True,
        }
