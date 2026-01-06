from fastapi import APIRouter
from typing import List
from datetime import datetime

from app.api.ingest import chunk_text
from app.rag.vector_store import add_texts
from app.models.ingest import IngestRequest

router = APIRouter(tags=["Ingest"])


@router.post("/batch")
async def ingest_batch(items: List[IngestRequest]):
    all_chunks: List[str] = []

    for item in items:
        chunks = chunk_text(item.text)

        for chunk in chunks:
            all_chunks.append(
                f"{chunk}\n\nMETA: {item.metadata} | INGESTED_AT: {datetime.utcnow().isoformat()}"
            )

    add_texts(all_chunks)

    return {
        "status": "ok",
        "documents": len(items),
        "chunks_added": len(all_chunks),
    }
