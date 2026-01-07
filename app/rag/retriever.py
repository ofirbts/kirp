# app/rag/retriever.py

from typing import List
from app.rag.vector_store import get_vector_store
from app.rag.memory_ranker import rank_memories


def retrieve_context(query: str, k: int = 5) -> List[str]:
    store = get_vector_store()

    docs_with_scores = store.similarity_search_with_score(query, k=k)

    docs = [d for d, _ in docs_with_scores]
    similarities = [1 - s for _, s in docs_with_scores]  # FAISS distance → similarity

    ranked = rank_memories(docs, similarities)

    # כרגע מחזירים טקסט, בהמשך גם trace
    formatted = []
    for r in ranked:
        meta = r["metadata"]
        formatted.append(
            f"{r['text']}\n\nMETA: {meta}\nSCORE: {r['score']}"
        )

    return formatted
