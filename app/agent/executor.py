# app/agent/executor.py
from typing import Dict, Any
from app.runtime.sandbox import run_with_timeout


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

            # Wrap the execution inside sandbox timeout
            def step():
                # This is the synchronous wrapper that run_with_timeout expects
                # It calls the async agent method using asyncio.run or loop.run_until_complete
                import asyncio
                return asyncio.run(agent._execute_query(query))

            result = run_with_timeout(step)
            return result

        # Future actions (e.g. "search_only", "update_memory") can go here.
        return {
            "answer": "Unsupported action in plan.",
            "sources": [],
            "suggestions": [],
            "agent_mode": True,
        }
