from __future__ import annotations

import json
from typing import Any

from src.telemetry.trace_sink import append_telemetry_line, trace_log_path

_GOLDEN_TRACE_ID = "demo-trace-1"
_BAD_TRACE_ID = "demo-trace-bad"
_GOOD_BASELINE_ID = "demo-trace-good"


def _row(trace_id: str, stage: str, ts: str, **meta: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": "telemetry_trace",
        "trace_id": trace_id,
        "stage": stage,
        "timestamp": ts,
        "tenant_id": "t1",
    }
    payload.update(meta)
    return payload


def demo_trace_payloads() -> list[dict[str, Any]]:
    return [
        _row(_GOLDEN_TRACE_ID, "kafka_received", "2026-06-02T10:00:01+00:00", event_id="e1"),
        _row(_GOLDEN_TRACE_ID, "governance_before", "2026-06-02T10:00:02+00:00", event_id="e1"),
        _row(_GOLDEN_TRACE_ID, "governance_after", "2026-06-02T10:00:03+00:00", event_id="e1", allowed=True),
        _row(_GOLDEN_TRACE_ID, "rag_before", "2026-06-02T10:00:04+00:00", event_id="e1"),
        _row(_GOLDEN_TRACE_ID, "mongo_before", "2026-06-02T10:00:05+00:00", event_id="e1"),
        _row(_BAD_TRACE_ID, "governance_after", "2026-06-02T10:00:01+00:00", allowed=False),
        _row(_GOOD_BASELINE_ID, "governance_after", "2026-06-02T10:00:01+00:00", allowed=True),
    ]


def seed_demo_traces(*, log_path: str | None = None, reset: bool = False) -> tuple[str, ...]:
    path = (log_path or trace_log_path()).strip()
    if not path:
        return ()
    if reset:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("")
    written: list[str] = []
    for payload in demo_trace_payloads():
        if append_telemetry_line(payload, log_path=path):
            tid = str(payload.get("trace_id") or "")
            if tid and tid not in written:
                written.append(tid)
    return tuple(written)


def golden_trace_id() -> str:
    return _GOLDEN_TRACE_ID


def bad_trace_id() -> str:
    return _BAD_TRACE_ID


def baseline_trace_id() -> str:
    return _GOOD_BASELINE_ID
