from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.auth.tenant_context import (
    DEFAULT_LOCAL_CONTEXT,
    get_tenant_context,
    is_local_or_skip_auth,
    require_tenant_context,
)


def _request_with_user(user: dict[str, object] | None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/events",
        "headers": [],
    }
    req = Request(scope)
    if user is not None:
        req.state.user = user
    return req


def test_development_without_skip_auth_requires_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKIP_AUTH", raising=False)
    monkeypatch.setenv("ENV", "development")
    with pytest.raises(HTTPException) as exc:
        get_tenant_context(_request_with_user(None))
    assert exc.value.status_code == 401


def test_development_with_jwt_uses_token_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKIP_AUTH", raising=False)
    monkeypatch.setenv("ENV", "development")
    ctx = get_tenant_context(
        _request_with_user(
            {
                "user_id": "user_a",
                "tenant_id": "tenant_a",
                "roles": ["user"],
            }
        )
    )
    assert ctx.tenant_id == "tenant_a"
    assert ctx.user_id == "user_a"


def test_skip_auth_returns_default_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "1")
    ctx = get_tenant_context(_request_with_user(None))
    assert ctx == DEFAULT_LOCAL_CONTEXT


def test_require_tenant_context_rejects_cross_tenant_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKIP_AUTH", raising=False)
    req = _request_with_user(
        {
            "user_id": "user_a",
            "tenant_id": "tenant_a",
            "roles": ["user"],
        }
    )
    with pytest.raises(HTTPException) as exc:
        require_tenant_context(req, query_tenant_id="tenant_b")
    assert exc.value.status_code == 403


def test_is_local_or_skip_auth() -> None:
    import os

    prev = os.environ.get("SKIP_AUTH")
    os.environ["SKIP_AUTH"] = "1"
    try:
        assert is_local_or_skip_auth()
    finally:
        if prev is None:
            os.environ.pop("SKIP_AUTH", None)
        else:
            os.environ["SKIP_AUTH"] = prev
