from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_community.vectorstores import Qdrant
from app.rag.embedder import embeddings

qdrant = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "kirp_vectors"

def init_collection():
    collections = qdrant.get_collections().collections
    existing = [c.name for c in collections]

    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )

def store_texts(texts: list[str]):
    init_collection()
    Qdrant.from_texts(
        texts=texts,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        client=qdrant
    )

def search_similar(query: str, k: int = 3):
    init_collection()
    qdrant_store = Qdrant(
        client=qdrant,
        collection_name=COLLECTION_NAME,
        embeddings=embeddings
    )
    return qdrant_store.similarity_search(query, k=k)
