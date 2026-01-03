from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS
from app.rag.embedder import get_embeddings

# 📁 data/vector_store/
VECTOR_STORE_PATH = Path("data/vector_store")
VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

_vector_store: Optional[FAISS] = None


def get_vector_store() -> FAISS:
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Ingest data first.")
    return _vector_store


def add_texts(texts: list[str]) -> None:
    global _vector_store

    embeddings = get_embeddings()

    if _vector_store is None:
        _vector_store = FAISS.from_texts(texts, embeddings)
        _vector_store.save_local(str(VECTOR_STORE_PATH))
    else:
        _vector_store.add_texts(texts)
        _vector_store.save_local(str(VECTOR_STORE_PATH))


def load_vector_store() -> None:
    global _vector_store

    index_file = VECTOR_STORE_PATH / "index.faiss"
    store_file = VECTOR_STORE_PATH / "index.pkl"

    if not index_file.exists() or not store_file.exists():
        # No vector store yet – this is expected on first run
        return

    embeddings = get_embeddings()

    try:
        _vector_store = FAISS.load_local(
            str(VECTOR_STORE_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )
    except Exception as e:
        # Corrupted / incompatible index – ignore and rebuild later
        print("⚠️ Failed to load vector store, will recreate on ingest.")
        print(f"Reason: {e}")
        _vector_store = None


def debug_info() -> dict:
    if _vector_store is None:
        return {"initialized": False, "vectors_count": 0}

    return {
        "initialized": True,
        "vectors_count": _vector_store.index.ntotal,
    }
