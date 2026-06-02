from __future__ import annotations

import json
from pathlib import Path

from src.telemetry.trace_bundle import build_full_trace_response


def _write_demo_log(path: Path) -> None:
    lines = [
        {
            "event": "telemetry_trace",
            "trace_id": "tr-bundle",
            "stage": "kafka_received",
            "timestamp": "2026-06-02T10:00:01+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-bundle",
            "stage": "governance_before",
            "timestamp": "2026-06-02T10:00:02+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-bundle",
            "stage": "governance_after",
            "timestamp": "2026-06-02T10:00:03+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
            "allowed": True,
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-bundle",
            "stage": "rag_before",
            "timestamp": "2026-06-02T10:00:04+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-bundle",
            "stage": "mongo_before",
            "timestamp": "2026-06-02T10:00:05+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in lines) + "\n", encoding="utf-8")


def test_build_full_trace_response(tmp_path: Path) -> None:
    log_file = tmp_path / "trace.jsonl"
    _write_demo_log(log_file)
    payload = build_full_trace_response("tr-bundle", str(log_file))
    assert payload["trace_id"] == "tr-bundle"
    assert payload["timeline"]["total_stages"] == 5
    assert "replay" in payload
    assert "decision_memory" in payload
    assert "orchestration" in payload
    assert "governed_runtime" in payload
    assert payload["orchestration"]["valid"] is True
