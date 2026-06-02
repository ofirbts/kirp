from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Callable

from src.kirp_policy_lib.core.engine import PolicyEngine
from src.kirp_policy_lib.core.policy import Policy, default_builtin_policy
from src.kirp_policy_lib.core.rules import Rule
from src.kirp_policy_lib.model.decision import EvaluationConfig, EvaluationDecision, PolicyResult, Verdict
from src.kirp_policy_lib.model.request import RequestEnvelope
from src.kirp_policy_lib.model.tenant import TenantContext, resolve_tenant_context
from src.kirp_policy_lib.tracing.graph import DecisionTrace, DecisionTraceBuilder

LegacyRuleFn = Callable[[Mapping[str, object], str | None, EvaluationConfig], PolicyResult | None]


def _request_dict_for_legacy(envelope: RequestEnvelope) -> dict[str, object]:
    d: dict[str, object] = {"method": envelope.method, "path": envelope.path, "roles": list(envelope.roles)}
    if envelope.explicit_mutating is not None:
        d["mutating"] = envelope.explicit_mutating
    d.update(dict(envelope.extras))
    return d


def evaluate_envelope(
    envelope: RequestEnvelope,
    tenant_ctx: TenantContext,
    *,
    trace_id: str,
    config: EvaluationConfig | None = None,
    policy: Policy | None = None,
    extra_rules: tuple[Rule, ...] = (),
) -> tuple[EvaluationDecision, DecisionTrace]:
    cfg = config or EvaluationConfig()
    eng = PolicyEngine(policy)
    return eng.evaluate(envelope, tenant_ctx, cfg, trace_id, extra_rules=extra_rules)


def evaluate_request_like(
    request_like: Mapping[str, object],
    *,
    trace_id: str,
    config: EvaluationConfig | None = None,
    policy: Policy | None = None,
    extra_rules: Sequence[LegacyRuleFn] | None = None,
    decision_log: object | None = None,
    use_builtin_rules: bool = True,
) -> EvaluationDecision:
    from src.kirp_policy_lib.decision_log import InMemoryDecisionLog

    cfg = config or EvaluationConfig()
    envelope = RequestEnvelope.from_mapping(request_like, mutation_methods=cfg.mutation_methods)
    tenant_ctx = resolve_tenant_context(request_like)
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
    for fn in extra_rules or ():
        req_d = _request_dict_for_legacy(envelope)
        pr = fn(req_d, tenant_ctx.tenant_id, cfg)
        builder.emit("legacy_rule", invoked=True, returned=pr is not None, rule_id=getattr(pr, "rule_id", None))
        if pr is not None and pr.matched and pr.effect == Verdict.DENY:
            builder.emit("aggregate", matched_count=1)
            builder.emit("final", verdict=Verdict.DENY.value, reason=pr.rule_id)
            trace = builder.build(Verdict.DENY.value, pr.rule_id)
            decision = EvaluationDecision(
                verdict=Verdict.DENY,
                reason=pr.rule_id,
                tenant_id=tenant_ctx.tenant_id,
                policy_results=(pr,),
                trace_id=trace_id,
            )
            if decision_log is not None and isinstance(decision_log, InMemoryDecisionLog):
                decision_log.append_trace(trace, tenant_ctx.tenant_id, decision.verdict.value)
            return decision
    if not use_builtin_rules:
        builder.emit("aggregate", matched_count=0)
        builder.emit("final", verdict=Verdict.DENY.value, reason="default_deny")
        trace = builder.build(Verdict.DENY.value, "default_deny")
        decision = EvaluationDecision(
            verdict=Verdict.DENY,
            reason="default_deny",
            tenant_id=tenant_ctx.tenant_id,
            policy_results=(),
            trace_id=trace_id,
        )
        if decision_log is not None and isinstance(decision_log, InMemoryDecisionLog):
            decision_log.append_trace(trace, tenant_ctx.tenant_id, decision.verdict.value)
        return decision
    pol = policy if policy is not None else default_builtin_policy()
    eng = PolicyEngine(pol)
    decision, trace = eng.evaluate(envelope, tenant_ctx, cfg, trace_id, extra_rules=())
    if decision_log is not None and isinstance(decision_log, InMemoryDecisionLog):
        decision_log.append_trace(trace, tenant_ctx.tenant_id, decision.verdict.value)
    return decision
