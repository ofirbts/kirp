# app/agent/planner.py
from typing import Dict


class PlannerAgent:
    """
    Very simple planner stub.

    In the future, this can become a proper planning LLM that decides
    between actions (search, write, call tool, etc.). For now, it just
    says: "answer the question".
    """

    def plan(self, question: str) -> Dict[str, str]:
        return {
            "action": "answer",
            "query": question,
        }
