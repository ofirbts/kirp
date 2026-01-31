from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json().get("status") == "ok"

def test_post_run():
    r = client.post("/brand-os/run", json={"tenant_id": "t1", "platform": "linkedin", "topic_hint": "API"})
    assert r.status_code == 200
    d = r.json()
    assert "trace_id" in d and "content" in d and "status" in d

def test_post_run_422():
    r = client.post("/brand-os/run", json={"tenant_id": "t1"})
    assert r.status_code == 422
