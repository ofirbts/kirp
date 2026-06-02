"""
Context API — Accessible spaces and context switching for the shared context model.

Used by the UI to drive tenant/space selectors and to validate access before RAG/SchemaEngine calls.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.auth.tenant_context import get_tenant_context
from src.services.context_service import (
    get_accessible_space_ids,
    list_spaces_for_context,
    can_access_space,
)

router = APIRouter(prefix="/api/v1", tags=["context"])


@router.get("/context/accessible-spaces")
async def get_accessible_spaces(request: Request) -> dict:
    """
    Return list of space_ids the user can access in this tenant (JWT / dev context only).
    """
    ctx = get_tenant_context(request)
    space_ids = await get_accessible_space_ids(ctx.tenant_id, ctx.user_id)
    return {"tenant_id": ctx.tenant_id, "user_id": ctx.user_id, "space_ids": space_ids}


@router.get("/context/spaces")
async def get_spaces_for_context(request: Request) -> dict:
    """
    Return list of { space_id, role } for context switching (e.g. dropdown).
    """
    ctx = get_tenant_context(request)
    spaces = await list_spaces_for_context(ctx.tenant_id, ctx.user_id)
    return {"tenant_id": ctx.tenant_id, "user_id": ctx.user_id, "spaces": spaces}


@router.get("/context/can-access")
async def check_can_access(
    request: Request,
    space_id: str = Query(..., description="Space ID to check"),
) -> dict:
    """Check whether the authenticated user can access the given space."""
    ctx = get_tenant_context(request)
    allowed = await can_access_space(ctx.tenant_id, ctx.user_id, space_id)
    return {
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "space_id": space_id,
        "allowed": allowed,
    }
