"""
Admin bootstrap API for KIRP.

This endpoint is the ONLY supported way to initialize a clean production
environment with initial tenants, spaces, users, and roles. It is designed
to go through the same SchemaEngine and models used by the rest of the app
so that seed data is consistent with real production behavior.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status

from src.core.config import get_settings
from src.core.schema_engine import SchemaEngine
from src.services.admin_service import BootstrapError, bootstrap_system


router = APIRouter(prefix="/api/admin", tags=["Admin"])


_schema_engine: SchemaEngine | None = None


async def get_schema_engine_for_admin() -> SchemaEngine:
    """
    Local SchemaEngine provider to avoid circular imports with src.main.

    This mirrors the configuration used in src.main.get_schema_engine.
    """
    global _schema_engine
    if _schema_engine is None:
        settings = get_settings()
        _schema_engine = SchemaEngine(settings.postgres_uri)
        await _schema_engine.connect()
    return _schema_engine


async def get_async_session(schema_engine: SchemaEngine = Depends(get_schema_engine_for_admin)):
    """Provide an AsyncSession from SchemaEngine for use in the bootstrap endpoint."""
    return await schema_engine.get_session()


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def admin_bootstrap(
    payload: Dict[str, Any] = Body(
        ...,
        description=(
            "Bootstrap payload with keys: 'tenant', 'spaces', 'users', 'roles'. "
            "See seed/domain_spec.md and seed/seed_definition.json for the canonical structure."
        ),
    ),
    session=Depends(get_async_session),
) -> Dict[str, Any]:
    """
    Bootstrap a tenant with spaces, users, and roles.

    Expected payload shape:

    {
      "tenant": { "id": "...", "name": "...", "slug": "...", ... },
      "spaces": [{ "id": "...", "tenant_id": "...", "name": "...", "slug": "...", "purpose": "..." }],
      "users": [{ "id": "...", "email": "...", "name": "...", "tenant_id": "...", "role_ids": [...] }],
      "roles": [{ "id": "...", "name": "...", "description": "...", "permissions": [...] }]
    }
    """
    tenant_spec = payload.get("tenant") or {}
    spaces_spec = payload.get("spaces") or []
    users_spec = payload.get("users") or []
    roles_spec = payload.get("roles") or []

    if not tenant_spec:
        raise HTTPException(status_code=status.NOT_FOUND, detail="tenant spec is required for bootstrap")

    try:
        async with session as s:
            async with s.begin():
                result = await bootstrap_system(
                    s,
                    tenant_payload=tenant_spec,
                    spaces_payload=spaces_spec,
                    users_payload=users_spec,
                    roles_payload=roles_spec,
                )
        return {"ok": True, "data": result}
    except BootstrapError as exc:
        # Treat bootstrap conflicts / validation issues as 400‑class errors.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        # Surface the real error so clients (e.g. seed_postgres) can debug.
        raise HTTPException(status_code=500, detail=f"bootstrap failed: {exc!r}") from exc

