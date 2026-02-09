"""
Users & Roles API — minimal JSON endpoints for the frontend.

Backs:
- GET /api/users
- GET /api/roles
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import UsersListResponse, RolesListResponse
from src.services import users_service


router = APIRouter(prefix="/api", tags=["Users"])


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> UsersListResponse:
    """List users (read-only, backed by service layer). Tenant context required but not yet used for filtering."""
    users = await users_service.list_users()
    return UsersListResponse(data=users, meta={})


@router.get("/roles", response_model=RolesListResponse)
async def list_roles(
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> RolesListResponse:
    """List roles (read-only, backed by service layer). Tenant context required but not yet used for filtering."""
    roles = await users_service.list_roles()
    return RolesListResponse(data=roles, meta={})

