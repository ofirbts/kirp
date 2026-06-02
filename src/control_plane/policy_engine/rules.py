from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuleAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    effect: RuleAction
    resource_type: str
    required_keys: frozenset[str]


def rule_matches(rule: Rule, resource_type: str, present_keys: frozenset[str]) -> bool:
    if rule.resource_type != resource_type:
        return False
    return rule.required_keys <= present_keys
