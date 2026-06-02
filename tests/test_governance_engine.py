"""GovernanceEngine.check — OPA enabled vs disabled (fail-closed on errors)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest


class _Resp503:
    status_code = 503


class _Client503:
    async def __aenter__(self) -> _Client503:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> _Resp503:
        return _Resp503()


def test_governance_disabled_allows_when_opa_url_falsy(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.governance import GovernanceEngine

    monkeypatch.setenv("ENV", "development")

    async def _go() -> bool:
        ge = GovernanceEngine(None)
        c = await ge.check("t1", "s1", "u1", "write", "event")
        return c.allowed

    assert asyncio.run(_go()) is True


def test_governance_opa_non_200_denies() -> None:
    from src.core.governance import GovernanceEngine

    async def _go() -> tuple[bool, str]:
        ge = GovernanceEngine("http://opa.test")
        c = await ge.check("t1", "s1", "u1", "write", "event")
        return c.allowed, c.reason

    with patch("httpx.AsyncClient", lambda **kw: _Client503()):
        allowed, reason = asyncio.run(_go())
    assert allowed is False
    assert "503" in reason


def test_governance_opa_transport_error_allows_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.governance import GovernanceEngine

    monkeypatch.setenv("ENV", "development")

    class _ClientBoom:
        async def __aenter__(self) -> _ClientBoom:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> None:
            raise OSError("connection refused")

    async def _go() -> bool:
        ge = GovernanceEngine("http://opa.test")
        c = await ge.check("t1", "s1", "u1", "write", "event")
        return c.allowed

    with patch("httpx.AsyncClient", lambda **kw: _ClientBoom()):
        assert asyncio.run(_go()) is True


def test_governance_opa_transport_error_denies_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    from src.core.governance import GovernanceEngine

    class _ClientBoom:
        async def __aenter__(self) -> _ClientBoom:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> None:
            raise OSError("connection refused")

    async def _go() -> tuple[bool, bool]:
        ge = GovernanceEngine("http://opa.test")
        c = await ge.check("t1", "s1", "u1", "write", "event")
        return c.allowed, c.requires_approval

    with patch("httpx.AsyncClient", lambda **kw: _ClientBoom()):
        allowed, req_appr = asyncio.run(_go())
    assert allowed is False
    assert req_appr is True
