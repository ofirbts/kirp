"""
M3 IdentityOS — Semantic search over M3 reflections in Qdrant.

Reflections are upserted by the pipeline (event_type + module=m3 in payload).
This module queries the shared RAG collection with payload_filter module=m3.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def search_m3_reflections(
    tenant_id: str,
    user_id: str,
    query: str,
    *,
    space_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Semantic search over M3 reflections (Qdrant points with module=m3).
    Returns list of { event_id, content, score, source, metadata }.
    """
    from src.core.rag_engine import get_shared_rag_engine

    rag = await get_shared_rag_engine()
    resp = await rag.search(
        query=query,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        limit=limit,
        use_multihop=False,
        payload_filter={"module": "m3"},
    )
    out: list[dict[str, Any]] = []
    for r in resp.results:
        meta = r.metadata or {}
        event_id = meta.get("event_id")
        out.append({
            "event_id": event_id,
            "content": r.text,
            "score": round(r.score, 4),
            "source": r.source,
            "metadata": {k: v for k, v in meta.items() if k not in ("embedding",)},
        })
    return out
