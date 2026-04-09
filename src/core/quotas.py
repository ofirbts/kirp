"""
Per-tenant LLM spend quotas (Redis counter).

When LLM_QUOTA_LIMIT_USD > 0, LLMClient checks remaining budget before each call
and increments usage after successful billed completion.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Redis key: floating total USD (estimated) spent in window
_TENANT_COST_KEY = "tenant:{tenant_id}:llm_cost"
_TTL_SEC = int(os.getenv("LLM_QUOTA_COUNTER_TTL_SEC", str(86400 * 45)))


class QuotaExceeded(Exception):
    """Raised when tenant would exceed LLM spend limit."""

    def __init__(
        self,
        *,
        tenant_id: str,
        llm_cost_used: float,
        limit_usd: float,
        estimated_cost: float,
        message: str = "LLM quota exceeded for tenant",
    ) -> None:
        self.tenant_id = tenant_id
        self.llm_cost_used = llm_cost_used
        self.limit_usd = limit_usd
        self.estimated_cost = estimated_cost
        super().__init__(message)


def get_effective_llm_quota_limit_usd() -> float:
    """0 or negative means quotas disabled (no enforcement)."""
    raw = (os.getenv("LLM_QUOTA_LIMIT_USD") or "").strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


async def _redis() -> Any:
    from src.core.integrations import get_redis_async

    return get_redis_async()


def _cost_key(tenant_id: str) -> str:
    return _TENANT_COST_KEY.format(tenant_id=tenant_id)


async def get_tenant_llm_cost_used(tenant_id: str) -> float:
    if not tenant_id or tenant_id == "*":
        return 0.0
    r = await _redis()
    if r is None:
        return 0.0
    try:
        raw = await r.get(_cost_key(tenant_id))
        if raw is None:
            return 0.0
        return float(raw)
    except Exception as e:
        logger.warning("quota get_tenant_llm_cost_used failed: %s", e)
        return 0.0


async def increment_tenant_llm_cost(tenant_id: str, cost_usd: float) -> None:
    if not tenant_id or tenant_id == "*" or cost_usd <= 0:
        return
    r = await _redis()
    if r is None:
        logger.warning("quota increment skipped: redis unavailable tenant=%s", tenant_id)
        return
    key = _cost_key(tenant_id)
    try:
        await r.incrbyfloat(key, cost_usd)
        await r.expire(key, _TTL_SEC)
    except Exception as e:
        logger.warning("quota increment_tenant_llm_cost failed: %s", e)


async def check_tenant_llm_budget(tenant_id: str, estimated_cost_usd: float) -> None:
    """
    If quotas enabled and used + estimated > limit, raise QuotaExceeded.
    Does not mutate counters.
    """
    limit = get_effective_llm_quota_limit_usd()
    if limit <= 0 or estimated_cost_usd <= 0:
        return
    if not tenant_id or tenant_id == "*":
        return
    used = await get_tenant_llm_cost_used(tenant_id)
    if used + estimated_cost_usd > limit + 1e-9:
        raise QuotaExceeded(
            tenant_id=tenant_id,
            llm_cost_used=used,
            limit_usd=limit,
            estimated_cost=estimated_cost_usd,
        )


class TenantQuota:
    """Facade matching the production-quota spec (check against Redis + limit)."""

    @staticmethod
    async def check_tenant_budget(tenant_id: str, estimated_cost: float) -> None:
        await check_tenant_llm_budget(tenant_id, estimated_cost)

    @staticmethod
    async def record_spend(tenant_id: str, cost_usd: float) -> None:
        await increment_tenant_llm_cost(tenant_id, cost_usd)
