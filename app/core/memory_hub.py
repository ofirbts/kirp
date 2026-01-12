import logging
from typing import List, Dict, Any
from app.rag.vector_store import add_texts, search_vectors

logger = logging.getLogger(__name__)

class MemoryHub:
    def __init__(self):
        self.tier_map = {"short": "recent", "long": "permanent"}

    def add_text(self, content: str, source: str, tier: str = "short", session_id: str = "default"):
        logger.info(f"🧠 Storing in Vector Store: {content[:30]}...")
        try:
            add_texts(
                texts=[content], 
                metadatas=[{"source": source, "tier": tier, "session_id": session_id}]
            )
            return "mem_" + str(hash(content))[:8]
        except Exception as e:
            logger.error(f"❌ MemoryHub storage failed: {e}")
            return None

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """שליפה אמיתית מה-Vector Store"""
        logger.info(f"🔍 Searching memories for: '{query}'")
        try:
            results = search_vectors(query, k=k)
            return results
        except Exception as e:
            logger.error(f"❌ MemoryHub search failed: {e}")
            return []
