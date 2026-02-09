"""
V1 domain APIs — signals, visuals, content intelligence.

(History 2.0 is in v1_history.)
Backs:
- GET/POST /api/v1/signals
- GET/POST /api/v1/visuals
- GET/POST /api/v1/content/intelligence
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.core import domain_store


router = APIRouter(prefix="/api/v1", tags=["V1 Domain"])


@router.get("/signals")
async def list_signals(
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """List signals (topic, relevance, urgency, trend) for tenant."""
    items = await domain_store.list_signals(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or None,
        limit=100,
    )
    return {"data": items, "meta": {"tenantId": ctx.tenant_id}}


class CreateSignalBody(BaseModel):
    topic: str
    relevance: int = 80
    urgency: str = "medium"
    trend: str = "stable"
    source: str = "api"


@router.post("/signals", status_code=201)
async def create_signal(
    body: CreateSignalBody,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Create a signal (for seeding)."""
    sid = await domain_store.upsert_signal(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        topic=body.topic,
        relevance=body.relevance,
        urgency=body.urgency,
        trend=body.trend,
        source=body.source,
    )
    return {"ok": True, "id": sid}


@router.get("/visuals")
async def list_visuals(
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """List saved visuals/dashboards for tenant."""
    items = await domain_store.list_visuals(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or None,
        limit=100,
    )
    return {"data": items, "meta": {"tenantId": ctx.tenant_id}}


class CreateVisualBody(BaseModel):
    name: str
    chart_type: str = "bar"
    config: dict[str, Any] | None = None


@router.post("/visuals", status_code=201)
async def create_visual(
    body: CreateVisualBody,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Create a visual (for seeding)."""
    vid = await domain_store.create_visual(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        name=body.name,
        chart_type=body.chart_type,
        config=body.config,
    )
    return {"ok": True, "id": vid}


@router.get("/content/intelligence")
async def list_content_intelligence(
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """List content intelligence entries (topic, platform, status) for tenant."""
    items = await domain_store.list_content_intelligence(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or None,
        limit=100,
    )
    return {"data": items, "meta": {"tenantId": ctx.tenant_id}}


class CreateContentIntelligenceBody(BaseModel):
    trace_id: str
    topic_hint: str
    platform: str
    status: str = "draft"
    content_preview: str | None = None


@router.post("/content/intelligence", status_code=201)
async def create_content_intelligence(
    body: CreateContentIntelligenceBody,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Create a content intelligence entry (for seeding)."""
    cid = await domain_store.create_content_intelligence(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        trace_id=body.trace_id,
        topic_hint=body.topic_hint,
        platform=body.platform,
        status=body.status,
        content_preview=body.content_preview,
    )
    return {"ok": True, "id": cid}
