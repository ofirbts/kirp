from __future__ import annotations

from typing import Any, Mapping

from fastapi import HTTPException, status


def require_event_tenant(event: Mapping[str, Any], ctx_tenant: str) -> None:
    et = event.get("tenant_id")
    if not isinstance(et, str) or not et.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="event tenant_id missing",
        )
    if et.strip() != ctx_tenant.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="event tenant scope mismatch",
        )
