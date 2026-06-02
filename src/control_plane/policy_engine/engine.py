from __future__ import annotations

from src.control_plane.policy_engine.evaluator import evaluate_rules
from src.control_plane.policy_engine.registry import RuleRegistry
from src.control_plane.policy_engine.rules import RuleAction


class PolicyEngine:
    def __init__(self, registry: RuleRegistry) -> None:
        self._registry = registry

    def decide(self, resource_type: str, context: dict[str, object]) -> RuleAction:
        rules = self._registry.rules_for(resource_type)
        return evaluate_rules(rules, resource_type, context)
