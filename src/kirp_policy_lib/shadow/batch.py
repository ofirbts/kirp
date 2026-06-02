from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.kirp_policy_lib.core.engine import PolicyEngine
from src.kirp_policy_lib.core.policy import Policy
from src.kirp_policy_lib.model.decision import EvaluationConfig, EvaluationDecision
from src.kirp_policy_lib.model.request import RequestEnvelope
from src.kirp_policy_lib.model.tenant import TenantContext
from src.kirp_policy_lib.tracing.graph import DecisionTrace


def evaluate_many(
    cases: tuple[tuple[str, RequestEnvelope, TenantContext], ...],
    *,
    config: EvaluationConfig | None = None,
    policy: Policy | None = None,
) -> tuple[tuple[str, EvaluationDecision, DecisionTrace], ...]:
    cfg = config or EvaluationConfig()
    eng = PolicyEngine(policy)
    out: list[tuple[str, EvaluationDecision, DecisionTrace]] = []
    for case_id, env, tc in cases:
        dec, tr = eng.evaluate(env, tc, cfg, trace_id=f"batch:{case_id}")
        out.append((case_id, dec, tr))
    return tuple(out)


@dataclass(frozen=True)
class RegressionDiffReport:
    only_in_baseline: frozenset[str]
    only_in_current: frozenset[str]
    changed: tuple[tuple[str, str, str, str, str], ...]


def regression_compare(
    baseline: Mapping[str, tuple[str, str]],
    current: Mapping[str, tuple[str, str]],
) -> RegressionDiffReport:
    bk = frozenset(baseline)
    ck = frozenset(current)
    changed: list[tuple[str, str, str, str, str]] = []
    for k in bk & ck:
        b = baseline[k]
        c = current[k]
        if b != c:
            changed.append((k, b[0], c[0], b[1], c[1]))
    return RegressionDiffReport(
        only_in_baseline=bk - ck,
        only_in_current=ck - bk,
        changed=tuple(changed),
    )


def format_diff_report(report: RegressionDiffReport) -> str:
    lines: list[str] = []
    if report.only_in_baseline:
        lines.append("only_in_baseline:" + ",".join(sorted(report.only_in_baseline)))
    if report.only_in_current:
        lines.append("only_in_current:" + ",".join(sorted(report.only_in_current)))
    for row in report.changed:
        lines.append(f"changed:{row[0]}:{row[1]}->{row[2]}:{row[3]}->{row[4]}")
    return "\n".join(lines) if lines else "no_diff"


def snapshots_from_batch(
    batch: tuple[tuple[str, EvaluationDecision, DecisionTrace], ...],
) -> dict[str, tuple[str, str, str | None]]:
    return {cid: (d.verdict.value, d.reason, d.tenant_id) for cid, d, _ in batch}
