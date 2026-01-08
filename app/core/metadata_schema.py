from typing import TypedDict
import time
import uuid


class MemoryMetadata(TypedDict):
    id: str
    created_at: float
    source: str
    memory_plane: str
    embedding_ref: str


def ensure_metadata(meta: dict, *, plane: str, source: str) -> MemoryMetadata:
    return {
        "id": meta.get("id", str(uuid.uuid4())),
        "created_at": meta.get("created_at", time.time()),
        "source": source,
        "memory_plane": plane,
        "embedding_ref": meta.get("embedding_ref", "faiss"),
    }
