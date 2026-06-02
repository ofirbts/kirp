from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


def _write_trace_log(path: Path) -> str:
    good_fp = None
    lines = [
        {
            "event": "telemetry_trace",
            "trace_id": "tr-good",
            "stage": "governance_after",
            "timestamp": "2026-06-02T10:00:01+00:00",
            "tenant_id": "t1",
            "allowed": True,
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-current",
            "stage": "kafka_received",
            "timestamp": "2026-06-02T10:00:01+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-current",
            "stage": "governance_before",
            "timestamp": "2026-06-02T10:00:02+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-current",
            "stage": "governance_after",
            "timestamp": "2026-06-02T10:00:03+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
            "allowed": False,
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-current",
            "stage": "rag_before",
            "timestamp": "2026-06-02T10:00:04+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
        {
            "event": "telemetry_trace",
            "trace_id": "tr-current",
            "stage": "mongo_before",
            "timestamp": "2026-06-02T10:00:05+00:00",
            "tenant_id": "t1",
            "event_id": "e1",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in lines) + "\n", encoding="utf-8")
    from src.telemetry.decision_memory import build_decision_memory
    from src.telemetry.replay_engine import replay_timeline
    from src.telemetry.trace_reconstructor import reconstruct_timeline

    good_timeline = reconstruct_timeline("tr-good", [json.dumps(lines[0])])
    good_fp = build_decision_memory(replay_timeline(good_timeline)).fingerprint
    return good_fp


def test_trace_api_full_telemetry_stack(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "trace.log"
    baseline_fp = _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))

    r = client_skip.get(
        "/api/v1/trace/tr-current",
        params={
            "include_graph": "true",
            "include_replay": "true",
            "include_decision_memory": "true",
            "include_policy_drift": "true",
            "baseline_trace_id": "tr-good",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["trace_id"] == "tr-current"
    assert "timeline" in body
    assert "graph" in body
    assert body["replay"]["trace_id"] == "tr-current"
    assert body["decision_memory"]["fingerprint"]
    drift = body["policy_drift"]
    assert drift["drift_detected"] is True
    assert drift["drift_score"] > 0.0
    assert any(s["key"] == "governance.last_outcome" for s in drift["signals"])


def test_trace_api_policy_drift_env_baseline_fingerprint(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "trace.log"
    baseline_fp = _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    monkeypatch.setenv("KIRP_POLICY_BASELINE_FINGERPRINT", baseline_fp)

    r = client_skip.get(
        "/api/v1/trace/tr-current",
        params={
            "include_replay": "true",
            "include_policy_drift": "true",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "policy_drift" in body
    assert body["policy_drift"]["baseline_fingerprint"] == baseline_fp


def test_trace_api_include_governed_runtime(client_skip: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_file = tmp_path / "trace.log"
    _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    r = client_skip.get(
        "/api/v1/trace/tr-good",
        params={"include_governed_runtime": "true"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "governed_runtime" in body
    assert body["governed_runtime"]["mode"] in {"shadow", "enforce"}


def test_trace_api_include_orchestration(client_skip: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_file = tmp_path / "trace.log"
    _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    r = client_skip.get(
        "/api/v1/trace/tr-current",
        params={"include_graph": "false", "include_orchestration": "true"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "orchestration" in body
    assert body["orchestration"]["trace_id"] == "tr-current"
    assert "expected_sequence" in body["orchestration"]


def test_trace_api_list_traces(client_skip: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_file = tmp_path / "trace.log"
    _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    r = client_skip.get("/api/v1/traces", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert "tr-current" in body["trace_ids"]


def test_trace_api_include_full(client_skip: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_file = tmp_path / "trace.log"
    _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    r = client_skip.get(
        "/api/v1/trace/tr-current",
        params={"include_full": "true", "baseline_trace_id": "tr-good"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["timeline"]["total_stages"] == 5
    assert "governed_runtime" in body
    assert "policy_drift" in body


def test_trace_api_health(client_skip: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_file = tmp_path / "trace.log"
    _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    monkeypatch.setenv("KIRP_GOVERNED_RUNTIME_MODE", "shadow")
    r = client_skip.get("/api/v1/traces/health")
    assert r.status_code == 200
    body = r.json()
    assert body["log_readable"] is True
    assert body["total_trace_ids"] >= 1
    assert "tr-current" in body["sample_trace_ids"]


def test_trace_api_baseline_endpoint(client_skip: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_file = tmp_path / "trace.log"
    _write_trace_log(log_file)
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    r = client_skip.get("/api/v1/trace/tr-current/baseline")
    assert r.status_code == 200
    body = r.json()
    assert body["trace_id"] == "tr-current"
    assert body["decision_fingerprint"]
    assert body["ready_for_baseline"] is True
    assert "KIRP_POLICY_BASELINE_FINGERPRINT" in body["env_hint"]

    r_missing = client_skip.get("/api/v1/trace/does-not-exist/baseline")
    assert r_missing.status_code == 404


def test_trace_api_missing_log_returns_empty_timeline(client_skip: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", "/tmp/does-not-exist-kirp-trace.log")
    r = client_skip.get("/api/v1/trace/tr-missing")
    assert r.status_code == 200
    body = r.json()
    assert body["total_stages"] == 0
