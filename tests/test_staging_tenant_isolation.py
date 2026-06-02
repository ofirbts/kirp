from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from scripts.staging_smoke_url import validate_api_url
from scripts.staging_tenant_helpers import (
    create_smoke_token,
    events_json_contains_marker,
    kafka_host_hint,
)
from src.core.jwt_utils import create_access_token


@pytest.mark.parametrize(
    "url,expected_substr",
    [
        ("https://staging...", "placeholder"),
        ("https://staging.example.com", "placeholder"),
        ("", "empty"),
        ("ftp://bad/scheme", "http or https"),
    ],
)
def test_validate_api_url_rejects_bad_urls(url: str, expected_substr: str) -> None:
    err = validate_api_url(url)
    assert err is not None
    assert expected_substr in err.lower()


def test_validate_api_url_accepts_local() -> None:
    assert validate_api_url("http://127.0.0.1:8002") is None


def test_create_smoke_token_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "smoke-test-secret")
    token = create_smoke_token("user_a", "tenant_a")
    assert len(token.split(".")) == 3
    import importlib

    import src.auth.jwt as jwt_mod

    importlib.reload(jwt_mod)
    payload = jwt_mod.decode_access_token(token)
    assert payload["tenant_id"] == "tenant_a"
    assert payload["user_id"] == "user_a"


def test_kafka_host_hint_for_wrong_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    hint = kafka_host_hint()
    assert hint is not None
    assert "9093" in hint


def test_fetch_events_timeout_returns_zero_status(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    from scripts.staging_tenant_helpers import fetch_events

    def _timeout(*_args: object, **_kwargs: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", _timeout)
    status, body = fetch_events("http://127.0.0.1:8002", "token", timeout_sec=1.0)
    assert status == 0
    assert body == ""


def test_poll_retries_after_transient_fetch_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.staging_tenant_helpers import poll_events_for_marker

    calls = {"n": 0}
    marker = "tenant-smoke-retry"

    def _fetch(*_args: object, **_kwargs: object) -> tuple[int, str]:
        calls["n"] += 1
        if calls["n"] == 1:
            return 0, ""
        body = json.dumps({"data": [{"payloadPreview": marker}]})
        return 200, body

    monkeypatch.setattr("scripts.staging_tenant_helpers.fetch_events", _fetch)
    monkeypatch.setattr("scripts.staging_tenant_helpers.time.sleep", lambda _s: None)

    assert poll_events_for_marker(
        "http://127.0.0.1:8002",
        "token",
        marker,
        timeout_sec=5,
        interval_sec=0.01,
        request_timeout_sec=1.0,
    )
    assert calls["n"] >= 2


def test_poll_default_timeout_is_ninety_seconds() -> None:
    import inspect

    from scripts.staging_tenant_helpers import poll_events_for_marker

    sig = inspect.signature(poll_events_for_marker)
    assert sig.parameters["timeout_sec"].default == 90


def test_events_json_contains_marker_in_payload_preview() -> None:
    body = json.dumps(
        {
            "data": [
                {
                    "payloadPreview": "tenant-smoke-abc",
                    "tenantId": "tenant_a",
                }
            ]
        }
    )
    assert events_json_contains_marker(body, "tenant-smoke-abc")
    assert not events_json_contains_marker(body, "other-marker")


def test_staging_smoke_script_rejects_placeholder_url() -> None:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        ["bash", "scripts/staging_tenant_smoke.sh"],
        cwd=root,
        env={"KIRP_API_URL": "https://staging...", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "placeholder" in proc.stdout.lower() or "placeholder" in proc.stderr.lower()


@pytest.fixture
def client_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "0")
    monkeypatch.setenv("ENV", "test")
    from src.main import app

    return TestClient(app)


def test_tenant_b_cannot_see_tenant_a_events(client_auth: TestClient) -> None:
    token_a = create_access_token("user_a", "tenant_a", roles=["user"])
    token_b = create_access_token("user_b", "tenant_b", roles=["user"])
    marker = "iso-marker-xyz"

    async def fake_list(*, tenant_id: str, **_kw: object) -> list[dict[str, str]]:
        if tenant_id == "tenant_a":
            return [{"content": marker, "tenant_id": tenant_id}]
        return []

    with patch("src.api.v1_events.events_service.list_events", new=AsyncMock(side_effect=fake_list)):
        r_a = client_auth.get("/api/v1/events", headers={"Authorization": f"Bearer {token_a}"})
        r_b = client_auth.get("/api/v1/events", headers={"Authorization": f"Bearer {token_b}"})

    assert r_a.status_code == 200
    assert r_b.status_code == 200
    assert marker in str(r_a.json())
    assert marker not in str(r_b.json())
