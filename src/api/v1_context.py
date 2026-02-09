"""
Context API — Accessible spaces and context switching for the shared context model.

Used by the UI to drive tenant/space selectors and to validate access before RAG/SchemaEngine calls.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.context_service import (
    get_accessible_space_ids,
    list_spaces_for_context,
    can_access_space,
)

router = APIRouter(prefix="/api/v1", tags=["context"])


@router.get("/context/accessible-spaces")
async def get_accessible_spaces(
    tenant_id: str = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID"),
) -> dict:
    """
    Return list of space_ids the user can access in this tenant.
    Use this to validate context or to pass allowed_space_ids to RAG/SchemaEngine.
    """
    space_ids = await get_accessible_space_ids(tenant_id, user_id)
    return {"tenant_id": tenant_id, "user_id": user_id, "space_ids": space_ids}


@router.get("/context/spaces")
async def get_spaces_for_context(
    tenant_id: str = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID"),
) -> dict:
    """
    Return list of { space_id, role } for context switching (e.g. dropdown).
    """
    spaces = await list_spaces_for_context(tenant_id, user_id)
    return {"tenant_id": tenant_id, "user_id": user_id, "spaces": spaces}


@router.get("/context/can-access")
async def check_can_access(
    tenant_id: str = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID"),
    space_id: str = Query(..., description="Space ID to check"),
) -> dict:
    """Check whether the user can access the given space."""
    allowed = await can_access_space(tenant_id, user_id, space_id)
    return {"tenant_id": tenant_id, "user_id": user_id, "space_id": space_id, "allowed": allowed}
