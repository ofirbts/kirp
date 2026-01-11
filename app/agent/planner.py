# app/agent/planner.py
from typing import Dict

class PlannerAgent:
    def plan(self, question: str) -> Dict:
        return {
            "action": "answer",
            "query": question,
        }
