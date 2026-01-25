"""
ToolAgent (Phase 1)

This agent supports tool invocation via simple heuristics.
It does NOT perform autonomous tool selection via LLM policy.
This is intentional and part of the current system contract.
"""

from app.agent.tools import TOOL_REGISTRY
from app.agent.agent import agent

class ToolAgent:
    def run(self, query: str):
        # טיפול בכלי חישוב (calc)
        if "calculate" in query:
            expr = query.replace("calculate", "").strip()
            tool = TOOL_REGISTRY.get("calc")
            if not tool:
                return "Calc tool not registered"
            return tool(expr)

        # טיפול בכלי חיפוש (search)
        if "search" in query:
            q = query.replace("search", "").strip()
            tool = TOOL_REGISTRY.get("search")
            if not tool:
                return "Search tool not registered"
            return tool(q)

        # אם אין התאמה לכלים, עוברים לשאילתה רגילה בסוכן
        return agent.query(query)