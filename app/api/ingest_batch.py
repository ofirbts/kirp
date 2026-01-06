from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from datetime import datetime
from app.rag.chunker import chunk_text  # ← שנה ל-rag.chunker!
from app.rag.vector_store import add_texts

router = APIRouter(tags=["Ingest"])

class IngestRequest(BaseModel):
    text: str
    metadata: dict = {}

@router.post("/batch")
async def ingest_batch(items: List[IngestRequest]):
    all_chunks = []
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
        "chunks_added": len(all_chunks)
    }
