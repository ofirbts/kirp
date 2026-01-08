from typing import Dict, List


class PolicyViolation(Exception):
    pass


DEFAULT_POLICY = {
    "allowed_intents": ["pricing", "reason", "research", "summarize"],
    "allowed_tools": ["rag", "memory", "analysis"],
    "max_steps": 5,
    "require_explanation": True,
}


def enforce_policy(
    plan: Dict,
    policy: Dict = DEFAULT_POLICY
) -> None:
    intents = plan.get("intents", [])
    tools = plan.get("tools", [])
    steps = plan.get("steps", [])

    for intent in intents:
        if intent not in policy["allowed_intents"]:
            raise PolicyViolation(f"Intent '{intent}' not allowed")

    for tool in tools:
        if tool not in policy["allowed_tools"]:
            raise PolicyViolation(f"Tool '{tool}' not allowed")

    if len(steps) > policy["max_steps"]:
        raise PolicyViolation("Plan exceeds max allowed steps")

    if policy["require_explanation"] and not plan.get("explanation"):
        raise PolicyViolation("Explanation required by policy")
