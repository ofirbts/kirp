"""POST /api/v1/stripe/webhook — Stripe → tenant lifecycle."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient


def _sub_event(etype: str, tenant_id: str) -> dict[str, Any]:
    return {
        "id": "evt_test",
        "type": etype,
        "data": {
            "object": {
                "id": "sub_test",
                "metadata": {"tenant_id": tenant_id},
            }
        },
    }


@pytest.fixture
def client() -> TestClient:
    from src.main import app

    return TestClient(app)


def test_stripe_webhook_subscription_created_calls_active(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []

    async def _fake_update(tenant_id: str, lifecycle: str) -> None:
        calls.append((tenant_id, lifecycle))

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    monkeypatch.setattr(
        "src.services.stripe_service.verify_webhook_signature",
        lambda _p, _s: _sub_event("customer.subscription.created", "11111111-1111-1111-1111-111111111111"),
    )
    monkeypatch.setattr(
        "src.services.stripe_service.update_tenant_lifecycle",
        _fake_update,
    )

    r = client.post(
        "/api/v1/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "v1,ignored"},
    )
    assert r.status_code == 200
    assert r.json() == {"received": True}
    assert calls == [("11111111-1111-1111-1111-111111111111", "active")]


def test_stripe_webhook_subscription_deleted_calls_suspended(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []

    async def _fake_update(tenant_id: str, lifecycle: str) -> None:
        calls.append((tenant_id, lifecycle))

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    monkeypatch.setattr(
        "src.services.stripe_service.verify_webhook_signature",
        lambda _p, _s: _sub_event("customer.subscription.deleted", "22222222-2222-2222-2222-222222222222"),
    )
    monkeypatch.setattr(
        "src.services.stripe_service.update_tenant_lifecycle",
        _fake_update,
    )

    r = client.post(
        "/api/v1/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "v1,ignored"},
    )
    assert r.status_code == 200
    assert calls == [("22222222-2222-2222-2222-222222222222", "suspended")]


def test_stripe_webhook_invalid_signature_400(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import stripe

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    def _boom(_p: bytes, _s: str) -> dict[str, Any]:
        raise stripe.SignatureVerificationError("bad", "sig", "body")

    monkeypatch.setattr("src.services.stripe_service.verify_webhook_signature", _boom)

    r = client.post(
        "/api/v1/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "v1,bad"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid signature"


def test_handle_webhook_skips_without_tenant_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_update = AsyncMock()
    monkeypatch.setattr("src.services.stripe_service.update_tenant_lifecycle", mock_update)

    from src.services.stripe_service import handle_webhook

    ev = _sub_event("customer.subscription.created", "")
    ev["data"]["object"]["metadata"] = {}

    asyncio.run(handle_webhook(ev))
    mock_update.assert_not_called()
