from __future__ import annotations

from src.kirp_policy_lib.core.rules import Rule
from src.kirp_policy_lib.model.decision import EvaluationConfig, Verdict
from src.kirp_policy_lib.model.request import RequestEnvelope
from src.kirp_policy_lib.model.tenant import TenantContext


def rule_deny_path_prefix(
    rule_id: str,
    group_id: str,
    priority: int,
    path_prefix: str,
    *,
    reason_code: str | None = None,
) -> Rule:
    rc = reason_code or rule_id

    def matcher(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
        _ = tc, cfg
        return env.path.startswith(path_prefix)

    return Rule(rule_id, priority, group_id, rc, Verdict.DENY, matcher)


def rule_deny_method_in(
    rule_id: str,
    group_id: str,
    priority: int,
    methods: frozenset[str],
    *,
    reason_code: str | None = None,
) -> Rule:
    rc = reason_code or rule_id
    upper = frozenset(m.upper() for m in methods)

    def matcher(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
        _ = tc, cfg
        return env.method.upper() in upper

    return Rule(rule_id, priority, group_id, rc, Verdict.DENY, matcher)


def rule_deny_path_unless_any_role(
    rule_id: str,
    group_id: str,
    priority: int,
    path_prefix: str,
    required_any: frozenset[str],
    *,
    reason_code: str | None = None,
) -> Rule:
    rc = reason_code or rule_id
    req = frozenset(r.lower() for r in required_any)

    def matcher(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
        _ = tc, cfg
        if not env.path.startswith(path_prefix):
            return False
        have = frozenset(env.roles)
        return have.isdisjoint(req)

    return Rule(rule_id, priority, group_id, rc, Verdict.DENY, matcher)
