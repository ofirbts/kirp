from __future__ import annotations

import json

import pytest

from src.core.webhook_tenant import resolve_whatsapp_webhook_tenant


def test_webhook_tenant_map_routes_by_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHATSAPP_WEBHOOK_TENANT_ID", "default")
    monkeypatch.setenv("WHATSAPP_WEBHOOK_USER_ID", "system")
    monkeypatch.setenv(
        "WHATSAPP_WEBHOOK_TENANT_MAP",
        json.dumps({"+972501234567": "tenant-il"}),
    )
    tenant, space, user = resolve_whatsapp_webhook_tenant("+972501234567")
    assert tenant == "tenant-il"
    assert space == "all"
    assert user == "system"


def test_webhook_tenant_fallback_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHATSAPP_WEBHOOK_TENANT_ID", "tenant-a")
    monkeypatch.delenv("WHATSAPP_WEBHOOK_TENANT_MAP", raising=False)
    tenant, _, _ = resolve_whatsapp_webhook_tenant("+1999")
    assert tenant == "tenant-a"
