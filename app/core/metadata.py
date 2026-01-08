import uuid
import time
from typing import Dict, Any


def normalize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure every memory / knowledge item has a minimal, stable schema.
    """
    return {
        "id": meta.get("id", str(uuid.uuid4())),
        "created_at": meta.get("created_at", time.time()),
        "memory_plane": meta.get("memory_plane", "knowledge"),
        "source": meta.get("source", "unknown"),
        "embedding_ref": meta.get("embedding_ref", "faiss"),
    }
