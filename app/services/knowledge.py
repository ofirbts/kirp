# app/services/knowledge.py
from typing import List, Any, Dict

from app.rag.vector_store import add_texts_with_metadata, get_vector_store
from app.core.persistence import PersistenceManager


class UnifiedKnowledgeStore:
    """
    Unified knowledge plane that wraps the vector store.

    All long-term knowledge is written into the vector store, and replay
    can re-hydrate knowledge by re-applying 'knowledge_add' events.
    """

    def __init__(self) -> None:
        # No direct handle is stored; we rely on the global vector store
        # helpers to keep things simple.
        ...

    def add(self, content: str, source: str, replaying: bool = False) -> None:
        """
        Add a piece of knowledge into the unified store.

        When replaying, we skip emitting events to avoid event duplication.
        """
        add_texts_with_metadata(
            texts=[content],
            metadatas=[{"source": source}],
        )

        if not replaying:
            PersistenceManager.append_event(
                "knowledge_add",
                {"content": content, "source": source},
            )

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Simple semantic search wrapper.

        Returns a list of LangChain Document objects (or empty list).
        """
        try:
            vs = get_vector_store()
        except RuntimeError:
            return []

        return vs.similarity_search(query, k=k)
