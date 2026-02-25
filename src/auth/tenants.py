"""
Tenant Engine — Multi-tenant hierarchy.

Root Tenant (Organization)
├── User Private Space
├── Shared Spaces (Family / Partners / Teams)
└── Org Space (Company-wide)

Zero leakage: no cross-tenant access unless explicitly granted.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select

logger = logging.getLogger(__name__)


class SpaceKind(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    TEAM = "team"
    ORG = "org"


@dataclass
class Tenant:
    """Organization root."""

    id: str
    name: str
    metadata: dict[str, Any]
    created_at: datetime


@dataclass
class Space:
    """Tenant space: private, shared, team, or org."""

    id: str
    tenant_id: str
    kind: SpaceKind
    name: str
    owner_id: str | None
    metadata: dict[str, Any]
    created_at: datetime


def _row_to_tenant(t: Any) -> Tenant:
    return Tenant(
        id=str(t.id),
        name=t.name or "",
        metadata=dict(t.extra or {}),
        created_at=t.created_at or datetime.now(timezone.utc),
    )


def _row_to_space(s: Any) -> Space:
    return Space(
        id=str(s.id),
        tenant_id=str(s.tenant_id),
        kind=SpaceKind(s.kind) if s.kind else SpaceKind.PRIVATE,
        name=s.name or "",
        owner_id=getattr(s, "owner_id", None),
        metadata=dict(getattr(s, "extra", None) or {}),
        created_at=s.created_at or datetime.now(timezone.utc),
    )


class TenantEngine:
    """
    Tenant and space management. Persists to PostgreSQL (metadata store).
    """

    def __init__(self, postgres_uri: str) -> None:
        self._postgres_uri = postgres_uri
        self._session_factory: Any = None

    async def connect(self) -> None:
        """Initialize DB connection and create tables if missing."""
        try:
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
            from src.models.base import Base
            import src.models.tenant  # noqa: F401 — register Tenant, Space
            engine = create_async_engine(self._postgres_uri, echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("TenantEngine connected")
        except Exception as e:
            logger.error("TenantEngine connection failed: %s", e)
            raise

    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Fetch tenant by ID or by slug 'default'."""
        if self._session_factory is None:
            await self.connect()
        from src.models.tenant import Tenant as TenantModel
        async with self._session_factory() as session:
            if tenant_id == "default":
                result = await session.execute(
                    select(TenantModel).where(TenantModel.name == "Default").limit(1)
                )
            else:
                try:
                    uid = uuid.UUID(tenant_id)
                    result = await session.execute(select(TenantModel).where(TenantModel.id == uid).limit(1))
                except (ValueError, TypeError):
                    return None
            row = result.scalar_one_or_none()
            return _row_to_tenant(row) if row else None

    async def get_space(self, tenant_id: str, space_id: str) -> Space | None:
        """Fetch space by tenant + space ID."""
        if self._session_factory is None:
            await self.connect()
        try:
            tid = uuid.UUID(tenant_id)
            sid = uuid.UUID(space_id)
        except (ValueError, TypeError):
            return None
        from src.models.tenant import Space as SpaceModel
        async with self._session_factory() as session:
            result = await session.execute(
                select(SpaceModel).where(
                    SpaceModel.id == sid,
                    SpaceModel.tenant_id == tid,
                ).limit(1)
            )
            row = result.scalar_one_or_none()
            return _row_to_space(row) if row else None

    async def list_spaces(self, tenant_id: str, kind: SpaceKind | None = None) -> list[Space]:
        """List spaces for tenant, optionally filtered by kind."""
        if self._session_factory is None:
            await self.connect()
        try:
            tid = uuid.UUID(tenant_id)
        except (ValueError, TypeError):
            return []
        from src.models.tenant import Space as SpaceModel
        async with self._session_factory() as session:
            q = select(SpaceModel).where(SpaceModel.tenant_id == tid)
            if kind is not None:
                q = q.where(SpaceModel.kind == kind.value)
            result = await session.execute(q.order_by(SpaceModel.name))
            return [_row_to_space(s) for s in result.scalars().all()]

    async def ensure_private_space(self, tenant_id: str, user_id: str) -> Space:
        """Ensure user has a private space; create if missing."""
        if self._session_factory is None:
            await self.connect()
        try:
            tid = uuid.UUID(tenant_id)
        except (ValueError, TypeError):
            return Space(
                id=f"private_{user_id}",
                tenant_id=tenant_id,
                kind=SpaceKind.PRIVATE,
                name="Private",
                owner_id=user_id,
                metadata={},
                created_at=datetime.now(timezone.utc),
            )
        from src.models.tenant import Space as SpaceModel
        async with self._session_factory() as session:
            result = await session.execute(
                select(SpaceModel).where(
                    SpaceModel.tenant_id == tid,
                    SpaceModel.kind == SpaceKind.PRIVATE.value,
                    SpaceModel.owner_id == user_id,
                ).limit(1)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return _row_to_space(existing)
            space = SpaceModel(
                id=uuid.uuid4(),
                tenant_id=tid,
                kind=SpaceKind.PRIVATE.value,
                name="Private",
                owner_id=user_id,
                extra={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(space)
            await session.commit()
            return _row_to_space(space)
