"""POST /api/v1/onboarding — SaaS tenant signup + trial + API keys."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_onboarding_rate_limit() -> None:
    import src.main as main_mod

    main_mod._onboarding_rl_hits.clear()
    yield
    main_mod._onboarding_rl_hits.clear()


@pytest.fixture
def client() -> TestClient:
    from src.main import app

    return TestClient(app)


def test_onboarding_validation_422(client: TestClient) -> None:
    r = client.post(
        "/api/v1/onboarding",
        json={"tenant_name": "", "email": "a@b.com"},
    )
    assert r.status_code == 422


def test_onboarding_invalid_email_422(client: TestClient) -> None:
    r = client.post(
        "/api/v1/onboarding",
        json={"tenant_name": "acme", "email": "not-an-email"},
    )
    assert r.status_code == 422


def test_onboarding_conflict_409(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services.onboarding_service import OnboardingError

    async def _dup(_name: str, _email: str) -> None:
        raise OnboardingError("tenant name already registered")

    monkeypatch.setattr("src.services.onboarding_service.create_tenant", _dup)

    r = client.post(
        "/api/v1/onboarding",
        json={"tenant_name": "acme", "email": "user@acme.com"},
    )
    assert r.status_code == 409
    assert "already registered" in r.json()["detail"].lower()


def test_onboarding_success_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake(name: str, email: str) -> dict:
        return {
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "tenant_name": name,
            "email": email,
            "lifecycle": "trial",
            "trial_ends_at": "2026-12-31T00:00:00Z",
            "trial_days": 30,
            "publishable_key": "kirp_pk_test",
            "secret_key": "kirp_sk_testsecret",
        }

    monkeypatch.setattr("src.services.onboarding_service.create_tenant", _fake)

    r = client.post(
        "/api/v1/onboarding",
        json={"tenant_name": "acme", "email": "user@acme.com"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["tenant_name"] == "acme"
    assert data["email"] == "user@acme.com"
    assert data["lifecycle"] == "trial"
    assert data["trial_days"] == 30
    assert data["publishable_key"].startswith("kirp_pk_")
    assert data["secret_key"].startswith("kirp_sk_")


def test_onboarding_rate_limit_429(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONBOARDING_RL_MAX", "2")
    monkeypatch.setenv("ONBOARDING_RL_WINDOW_SEC", "60")

    async def _fake(name: str, email: str) -> dict:
        return {
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "tenant_name": name,
            "email": email,
            "lifecycle": "trial",
            "trial_ends_at": "2026-12-31T00:00:00Z",
            "trial_days": 30,
            "publishable_key": "kirp_pk_x",
            "secret_key": "kirp_sk_x",
        }

    monkeypatch.setattr("src.services.onboarding_service.create_tenant", _fake)

    assert client.post(
        "/api/v1/onboarding",
        json={"tenant_name": "a1", "email": "a1@t.com"},
    ).status_code == 201
    assert client.post(
        "/api/v1/onboarding",
        json={"tenant_name": "a2", "email": "a2@t.com"},
    ).status_code == 201
    r3 = client.post(
        "/api/v1/onboarding",
        json={"tenant_name": "a3", "email": "a3@t.com"},
    )
    assert r3.status_code == 429
