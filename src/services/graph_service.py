"""
Graph service — Postgres-backed list for knowledge graph.

Reads graph_nodes and graph_edges. Tenant-scoped.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import select, or_

from src.core.schema_engine import get_schema_engine
from src.models.agent import GraphNode, GraphEdge
from src.schemas.api_models import GraphNode as GraphNodeSchema, GraphEdge as GraphEdgeSchema


def _node_to_schema(n: GraphNode) -> GraphNodeSchema:
    meta = getattr(n, "meta", None) or getattr(n, "metadata", None) or {}
    return GraphNodeSchema(
        id=str(n.id),
        type=n.type or "document",
        label=n.label or "",
        tenantId=n.tenant_id,
        spaceId=n.space_id,
        metadata=meta if isinstance(meta, dict) else {},
    )


def _edge_to_schema(e: GraphEdge) -> GraphEdgeSchema:
    meta = getattr(e, "meta", None) or getattr(e, "metadata", None) or {}
    return GraphEdgeSchema(
        id=str(e.id),
        fromId=str(e.from_id),
        toId=str(e.to_id),
        type=e.type or "related",
        metadata=meta if isinstance(meta, dict) else {},
    )


async def get_graph(
    tenant_id: Optional[str] = None,
    space_id: Optional[str] = None,
    node_type: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> Tuple[List[GraphNodeSchema], List[GraphEdgeSchema]]:
    if not tenant_id:
        return [], []
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        q = select(GraphNode).where(GraphNode.tenant_id == tenant_id)
        if space_id:
            q = q.where(GraphNode.space_id == space_id)
        if node_type:
            q = q.where(GraphNode.type == node_type)
        result = await session.execute(q.limit(200))
        nodes = result.scalars().all()
        node_uuids = [n.id for n in nodes]
        edges = []
        if node_uuids:
            eq = select(GraphEdge).where(
                or_(GraphEdge.from_id.in_(node_uuids), GraphEdge.to_id.in_(node_uuids))
            )
            eres = await session.execute(eq.limit(500))
            edges = eres.scalars().all()
        return [_node_to_schema(n) for n in nodes], [_edge_to_schema(e) for e in edges]
    finally:
        await session.close()


async def get_node(node_id: str) -> Tuple[List[GraphNodeSchema], List[GraphEdgeSchema]]:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        from uuid import UUID
        nid = UUID(node_id)
        result = await session.execute(select(GraphNode).where(GraphNode.id == nid))
        node = result.scalar_one_or_none()
        if not node:
            return [], []
        eres = await session.execute(
            select(GraphEdge).where((GraphEdge.from_id == nid) | (GraphEdge.to_id == nid))
        )
        edges = eres.scalars().all()
        return [_node_to_schema(node)], [_edge_to_schema(e) for e in edges]
    finally:
        await session.close()


async def get_neighbors(node_id: str) -> Tuple[List[GraphNodeSchema], List[GraphEdgeSchema]]:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        from uuid import UUID
        nid = UUID(node_id)
        eres = await session.execute(
            select(GraphEdge).where((GraphEdge.from_id == nid) | (GraphEdge.to_id == nid))
        )
        edges = eres.scalars().all()
        neighbor_ids = set()
        for e in edges:
            if e.from_id != nid:
                neighbor_ids.add(e.from_id)
            if e.to_id != nid:
                neighbor_ids.add(e.to_id)
        if not neighbor_ids:
            return [], [_edge_to_schema(e) for e in edges]
        nres = await session.execute(select(GraphNode).where(GraphNode.id.in_(neighbor_ids)))
        nodes = nres.scalars().all()
        return [_node_to_schema(n) for n in nodes], [_edge_to_schema(e) for e in edges]
    finally:
        await session.close()
