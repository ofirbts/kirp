"""
Read-only Collections service.

Phase 4.2: exposes list/search operations. For now it returns empty
collections; later phases will back it with Qdrant collections and vector
search.
"""

from __future__ import annotations

from typing import List

from src.schemas.api_models import Collection, VectorSearchResult


async def list_collections() -> List[Collection]:
    """List collections. Phase 4.2: returns an empty list."""
    return []


async def vector_search(
    collection_id: str,
    query: dict,
) -> List[VectorSearchResult]:
    """Vector search. Phase 4.2: returns an empty list."""
    return []

