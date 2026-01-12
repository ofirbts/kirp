import os
import logging  # <--- תוסיף את השורה הזו!
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

logger = logging.getLogger(__name__)

DB_PATH = "data/faiss_index"
_vector_store = None
_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings()
    return _embeddings

def load_vector_store():
    global _vector_store
    embeddings = get_embeddings()
    os.makedirs(DB_PATH, exist_ok=True)

    if os.path.exists(os.path.join(DB_PATH, "index.faiss")):
        _vector_store = FAISS.load_local(
            DB_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        logger.info("Vector store loaded from disk")
    else:
        _vector_store = FAISS.from_texts(
            ["KIRP OS initialized"],
            embeddings
        )
        _vector_store.save_local(DB_PATH)
        logger.info("New vector store created")

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        load_vector_store()
    return _vector_store

def add_texts(
    texts: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None
):
    store = get_vector_store()
    store.add_texts(texts, metadatas=metadatas)
    store.save_local(DB_PATH)

def search_vectors(query: str, k: int = 5):
    store = get_vector_store()
    return [
        {"text": d.page_content, "metadata": d.metadata}
        for d in store.similarity_search(query, k=k)
    ]
add_texts_with_metadata = add_texts