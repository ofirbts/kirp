from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.telemetry.decision_memory import build_decision_memory
from src.telemetry.deterministic_orchestration import validate_graph_orchestration, validate_timeline_orchestration
from src.telemetry.execution_graph import ExecutionGraph, build_execution_graph
from src.telemetry.orchestration_trace import log_trace
from src.telemetry.replay_engine import replay_from_graph
from src.telemetry.trace_reconstructor import TraceStage, TraceTimeline


@dataclass(frozen=True)
class GovernedRuntimeVerdict:
    trace_id: str
    tenant_id: str | None
    mode: str
    profile: str
    allow_execute: bool
    would_block: bool
    reasons: tuple[str, ...]
    orchestration_valid: bool
    orchestration_complete: bool
    replay_hash: str | None
    decision_fingerprint: str | None
    verdict_fingerprint: str

    def should_block(self) -> bool:
        return self.mode == "enforce" and self.would_block


def runtime_mode_from_env() -> str:
    raw = (os.getenv("KIRP_GOVERNED_RUNTIME_MODE") or "shadow").strip().lower()
    if raw in {"enforce", "enforcement", "block"}:
        return "enforce"
    return "shadow"


def evaluate_governed_runtime(
    timeline: TraceTimeline,
    graph: ExecutionGraph | None = None,
    *,
    profile: str = "full",
    mode: str | None = None,
) -> GovernedRuntimeVerdict:
    resolved_mode = mode or runtime_mode_from_env()
    require_golden = profile == "full"
    if graph is None:
        graph = build_execution_graph(timeline)
    if profile == "full":
        orchestration = validate_graph_orchestration(graph, timeline, require_golden_path=True)
    else:
        orchestration = validate_timeline_orchestration(timeline, require_golden_path=False)
    replay = replay_from_graph(graph, timeline)
    decision = build_decision_memory(replay)
    reasons: list[str] = []
    would_block = False
    if not orchestration.valid:
        would_block = True
        reasons.append("orchestration_invalid")
    if replay.governance_would_block:
        would_block = True
        reasons.append("replay_governance_would_deny")
    if decision.entries and any(e.key == "governance.last_outcome" and e.value == "would_deny" for e in decision.entries):
        would_block = True
        if "replay_governance_would_deny" not in reasons:
            reasons.append("decision_memory_governance_deny")
    allow_execute = True if resolved_mode == "shadow" else not would_block
    payload = {
        "trace_id": timeline.trace_id,
        "mode": resolved_mode,
        "profile": profile,
        "would_block": would_block,
        "allow_execute": allow_execute,
        "reasons": sorted(reasons),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return GovernedRuntimeVerdict(
        trace_id=timeline.trace_id,
        tenant_id=timeline.tenant_id,
        mode=resolved_mode,
        profile=profile,
        allow_execute=allow_execute,
        would_block=would_block,
        reasons=tuple(sorted(reasons)),
        orchestration_valid=orchestration.valid,
        orchestration_complete=orchestration.complete,
        replay_hash=replay.deterministic_hash,
        decision_fingerprint=decision.fingerprint,
        verdict_fingerprint=digest,
    )


def build_pipeline_governance_timeline(
    *,
    trace_id: str,
    tenant_id: str | None,
    event_id: str | None,
    allowed: bool,
    event_type: str | None = None,
    source: str | None = None,
) -> TraceTimeline:
    now = datetime.now(timezone.utc)
    meta: dict[str, Any] = {"allowed": allowed}
    if event_type is not None:
        meta["event_type"] = event_type
    if source is not None:
        meta["source"] = source
    if event_id is not None:
        meta["event_id"] = event_id
    stages = (
        TraceStage(stage="governance_before", timestamp=now, metadata=dict(meta)),
        TraceStage(stage="governance_after", timestamp=now, metadata=dict(meta)),
    )
    return TraceTimeline(
        trace_id=trace_id,
        tenant_id=tenant_id,
        started_at=now,
        completed_at=now,
        stages=stages,
    )


def _append_decision_log(verdict: GovernedRuntimeVerdict) -> None:
    path = (os.getenv("KIRP_DECISION_LOG_PATH") or "").strip()
    if not path:
        return
    payload = {
        "event": "governed_runtime_decision",
        "trace_id": verdict.trace_id,
        "tenant_id": verdict.tenant_id,
        "mode": verdict.mode,
        "would_block": verdict.would_block,
        "allow_execute": verdict.allow_execute,
        "reasons": list(verdict.reasons),
        "verdict_fingerprint": verdict.verdict_fingerprint,
    }
    from src.telemetry.trace_sink import append_telemetry_line

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    line = json.dumps(payload, sort_keys=True, default=str)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def emit_governed_runtime_trace(
    logger: logging.Logger,
    verdict: GovernedRuntimeVerdict,
    *,
    event_id: str | None = None,
) -> None:
    _append_decision_log(verdict)
    log_trace(
        logger,
        stage="governed_runtime_verdict",
        trace_id=verdict.trace_id or None,
        event_id=event_id,
        tenant_id=verdict.tenant_id,
        mode=verdict.mode,
        profile=verdict.profile,
        would_block=verdict.would_block,
        allow_execute=verdict.allow_execute,
        reasons=list(verdict.reasons),
        orchestration_valid=verdict.orchestration_valid,
        verdict_fingerprint=verdict.verdict_fingerprint,
    )


def evaluate_and_emit_for_trace_file(
    trace_id: str,
    log_path: str,
    logger: logging.Logger,
    *,
    profile: str = "full",
    event_id: str | None = None,
) -> GovernedRuntimeVerdict | None:
    from src.telemetry.trace_reconstructor import reconstruct_timeline_from_file

    if not trace_id.strip() or not log_path.strip():
        return None
    timeline = reconstruct_timeline_from_file(trace_id, log_path)
    if not timeline.stages:
        return None
    graph = build_execution_graph(timeline)
    verdict = evaluate_governed_runtime(timeline, graph, profile=profile)
    emit_governed_runtime_trace(logger, verdict, event_id=event_id)
    return verdict


def apply_governed_runtime_verdict(verdict: GovernedRuntimeVerdict) -> None:
    if verdict.should_block():
        joined = ",".join(verdict.reasons) if verdict.reasons else "policy"
        raise PermissionError(f"Governed runtime blocked: {joined}")


def governed_runtime_verdict_to_dict(verdict: GovernedRuntimeVerdict) -> dict[str, Any]:
    return {
        "trace_id": verdict.trace_id,
        "tenant_id": verdict.tenant_id,
        "mode": verdict.mode,
        "profile": verdict.profile,
        "allow_execute": verdict.allow_execute,
        "would_block": verdict.would_block,
        "should_block": verdict.should_block(),
        "reasons": list(verdict.reasons),
        "orchestration_valid": verdict.orchestration_valid,
        "orchestration_complete": verdict.orchestration_complete,
        "replay_hash": verdict.replay_hash,
        "decision_fingerprint": verdict.decision_fingerprint,
        "verdict_fingerprint": verdict.verdict_fingerprint,
    }
