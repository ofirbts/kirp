"""
Schema Engine — Tasks, projects, life areas, categories.

Builds and maintains structured schemas from events.
Used by agents (e.g. SchemaStructureAgent) and UI views.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schema import SchemaNode, SchemaEntity

logger = logging.getLogger(__name__)

_schema_engine: "SchemaEngine | None" = None


async def get_schema_engine(postgres_uri: str | None = None) -> "SchemaEngine":
    """Singleton SchemaEngine for use by services and main app."""
    global _schema_engine
    if _schema_engine is None:
        import os
        uri = postgres_uri or os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp")
        _schema_engine = SchemaEngine(uri)
        await _schema_engine.connect()
    return _schema_engine


class SchemaEngine:
    """
    Manages structured schemas. Full CRUD operations with PostgreSQL.
    Multi-tenant, event-sourced compatible.
    """

    def __init__(self, postgres_uri: str) -> None:
        self._postgres_uri = postgres_uri
        self._session_factory: Any = None

    async def connect(self) -> None:
        """Initialize SQLAlchemy async engine + session factory."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
            engine = create_async_engine(self._postgres_uri, echo=False)
            self._session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("SchemaEngine connected to PostgreSQL")
        except Exception as e:
            logger.error("SchemaEngine connection failed: %s", e)
            raise

    async def _get_session(self) -> AsyncSession:
        """Get async session."""
        if self._session_factory is None:
            await self.connect()
        return self._session_factory()

    async def get_session(self) -> AsyncSession:
        """
        Public helper to obtain an AsyncSession.

        Used by other components (e.g. projections) that share the same
        PostgreSQL engine. Callers are responsible for transaction
        boundaries (commit/rollback) when using the returned session.
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
        Insert or update a schema node.
        Returns the node ID (UUID string).
        """
        async with await self._get_session() as session:
            try:
                # Convert string IDs to UUIDs
                node_uuid = uuid.UUID(node_id) if node_id else uuid.uuid4()
                parent_uuid = uuid.UUID(parent_id) if parent_id else None
                
                # Check if node exists
                stmt = select(SchemaNode).where(
                    and_(
                        SchemaNode.id == node_uuid,
                        SchemaNode.tenant_id == tenant_id,
                        SchemaNode.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing node
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
                    # Invalidate cache
                    from src.core.cache import invalidate_cache
                    await invalidate_cache("schema_nodes", tenant_id)
                    logger.info("SchemaEngine updated node: %s %s", entity.value, node_uuid)
                    return str(node_uuid)
                else:
                    # Create new node
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
                    # Invalidate cache
                    from src.core.cache import invalidate_cache
                    await invalidate_cache("schema_nodes", tenant_id)
                    logger.info("SchemaEngine created node: %s %s", entity.value, node_uuid)
                    return str(node_uuid)
            except Exception as e:
                await session.rollback()
                logger.error("SchemaEngine upsert failed: %s", e)
                raise

    async def get_node(self, node_id: str, tenant_id: str) -> dict[str, Any] | None:
        """Get a single schema node by ID."""
        async with await self._get_session() as session:
            try:
                node_uuid = uuid.UUID(node_id)
                stmt = select(SchemaNode).where(
                    and_(
                        SchemaNode.id == node_uuid,
                        SchemaNode.tenant_id == tenant_id,
                        SchemaNode.deleted_at.is_(None)
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
        entity: SchemaEntity | None = None,
        parent_id: str | None = None,
        status: str | None = None,
        include_deleted: bool = False,
        limit: int = 1000,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List schema nodes with optional filters.
        Returns list of node dictionaries.
        Uses caching for performance.
        """
        # Check cache
        if use_cache:
            from src.core.cache import get_cached, set_cached, _cache_key, CACHE_TTL_SCHEMA
            cache_key = _cache_key("schema_nodes", tenant_id, space_id, entity, parent_id, status, include_deleted, limit)
            cached = await get_cached(cache_key)
            if cached is not None:
                return cached
        
        async with await self._get_session() as session:
            try:
                conditions = [SchemaNode.tenant_id == tenant_id]
                
                if space_id:
                    conditions.append(SchemaNode.space_id == space_id)
                
                if entity:
                    conditions.append(SchemaNode.entity == entity.value)
                
                if parent_id:
                    parent_uuid = uuid.UUID(parent_id)
                    conditions.append(SchemaNode.parent_id == parent_uuid)
                elif parent_id is False:  # Explicitly request root nodes
                    conditions.append(SchemaNode.parent_id.is_(None))
                
                if status:
                    conditions.append(SchemaNode.status == status)
                
                if not include_deleted:
                    conditions.append(SchemaNode.deleted_at.is_(None))
                
                stmt = select(SchemaNode).where(and_(*conditions)).limit(limit)
                result = await session.execute(stmt)
                nodes = result.scalars().all()
                node_dicts = [node.to_dict() for node in nodes]
                
                # Cache result
                if use_cache:
                    from src.core.cache import set_cached, _cache_key, CACHE_TTL_SCHEMA
                    cache_key = _cache_key("schema_nodes", tenant_id, space_id, entity, parent_id, status, include_deleted, limit)
                    await set_cached(cache_key, node_dicts, CACHE_TTL_SCHEMA)
                
                return node_dicts
            except Exception as e:
                logger.error("SchemaEngine list_nodes failed: %s", e)
                return []

    async def delete_node(self, node_id: str, tenant_id: str, soft: bool = True) -> bool:
        """
        Delete a schema node (soft delete by default).
        Returns True if successful.
        """
        async with await self._get_session() as session:
            try:
                node_uuid = uuid.UUID(node_id)
                stmt = select(SchemaNode).where(
                    and_(
                        SchemaNode.id == node_uuid,
                        SchemaNode.tenant_id == tenant_id,
                        SchemaNode.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                node = result.scalar_one_or_none()
                
                if not node:
                    return False
                
                if soft:
                    # Soft delete
                    node.deleted_at = datetime.now(timezone.utc)
                    node.updated_at = datetime.now(timezone.utc)
                else:
                    # Hard delete
                    await session.delete(node)
                
                await session.commit()
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
        root_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get a tree structure of nodes (with children).
        Returns a dictionary with root nodes and their children.
        """
        # Get all nodes
        all_nodes = await self.list_nodes(tenant_id=tenant_id, space_id=space_id, include_deleted=False)
        
        # Build tree
        node_map = {node["id"]: {**node, "children": []} for node in all_nodes}
        roots = []
        
        for node in all_nodes:
            if node["parent_id"]:
                if node["parent_id"] in node_map:
                    node_map[node["parent_id"]]["children"].append(node_map[node["id"]])
            else:
                roots.append(node_map[node["id"]])
        
        if root_id:
            # Return specific subtree
            return node_map.get(root_id, {})
        else:
            # Return all roots
            return {"roots": roots, "count": len(all_nodes)}
