import uuid
from typing import List, Any, Dict

from app.core.metadata import normalize_metadata
from app.rag.vector_store import add_texts_with_metadata, get_vector_store
from app.core.persistence import PersistenceManager
from app.core.metadata_schema import ensure_metadata


class UnifiedKnowledgeStore:
    # הוספתי את user_id כפרמטר לפונקציה (עם ערך ברירת מחדל "default_user" ליתר ביטחון)
    def add(self, content: str, source: str, user_id: str = "default_user", replaying: bool = False) -> None:
        # עכשיו user_id מוגדר ו-Pylance יהיה מרוצה
        meta = ensure_metadata(
            {"user_id": user_id},
            plane="knowledge",
            source=source,
        )
        
        # Write into vector store
        add_texts_with_metadata(
            texts=[content],
            metadatas=[meta],
        )
        
        # Log event (unless replaying)
        if not replaying:
            PersistenceManager.append_event(
                "knowledge_add",
                {
                    "content": content,
                    "source": source,
                    "user_id": user_id, # מומלץ להוסיף גם ללוג של ה-Persistence
                },
            )

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        try:
            vs = get_vector_store()
        except RuntimeError:
            return []

        return vs.similarity_search(query, k=k)