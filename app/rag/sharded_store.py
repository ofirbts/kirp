# app/rag/sharded_store.py
from app.rag.vector_store import add_texts_with_metadata, get_vector_store


class ShardedVectorStore:
    def add(self, shard: str, text: str, metadata: dict):
        metadata = dict(metadata)
        metadata["shard"] = shard
        add_texts_with_metadata([text], [metadata])

    def search(self, shard: str, query: str, k: int = 5):
        vs = get_vector_store()
        results = vs.similarity_search(query, k=k * 2)
        return [r for r in results if r.metadata.get("shard") == shard][:k]
