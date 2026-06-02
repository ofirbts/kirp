from __future__ import annotations

from src.control_plane.policy_engine.rules import Rule, RuleAction, rule_matches


def evaluate_rules(rules: list[Rule], resource_type: str, context: dict[str, object]) -> RuleAction:
    present = frozenset(k for k, v in context.items() if v not in (None, "", False))
    matched = [r for r in rules if rule_matches(r, resource_type, present)]
    if any(r.effect == RuleAction.DENY for r in matched):
        return RuleAction.DENY
    if any(r.effect == RuleAction.ALLOW for r in matched):
        return RuleAction.ALLOW
    return RuleAction.DENY
