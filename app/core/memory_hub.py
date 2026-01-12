import logging
from typing import List, Dict, Any
from app.rag.vector_store import add_texts, search_vectors

logger = logging.getLogger(__name__)

class MemoryHub:
    """
    Central memory abstraction for KIRP.
    Backed by vector store (FAISS).
    """

    def add_text(
        self,
        content: str,
        source: str,
        tier: str = "short",
        session_id: str = "default"
    ) -> str | None:
        try:
            add_texts(
                texts=[content],
                metadatas=[{
                    "source": source,
                    "tier": tier,
                    "session_id": session_id
                }]
            )
            logger.info("Memory stored successfully")
            return f"mem_{hash(content) & 0xfffffff}"
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            return None

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        try:
            return search_vectors(query, k=k)
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []
