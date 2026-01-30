"""
Audit API — minimal JSON endpoint for the frontend.

Backs:
- GET /api/audit
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.observability.metrics import MetricsCollector
from src.schemas.api_models import AuditListResponse
from src.services import audit_service


router = APIRouter(prefix="/api", tags=["Audit"])
_metrics = MetricsCollector("kirp_audit")


@router.get("/audit", response_model=AuditListResponse)
async def list_audit_entries(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    actorId: str | None = Query(None),
    resourceType: str | None = Query(None),
    action: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> AuditListResponse:
    """List audit entries (read-only, backed by service layer). Tenant/space enforced via JWT context."""
    entries = await audit_service.list_audit_entries(
        actor_id=actorId,
        tenant_id=ctx.tenant_id,
        resource_type=resourceType,
        action=action,
        from_ts=from_,
        to_ts=to,
    )
    _metrics.inc("list_requests_total", labels={"tenant_id": ctx.tenant_id})
    return AuditListResponse(data=entries, meta={})

