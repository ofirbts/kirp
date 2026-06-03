from __future__ import annotations

import pytest

from src.core.webhook_tenant import (
    resolve_notion_webhook_tenant,
    resolve_slack_webhook_tenant,
    resolve_whatsapp_webhook_tenant,
)


def test_whatsapp_map_routes_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "WHATSAPP_WEBHOOK_TENANT_MAP",
        '{"+15551234567": {"tenant_id": "tenant_a", "space_id": "s1", "user_id": "u1"}}',
    )
    t, s, u = resolve_whatsapp_webhook_tenant("+15551234567")
    assert t == "tenant_a"
    assert s == "s1"
    assert u == "u1"


def test_slack_map_routes_tenant_a(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_ID", "tenant_fallback")
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_MAP", '{"T123": "tenant_a"}')
    t, s, u = resolve_slack_webhook_tenant("T123")
    assert t == "tenant_a"
    assert s == "all"
    assert u == "system"


def test_notion_map_routes_tenant_b(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTION_WEBHOOK_TENANT_ID", "tenant_fallback")
    monkeypatch.setenv("NOTION_WEBHOOK_TENANT_MAP", '{"ws-1": "tenant_b"}')
    t, _, _ = resolve_notion_webhook_tenant("ws-1")
    assert t == "tenant_b"


def test_slack_unknown_team_uses_explicit_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_ID", "tenant_fallback")
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_MAP", '{"T123": "tenant_a"}')
    t, _, _ = resolve_slack_webhook_tenant("T999")
    assert t == "tenant_fallback"
    assert t != "tenant_a"


def test_notion_unknown_workspace_uses_explicit_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTION_WEBHOOK_TENANT_ID", "tenant_fallback")
    monkeypatch.setenv("NOTION_WEBHOOK_TENANT_MAP", '{"ws-1": "tenant_b"}')
    t, _, _ = resolve_notion_webhook_tenant("ws-unknown")
    assert t == "tenant_fallback"
    assert t != "tenant_b"


def test_slack_missing_routing_key_does_not_use_map_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_ID", "tenant_explicit")
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_MAP", '{"T123": "tenant_a"}')
    t, _, _ = resolve_slack_webhook_tenant(None)
    assert t == "tenant_explicit"
