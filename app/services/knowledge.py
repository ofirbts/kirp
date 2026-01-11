import hashlib
from app.rag.vector_store import add_texts_with_metadata, get_vector_store
from app.core.persistence import PersistenceManager

class UnifiedKnowledgeStore:
    def _generate_id(self, content: str):
        return hashlib.sha256(content.encode()).hexdigest()

    def add(self, content: str, source: str, user_id: str = "default_user"):
        # יצירת ID ייחודי לפי התוכן (משימה 4)
        unique_id = self._generate_id(content)
        
        meta = {
            "user_id": user_id,
            "memory_type": "knowledge",
            "content_hash": unique_id,
            "source": source
        }

        # כאן המערכת תוסיף רק אם זה לא קיים (במימוש ה-vector_store שלך)
        add_texts_with_metadata(
            texts=[content],
            metadatas=[meta],
        )
        
        PersistenceManager.append_event(
            "knowledge_add",
            {"content": content, "source": source, "hash": unique_id}
        )
