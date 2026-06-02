"""
Tenants API — JSON endpoints for the frontend.

Backs:
- GET /api/tenants
- POST /api/tenants
- GET /api/tenants/{tenant_id}/spaces
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import TenantsListResponse, SpacesListResponse
from src.services import tenants_service


router = APIRouter(prefix="/api/tenants", tags=["Tenants"])


class CreateTenantRequest(BaseModel):
    name: str
    slug: str | None = None


@router.get("", response_model=TenantsListResponse)
async def list_tenants(
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> TenantsListResponse:
    """List tenants (Postgres-backed). Ensures default tenant if empty."""
    tenants = await tenants_service.list_tenants()
    return TenantsListResponse(data=tenants, meta={})


@router.post("", status_code=201)
async def create_tenant(
    body: CreateTenantRequest,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Create a new tenant and default space (requires admin/owner)."""
    tenant = await tenants_service.create_tenant(name=body.name, slug=body.slug)
    return {"data": tenant, "meta": {}}


@router.get("/{tenant_id}/spaces", response_model=SpacesListResponse)
async def list_spaces_for_tenant(
    tenant_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> SpacesListResponse:
    """List spaces for a tenant."""
    spaces = await tenants_service.list_spaces_for_tenant(tenant_id)
    return SpacesListResponse(data=spaces, meta={})

