from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from app.services.pipeline import ingest_text
from app.rag.vector_store import add_texts_with_metadata


router = APIRouter(tags=["Ingest"])

class IngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

@router.post("/")
def ingest_text_endpoint(data: IngestRequest):

    # 1. הפעלת ה־pipeline
    result = ingest_text(data.text, "api", data.metadata)

    # 2. הזרמה ל־Vector Store
    add_texts_with_metadata(
        texts=[data.text],
        metadatas=[{
            "source": "api",
            "memory_type": result["memory_type"]
        }]
    )

    # 3. החזרה ללקוח
    return {
        "status": result["status"],
        "chunks_added": result["chunks_added"],
        "memory_type": result["memory_type"]
    }
