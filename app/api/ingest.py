from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime

from app.rag.vector_store import add_texts

router = APIRouter(tags=["Ingest"])


class IngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> List[str]:
    """
    Simple sliding window chunking
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


@router.post("/")
async def ingest_text(data: IngestRequest):
    chunks = chunk_text(data.text)

    enriched_chunks = []
    for chunk in chunks:
        enriched_chunks.append(
            f"{chunk}\n\nMETA: {data.metadata} | INGESTED_AT: {datetime.utcnow().isoformat()}"
        )

    add_texts(enriched_chunks)

    return {
        "status": "ingested",
        "chunks_added": len(enriched_chunks),
    }
