import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from app.rag.embedder import embeddings

qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "kirp_vectors"

# אתחול הלקוח
client = QdrantClient(url=qdrant_url)

def init_collection():
    try:
        collections = client.get_collections().collections
        existing = [c.name for c in collections]
        if COLLECTION_NAME not in existing:
            # יצירת קולקציה עם 1536 ממדים (OpenAI standard)
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
    except Exception as e:
        print(f"Qdrant connection error: {e}")

def store_texts(texts: list[str]):
    init_collection()
    for i, text in enumerate(texts):
        # יצירת וקטור מהטקסט
        vector = embeddings.embed_query(text)
        # שמירה ב-Qdrant
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=hash(text) % 10**10, # מזהה ייחודי פשוט
                    vector=vector,
                    payload={"page_content": text}
                )
            ]
        )

def search_similar(query: str, k: int = 3):
    init_collection()
    query_vector = embeddings.embed_query(query)
    
    try:
        # ניסיון 1: הסטנדרט של הגרסאות החדשות (1.1x ומעלה)
        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=k
        ).points
    except AttributeError:
        # ניסיון 2: הסטנדרט הישן יותר (Legacy)
        search_result = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=k
        )

    class Document:
        def __init__(self, content):
            self.page_content = content

    # עיבוד התוצאות בהתאם למבנה שחזר
    docs = []
    for res in search_result:
        # ב-query_points זה אובייקט, ב-search זה יכול להיות דיקט
        payload = res.payload if hasattr(res, 'payload') else res.payload
        if payload and "page_content" in payload:
            docs.append(Document(payload["page_content"]))
            
    return docs