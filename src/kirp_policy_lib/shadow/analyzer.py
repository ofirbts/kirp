from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.kirp_policy_lib.core.evaluator import evaluate_request_like
from src.kirp_policy_lib.model.decision import EvaluationConfig, EvaluationDecision, Verdict


@dataclass(frozen=True)
class StaticRouteDefinition:
    name: str
    method: str
    path: str
    mutating: bool


@dataclass(frozen=True)
class ShadowRow:
    route_name: str
    method: str
    path: str
    context_label: str
    verdict: Verdict
    reason: str
    tenant_id: str | None


def _merge_request_like(
    route: StaticRouteDefinition,
    partial: Mapping[str, Any],
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "method": route.method,
        "path": route.path,
        "mutating": route.mutating,
    }
    for k, v in partial.items():
        base[k] = v
    return base


def shadow_analyze(
    routes: tuple[StaticRouteDefinition, ...],
    labeled_contexts: tuple[tuple[str, Mapping[str, Any]], ...],
    *,
    config: EvaluationConfig | None = None,
) -> tuple[ShadowRow, ...]:
    rows: list[ShadowRow] = []
    cfg = config or EvaluationConfig()
    for route in routes:
        for label, partial in labeled_contexts:
            req = _merge_request_like(route, partial)
            dec: EvaluationDecision = evaluate_request_like(
                req,
                trace_id=f"shadow:{route.name}:{label}",
                config=cfg,
            )
            rows.append(
                ShadowRow(
                    route_name=route.name,
                    method=route.method,
                    path=route.path,
                    context_label=label,
                    verdict=dec.verdict,
                    reason=dec.reason,
                    tenant_id=dec.tenant_id,
                )
            )
    return tuple(rows)
