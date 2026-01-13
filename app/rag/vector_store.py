import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient

load_dotenv()
logger = logging.getLogger(__name__)

# הגדרות חיבור (משתמש בשמות השירותים מה-docker-compose)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = 6333
COLLECTION_NAME = "kirp_memories"

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
        embeddings = get_embeddings()
        
        # חיבור ללקוח Qdrant
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
        # יצירת ה-Vector Store של LangChain מעל Qdrant
        _vector_store = Qdrant(
            client=client,
            collection_name=COLLECTION_NAME,
            embeddings=embeddings
        )
        logger.info(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        
    return _vector_store

def add_texts(
    texts: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None
):
    store = get_vector_store()
    # ב-Qdrant אין צורך ב-save_local, הוא שומר אוטומטית ב-DB
    store.add_texts(texts, metadatas=metadatas)
    logger.info(f"Added {len(texts)} items to Qdrant")

def search_vectors(query: str, k: int = 5):
    store = get_vector_store()
    results = store.similarity_search(query, k=k)
    return [
        {"text": d.page_content, "metadata": d.metadata}
        for d in results
    ]

# Alias תאימות לקוד ישן
add_texts_with_metadata = add_texts