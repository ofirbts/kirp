from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from src.api import v1_auth


class _SlowStore:
    async def get_user_by_email(self, email: str):  # type: ignore[no-untyped-def]
        await asyncio.sleep(10)
        return None

    async def update_last_login(self, user_id: str):  # type: ignore[no-untyped-def]
        await asyncio.sleep(10)


@pytest.mark.asyncio
async def test_login_returns_503_when_lookup_times_out(monkeypatch) -> None:
    monkeypatch.setattr(v1_auth, "get_user_store", lambda: _SlowStore())
    body = v1_auth.LoginBody(email="dev@localhost", password="x")
    with pytest.raises(HTTPException) as exc:
        await v1_auth.login(body)
    assert exc.value.status_code == 503
    assert "timed out" in str(exc.value.detail).lower()
