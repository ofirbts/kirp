from datetime import datetime, timezone
import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient

load_dotenv()
logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = 6333
COLLECTION_NAME = "kirp_memories"

_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        try:
            embeddings = OpenAIEmbeddings()
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            
            # בדיקה אם ה-Collection קיים, אם לא - צור אותו
            collections = client.get_collections().collections
            if not any(c.name == COLLECTION_NAME for c in collections):
                from qdrant_client.http import models
                client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)
                )
            
            # יצירת ה-Vector Store דרך LangChain בצורה מפורשת
            _vector_store = Qdrant(
                client=client,
                collection_name=COLLECTION_NAME,
                embeddings=embeddings
            )
            logger.info(f"Successfully connected to Qdrant at {QDRANT_HOST}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise e
    return _vector_store

async def search_vectors(query: str, k: int = 5, **kwargs):
    """
    מבצע חיפוש דמיון סמנטי ומחזיר גם ציונים ווקטורים
    """
    try:
        limit = kwargs.get("limit", k)
        store = get_vector_store()
        
        # שימוש ב-similarity_search_with_score כדי לקבל את הציון (Score)
        # זה קריטי עבור ה-confidence ב-retrieval_pipeline
        docs_with_scores = store.similarity_search_with_score(query, k=limit)
        
        results = []
        for doc, score in docs_with_scores:
            # אנחנו אורזים את זה במבנה שה-Pipeline מצפה לו
            results.append({
                "text": doc.page_content,
                "score": round(score, 4),
                "meta": doc.metadata,
                "id": doc.metadata.get("id", "unknown"),
                # הערה: LangChain לא תמיד מחזירה את ה-embedding המקורי בחיפוש רגיל.
                # אם ה-Deduplication הסמנטי נכשל, הוא ישתמש ב-logical_dedup כגיבוי.
                "embedding": getattr(doc, "embedding", None) 
            })
        return results
    except Exception as e:
        logger.error(f"Error during vector search: {e}")
        return []

# פונקציית עזר להוספת טקסטים עם מטא-דאטה עשיר
def add_texts_with_metadata(texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
    if not texts:
        return 0
    store = get_vector_store()
    
    # הוספת חותמת זמן אם לא קיימת
    if metadatas:
        now = datetime.now(timezone.utc).isoformat()
        for m in metadatas:
            if "created_at" not in m:
                m["created_at"] = now

    store.add_texts(texts, metadatas=metadatas)
    logger.info(f"Added {len(texts)} items to Qdrant")
    return len(texts)