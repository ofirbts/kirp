from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

from app.services.pipeline import ingest_text
from app.rag.vector_store import add_texts_with_metadata
from app.api.status import mark_ingest, mark_error
from app.core.persistence import PersistenceManager
from app.agent.agent import agent

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
                "memory_type": result["memory_type"],
            }],
        )

        # Long-term knowledge
        agent.knowledge.add(data.text, source="api")

        mark_ingest()

        # Persistence hook — ingest
        PersistenceManager.append_event("ingest", {
            "source": "api",
            "memory_type": result["memory_type"],
            "text_length": len(data.text),
        })

        return {
            "chunks_added": result["chunks_added"],
            "memory_type": result["memory_type"],
        }
    except Exception as e:
        mark_error(f"ingest_failed: {e}")
        raise
