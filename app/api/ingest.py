from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from app.services.pipeline import ingest_text
from app.rag.vector_store import add_texts_with_metadata
from app.api.status import mark_ingest, mark_error



router = APIRouter(tags=["Ingest"])

class IngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

@router.post("/")
def ingest_text_endpoint(data: IngestRequest):
    try:
        result = ingest_text(data.text, "api", data.metadata)

        add_texts_with_metadata(
            texts=[data.text],
            metadatas=[{
                "source": "api",
                "memory_type": result["memory_type"]
            }]
        )

        mark_ingest()

        return {
            "status": result["status"],
            "chunks_added": result["chunks_added"],
            "memory_type": result["memory_type"]
        }
    except Exception as e:
        mark_error(f"ingest_failed: {e}")
        raise
