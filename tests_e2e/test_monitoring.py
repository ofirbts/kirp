"""E2E: Monitoring FastAPI /metrics, /dashboard HTML."""
from fastapi.testclient import TestClient

from brand_os_monitoring.app import app

client = TestClient(app)


def test_metrics():
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "total_runs" in data
    assert "approved" in data
    assert "top_hooks" in data
    assert "top_pillars" in data


def test_dashboard_html():
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"Brand OS" in r.content or b"Dashboard" in r.content
