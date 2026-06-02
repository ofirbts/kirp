from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from src.telemetry.execution_graph import ExecutionGraph
from src.telemetry.trace_reconstructor import TraceTimeline

CANONICAL_STAGE_ORDER: tuple[str, ...] = (
    "kafka_received",
    "kafka_flattened",
    "idempotency_check_start",
    "idempotency_duplicate",
    "event_store_resolved",
    "canonical_event_created",
    "registry_dispatch_start",
    "governance_before",
    "governance_after",
    "agent_detection",
    "rag_before",
    "mongo_before",
)

GOLDEN_PATH_STAGES: tuple[str, ...] = (
    "kafka_received",
    "governance_before",
    "governance_after",
    "rag_before",
    "mongo_before",
)

_STAGE_RANK = {stage: idx for idx, stage in enumerate(CANONICAL_STAGE_ORDER)}


@dataclass(frozen=True)
class OrchestrationViolation:
    kind: str
    message: str
    expected: str | None
    actual: str | None


@dataclass(frozen=True)
class OrchestrationPlan:
    trace_id: str
    tenant_id: str | None
    expected_sequence: tuple[str, ...]
    observed_sequence: tuple[str, ...]
    valid: bool
    complete: bool
    violations: tuple[OrchestrationViolation, ...]
    plan_fingerprint: str


def _rank(stage: str) -> int | None:
    return _STAGE_RANK.get(stage)


def _first_occurrence_order(stages: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for stage in stages:
        if stage in seen:
            continue
        seen.add(stage)
        if _rank(stage) is not None:
            ordered.append(stage)
    return ordered


def _violations_for_order(observed: list[str]) -> list[OrchestrationViolation]:
    violations: list[OrchestrationViolation] = []
    last_rank: int | None = None
    last_stage: str | None = None
    for stage in observed:
        rank = _rank(stage)
        if rank is None:
            continue
        if last_rank is not None and rank < last_rank:
            violations.append(
                OrchestrationViolation(
                    kind="stage_order_violation",
                    message="canonical stage order violated",
                    expected=f"{last_stage} before {stage}",
                    actual=f"{stage} observed before expected position",
                )
            )
        last_rank = rank
        last_stage = stage
    return violations


def _missing_golden_stages(observed_set: set[str]) -> list[OrchestrationViolation]:
    violations: list[OrchestrationViolation] = []
    for stage in GOLDEN_PATH_STAGES:
        if stage not in observed_set:
            violations.append(
                OrchestrationViolation(
                    kind="missing_stage",
                    message="golden path stage missing",
                    expected=stage,
                    actual=None,
                )
            )
    return violations


def _plan_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_timeline_orchestration(
    timeline: TraceTimeline,
    *,
    require_golden_path: bool = True,
) -> OrchestrationPlan:
    observed_all = [s.stage for s in timeline.stages]
    observed_canonical = _first_occurrence_order(observed_all)
    observed_set = set(observed_all)
    violations = _violations_for_order(observed_canonical)
    if require_golden_path:
        violations.extend(_missing_golden_stages(observed_set))
    if "governance_before" in observed_set and "governance_after" in observed_set:
        if observed_all.index("governance_after") < observed_all.index("governance_before"):
            violations.append(
                OrchestrationViolation(
                    kind="governance_pair_violation",
                    message="governance_after precedes governance_before",
                    expected="governance_before then governance_after",
                    actual="reversed",
                )
            )
    complete = all(stage in observed_set for stage in GOLDEN_PATH_STAGES) if require_golden_path else True
    valid = len(violations) == 0
    ordered_violations = tuple(sorted(violations, key=lambda v: (v.kind, v.message)))
    payload = {
        "trace_id": timeline.trace_id,
        "valid": valid,
        "complete": complete,
        "observed_sequence": observed_canonical,
        "violations": [
            {"kind": v.kind, "message": v.message, "expected": v.expected, "actual": v.actual}
            for v in ordered_violations
        ],
    }
    return OrchestrationPlan(
        trace_id=timeline.trace_id,
        tenant_id=timeline.tenant_id,
        expected_sequence=GOLDEN_PATH_STAGES,
        observed_sequence=tuple(observed_canonical),
        valid=valid,
        complete=complete,
        violations=ordered_violations,
        plan_fingerprint=_plan_fingerprint(payload),
    )


def validate_graph_orchestration(
    graph: ExecutionGraph,
    timeline: TraceTimeline,
    *,
    require_golden_path: bool = True,
) -> OrchestrationPlan:
    base = validate_timeline_orchestration(timeline, require_golden_path=require_golden_path)
    extra: list[OrchestrationViolation] = list(base.violations)
    for edge in graph.edges:
        if edge.relationship != "chronological_next":
            continue
        src_rank = _rank(edge.source_stage)
        dst_rank = _rank(edge.target_stage)
        if src_rank is None or dst_rank is None:
            continue
        if dst_rank < src_rank:
            extra.append(
                OrchestrationViolation(
                    kind="graph_edge_violation",
                    message="chronological edge violates canonical order",
                    expected=f"{edge.source_stage} -> forward",
                    actual=f"{edge.source_stage} -> {edge.target_stage}",
                )
            )
    ordered_extra = tuple(sorted(extra, key=lambda v: (v.kind, v.message)))
    valid = len(ordered_extra) == 0
    payload = {
        "trace_id": base.trace_id,
        "valid": valid,
        "complete": base.complete,
        "observed_sequence": list(base.observed_sequence),
        "violations": [
            {"kind": v.kind, "message": v.message, "expected": v.expected, "actual": v.actual}
            for v in ordered_extra
        ],
    }
    return OrchestrationPlan(
        trace_id=base.trace_id,
        tenant_id=base.tenant_id,
        expected_sequence=base.expected_sequence,
        observed_sequence=base.observed_sequence,
        valid=valid,
        complete=base.complete,
        violations=ordered_extra,
        plan_fingerprint=_plan_fingerprint(payload),
    )


def orchestration_plan_to_dict(plan: OrchestrationPlan) -> dict[str, Any]:
    return {
        "trace_id": plan.trace_id,
        "tenant_id": plan.tenant_id,
        "expected_sequence": list(plan.expected_sequence),
        "observed_sequence": list(plan.observed_sequence),
        "valid": plan.valid,
        "complete": plan.complete,
        "plan_fingerprint": plan.plan_fingerprint,
        "total_violations": len(plan.violations),
        "violations": [
            {
                "kind": v.kind,
                "message": v.message,
                "expected": v.expected,
                "actual": v.actual,
            }
            for v in plan.violations
        ],
    }
