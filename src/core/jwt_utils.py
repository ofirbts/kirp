"""
JWT helpers and FastAPI-friendly dependencies.

Thin wrapper around src.auth.jwt so the rest of the codebase can treat this as
the canonical place for JWT creation / decoding and auth dependencies.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from fastapi import Depends, HTTPException, Request, status

from src.auth import jwt as core_jwt
from src.auth.tenant_context import get_tenant_context, TenantContext


def create_access_token(user_id: str, tenant_id: str, roles: list[str] | None = None, expires_in_seconds: int | None = None) -> str:
  """Create access token with minimal standard claims."""
  claims: Dict[str, Any] = {
    "user_id": user_id,
    "tenant_id": tenant_id,
    "roles": roles or ["user"],
  }
  expires_delta = None
  if expires_in_seconds is not None:
    expires_delta = timedelta(seconds=expires_in_seconds)
  return core_jwt.create_access_token(claims, expires_delta=expires_delta)


def decode_token(token: str) -> Dict[str, Any]:
  """Decode token and return payload or raise HTTPException(401)."""
  return core_jwt.decode_access_token(token)


async def require_auth(request: Request) -> Dict[str, Any]:
  """
  FastAPI dependency: require a valid JWT in Authorization header.

  Also populates request.state.user so tenant_context works.
  """
  auth = request.headers.get("Authorization") or ""
  if not auth.startswith("Bearer "):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Authorization header missing or invalid",
    )
  token = auth[7:].strip()
  payload = decode_token(token)
  # Normalize into request.state.user
  request.state.user = {
    "tenant_id": payload.get("tenant_id"),
    "space_id": payload.get("space_id") or "all",
    "user_id": payload.get("user_id"),
    "roles": payload.get("roles") or [],
  }
  return payload


def require_role(role: str):
  """
  Dependency factory for admin-only / role-guarded routes.

  Usage:
      @router.get("/admin", dependencies=[Depends(require_role("admin"))])
  """

  async def _dep(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    roles = ctx.roles or []
    if role not in roles:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient role",
      )
    return ctx

  return _dep

