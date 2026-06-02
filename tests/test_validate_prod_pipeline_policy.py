from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_validate_prod_env_requires_strict_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("SKIP_AUTH", raising=False)
    monkeypatch.setenv("OPA_URL", "http://opa:8181")
    monkeypatch.setenv("PIPELINE_RUN_POLICY", "warn")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("REDIS_URL", "redis://x")

    from src.main import validate_prod_env

    with pytest.raises(RuntimeError, match="PIPELINE_RUN_POLICY"):
        await validate_prod_env()
