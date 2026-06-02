from __future__ import annotations

import os
from typing import Any

from src.telemetry.decision_memory import build_decision_memory, decision_memory_to_dict
from src.telemetry.deterministic_orchestration import orchestration_plan_to_dict, validate_graph_orchestration
from src.telemetry.execution_graph import build_execution_graph, summarize_execution_graph
from src.telemetry.governed_runtime import evaluate_governed_runtime, governed_runtime_verdict_to_dict
from src.telemetry.policy_intelligence import (
    compare_decision_memory,
    compare_fingerprint_only,
    policy_drift_to_dict,
)
from src.telemetry.replay_engine import replay_from_graph, replay_report_to_dict
from src.telemetry.trace_reconstructor import TraceTimeline, reconstruct_timeline_from_file


def timeline_to_payload(timeline: TraceTimeline) -> dict[str, object]:
    return {
        "trace_id": timeline.trace_id,
        "tenant_id": timeline.tenant_id,
        "started_at": timeline.started_at.isoformat() if timeline.started_at else None,
        "completed_at": timeline.completed_at.isoformat() if timeline.completed_at else None,
        "total_stages": len(timeline.stages),
        "stages": [
            {
                "stage": s.stage,
                "timestamp": s.timestamp.isoformat(),
                "metadata": s.metadata,
            }
            for s in timeline.stages
        ],
    }


def build_trace_response(
    timeline: TraceTimeline,
    *,
    include_graph: bool = True,
    include_replay: bool = False,
    include_decision_memory: bool = False,
    include_policy_drift: bool = False,
    include_orchestration: bool = False,
    include_governed_runtime: bool = False,
    baseline_fingerprint: str | None = None,
    baseline_trace_id: str | None = None,
    log_path: str | None = None,
) -> dict[str, object]:
    timeline_payload = timeline_to_payload(timeline)
    response: dict[str, object] = {
        "trace_id": timeline.trace_id,
        "timeline": timeline_payload,
        "started_at": timeline_payload["started_at"],
        "completed_at": timeline_payload["completed_at"],
        "total_stages": timeline_payload["total_stages"],
        "stages": timeline_payload["stages"],
    }
    graph = None
    if include_graph:
        graph = build_execution_graph(timeline)
        summary = summarize_execution_graph(graph)
        response["graph"] = {
            "trace_id": graph.trace_id,
            "nodes": [
                {
                    "stage": n.stage,
                    "timestamp": n.timestamp.isoformat(),
                    "metadata": n.metadata,
                }
                for n in graph.nodes
            ],
            "edges": [
                {
                    "source_stage": e.source_stage,
                    "target_stage": e.target_stage,
                    "relationship": e.relationship,
                }
                for e in graph.edges
            ],
            "summary": {
                "total_nodes": summary.total_nodes,
                "total_edges": summary.total_edges,
                "detected_failures": summary.detected_failures,
                "missing_links": summary.missing_links,
                "governance_observed": summary.governance_observed,
                "agents_detected": list(summary.agents_detected),
            },
        }
    replay_report = None
    decision_snapshot = None

    def _ensure_replay():
        nonlocal graph, replay_report
        if replay_report is not None:
            return replay_report
        if graph is None:
            graph = build_execution_graph(timeline)
        replay_report = replay_from_graph(graph, timeline)
        return replay_report

    if include_replay:
        response["replay"] = replay_report_to_dict(_ensure_replay())
    if include_decision_memory or include_policy_drift:
        decision_snapshot = build_decision_memory(_ensure_replay())
        if include_decision_memory:
            response["decision_memory"] = decision_memory_to_dict(decision_snapshot)
    if include_policy_drift and decision_snapshot is not None:
        path = (log_path or os.getenv("KIRP_TRACE_LOG_PATH", "")).strip()
        baseline_snapshot = None
        if baseline_trace_id and path:
            baseline_timeline = reconstruct_timeline_from_file(baseline_trace_id, path)
            baseline_graph = build_execution_graph(baseline_timeline)
            baseline_snapshot = build_decision_memory(replay_from_graph(baseline_graph, baseline_timeline))
        env_fp = os.getenv("KIRP_POLICY_BASELINE_FINGERPRINT", "").strip()
        fp = (baseline_fingerprint or env_fp).strip()
        if baseline_snapshot is not None:
            response["policy_drift"] = policy_drift_to_dict(
                compare_decision_memory(decision_snapshot, baseline_snapshot)
            )
        elif fp:
            response["policy_drift"] = policy_drift_to_dict(compare_fingerprint_only(decision_snapshot, fp))
    if include_orchestration:
        if graph is None:
            graph = build_execution_graph(timeline)
        response["orchestration"] = orchestration_plan_to_dict(validate_graph_orchestration(graph, timeline))
    if include_governed_runtime:
        if graph is None:
            graph = build_execution_graph(timeline)
        response["governed_runtime"] = governed_runtime_verdict_to_dict(
            evaluate_governed_runtime(timeline, graph, profile="full")
        )
    return response


def build_full_trace_response(
    trace_id: str,
    log_path: str,
    *,
    baseline_fingerprint: str | None = None,
    baseline_trace_id: str | None = None,
) -> dict[str, object]:
    timeline = reconstruct_timeline_from_file(trace_id, log_path)
    return build_trace_response(
        timeline,
        include_graph=True,
        include_replay=True,
        include_decision_memory=True,
        include_policy_drift=True,
        include_orchestration=True,
        include_governed_runtime=True,
        baseline_fingerprint=baseline_fingerprint,
        baseline_trace_id=baseline_trace_id,
        log_path=log_path,
    )
