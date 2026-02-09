"""
V1 Users API — Dashboard compatibility under /api/v1.

GET /api/v1/users/me, POST /api/v1/users/assign.
me delegates to auth/me shape; assign is a minimal stub.
"""

from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.core.auth import get_user_store
from src.core.jwt_utils import decode_token


router = APIRouter(prefix="/api/v1/users", tags=["V1 Users"])


class AssignBody(BaseModel):
    user_id: str
    role: str | None = None
    space_id: str | None = None


@router.get("/me")
async def me_v1(request: Request):
    """
    Return current user (same shape as /api/v1/auth/me).
    Uses JWT from Authorization or default dev user when SKIP_AUTH/ENV=local.
    """
    skip = os.getenv("SKIP_AUTH", "").lower() in ("1", "true", "yes")
    dev_env = os.getenv("ENV", "").lower() in ("development", "local")
    auth = (request.headers.get("Authorization") or "").strip()
    token = auth[7:].strip() if auth.startswith("Bearer ") else ""

    if (skip or dev_env) and not token:
        return {
            "id": "dev",
            "email": "dev@local",
            "name": "Developer",
            "tenant_id": "default",
            "roles": ["admin"],
        }

    if token:
        try:
            payload = decode_token(token)
            store = get_user_store()
            user_id = payload.get("user_id")
            if user_id:
                user = await store.get_user_by_id(user_id)
                if user:
                    return {
                        "id": user.id,
                        "email": user.email,
                        "name": user.name,
                        "tenant_id": user.tenant_id,
                        "roles": user.roles,
                    }
            return {
                "id": payload.get("user_id") or "dev",
                "email": "dev@example.com",
                "name": "Dev",
                "tenant_id": payload.get("tenant_id") or "default",
                "roles": payload.get("roles") or ["admin"],
            }
        except Exception:
            if skip or dev_env:
                return {
                    "id": "dev",
                    "email": "dev@local",
                    "name": "Developer",
                    "tenant_id": "default",
                    "roles": ["admin"],
                }
            raise

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")


@router.post("/assign")
async def assign_v1(
    body: AssignBody,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Assign user to role/space. Minimal stub: returns ok."""
    return {"ok": True, "user_id": body.user_id, "role": body.role, "space_id": body.space_id}
