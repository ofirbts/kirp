# app/rag/vector_store.py
"""
KIRP Unified Vector Store v8
Enterprise Qdrant + LangChain integration
- Singleton QdrantVectorStore
- Per-user semantic search
- Metadata enrichment for analytics & RAG
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "kirp_memories")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

_vector_store: Optional[QdrantVectorStore] = None


def get_vector_store() -> QdrantVectorStore:
    """
    Singleton Qdrant vector store with auto‑initialization.
    Compatible with existing code (agent.py, etc.).
    """
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    client = QdrantClient(
        url=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        prefer_grpc=False,
    )

    # Create collection if missing
    collections = client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info(f"📦 Created Qdrant collection: {COLLECTION_NAME}")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    _vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    logger.info(f"🚀 QdrantVectorStore initialized at {QDRANT_HOST}:{QDRANT_PORT}")
    return _vector_store


async def search_vectors(
    query: str,
    k: int = 5,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Async wrapper over LangChain similarity_search with optional user_id filtering.
    Returns a normalized list of dicts:
    - text
    - metadata
    - score (if available)
    """
    store = get_vector_store()

    qdrant_filter = None
    if user_id:
        qdrant_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
        )

    # LangChain call is sync, אבל אנחנו שומרים על חתימה async לצורך תאימות
    docs = store.similarity_search(
        query=query,
        k=k,
        filter=qdrant_filter,
    )

    results: List[Dict[str, Any]] = []
    for doc in docs:
        meta = doc.metadata or {}
        results.append(
            {
                "id": meta.get("id"),
                "text": doc.page_content,
                "score": meta.get("score", 0.0),
                "source": meta.get("source", "unknown"),
                "created_at": meta.get("created_at", "N/A"),
                "metadata": meta,
            }
        )

    return results


def add_texts_with_metadata(
    texts: List[str],
    user_id: str,
    metadatas: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """
    Add texts to Qdrant with metadata enrichment.
    Used by ingestion pipeline and memory storage.
    """
    store = get_vector_store()
    now = datetime.now(timezone.utc).isoformat()

    if metadatas is None:
        metadatas = [{} for _ in texts]

    enriched: List[Dict[str, Any]] = []
    for m in metadatas:
        meta = m.copy()
        meta["user_id"] = user_id
        meta.setdefault("source", "manual_ingest")
        meta.setdefault("created_at", now)
        enriched.append(meta)

    store.add_texts(texts=texts, metadatas=enriched)
    logger.info(f"🧠 Added {len(texts)} items to Qdrant for user {user_id}")

    return len(texts)
