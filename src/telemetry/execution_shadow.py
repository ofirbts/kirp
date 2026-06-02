from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.telemetry.trace_reconstructor import TraceTimeline, reconstruct_timeline_from_file
from src.telemetry.trace_sink import append_telemetry_line, trace_log_path


@dataclass(frozen=True)
class ShadowExecution:
    event_id: str
    tenant_id: str
    action_type: str
    would_execute: bool
    reason: str


@dataclass(frozen=True)
class ShadowExecutionTrace:
    trace_id: str
    tenant_id: str | None
    event_id: str | None
    would_governance_pass: bool | None
    would_execute: bool
    would_be_blocked: bool
    potential_execution_path: tuple[str, ...]
    shadow_executions: tuple[ShadowExecution, ...]
    agent_selection_preview: tuple[str, ...]
    governance_outcome_prediction: str
    deterministic_hash: str
    source: str | None


_DEFAULT_INGEST_PATH: tuple[str, ...] = (
    "kafka_received",
    "governance_before",
    "governance_after",
    "rag_before",
    "mongo_before",
)


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _extract_json(line: str) -> dict[str, Any] | None:
    text = line.strip()
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        obj = json.loads(text[start:])
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _infer_potential_action_types(
    event_type: str,
    source: str,
    metadata: dict[str, Any],
) -> tuple[str, ...]:
    actions: list[str] = ["governance_write", "mongo_persist", "rag_upsert"]
    if event_type.startswith("m3."):
        actions.append("m3_whatsapp_escalation")
    if event_type == "agent_run" or metadata.get("agent_name"):
        actions.append("agent_dispatch")
    if source in {"notion", "execution_engine"} or metadata.get("command_type"):
        actions.append("external_execute")
    return tuple(dict.fromkeys(actions))


def _governance_pass_from_timeline(timeline: TraceTimeline) -> bool | None:
    for stage in reversed(timeline.stages):
        if stage.stage != "governance_after":
            continue
        allowed = stage.metadata.get("allowed")
        if isinstance(allowed, bool):
            return allowed
    return None


def _requires_approval_from_timeline(timeline: TraceTimeline) -> bool:
    for stage in reversed(timeline.stages):
        if stage.stage != "governance_after":
            continue
        raw = stage.metadata.get("requires_approval")
        if isinstance(raw, bool):
            return raw
    return False


def _observed_path_from_timeline(timeline: TraceTimeline) -> tuple[str, ...]:
    if timeline.stages:
        return tuple(s.stage for s in timeline.stages)
    return _DEFAULT_INGEST_PATH


def preview_agent_selection(event_type: str, metadata: dict[str, Any]) -> tuple[str, ...]:
    if event_type.startswith("m3."):
        return ("m3_reflection", "m3_synthesis", "m3_micro_action")
    agent_name = metadata.get("agent_name")
    if isinstance(agent_name, str) and agent_name.strip():
        return (agent_name.strip(),)
    if event_type == "agent_run":
        return ("agent_run",)
    return ()


def _governance_outcome_label(
    would_pass: bool | None,
    requires_approval: bool,
) -> str:
    if would_pass is None:
        return "pending_governance_observation"
    if not would_pass:
        return "would_deny"
    if requires_approval:
        return "would_allow_with_approval"
    return "would_allow"


def _simulate_action(
    action_type: str,
    *,
    event_id: str,
    tenant_id: str,
    would_governance_pass: bool | None,
    requires_approval: bool,
    would_be_blocked: bool,
) -> ShadowExecution:
    if action_type == "governance_write":
        if would_governance_pass is None:
            return ShadowExecution(
                event_id=event_id,
                tenant_id=tenant_id,
                action_type=action_type,
                would_execute=False,
                reason="governance_not_observed_yet",
            )
        return ShadowExecution(
            event_id=event_id,
            tenant_id=tenant_id,
            action_type=action_type,
            would_execute=would_governance_pass,
            reason="governance_would_pass" if would_governance_pass else "governance_would_deny",
        )
    if would_governance_pass is False:
        return ShadowExecution(
            event_id=event_id,
            tenant_id=tenant_id,
            action_type=action_type,
            would_execute=False,
            reason="blocked_by_governance",
        )
    if would_governance_pass is None:
        return ShadowExecution(
            event_id=event_id,
            tenant_id=tenant_id,
            action_type=action_type,
            would_execute=False,
            reason="shadow_pending_pipeline_governance",
        )
    if would_be_blocked:
        return ShadowExecution(
            event_id=event_id,
            tenant_id=tenant_id,
            action_type=action_type,
            would_execute=False,
            reason="governed_runtime_would_block",
        )
    if requires_approval and action_type in {
        "m3_whatsapp_escalation",
        "external_execute",
        "agent_dispatch",
    }:
        return ShadowExecution(
            event_id=event_id,
            tenant_id=tenant_id,
            action_type=action_type,
            would_execute=False,
            reason="requires_approval",
        )
    if action_type in {"mongo_persist", "rag_upsert"}:
        return ShadowExecution(
            event_id=event_id,
            tenant_id=tenant_id,
            action_type=action_type,
            would_execute=True,
            reason="pipeline_projection_simulated",
        )
    return ShadowExecution(
        event_id=event_id,
        tenant_id=tenant_id,
        action_type=action_type,
        would_execute=False,
        reason="shadow_no_side_effect",
    )


def simulate_execution_shadow(
    timeline: TraceTimeline,
    *,
    event_id: str | None = None,
    event_type: str = "ingest",
    source: str = "pipeline",
    governance_allowed: bool | None = None,
    governance_requires_approval: bool | None = None,
    governance_reason: str = "",
    metadata: dict[str, Any] | None = None,
    hook_source: str | None = None,
) -> ShadowExecutionTrace:
    meta = dict(metadata or {})
    for stage in timeline.stages:
        if stage.stage == "governance_after":
            if governance_allowed is None and isinstance(stage.metadata.get("allowed"), bool):
                governance_allowed = stage.metadata.get("allowed")
            if governance_requires_approval is None and isinstance(
                stage.metadata.get("requires_approval"), bool
            ):
                governance_requires_approval = stage.metadata.get("requires_approval")
    if governance_allowed is None:
        governance_allowed = _governance_pass_from_timeline(timeline)
    requires_approval = (
        governance_requires_approval
        if governance_requires_approval is not None
        else _requires_approval_from_timeline(timeline)
    )
    resolved_event_id = (
        event_id
        or str(meta.get("event_id") or "")
        or (str(timeline.stages[-1].metadata.get("event_id")) if timeline.stages else "")
        or "unknown"
    )
    tenant_id = timeline.tenant_id or str(meta.get("tenant_id") or "unknown")
    would_governance_pass = governance_allowed
    would_be_blocked = would_governance_pass is False or (
        would_governance_pass is True and requires_approval and event_type.startswith("m3.")
    )
    action_types = _infer_potential_action_types(event_type, source, meta)
    shadow_executions = tuple(
        _simulate_action(
            action,
            event_id=resolved_event_id,
            tenant_id=tenant_id,
            would_governance_pass=would_governance_pass,
            requires_approval=requires_approval,
            would_be_blocked=would_be_blocked,
        )
        for action in action_types
    )
    would_execute = any(s.would_execute for s in shadow_executions)
    path = _observed_path_from_timeline(timeline)
    if hook_source == "kafka" and "kafka_received" not in path:
        path = ("kafka_received",) + path
    agents = preview_agent_selection(event_type, meta)
    outcome = _governance_outcome_label(would_governance_pass, requires_approval)
    if governance_reason:
        outcome = f"{outcome}:{governance_reason}"
    canonical = {
        "trace_id": timeline.trace_id,
        "tenant_id": tenant_id,
        "event_id": resolved_event_id,
        "would_governance_pass": would_governance_pass,
        "would_execute": would_execute,
        "would_be_blocked": would_be_blocked,
        "path": list(path),
        "actions": [s.__dict__ for s in shadow_executions],
        "agents": list(agents),
        "outcome": outcome,
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode("utf-8")).hexdigest()
    return ShadowExecutionTrace(
        trace_id=timeline.trace_id,
        tenant_id=tenant_id,
        event_id=resolved_event_id,
        would_governance_pass=would_governance_pass,
        would_execute=would_execute,
        would_be_blocked=would_be_blocked,
        potential_execution_path=path,
        shadow_executions=shadow_executions,
        agent_selection_preview=agents,
        governance_outcome_prediction=outcome,
        deterministic_hash=digest,
        source=hook_source,
    )


def shadow_execution_trace_to_dict(report: ShadowExecutionTrace) -> dict[str, Any]:
    return {
        "trace_id": report.trace_id,
        "tenant_id": report.tenant_id,
        "event_id": report.event_id,
        "would_governance_pass": report.would_governance_pass,
        "would_execute": report.would_execute,
        "would_be_blocked": report.would_be_blocked,
        "potential_execution_path": list(report.potential_execution_path),
        "shadow_executions": [
            {
                "event_id": s.event_id,
                "tenant_id": s.tenant_id,
                "action_type": s.action_type,
                "would_execute": s.would_execute,
                "reason": s.reason,
            }
            for s in report.shadow_executions
        ],
        "agent_selection_preview": list(report.agent_selection_preview),
        "governance_outcome_prediction": report.governance_outcome_prediction,
        "deterministic_hash": report.deterministic_hash,
        "source": report.source,
    }


def _append_shadow_trace_payload(report: ShadowExecutionTrace) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    body = shadow_execution_trace_to_dict(report)
    payload: dict[str, Any] = {
        "event": "shadow_execution_trace",
        "stage": "shadow_execution_trace",
        "trace_id": report.trace_id,
        "tenant_id": report.tenant_id,
        "timestamp": ts,
        **body,
    }
    append_telemetry_line(payload)


def emit_shadow_execution_observation(
    *,
    trace_id: str,
    event_id: str,
    tenant_id: str,
    hook_source: str,
    event_type: str = "ingest",
    source: str = "pipeline",
    governance_allowed: bool | None = None,
    governance_requires_approval: bool | None = None,
    governance_reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> ShadowExecutionTrace | None:
    tid = (trace_id or "").strip()
    if not tid:
        return None
    timeline = TraceTimeline(
        trace_id=tid,
        tenant_id=tenant_id or None,
        started_at=None,
        completed_at=None,
        stages=(),
    )
    report = simulate_execution_shadow(
        timeline,
        event_id=event_id,
        event_type=event_type,
        source=source,
        governance_allowed=governance_allowed,
        governance_requires_approval=governance_requires_approval,
        governance_reason=governance_reason,
        metadata=metadata,
        hook_source=hook_source,
    )
    _append_shadow_trace_payload(report)
    return report


def list_shadow_traces_from_file(
    trace_id: str,
    log_path: str | None = None,
) -> list[dict[str, Any]]:
    path = (log_path or trace_log_path()).strip()
    if not path:
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return []
    found: list[dict[str, Any]] = []
    for line in lines:
        payload = _extract_json(line)
        if payload is None:
            continue
        if str(payload.get("trace_id") or "") != trace_id:
            continue
        if payload.get("event") != "shadow_execution_trace":
            continue
        found.append(payload)
    return found


def build_shadow_execution_response(
    trace_id: str,
    log_path: str | None = None,
) -> dict[str, Any]:
    path = log_path or trace_log_path()
    timeline = reconstruct_timeline_from_file(trace_id, path)
    stored = list_shadow_traces_from_file(trace_id, path)
    if stored:
        latest = stored[-1]
        return {
            "trace_id": trace_id,
            "shadow_execution_trace": latest,
            "simulated_from": "telemetry_log",
            "timeline_stages": len(timeline.stages),
        }
    report = simulate_execution_shadow(
        timeline,
        hook_source="trace_replay",
    )
    return {
        "trace_id": trace_id,
        "shadow_execution_trace": shadow_execution_trace_to_dict(report),
        "simulated_from": "timeline_reconstruction",
        "timeline_stages": len(timeline.stages),
    }
