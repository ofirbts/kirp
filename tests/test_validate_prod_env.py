from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_validate_prod_env_rejects_skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SKIP_AUTH", "1")
    monkeypatch.setenv("OPA_URL", "http://opa:8181")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("REDIS_URL", "redis://x")
    monkeypatch.setenv("PIPELINE_RUN_POLICY", "strict")

    from src.main import validate_prod_env

    with pytest.raises(RuntimeError, match="SKIP_AUTH"):
        await validate_prod_env()


@pytest.mark.asyncio
async def test_validate_prod_env_requires_opa_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("SKIP_AUTH", raising=False)
    monkeypatch.delenv("OPA_URL", raising=False)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("REDIS_URL", "redis://x")
    monkeypatch.setenv("PIPELINE_RUN_POLICY", "strict")

    from src.main import validate_prod_env

    with pytest.raises(RuntimeError, match="OPA_URL"):
        await validate_prod_env()
