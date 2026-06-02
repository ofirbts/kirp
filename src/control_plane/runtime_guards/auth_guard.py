from __future__ import annotations

from fastapi import HTTPException, status


def require_any_role(user_roles: list[str] | None, required: set[str]) -> None:
    roles = set(user_roles or [])
    if not required:
        return
    if not roles.intersection(required):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient role",
        )
