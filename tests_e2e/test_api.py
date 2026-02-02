"""
E2E tests for Brand OS API (api.main).
Uses TestClient; no mocks. Accepts 503 when Brand OS config is not present.
"""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json().get("status") == "ok"


def test_post_run():
    r = client.post(
        "/brand-os/run",
        json={"tenant_id": "t1", "platform": "linkedin", "topic_hint": "API"},
    )
    # 200 when Brand OS is configured; 503 when config/orchestrator unavailable
    assert r.status_code in (200, 503), f"Unexpected status {r.status_code}"
    if r.status_code == 200:
        d = r.json()
        assert "trace_id" in d and "content" in d and "status" in d


def test_post_run_422():
    r = client.post("/brand-os/run", json={"tenant_id": "t1"})
    assert r.status_code == 422
