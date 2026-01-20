import logging
from typing import List, Dict, Any
from app.rag.vector_store import add_texts_with_metadata as add_texts, search_vectors

logger = logging.getLogger(__name__)

class MemoryHub:
    def add_text(self, content: str, source: str, user_id: str) -> str:
        """הוספת מידע לזיכרון הוקטורי עם מניעת כפילויות סמנטית"""
        # 1. Semantic Deduplication Check
        try:
            existing = search_vectors(content, k=1)
            if existing and existing[0].get("score", 0) > 0.95:
                logger.info(f"ℹ️ Semantic duplicate detected for user {user_id}. Skipping.")
                return "duplicate"
        except Exception as e:
            logger.warning(f"Deduplication check failed, proceeding with storage: {e}")

        # 2. Store in Vector DB
        try:
            add_texts(
                texts=[content],
                metadatas=[{"source": source, "user_id": user_id, "timestamp": str(logging.time.time())}]
            )
            logger.info(f"🧠 New memory indexed for user {user_id}")
            return "stored"
        except Exception as e:
            logger.error(f"❌ Memory storage failed: {e}")
            return "error"

    def search_context(self, query: str, k: int = 5):
        """חיפוש הקשר רלוונטי בזיכרון הוקטורי"""
        return search_vectors(query, k=k)

memory_hub = MemoryHub()