from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class TraceStage:
    stage: str
    timestamp: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True)
class TraceTimeline:
    trace_id: str
    tenant_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    stages: tuple[TraceStage, ...]


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
    candidate = text[start:]
    try:
        obj = json.loads(candidate)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def parse_trace_events(lines: Iterable[str], trace_id: str) -> tuple[list[TraceStage], str | None]:
    stages: list[TraceStage] = []
    tenant_id: str | None = None
    for line in lines:
        payload = _extract_json(line)
        if payload is None:
            continue
        if payload.get("event") != "telemetry_trace":
            continue
        if str(payload.get("trace_id") or "") != trace_id:
            continue
        stage_name = payload.get("stage")
        if not isinstance(stage_name, str) or not stage_name:
            continue
        ts = _parse_timestamp(payload.get("timestamp")) or _parse_timestamp(payload.get("ts"))
        if ts is None:
            continue
        if tenant_id is None:
            tenant_raw = payload.get("tenant_id")
            if tenant_raw is not None:
                tenant_id = str(tenant_raw)
        metadata: dict[str, Any] = {}
        for k, v in payload.items():
            if k in {"event", "stage", "trace_id", "event_id", "tenant_id", "timestamp", "ts"}:
                continue
            metadata[k] = v
        event_id = payload.get("event_id")
        if event_id is not None:
            metadata["event_id"] = str(event_id)
        stages.append(TraceStage(stage=stage_name, timestamp=ts, metadata=metadata))
    stages.sort(key=lambda s: s.timestamp)
    deduped: list[TraceStage] = []
    seen: set[tuple[str, str, str]] = set()
    for stage in stages:
        meta_key = json.dumps(stage.metadata, sort_keys=True, default=str)
        key = (stage.stage, stage.timestamp.isoformat(), meta_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(stage)
    return deduped, tenant_id


def reconstruct_timeline(trace_id: str, lines: Iterable[str]) -> TraceTimeline:
    stages, tenant_id = parse_trace_events(lines, trace_id)
    started_at = stages[0].timestamp if stages else None
    completed_at = stages[-1].timestamp if stages else None
    return TraceTimeline(
        trace_id=trace_id,
        tenant_id=tenant_id,
        started_at=started_at,
        completed_at=completed_at,
        stages=tuple(stages),
    )


def reconstruct_timeline_from_file(trace_id: str, log_path: str) -> TraceTimeline:
    if not log_path or not os.path.exists(log_path):
        return TraceTimeline(trace_id=trace_id, tenant_id=None, started_at=None, completed_at=None, stages=())
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        return reconstruct_timeline(trace_id, f)

