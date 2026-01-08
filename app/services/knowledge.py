import uuid
from typing import List, Any, Dict

from app.rag.sharded_store import ShardedVectorStore
from app.rag.vector_store import get_vector_store
from app.core.persistence import PersistenceManager


class UnifiedKnowledgeStore:
    def add(self, content: str, source: str, replaying: bool = False) -> None:
        kid = str(uuid.uuid4())

        metadata = {
            "id": kid,
            "source": source,
            "memory_type": "knowledge",
        }

        # NEW: write into sharded vector store
        store = ShardedVectorStore()
        store.add("knowledge", content, metadata)

        # Log event (unless replaying)
        if not replaying:
            PersistenceManager.append_event(
                "knowledge_add",
                {
                    "id": kid,
                    "content": content,
                    "source": source,
                },
            )

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        try:
            vs = get_vector_store()
        except RuntimeError:
            return []

        return vs.similarity_search(query, k=k)
