from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_trace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(tmp_path / "live.jsonl"))
    monkeypatch.setenv("KIRP_POLICY_BASELINE_FINGERPRINT", "")
    from src.main import app

    return TestClient(app)


def test_golden_path_smoke_chain(client_trace: TestClient) -> None:
    seed = client_trace.post("/api/v1/traces/dev/seed", params={"reset": "true"})
    assert seed.status_code == 200
    health = client_trace.get("/api/v1/traces/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    full = client_trace.get(
        "/api/v1/trace/demo-trace-1",
        params={"include_full": "true", "baseline_trace_id": "demo-trace-good"},
    )
    assert full.status_code == 200
    body = full.json()
    assert body["timeline"]["total_stages"] == 5
    assert body["orchestration"]["valid"] is True
    bad = client_trace.get(
        "/api/v1/trace/demo-trace-bad",
        params={"include_full": "true", "baseline_trace_id": "demo-trace-1"},
    )
    assert bad.status_code == 200
    bad_body = bad.json()
    assert bad_body["policy_drift"]["drift_detected"] is True
    assert bad_body["governed_runtime"]["would_block"] is True
