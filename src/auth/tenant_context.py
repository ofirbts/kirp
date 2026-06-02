"""
Tenant context for multi-tenant isolation.

Provides FastAPI dependencies to read and enforce tenant/space from
request.state.user (set by JWT middleware). In local/development mode
(SKIP_AUTH=1 or ENV=local|development), always resolves a valid context
and never raises 401/403.
"""

from __future__ import annotations

import os
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


# Default context for local/development when unauthenticated (dashboard-friendly).
DEFAULT_LOCAL_CONTEXT = TenantContext(
    tenant_id="default",
    space_id="default",
    user_id="dev",
    roles=["admin"],
)


def is_local_or_skip_auth() -> bool:
    return os.getenv("SKIP_AUTH", "").lower() in ("1", "true", "yes")


def get_tenant_context(request: Request) -> TenantContext:
    """
    Read tenant context from request.state.user (set by JWT middleware).
    - If request.state.user exists with valid tenant_id and user_id → use EXACTLY as-is (no dev fallback).
    - If no user AND (SKIP_AUTH=1 or local dev) → return DEFAULT_LOCAL_CONTEXT.
    - If no user in production → 401.
    - If user exists but missing tenant_id or user_id → 403 (never silently use "dev").
    """
    if not hasattr(request.state, "user") or not request.state.user:
        if is_local_or_skip_auth():
            return DEFAULT_LOCAL_CONTEXT
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    u = request.state.user
    tenant_id = (u.get("tenant_id") or "").strip()
    space_id = (u.get("space_id") or "").strip() or "all"
    user_id_raw = u.get("user_id")
    user_id = user_id_raw if isinstance(user_id_raw, str) and user_id_raw.strip() else None
    roles = u.get("roles") or []

    # Never fall back to "dev" when JWT/user is present. Require valid user_id.
    if not user_id:
        if is_local_or_skip_auth():
            return DEFAULT_LOCAL_CONTEXT
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id required in token",
        )
    if not tenant_id:
        if is_local_or_skip_auth():
            return DEFAULT_LOCAL_CONTEXT
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context missing",
        )
    return TenantContext(
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id.strip(),
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
    """
    Use get_tenant_context (JWT) for all authenticated flows.
    When SKIP_AUTH=1 or local dev, get_tenant_context handles defaults.
    When auth required, use JWT only — do not fall back to header defaults.
    """
    return get_tenant_context(request)
