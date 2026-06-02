from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.kirp_policy_lib.model.decision import EvaluationConfig, Verdict
from src.kirp_policy_lib.model.request import OperationType, RequestEnvelope
from src.kirp_policy_lib.model.tenant import TenantContext


Matcher = Callable[[RequestEnvelope, TenantContext, EvaluationConfig], bool]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    priority: int
    group_id: str
    reason_code: str
    effect: Verdict
    matcher: Matcher


@dataclass(frozen=True)
class RuleGroup:
    group_id: str
    rules: tuple[Rule, ...]


def _match_wildcard(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
    _ = env
    if not cfg.deny_wildcard_tenant:
        return False
    return tc.tenant_id is not None and tc.tenant_id.strip() == "*"


def _match_mutation_no_tenant(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
    if env.operation != OperationType.MUTATION:
        return False
    if not cfg.require_tenant_for_mutations:
        return False
    return tc.tenant_id is None or not str(tc.tenant_id).strip()


def _match_mutation_ok(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
    if env.operation != OperationType.MUTATION:
        return False
    if not cfg.require_tenant_for_mutations:
        return False
    return tc.tenant_id is not None and bool(str(tc.tenant_id).strip()) and tc.tenant_id.strip() != "*"


def _match_mutation_optional_ok(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
    _ = tc
    if env.operation != OperationType.MUTATION:
        return False
    return not cfg.require_tenant_for_mutations


def _match_read_deny(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
    if env.operation != OperationType.READ:
        return False
    if cfg.allow_read_without_tenant:
        return False
    return tc.tenant_id is None or not str(tc.tenant_id).strip()


def _match_read_allow(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
    if env.operation != OperationType.READ:
        return False
    if not cfg.allow_read_without_tenant:
        return tc.tenant_id is not None and bool(str(tc.tenant_id).strip())
    return True


def _match_unknown_deny(env: RequestEnvelope, tc: TenantContext, cfg: EvaluationConfig) -> bool:
    _ = tc, cfg
    return env.operation == OperationType.UNKNOWN


def builtin_rule_groups() -> tuple[RuleGroup, ...]:
    return (
        RuleGroup(
            "builtin",
            (
                Rule("mutation_tenant_required", 8500, "builtin", "mutation_tenant_required", Verdict.DENY, _match_mutation_no_tenant),
                Rule("wildcard_tenant", 8400, "builtin", "wildcard_tenant", Verdict.DENY, _match_wildcard),
                Rule("mutation_tenant_present", 7000, "builtin", "mutation_tenant_present", Verdict.ALLOW, _match_mutation_ok),
                Rule("mutation_tenant_optional", 6500, "builtin", "mutation_tenant_optional", Verdict.ALLOW, _match_mutation_optional_ok),
                Rule("read_requires_tenant", 3000, "builtin", "read_requires_tenant", Verdict.DENY, _match_read_deny),
                Rule("read_path", 500, "builtin", "read_path", Verdict.ALLOW, _match_read_allow),
                Rule("unknown_operation", 100, "builtin", "unknown_operation", Verdict.DENY, _match_unknown_deny),
            ),
        ),
    )
