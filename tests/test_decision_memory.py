from __future__ import annotations

import json

from src.telemetry.decision_memory import build_decision_memory, decision_memory_to_dict
from src.telemetry.replay_engine import replay_timeline
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


def test_decision_memory_governance_and_agents() -> None:
    lines = [
        _line("tr-m-1", "kafka_received", "2026-06-02T10:00:01+00:00", event_id="e1"),
        _line("tr-m-1", "agent_detection", "2026-06-02T10:00:02+00:00", potential_agents=["planner", "writer"]),
        _line("tr-m-1", "governance_after", "2026-06-02T10:00:03+00:00", allowed=False),
    ]
    timeline = reconstruct_timeline("tr-m-1", lines)
    report = replay_timeline(timeline)
    snapshot = build_decision_memory(report)
    payload = decision_memory_to_dict(snapshot)
    assert payload["trace_id"] == "tr-m-1"
    assert payload["total_entries"] >= 2
    keys = {entry["key"] for entry in payload["entries"]}
    assert "governance.last_outcome" in keys
    assert "agents.detected" in keys


def test_decision_memory_deterministic_fingerprint() -> None:
    lines = [
        _line("tr-m-2", "governance_after", "2026-06-02T10:00:01+00:00", allowed=True),
        _line("tr-m-2", "mongo_write_failed", "2026-06-02T10:00:02+00:00"),
    ]
    timeline = reconstruct_timeline("tr-m-2", lines)
    report = replay_timeline(timeline)
    s1 = build_decision_memory(report)
    s2 = build_decision_memory(report)
    assert s1.fingerprint == s2.fingerprint
    assert len(s1.entries) == len(s2.entries)


def test_decision_memory_partial_flag_entry() -> None:
    lines = [_line("tr-m-3", "kafka_received", "2026-06-02T10:00:01+00:00")]
    timeline = reconstruct_timeline("tr-m-3", lines)
    report = replay_timeline(timeline)
    snapshot = build_decision_memory(report)
    payload = decision_memory_to_dict(snapshot)
    assert any(entry["key"] == "trace.completeness" for entry in payload["entries"])
