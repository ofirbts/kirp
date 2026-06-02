"""
JWT utilities for KIRP Enterprise.

Responsibilities:
- Create signed JWT access tokens with standard and domain-specific claims.
- Decode and validate incoming tokens for API requests.

This module is intentionally small and framework-agnostic so it can be used
from FastAPI middleware, dependencies, or background workers.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException, status
from jose import JWTError, jwt


# In production, JWT_SECRET **must** be set. For dev/local, we fall back to a
# deterministic but obviously insecure default. JWT_SECRET_PREVIOUS supports
# seamless key rotation (decode will try both current and previous).
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_SECRET_PREVIOUS = os.getenv("JWT_SECRET_PREVIOUS")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))
)


def create_access_token(
    claims: Dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Expected claims include:
    - user_id (str)
    - tenant_id (str)
    - roles (list[str])
    - permissions (list[str])
    """
    to_encode = claims.copy()

    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + expires_delta

    # Standard registered claims
    to_encode.setdefault("iat", int(now.timestamp()))
    to_encode.setdefault("exp", int(expire.timestamp()))

    token = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises HTTPException(401) on any validation error.
    """
    def _decode_with_secret(secret: str) -> Dict[str, Any]:
        return jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},
        )

    try:
        try:
            payload = _decode_with_secret(JWT_SECRET)
        except JWTError:
            if JWT_SECRET_PREVIOUS:
                payload = _decode_with_secret(JWT_SECRET_PREVIOUS)
            else:
                raise
        # Minimal shape sanity checks – more can be added later.
        if "user_id" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user_id",
            )
        if "tenant_id" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing tenant_id",
            )
        return payload
    except HTTPException:
        # Bubble up our own explicit errors unchanged.
        raise
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

