from typing import List
from app.rag.vector_store import get_vector_store
from datetime import datetime

def retrieve_context(query: str, k: int = 4) -> List[str]:
    store = get_vector_store()
    docs = store.similarity_search(query, k=k)
    
    formatted = []
    for doc in docs:
        meta = getattr(doc, 'metadata', {})
        text = doc.page_content
        meta_str = f"META: {meta}"
        formatted.append(f"{text}\n\n{meta_str}")
    return formatted
