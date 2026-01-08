from typing import List, Dict, Any
from app.rag.vector_store import get_vector_store
from app.rag.retrieval_pipeline import retrieval_pipeline


def retrieve_context(query: str, k: int = 5) -> List[Dict[str, Any]]:
    store = get_vector_store()
    docs_with_scores = store.similarity_search_with_score(query, k=25)

    raw_results: List[Dict[str, Any]] = []
    for doc, distance in docs_with_scores:
        meta = dict(doc.metadata or {})
        raw_results.append({
            "id": meta.get("id"),
            "text": doc.page_content,
            "score": 1 - float(distance),
            "embedding": meta.get("embedding"),
            "meta": meta,
        })

    memories = retrieval_pipeline(
        query=query,
        raw_results=raw_results,
        final_k=k,
    )
    return memories
