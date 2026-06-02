from __future__ import annotations

import json
from pathlib import Path

from src.telemetry.trace_health import probe_trace_health


def test_probe_ok_with_log(tmp_path: Path, monkeypatch) -> None:
    log_file = tmp_path / "t.jsonl"
    log_file.write_text(
        json.dumps(
            {
                "event": "telemetry_trace",
                "trace_id": "tr-h",
                "stage": "kafka_received",
                "timestamp": "2026-06-02T10:00:01+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    monkeypatch.setenv("KIRP_GOVERNED_RUNTIME_MODE", "shadow")
    report = probe_trace_health()
    assert report.ok is True
    assert report.total_trace_ids == 1
    assert report.sample_trace_ids == ("tr-h",)


def test_probe_missing_path(monkeypatch) -> None:
    monkeypatch.delenv("KIRP_TRACE_LOG_PATH", raising=False)
    monkeypatch.setenv("ENV", "production")
    report = probe_trace_health()
    assert report.ok is False
    assert "KIRP_TRACE_LOG_PATH not set" in report.issues


def test_trace_log_path_dev_default(monkeypatch) -> None:
    from src.telemetry.trace_sink import trace_log_path

    monkeypatch.delenv("KIRP_TRACE_LOG_PATH", raising=False)
    monkeypatch.setenv("ENV", "development")
    assert trace_log_path() == "/tmp/kirp-traces.jsonl"
    monkeypatch.setenv("ENV", "production")
    assert trace_log_path() == ""


def test_probe_enforce_without_baseline_warns(tmp_path: Path, monkeypatch) -> None:
    log_file = tmp_path / "t.jsonl"
    log_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    monkeypatch.setenv("KIRP_GOVERNED_RUNTIME_MODE", "enforce")
    monkeypatch.setenv("KIRP_POLICY_BASELINE_FINGERPRINT", "")
    report = probe_trace_health()
    assert report.ok is False
    assert report.governed_runtime_mode == "enforce"
    assert report.baseline_fingerprint_configured is False
    assert any("KIRP_POLICY_BASELINE_FINGERPRINT" in issue for issue in report.issues)
