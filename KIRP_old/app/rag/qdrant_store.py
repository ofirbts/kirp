# app/rag/qdrant_store.py
"""
Qdrant-backed vector store for KIRP RAG.

אחראי על:
- יצירת חיבור ל-Qdrant
- יצירת קולקציה (אם לא קיימת)
- הוספת וקטורים עם מטא-דאטה
- חיפוש לפי user_id + טקסט
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
    PointStruct,
)

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = os.getenv("QDRANT_COLLECTION", "kirp_memories")
VECTOR_SIZE = int(os.getenv("EMBEDDING_DIM", "1536"))  # להתאים למודל האמבדינג


class QdrantStore:
    def __init__(self):
        url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        self.collection = DEFAULT_COLLECTION

        self.client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=10.0,
        )

        self._ensure_collection()

    def _ensure_collection(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection not in collections:
            logger.info(f"Creating Qdrant collection: {self.collection}")
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_points(
        self,
        embeddings: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> int:
        points = [
            PointStruct(
                id=payload.get("trace_id") or payload.get("id") or idx,
                vector=emb,
                payload=payload,
            )
            for idx, (emb, payload) in enumerate(zip(embeddings, payloads))
        ]

        self.client.upsert(
            collection_name=self.collection,
            points=points,
            wait=True,
        )
        return len(points)

    def search(
        self,
        embedding: List[float],
        user_id: Optional[str],
        limit: int = 6,
    ) -> List[Dict[str, Any]]:
        must: List[FieldCondition] = []
        if user_id:
            must.append(
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                )
            )

        q_filter: Optional[Filter] = Filter(must=must) if must else None

        results = self.client.search(
            collection_name=self.collection,
            query_vector=embedding,
            limit=limit,
            query_filter=q_filter,
        )

        docs: List[Dict[str, Any]] = []
        for r in results:
            payload = r.payload or {}
            payload["score"] = float(r.score)
            docs.append(payload)

        return docs


_qdrant_store: Optional[QdrantStore] = None


def get_qdrant_store() -> QdrantStore:
    global _qdrant_store
    if _qdrant_store is None:
        _qdrant_store = QdrantStore()
    return _qdrant_store
