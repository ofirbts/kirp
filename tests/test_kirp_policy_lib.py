from __future__ import annotations

from src.kirp_policy_lib import (
    EvaluationConfig,
    InMemoryDecisionLog,
    Policy,
    PolicyEngine,
    PolicyResult,
    RequestEnvelope,
    Rule,
    RuleGroup,
    TenantContext,
    Verdict,
    default_builtin_policy,
    evaluate_envelope,
    evaluate_many,
    evaluate_request_like,
    extract_tenant_id,
    flatten_trace_to_rows,
    format_diff_report,
    merge_policies,
    policy_from_groups,
    regression_compare,
    resolve_tenant_context,
    rule_deny_path_unless_any_role,
    shadow_analyze,
    snapshots_from_batch,
    trace_ordered_steps,
)
from src.kirp_policy_lib.shadow.analyzer import StaticRouteDefinition


def test_extract_top_level_tenant_wins_over_auth() -> None:
    req = {"tenant_id": "top", "auth": {"tenant_id": "auth"}}
    assert extract_tenant_id(req) == "top"


def test_extract_auth_when_no_top_level() -> None:
    req = {"auth": {"tenant_id": "a1"}}
    assert extract_tenant_id(req) == "a1"


def test_extract_jwt_alias() -> None:
    req = {"jwt": {"tenant_id": "j1"}}
    assert extract_tenant_id(req) == "j1"


def test_extract_header_case_insensitive() -> None:
    req = {"headers": {"X-Tenant-ID": "h1"}}
    assert extract_tenant_id(req) == "h1"


def test_extract_body_last() -> None:
    req = {"body": {"tenant_id": "b1"}}
    assert extract_tenant_id(req) == "b1"


def test_extract_none_when_missing() -> None:
    assert extract_tenant_id({}) is None


def test_resolve_tenant_context_provenance() -> None:
    tc = resolve_tenant_context({"auth": {"tenant_id": "z"}})
    assert tc.tenant_id == "z"
    assert tc.provenance == "auth"


def test_evaluate_mutation_denies_without_tenant() -> None:
    d = evaluate_request_like(
        {"method": "POST", "path": "/x"},
        trace_id="t1",
    )
    assert d.verdict == Verdict.DENY
    assert d.reason == "mutation_tenant_required"
    assert d.tenant_id is None


def test_evaluate_mutation_allows_with_tenant() -> None:
    d = evaluate_request_like(
        {"method": "POST", "tenant_id": "acme", "path": "/x"},
        trace_id="t2",
    )
    assert d.verdict == Verdict.ALLOW
    assert d.tenant_id == "acme"


def test_evaluate_read_allows_without_tenant_by_default() -> None:
    d = evaluate_request_like({"method": "GET"}, trace_id="t3")
    assert d.verdict == Verdict.ALLOW
    assert d.reason == "read_path"


def test_evaluate_read_denies_when_config_requires_tenant() -> None:
    cfg = EvaluationConfig(allow_read_without_tenant=False)
    d = evaluate_request_like({"method": "GET"}, trace_id="t4", config=cfg)
    assert d.verdict == Verdict.DENY
    assert d.reason == "read_requires_tenant"


def test_evaluate_wildcard_tenant_denied() -> None:
    d = evaluate_request_like(
        {"method": "POST", "tenant_id": "*"},
        trace_id="t5",
    )
    assert d.verdict == Verdict.DENY
    assert d.reason == "wildcard_tenant"


def test_extra_rule_deny_first() -> None:
    def deny_admin_path(
        req: dict,
        _tenant: str | None,
        _cfg: EvaluationConfig,
    ) -> PolicyResult | None:
        if str(req.get("path", "")).startswith("/admin"):
            return PolicyResult("block_admin", True, Verdict.DENY)
        return None

    d = evaluate_request_like(
        {"method": "GET", "path": "/admin/users", "tenant_id": "t"},
        trace_id="t6",
        extra_rules=(deny_admin_path,),
    )
    assert d.verdict == Verdict.DENY
    assert d.reason == "block_admin"


def test_decision_log_records_trace() -> None:
    log = InMemoryDecisionLog(max_entries=5)
    evaluate_request_like({"method": "GET"}, trace_id="tr-1", decision_log=log)
    assert len(log) == 1
    e = log.entries()[0]
    assert e.trace_id == "tr-1"
    assert e.decision == "ALLOW"
    assert e.tenant_id is None
    assert e.trace.root.step == "evaluation"
    steps = trace_ordered_steps(e.trace.root)
    assert "envelope" in steps
    assert "rule_eval" in steps


def test_builtin_off_default_deny() -> None:
    d = evaluate_request_like({"method": "GET"}, trace_id="z", use_builtin_rules=False)
    assert d.verdict == Verdict.DENY
    assert d.reason == "default_deny"


def test_shadow_analyzer_matrix() -> None:
    routes = (
        StaticRouteDefinition("create_item", "POST", "/api/v1/items", True),
        StaticRouteDefinition("list_items", "GET", "/api/v1/items", False),
    )
    contexts = (
        ("no_tenant", {}),
        ("with_tenant", {"tenant_id": "acme"}),
    )
    rows = shadow_analyze(routes, contexts)
    assert len(rows) == 4
    post_no = next(r for r in rows if r.route_name == "create_item" and r.context_label == "no_tenant")
    assert post_no.verdict == Verdict.DENY
    post_ok = next(r for r in rows if r.route_name == "create_item" and r.context_label == "with_tenant")
    assert post_ok.verdict == Verdict.ALLOW
    get_no = next(r for r in rows if r.route_name == "list_items" and r.context_label == "no_tenant")
    assert get_no.verdict == Verdict.ALLOW


def test_custom_rule_priority_overrides_read() -> None:
    from src.kirp_policy_lib.core.rules import builtin_rule_groups

    def deny_paths(env: RequestEnvelope, tc: TenantContext, _cfg: EvaluationConfig) -> bool:
        _ = env, tc
        return True

    hi = Rule("always_deny", 90000, "custom", "forced", Verdict.DENY, deny_paths)
    pol = Policy((RuleGroup("g", (hi,)),) + builtin_rule_groups())
    eng = PolicyEngine(pol)
    env = RequestEnvelope.from_mapping({"method": "GET", "path": "/"})
    dec, tr = eng.evaluate(env, TenantContext.absent(), EvaluationConfig(), "tp")
    assert dec.verdict == Verdict.DENY
    assert dec.reason == "forced"
    assert "rule_eval" in trace_ordered_steps(tr.root)


def test_evaluate_envelope_returns_trace() -> None:
    env = RequestEnvelope.from_mapping({"method": "POST", "tenant_id": "x", "path": "/p"})
    tc = TenantContext("x", "test")
    dec, tr = evaluate_envelope(env, tc, trace_id="e1")
    assert dec.verdict == Verdict.ALLOW
    assert tr.verdict == "ALLOW"


def test_evaluate_many_batch() -> None:
    cases = (
        ("a", RequestEnvelope.from_mapping({"method": "GET"}), TenantContext.absent()),
        ("b", RequestEnvelope.from_mapping({"method": "POST"}), TenantContext.absent()),
    )
    out = evaluate_many(cases)
    assert len(out) == 2
    assert out[0][0] == "a" and out[0][1].verdict == Verdict.ALLOW
    assert out[1][0] == "b" and out[1][1].verdict == Verdict.DENY


def test_regression_compare_and_format() -> None:
    base = {"x": ("ALLOW", "read_path"), "y": ("DENY", "mutation_tenant_required")}
    cur = {"x": ("DENY", "read_requires_tenant"), "z": ("ALLOW", "read_path")}
    rep = regression_compare(base, cur)
    assert "y" in rep.only_in_baseline
    assert "z" in rep.only_in_current
    assert any(c[0] == "x" for c in rep.changed)
    txt = format_diff_report(rep)
    assert "only_in_baseline" in txt or "only_in_current" in txt or "changed" in txt


def test_request_envelope_roles_from_auth() -> None:
    env = RequestEnvelope.from_mapping({"method": "GET", "path": "/x", "auth": {"roles": ["Admin", "user"]}})
    assert env.roles == ("admin", "user")


def test_rule_deny_admin_path_without_role() -> None:
    r = rule_deny_path_unless_any_role(
        "admin_need_role",
        "sec",
        9200,
        "/admin",
        frozenset({"admin"}),
    )
    pol = merge_policies(policy_from_groups(RuleGroup("sec", (r,))), default_builtin_policy())
    eng = PolicyEngine(pol)
    dec, tr = eng.evaluate(
        RequestEnvelope.from_mapping({"method": "GET", "path": "/admin/users"}),
        TenantContext.absent(),
        EvaluationConfig(),
        "t-admin",
    )
    assert dec.verdict == Verdict.DENY
    rows = flatten_trace_to_rows(tr)
    assert any(row.get("step") == "rule_eval" for row in rows)


def test_admin_path_with_admin_role_allowed() -> None:
    r = rule_deny_path_unless_any_role("admin_need_role", "sec", 9200, "/admin", frozenset({"admin"}))
    pol = merge_policies(policy_from_groups(RuleGroup("sec", (r,))), default_builtin_policy())
    eng = PolicyEngine(pol)
    dec, _tr = eng.evaluate(
        RequestEnvelope.from_mapping({"method": "GET", "path": "/admin", "auth": {"roles": ["admin"]}}),
        TenantContext("t1", "x"),
        EvaluationConfig(),
        "t-admin2",
    )
    assert dec.verdict == Verdict.ALLOW


def test_snapshots_from_batch() -> None:
    cases = (
        ("a", RequestEnvelope.from_mapping({"method": "GET"}), TenantContext.absent()),
        ("b", RequestEnvelope.from_mapping({"method": "POST"}), TenantContext.absent()),
    )
    batch = evaluate_many(cases)
    snap = snapshots_from_batch(batch)
    assert snap["a"][0] == "ALLOW" and snap["b"][0] == "DENY"
