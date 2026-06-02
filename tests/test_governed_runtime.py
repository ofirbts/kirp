from __future__ import annotations

import json
import logging

import pytest

from src.telemetry.governed_runtime import (
    apply_governed_runtime_verdict,
    build_pipeline_governance_timeline,
    emit_governed_runtime_trace,
    evaluate_governed_runtime,
    runtime_mode_from_env,
)
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


def test_shadow_mode_never_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIRP_GOVERNED_RUNTIME_MODE", "shadow")
    lines = [
        _line("tr-gr-1", "governance_after", "2026-06-02T10:00:01+00:00", allowed=False),
    ]
    timeline = reconstruct_timeline("tr-gr-1", lines)
    verdict = evaluate_governed_runtime(timeline, profile="pipeline", mode="shadow")
    assert verdict.would_block is True
    assert verdict.allow_execute is True
    assert verdict.should_block() is False


def test_enforce_mode_blocks_on_deny(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIRP_GOVERNED_RUNTIME_MODE", "enforce")
    timeline = build_pipeline_governance_timeline(
        trace_id="tr-gr-2",
        tenant_id="t1",
        event_id="e1",
        allowed=False,
    )
    verdict = evaluate_governed_runtime(timeline, profile="pipeline", mode="enforce")
    assert verdict.should_block() is True
    with pytest.raises(PermissionError):
        apply_governed_runtime_verdict(verdict)


def test_full_profile_valid_golden_path() -> None:
    lines = [
        _line("tr-gr-3", "kafka_received", "2026-06-02T10:00:01+00:00", event_id="e1"),
        _line("tr-gr-3", "governance_before", "2026-06-02T10:00:02+00:00", event_id="e1"),
        _line("tr-gr-3", "governance_after", "2026-06-02T10:00:03+00:00", event_id="e1", allowed=True),
        _line("tr-gr-3", "rag_before", "2026-06-02T10:00:04+00:00", event_id="e1"),
        _line("tr-gr-3", "mongo_before", "2026-06-02T10:00:05+00:00", event_id="e1"),
    ]
    timeline = reconstruct_timeline("tr-gr-3", lines)
    verdict = evaluate_governed_runtime(timeline, profile="full", mode="shadow")
    assert verdict.orchestration_valid is True
    assert verdict.would_block is False


def test_runtime_mode_from_env_default_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KIRP_GOVERNED_RUNTIME_MODE", raising=False)
    assert runtime_mode_from_env() == "shadow"


def test_decision_log_append(tmp_path, monkeypatch) -> None:
    decision_file = tmp_path / "decisions.jsonl"
    monkeypatch.setenv("KIRP_DECISION_LOG_PATH", str(decision_file))
    timeline = build_pipeline_governance_timeline(
        trace_id="tr-gr-5",
        tenant_id="t1",
        event_id="e1",
        allowed=True,
    )
    verdict = evaluate_governed_runtime(timeline, profile="pipeline", mode="shadow")
    emit_governed_runtime_trace(logging.getLogger("test_gr"), verdict)
    text = decision_file.read_text(encoding="utf-8")
    assert "governed_runtime_decision" in text
    assert "tr-gr-5" in text


def test_verdict_fingerprint_stable() -> None:
    timeline = build_pipeline_governance_timeline(
        trace_id="tr-gr-4",
        tenant_id="t1",
        event_id="e1",
        allowed=True,
    )
    v1 = evaluate_governed_runtime(timeline, profile="pipeline", mode="shadow")
    v2 = evaluate_governed_runtime(timeline, profile="pipeline", mode="shadow")
    assert v1.verdict_fingerprint == v2.verdict_fingerprint
