from typing import Dict
from app.policies.policy_engine import enforce_policy, PolicyViolation


class PlannerAgent:
    """
    Very simple planner stub.

    In the future, this can become a proper planning LLM that decides
    between actions (search, write, call tool, etc.). For now, it just
    says: "answer the question".
    """

    def plan(self, question: str) -> Dict[str, str]:
        plan = {
            "action": "answer",
            "query": question,
        }

        # Enforce policy before returning the plan
        enforce_policy(plan)

        return plan
