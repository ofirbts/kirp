# app/rag/retriever.py
"""
KIRP Unified Retriever
Production hybrid retriever with ranking + deduplication
"""

from typing import List, Dict, Any

from app.rag.vector_store import search_vectors
from app.rag.retrieval_pipeline import retrieval_pipeline


class Retriever:
    """Unified production retriever"""

    async def retrieve(
        self,
        query: str,
        user_id: str,
        k: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        1. Raw vector search from the vector store
        2. Ranking + deduplication + explainability via retrieval_pipeline
        """
        # 1. Raw vector search (over-fetch for better ranking)
        raw_results = await search_vectors(query, k=20, user_id=user_id)

        # 2. Ranking + deduplication + explainability
        ranked = retrieval_pipeline(query, raw_results, final_k=k)

        return ranked


retriever = Retriever()


async def retrieve_context(
    query: str,
    user_id: str,
    k: int = 6,
) -> List[Dict[str, Any]]:
    """
    Backward-compatible helper used by other modules.
    """
    return await retriever.retrieve(query=query, user_id=user_id, k=k)
