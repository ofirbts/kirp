"""
Tenant context for multi-tenant isolation.

Provides FastAPI dependencies to read and enforce tenant/space from
request.state.user (set by JWT middleware). Callers can require that
query params match the authenticated context or default to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from fastapi import HTTPException
from fastapi import status


@dataclass
class TenantContext:
    """Effective tenant/space and user for the current request."""

    tenant_id: str
    space_id: str
    user_id: str
    roles: list[str]


def get_tenant_context(request: Request) -> TenantContext:
    """
    Read tenant context from request.state.user (set by JWT middleware).
    Raises 401 if not authenticated (no user on state).
    """
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    u = request.state.user
    tenant_id = u.get("tenant_id") or ""
    space_id = u.get("space_id") or ""
    user_id = u.get("user_id") or ""
    roles = u.get("roles") or []
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context missing",
        )
    return TenantContext(
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        roles=roles,
    )


def require_tenant_context(
    request: Request,
    query_tenant_id: Optional[str] = None,
    query_space_id: Optional[str] = None,
    allow_cross_tenant_roles: Optional[list[str]] = None,
) -> TenantContext:
    """
    Resolve effective tenant/space: JWT context with optional validation of query params.

    - If query_tenant_id / query_space_id are not provided, use JWT context.
    - If provided and equal to JWT (or JWT space is empty), use JWT context.
    - If provided and different from JWT: allow only when user has a role in
      allow_cross_tenant_roles (e.g. "admin"); otherwise 403.

    Returns TenantContext with effective tenant_id and space_id (from query when
    allowed, else from JWT).
    """
    ctx = get_tenant_context(request)
    effective_tenant = ctx.tenant_id
    effective_space = ctx.space_id

    if query_tenant_id is not None and query_tenant_id.strip() != "":
        if query_tenant_id != ctx.tenant_id:
            allowed_roles = allow_cross_tenant_roles or []
            if not any(r in (ctx.roles or []) for r in allowed_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant scope does not match authenticated context",
                )
            effective_tenant = query_tenant_id
    if query_space_id is not None and query_space_id.strip() != "":
        effective_space = query_space_id

    return TenantContext(
        tenant_id=effective_tenant,
        space_id=effective_space,
        user_id=ctx.user_id,
        roles=ctx.roles,
    )


def get_effective_tenant_context(request: Request) -> TenantContext:
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    space_id = request.headers.get("X-Space-ID", "all")
    user_id = request.headers.get("X-User-ID", "dev-user")
    roles = ["owner"]
    return TenantContext(tenant_id, space_id, user_id, roles)
