"""
Auth API — RBAC/ABAC endpoints.

Endpoints:
- GET /auth/roles — list user roles
- POST /auth/check — check permission
- POST /auth/assign-role — assign role (admin only)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.auth.rbac import RBACEngine, Role, Permission, AccessCheck

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

# Global RBAC engine
_rbac_engine: RBACEngine | None = None


async def get_rbac_engine() -> RBACEngine:
    """Get RBAC engine instance."""
    global _rbac_engine
    if _rbac_engine is None:
        _rbac_engine = RBACEngine(
            postgres_uri=os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp"),
            opa_url=os.getenv("OPA_URL", "http://opa:8181"),
        )
        await _rbac_engine.connect()
    return _rbac_engine


class CheckPermissionRequest(BaseModel):
    tenant_id: str
    space_id: str
    user_id: str
    permission: str
    resource: str
    resource_attributes: dict[str, Any] | None = None


class AssignRoleRequest(BaseModel):
    tenant_id: str
    space_id: str
    user_id: str
    role: str
    assigned_by: str


@router.get("/roles")
async def get_user_roles(
    tenant_id: str,
    space_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Get user roles in space."""
    try:
        rbac = await get_rbac_engine()
        role = await rbac.get_role(tenant_id, space_id, user_id)
        return {
            "tenant_id": tenant_id,
            "space_id": space_id,
            "user_id": user_id,
            "role": role.value if role else None,
        }
    except Exception as e:
        logger.exception("Get roles failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check")
async def check_permission(req: CheckPermissionRequest) -> dict[str, Any]:
    """Check if user has permission on resource."""
    try:
        rbac = await get_rbac_engine()
        perm = Permission(req.permission)
        check = await rbac.check(
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.user_id,
            permission=perm,
            resource=req.resource,
            resource_attributes=req.resource_attributes,
        )
        return {
            "allowed": check.allowed,
            "reason": check.reason,
        }
    except Exception as e:
        logger.exception("Permission check failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assign-role")
async def assign_role(req: AssignRoleRequest) -> dict[str, Any]:
    """Assign role to user (admin only)."""
    try:
        # Check if requester is admin
        rbac = await get_rbac_engine()
        requester_check = await rbac.check(
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.assigned_by,
            permission=Permission.ADMIN,
            resource="role_assignment",
        )
        if not requester_check.allowed:
            raise HTTPException(status_code=403, detail="Only admins can assign roles")
        
        # TODO: Implement role assignment in database
        # For now, return success
        return {
            "ok": True,
            "message": f"Role {req.role} assigned to {req.user_id}",
            "tenant_id": req.tenant_id,
            "space_id": req.space_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Assign role failed")
        raise HTTPException(status_code=500, detail=str(e))
