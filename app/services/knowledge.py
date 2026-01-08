import uuid
from typing import List, Any, Dict

from app.core.metadata import normalize_metadata
from app.rag.vector_store import add_texts_with_metadata, get_vector_store
from app.core.persistence import PersistenceManager
from app.core.metadata_schema import ensure_metadata


class UnifiedKnowledgeStore:
    def add(self, content: str, source: str, replaying: bool = False) -> None:
        # NEW: metadata creation using ensure_metadata
        meta = ensure_metadata(
            {},
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
                },
            )

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        try:
            vs = get_vector_store()
        except RuntimeError:
            return []

        return vs.similarity_search(query, k=k)
