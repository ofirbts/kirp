from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from src.telemetry.execution_graph import ExecutionGraph, build_execution_graph
from src.telemetry.trace_reconstructor import TraceTimeline, reconstruct_timeline_from_file


@dataclass(frozen=True)
class ReplayStep:
    sequence: int
    stage: str
    action: str
    outcome: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ReplayReport:
    trace_id: str
    mode: str
    tenant_id: str | None
    steps: tuple[ReplayStep, ...]
    deterministic_hash: str
    partial: bool
    governance_would_block: bool
    agents_observed: tuple[str, ...]


def _governance_would_block_from_metadata(metadata: dict[str, Any]) -> bool | None:
    if metadata.get("allowed") is False:
        return True
    if metadata.get("allowed") is True:
        return False
    would_block = metadata.get("would_block")
    if isinstance(would_block, bool):
        return would_block
    return None


def _collect_agents(metadata: dict[str, Any], found: list[str]) -> None:
    raw = metadata.get("potential_agents")
    if not isinstance(raw, list):
        return
    for item in raw:
        if isinstance(item, str) and item and item not in found:
            found.append(item)


def _infer_action(stage: str) -> str:
    if stage == "governance_before":
        return "simulate_governance_check"
    if stage == "governance_after":
        return "record_governance_result"
    if stage == "agent_detection":
        return "discover_agents_dry_run"
    if stage.startswith("kafka"):
        return "observe_ingress"
    if stage in {"rag_before", "mongo_before"}:
        return "observe_pipeline_write"
    if "failed" in stage:
        return "observe_failure"
    return "observe_stage"


def _infer_outcome(stage: str, metadata: dict[str, Any], would_block: bool | None) -> str:
    if stage == "governance_after":
        if would_block is True:
            return "would_deny"
        if would_block is False:
            return "would_allow"
        allowed = metadata.get("allowed")
        if allowed is False:
            return "would_deny"
        if allowed is True:
            return "would_allow"
        return "governance_observed"
    if stage == "agent_detection":
        return "agents_not_executed"
    if "failed" in stage:
        return "failure_observed"
    return "no_side_effects"


def replay_timeline(timeline: TraceTimeline, *, mode: str = "dry_run") -> ReplayReport:
    steps: list[ReplayStep] = []
    agents: list[str] = []
    governance_would_block = False
    expected_stages = (
        "kafka_received",
        "governance_before",
        "governance_after",
        "rag_before",
        "mongo_before",
    )
    present = {s.stage for s in timeline.stages}
    partial = any(s not in present for s in expected_stages) or len(timeline.stages) == 0

    for seq, stage in enumerate(timeline.stages):
        meta = dict(stage.metadata)
        block = _governance_would_block_from_metadata(meta)
        if block is True:
            governance_would_block = True
        _collect_agents(meta, agents)
        action = _infer_action(stage.stage)
        outcome = _infer_outcome(stage.stage, meta, block)
        steps.append(
            ReplayStep(
                sequence=seq,
                stage=stage.stage,
                action=action,
                outcome=outcome,
                metadata=meta,
            )
        )

    canonical = [
        {
            "sequence": s.sequence,
            "stage": s.stage,
            "action": s.action,
            "outcome": s.outcome,
            "metadata": s.metadata,
        }
        for s in steps
    ]
    payload = json.dumps(canonical, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return ReplayReport(
        trace_id=timeline.trace_id,
        mode=mode,
        tenant_id=timeline.tenant_id,
        steps=tuple(steps),
        deterministic_hash=digest,
        partial=partial,
        governance_would_block=governance_would_block,
        agents_observed=tuple(agents),
    )


def replay_from_graph(graph: ExecutionGraph, timeline: TraceTimeline, *, mode: str = "dry_run") -> ReplayReport:
    base = replay_timeline(timeline, mode=mode)
    edge_count = len(graph.edges)
    if edge_count == 0 and len(base.steps) > 0:
        return ReplayReport(
            trace_id=base.trace_id,
            mode=base.mode,
            tenant_id=base.tenant_id,
            steps=base.steps,
            deterministic_hash=base.deterministic_hash,
            partial=True,
            governance_would_block=base.governance_would_block,
            agents_observed=base.agents_observed,
        )
    extra_meta = {"graph_edges": edge_count}
    if not base.steps:
        return base
    last = base.steps[-1]
    merged_meta = {**last.metadata, **extra_meta}
    patched_last = ReplayStep(
        sequence=last.sequence,
        stage=last.stage,
        action=last.action,
        outcome=last.outcome,
        metadata=merged_meta,
    )
    steps = base.steps[:-1] + (patched_last,)
    canonical = json.dumps(
        [{"sequence": s.sequence, "stage": s.stage, "action": s.action, "outcome": s.outcome} for s in steps],
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return ReplayReport(
        trace_id=base.trace_id,
        mode=base.mode,
        tenant_id=base.tenant_id,
        steps=steps,
        deterministic_hash=digest,
        partial=base.partial,
        governance_would_block=base.governance_would_block,
        agents_observed=base.agents_observed,
    )


def replay_from_file(trace_id: str, log_path: str, *, mode: str = "dry_run") -> ReplayReport:
    timeline = reconstruct_timeline_from_file(trace_id, log_path)
    graph = build_execution_graph(timeline)
    return replay_from_graph(graph, timeline, mode=mode)


def replay_report_to_dict(report: ReplayReport) -> dict[str, Any]:
    return {
        "trace_id": report.trace_id,
        "mode": report.mode,
        "tenant_id": report.tenant_id,
        "partial": report.partial,
        "deterministic_hash": report.deterministic_hash,
        "governance_would_block": report.governance_would_block,
        "agents_observed": list(report.agents_observed),
        "total_steps": len(report.steps),
        "steps": [
            {
                "sequence": s.sequence,
                "stage": s.stage,
                "action": s.action,
                "outcome": s.outcome,
                "metadata": s.metadata,
            }
            for s in report.steps
        ],
    }
