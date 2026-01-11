from typing import List, Dict, Any
from app.core.memory_redis import RedisMemory
from app.rag.vector_store import add_texts_with_metadata, get_vector_store

class MemoryHub:
    """
    Unified memory interface for KIRP.
    Handles both Short-term (Redis) and Long-term (FAISS) memory.
    """

    def __init__(self):
        # וודא שהשם כאן תואם לשימוש בהמשך
        self.redis = RedisMemory()

    # ---------- Store ----------

    def add_text(
        self,
        content: str,
        source: str = "user",
        tier: str = "short",
        session_id: str = "default",
        meta: Dict[str, Any] = None
    ) -> str:
        
        # 1. שמירה ב-Short-term (Redis) תמיד לצרכי UI וזיכרון מהיר
        stored_in_redis = self.redis.add(content, session_id=session_id)
        
        # 2. אם הוגדר כזיכרון לטווח קצר בלבד - עוצרים כאן
        if tier == "short":
            return "redis" if stored_in_redis else "duplicate"

        # 3. שמירה ב-Long-term (FAISS) - כאן קרה ה-AssertionError קודם
        try:
            add_texts_with_metadata(
                texts=[content],
                metadatas=[{"source": source, "session_id": session_id}]
            )
            return "faiss"
        except Exception as e:
            # אם FAISS קורס (בגלל המימדים), לפחות ה-Redis עובד
            print(f"⚠️ FAISS Storage Error: {e}")
            return "redis_only_fallback"

    # ---------- Search ----------

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        try:
            store = get_vector_store()
            if not store:
                return []
                
            docs = store.similarity_search(query, k=k)
            results = []
            for d in docs:
                results.append({
                    "text": d.page_content,
                    "source": d.metadata.get("source", "unknown"),
                })
            return results
        except Exception as e:
            print(f"🔍 Search failed: {e}")
            return []

    # ---------- Debug ----------

    def debug(self) -> Dict[str, Any]:
        return {
            "redis": self.redis.debug_info()
        }