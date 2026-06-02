"""
Schema Engine — Service layer for SchemaNode CRUD, trees, and life areas.

- Single source of truth for schema/life-graph data in PostgreSQL.
- All operations are scoped by tenant_id and (optionally) space_id to align with
  the governance policy (tenant isolation, space-level access).
- Session pattern: one async session per operation; write paths commit explicitly
  and invalidate cache; read paths do not commit.
- Cache: list_nodes reads/writes cache when use_cache=True and space_ids is None
  (single-tenant + single-space key); any write (upsert/update/delete) invalidates
  by tenant_id so subsequent reads see fresh data.
"""

from __future__ import annotations

import logging
import os
import ssl
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.cache import (
    CACHE_TTL_SCHEMA,
    get_cached,
    invalidate_cache,
    set_cached,
    _cache_key,
)
from src.models.schema import LIFE_AREA_NAMES, SchemaEntity, SchemaNode

logger = logging.getLogger(__name__)

_schema_engine: SchemaEngine | None = None

# Stable UUID namespace for canonical life-area node IDs (idempotent per tenant+title)
LIFE_AREA_NAMESPACE = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")


def _build_list_nodes_conditions(
    tenant_id: str,
    space_id: str | None,
    space_ids: list[str] | None,
    entity: SchemaEntity | None,
    parent_id: str | None | bool,
    status: str | None,
    include_deleted: bool,
) -> list[Any]:
    """Build SQLAlchemy conditions for list_nodes. Used for both DB and cache key consistency."""
    conditions: list[Any] = [SchemaNode.tenant_id == tenant_id]
    if space_ids is not None:
        conditions.append(SchemaNode.space_id.in_(space_ids))
    elif space_id:
        conditions.append(SchemaNode.space_id == space_id)
    if entity:
        conditions.append(SchemaNode.entity == entity.value)
    if parent_id is False:
        conditions.append(SchemaNode.parent_id.is_(None))
    elif parent_id:
        conditions.append(SchemaNode.parent_id == uuid.UUID(str(parent_id)))
    if status:
        conditions.append(SchemaNode.status == status)
    if not include_deleted:
        conditions.append(SchemaNode.deleted_at.is_(None))
    return conditions


def _build_node_tree(all_nodes: list[dict[str, Any]], root_id: str | None = None) -> dict[str, Any]:
    """Build a tree from flat node list. root_id=None returns {roots, count}; else returns subtree."""
    node_map = {n["id"]: {**n, "children": []} for n in all_nodes}
    roots: list[dict[str, Any]] = []
    for node in all_nodes:
        pid = node.get("parent_id")
        if pid and pid in node_map:
            node_map[pid]["children"].append(node_map[node["id"]])
        elif not pid:
            roots.append(node_map[node["id"]])
    if root_id:
        return node_map.get(root_id, {})
    return {"roots": roots, "count": len(all_nodes)}


async def get_schema_engine(postgres_uri: str | None = None) -> SchemaEngine:
    """Singleton SchemaEngine for use by services and main app."""
    global _schema_engine
    if _schema_engine is None:
        uri = postgres_uri or os.getenv(
            "POSTGRES_URI",
            "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp",
        )
        _schema_engine = SchemaEngine(uri)
        await _schema_engine.connect()
    return _schema_engine


class SchemaEngine:
    """
    Main service layer for SchemaNode in PostgreSQL (multi-tenant, multi-space).

    - Session handling: each method that touches the DB uses a fresh AsyncSession
      via async context manager. Write operations call session.commit() and then
      invalidate_cache(prefix, tenant_id). Read operations do not commit.
    - All queries are scoped by tenant_id; list/get/update/delete also enforce
      tenant_id so that governance (Rego) and data access stay aligned.
    """

    def __init__(self, postgres_uri: str) -> None:
        self._postgres_uri = postgres_uri
        self._session_factory: Any = None

    async def connect(self) -> None:
        """Initialize async engine and session factory. Creates tables if missing."""
        uri_lower = self._postgres_uri.lower()
        use_ssl = (
            "sslmode=require" in uri_lower
            or "neon.tech" in uri_lower
            or "amazonaws.com" in uri_lower
        )
        connect_args: dict[str, Any] = {}
        if use_ssl:
            connect_args["ssl"] = ssl.create_default_context()
        else:
            connect_args["ssl"] = False

        engine = create_async_engine(
            self._postgres_uri,
            echo=False,
            connect_args=connect_args,
        )

        from src.models.base import Base
        import src.models.agent
        import src.models.event
        import src.models.schema
        import src.models.space_membership
        import src.models.tenant
        import src.models.user

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self._session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("SchemaEngine connected to PostgreSQL")

    async def _get_session(self) -> AsyncSession:
        """Return a new AsyncSession. Caller uses it as context manager."""
        if self._session_factory is None:
            await self.connect()
        return self._session_factory()

    async def get_session(self) -> AsyncSession:
        """
        Public helper for components that share this engine (e.g. projections).
        Callers must manage transaction boundaries (commit/rollback).
        """
        return await self._get_session()

    async def upsert_node(
        self,
        tenant_id: str,
        space_id: str,
        entity: SchemaEntity,
        title: str,
        node_id: str | None = None,
        description: str | None = None,
        parent_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_date: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Insert or update a schema node. Always scoped by tenant_id and space_id.
        Returns the node ID (UUID string). Invalidates schema_nodes cache for tenant_id.
        """
        node_uuid = uuid.UUID(node_id) if node_id else uuid.uuid4()
        parent_uuid = uuid.UUID(parent_id) if parent_id else None

        async with await self._get_session() as session:
            try:
                stmt = select(SchemaNode).where(
                    and_(
                        SchemaNode.id == node_uuid,
                        SchemaNode.tenant_id == tenant_id,
                        SchemaNode.deleted_at.is_(None),
                    )
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.title = title
                    existing.description = description
                    existing.parent_id = parent_uuid
                    existing.status = status
                    existing.priority = priority
                    existing.due_date = due_date
                    if metadata:
                        existing.extra = {**(existing.extra or {}), **metadata}
                    existing.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                    await invalidate_cache("schema_nodes", tenant_id)
                    logger.info("SchemaEngine updated node: %s %s", entity.value, node_uuid)
                    return str(node_uuid)

                new_node = SchemaNode(
                    id=node_uuid,
                    tenant_id=tenant_id,
                    space_id=space_id,
                    entity=entity.value,
                    title=title,
                    description=description,
                    parent_id=parent_uuid,
                    status=status,
                    priority=priority,
                    due_date=due_date,
                    extra=metadata or {},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(new_node)
                await session.commit()
                await invalidate_cache("schema_nodes", tenant_id)
                logger.info("SchemaEngine created node: %s %s", entity.value, node_uuid)
                return str(node_uuid)
            except Exception as e:
                await session.rollback()
                logger.error("SchemaEngine upsert failed: %s", e)
                raise

    async def get_node(self, node_id: str, tenant_id: str) -> dict[str, Any] | None:
        """Get a single schema node by ID. Scoped by tenant_id (no commit)."""
        async with await self._get_session() as session:
            try:
                node_uuid = uuid.UUID(node_id)
                stmt = select(SchemaNode).where(
                    and_(
                        SchemaNode.id == node_uuid,
                        SchemaNode.tenant_id == tenant_id,
                        SchemaNode.deleted_at.is_(None),
                    )
                )
                result = await session.execute(stmt)
                node = result.scalar_one_or_none()
                return node.to_dict() if node else None
            except Exception as e:
                logger.error("SchemaEngine get_node failed: %s", e)
                return None

    async def list_nodes(
        self,
        tenant_id: str,
        space_id: str | None = None,
        space_ids: list[str] | None = None,
        entity: SchemaEntity | None = None,
        parent_id: str | None = None,
        status: str | None = None,
        include_deleted: bool = False,
        limit: int = 1000,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List schema nodes with optional filters. Scoped by tenant_id and space_id or space_ids.
        When space_ids is set, used for membership-aware listing (no cache to avoid key explosion).
        Cache: read/write only when use_cache=True and space_ids is None; key includes tenant_id, space_id, filters.
        """
        if use_cache and space_ids is None:
            cache_key = _cache_key(
                "schema_nodes",
                tenant_id,
                space_id,
                entity,
                parent_id,
                status,
                include_deleted,
                limit,
            )
            cached = await get_cached(cache_key)
            if cached is not None:
                return cached

        conditions = _build_list_nodes_conditions(
            tenant_id, space_id, space_ids, entity, parent_id, status, include_deleted
        )

        async with await self._get_session() as session:
            try:
                stmt = select(SchemaNode).where(and_(*conditions)).limit(limit)
                result = await session.execute(stmt)
                nodes = result.scalars().all()
                node_dicts = [n.to_dict() for n in nodes]

                if use_cache and space_ids is None:
                    await set_cached(cache_key, node_dicts, CACHE_TTL_SCHEMA)

                return node_dicts
            except Exception as e:
                logger.error("SchemaEngine list_nodes failed: %s", e)
                return []

    async def list_upcoming_obligations(
        self,
        tenant_id: str,
        space_id: str | None = None,
        space_ids: list[str] | None = None,
        due_from: datetime | None = None,
        due_to: datetime | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """
        List tasks and commitments with due_date in [due_from, due_to].
        Scoped by tenant_id and space_id or space_ids (membership-aware when space_ids provided).
        """
        conditions = [
            SchemaNode.tenant_id == tenant_id,
            SchemaNode.deleted_at.is_(None),
            SchemaNode.due_date.isnot(None),
            or_(
                SchemaNode.entity == SchemaEntity.TASK.value,
                SchemaNode.entity == SchemaEntity.COMMITMENT.value,
            ),
        ]
        if space_ids is not None:
            conditions.append(SchemaNode.space_id.in_(space_ids))
        elif space_id:
            conditions.append(SchemaNode.space_id == space_id)
        if due_from is not None:
            conditions.append(SchemaNode.due_date >= due_from)
        if due_to is not None:
            conditions.append(SchemaNode.due_date <= due_to)

        async with await self._get_session() as session:
            try:
                stmt = (
                    select(SchemaNode)
                    .where(and_(*conditions))
                    .order_by(SchemaNode.due_date.asc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                nodes = result.scalars().all()
                return [n.to_dict() for n in nodes]
            except Exception as e:
                logger.error("SchemaEngine list_upcoming_obligations failed: %s", e)
                return []

    async def update_node(
        self,
        node_id: str,
        tenant_id: str,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_date: datetime | None = None,
        parent_id: str | None = None,
        metadata_merge: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Partial update of a schema node. Scoped by tenant_id. Invalidates cache for tenant_id.
        Returns updated node dict or None if not found.
        """
        async with await self._get_session() as session:
            try:
                node_uuid = uuid.UUID(node_id)
                stmt = select(SchemaNode).where(
                    and_(
                        SchemaNode.id == node_uuid,
                        SchemaNode.tenant_id == tenant_id,
                        SchemaNode.deleted_at.is_(None),
                    )
                )
                result = await session.execute(stmt)
                node = result.scalar_one_or_none()
                if not node:
                    return None
                if title is not None:
                    node.title = title
                if description is not None:
                    node.description = description
                if status is not None:
                    node.status = status
                if priority is not None:
                    node.priority = priority
                if due_date is not None:
                    node.due_date = due_date
                if parent_id is not None:
                    node.parent_id = uuid.UUID(parent_id) if parent_id else None
                if metadata_merge is not None:
                    node.extra = {**(node.extra or {}), **metadata_merge}
                node.updated_at = datetime.now(timezone.utc)
                await session.commit()
                await invalidate_cache("schema_nodes", tenant_id)
                return node.to_dict()
            except Exception as e:
                await session.rollback()
                logger.error("SchemaEngine update_node failed: %s", e)
                raise

    async def delete_node(self, node_id: str, tenant_id: str, soft: bool = True) -> bool:
        """
        Delete a schema node (soft by default). Scoped by tenant_id.
        Invalidates schema_nodes cache for tenant_id. Returns True if a node was deleted.
        """
        async with await self._get_session() as session:
            try:
                node_uuid = uuid.UUID(node_id)
                stmt = select(SchemaNode).where(
                    and_(
                        SchemaNode.id == node_uuid,
                        SchemaNode.tenant_id == tenant_id,
                        SchemaNode.deleted_at.is_(None),
                    )
                )
                result = await session.execute(stmt)
                node = result.scalar_one_or_none()
                if not node:
                    return False
                if soft:
                    node.deleted_at = datetime.now(timezone.utc)
                    node.updated_at = datetime.now(timezone.utc)
                else:
                    await session.delete(node)
                await session.commit()
                await invalidate_cache("schema_nodes", tenant_id)
                logger.info("SchemaEngine deleted node: %s (soft=%s)", node_id, soft)
                return True
            except Exception as e:
                await session.rollback()
                logger.error("SchemaEngine delete_node failed: %s", e)
                return False

    async def get_node_tree(
        self,
        tenant_id: str,
        space_id: str | None = None,
        space_ids: list[str] | None = None,
        root_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Return a tree of nodes (with children). Uses list_nodes then builds tree.
        Scoped by tenant_id and space_id or space_ids (membership-aware when space_ids provided).
        """
        all_nodes = await self.list_nodes(
            tenant_id=tenant_id,
            space_id=space_id,
            space_ids=space_ids,
            include_deleted=False,
        )
        return _build_node_tree(all_nodes, root_id)

    async def ensure_life_areas(self, tenant_id: str, space_id: str) -> list[str]:
        """
        Ensure canonical life areas (Work, Family, Health, Learning) exist. Idempotent.
        Uses stable UUIDs per tenant+title. Returns list of node IDs (created or existing).
        """
        created: list[str] = []
        for title in LIFE_AREA_NAMES:
            node_id = str(uuid.uuid5(LIFE_AREA_NAMESPACE, f"{tenant_id}:life_area:{title}"))
            try:
                await self.upsert_node(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    entity=SchemaEntity.LIFE_AREA,
                    title=title,
                    node_id=node_id,
                    description=f"Life area: {title}",
                    metadata={"canonical": True},
                )
                created.append(node_id)
            except Exception as e:
                logger.warning("ensure_life_areas upsert %s: %s", title, e)
        return created
