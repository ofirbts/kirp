from langchain_community.vectorstores import FAISS
from app.rag.embedder import get_embeddings

_vector_store: FAISS | None = None


def get_vector_store() -> FAISS:
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Ingest data first.")
    return _vector_store


def add_texts(texts: list[str]) -> None:
    global _vector_store

    embeddings = get_embeddings()

    if _vector_store is None:
        _vector_store = FAISS.from_texts(texts, embeddings)
    else:
        _vector_store.add_texts(texts)


def debug_info():
    if _vector_store is None:
        return {
            "initialized": False,
            "vectors_count": 0
        }

    try:
        count = _vector_store.index.ntotal
    except Exception:
        count = None

    return {
        "initialized": True,
        "vectors_count": count
    }
