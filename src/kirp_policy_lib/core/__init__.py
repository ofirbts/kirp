from __future__ import annotations

from src.kirp_policy_lib.core.engine import PolicyEngine
from src.kirp_policy_lib.core.evaluator import evaluate_envelope, evaluate_request_like
from src.kirp_policy_lib.core.policy import Policy, default_builtin_policy, merge_policies, policy_from_groups
from src.kirp_policy_lib.core.rule_factories import rule_deny_method_in, rule_deny_path_prefix, rule_deny_path_unless_any_role
from src.kirp_policy_lib.core.rules import Rule, RuleGroup, builtin_rule_groups

__all__ = [
    "Policy",
    "PolicyEngine",
    "Rule",
    "RuleGroup",
    "builtin_rule_groups",
    "default_builtin_policy",
    "evaluate_envelope",
    "evaluate_request_like",
    "merge_policies",
    "policy_from_groups",
    "rule_deny_method_in",
    "rule_deny_path_prefix",
    "rule_deny_path_unless_any_role",
]
