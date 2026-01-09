import uuid
from typing import List, Any, Dict

from app.core.metadata import normalize_metadata
from app.rag.vector_store import add_texts_with_metadata, get_vector_store
from app.core.persistence import PersistenceManager
from app.core.metadata_schema import ensure_metadata


class UnifiedKnowledgeStore:
    def add(self, content: str, source: str, user_id: str = "default_user", replaying: bool = False) -> None:
        # יצירת מטא-דאטה מועשר (לפי משימה 5)
        meta = ensure_metadata(
            {
                "user_id": user_id,
                "memory_type": "knowledge",
                "id": f"knowledge::{hash(content)}"
            },
            plane="knowledge",
            source=source,
        )
        
        add_texts_with_metadata(
            texts=[content],
            metadatas=[meta],
        )
        
        if not replaying:
            PersistenceManager.append_event(
                "knowledge_add",
                {
                    "content": content,
                    "source": source,
                    "user_id": user_id,
                },
            )

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        חיפוש בידע המאוחד עם סינון לפי memory_type
        """
        try:
            vs = get_vector_store()
        except RuntimeError:
            return []

        # 🔍 הוספת סינון כדי להבטיח שאנחנו מקבלים רק ידע (knowledge)
        # זה מונע ערבוב עם תוצאות מ-memory_plane אחרים
        return vs.similarity_search(
            query, 
            k=k,
            filter={"memory_type": "knowledge"}
        )