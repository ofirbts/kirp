from __future__ import annotations

from dataclasses import dataclass

from src.kirp_policy_lib.core.rules import Rule, RuleGroup


@dataclass(frozen=True)
class Policy:
    groups: tuple[RuleGroup, ...]

    def rules_by_priority(self) -> tuple[Rule, ...]:
        flat: list[Rule] = []
        for g in self.groups:
            flat.extend(g.rules)
        return tuple(sorted(flat, key=lambda r: r.priority, reverse=True))


def default_builtin_policy() -> Policy:
    from src.kirp_policy_lib.core.rules import builtin_rule_groups

    return Policy(groups=builtin_rule_groups())


def merge_policies(*policies: Policy) -> Policy:
    groups: list[RuleGroup] = []
    for p in policies:
        groups.extend(p.groups)
    return Policy(tuple(groups))


def policy_from_groups(*groups: RuleGroup) -> Policy:
    return Policy(tuple(groups))
