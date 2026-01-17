import os
import logging
import time
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from app.rag.embedder import embeddings

# הגדרת לוגר כדי לראות מה קורה בזמן אמת
logger = logging.getLogger(__name__)

# --- SMART ENVIRONMENT DETECTION ---
IS_DOCKER = os.path.exists('/.dockerenv') or os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
QDRANT_HOST = "qdrant" if IS_DOCKER else "localhost"

# יצירת ה-Client פעם אחת בלבד ברמת המודול
# הסרנו את המשתנה qdrant_url הישן שהיה מקובע ל-localhost
client = QdrantClient(host=QDRANT_HOST, port=6333)

COLLECTION_NAME = "kirp_vectors"

def init_collection():
    retries = 5
    while retries > 0:
        try:
            collections = client.get_collections().collections
            existing = [c.name for c in collections]
            if COLLECTION_NAME not in existing:
                client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
                )
            return # הצלחנו להתחבר, יוצאים מהלולאה
        except Exception as e:
            retries -= 1
            logger.warning(f"⏳ Qdrant not ready. Retrying in 3s... ({retries} retries left)")
            time.sleep(3)
    
    logger.error("❌ Could not connect to Qdrant after 5 attempts.")
    raise Exception("Qdrant Connection Failed")
    
def store_texts(texts: list[str]):
    # וודא שהקולקציה קיימת
    init_collection()
    
    points = []
    for i, text in enumerate(texts):
        vector = embeddings.embed_query(text)
        points.append(
            PointStruct(
                id=hash(text) % 10**10,
                vector=vector,
                payload={"page_content": text}
            )
        )
    
    # ביצוע Upsert מרוכז (יעיל יותר מאחד-אחד בלולאה)
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    logger.info(f"✅ Stored {len(texts)} vectors in Qdrant.")

def search_similar(query: str, k: int = 3):
    init_collection()
    query_vector = embeddings.embed_query(query)
    
    try:
        # ניסיון לגרסה חדשה
        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=k
        ).points
    except Exception:
        # Fallback לגרסה ישנה
        search_result = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=k
        )

    class Document:
        def __init__(self, content):
            self.page_content = content

    docs = []
    for res in search_result:
        payload = res.payload
        if payload and "page_content" in payload:
            docs.append(Document(payload["page_content"]))
            
    return docs