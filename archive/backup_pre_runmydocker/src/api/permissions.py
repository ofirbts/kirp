"""
Permissions API — minimal JSON endpoint for the frontend.

Backs:
- POST /api/permissions/effective

Note: The modern frontend primarily uses GET
/api/users/{user_id}/effective-permissions, which is implemented in
src.main. This endpoint exists to keep the typed ApiClient compatible.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import EffectivePermissionsResponse


router = APIRouter(prefix="/api/permissions", tags=["Permissions"])


@router.post("/effective", response_model=EffectivePermissionsResponse)
async def get_effective_permissions(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    body: dict[str, Any] = Body(...),
) -> EffectivePermissionsResponse:
    """
    Compute effective permissions.

    In Phase 4.1 this returns an empty permission set. Real resolution will be
    implemented in later phases. Tenant context is required to enforce scope.
    """
    return EffectivePermissionsResponse(data=[], meta={})

