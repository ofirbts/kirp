"""
KIRP API key authentication: ``Authorization: Kirp <secret>`` (same string as onboarding ``secret_key``).

Resolves tenant via ``tenants.extra.secret_key_hash`` (SHA-256 hex). Blocks ``suspended`` and expired ``trial``.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from src.core.schema_engine import get_schema_engine
from src.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Paths that skip API-key handling (no ``Kirp`` required; normal JWT / SKIP_AUTH applies).
_PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/health",
    "/healthz",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/onboarding",
    "/api/v1/stripe/webhook",
    "/api/v1/stripe/create-payment-intent",
)


def _is_public_path(path: str) -> bool:
    if path.rstrip("/") in ("/", ""):
        return False
    p = path.split("?", 1)[0]
    return any(p == px or p.startswith(px + "/") for px in _PUBLIC_PATH_PREFIXES)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin") or ""
    allowed = {
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    env = os.getenv("CORS_ORIGINS", "")
    if env:
        allowed |= {o.strip() for o in env.split(",") if o.strip()}
    if origin.rstrip("/") in {a.rstrip("/") for a in allowed}:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {
        "Access-Control-Allow-Origin": "http://localhost:3100",
        "Access-Control-Allow-Credentials": "true",
    }


def hash_kirp_secret(secret: str) -> str:
    return hashlib.sha256(secret.strip().encode("utf-8")).hexdigest()


def _parse_kirp_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    raw = authorization.strip()
    scheme, _, rest = raw.partition(" ")
    if scheme.lower() != "kirp":
        return None
    token = rest.strip()
    return token or None


def _trial_still_valid(extra: dict[str, Any]) -> bool:
    if (extra or {}).get("lifecycle") != "trial":
        return True
    ends = (extra or {}).get("trial_ends_at")
    if not ends or not isinstance(ends, str):
        return True
    try:
        iso = ends.replace("Z", "+00:00") if ends.endswith("Z") else ends
        end_dt = datetime.fromisoformat(iso)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) <= end_dt
    except (ValueError, TypeError):
        return True


async def resolve_kirp_principal(secret: str) -> dict[str, Any] | None:
    """
    Look up tenant by API secret; return a ``request.state.user``-shaped dict, or ``None``.
    """
    h = hash_kirp_secret(secret)
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(Tenant))
        for row in result.scalars():
            ex = row.extra or {}
            if ex.get("secret_key_hash") != h:
                continue
            lifecycle = str(ex.get("lifecycle") or "active")
            if lifecycle == "suspended":
                return {"_blocked": True, "reason": "tenant_suspended", "status": 403}
            if not _trial_still_valid(ex):
                return {"_blocked": True, "reason": "trial_expired", "status": 403}
            tid = str(row.id)
            pk = ex.get("publishable_key")
            return {
                "tenant_id": tid,
                "space_id": "all",
                "user_id": "api_key",
                "roles": ["api_key"],
                "auth_via": "kirp_api_key",
                "publishable_key": pk,
            }
        return None
    finally:
        await session.close()


async def kirp_api_key_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if _is_public_path(path):
        return await call_next(request)

    auth_header = request.headers.get("Authorization") or ""
    token = _parse_kirp_token(auth_header)
    if token is None:
        return await call_next(request)

    try:
        principal = await resolve_kirp_principal(token)
    except Exception as e:
        logger.warning("Kirp API key lookup failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"detail": "API key validation temporarily unavailable"},
            headers=_cors_headers(request),
        )

    if principal is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
            headers=_cors_headers(request),
        )

    if principal.get("_blocked"):
        return JSONResponse(
            status_code=int(principal.get("status") or 403),
            content={"detail": principal.get("reason", "forbidden")},
            headers=_cors_headers(request),
        )

    request.state.user = {
        "tenant_id": principal["tenant_id"],
        "space_id": principal["space_id"],
        "user_id": principal["user_id"],
        "roles": principal.get("roles") or [],
    }
    return await call_next(request)
