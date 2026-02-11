from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_llm_usage_requires_auth() -> None:
  # Without Authorization header expect 401 from require_auth
  r = client.get("/api/v1/llm/usage")
  assert r.status_code == 401


def test_llm_usage_missing_keys(monkeypatch) -> None:
  # Provide a dummy Bearer token that decodes to a minimal payload via SKIP_AUTH dev path.
  # In test environments SKIP_AUTH may be enabled; we just need any Bearer header.
  headers = {"Authorization": "Bearer test-token"}

  # Ensure provider keys are not present so helpers short‑circuit and do NOT hit network.
  monkeypatch.delenv("GROQ_API_KEY", raising=False)
  monkeypatch.delenv("OPENAI_API_KEY", raising=False)
  monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
  monkeypatch.delenv("GEMINI_API_KEY", raising=False)
  monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

  r = client.get("/api/v1/llm/usage", headers=headers)
  assert r.status_code in (200, 401)
  # If auth is skipped in test env we should get a JSON body; otherwise 401.
  if r.status_code == 200:
    data = r.json()
    assert "groq" in data
    assert "openai" in data
    assert "anthropic" in data
    assert "gemini" in data
    assert "recommendation" in data

