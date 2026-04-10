"""
SaaS self-serve onboarding: create Postgres tenant, default space, trial lifecycle, API keys.

``secret_key`` is shown once; only its SHA-256 is stored in ``tenants.extra``.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from src.core.schema_engine import get_schema_engine
from src.models.tenant import Tenant, Space
from src.services.tenants_service import _slug

logger = logging.getLogger(__name__)

TRIAL_DAYS = 30


class OnboardingError(ValueError):
    """Validation or conflict (e.g. tenant name taken)."""


async def create_tenant(tenant_name: str, email: str) -> dict[str, Any]:
    """
    Create a new tenant row + default ``all`` space, trial lifecycle, and API key material.

    Returns ``tenant_id``, ``publishable_key``, ``secret_key`` (plaintext once), and trial metadata.
    """
    name = (tenant_name or "").strip()
    if not name:
        raise OnboardingError("tenant_name is required")
    em = (email or "").strip().lower()
    if not em or "@" not in em:
        raise OnboardingError("valid email is required")

    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        dup = await session.execute(select(Tenant).where(Tenant.name == name).limit(1))
        if dup.scalar_one_or_none() is not None:
            raise OnboardingError("tenant name already registered")

        tid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=TRIAL_DAYS)
        slug = _slug(name)

        raw_secret = secrets.token_urlsafe(32)
        secret_key = f"kirp_sk_{raw_secret}"
        secret_hash = hashlib.sha256(secret_key.encode("utf-8")).hexdigest()
        publishable_key = f"kirp_pk_{secrets.token_urlsafe(24)}"

        tenant = Tenant(
            id=tid,
            name=name,
            extra={
                "slug": slug,
                "lifecycle": "trial",
                "onboarding_email": em,
                "publishable_key": publishable_key,
                "secret_key_hash": secret_hash,
                "trial_ends_at": trial_end.isoformat().replace("+00:00", "Z"),
            },
            created_at=now,
            updated_at=now,
        )
        space = Space(
            id=uuid.uuid4(),
            tenant_id=tid,
            kind="shared",
            name="all",
            extra={},
            created_at=now,
            updated_at=now,
        )
        session.add(tenant)
        session.add(space)
        await session.commit()

        logger.info("Onboarding created tenant id=%s name=%s", tid, name)

        return {
            "tenant_id": str(tid),
            "tenant_name": name,
            "email": em,
            "lifecycle": "trial",
            "trial_ends_at": trial_end.isoformat().replace("+00:00", "Z"),
            "trial_days": TRIAL_DAYS,
            "publishable_key": publishable_key,
            "secret_key": secret_key,
        }
    finally:
        await session.close()
