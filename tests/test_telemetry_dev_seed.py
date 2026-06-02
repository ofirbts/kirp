from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.telemetry.dev_seed import bad_trace_id, golden_trace_id, seed_demo_traces
from src.telemetry.trace_reconstructor import reconstruct_timeline_from_file


@pytest.fixture
def client_dev(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    monkeypatch.setenv("ENV", "development")
    from src.main import app

    return TestClient(app)


def test_seed_demo_traces_writes_file(tmp_path: Path) -> None:
    log_file = tmp_path / "live.jsonl"
    ids = seed_demo_traces(log_path=str(log_file), reset=True)
    assert golden_trace_id() in ids
    assert bad_trace_id() in ids
    timeline = reconstruct_timeline_from_file(golden_trace_id(), str(log_file))
    assert len(timeline.stages) == 5


def test_api_dev_seed(client_dev: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_file = tmp_path / "live.jsonl"
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    r = client_dev.post("/api/v1/traces/dev/seed", params={"reset": "true"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert golden_trace_id() in body["trace_ids"]


def test_api_dev_seed_forbidden_outside_dev(client_dev: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    r = client_dev.post("/api/v1/traces/dev/seed")
    assert r.status_code == 403
