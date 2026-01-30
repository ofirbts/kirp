"""
Policies API — minimal JSON endpoints for the frontend.

Backs:
- GET /api/policies
- GET /api/policies/{id}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import PoliciesListResponse, PolicyItemResponse
from src.services import policies_service


router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("", response_model=PoliciesListResponse)
async def list_policies(
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> PoliciesListResponse:
    """List policies (read-only, backed by service layer). Tenant context required but not yet used for filtering."""
    policies = await policies_service.list_policies()
    return PoliciesListResponse(data=policies, meta={})


@router.get("/{policy_id}", response_model=PolicyItemResponse)
async def get_policy(policy_id: str) -> PolicyItemResponse:
    """Get a single policy (read-only, backed by service layer)."""
    policy = await policies_service.get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicyItemResponse(data=policy, meta={})

