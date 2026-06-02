"""
Tenant billing / usage details + Stripe Checkout for upgrades.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.auth.tenant_context import TenantContext, get_tenant_context
from src.core.quotas import get_effective_llm_quota_limit_usd, get_tenant_llm_cost_used
from src.core.run_controller import get_run_controller
from src.core.schema_engine import get_schema_engine
from src.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["V1 Tenant billing"])


def _trial_days_remaining(extra: dict[str, Any]) -> int | None:
    if (extra or {}).get("lifecycle") != "trial":
        return None
    raw = (extra or {}).get("trial_ends_at")
    if not raw:
        return None
    try:
        s = str(raw)
        iso = s.replace("Z", "+00:00") if s.endswith("Z") else s
        end = datetime.fromisoformat(iso)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now >= end:
            return 0
        return max(0, int((end - now).total_seconds() // 86400))
    except (ValueError, TypeError):
        return None


async def _load_tenant_row(tenant_id: str) -> Tenant | None:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        try:
            uid = uuid.UUID(tenant_id)
            r = await session.execute(select(Tenant).where(Tenant.id == uid).limit(1))
        except (ValueError, TypeError):
            r = await session.execute(select(Tenant).where(Tenant.name == tenant_id).limit(1))
        return r.scalar_one_or_none()
    finally:
        await session.close()


@router.get("/tenant/{tenant_id}/usage/details")
async def tenant_usage_details(
    tenant_id: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    """
    LLM spend vs quota, trial countdown, lifecycle, and per-run cost rollup by ``model`` + day.
    """
    if ctx.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")

    used = await get_tenant_llm_cost_used(tenant_id)
    limit = get_effective_llm_quota_limit_usd()
    quota_enabled = limit > 0

    rc = get_run_controller()
    runs = await rc.get_recent_runs(tenant_id, limit=100)
    recent_runs_count = len(runs)
    agg: dict[tuple[str, str], float] = defaultdict(float)
    for r in runs:
        model = str(r.get("model") or "unknown")
        sa = r.get("started_at") or ""
        day = sa[:10] if isinstance(sa, str) and len(sa) >= 10 else (sa or "unknown")
        agg[(model, day)] += float(r.get("cost") or 0.0)

    breakdown = [
        {"model_used": m, "date": d, "cost_usd": round(v, 6)}
        for (m, d), v in sorted(agg.items(), key=lambda x: (x[0][1], x[0][0]))
    ]

    row = await _load_tenant_row(tenant_id)
    extra = dict(row.extra or {}) if row else {}
    lifecycle = str(extra.get("lifecycle") or "active")
    suspended = lifecycle == "suspended"

    return {
        "tenant_id": tenant_id,
        "recent_runs_count": recent_runs_count,
        "llm_cost_used": round(used, 6),
        "llm_quota_limit_usd": None if not quota_enabled else round(limit, 4),
        "quota_enabled": quota_enabled,
        "quota_remaining_usd": None
        if not quota_enabled
        else round(max(0.0, limit - used), 6),
        "trial_days_remaining": _trial_days_remaining(extra),
        "trial_ends_at": extra.get("trial_ends_at"),
        "lifecycle": lifecycle,
        "suspended": suspended,
        "breakdown": breakdown,
    }


class StripeCheckoutBody(BaseModel):
    success_url: str | None = Field(default=None, description="Stripe redirect after pay")
    cancel_url: str | None = Field(default=None, description="Stripe redirect on cancel")


@router.post("/tenant/{tenant_id}/stripe/checkout-session")
async def create_stripe_checkout_session(
    tenant_id: str,
    body: StripeCheckoutBody,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, str]:
    """Start Stripe Checkout (subscription). Requires ``STRIPE_SECRET_KEY`` and ``STRIPE_PRICE_ID``."""
    if ctx.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")

    import stripe as stripe_sdk

    sk = os.getenv("STRIPE_SECRET_KEY", "").strip()
    price = os.getenv("STRIPE_PRICE_ID", "").strip()
    if not sk or not price:
        raise HTTPException(
            status_code=503,
            detail="STRIPE_SECRET_KEY or STRIPE_PRICE_ID not configured",
        )

    front = os.getenv("FRONTEND_URL", "http://localhost:3100").rstrip("/")
    success = (body.success_url or f"{front}/billing?tenant={tenant_id}&checkout=success").strip()
    cancel = (body.cancel_url or f"{front}/billing?tenant={tenant_id}&checkout=cancel").strip()

    stripe_sdk.api_key = sk
    try:
        session = stripe_sdk.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price, "quantity": 1}],
            success_url=success,
            cancel_url=cancel,
            client_reference_id=tenant_id,
            metadata={"tenant_id": tenant_id},
            subscription_data={"metadata": {"tenant_id": tenant_id}},
        )
    except Exception as e:
        logger.warning("Stripe Checkout session failed: %s", e)
        raise HTTPException(status_code=502, detail="Stripe checkout error") from e

    url = session.url
    if not url:
        raise HTTPException(status_code=502, detail="Missing checkout URL from Stripe")
    return {"url": url}
