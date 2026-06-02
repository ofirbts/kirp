from __future__ import annotations

from fastapi import HTTPException, status


def require_non_wildcard_tenant(tenant_id: str) -> str:
    t = (tenant_id or "").strip()
    if not t or t == "*":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id required",
        )
    return t


def require_same_tenant(ctx_tenant: str, resource_tenant: str | None) -> None:
    if not resource_tenant or resource_tenant != ctx_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant scope mismatch",
        )
