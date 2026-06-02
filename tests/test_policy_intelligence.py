from __future__ import annotations

import json

from src.telemetry.decision_memory import DecisionMemoryEntry, DecisionMemorySnapshot, build_decision_memory
from src.telemetry.policy_intelligence import compare_decision_memory, compare_fingerprint_only, policy_drift_to_dict
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


def _snapshot(trace_id: str, fingerprint: str, entries: tuple[DecisionMemoryEntry, ...]) -> DecisionMemorySnapshot:
    return DecisionMemorySnapshot(trace_id=trace_id, tenant_id="t1", entries=entries, fingerprint=fingerprint)


def test_no_drift_when_snapshots_match() -> None:
    entry = DecisionMemoryEntry("governance.last_outcome", "would_allow", 0.9, "governance_after", {})
    snap = _snapshot("tr-pi-1", "fp-same", (entry,))
    report = compare_decision_memory(snap, snap)
    assert report.drift_detected is False
    assert report.drift_score == 0.0
    assert report.signals == ()


def test_governance_flip_detected_critical() -> None:
    allow = _snapshot(
        "tr-pi-2",
        "fp-a",
        (DecisionMemoryEntry("governance.last_outcome", "would_allow", 0.9, "governance_after", {}),),
    )
    deny = _snapshot(
        "tr-pi-2",
        "fp-b",
        (DecisionMemoryEntry("governance.last_outcome", "would_deny", 0.95, "governance_after", {}),),
    )
    report = compare_decision_memory(deny, allow)
    payload = policy_drift_to_dict(report)
    assert payload["drift_detected"] is True
    assert payload["drift_score"] > 0.0
    kinds = {s["kind"] for s in payload["signals"]}
    assert "entry_changed" in kinds
    severities = {s["severity"] for s in payload["signals"] if s["key"] == "governance.last_outcome"}
    assert "critical" in severities


def test_fingerprint_only_baseline_match() -> None:
    lines = [_line("tr-pi-3", "governance_after", "2026-06-02T10:00:01+00:00", allowed=True)]
    timeline = reconstruct_timeline("tr-pi-3", lines)
    current = build_decision_memory(replay_timeline(timeline))
    report = compare_fingerprint_only(current, current.fingerprint)
    assert report.drift_detected is False


def test_fingerprint_only_baseline_mismatch() -> None:
    lines = [_line("tr-pi-4", "governance_after", "2026-06-02T10:00:01+00:00", allowed=False)]
    timeline = reconstruct_timeline("tr-pi-4", lines)
    current = build_decision_memory(replay_timeline(timeline))
    report = compare_fingerprint_only(current, "deadbeef" * 8)
    assert report.drift_detected is True
    assert len(report.signals) == 1
    assert report.signals[0].kind == "fingerprint_mismatch"


def test_drift_report_fingerprint_stable() -> None:
    lines = [
        _line("tr-pi-5", "governance_after", "2026-06-02T10:00:01+00:00", allowed=True),
        _line("tr-pi-5", "mongo_write_failed", "2026-06-02T10:00:02+00:00"),
    ]
    baseline = build_decision_memory(replay_timeline(reconstruct_timeline("tr-pi-5", lines[:1])))
    current = build_decision_memory(replay_timeline(reconstruct_timeline("tr-pi-5", lines)))
    r1 = compare_decision_memory(current, baseline)
    r2 = compare_decision_memory(current, baseline)
    assert r1.report_fingerprint == r2.report_fingerprint
