from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.staging_smoke_url import validate_api_url
from scripts.staging_tenant_helpers import (
    create_smoke_token,
    events_json_contains_marker,
    kafka_consumer_hint,
    kafka_host_hint,
)


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


def test_poll_default_timeout_is_one_eighty_seconds() -> None:
    import inspect

    from scripts.staging_tenant_helpers import poll_events_for_marker

    sig = inspect.signature(poll_events_for_marker)
    assert sig.parameters["timeout_sec"].default == 180


@pytest.mark.parametrize(
    "host,docker,expected_substr",
    [
        (0, 0, "no kafka consumer"),
        (2, 0, "only one consumer"),
        (1, 1, "host and docker"),
    ],
)
def test_kafka_consumer_hint_warnings(
    monkeypatch: pytest.MonkeyPatch,
    host: int,
    docker: int,
    expected_substr: str,
) -> None:
    monkeypatch.setattr(
        "scripts.staging_tenant_helpers._count_host_kafka_processors",
        lambda: host,
    )
    monkeypatch.setattr(
        "scripts.staging_tenant_helpers._count_docker_kafka_processors",
        lambda: docker,
    )
    hint = kafka_consumer_hint()
    assert hint is not None
    assert expected_substr in hint


def test_kafka_consumer_hint_ok_single_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.staging_tenant_helpers._count_host_kafka_processors",
        lambda: 1,
    )
    monkeypatch.setattr(
        "scripts.staging_tenant_helpers._count_docker_kafka_processors",
        lambda: 0,
    )
    assert kafka_consumer_hint() is None


def test_operational_readiness_warns_on_consumer_hint() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "scripts" / "operational_readiness_smoke.sh").read_text(encoding="utf-8")
    assert "kafka_consumer_hint" in text


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
