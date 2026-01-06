from typing import List
from app.rag.vector_store import get_vector_store


def retrieve_context(query: str, k: int = 4) -> List[str]:
    """
    Retrieve relevant chunks from vector store
    """
    store = get_vector_store()
    docs = store.similarity_search(query, k=k)

    return [doc.page_content for doc in docs]
