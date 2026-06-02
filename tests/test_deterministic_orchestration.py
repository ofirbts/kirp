from __future__ import annotations

import json

from src.telemetry.deterministic_orchestration import (
    orchestration_plan_to_dict,
    validate_graph_orchestration,
    validate_timeline_orchestration,
)
from src.telemetry.execution_graph import build_execution_graph
from src.telemetry.trace_reconstructor import reconstruct_timeline


def _line(trace_id: str, stage: str, ts: str, **meta: object) -> str:
    payload = {
        "event": "telemetry_trace",
        "trace_id": trace_id,
        "stage": stage,
        "timestamp": ts,
    }
    payload.update(meta)
    return json.dumps(payload)


def test_valid_golden_path() -> None:
    lines = [
        _line("tr-orch-1", "kafka_received", "2026-06-02T10:00:01+00:00", event_id="e1"),
        _line("tr-orch-1", "governance_before", "2026-06-02T10:00:02+00:00", event_id="e1"),
        _line("tr-orch-1", "governance_after", "2026-06-02T10:00:03+00:00", event_id="e1", allowed=True),
        _line("tr-orch-1", "rag_before", "2026-06-02T10:00:04+00:00", event_id="e1"),
        _line("tr-orch-1", "mongo_before", "2026-06-02T10:00:05+00:00", event_id="e1"),
    ]
    timeline = reconstruct_timeline("tr-orch-1", lines)
    plan = validate_timeline_orchestration(timeline)
    payload = orchestration_plan_to_dict(plan)
    assert payload["valid"] is True
    assert payload["complete"] is True
    assert payload["total_violations"] == 0


def test_governance_before_kafka_violation() -> None:
    lines = [
        _line("tr-orch-2", "governance_before", "2026-06-02T10:00:01+00:00"),
        _line("tr-orch-2", "kafka_received", "2026-06-02T10:00:02+00:00"),
    ]
    timeline = reconstruct_timeline("tr-orch-2", lines)
    plan = validate_timeline_orchestration(timeline)
    kinds = {v.kind for v in plan.violations}
    assert "stage_order_violation" in kinds
    assert plan.valid is False


def test_partial_trace_missing_stages() -> None:
    lines = [_line("tr-orch-3", "kafka_received", "2026-06-02T10:00:01+00:00")]
    timeline = reconstruct_timeline("tr-orch-3", lines)
    plan = validate_timeline_orchestration(timeline)
    assert plan.complete is False
    assert any(v.kind == "missing_stage" for v in plan.violations)


def test_plan_fingerprint_stable() -> None:
    lines = [
        _line("tr-orch-4", "kafka_received", "2026-06-02T10:00:01+00:00"),
        _line("tr-orch-4", "governance_before", "2026-06-02T10:00:02+00:00"),
        _line("tr-orch-4", "governance_after", "2026-06-02T10:00:03+00:00", allowed=True),
    ]
    timeline = reconstruct_timeline("tr-orch-4", lines)
    p1 = validate_timeline_orchestration(timeline)
    p2 = validate_timeline_orchestration(timeline)
    assert p1.plan_fingerprint == p2.plan_fingerprint


def test_graph_validation_detects_backward_chronological_edge() -> None:
    lines = [
        _line("tr-orch-5", "mongo_before", "2026-06-02T10:00:01+00:00"),
        _line("tr-orch-5", "kafka_received", "2026-06-02T10:00:02+00:00"),
    ]
    timeline = reconstruct_timeline("tr-orch-5", lines)
    graph = build_execution_graph(timeline)
    plan = validate_graph_orchestration(graph, timeline)
    assert plan.valid is False
    assert any(v.kind == "graph_edge_violation" for v in plan.violations)
