from app.agent.tools import TOOL_REGISTRY
from app.agent.agent import agent

class ToolAgent:
    def run(self, query):
        if "calculate" in query:
            expr = query.replace("calculate", "").strip()
            return TOOL_REGISTRY["calc"](expr)

        if "search" in query:
            q = query.replace("search", "").strip()
            return TOOL_REGISTRY["search"](q)

        return agent.query(query)
