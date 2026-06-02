from __future__ import annotations

from src.control_plane.policy_engine.rules import Rule


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: list[Rule] = []

    def register(self, rule: Rule) -> None:
        self._rules.append(rule)

    def all_rules(self) -> tuple[Rule, ...]:
        return tuple(self._rules)

    def rules_for(self, resource_type: str) -> list[Rule]:
        return [r for r in self._rules if r.resource_type == resource_type]
