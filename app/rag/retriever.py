from typing import List, Dict, Any
from app.rag.vector_store import search_vectors

def retrieve_context(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    שליפת הקשר סמנטי מ-Qdrant עם ניקוי נתונים בסיסי
    """
    try:
        results = search_vectors(query, k=k)
        return results
    except Exception as e:
        print(f"Error in retriever: {e}")
        return []