"""
Read-only Graph service.

Phase 4.2: exposes list/get operations for graph nodes and edges. For now it
returns empty graphs; later phases will back it with Postgres projections and
Qdrant/knowledge-graph state.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from src.schemas.api_models import GraphNode, GraphEdge


async def get_graph(
    tenant_id: Optional[str] = None,
    space_id: Optional[str] = None,
    node_type: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """Get a snapshot of the graph. Phase 4.2: returns an empty graph."""
    return [], []


async def get_node(node_id: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """Get a single node as a tiny graph. Phase 4.2: returns an empty graph."""
    return [], []


async def get_neighbors(node_id: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """Get neighbors for a node. Phase 4.2: returns an empty graph."""
    return [], []

