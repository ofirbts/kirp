# app/rag/sharded_store.py
"""
Sharded vector store abstraction.

מאפשר:
- חלוקה לוגית לפי user_id / source
- ניתוב ל-Qdrant (או בעתיד backends נוספים)
"""

from typing import List, Dict, Any, Optional

from app.rag.qdrant_store import get_qdrant_store


class ShardedVectorStore:
    """
    כרגע: שכבת אבסטרקציה דקה מעל Qdrant.
    בעתיד: אפשר להרחיב ל-multi-cluster / multi-tenant.
    """

    def __init__(self):
        self.backend = get_qdrant_store()

    def add_embeddings(
        self,
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> int:
        return self.backend.upsert_points(embeddings, metadatas)

    def search(
        self,
        embedding: List[float],
        user_id: Optional[str],
        k: int = 6,
    ) -> List[Dict[str, Any]]:
        return self.backend.search(embedding, user_id=user_id, limit=k)


_sharded_store: Optional[ShardedVectorStore] = None


def get_sharded_store() -> ShardedVectorStore:
    global _sharded_store
    if _sharded_store is None:
        _sharded_store = ShardedVectorStore()
    return _sharded_store
