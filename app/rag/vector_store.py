import logging
import os
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)
DB_PATH = "data/faiss_index"

_vector_store = None
_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings()
    return _embeddings

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        load_vector_store()
    return _vector_store

def load_vector_store():
    global _vector_store
    embeddings = get_embeddings()
    try:
        if os.path.exists(os.path.join(DB_PATH, "index.faiss")):
            _vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
            logger.info("✅ Vector Store loaded from disk")
        else:
            _vector_store = FAISS.from_texts(["KIRP OS initialized"], embeddings)
            _vector_store.save_local(DB_PATH)
            logger.info("✅ New Vector Store created and saved to disk")
    except Exception as e:
        logger.error(f"❌ Error loading vector store: {e}")

def add_texts(texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
    store = get_vector_store()
    if store:
        store.add_texts(texts, metadatas=metadatas)
        store.save_local(DB_PATH) # שמירה מיידית לאחר כל הוספה
        logger.info(f"💾 Indexed and saved {len(texts)} memories")

def search_vectors(query: str, k: int = 5):
    store = get_vector_store()
    return [{"text": d.page_content, "metadata": d.metadata} for d in store.similarity_search(query, k=k)] if store else []

def add_texts_with_metadata(texts: List[str], metadatas: List[Dict[str, Any]]):
    return add_texts(texts, metadatas=metadatas)

def list_memories_for_ui(limit: int = 20): return []
def debug_info(): return {"initialized": _vector_store is not None, "path": DB_PATH}
