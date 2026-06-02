from __future__ import annotations

import json
from pathlib import Path

from src.telemetry.trace_baseline import capture_trace_baseline


def _write_golden(path: Path, trace_id: str) -> None:
    stages = [
        "kafka_received",
        "governance_before",
        "governance_after",
        "rag_before",
        "mongo_before",
    ]
    lines = []
    for idx, stage in enumerate(stages):
        row = {
            "event": "telemetry_trace",
            "trace_id": trace_id,
            "stage": stage,
            "timestamp": f"2026-06-02T10:00:0{idx + 1}+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        }
        if stage == "governance_after":
            row["allowed"] = True
        lines.append(row)
    path.write_text("\n".join(json.dumps(row, default=str) for row in lines) + "\n", encoding="utf-8")


def test_capture_trace_baseline(tmp_path: Path) -> None:
    log_file = tmp_path / "trace.jsonl"
    _write_golden(log_file, "tr-base")
    snap = capture_trace_baseline("tr-base", str(log_file))
    assert snap.trace_id == "tr-base"
    assert snap.total_stages == 5
    assert snap.orchestration_valid is True
    assert len(snap.decision_fingerprint) == 64
