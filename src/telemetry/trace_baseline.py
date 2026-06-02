from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.telemetry.decision_memory import build_decision_memory
from src.telemetry.execution_graph import build_execution_graph
from src.telemetry.replay_engine import replay_from_graph
from src.telemetry.trace_reconstructor import reconstruct_timeline_from_file


@dataclass(frozen=True)
class TraceBaselineSnapshot:
    trace_id: str
    tenant_id: str | None
    decision_fingerprint: str
    replay_hash: str
    orchestration_valid: bool
    orchestration_complete: bool
    total_stages: int


def capture_trace_baseline(trace_id: str, log_path: str) -> TraceBaselineSnapshot:
    timeline = reconstruct_timeline_from_file(trace_id, log_path)
    graph = build_execution_graph(timeline)
    replay = replay_from_graph(graph, timeline)
    decision = build_decision_memory(replay)
    from src.telemetry.deterministic_orchestration import validate_graph_orchestration

    orch = validate_graph_orchestration(graph, timeline)
    return TraceBaselineSnapshot(
        trace_id=trace_id,
        tenant_id=timeline.tenant_id,
        decision_fingerprint=decision.fingerprint,
        replay_hash=replay.deterministic_hash,
        orchestration_valid=orch.valid,
        orchestration_complete=orch.complete,
        total_stages=len(timeline.stages),
    )


def trace_baseline_to_dict(
    snapshot: TraceBaselineSnapshot,
    *,
    ready: bool,
    available_trace_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "trace_id": snapshot.trace_id,
        "tenant_id": snapshot.tenant_id,
        "decision_fingerprint": snapshot.decision_fingerprint,
        "replay_hash": snapshot.replay_hash,
        "orchestration_valid": snapshot.orchestration_valid,
        "orchestration_complete": snapshot.orchestration_complete,
        "total_stages": snapshot.total_stages,
        "ready_for_baseline": ready,
        "available_trace_ids": list(available_trace_ids),
    }
    if ready:
        payload["env_hint"] = {
            "KIRP_POLICY_BASELINE_FINGERPRINT": snapshot.decision_fingerprint,
        }
    return payload
