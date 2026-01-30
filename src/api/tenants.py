"""
Tenants API — minimal JSON endpoints for the frontend.

Backs:
- GET /api/tenants
- GET /api/tenants/{tenant_id}/spaces
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import TenantsListResponse, SpacesListResponse
from src.services import tenants_service


router = APIRouter(prefix="/api/tenants", tags=["Tenants"])


@router.get("", response_model=TenantsListResponse)
async def list_tenants(
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> TenantsListResponse:
    """List tenants (read-only, backed by service layer). Tenant context required but not yet used for filtering."""
    tenants = await tenants_service.list_tenants()
    return TenantsListResponse(data=tenants, meta={})


@router.get("/{tenant_id}/spaces", response_model=SpacesListResponse)
async def list_spaces_for_tenant(
    tenant_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> SpacesListResponse:
    """List spaces for a tenant (read-only, backed by service layer). Tenant context required but filtering is TODO."""
    spaces = await tenants_service.list_spaces_for_tenant(tenant_id)
    return SpacesListResponse(data=spaces, meta={})

