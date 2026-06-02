from __future__ import annotations

from src.kirp_policy_lib.core.policy import Policy, default_builtin_policy
from src.kirp_policy_lib.core.rules import Rule
from src.kirp_policy_lib.model.decision import EvaluationConfig, EvaluationDecision, PolicyResult, Verdict
from src.kirp_policy_lib.model.request import RequestEnvelope
from src.kirp_policy_lib.model.tenant import TenantContext
from src.kirp_policy_lib.tracing.graph import DecisionTrace, DecisionTraceBuilder


def _aggregate_matched(matched: list[Rule]) -> tuple[Verdict, str]:
    if not matched:
        return Verdict.DENY, "default_deny"
    denies = [r for r in matched if r.effect == Verdict.DENY]
    if denies:
        denies.sort(key=lambda r: r.priority, reverse=True)
        return Verdict.DENY, denies[0].reason_code
    allows = [r for r in matched if r.effect == Verdict.ALLOW]
    allows.sort(key=lambda r: r.priority, reverse=True)
    return Verdict.ALLOW, allows[0].reason_code


class PolicyEngine:
    def __init__(self, policy: Policy | None = None) -> None:
        self._policy = policy if policy is not None else default_builtin_policy()

    def evaluate(
        self,
        envelope: RequestEnvelope,
        tenant_ctx: TenantContext,
        config: EvaluationConfig,
        trace_id: str,
        extra_rules: tuple[Rule, ...] = (),
    ) -> tuple[EvaluationDecision, DecisionTrace]:
        builder = DecisionTraceBuilder(trace_id)
        builder.emit(
            "envelope",
            method=envelope.method,
            path=envelope.path,
            operation=envelope.operation.value,
        )
        builder.emit(
            "tenant_context",
            tenant_id=tenant_ctx.tenant_id,
            provenance=tenant_ctx.provenance,
        )
        base = list(self._policy.rules_by_priority())
        base.extend(extra_rules)
        rules = tuple(sorted(base, key=lambda r: r.priority, reverse=True))
        matched: list[Rule] = []
        prs: list[PolicyResult] = []
        for r in rules:
            m = r.matcher(envelope, tenant_ctx, config)
            prs.append(PolicyResult(r.rule_id, m, r.effect))
            builder.emit(
                "rule_eval",
                rule_id=r.rule_id,
                group_id=r.group_id,
                priority=r.priority,
                matched=m,
                effect=r.effect.value,
            )
            if m:
                matched.append(r)
        builder.emit("aggregate", matched_count=len(matched))
        verdict, reason = _aggregate_matched(matched)
        builder.emit("final", verdict=verdict.value, reason=reason)
        trace = builder.build(verdict.value, reason)
        decision = EvaluationDecision(
            verdict=verdict,
            reason=reason,
            tenant_id=tenant_ctx.tenant_id,
            policy_results=tuple(prs),
            trace_id=trace_id,
        )
        return decision, trace
