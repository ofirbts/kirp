"""
V1 Tenants & Spaces — Dashboard compatibility under /api/v1.

GET/POST /api/v1/tenants, GET/POST /api/v1/spaces.
Uses existing tenants_service; same shapes as /api/tenants.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.services import tenants_service
from src.services.tenants_service import TenantLifecycleError, update_tenant_lifecycle


router = APIRouter(prefix="/api/v1", tags=["V1 Tenants & Spaces"])


class CreateTenantBody(BaseModel):
    name: str
    slug: str | None = None


class CreateSpaceBody(BaseModel):
    name: str
    slug: str | None = None


class SetTenantLifecycleBody(BaseModel):
    lifecycle: str


@router.get("/tenants")
async def list_tenants_v1(
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """List tenants. Returns { data: [...], meta: {} }."""
    tenants = await tenants_service.list_tenants()
    return {"data": tenants, "meta": {}}


@router.post("/tenants", status_code=201)
async def create_tenant_v1(
    body: CreateTenantBody,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Create a tenant and default space."""
    tenant = await tenants_service.create_tenant(name=body.name, slug=body.slug)
    return {"data": tenant, "meta": {}}


@router.patch("/tenants/{tenant_id}/lifecycle")
async def patch_tenant_lifecycle_v1(
    tenant_id: str,
    body: SetTenantLifecycleBody,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Update SaaS lifecycle (same tenant as JWT / dev context). Stripe webhooks can use service layer directly."""
    if ctx.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    try:
        tenant = await update_tenant_lifecycle(tenant_id, body.lifecycle)
    except TenantLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"data": tenant, "meta": {}}


@router.get("/spaces")
async def list_spaces_v1(
    tenant_id: str = Query("default", description="Tenant ID"),
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """List spaces for a tenant. Returns { data: [...], meta: {} }."""
    spaces = await tenants_service.list_spaces_for_tenant(tenant_id)
    return {"data": spaces, "meta": {}}


@router.post("/spaces", status_code=201)
async def create_space_v1(
    body: CreateSpaceBody,
    tenant_id: str = Query("default", description="Tenant ID"),
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Create a space in a tenant. Uses create_space_if_not_exists then returns list."""
    space_id = await tenants_service.create_space_if_not_exists(
        tenant_id, name=body.name or "all", kind="shared"
    )
    spaces = await tenants_service.list_spaces_for_tenant(tenant_id)
    created = next((s for s in spaces if getattr(s, "id", None) == space_id), None)
    if created is None and spaces:
        created = spaces[0]
    out = created.model_dump() if hasattr(created, "model_dump") else (created if created else {"id": space_id, "tenant_id": tenant_id, "name": body.name})
    return {"data": out, "meta": {}}
