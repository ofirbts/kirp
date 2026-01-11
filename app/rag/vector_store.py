from pathlib import Path
from typing import Optional, List, Dict, Any

from langchain_community.vectorstores import FAISS
from app.rag.embedder import get_embeddings


VECTOR_STORE_PATH = Path("data/vector_store")
VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

_vector_store: Optional[FAISS] = None

def get_vector_store() -> FAISS:
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized")
    return _vector_store

def add_texts(texts: List[str]) -> None:
    global _vector_store
    embeddings = get_embeddings()
    if _vector_store is None:
        _vector_store = FAISS.from_texts(texts, embeddings)
    else:
        _vector_store.add_texts(texts)
    _vector_store.save_local(str(VECTOR_STORE_PATH))

def add_texts_with_metadata(texts: List[str], metadatas: List[Dict[str, Any]]) -> int:
    global _vector_store

    embeddings = get_embeddings()

    if _vector_store is None:
        # 🔥 אתחול ראשון
        _vector_store = FAISS.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas
        )
    else:
        try:
            _vector_store.add_texts(texts, metadatas=metadatas)
        except AssertionError:
            print("⚠️ Dimension mismatch – rebuilding index")
            _vector_store = FAISS.from_texts(
                texts=texts,
                embedding=embeddings,
                metadatas=metadatas
            )

    _vector_store.save_local(str(VECTOR_STORE_PATH))
    return len(texts)


def load_vector_store() -> None:
    global _vector_store
    index_file = VECTOR_STORE_PATH / "index.faiss"
    store_file = VECTOR_STORE_PATH / "index.pkl"
    if not index_file.exists() or not store_file.exists():
        return
    embeddings = get_embeddings()
    try:
        _vector_store = FAISS.load_local(
            str(VECTOR_STORE_PATH), embeddings, 
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        print(f"⚠️ Failed to load: {e}")
        _vector_store = None

def debug_info() -> Dict[str, Any]:
    index_file = VECTOR_STORE_PATH / "index.faiss"
    store_file = VECTOR_STORE_PATH / "index.pkl"
    disk_exists = index_file.exists() and store_file.exists()
    if _vector_store is None:
        return {
            "ram_loaded": False, "disk_exists": disk_exists,
            "vectors_count_ram": 0, "status": "Ready for ingest"
        }
    try:
        count = _vector_store.index.ntotal
        return {
            "ram_loaded": True, "disk_exists": disk_exists,
            "vectors_count_ram": count, "status": f"{count} memories"
        }
    except:
        return {"ram_loaded": False, "disk_exists": disk_exists, "status": "Error"}

def list_memories_for_ui(limit: int = 20):
    """
    Adapter for UI / Debug / Observability.
    Returns flat, safe memory objects.
    """
    if _vector_store is None:
        return []

    docs = _vector_store.docstore._dict
    memories = []

    for i, doc in enumerate(docs.values()):
        if i >= limit:
            break
        memories.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown")
        })

    return memories
