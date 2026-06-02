"""src/core/quotas — budget check and QuotaExceeded."""

from __future__ import annotations

import asyncio

import pytest

from src.core.quotas import QuotaExceeded, check_tenant_llm_budget, get_effective_llm_quota_limit_usd


@pytest.fixture
def limit_5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_QUOTA_LIMIT_USD", "5.0")


def test_quota_disabled_when_limit_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_QUOTA_LIMIT_USD", raising=False)
    assert get_effective_llm_quota_limit_usd() == 0.0


def test_check_allows_under_limit(limit_5: None, monkeypatch: pytest.MonkeyPatch) -> None:
    async def used(_tid: str) -> float:
        return 1.0

    monkeypatch.setattr("src.core.quotas.get_tenant_llm_cost_used", used)

    async def _go() -> None:
        await check_tenant_llm_budget("default", 3.9)

    asyncio.run(_go())


def test_check_blocks_over_limit(limit_5: None, monkeypatch: pytest.MonkeyPatch) -> None:
    async def used(_tid: str) -> float:
        return 4.95

    monkeypatch.setattr("src.core.quotas.get_tenant_llm_cost_used", used)

    async def _go() -> None:
        with pytest.raises(QuotaExceeded) as ei:
            await check_tenant_llm_budget("default", 0.1)
        assert ei.value.llm_cost_used == 4.95
        assert ei.value.limit_usd == 5.0

    asyncio.run(_go())
